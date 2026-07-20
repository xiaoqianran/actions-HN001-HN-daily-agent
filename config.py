"""
配置模块
负责环境变量加载和网络配置初始化
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# 模块导入时自动加载环境变量
load_dotenv()

# 禁用代理的常量配置
_NO_PROXY: Dict[str, Optional[str]] = {"http": None, "https": None}

DEFAULT_HN_TOP_COUNT = 15
DEFAULT_GITHUB_TOP_COUNT = 20
# 兼容旧引用
DEFAULT_TOP_COUNT = DEFAULT_HN_TOP_COUNT

# OpenAI 兼容接口默认值（NVIDIA NIM）
DEFAULT_OPENAI_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL_NAME = "stepfun-ai/step-3.5-flash"

# 严格结构化提示词：固定标签，避免自由 Markdown 导致微信排版错乱
DEFAULT_SUMMARY_PROMPT_TEMPLATE = """
你是技术日报编辑。请根据文章生成中文摘要，供微信推送阅读。

标题：{title}
正文：
{content}

【输出要求——必须严格遵守】
1. 只输出下面 4 行结构，不要前言、不要后记、不要代码块、不要标题符号（#）、不要表情符号。
2. 每行以固定标签开头，标签后紧跟一个空格，再写正文。
3. 「核心」一行，不超过 40 个汉字。
4. 「要点」恰好 3 条，用中文分号「；」分隔，每条不超过 25 个汉字。
5. 「亮点」一行，一句最有价值的信息，不超过 30 个汉字；没有则写「无」。
6. 「适合」一行，标注读者画像（如：后端/前端/AI/产品/安全），不超过 15 个汉字。
7. 禁止输出思考过程、英文长句、Markdown 列表（- * 1.）、加粗符号 **。

【标准输出格式示例】
核心 这是一款用 Rust 重写的 JS 运行时，显著降低冷启动延迟。
要点 用 Rust 重写核心循环；兼容大部分 Node API；基准测试延迟下降约 40%
亮点 已有生产环境案例，可渐进迁移。
适合 后端与基础设施工程师

现在按上述格式输出，不要输出示例本身。
""".strip()


def get_openai_api_key() -> str:
    """获取 OpenAI 兼容接口 API Key（优先 OPENAI_API_KEY，兼容 DEEPSEEK_API_KEY）"""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("环境变量 OPENAI_API_KEY（或 DEEPSEEK_API_KEY）未设置")
    return key


def get_openai_base_url() -> str:
    """获取 OpenAI 兼容接口 Base URL"""
    url = os.getenv("OPENAI_BASE_URL")
    if url and url.strip():
        return url.strip().rstrip("/")
    return DEFAULT_OPENAI_BASE_URL


def get_model_name() -> str:
    """获取 LLM 模型名称"""
    model = os.getenv("MODEL_NAME")
    if model and model.strip():
        return model.strip()
    return DEFAULT_MODEL_NAME


def get_deepseek_key() -> str:
    """兼容旧接口：等价于 get_openai_api_key()"""
    return get_openai_api_key()


def get_pushplus_token() -> str:
    """获取 PushPlus Token"""
    token = os.getenv("PUSHPLUS_TOKEN")
    if not token:
        raise ValueError("环境变量 PUSHPLUS_TOKEN 未设置")
    return token


def get_no_proxy() -> Dict[str, Optional[str]]:
    """获取 NO_PROXY 配置字典，用于禁用代理"""
    return _NO_PROXY


def _get_positive_int_env(var_name: str, default: int) -> int:
    """读取正整数环境变量，非法值时回退默认值"""
    raw_value = os.getenv(var_name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        parsed = int(raw_value)
        if parsed <= 0:
            raise ValueError
        return parsed
    except ValueError:
        print(f"[配置警告] {var_name}={raw_value!r} 非法，已回退默认值 {default}")
        return default


def get_hn_top_count() -> int:
    """获取 HN 抓取数量"""
    return _get_positive_int_env("HN_TOP_COUNT", DEFAULT_HN_TOP_COUNT)


def get_github_top_count() -> int:
    """获取 GitHub Trending 抓取数量"""
    return _get_positive_int_env("GITHUB_TOP_COUNT", DEFAULT_GITHUB_TOP_COUNT)


def get_summary_prompt_template() -> str:
    """获取摘要提示词模板"""
    prompt = os.getenv("SUMMARY_PROMPT_TEMPLATE")
    if prompt and prompt.strip():
        return prompt.strip()
    return DEFAULT_SUMMARY_PROMPT_TEMPLATE
