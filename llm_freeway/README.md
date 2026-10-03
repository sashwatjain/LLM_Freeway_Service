# LLM-Freeway

Multi-provider LLM API gateway with automatic fallback. Routes chat requests across 13+ free LLM providers, automatically switching models or providers when rate limits are hit.

> **No client needed** - interact directly via Swagger UI at `http://localhost:4545/docs` or use curl/any HTTP client.

## Features

- **13 providers** - OpenRouter, Groq, Google AI Studio (Gemini), Cohere, Cloudflare, Hyperbolic, SambaNova, Scaleway, Mistral, Cerebras, Kluster, GitHub Models, NVIDIA NIM
- **Automatic fallback** - `/continuechat` tries every model across every provider until one succeeds
- **OpenAI-compatible routes** - use `opencode` and other OpenAI-style clients via `/v1/models` and `/v1/chat/completions`
- **Rate-limit tracking** - in-memory counters per provider/model
- **Usage stats** - `/stats` returns today/minute counts by provider and model
- **Optional memory** - persists conversation context with automatic summarization to manage token usage
- **Stateless by default** - pass full message history each call; opt into memory per-request

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your keys

# Start the server
fastapi dev main.py --port 4545
# or: uvicorn main:app --host 0.0.0.0 --port 4545 --reload
```

Once running, open **http://localhost:4545/docs** for the interactive Swagger UI with pre-filled example payloads.

## API Reference

All endpoints are documented in Swagger at `/docs`. Main routes:

### `GET /providers`

Returns all providers with configuration status and model count.

```json
[
  {"name": "groq", "configured": true, "models_count": 12},
  {"name": "github", "configured": true, "models_count": 21}
]
```

### `GET /models/{provider}`

Returns available models and their rate limits for a provider.

```json
[
  {
    "id": "llama-3.3-70b-versatile",
    "name": "Llama 3.3 70B",
    "provider": "groq",
    "limits": {
      "requests_per_minute": null,
      "requests_per_day": 1000,
      "tokens_per_minute": 12000
    }
  }
]
```

### `GET /v1/models`

### `GET /models`

Returns the fixed OpenAI-compatible coding-model catalog used by `opencode` and other OpenAI-style clients.

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

### `POST /chat`

Chat with a specific provider and model.

```json
{
  "provider": "github",
  "model": "Ministral-3B",
  "messages": [{"role": "user", "content": "Hello!"}],
  "system_prompt": "You are a helpful assistant.",
  "memory": false,
  "session_id": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | string | yes | Provider name (for example `groq`, `openrouter`) |
| `model` | string | yes | Model ID from `/models/{provider}` |
| `messages` | array | yes | Array of `{role, content}` objects |
| `system_prompt` | string | no | System prompt prepended to messages |
| `memory` | bool | no | Enable session memory |
| `session_id` | string | no | Session ID for memory |

### `POST /v1/chat/completions`

### `POST /chat/completions`

OpenAI-compatible chat endpoint. Each compatibility `model` maps to one fixed backend provider/model pair.

```json
{
  "model": "gh-codestral-25-01",
  "messages": [
    {"role": "system", "content": "You are a coding assistant."},
    {"role": "user", "content": "Write a Python hello world."}
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

Notes:

- `stream: true` is supported with OpenAI-style SSE output
- streaming is synthetic: the provider call completes first, then the server emits stream chunks
- structured provider content is normalized to plain text for clients and Swagger UI

### `POST /continuechat`

Chat with automatic fallback. Tries every model across providers in priority order until one succeeds.

```json
{
  "messages": [{"role": "user", "content": "Hello!"}],
  "system_prompt": "You are a helpful assistant.",
  "memory": false,
  "session_id": null,
  "provider_priority": ["openrouter", "groq", "github"]
}
```

Fallback logic:

1. Try model[0] of provider[0]
2. On rate limit, try model[1] of the same provider
3. When all models are exhausted, move to the next provider
4. When all providers are exhausted, return `507`

### `GET /health`

```json
{"status": "ok", "providers": 13, "configured": 5}
```

### `GET /stats`

Returns in-memory request counts for the last minute and last 24 hours by provider and model.

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

### `DELETE /memory/{session_id}`

Clears stored memory for a session.

## OpenCode Integration

Use this config in `C:\Users\Sash\.config\opencode\config.json`:

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

1. Start `llm_freeway` on `http://127.0.0.1:4545`
2. Open `http://127.0.0.1:4545/docs`
3. Confirm `/v1/models` and `/v1/chat/completions` appear in Swagger
4. Add the config above to `opencode`
5. Pick one of the compatibility model IDs from the config

Compatibility model catalog:

- `cf-gpt-oss-120b`
- `cf-gpt-oss-20b`
- `cf-deepseek-coder-6.7b-base`
- `cf-deepseek-coder-6.7b-instruct`
- `cf-qwen2.5-coder-32b`
- `cf-qwen3-30b`
- `cf-sqlcoder-7b`
- `gh-codestral-25-01`
- `gh-gpt-oss-120b`
- `gh-gpt-oss-20b`
- `groq-gpt-oss-120b`
- `groq-gpt-oss-20b`
- `groq-qwen3-32b`

## Providers and Configuration

| Provider | Env Variable | Key Needed |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | Yes |
| Groq | `GROQ_API_KEY` | Yes |
| Google AI Studio | `GOOGLE_API_KEY` | Yes |
| Cohere | `COHERE_API_KEY` | Yes |
| Cloudflare | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_KEY` | Yes |
| Hyperbolic | `HYPERBOLIC_API_KEY` | Yes |
| SambaNova | `SAMBA_API_KEY` | Yes |
| Scaleway | `SCALEWAY_API_KEY` | Yes |
| Mistral | `MISTRAL_API_KEY` | Yes |
| Cerebras | `CEREBRAS_API_KEY` | Yes |
| Kluster | `KLUSTER_API_KEY` | Yes |
| GitHub Models | `GITHUB_TOKEN` | Yes |
| NVIDIA NIM | `NVIDIA_API_KEY` | Yes |

Providers without keys configured are listed as `"configured": false` and skipped during fallback.

## Memory System

When `memory: true` with a `session_id`, the service:

1. Stores conversation history server-side
2. When total character count exceeds the limit (default **1500**, configurable via `MEMORY_CHAR_LIMIT`), oldest messages are dropped and the recent tail is kept
3. Call `DELETE /memory/{session_id}` to clear

## Testing

```bash
# Test all providers and models
python test_providers.py
```

Generates a `provider_report_<timestamp>.txt` with per-provider model-level test results.

## Development

```bash
# Run with auto-reload
uvicorn main:app --host 0.0.0.0 --port 4545 --reload

# Generate providers spreadsheet
python generate_providers_xlsx.py
```
