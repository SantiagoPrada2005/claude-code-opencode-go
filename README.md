# Claude Code + OpenCode Go

<div align="center">

**$10/month → Claude Code with 14 models. No Anthropic subscription needed.**

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## What is this?

Claude Code normally requires an [Anthropic subscription](https://claude.com/pricing) ($20–$200/month) and only works with Claude models. This project lets you use it with **[OpenCode Go](https://opencode.ai)** — a $10/month service that gives you access to **14 models** including:

- **DeepSeek V4 Pro / Flash** — coding, reasoning, fast iteration
- **Kimi K2.6 / K2.5** — long context (128K+ tokens)
- **GLM 5.1 / 5** — bilingual coding (EN/ZH)
- **Qwen 3.6 Plus / 3.5 Plus** — general purpose
- **MiMo V2 Pro / Omni / V2.5** — multimodal
- **MiniMax M2.7 / M2.5** — creative tasks

It works by running a **tiny local proxy** that translates Claude Code's Anthropic API calls into OpenAI-compatible calls that OpenCode Go understands. Zero latency penalty, zero config changes to your workflow.

## How it works

```
┌──────────────┐       Anthropic API        ┌─────────────────┐       OpenAI API        ┌──────────────┐
│              │  POST /v1/messages          │                 │  POST /v1/chat/       │              │
│  Claude Code │ ────────────────────────→   │  proxy-server   │ ────────────────────→  │  OpenCode Go │
│              │                             │  (localhost:    │                        │              │
│  $0 (free)   │  ← Anthropic SSE response   │    port 11434)  │  ← OpenAI response     │  $10/month   │
└──────────────┘                             └─────────────────┘                        └──────────────┘
```

The proxy handles:
- **Message format** — Anthropic content blocks ↔ OpenAI messages
- **Tool use** — `name` + `input_schema` ↔ `function.name` + `parameters`
- **Thinking/reasoning** — `thinking` blocks ↔ `reasoning_content`
- **Streaming** — OpenAI SSE ↔ Anthropic SSE events
- **Multi-turn** — tool calls → tool results → final answer

## Quick Start

### Docker (recommended — works on Linux, macOS, Windows)

```bash
git clone https://github.com/SantiagoPrada2005/claude-code-opencode-go.git
cd claude-code-opencode-go
cp .env.example .env        # edit .env with your API key
docker compose up -d --build
```

### Direct Python

```bash
git clone https://github.com/SantiagoPrada2005/claude-code-opencode-go.git
cd claude-code-opencode-go
./setup.sh      # install deps, set API key, print config
./start.sh      # launch proxy in background
```

Then update your `~/.claude/settings.json` with the block printed by `setup.sh` (or shown below), and open `claude`.

That's it.

## Detailed Setup

### 1. Prerequisites

- **[Docker](https://docs.docker.com/get-docker/)** (recommended) **or** Python 3.9+
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** installed
- **[OpenCode Go API key](https://opencode.ai/auth)** ($10/month, $5 first month)

### 2. Configure

#### Option A: Docker (multiplatform — Linux, macOS, Windows)

```bash
git clone https://github.com/SantiagoPrada2005/claude-code-opencode-go.git ~/claude-code-opencode-go
cd ~/claude-code-opencode-go
cp .env.example .env
# Edit .env with your API key:
#   OPENCODE_API_KEY=sk-your-actual-key
docker compose up -d --build
```

The proxy will auto-restart on crash and on system boot (`restart: unless-stopped`).

#### Option B: Direct Python

```bash
git clone https://github.com/SantiagoPrada2005/claude-code-opencode-go.git ~/claude-code-opencode-go
cd ~/claude-code-opencode-go
./setup.sh
```

`setup.sh` will:
- Check Python is available
- Install `fastapi`, `httpx`, `uvicorn` via pip
- Prompt for your OpenCode Go API key → saves to `.env`
- Print the JSON block to add to your `settings.json`

Alternatively, manual setup:
```bash
pip3 install -r requirements.txt
cp .env.example .env   # then edit .env with your key
```

### 3. Add to Claude Code settings

Merge this into `~/.claude/settings.json` (create the file if it doesn't exist):

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "any-key",
    "ANTHROPIC_BASE_URL": "http://localhost:11434",
    "ANTHROPIC_MODEL": "deepseek-v4-pro",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "true"
  }
}
```

### 4. Start

```bash
# Docker:
docker compose up -d

# Direct Python:
./start.sh

# Then:
claude       # Start coding
```

## Daily Commands

| Command | What it does |
|---------|-------------|
| `docker compose up -d` | Start proxy via Docker |
| `docker compose down` | Stop Docker proxy |
| `docker compose logs -f` | Watch live logs |
| `./start.sh` | Start proxy (auto-detects Docker or direct) |
| `./stop.sh` | Stop proxy |
| `curl http://localhost:11434/health` | Check if proxy is running |

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_API_KEY` | *(required)* | Your OpenCode Go API key |
| `PROXY_HOST` | `127.0.0.1` | Listen address (use `0.0.0.0` to expose on network) |
| `PROXY_PORT` | `11434` | Listen port (11434 = Ollama standard for local LLMs) |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/go/v1/chat/completions` | Upstream API endpoint |
| `AVAILABLE_MODELS` | `deepseek-v4-pro,deepseek-v4-flash` | Models exposed via `/v1/models` (CSV) |

Set these in `.env` or as environment variables.

## Available Models

OpenCode Go supports 14 models. Configure exposed models via `AVAILABLE_MODELS` in `.env`:

```
deepseek-v4-pro  deepseek-v4-flash  kimi-k2.6       kimi-k2.5
glm-5.1          glm-5              qwen3.6-plus    qwen3.5-plus
mimo-v2-pro      mimo-v2-omni       mimo-v2.5-pro   mimo-v2.5
minimax-m2.7     minimax-m2.5
```

Example to expose all models:
```bash
AVAILABLE_MODELS=deepseek-v4-pro,deepseek-v4-flash,kimi-k2.6,kimi-k2.5,glm-5.1,glm-5,qwen3.6-plus,qwen3.5-plus,mimo-v2-pro,mimo-v2-omni,mimo-v2.5-pro,mimo-v2.5,minimax-m2.7,minimax-m2.5
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/messages` | POST | Anthropic Messages API (chat, tools, streaming) |
| `/v1/messages/count_tokens` | POST | Token counting (approximate) |
| `/v1/models` | GET | Model discovery |
| `/health` | GET | Health check |

## Switching Back to DeepSeek Direct

Replace your `settings.json` env block:

```json
"ANTHROPIC_API_KEY": "<your-deepseek-key>",
"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"
```

Remove `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`.

## Why not just use DeepSeek directly?

DeepSeek's endpoint works but with limited model variety. OpenCode Go gives you 14 models from 7 providers for $10/month. Switch between them based on your task — fast iteration with Flash, heavy reasoning with Pro, long context with Kimi.

## Known Limitations

- **Token counting is approximate** — word-based estimation (×2 factor). Good enough for context management.
- **DeepSeek V4 Pro thinking mode** — can exhaust `max_tokens` on reasoning if set too low. Use Flash for fast tasks.
- **No auth on proxy** — no API key validation. Only expose on localhost (`127.0.0.1`).
- **Minimal dependencies** — only `fastapi`, `httpx`, `uvicorn`. No database, no cloud services.

## Files

```
claude-code-opencode-go/
├── proxy-server.py      # The proxy — Anthropic ↔ OpenAI translation
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose orchestration
├── requirements.txt      # Python dependencies (pinned)
├── setup.sh              # Interactive setup (install deps, configure .env)
├── start.sh              # Start proxy (Docker or direct)
├── stop.sh               # Stop the proxy
├── .env.example          # Template for your API key + config
├── .dockerignore         # Docker build exclusions
├── litellm-config.yaml   # Backup config (LiteLLM explored, not used)
├── .gitignore
└── README.md
```

## License

MIT — use it, fork it, ship it.
