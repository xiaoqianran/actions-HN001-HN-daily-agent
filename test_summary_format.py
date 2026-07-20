"""摘要清洗与排版单测"""
from summarizer import format_summary_for_push, normalize_summary


def test_normalize_structured():
    raw = """
## 一句话核心
**核心**：这是一个测试项目
要点: 第一点；第二点；第三点；第四点
亮点 很有价值
适合 后端
"""
    out = normalize_summary(raw)
    assert "核心 " in out
    assert "要点 " in out
    assert "亮点 " in out
    assert "适合 " in out
    # 要点最多 3 条
    points_line = [l for l in out.splitlines() if l.startswith("要点 ")][0]
    assert points_line.count("；") == 2


def test_normalize_messy_markdown():
    raw = """```markdown
# Summary
- **something** cool about systems
1. foo
2. bar
```"""
    out = normalize_summary(raw)
    assert out.startswith("核心 ")
    assert "```" not in out
    assert "#" not in out.split("核心 ", 1)[1][:5]


def test_never_use_reasoning_as_is():
    # 模拟超长推理文本：应被截断进核心，而不是原样倾倒
    long = "Thinking about the problem " * 40
    out = normalize_summary(long)
    core = [l for l in out.splitlines() if l.startswith("核心 ")][0]
    assert len(core) < 100


def test_format_for_push_has_bullets():
    text = "核心 测试核心\n要点 A；B；C\n亮点 X\n适合 全员"
    md = format_summary_for_push(text)
    assert "**核心**" in md
    assert "- A" in md
    assert "- B" in md


if __name__ == "__main__":
    test_normalize_structured()
    test_normalize_messy_markdown()
    test_never_use_reasoning_as_is()
    test_format_for_push_has_bullets()
    print("all ok")
