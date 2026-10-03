# LLM-Freeway

Multi-provider LLM API gateway with automatic fallback. Routes chat requests across 13+ free LLM providers, automatically switching models or providers when rate limits are hit.

## Architecture

```
llm_freeway/                          # FastAPI backend (the service)
  ├── main.py                         # Entry point — run with fastapi dev or uvicorn
  ├── app/
  │   ├── config.py                   # Environment variable loader
  │   ├── schemas.py                  # Pydantic request/response models
  │   ├── providers/                  # 14 provider implementations
  │   ├── routers/                    # API route handlers
  │   └── services/                   # Business logic (memory, fallback)
  ├── .env.example                    # Template for API keys
  ├── generate_providers_xlsx.py      # Spreadsheet generator
  └── test_providers.py               # End-to-end provider tests

llm_freeway_client/                   # Streamlit UI (optional)
  ├── app.py                          # Streamlit frontend
  ├── utils/
  │   └── api_client.py               # Python client (can be used standalone)
  └── .env.example                    # Service URL config

root scripts/                         # Utility scripts
  ├── openrouter_chat.py              # Direct OpenRouter example
  └── pull_available_models.py        # Model discovery
```

## Quick Start

### Service (required)

```bash
cd llm_freeway
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
chcp 65001
$env:PYTHONIOENCODING="utf-8"
fastapi dev main.py --port 4545
# or: uvicorn main:app --host 0.0.0.0 --port 4545
```

The service starts at **http://localhost:4545** with interactive Swagger at **http://localhost:4545/docs**.

### Client (optional)

The Streamlit UI is optional — you can interact with the service directly via Swagger, curl, or any HTTP client.

```bash
cd llm_freeway_client
pip install -r requirements.txt
streamlit run app.py
```

Opens at **http://localhost:8501**.

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/providers` | GET | List all providers with config status |
| `/models/{provider}` | GET | List models for a provider |
| `/models` | GET | OpenAI-compatible coding-model catalog |
| `/chat` | POST | Chat with a specific provider/model |
| `/chat/completions` | POST | OpenAI-compatible chat completions |
| `/continuechat` | POST | Chat with auto-fallback across providers |
| `/v1/models` | GET | OpenAI-compatible coding-model catalog |
| `/v1/chat/completions` | POST | OpenAI-compatible chat completions |
| `/health` | GET | Service health check |
| `/stats` | GET | In-memory usage stats by provider/model |
| `/memory/{session_id}` | DELETE | Clear a memory session |

Full documentation with example payloads is available at **/docs** (Swagger UI) when the service is running.

## OpenCode Setup

`llm_freeway` now exposes OpenAI-compatible routes, so `opencode` can use it directly.

Use this provider config in `C:\Users\Sash\.config\opencode\config.json`:

```json
{
  "llm_freeway": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "LLM Freeway",
    "options": {
      "baseURL": "http://127.0.0.1:4545/v1"
    },
    "models": {
      "cf-gpt-oss-120b": { "name": "Cloudflare GPT OSS 120B" },
      "cf-gpt-oss-20b": { "name": "Cloudflare GPT OSS 20B" },
      "cf-deepseek-coder-6.7b-base": { "name": "Cloudflare DeepSeek Coder 6.7B Base" },
      "cf-deepseek-coder-6.7b-instruct": { "name": "Cloudflare DeepSeek Coder 6.7B Instruct" },
      "cf-qwen2.5-coder-32b": { "name": "Cloudflare Qwen2.5 Coder 32B" },
      "cf-qwen3-30b": { "name": "Cloudflare Qwen3 30B" },
      "cf-sqlcoder-7b": { "name": "Cloudflare SQLCoder 7B" },
      "gh-codestral-25-01": { "name": "GitHub Codestral 25.01" },
      "gh-gpt-oss-120b": { "name": "GitHub GPT OSS 120B" },
      "gh-gpt-oss-20b": { "name": "GitHub GPT OSS 20B" },
      "groq-gpt-oss-120b": { "name": "Groq GPT OSS 120B" },
      "groq-gpt-oss-20b": { "name": "Groq GPT OSS 20B" },
      "groq-qwen3-32b": { "name": "Groq Qwen3 32B" }
    }
  }
}
```

How to use it:

1. Start the service on `http://127.0.0.1:4545`.
2. Open `http://127.0.0.1:4545/docs` and confirm the server is up.
3. Add the config above to `opencode`.
4. Choose one of the compatibility model IDs from the config.

Notes:

- Use `http://127.0.0.1:4545/v1` as the base URL for `opencode`.
- Only the fixed coding-oriented compatibility model catalog is exposed on the OpenAI-compatible routes.
- `stream: true` is supported in OpenAI-style SSE format.
- Streaming is synthetic: the backend completes one normal request, then emits OpenAI-compatible stream chunks.

## New Endpoints

### `GET /v1/models` and `GET /models`

Returns the OpenAI-compatible compatibility catalog.

Example response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "gh-codestral-25-01",
      "object": "model",
      "created": 0,
      "owned_by": "github"
    }
  ]
}
```

### `POST /v1/chat/completions` and `POST /chat/completions`

OpenAI-compatible chat completions endpoint for `opencode` and other OpenAI-style clients.

Example request:

```json
{
  "model": "gh-codestral-25-01",
  "messages": [
    { "role": "system", "content": "You are a coding assistant." },
    { "role": "user", "content": "Write a Python hello world." }
  ],
  "stream": false
}
```

Example response:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1746890000,
  "model": "gh-codestral-25-01",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "print(\"Hello, world!\")"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {}
}
```

Behavior:

- Existing `/chat` and `/continuechat` routes are unchanged.
- Each compatibility model ID maps to one fixed backend `{provider, model}` pair.
- Structured provider message content is normalized to plain text for clients and Swagger.

### `GET /stats`

Returns in-memory request counts for the last minute and last 24 hours by provider and model.

Example response:

```json
{
  "providers": [
    {
      "provider": "github",
      "calls_this_minute": 2,
      "calls_today": 14,
      "models": [
        {
          "model": "Codestral-25.01",
          "calls_this_minute": 1,
          "calls_today": 9
        }
      ]
    }
  ],
  "models": [
    {
      "provider": "github",
      "model": "Codestral-25.01",
      "calls_this_minute": 1,
      "calls_today": 9
    }
  ]
}
```

The Streamlit dashboard shows these stats in the sidebar under `Usage Today`.

## Project Status

- **13 providers** — 12 configured (Kluster API key missing)
- **371+ models** across all providers
- Service and client actively running and functional
