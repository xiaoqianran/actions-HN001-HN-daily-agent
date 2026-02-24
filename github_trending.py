"""
GitHub Trending 抓取模块
通过 OSS Insight API 获取热门项目
"""
import requests
from config import get_no_proxy


class GitHubTrendingFetcher:
    """GitHub Trending 数据抓取器"""

    def __init__(self):
        self.no_proxy = get_no_proxy()
        self.api_url = "https://api.ossinsight.io/v1/trends/repos"

    def get_trending_repos(self, n=5):
        """
        获取 GitHub Trending 前 N 名的项目
        通过 OSS Insight API 获取当前热门项目

        Args:
            n: 获取项目数量，默认 5 个

        Returns:
            list: 项目列表，每个项目包含 name, url, description, stars, language
        """
        print(f"[系统] 正在查询 GitHub Trending 前 {n} 名...")

        params = {
            "limit": n
        }

        try:
            response = requests.get(
                self.api_url,
                params=params,
                proxies=self.no_proxy,
                timeout=20,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()

            data = response.json()
            return self._parse_repos(data.get("data", {}).get("rows", []), n)
        except Exception as e:
            print(f"[错误] 获取 GitHub Trending 失败: {e}")
            return []

    def _parse_repos(self, rows, n=5):
        """
        解析 OSS Insight API 返回的项目数据

        Args:
            rows: OSS Insight API 返回的项目行数据
            n: 需要返回的项目数量

        Returns:
            list: 解析后的项目列表
        """
        repos = []
        for row in rows[:n]:  # 只取前 n 个
            repos.append({
                "name": row.get("repo_name"),
                "url": f"https://github.com/{row.get('repo_name')}",
                "description": row.get("description") or "暂无描述",
                "stars": int(row.get("stars", 0)),
                "language": row.get("primary_language") or "Unknown"
            })
        return repos
