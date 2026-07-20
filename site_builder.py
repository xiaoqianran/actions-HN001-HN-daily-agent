"""
静态站点构建模块
将 HN 摘要 + GitHub Trending 汇总为完整日报页，供 GitHub Pages 部署。
不拆分推送：同一天一份完整页面。
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from summarizer import normalize_summary

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
ARCHIVE_DIR = PUBLIC_DIR / "archive"


def _esc(text: Any) -> str:
    return html.escape("" if text is None else str(text), quote=True)


def _today_id() -> str:
    # 使用 UTC 日期，与 Actions 时区一致，避免跨日混乱
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_summary_fields(summary: str) -> Dict[str, str]:
    normalized = normalize_summary(summary)
    fields = {"核心": "", "要点": "", "亮点": "", "适合": ""}
    for line in normalized.splitlines():
        m = re.match(r"^(核心|要点|亮点|适合)\s+(.+)$", line.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


class SiteBuilder:
    """汇总日报并生成 GitHub Pages 静态站点"""

    def __init__(self, data_dir: Path = DATA_DIR, public_dir: Path = PUBLIC_DIR):
        self.data_dir = data_dir
        self.public_dir = public_dir
        self.archive_dir = public_dir / "archive"

    def publish(
        self,
        hn_articles: Optional[List[Dict]] = None,
        gh_repos: Optional[List[Dict]] = None,
        date_id: Optional[str] = None,
    ) -> Path:
        """
        写入当日 JSON 数据，并重建整个站点（首页 + 全部归档）。
        返回生成的当日页面路径。
        """
        date_id = date_id or _today_id()
        hn_articles = hn_articles or []
        gh_repos = gh_repos or []

        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "date": date_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hn_count": len(hn_articles),
            "gh_count": len(gh_repos),
            "hn_articles": hn_articles,
            "gh_repos": gh_repos,
        }
        data_path = self.data_dir / f"{date_id}.json"
        data_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[站点] 已写入数据 {data_path}")

        self.rebuild()
        page = self.archive_dir / f"{date_id}.html"
        print(f"[站点] 已生成页面 {page}")
        print(f"[站点] 首页 {self.public_dir / 'index.html'}")
        return page

    def rebuild(self) -> None:
        """根据 data/*.json 重建 public/ 全部页面"""
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        digests = self._load_all_digests()
        (self.public_dir / "styles.css").write_text(self._css(), encoding="utf-8")
        (self.public_dir / "theme.js").write_text(self._theme_js(), encoding="utf-8")

        # 归档页
        for d in digests:
            path = self.archive_dir / f"{d['date']}.html"
            path.write_text(
                self._render_digest_page(d, digests, is_home=False),
                encoding="utf-8",
            )

        # 首页：最新一天；若无数据则占位
        if digests:
            latest = digests[0]
            index_html = self._render_digest_page(latest, digests, is_home=True)
        else:
            index_html = self._render_empty_home()
        (self.public_dir / "index.html").write_text(index_html, encoding="utf-8")

        # 简单 404
        (self.public_dir / "404.html").write_text(
            self._shell(
                "页面未找到",
                "<h1>404</h1><p>页面不存在。<a href=\"./index.html\">返回首页</a></p>",
                digests,
                active_date=None,
                base_prefix=".",
            ),
            encoding="utf-8",
        )

    def _load_all_digests(self) -> List[Dict]:
        if not self.data_dir.exists():
            return []
        items = []
        for path in sorted(self.data_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "date" in data:
                    items.append(data)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[站点警告] 跳过损坏数据文件 {path}: {e}")
        items.sort(key=lambda x: x.get("date", ""), reverse=True)
        return items

    def _render_empty_home(self) -> str:
        body = (
            "<section class='hero'><h1>HN Daily Digest</h1>"
            "<p class='muted'>暂无日报数据。等待下一次 Actions 运行。</p></section>"
        )
        return self._shell("HN Daily Digest", body, [], active_date=None, base_prefix=".")

    def _render_digest_page(
        self,
        digest: Dict,
        all_digests: List[Dict],
        is_home: bool,
    ) -> str:
        date_id = digest["date"]
        base = "." if is_home else ".."
        title = f"{date_id} 技术日报" if not is_home else f"技术日报 · {date_id}"

        hn_articles = digest.get("hn_articles") or []
        gh_repos = digest.get("gh_repos") or []

        parts = [
            "<section class='hero'>",
            f"<p class='eyebrow'>Catppuccin · Hacker News · GitHub Trending</p>",
            f"<h1>{_esc(date_id)} 技术日报</h1>",
            f"<p class='meta'>HN {len(hn_articles)} 篇 · Trending {len(gh_repos)} 项"
            f" · 生成于 {_esc((digest.get('generated_at') or '')[:19].replace('T', ' '))} UTC</p>",
            "<div class='hero-pills' aria-hidden='true'>"
            "<span class='pill peach'>Peach</span>"
            "<span class='pill mauve'>Mauve</span>"
            "<span class='pill blue'>Blue</span>"
            "<span class='pill green'>Green</span>"
            "</div>",
            "</section>",
            # 同一页完整汇总，不拆分
            self._render_hn_section(hn_articles),
            self._render_gh_section(gh_repos),
        ]
        return self._shell(
            title,
            "\n".join(parts),
            all_digests,
            active_date=date_id,
            base_prefix=base,
        )

    def _render_hn_section(self, articles: List[Dict]) -> str:
        if not articles:
            return "<section><h2>Hacker News</h2><p class='muted'>今日无条目</p></section>"

        cards = []
        for idx, item in enumerate(articles, 1):
            fields = _parse_summary_fields(item.get("summary") or "")
            points = [
                p.strip()
                for p in re.split(r"[；;]", fields.get("要点") or "")
                if p.strip() and p.strip() != "无"
            ]
            points_html = (
                "<ul class='points'>"
                + "".join(f"<li>{_esc(p)}</li>" for p in points)
                + "</ul>"
                if points
                else ""
            )
            cards.append(
                f"""
<article class="card hn-card">
  <header class="card-head">
    <span class="idx" aria-hidden="true">{idx}</span>
    <div class="card-title">
      <h3><a href="{_esc(item.get('url') or '#')}" target="_blank" rel="noopener noreferrer">{_esc(item.get('title') or '无标题')}</a></h3>
      <a class="origin" href="{_esc(item.get('url') or '#')}" target="_blank" rel="noopener noreferrer">阅读原文 →</a>
    </div>
  </header>
  <dl class="summary">
    <div class="row row-core"><dt>核心</dt><dd>{_esc(fields.get('核心') or '—')}</dd></div>
    <div class="row row-points"><dt>要点</dt><dd>{points_html or _esc(fields.get('要点') or '—')}</dd></div>
    <div class="row row-spark"><dt>亮点</dt><dd>{_esc(fields.get('亮点') or '—')}</dd></div>
    <div class="row row-fit"><dt>适合</dt><dd><span class="tag">{_esc(fields.get('适合') or '通用')}</span></dd></div>
  </dl>
</article>
"""
            )
        return (
            f"<section id='hn' aria-labelledby='hn-heading'>"
            f"<h2 id='hn-heading'><span class='dot hn'></span>Hacker News 精选 "
            f"<span class='count'>Top {len(articles)}</span></h2>"
            f"<div class='cards-grid'>"
            + "\n".join(cards)
            + "</div></section>"
        )

    def _render_gh_section(self, repos: List[Dict]) -> str:
        if not repos:
            return "<section id='gh'><h2>GitHub Trending</h2><p class='muted'>今日无条目</p></section>"

        rows = []
        mobile_cards = []
        for idx, repo in enumerate(repos, 1):
            stars = repo.get("stars", 0)
            try:
                stars_s = f"{int(stars):,}"
            except (TypeError, ValueError):
                stars_s = str(stars)
            # 优先展示简体中文简介；原文保留为 title 悬停提示
            desc = (repo.get("description") or "")[:200]
            original = (repo.get("description_original") or "").strip()
            title_attr = ""
            if original and original != desc:
                title_attr = f' title="原文: {_esc(original[:200])}"'
            name = _esc(repo.get("name") or "")
            url = _esc(repo.get("url") or "#")
            lang = _esc(repo.get("language") or "—")
            desc_e = _esc(desc)
            rows.append(
                f"""
<tr>
  <td class="num">{idx}</td>
  <td>
    <a class="repo" href="{url}" target="_blank" rel="noopener noreferrer">{name}</a>
    <div class="desc"{title_attr}>{desc_e}</div>
  </td>
  <td class="lang">{lang}</td>
  <td class="stars">★ {stars_s}</td>
</tr>
"""
            )
            mobile_cards.append(
                f"""
<article class="card gh-card">
  <header class="gh-card-head">
    <span class="idx" aria-hidden="true">{idx}</span>
    <div class="card-title">
      <h3><a class="repo" href="{url}" target="_blank" rel="noopener noreferrer">{name}</a></h3>
      <div class="gh-meta">
        <span class="lang">{lang}</span>
        <span class="stars">★ {stars_s}</span>
      </div>
    </div>
  </header>
  <p class="desc"{title_attr}>{desc_e}</p>
</article>
"""
            )
        return f"""
<section id="gh" aria-labelledby="gh-heading">
  <h2 id="gh-heading"><span class="dot gh"></span>GitHub Trending <span class="count">Top {len(repos)}</span></h2>
  <div class="table-wrap gh-table" role="region" aria-label="GitHub Trending 列表" tabindex="0">
    <table>
      <thead><tr><th scope="col">#</th><th scope="col">仓库</th><th scope="col">语言</th><th scope="col">Stars</th></tr></thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
  <div class="cards-grid gh-cards" aria-label="GitHub Trending 卡片列表">
    {''.join(mobile_cards)}
  </div>
</section>
"""

    def _shell(
        self,
        title: str,
        body: str,
        digests: List[Dict],
        active_date: Optional[str],
        base_prefix: str,
    ) -> str:
        archive_links = []
        for d in digests[:60]:
            date = d["date"]
            cls = "active" if date == active_date else ""
            if digests and date == digests[0]["date"]:
                href = f"{base_prefix}/index.html"
            else:
                href = f"{base_prefix}/archive/{date}.html"
            aria = ' aria-current="page"' if date == active_date else ""
            archive_links.append(
                f'<li><a class="{cls}" href="{href}"{aria}>{_esc(date)}</a></li>'
            )

        archive_html = (
            "<ul class='archive-list'>" + "".join(archive_links) + "</ul>"
            if archive_links
            else "<p class='muted'>暂无归档</p>"
        )

        return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="mocha">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="Hacker News + GitHub Trending 每日技术日报 · Catppuccin" />
  <meta name="color-scheme" content="dark light" />
  <meta name="theme-color" content="#1e1e2e" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{base_prefix}/styles.css" />
  <script>
    (function () {{
      try {{
        var t = localStorage.getItem("ctp-theme");
        if (!t) {{
          t = window.matchMedia("(prefers-color-scheme: light)").matches ? "latte" : "mocha";
        }}
        document.documentElement.setAttribute("data-theme", t);
      }} catch (e) {{
        document.documentElement.setAttribute("data-theme", "mocha");
      }}
    }})();
  </script>
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <div class="layout">
    <aside class="sidebar" aria-label="站点导航">
      <div class="brand-row">
        <a class="brand" href="{base_prefix}/index.html">
          <span class="brand-mark" aria-hidden="true">猫</span>
          <span>HN Daily</span>
        </a>
        <button type="button" class="theme-toggle" id="theme-toggle" aria-label="切换 Catppuccin 主题">
          <span class="theme-icon" aria-hidden="true">◐</span>
          <span class="theme-label">Mocha</span>
        </button>
      </div>
      <p class="sidebar-desc">Catppuccin Userstyles · HN 精选 + GitHub Trending 完整汇总</p>
      <nav aria-label="日报归档">
        <h2>归档</h2>
        {archive_html}
      </nav>
      <footer class="sidebar-foot">
        <span class="flavor-badge">Catppuccin</span>
        GitHub Pages · Actions
      </footer>
    </aside>
    <main class="content" id="main">
      {body}
      <footer class="page-foot">由 actions-HN001-HN-daily-agent 自动生成 · 风格 Catppuccin</footer>
    </main>
  </div>
  <script src="{base_prefix}/theme.js" defer></script>
</body>
</html>
"""

    def _css(self) -> str:
        # Catppuccin Mocha (default) + Latte (light) — official palette
        # Soft UI Evolution: readable contrast, subtle depth, focus rings
        return """
/* ========== Catppuccin flavors ========== */
:root, [data-theme="mocha"] {
  --ctp-rosewater: #f5e0dc;
  --ctp-flamingo: #f2cdcd;
  --ctp-pink: #f5c2e7;
  --ctp-mauve: #cba6f7;
  --ctp-red: #f38ba8;
  --ctp-maroon: #eba0ac;
  --ctp-peach: #fab387;
  --ctp-yellow: #f9e2af;
  --ctp-green: #a6e3a1;
  --ctp-teal: #94e2d5;
  --ctp-sky: #89dceb;
  --ctp-sapphire: #74c7ec;
  --ctp-blue: #89b4fa;
  --ctp-lavender: #b4befe;
  --ctp-text: #cdd6f4;
  --ctp-subtext1: #bac2de;
  --ctp-subtext0: #a6adc8;
  --ctp-overlay2: #9399b2;
  --ctp-overlay1: #7f849c;
  --ctp-overlay0: #6c7086;
  --ctp-surface2: #585b70;
  --ctp-surface1: #45475a;
  --ctp-surface0: #313244;
  --ctp-base: #1e1e2e;
  --ctp-mantle: #181825;
  --ctp-crust: #11111b;
  color-scheme: dark;
}

[data-theme="latte"] {
  --ctp-rosewater: #dc8a78;
  --ctp-flamingo: #dd7878;
  --ctp-pink: #ea76cb;
  --ctp-mauve: #8839ef;
  --ctp-red: #d20f39;
  --ctp-maroon: #e64553;
  --ctp-peach: #fe640b;
  --ctp-yellow: #df8e1d;
  --ctp-green: #40a02b;
  --ctp-teal: #179299;
  --ctp-sky: #04a5e5;
  --ctp-sapphire: #209fb5;
  --ctp-blue: #1e66f5;
  --ctp-lavender: #7287fd;
  --ctp-text: #4c4f69;
  --ctp-subtext1: #5c5f77;
  --ctp-subtext0: #6c6f85;
  --ctp-overlay2: #7c7f93;
  --ctp-overlay1: #8c8fa1;
  --ctp-overlay0: #9ca0b0;
  --ctp-surface2: #acb0be;
  --ctp-surface1: #bcc0cc;
  --ctp-surface0: #ccd0da;
  --ctp-base: #eff1f5;
  --ctp-mantle: #e6e9ef;
  --ctp-crust: #dce0e8;
  color-scheme: light;
}

/* Semantic tokens */
:root {
  --bg: var(--ctp-base);
  --bg-sidebar: var(--ctp-mantle);
  --bg-card: var(--ctp-mantle);
  --bg-elevated: var(--ctp-surface0);
  --border: color-mix(in srgb, var(--ctp-surface1) 85%, transparent);
  --text: var(--ctp-text);
  --muted: var(--ctp-subtext0);
  --link: var(--ctp-blue);
  --link-hover: var(--ctp-sky);
  --accent: var(--ctp-peach);
  --accent-2: var(--ctp-mauve);
  --focus: var(--ctp-lavender);
  --radius: 14px;
  --radius-sm: 10px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --shadow: 0 8px 24px color-mix(in srgb, var(--ctp-crust) 35%, transparent);
  --font: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --ease: 200ms cubic-bezier(0.2, 0.8, 0.2, 1);
  --sidebar-w: clamp(200px, 22vw, 280px);
  --content-max: 92rem;
  --card-min: min(100%, 22rem);
}

*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: clamp(15px, 0.35vw + 14px, 17px);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
  overflow-x: clip;
}
body {
  min-height: 100dvh;
  background-image:
    radial-gradient(1200px 500px at 10% -10%, color-mix(in srgb, var(--ctp-mauve) 14%, transparent), transparent 60%),
    radial-gradient(900px 400px at 100% 0%, color-mix(in srgb, var(--ctp-peach) 10%, transparent), transparent 55%);
  background-attachment: fixed;
}

/* A11y */
.skip-link {
  position: absolute; left: -999px; top: 0; z-index: 100;
  background: var(--ctp-lavender); color: var(--ctp-base);
  padding: 8px 12px; border-radius: 0 0 8px 0; font-weight: 600;
}
.skip-link:focus { left: 0; }
:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}
::selection {
  background: color-mix(in srgb, var(--ctp-overlay2) 35%, transparent);
  color: var(--ctp-text);
}

a { color: var(--link); text-decoration: none; transition: color var(--ease); }
a:hover { color: var(--link-hover); text-decoration: underline; text-underline-offset: 3px; }

/* ========== Fluid shell ========== */
.layout {
  display: grid;
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  min-height: 100dvh;
  width: 100%;
}

/* Sidebar */
.sidebar {
  position: sticky; top: 0; height: 100dvh; overflow: auto;
  padding: clamp(16px, 2vw, 28px) clamp(12px, 1.5vw, 20px);
  border-right: 1px solid var(--border);
  background: color-mix(in srgb, var(--bg-sidebar) 92%, transparent);
  backdrop-filter: blur(10px);
  min-width: 0;
}
.brand-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  margin-bottom: var(--space-3); flex-wrap: wrap;
}
.brand {
  display: inline-flex; align-items: center; gap: 10px; min-width: 0;
  font-weight: 700; font-size: 1.1rem; color: var(--text); letter-spacing: 0.2px;
}
.brand:hover { color: var(--ctp-lavender); text-decoration: none; }
.brand-mark {
  width: 32px; height: 32px; border-radius: 10px; flex: 0 0 auto;
  display: grid; place-items: center;
  font-size: 0.85rem; font-weight: 700;
  color: var(--ctp-base);
  background: linear-gradient(145deg, var(--ctp-mauve), var(--ctp-blue));
  box-shadow: 0 4px 12px color-mix(in srgb, var(--ctp-mauve) 35%, transparent);
}
.theme-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--ctp-subtext1);
  border-radius: 999px;
  padding: 6px 10px;
  font: inherit; font-size: 0.75rem; font-weight: 600;
  cursor: pointer;
  transition: background var(--ease), border-color var(--ease), color var(--ease), transform 150ms ease;
}
.theme-toggle:hover {
  border-color: var(--ctp-lavender);
  color: var(--ctp-text);
  background: color-mix(in srgb, var(--ctp-lavender) 12%, var(--bg-elevated));
}
.theme-toggle:active { transform: scale(0.97); }
.theme-icon { color: var(--ctp-yellow); }
.sidebar-desc {
  color: var(--muted); font-size: 0.86rem; line-height: 1.5;
  margin: 0 0 var(--space-5);
  overflow-wrap: anywhere;
}
.sidebar h2 {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ctp-overlay1); margin: 0 0 var(--space-2); font-weight: 700;
}
.archive-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.archive-list a {
  display: block; padding: 8px 10px; border-radius: var(--radius-sm);
  color: var(--ctp-subtext0); font-size: 0.9rem; font-family: var(--font-mono);
  transition: background var(--ease), color var(--ease);
}
.archive-list a:hover {
  background: color-mix(in srgb, var(--ctp-surface0) 80%, transparent);
  color: var(--ctp-text); text-decoration: none;
}
.archive-list a.active {
  background: color-mix(in srgb, var(--ctp-lavender) 18%, var(--ctp-surface0));
  color: var(--ctp-lavender); font-weight: 600;
}
.sidebar-foot {
  margin-top: var(--space-6); font-size: 0.72rem; color: var(--ctp-overlay0);
  display: flex; flex-direction: column; gap: 8px;
}
.flavor-badge {
  display: inline-flex; width: fit-content;
  padding: 3px 8px; border-radius: 999px;
  background: color-mix(in srgb, var(--ctp-mauve) 18%, transparent);
  color: var(--ctp-mauve); font-weight: 700; letter-spacing: 0.04em;
}

/* Main — fills remaining viewport, not a fixed narrow column */
.content {
  min-width: 0;
  width: 100%;
  max-width: none;
  padding: clamp(16px, 2.5vw, 36px) clamp(14px, 3vw, 40px) clamp(32px, 5vw, 64px);
}
.content > * {
  width: 100%;
  max-width: var(--content-max);
}

.hero {
  margin-bottom: clamp(16px, 2vw, 28px);
  padding: clamp(16px, 2.2vw, 28px);
  border-radius: calc(var(--radius) + 4px);
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--ctp-surface0) 70%, transparent),
      color-mix(in srgb, var(--ctp-mantle) 90%, transparent));
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.eyebrow {
  color: var(--ctp-peach); font-size: 0.78rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 8px;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: clamp(1.4rem, 1.2vw + 1.1rem, 2.15rem);
  line-height: 1.25; letter-spacing: -0.02em; color: var(--ctp-text);
  overflow-wrap: anywhere;
}
.meta, .muted { color: var(--muted); font-size: 0.92rem; }
.hero-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.pill {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
  padding: 3px 9px; border-radius: 999px; font-family: var(--font-mono);
  border: 1px solid transparent;
}
.pill.peach { color: var(--ctp-peach); background: color-mix(in srgb, var(--ctp-peach) 16%, transparent); border-color: color-mix(in srgb, var(--ctp-peach) 30%, transparent); }
.pill.mauve { color: var(--ctp-mauve); background: color-mix(in srgb, var(--ctp-mauve) 16%, transparent); border-color: color-mix(in srgb, var(--ctp-mauve) 30%, transparent); }
.pill.blue { color: var(--ctp-blue); background: color-mix(in srgb, var(--ctp-blue) 16%, transparent); border-color: color-mix(in srgb, var(--ctp-blue) 30%, transparent); }
.pill.green { color: var(--ctp-green); background: color-mix(in srgb, var(--ctp-green) 16%, transparent); border-color: color-mix(in srgb, var(--ctp-green) 30%, transparent); }

section { margin: clamp(20px, 3vw, 36px) 0; }
section > h2 {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
  font-size: clamp(1.05rem, 0.4vw + 1rem, 1.3rem);
  margin: 0 0 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border); color: var(--ctp-text);
}
.dot {
  width: 10px; height: 10px; border-radius: 999px; display: inline-block; flex: 0 0 auto;
  box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 18%, transparent);
}
.dot.hn { background: var(--ctp-peach); color: var(--ctp-peach); }
.dot.gh { background: var(--ctp-blue); color: var(--ctp-blue); }
.count {
  font-size: 0.75rem; font-weight: 600; color: var(--ctp-subtext0);
  background: var(--ctp-surface0); border: 1px solid var(--border);
  padding: 3px 9px; border-radius: 999px; font-family: var(--font-mono);
}

/* ========== Dynamic card grid (auto-fill) ========== */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--card-min), 1fr));
  gap: clamp(12px, 1.5vw, 18px);
  align-items: stretch;
  width: 100%;
}

.card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: clamp(12px, 1.4vw, 18px);
  margin: 0;
  box-shadow: var(--shadow);
  transition: border-color var(--ease), transform var(--ease), box-shadow var(--ease);
}
.card:hover {
  border-color: color-mix(in srgb, var(--ctp-lavender) 40%, var(--border));
  box-shadow: 0 12px 28px color-mix(in srgb, var(--ctp-crust) 28%, transparent);
}
.card-head, .gh-card-head {
  display: flex; gap: 12px; align-items: flex-start; min-width: 0;
}
.card-title { min-width: 0; flex: 1 1 auto; }
.idx {
  flex: 0 0 auto; width: 30px; height: 30px; border-radius: 10px;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--ctp-peach) 18%, var(--ctp-surface0));
  color: var(--ctp-peach); font-weight: 700; font-size: 0.85rem;
  font-family: var(--font-mono);
}
.gh-card .idx {
  background: color-mix(in srgb, var(--ctp-blue) 18%, var(--ctp-surface0));
  color: var(--ctp-blue);
}
.card h3 {
  margin: 0 0 6px;
  font-size: clamp(0.98rem, 0.25vw + 0.92rem, 1.08rem);
  line-height: 1.4;
}
.card h3 a {
  color: var(--ctp-text); font-weight: 600;
  overflow-wrap: anywhere; word-break: break-word;
}
.card h3 a:hover { color: var(--ctp-lavender); }
.origin { font-size: 0.82rem; color: var(--ctp-peach); font-weight: 600; }
.origin:hover { color: var(--ctp-yellow); }

.summary {
  margin: 14px 0 0;
  display: grid;
  gap: 8px;
  flex: 1 1 auto;
}
.summary .row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--ctp-surface0) 55%, transparent);
  min-width: 0;
}
.summary dt {
  margin: 0; font-size: 0.75rem; font-weight: 700;
  letter-spacing: 0.04em; padding-top: 2px; white-space: nowrap;
}
.summary dd {
  margin: 0; line-height: 1.6; color: var(--ctp-text);
  font-size: 0.95rem; min-width: 0;
  overflow-wrap: anywhere; word-break: break-word;
}
.row-core dt { color: var(--ctp-peach); }
.row-points dt { color: var(--ctp-blue); }
.row-spark dt { color: var(--ctp-yellow); }
.row-fit dt { color: var(--ctp-green); }
.points { margin: 0; padding-left: 1.1rem; }
.points li { margin: 2px 0; overflow-wrap: anywhere; }
.points li::marker { color: var(--ctp-sapphire); }
.tag {
  display: inline-block;
  max-width: 100%;
  background: color-mix(in srgb, var(--ctp-green) 16%, var(--ctp-surface0));
  border: 1px solid color-mix(in srgb, var(--ctp-green) 30%, var(--border));
  border-radius: 999px; padding: 2px 10px; font-size: 0.82rem;
  color: var(--ctp-green); font-weight: 600;
  overflow-wrap: anywhere;
}

/* GH desktop table / mobile cards */
.gh-table { display: block; }
.gh-cards { display: none; }
.gh-meta {
  display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center;
  margin-top: 4px;
}
.gh-card .desc { margin: 10px 0 0; }

.table-wrap {
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  box-shadow: var(--shadow);
  width: 100%;
  max-width: 100%;
}
table {
  width: 100%;
  min-width: 0;
  border-collapse: collapse;
  font-size: 0.92rem;
  table-layout: fixed;
}
th, td {
  padding: clamp(10px, 1.2vw, 14px);
  border-bottom: 1px solid var(--border);
  vertical-align: top; text-align: left;
}
th {
  color: var(--ctp-subtext0); font-size: 0.75rem; letter-spacing: 0.05em;
  text-transform: uppercase; background: color-mix(in srgb, var(--ctp-surface0) 70%, transparent);
  position: sticky; top: 0;
}
th:nth-child(1), td.num { width: 3rem; }
th:nth-child(3), td.lang { width: 7rem; }
th:nth-child(4), td.stars { width: 6.5rem; }
tbody tr { transition: background var(--ease); }
tbody tr:hover { background: color-mix(in srgb, var(--ctp-surface0) 45%, transparent); }
tr:last-child td { border-bottom: 0; }
.num { color: var(--ctp-overlay1); font-family: var(--font-mono); }
.repo {
  font-weight: 700; color: var(--ctp-text);
  overflow-wrap: anywhere; word-break: break-word;
}
.repo:hover { color: var(--ctp-blue); }
.desc {
  color: var(--muted); font-size: 0.85rem; margin-top: 4px; line-height: 1.5;
  overflow-wrap: anywhere; word-break: break-word;
}
.lang { color: var(--ctp-sapphire); font-weight: 600; font-size: 0.85rem; }
.stars { color: var(--ctp-yellow); font-family: var(--font-mono); font-size: 0.85rem; }
.page-foot {
  margin-top: clamp(28px, 4vw, 40px); color: var(--ctp-overlay0); font-size: 0.78rem;
  padding-top: 16px; border-top: 1px solid var(--border);
}

/* ========== Breakpoints ========== */
@media (max-width: 1100px) {
  :root { --card-min: min(100%, 20rem); }
}

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar {
    position: relative; height: auto; max-height: none;
    border-right: 0; border-bottom: 1px solid var(--border);
  }
  .archive-list {
    display: flex; flex-wrap: wrap; gap: 6px;
  }
  .archive-list a { padding: 6px 10px; }
  :root { --card-min: min(100%, 18rem); }
}

@media (max-width: 720px) {
  /* 窄屏：文章单列更易读；GH 表格切卡片 */
  :root { --card-min: 100%; }
  .summary .row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .summary dt { white-space: normal; }
  .gh-table { display: none; }
  .gh-cards { display: grid; }
  table { table-layout: auto; min-width: 520px; }
}

@media (min-width: 1400px) {
  :root {
    --card-min: min(100%, 24rem);
    --content-max: 100rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
"""

    def _theme_js(self) -> str:
        return """
(function () {
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  function labelFor(theme) {
    return theme === "latte" ? "Latte" : "Mocha";
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem("ctp-theme", theme); } catch (e) {}
    var label = btn.querySelector(".theme-label");
    if (label) label.textContent = labelFor(theme);
    btn.setAttribute("aria-label", "当前主题 " + labelFor(theme) + "，点击切换");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "latte" ? "#eff1f5" : "#1e1e2e");
  }

  var current = root.getAttribute("data-theme") || "mocha";
  apply(current);

  btn.addEventListener("click", function () {
    var next = (root.getAttribute("data-theme") === "latte") ? "mocha" : "latte";
    apply(next);
  });
})();
"""
