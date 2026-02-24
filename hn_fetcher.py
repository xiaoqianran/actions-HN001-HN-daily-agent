"""
HN抓取模块
负责从 Hacker News 获取排行榜和文章内容
"""
from typing import List, Dict, Any
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
from config import get_no_proxy


class HNFetcher:
    """Hacker News 数据抓取器"""

    def __init__(self):
        self.no_proxy = get_no_proxy()

    def get_top_stories(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        获取 Hacker News 排行榜前 N 名的文章

        Args:
            n: 获取文章数量，默认 5 篇

        Returns:
            list: 文章列表，每篇文章包含 title, url, score
        """
        if not isinstance(n, int) or n <= 0:
            raise ValueError("n 必须是正整数")
        print(f"[系统] 正在查询 HN 排行榜前 {n} 名...")
        try:
            resp = requests.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                proxies=self.no_proxy,
                timeout=10
            )
            resp.raise_for_status()
            top_ids = resp.json()

            stories = []
            for sid in top_ids[:n]:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    proxies=self.no_proxy,
                    timeout=10
                )
                item_resp.raise_for_status()
                item = item_resp.json()
                if item and item.get('url') and item.get('title'):
                    stories.append({
                        'title': item['title'],
                        'url': item['url'],
                        'score': item.get('score', 0)
                    })
                else:
                    title = item.get('title', '未知') if item else 'API返回null'
                    print(f"[跳过] 无链接或无标题文章: {title}")

            return stories
        except Timeout as e:
            print(f"[错误] HN API 请求超时: {e}")
            return []
        except ConnectionError as e:
            print(f"[错误] 无法连接到 HN API: {e}")
            return []
        except RequestException as e:
            print(f"[错误] 获取 HN 列表失败: {e}")
            return []

    def fetch_content(self, url: str) -> str:
        """
        使用 Jina Reader 抓取文章内容

        Args:
            url: 文章链接

        Returns:
            str: 抓取到的文章内容，失败返回空字符串
        """
        if not url:
            return ""
        print(f"[阅读] 正在抓取: {url} ...")
        jina_url = f"https://r.jina.ai/{url}"
        try:
            response = requests.get(jina_url, proxies=self.no_proxy, timeout=20)
            response.raise_for_status()
            return response.text
        except Timeout as e:
            print(f"   -> 读取超时: {e}")
            return ""
        except ConnectionError as e:
            print(f"   -> 连接失败: {e}")
            return ""
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else "未知"
            print(f"   -> HTTP 错误 {status_code}: {e}")
            return ""
        except RequestException as e:
            print(f"   -> 读取失败: {e}")
            return ""
