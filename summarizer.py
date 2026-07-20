"""
总结模块
负责调用 OpenAI 兼容接口生成文章摘要（支持 NVIDIA NIM / DeepSeek 等）
"""
import re
import httpx
from openai import OpenAI

# 结构化摘要标签（与默认提示词对齐）
_LABELS = ("核心", "要点", "亮点", "适合")
_LABEL_PATTERN = re.compile(
    r"^(?:[-*•]\s*)?(?:\*\*)?(核心|要点|亮点|适合)(?:\*\*)?[：:\s]\s*(.+)$"
)


def normalize_summary(text: str) -> str:
    """
    清洗模型输出，统一为微信友好的 4 行结构。

    目标格式：
      核心 ...
      要点 ...
      亮点 ...
      适合 ...
    """
    if not text or not str(text).strip():
        return "核心 摘要为空，请查看原文。\n要点 无；无；无\n亮点 无\n适合 通用"

    raw = str(text).strip()
    # 去掉常见代码围栏与 BOM
    raw = raw.replace("\ufeff", "")
    raw = re.sub(r"^```(?:markdown|md|text)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    # 去掉 Markdown 标题前缀
    raw = re.sub(r"(?m)^#{1,6}\s*", "", raw)
    # 去掉加粗标记
    raw = raw.replace("**", "")

    parsed = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _LABEL_PATTERN.match(line)
        if m:
            label, value = m.group(1), m.group(2).strip()
            if label not in parsed and value:
                parsed[label] = value
            continue
        # 兼容「核心：xxx」单独成行后下一行是内容
        for label in _LABELS:
            if line in (label, f"{label}:", f"{label}："):
                parsed.setdefault(label, "")
                break

    # 若完全解析失败，把全文压成「核心」一行，避免把混乱 Markdown 直接推送
    if "核心" not in parsed or not parsed.get("核心"):
        flat = re.sub(r"\s+", " ", raw).strip()
        # 截断过长输出
        if len(flat) > 120:
            flat = flat[:117] + "..."
        parsed["核心"] = flat or "摘要解析失败，请查看原文。"

    if "要点" not in parsed or not parsed.get("要点"):
        parsed["要点"] = "详见原文；信息有限；建议点击链接"
    else:
        # 统一要点分隔符为中文分号
        points = parsed["要点"]
        points = re.sub(r"[；;]\s*", "；", points)
        points = re.sub(r"(?:^|[；])\s*[-*•\d.、]+\s*", "；", points)
        points = points.strip("；; \t")
        parts = [p.strip() for p in points.split("；") if p.strip()]
        if len(parts) > 3:
            parts = parts[:3]
        while len(parts) < 3:
            parts.append("无")
        parsed["要点"] = "；".join(parts)

    parsed.setdefault("亮点", "无")
    parsed.setdefault("适合", "通用读者")

    # 单行长度保护，避免微信气泡撑爆
    for key, limit in (("核心", 80), ("要点", 120), ("亮点", 60), ("适合", 30)):
        val = re.sub(r"\s+", " ", parsed[key]).strip()
        if len(val) > limit:
            val = val[: limit - 1] + "…"
        parsed[key] = val

    return "\n".join(f"{label} {parsed[label]}" for label in _LABELS)


def format_summary_for_push(summary: str) -> str:
    """将结构化摘要转为推送用的轻量 Markdown（避免 # 标题嵌套）。"""
    text = normalize_summary(summary)
    lines = []
    for line in text.splitlines():
        m = _LABEL_PATTERN.match(line.strip())
        if not m:
            continue
        label, value = m.group(1), m.group(2).strip()
        if label == "要点":
            items = [p.strip() for p in re.split(r"[；;]", value) if p.strip() and p.strip() != "无"]
            if items:
                lines.append(f"**{label}**")
                for item in items:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{label}** {value}")
        else:
            lines.append(f"**{label}** {value}")
    return "\n".join(lines) if lines else text


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
        self.http_client = httpx.Client(trust_env=False, timeout=120.0)
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
            str: 清洗后的结构化摘要；失败时返回可读错误信息
        """
        print(f"[思考] 正在总结: {title} ...")
        print(f"[LLM] model={self.model_name} base_url={self.base_url}")

        # 控制正文长度，减少噪声与超时
        article_content = content[:5000]
        prompt = self.prompt_template.format(title=title, content=article_content)

        try:
            # reasoning 模型会占用 completion tokens，需给足 max_tokens
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你只输出中文结构化摘要，格式固定为四行："
                            "核心 ... / 要点 ... / 亮点 ... / 适合 ..."
                            "禁止输出思考过程、Markdown 标题与代码块。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                max_tokens=2048,
                temperature=0.3,
            )
            message = response.choices[0].message
            text = message.content
            # 注意：绝不能把 reasoning / reasoning_content 当作摘要推送
            if not text or not str(text).strip():
                return normalize_summary("核心 模型返回空内容，请查看原文。\n要点 无；无；无\n亮点 无\n适合 通用")
            return normalize_summary(text)
        except Exception as e:
            return normalize_summary(
                f"核心 总结失败：{e}\n要点 无；无；无\n亮点 无\n适合 通用"
            )
