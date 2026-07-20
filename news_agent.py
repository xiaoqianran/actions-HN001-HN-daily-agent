"""
Hacker News 日报 Agent
主入口：抓取、总结，并汇总生成 GitHub Pages 静态站点
"""
import time
from config import (
    DEFAULT_SUMMARY_PROMPT_TEMPLATE,
    get_github_top_count,
    get_hn_top_count,
    get_model_name,
    get_openai_api_key,
    get_openai_base_url,
    get_summary_prompt_template,
)
from hn_fetcher import HNFetcher
from github_trending import GitHubTrendingFetcher
from summarizer import Summarizer
from site_builder import SiteBuilder


def main():
    """主流程"""
    print("[系统] Agent 开始工作...")

    try:
        # 1. 初始化配置（OpenAI 兼容接口：NVIDIA NIM 等）
        api_key = get_openai_api_key()
        base_url = get_openai_base_url()
        model_name = get_model_name()
        hn_top_count = get_hn_top_count()
        github_top_count = get_github_top_count()
        prompt_template = get_summary_prompt_template()

        print(f"[配置] OPENAI_BASE_URL={base_url}")
        print(f"[配置] MODEL_NAME={model_name}")
        print(f"[配置] HN_TOP_COUNT={hn_top_count} GH_TOP_COUNT={github_top_count}")

        if "{title}" not in prompt_template or "{content}" not in prompt_template:
            print("[配置警告] SUMMARY_PROMPT_TEMPLATE 必须包含 {title} 和 {content}，已回退默认提示词。")
            prompt_template = DEFAULT_SUMMARY_PROMPT_TEMPLATE

        # 2. 创建各模块实例
        hn_fetcher = HNFetcher()
        gh_fetcher = GitHubTrendingFetcher()
        site = SiteBuilder()

        with Summarizer(
            api_key,
            prompt_template,
            base_url=base_url,
            model_name=model_name,
        ) as summarizer:
            # 3. 获取 HN 文章列表
            stories = hn_fetcher.get_top_stories(n=hn_top_count)

            # 4. 获取 GitHub Trending 项目，并将简介译为简体中文
            gh_repos = gh_fetcher.get_trending_repos(n=github_top_count)
            if gh_repos:
                summarizer.translate_repo_descriptions(gh_repos)

            digest_data = []

            # 5. 处理每篇 HN 文章（摘要）
            for story in stories:
                content = hn_fetcher.fetch_content(story["url"])

                if len(content) < 100:
                    summary = "核心 无法抓取正文，请直接点击链接查看。\n要点 无；无；无\n亮点 无\n适合 通用"
                else:
                    summary = summarizer.summarize(story["title"], content)

                digest_data.append(
                    {
                        "title": story["title"],
                        "url": story["url"],
                        "summary": summary,
                    }
                )
                time.sleep(1)

            # 6. 汇总写入站点（不推送 PushPlus，不拆分消息）
            if digest_data or gh_repos:
                page = site.publish(digest_data, gh_repos)
                print(f"[系统] 日报已汇总发布到站点: {page}")
            else:
                print("[系统] 今天没有抓取到有效新闻。")
                # 仍重建站点，保留历史归档
                site.rebuild()

    except ValueError as e:
        print(f"[配置错误] {e}")
        print("[提示] 请检查环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / MODEL_NAME")
        return
    except Exception as e:
        print(f"[错误] Agent 运行失败: {e}")
        raise


if __name__ == "__main__":
    main()
