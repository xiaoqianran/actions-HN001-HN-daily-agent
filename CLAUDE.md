# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an AI agent that runs on GitHub Actions to deliver a daily tech digest to WeChat. The workflow:
1. Fetches top 5 stories from Hacker News API
2. Fetches top 5 trending repositories from GitHub
3. Extracts clean content using Jina Reader
4. Summarizes each article using an OpenAI-compatible LLM (default: NVIDIA NIM)
5. Pushes a Markdown-formatted digest (HN articles + GitHub Trending) to WeChat via PushPlus

## Commands

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables in .env file:
# OPENAI_API_KEY=nvapi-xxx
# OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
# MODEL_NAME=stepfun-ai/step-3.5-flash
# PUSHPLUS_TOKEN=your_token_here

# Run the agent
python news_agent.py
```

### GitHub Actions
- Workflow: `.github/workflows/daily_run.yml`
- Schedule: Daily at UTC 22:00 (Beijing 06:00)
- Manual trigger: Go to Actions tab → Daily HN Digest → Run workflow
- Required secrets: `OPENAI_API_KEY`, `PUSHPLUS_TOKEN`
- Optional variables: `OPENAI_BASE_URL`, `MODEL_NAME`

## Architecture

**Modular design**: The codebase is organized into separate, focused modules:

- `config.py` - Environment configuration and credential management
- `hn_fetcher.py` - Hacker News API client and content fetching (HNFetcher class)
- `github_trending.py` - GitHub Trending repository scraper (GitHubTrendingFetcher class)
- `summarizer.py` - OpenAI-compatible article summarization (Summarizer class)
- `notifier.py` - WeChat push notification via PushPlus (WeChatNotifier class)
- `news_agent.py` - Main orchestrator that coordinates all modules

**Network configuration**:
- Uses `httpx.Client(trust_env=False)` to bypass system proxy settings
- `NO_PROXY` dict is passed to all `requests.get()` calls to prevent proxy interference
- OpenAI-compatible client uses the custom http_client

**Execution flow** (`news_agent.py` main function):
1. Load environment variables (OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, PUSHPLUS_TOKEN)
2. Initialize module instances (HNFetcher, GitHubTrendingFetcher, Summarizer, WeChatNotifier)
3. Fetch top 5 HN stories via `hn_fetcher.get_top_stories(n=5)`
4. Fetch top 5 GitHub Trending repos via `gh_fetcher.get_trending_repos(n=5)`
5. For each HN story: fetch content → summarize via OpenAI-compatible LLM → append to digest
6. Push combined digest (HN articles + GitHub Trending) to WeChat

## Key Implementation Details

- The agent skips HN posts that don't have external URLs (e.g., "Ask HN" text-only posts)
- Content shorter than 100 characters is considered a fetch failure and falls back to a generic message
- A 1-second sleep between articles prevents rate limiting
- All HTTP requests use explicit `timeout` parameters
- Default LLM endpoint is NVIDIA NIM (`https://integrate.api.nvidia.com/v1`, model `stepfun-ai/step-3.5-flash`); override via env vars
- GitHub Trending fetcher scrapes the trending page to extract repository names, URLs, and descriptions
