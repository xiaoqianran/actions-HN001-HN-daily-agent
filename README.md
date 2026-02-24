# Hacker News Daily Digest (AI Agent)

![Stars](https://img.shields.io/github/stars/GeYugong/HN-daily-agent?style=social)
![Forks](https://img.shields.io/github/forks/GeYugong/HN-daily-agent?style=social)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-critical)

> 一个运行在 GitHub Actions 上的 AI 智能体，每天早上 6:00 自动抓取 Hacker News 热门文章和 GitHub Trending 项目，生成中文简报并推送至你的微信。

无需服务器，完全免费，开箱即用。

## ✨ 特性

- **自动抓取**：每天定时获取 Hacker News Top 榜单和 GitHub Trending 热门项目
- **智能去广**：使用 Jina Reader 提取纯净网页内容
- **深度总结**：调用 DeepSeek API 生成高质量中文技术简报
- **微信推送**：通过 PushPlus 推送 Markdown 格式日报到你的微信
- **零成本**：完全基于 GitHub Actions 免费运行，无需服务器
- **模块化架构**：代码结构清晰，易于维护和扩展

## 📸 推送效果示例

每日报告包含以下内容：

```
📅 HN 每日简报 | 2025-01-08

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 Hacker News Top 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [文章标题]
   📝 AI摘要：文章的核心内容总结...
   🔗 原文链接

2. [另一篇文章]
   ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 GitHub Trending
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [repo-name] - stars数
   📝 项目简介...
```


## 🚀 快速开始

你不需要写任何代码，只需要 Fork 本项目并配置 API Key。

### 1️⃣ Fork 本仓库

点击右上角的 **Fork** 按钮，将项目复刻到你的 GitHub 账号下。

### 2️⃣ 获取必要的密钥

| 服务 | 用途 | 获取链接 |
|------|------|----------|
| **DeepSeek** | AI 文章摘要 | [platform.deepseek.com](https://platform.deepseek.com/) |
| **PushPlus** | 微信消息推送 | [pushplus.plus](http://www.pushplus.plus/) |

> 💡 **提示**：DeepSeek 需要充值少量金额（约 ¥1 即可测试），PushPlus 有免费额度（每天 100 条）。

### 3️⃣ 配置 GitHub Secrets

在你的 Fork 仓库页面：

1. 进入 `Settings` → `Secrets and variables` → `Actions`
2. 点击 `New repository secret`，添加以下两个变量：

```
DEEPSEEK_API_KEY = sk-xxxxxxxxxxxxxxxx
PUSHPLUS_TOKEN   = xxxxxxxxxxxxxxxxxx
```

### 4️⃣ 启用 GitHub Actions

1. 点击仓库上方的 `Actions` 标签
2. 如果看到警告，点击 **"I understand my workflows, go ahead and enable them"**
3. 点击左侧 `Daily HN Digest` → `Run workflow` 手动测试一次

🎉 完成！以后每天 **北京时间 06:00**，它会自动运行并推送简报到你的微信。

## 💻 本地开发测试

如果需要在本地运行或调试：

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（创建 .env 文件）
DEEPSEEK_API_KEY=your_key_here
PUSHPLUS_TOKEN=your_token_here

# 3. 运行主程序
python news_agent.py

# 4. 运行测试
python test_hn_fetcher.py
```

> ⚠️ **注意**：本地运行时会自动跳过系统代理设置。如果遇到网络问题，请检查网络连接。

## 🛠 技术栈

| 技术 | 版本/说明 | 用途 |
|------|----------|------|
| **Python** | 3.9+ | 主要编程语言 |
| **OpenAI SDK** | 最新版 | DeepSeek API 兼容客户端 |
| **DeepSeek** | - | AI 文章摘要生成 |
| **Jina Reader** | - | 网页内容提取 |
| **httpx** | - | 异步 HTTP 客户端 |
| **GitHub Actions** | - | 自动化调度 |

## 📁 项目结构

```
.
├── .github/
│   └── workflows/
│       └── daily_run.yml    # GitHub Actions 工作流配置
├── config.py                # 环境配置和凭证管理
├── hn_fetcher.py            # Hacker News 抓取模块
├── github_trending.py       # GitHub Trending 抓取模块
├── summarizer.py            # DeepSeek 文章摘要模块
├── notifier.py              # PushPlus 微信推送模块
├── news_agent.py            # 主程序入口（编排所有模块）
├── test_hn_fetcher.py       # HN 抓取模块单元测试
├── requirements.txt         # Python 依赖列表
├── .env.example             # 环境变量示例
├── CLAUDE.md                # Claude Code 项目说明
└── README.md                # 本文件
```

## ❓ 常见问题

### Q: 收不到微信推送怎么办？

**A:** 请按以下步骤排查：

1. 检查 GitHub Actions 是否运行成功（查看 Actions 标签页）
2. 确认 `PUSHPLUS_TOKEN` 配置正确
3. 登录 [PushPlus](http://www.pushplus.plus/) 确认发送记录
4. 确认已关注 PushPlus 公众号

### Q: 可以修改推送时间吗？

**A:** 可以。编辑 `.github/workflows/daily_run.yml`，修改 `cron` 字段：

```yaml
schedule:
  - cron: '0 22 * * *'  # UTC 22:00 = 北京 06:00
```

### Q: 可以抓取更多文章吗？

**A:** 可以。修改 `news_agent.py` 中的参数：

```python
hn_stories = hn_fetcher.get_top_stories(n=5)  # 改为你想要的数量
gh_repos = gh_fetcher.get_trending_repos(n=5)  # 改为你想要的数量
```

⚠️ **注意**：增加数量会消耗更多 DeepSeek API 额度，也可能导致推送超时。

### Q: DeepSeek API 额度不够怎么办？

**A:** 可以替换为其他兼容 OpenAI 格式的 API：

1. 修改 `summarizer.py` 中的 `base_url`
2. 更新 GitHub Secrets 中的 `DEEPSEEK_API_KEY`

### Q: GitHub Actions 失败了怎么办？

**A:** 点击失败的 Run 查看 Logs，常见问题：

- **网络超时**：GitHub Actions 网络不稳定，重试即可
- **API 错误**：检查 API Key 是否正确、余额是否充足
- **依赖安装失败**：检查 `requirements.txt` 是否正常

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果你有好的想法或发现了 Bug，请：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

## 🌟 Star History

如果这个项目对你有帮助，请给一个 Star ⭐️

---

<div align="center">

Made with ❤️ by [GeYugong](https://github.com/GeYugong)

</div>

