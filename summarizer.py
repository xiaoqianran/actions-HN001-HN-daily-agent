"""
总结模块
负责调用 DeepSeek API 生成文章摘要
"""
import httpx
from openai import OpenAI


class Summarizer:
    """文章总结器，使用 DeepSeek API"""

    def __init__(self, api_key):
        """
        初始化总结器

        Args:
            api_key: DeepSeek API Key
        """
        self.api_key = api_key
        self.http_client = httpx.Client(trust_env=False)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            http_client=self.http_client
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭 HTTP 客户端，释放资源"""
        if self.http_client:
            self.http_client.close()

    def summarize(self, title, content):
        """
        为单篇文章生成摘要

        Args:
            title: 文章标题
            content: 文章内容

        Returns:
            str: 摘要内容，失败返回错误信息
        """
        print(f"[思考] 正在总结: {title} ...")

        prompt = f"""
        请为 Hacker News 的热门文章撰写微型简报。
        标题: {title}
        内容: {content[:6000]}

        请输出 Markdown 格式，包含：
        1. **一句话核心**：它是什么？
        2. **关键点**：3个以内的技术要点或观点。
        (保持简洁，不要废话，不要使用任何表情符号)
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"总结失败: {e}"
