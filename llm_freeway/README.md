# LLM-Freeway

Multi-provider LLM API gateway with automatic fallback. Routes chat requests across 13+ free LLM providers, automatically switching models or providers when rate limits are hit.

> **No client needed** — interact directly via Swagger UI at `http://localhost:4545/docs` or use curl/any HTTP client.

## Features

- **13 providers** — OpenRouter, Groq, Google AI Studio (Gemini), Cohere, Cloudflare, Hyperbolic, SambaNova, Scaleway, Mistral, Cerebras, Kluster, GitHub Models, NVIDIA NIM
- **Automatic fallback** — `/continuechat` tries every model across every provider until one succeeds
- **Rate-limit tracking** — in-memory counters per provider/model
- **Optional memory** — persists conversation context with automatic summarization to manage token usage
- **Stateless by default** — pass full message history each call; opt into memory per-request

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

All endpoints are fully documented in Swagger at `/docs`. Here's a summary:

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
  {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "provider": "groq", "limits": {"requests_per_minute": null, "requests_per_day": 1000, "tokens_per_minute": 12000}}
]
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
| `provider` | string | yes | Provider name (e.g. `groq`, `openrouter`) |
| `model` | string | yes | Model ID from `/models/{provider}` |
| `messages` | array | yes | Array of `{role, content}` objects |
| `system_prompt` | string | no | System prompt prepended to messages |
| `memory` | bool | no | Enable session memory (default: `false`) |
| `session_id` | string | no | Session ID for memory (required if `memory: true`) |

### `POST /continuechat`

Chat with automatic fallback. Tries every model across providers in priority order until one succeeds.

```json
{
  "messages": [{"role": "user", "content": "Hello!"}],
  "system_prompt": "You are a helpful assistant.",
  "memory": false,
  "session_id": null,
  "provider_priority": ["openrouter", "groq", "gemini"]
}
```

**Fallback logic:**

1. Try model[0] of provider[0]
2. On rate limit → try model[1] of same provider
3. All models exhausted → move to next provider
4. All providers exhausted → returns `507` with error details

### `GET /health`

```json
{"status": "ok", "providers": 13, "configured": 5}
```

### `DELETE /memory/{session_id}`

Clears stored memory for a session.

## Providers & Configuration

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

Providers without keys configured are listed as `"configured": false` and skipped during fallback — the server won't crash.

## Memory System

When `memory: true` with a `session_id`, the service:

1. Stores conversation history server-side
2. When total character count exceeds the limit (default **1500**, configurable via `MEMORY_CHAR_LIMIT`), oldest messages are dropped — keeps the tail of the conversation
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
