"""
总结模块
负责调用 OpenAI 兼容接口生成文章摘要（支持 NVIDIA NIM / DeepSeek 等）
"""
import httpx
from openai import OpenAI


class Summarizer:
    """文章总结器，使用 OpenAI 兼容 API"""

    def __init__(self, api_key, prompt_template, base_url=None, model_name=None):
        """
        初始化总结器

        Args:
            api_key: API Key
            prompt_template: 摘要提示词模板，必须包含 {title} 和 {content} 占位符
            base_url: OpenAI 兼容接口地址，默认 NVIDIA NIM
            model_name: 模型名称，默认 stepfun-ai/step-3.5-flash
        """
        from config import DEFAULT_MODEL_NAME, DEFAULT_OPENAI_BASE_URL

        self.api_key = api_key
        self.prompt_template = prompt_template
        self.base_url = (base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        self.model_name = model_name or DEFAULT_MODEL_NAME
        self.http_client = httpx.Client(trust_env=False)
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            http_client=self.http_client,
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
        print(f"[LLM] model={self.model_name} base_url={self.base_url}")

        article_content = content[:6000]
        prompt = self.prompt_template.format(title=title, content=article_content)

        try:
            # step 等 reasoning 模型会消耗 completion tokens 做思考，max_tokens 过小可能导致 content 为空
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content
            # 兜底：部分兼容接口可能把正文放在 model_extra
            extra = getattr(response.choices[0].message, "model_extra", None) or {}
            for key in ("reasoning_content", "reasoning"):
                if extra.get(key):
                    return str(extra[key])
            return "总结失败: 模型返回空内容"
        except Exception as e:
            return f"总结失败: {e}"
