# Hacker News Daily Digest (AI Agent)

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Node](https://img.shields.io/badge/Node-22-green.svg)
![NVIDIA NIM](https://img.shields.io/badge/AI-NVIDIA%20NIM-76B900)
![Pages](https://img.shields.io/badge/GitHub%20Pages-Actions-222)

> 运行在 GitHub Actions 上的 AI 日报：抓取 Hacker News + GitHub Trending，生成中文结构化摘要，**完整汇总**后部署到 **GitHub Pages**。

站点（部署成功后）：  
https://xiaoqianran.github.io/actions-HN001-HN-daily-agent/

## ✨ 特性

- **自动抓取**：定时获取 HN 热门与 GitHub Trending
- **智能去广**：Jina Reader 提取正文
- **结构化摘要**：核心 / 要点 / 亮点 / 适合（OpenAI 兼容接口，默认 NVIDIA NIM）
- **完整汇总**：HN + Trending 同一份日报，不拆分、不推送微信
- **GitHub Pages**：由 Actions 构建并部署静态站，支持按日归档
- **零服务器**：完全跑在 GitHub Actions

## 🚀 快速开始

### 1. Secrets / Variables

**Secrets**

```
OPENAI_API_KEY = nvapi-xxxxxxxx
```

**Variables**（可选）

```
OPENAI_BASE_URL = https://integrate.api.nvidia.com/v1
MODEL_NAME      = stepfun-ai/step-3.5-flash
HN_TOP_COUNT    = 15
GH_TOP_COUNT    = 20
```

> 仓库 Variable 名不能以 `GITHUB_` 开头，故 Trending 数量用 `GH_TOP_COUNT`。

### 2. 启用 Pages（Actions）

仓库 `Settings` → `Pages` → **Source** 选择 **GitHub Actions**。  
本仓库 workflow 已使用 `actions/deploy-pages`，首次 run 成功后站点可用。

### 3. 运行

Actions → **Daily HN Digest** → **Run workflow**  
或等待每天 UTC 22:00（北京时间 06:00）定时任务。

## 📂 产物结构

```
data/YYYY-MM-DD.json     # 当日原始汇总数据（入库/归档）
public/
  index.html             # 最新日报
  styles.css
  archive/YYYY-MM-DD.html
```

流程：抓取 → 摘要 → **写入 data + 重建 public** → 提交 → **Deploy Pages**。

## 💻 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 OPENAI_API_KEY 等
python news_agent.py   # 生成 data/ 与 public/
```

本地预览：用浏览器打开 `public/index.html`。

## 🛠 技术栈

| 技术 | 说明 |
|------|------|
| Python 3.12 | Agent 与站点生成 |
| Node 22 | Actions 工具链 |
| OpenAI SDK | 兼容 NIM 等接口 |
| GitHub Pages | `configure-pages` + `upload-pages-artifact` + `deploy-pages` |

## ❓ 说明

- **不再使用 PushPlus**：曾因内容超过 2 万字被拒；现改为 Pages 承载完整日报。
- 自定义摘要提示词：Variable `SUMMARY_PROMPT_TEMPLATE`，必须含 `{title}` 与 `{content}`。模板见 `SUMMARY_PROMPT_TEMPLATES.md`。
