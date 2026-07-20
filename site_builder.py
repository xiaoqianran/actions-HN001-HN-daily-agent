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
            f"<p class='eyebrow'>Hacker News · GitHub Trending</p>",
            f"<h1>{_esc(date_id)} 技术日报</h1>",
            f"<p class='meta'>HN {len(hn_articles)} 篇 · Trending {len(gh_repos)} 项"
            f" · 生成于 {_esc((digest.get('generated_at') or '')[:19].replace('T', ' '))} UTC</p>",
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
<article class="card">
  <header class="card-head">
    <span class="idx">{idx}</span>
    <div>
      <h3><a href="{_esc(item.get('url') or '#')}" target="_blank" rel="noopener noreferrer">{_esc(item.get('title') or '无标题')}</a></h3>
      <a class="origin" href="{_esc(item.get('url') or '#')}" target="_blank" rel="noopener noreferrer">阅读原文 →</a>
    </div>
  </header>
  <dl class="summary">
    <div><dt>核心</dt><dd>{_esc(fields.get('核心') or '—')}</dd></div>
    <div><dt>要点</dt><dd>{points_html or _esc(fields.get('要点') or '—')}</dd></div>
    <div><dt>亮点</dt><dd>{_esc(fields.get('亮点') or '—')}</dd></div>
    <div><dt>适合</dt><dd><span class="tag">{_esc(fields.get('适合') or '通用')}</span></dd></div>
  </dl>
</article>
"""
            )
        return (
            f"<section id='hn'><h2>Hacker News 精选 <span class='count'>Top {len(articles)}</span></h2>"
            + "\n".join(cards)
            + "</section>"
        )

    def _render_gh_section(self, repos: List[Dict]) -> str:
        if not repos:
            return "<section id='gh'><h2>GitHub Trending</h2><p class='muted'>今日无条目</p></section>"

        rows = []
        for idx, repo in enumerate(repos, 1):
            stars = repo.get("stars", 0)
            try:
                stars_s = f"{int(stars):,}"
            except (TypeError, ValueError):
                stars_s = str(stars)
            desc = (repo.get("description") or "")[:160]
            rows.append(
                f"""
<tr>
  <td class="num">{idx}</td>
  <td>
    <a class="repo" href="{_esc(repo.get('url') or '#')}" target="_blank" rel="noopener noreferrer">{_esc(repo.get('name') or '')}</a>
    <div class="desc">{_esc(desc)}</div>
  </td>
  <td class="lang">{_esc(repo.get('language') or '—')}</td>
  <td class="stars">★ {stars_s}</td>
</tr>
"""
            )
        return f"""
<section id="gh">
  <h2>GitHub Trending <span class="count">Top {len(repos)}</span></h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>#</th><th>仓库</th><th>语言</th><th>Stars</th></tr></thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
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
            href = (
                f"{base_prefix}/index.html"
                if digests and date == digests[0]["date"] and base_prefix == "."
                else f"{base_prefix}/archive/{date}.html"
            )
            # 首页上最新日期链到 index；归档页上最新也链到 ../index.html
            if digests and date == digests[0]["date"]:
                href = f"{base_prefix}/index.html"
            else:
                href = f"{base_prefix}/archive/{date}.html"
            archive_links.append(
                f'<li><a class="{cls}" href="{href}">{_esc(date)}</a></li>'
            )

        archive_html = (
            "<ul class='archive-list'>" + "".join(archive_links) + "</ul>"
            if archive_links
            else "<p class='muted'>暂无归档</p>"
        )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="Hacker News + GitHub Trending 每日技术日报" />
  <link rel="stylesheet" href="{base_prefix}/styles.css" />
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <a class="brand" href="{base_prefix}/index.html">HN Daily</a>
      <p class="sidebar-desc">Hacker News 精选 + GitHub Trending 完整汇总</p>
      <nav>
        <h2>归档</h2>
        {archive_html}
      </nav>
      <footer class="sidebar-foot">GitHub Pages · Actions 自动部署</footer>
    </aside>
    <main class="content">
      {body}
      <footer class="page-foot">由 actions-HN001-HN-daily-agent 自动生成 · 内容汇总不拆分</footer>
    </main>
  </div>
</body>
</html>
"""

    def _css(self) -> str:
        return """
:root {
  --bg: #0b1020;
  --panel: #121a2f;
  --card: #172038;
  --border: #273352;
  --text: #e8eefc;
  --muted: #93a0bf;
  --accent: #ff6b2c;
  --accent2: #5b9dff;
  --tag: #243356;
  --shadow: 0 10px 30px rgba(0,0,0,.25);
  --radius: 14px;
  --font: "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text); font-family: var(--font); }
a { color: var(--accent2); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow: auto;
  padding: 24px 18px; border-right: 1px solid var(--border); background: #0a0f1c;
}
.brand { display: inline-block; font-weight: 800; font-size: 1.25rem; color: var(--text); letter-spacing: .3px; }
.sidebar-desc { color: var(--muted); font-size: .85rem; line-height: 1.5; margin: 10px 0 22px; }
.sidebar h2 { font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 0 0 10px; }
.archive-list { list-style: none; margin: 0; padding: 0; }
.archive-list a {
  display: block; padding: 8px 10px; border-radius: 8px; color: var(--muted); font-size: .92rem;
}
.archive-list a:hover, .archive-list a.active {
  background: var(--panel); color: var(--text); text-decoration: none;
}
.sidebar-foot { margin-top: 28px; font-size: .72rem; color: #66748f; }
.content { padding: 28px 32px 48px; max-width: 980px; }
.hero { margin-bottom: 28px; }
.eyebrow { color: var(--accent); font-size: .8rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; margin: 0 0 8px; }
.hero h1 { margin: 0 0 8px; font-size: 1.9rem; line-height: 1.25; }
.meta, .muted { color: var(--muted); }
section { margin: 28px 0 36px; }
section > h2 {
  display: flex; align-items: baseline; gap: 10px;
  font-size: 1.25rem; margin: 0 0 16px; padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.count {
  font-size: .78rem; font-weight: 600; color: var(--muted);
  background: var(--tag); padding: 3px 8px; border-radius: 999px;
}
.card {
  background: linear-gradient(180deg, var(--card), var(--panel));
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 16px 18px; margin: 0 0 14px; box-shadow: var(--shadow);
}
.card-head { display: flex; gap: 12px; align-items: flex-start; }
.idx {
  flex: 0 0 auto; width: 28px; height: 28px; border-radius: 8px;
  display: grid; place-items: center; background: rgba(255,107,44,.15);
  color: var(--accent); font-weight: 700; font-size: .85rem;
}
.card h3 { margin: 0 0 6px; font-size: 1.05rem; line-height: 1.4; }
.card h3 a { color: var(--text); }
.card h3 a:hover { color: var(--accent); }
.origin { font-size: .82rem; color: var(--accent); }
.summary { margin: 12px 0 0; }
.summary > div { display: grid; grid-template-columns: 48px 1fr; gap: 10px; margin: 8px 0; }
.summary dt {
  margin: 0; color: var(--muted); font-size: .78rem; font-weight: 700;
  letter-spacing: .04em; padding-top: 2px;
}
.summary dd { margin: 0; line-height: 1.55; color: #d7e0f5; font-size: .95rem; }
.points { margin: 0; padding-left: 18px; }
.points li { margin: 2px 0; }
.tag {
  display: inline-block; background: var(--tag); border: 1px solid var(--border);
  border-radius: 999px; padding: 2px 10px; font-size: .82rem; color: #c8d6f5;
}
.table-wrap {
  overflow: auto; border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--panel); box-shadow: var(--shadow);
}
table { width: 100%; border-collapse: collapse; font-size: .92rem; }
th, td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: top; text-align: left; }
th { color: var(--muted); font-size: .78rem; letter-spacing: .04em; background: rgba(0,0,0,.18); }
tr:last-child td { border-bottom: 0; }
.num { width: 40px; color: var(--muted); }
.repo { font-weight: 700; color: var(--text); }
.desc { color: var(--muted); font-size: .85rem; margin-top: 4px; line-height: 1.45; }
.lang, .stars { white-space: nowrap; color: #c3cee8; }
.page-foot { margin-top: 40px; color: #66748f; font-size: .78rem; }

@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: relative; height: auto; border-right: 0; border-bottom: 1px solid var(--border); }
  .content { padding: 20px 16px 36px; }
  .summary > div { grid-template-columns: 1fr; gap: 4px; }
}
"""
