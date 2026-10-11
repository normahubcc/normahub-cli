<p align="center">
  <a href="https://normahub.cc?utm_source=github&utm_medium=repo&utm_campaign=normahub_cli&utm_content=logo">
    <img src="https://normahub.cc/images/logo_main.png" alt="NormaHub Gateway" width="120" height="auto" onerror="this.src='https://raw.githubusercontent.com/normahubcc/normahub-cli/main/normahub_cli/ui/icon.png'"/>
  </a>
</p>

<h1 align="center">normahub-cli</h1>

<p align="center">
  <strong>Universal Local AI Gateway, Pareto Router & Local Model Arena</strong><br>
  <em>Zero-config, zero-VPN access to 30+ frontier models (GPT-6, Claude Sonnet 3.5/5, DeepSeek v4.1, SeeDance 2.5 Video) for developers in Russia & CIS.</em>
</p>

<p align="center">
  <a href="https://github.com/normahubcc/normahub-cli/actions"><img src="https://img.shields.io/badge/CI-Passing-brightgreen?style=flat-square&logo=github-actions" alt="CI Status"></a>
  <a href="https://pypi.org/project/normahub-cli/"><img src="https://img.shields.io/badge/pypi-v1.0.0-blue?style=flat-square&logo=pypi" alt="PyPI Version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-3776AB?style=flat-square&logo=python" alt="Python Support"></a>
  <a href="#dependencies"><img src="https://img.shields.io/badge/dependencies-zero_stdlib-success?style=flat-square" alt="Zero Dependencies"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License MIT"></a>
  <a href="https://normahub.cc?utm_source=github&utm_medium=readme&utm_campaign=normahub_cli"><img src="https://img.shields.io/badge/payment-RUB%20%2F%20SBP%20%2F%20Cards-orange?style=flat-square" alt="Russian Payment Methods"></a>
</p>

---

## ⚡ Why normahub-cli?

Building AI-powered applications in Russia and CIS often involves hurdles: foreign card requirements for OpenAI/Anthropic, high latency, unstable VPN tunnels, and fragmented toolchains.

`normahub-cli` runs as a high-performance, local bridge daemon (`127.0.0.1:8080`) that connects your IDEs, code agents, and local terminals directly to **30+ top-tier AI models** via the [NormaHub API](https://normahub.cc?utm_source=github&utm_medium=readme&utm_campaign=normahub_cli) with RUB billing, zero foreign credit card requirements, and sub-100ms connection latency.

```mermaid
flowchart LR
    subgraph Client ["Your Development Environment"]
        Cursor["Cursor IDE"]
        Cline["Cline / VSCode"]
        OpenWebUI["Open WebUI / Ollama Client"]
        Terminal["Terminal / Curl / Python"]
    end

    subgraph Daemon ["normahub-cli (127.0.0.1:8080)"]
        OpenAIServer["OpenAI API (/v1/*)"]
        OllamaServer["Ollama API (/api/*)"]
        Cache["SQLite Local Cache"]
        Router["Pareto Cost Router"]
        WebUI["Local Web UI Arena & FinOps"]
    end

    subgraph Cloud ["NormaHub Cloud Infrastructure"]
        NormaGateway["NormaHub API Gateway (RUB Billing)"]
        Models["Claude Sonnet / GPT-6 / DeepSeek / SeeDance"]
    end

    Cursor -->|OpenAI Wire| OpenAIServer
    Cline -->|OpenAI Wire| OpenAIServer
    OpenWebUI -->|Ollama Wire| OllamaServer
    Terminal -->|HTTP / SSE| OpenAIServer

    OpenAIServer --> Cache
    OllamaServer --> Cache
    Cache -->|Cache Miss| Router
    Router --> NormaGateway
    NormaGateway --> Models
    Cache -.->|Cache Hit (0 ms, 0 RUB)| OpenAIServer
    WebUI -.->|Inspect Metrics| Cache
```

### 🌟 Key Features

- **🚀 100% Zero External Dependencies**: Built strictly on the Python Standard Library (`http.server`, `urllib`, `sqlite3`, `asyncio`). Runs out of the box on macOS, Linux, and Windows with zero package conflicts.
- **🔄 Dual Protocol Wire Emulation**:
  - **OpenAI Compatible**: Drop-in proxy at `http://127.0.0.1:8080/v1` for Cursor, Cline, Continue, Aider, and the official `openai` SDK.
  - **Ollama Compatible**: Emulates `/api/chat`, `/api/generate`, `/api/tags` so Open WebUI, Ollama CLI, and local tools connect seamlessly.
- **🧠 Pareto Intelligent Cost Router (`normahub/auto`)**: Analyzes code complexity, prompt length, and task difficulty in real time. Routes simple tasks to ultra-fast, budget models (DeepSeek v4.1 Flash) and complex multi-step reasoning to frontier reasoning flagships (Claude 3.5/5 Sonnet, GPT-6), cutting monthly AI spend by up to 60%.
- **💾 Local SQLite Cache**: Hashes prompts with SHA-256 and caches idempotent completions. Identical queries return with 0ms latency and 0 RUB cost, with cumulative savings tracked automatically.
- **🛠️ 1-Click IDE Auto-Patcher**: Instantly configures settings for **Cursor**, **Cline**, **OpenCode**, and **Claude Desktop** with a single command (`normahub setup cursor`).
- **🎨 Embedded Local Web UI Arena**: Dark-mode dashboard at `http://127.0.0.1:8080/ui` featuring interactive Model Arena (side-by-side prompt testing), SeeDance Video Studio, and live FinOps metrics (saved tokens, cached queries, saved rubles).

---

## 📦 Quick Start

### 1. Installation

Install via pip:

```bash
pip install normahub-cli
```

Or clone and run locally without installing:

```bash
git clone https://github.com/normahubcc/normahub-cli.git
cd normahub-cli
python3 -m normahub_cli.cli start
```

### 2. Configure Your API Key

Get your API key at [normahub.cc](https://normahub.cc?utm_source=github&utm_medium=readme&utm_campaign=normahub_cli) (use promo code **`GH-CLI`** for complimentary starting balance), then export it:

```bash
export NORMAHUB_API_KEY="your-normahub-api-key"
```

Or pass it interactively during setup:

```bash
normahub setup
```

### 3. Launch Gateway

```bash
normahub start
```

```text
╭─────────────────────────────────────────────────────────────╮
│  🚀 NormaHub Local AI Gateway v1.0.0                         │
│                                                             │
│  • OpenAI Base URL:   http://127.0.0.1:8080/v1              │
│  • Ollama Base URL:   http://127.0.0.1:8080/api             │
│  • Local Web UI:      http://127.0.0.1:8080/ui              │
│  • SQLite Cache:      ~/.normahub/cache.db                  │
│                                                             │
│  💡 Press Ctrl+C to stop. Serving 30 models without VPN.    │
╰─────────────────────────────────────────────────────────────╯
```

---

## 💻 CLI Commands

| Command | Description |
| :--- | :--- |
| `normahub start [--host 127.0.0.1] [--port 8080]` | Start local gateway server with caching and UI |
| `normahub setup [cursor \| cline \| opencode \| claude]` | 1-Click configure IDE settings to point to local gateway |
| `normahub models` | Display catalog of 30 models with pricing and context limits |
| `normahub stats` | Show local FinOps metrics (cached queries, saved tokens, saved rubles) |

---

## 🔌 Connecting to Your Tools

### 1. Cursor IDE (1-Click Auto-Setup)

Automatically patch `~/.config/Cursor/User/settings.json`:

```bash
normahub setup cursor
```

Or configure manually in **Cursor Settings > Models > OpenAI API**:
- **OpenAI API Key**: `normahub` (or any string)
- **Base URL**: `http://127.0.0.1:8080/v1`
- **Model Override**: `normahub/auto` or `claude-3-5-sonnet-20241022`

---

### 2. Cline / Roo-Code

```bash
normahub setup cline
```

Or select **OpenAI Compatible** provider:
- **Base URL**: `http://127.0.0.1:8080/v1`
- **API Key**: `normahub`
- **Model ID**: `normahub/auto`

---

### 3. Official Python OpenAI SDK

```python
from openai import OpenAI

# Point directly to your local normahub-cli daemon
client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="normahub-local"
)

response = client.chat.completions.create(
    model="normahub/auto",  # Or "deepseek-chat", "gpt-4o", "claude-3-5-sonnet"
    messages=[
        {"role": "user", "content": "Write an async worker in Python with exponential backoff"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)
```

---

### 4. Ollama Client & Open WebUI

Because `normahub-cli` emulates the Ollama protocol, you can configure Open WebUI or any Ollama client:

- **Ollama API URL**: `http://127.0.0.1:8080`

Test via curl:

```bash
curl http://127.0.0.1:8080/api/chat -d '{
  "model": "deepseek-chat",
  "messages": [{"role": "user", "content": "Hello from Ollama client!"}]
}'
```

---

## 🧠 Pareto Cost Router (`normahub/auto`)

When using the model `normahub/auto`, the daemon evaluates incoming messages using a heuristic engine:

```text
Incoming Prompt
      │
      ├──> Short greeting / general lookup (< 60 words, no code)
      │     └──> DeepSeek v4.1 Flash (~0.14 RUB / 1K tokens)  [Saves 90%]
      │
      ├──> Complex math / multi-step logic ("solve step-by-step")
      │     └──> GPT-6 Sol / GPT-5.5 (~1.20 RUB / 1K tokens)
      │
      └──> High-complexity code (Python/TS code blocks, refactors)
            └──> Claude Sonnet 3.5 / 5.0 (~0.95 RUB / 1K tokens)
```

You get the highest output quality where it matters, without wasting flagship credits on simple lookups.

---

## 🎨 Local Web UI Arena & FinOps Dashboard

Open `http://127.0.0.1:8080/ui` in your browser to access:

1. **Model Arena**: Send side-by-side prompts to test model quality and latency across DeepSeek, Claude, and GPT-6.
2. **SeeDance 2.5 Video Studio**: Input video prompts, configure aspect ratios (16:9, 9:16), duration, and inspect generated videos.
3. **FinOps Analytics**: Real-time counter of total requests, cache hit ratio, tokens saved, and rubles preserved.

---

## 📊 Catalog of Supported Models (Excerpt)

| Category | Model ID | Context | Description |
| :--- | :--- | :--- | :--- |
| **Smart Routing** | `normahub/auto` | Auto | Pareto cost-quality auto-router |
| **High Speed** | `deepseek-chat` / `deepseek-v4.1` | 64K | Ultra-low-cost, high intelligence code & logic |
| **High Speed** | `z-ai-glm-5.3-flash` | 128K | Large context, rapid summarization |
| **Code & Reasoning** | `claude-3-5-sonnet-20241022` | 200K | Industry benchmark for architecture & code |
| **Reasoning Flagship**| `gpt-6-sol` / `gpt-6.1-sol` | 128K | Complex reasoning, math & data synthesis |
| **Creative & Search** | `xai-grok-4.7` | 128K | Unfiltered generation, current knowledge |
| **Video Generation** | `bytedance-seedance-2.5` | — | Text-to-Video & Image-to-Video generation |

Run `normahub models` for the complete real-time catalog.

---

## 🐳 Docker Deployment

Run `normahub-cli` in a Docker container on any server:

```bash
docker run -d \
  -p 8080:8080 \
  -e NORMAHUB_API_KEY="your-normahub-api-key" \
  -v ~/.normahub:/root/.normahub \
  --name normahub-gateway \
  normahubcc/normahub-cli:latest
```

---

## 🎁 Special Bonus for Developers

Register at [normahub.cc](https://normahub.cc?utm_source=github&utm_medium=readme&utm_campaign=normahub_cli) and use promo code **`GH-CLI`** in the billing section to receive test balance for prompt generation and video synthesis.

- Direct connection inside Russia (no VPN required)
- Corporate invoicing for legal entities (RUB, invoice, act)
- Instant payment via SBP, Russian bank cards, and Mir

---

## 📄 License

MIT © [NormaHub Team](https://normahub.cc?utm_source=github&utm_medium=readme&utm_campaign=normahub_cli)
