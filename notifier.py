"""
推送通知模块
负责通过 PushPlus 发送微信消息
"""
import html
import re
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
from datetime import datetime
from config import get_no_proxy
from summarizer import format_summary_for_push, normalize_summary


class WeChatNotifier:
    """微信推送通知器，使用 PushPlus"""

    def __init__(self, token):
        """
        初始化通知器

        Args:
            token: PushPlus Token
        """
        self.token = token
        self.no_proxy = get_no_proxy()
        self.api_url = "http://www.pushplus.plus/send"

    def send_digest(self, hn_articles=None, gh_repos=None, show_customize_tip=False):
        """
        发送日报摘要到微信

        Args:
            hn_articles: HN 文章列表，每篇包含 title, url, summary
            gh_repos: GitHub Trending 项目列表，每个包含 name, url, description, stars, language
            show_customize_tip: 是否在日报末尾提示用户可自定义设置
        """
        if not self.token:
            print("[警告] 未配置 PUSHPLUS_TOKEN，跳过推送。")
            return

        print("[推送] 正在生成日报并推送...")

        title = self._format_title()
        # 使用 HTML 模板：微信内 Markdown 嵌套标题极易错乱
        body = self._format_body_html(hn_articles, gh_repos, show_customize_tip)

        data = {
            "token": self.token,
            "title": title,
            "content": body,
            "template": "html",
        }

        try:
            resp = requests.post(self.api_url, json=data, proxies=self.no_proxy, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 200:
                print(f"[成功] [{title}] 推送完成！")
            else:
                print(f"[失败] 推送被拒绝: {resp.text}")
        except Timeout as e:
            print(f"[错误] 推送请求超时: {e}")
        except ConnectionError as e:
            print(f"[错误] 无法连接到推送服务器: {e}")
        except requests.HTTPError as e:
            print(f"[错误] 推送HTTP错误 {resp.status_code}: {e}")
        except ValueError as e:
            print(f"[错误] 推送服务器返回了无效的JSON: {e}")
        except RequestException as e:
            print(f"[错误] 推送网络错误: {e}")

    def _format_title(self):
        """格式化推送标题"""
        today_str = datetime.now().strftime("%m月%d日")
        return f"{today_str} 技术日报"

    def _esc(self, text) -> str:
        return html.escape("" if text is None else str(text), quote=True)

    def _summary_to_html(self, summary: str) -> str:
        """结构化摘要 → 简洁 HTML 块"""
        normalized = normalize_summary(summary)
        blocks = []
        for line in normalized.splitlines():
            line = line.strip()
            m = re.match(r"^(核心|要点|亮点|适合)\s+(.+)$", line)
            if not m:
                continue
            label, value = m.group(1), m.group(2).strip()
            if label == "要点":
                items = [
                    p.strip()
                    for p in re.split(r"[；;]", value)
                    if p.strip() and p.strip() != "无"
                ]
                if items:
                    lis = "".join(f"<li>{self._esc(item)}</li>" for item in items)
                    blocks.append(
                        f'<div style="margin:6px 0 2px;color:#666;font-size:13px;">'
                        f"<b>{label}</b></div>"
                        f'<ul style="margin:4px 0 8px 18px;padding:0;color:#333;font-size:14px;line-height:1.55;">'
                        f"{lis}</ul>"
                    )
                else:
                    blocks.append(
                        f'<p style="margin:4px 0;font-size:14px;line-height:1.55;">'
                        f'<b style="color:#666;">{label}</b> {self._esc(value)}</p>'
                    )
            else:
                blocks.append(
                    f'<p style="margin:4px 0;font-size:14px;line-height:1.55;">'
                    f'<b style="color:#666;">{label}</b> {self._esc(value)}</p>'
                )
        if not blocks:
            # 兜底：纯文本
            md = format_summary_for_push(summary)
            return f'<p style="font-size:14px;line-height:1.55;">{self._esc(md)}</p>'
        return "".join(blocks)

    def _format_body_html(self, hn_articles, gh_repos, show_customize_tip):
        """生成适合微信阅读的 HTML 正文"""
        parts = [
            '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            'color:#222;max-width:680px;margin:0 auto;">'
        ]

        if hn_articles:
            parts.append(
                f'<h2 style="font-size:18px;border-left:4px solid #ff6600;padding-left:10px;margin:16px 0 12px;">'
                f"Hacker News 精选 · Top {len(hn_articles)}</h2>"
            )
            for idx, item in enumerate(hn_articles, 1):
                title = self._esc(item.get("title", "无标题"))
                url = self._esc(item.get("url", "#"))
                parts.append(
                    '<div style="margin:0 0 16px;padding:12px 14px;background:#fafafa;'
                    'border:1px solid #eee;border-radius:8px;">'
                    f'<div style="font-size:15px;font-weight:600;line-height:1.45;margin-bottom:6px;">'
                    f"{idx}. {title}</div>"
                    f'<div style="margin-bottom:8px;">'
                    f'<a href="{url}" style="color:#ff6600;font-size:13px;text-decoration:none;">阅读原文 →</a>'
                    f"</div>"
                    f'{self._summary_to_html(item.get("summary", ""))}'
                    "</div>"
                )

        if gh_repos:
            parts.append(
                f'<h2 style="font-size:18px;border-left:4px solid #24292f;padding-left:10px;margin:20px 0 12px;">'
                f"GitHub Trending · Top {len(gh_repos)}</h2>"
            )
            parts.append(
                '<table style="width:100%;border-collapse:collapse;font-size:13px;line-height:1.45;">'
                '<thead><tr style="background:#f6f8fa;text-align:left;">'
                '<th style="padding:8px;border-bottom:1px solid #eaecef;">#</th>'
                '<th style="padding:8px;border-bottom:1px solid #eaecef;">仓库</th>'
                '<th style="padding:8px;border-bottom:1px solid #eaecef;">语言</th>'
                '<th style="padding:8px;border-bottom:1px solid #eaecef;">Stars</th>'
                "</tr></thead><tbody>"
            )
            for idx, repo in enumerate(gh_repos, 1):
                name = self._esc(repo.get("name", ""))
                url = self._esc(repo.get("url", "#"))
                lang = self._esc(repo.get("language") or "-")
                stars = repo.get("stars", 0)
                try:
                    stars_s = f"{int(stars):,}"
                except (TypeError, ValueError):
                    stars_s = self._esc(stars)
                desc = self._esc((repo.get("description") or "")[:100])
                parts.append(
                    f'<tr style="border-bottom:1px solid #f0f0f0;">'
                    f'<td style="padding:8px;vertical-align:top;color:#888;">{idx}</td>'
                    f'<td style="padding:8px;vertical-align:top;">'
                    f'<a href="{url}" style="color:#0969da;text-decoration:none;font-weight:600;">{name}</a>'
                    f'<div style="color:#666;margin-top:4px;">{desc}</div></td>'
                    f'<td style="padding:8px;vertical-align:top;white-space:nowrap;">{lang}</td>'
                    f'<td style="padding:8px;vertical-align:top;white-space:nowrap;">★ {stars_s}</td>'
                    f"</tr>"
                )
            parts.append("</tbody></table>")

        if show_customize_tip:
            parts.append(
                '<div style="margin-top:18px;padding:10px 12px;background:#f0f7ff;border-radius:6px;'
                'font-size:12px;color:#444;line-height:1.5;">'
                "<b>提示</b>：可在仓库 Settings → Variables 配置 "
                "<code>HN_TOP_COUNT</code> / <code>GH_TOP_COUNT</code> / "
                "<code>SUMMARY_PROMPT_TEMPLATE</code>（需含 {title} 与 {content}）。"
                "</div>"
            )

        parts.append(
            '<p style="margin-top:20px;color:#999;font-size:11px;text-align:center;">'
            "由 HN Daily Agent 自动生成</p></div>"
        )
        return "".join(parts)
