# LLM-Freeway Client (Optional)

A Streamlit-based UI for the LLM-Freeway service. Provides a graphical interface for chatting with 13+ LLM providers, managing automatic fallback, and monitoring provider status.

> **Running this client is optional.** You can interact with the service directly via:
> - **Swagger UI** at `http://localhost:4545/docs` — fully interactive with example payloads
> - **curl** or any HTTP client against the REST API
> - The **Python client** in `utils/api_client.py` — import it anywhere

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure service URL (default: http://localhost:4545)
echo "LLM_FREEWAY_URL=http://localhost:4545" > .env

# 3. Launch the UI
streamlit run app.py
```

Opens at **http://localhost:8501**

## Prerequisites

- **LLM-Freeway service** running on port 4545 (or your configured port)
- Python 3.10+
- An internet connection (the client itself needs no API keys — those live on the service)

## UI Tabs

### Dashboard
Shows service health, total providers, configured count, and model totals. Provider cards give a quick overview of which providers are ready to use.

### Providers
Select a provider from the dropdown to see all its models with their rate limits. Configured status is shown at the top.

### Chat
Full chat interface against a specific provider and model.

**Sidebar controls:**
- **Provider** — dropdown of configured providers
- **Model** — auto-populated model list for selected provider (or type manually)
- **System prompt** — text area for system instructions
- **Memory** — toggle session memory on/off
- **Session ID** — required when memory is enabled

**Features:**
- Message bubbles (user left, assistant right)
- Each assistant response shows an expandable **Details** section with provider, model, and token usage
- Conversation history persists within the tab during the session

### ContinueChat
Chat with automatic fallback. Tries providers/models in priority order until one succeeds.

**Controls (sidebar):**
- **Provider priority** — multi-select to order which providers to try first
- System prompt, memory, session ID (same as Chat tab)

**Behavior:**
1. Sends message to first provider in priority list
2. On rate limit / error → tries next provider
3. Shows which provider+model actually answered
4. If all fail, shows an error message

### Memory
Manage server-side memory sessions.

- Enter a session ID to clear its stored context
- Explains how the summarization system works

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_FREEWAY_URL` | `http://localhost:4545` | URL of the LLM-Freeway service |

Create a `.env` file:
```env
LLM_FREEWAY_URL=http://localhost:4545
```

## Using the Python Client Directly

The `utils/api_client.py` module can be imported and used independently:

```python
from utils.api_client import FreewayClient

client = FreewayClient("http://localhost:4545")

# Check health
print(client.health())

# List providers
for p in client.list_providers():
    print(f"{p['name']} - configured: {p['configured']}")

# List models for a provider
models = client.list_models("groq")
for m in models:
    print(f"  {m['id']}: {m.get('limits', {})}")

# Chat
resp = client.chat(
    provider="groq",
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello!"}],
    system_prompt="You are helpful.",
)
print(resp["choices"][0]["message"]["content"])

# Continue chat (auto-fallback)
resp = client.continue_chat(
    messages=[{"role": "user", "content": "Hello!"}],
    provider_priority=["openrouter", "groq", "gemini"],
)
print(f"Answered by: {resp['provider']}/{resp['model']}")

# Clear memory
client.clear_memory("my-session-id")
```

## API Client Reference

### `FreewayClient(base_url=None)`

| Method | Returns | Description |
|---|---|---|
| `health()` | `dict` | Service health status |
| `list_providers()` | `list[dict]` | All providers with config status |
| `list_models(provider)` | `list[dict]` | Models for a provider |
| `chat(provider, model, messages, ...)` | `dict` | Chat completion |
| `continue_chat(messages, ...)` | `dict` | Auto-fallback chat |
| `clear_memory(session_id)` | `dict` | Clear a memory session |

### `chat()` Parameters

| Param | Type | Required | Description |
|---|---|---|---|
| `provider` | str | yes | Provider name |
| `model` | str | yes | Model ID |
| `messages` | list[dict] | yes | `[{"role": "user", "content": "..."}]` |
| `system_prompt` | str | no | System instructions |
| `memory` | bool | no | Enable session memory |
| `session_id` | str | no | Session ID for memory |

### `continue_chat()` Parameters

| Param | Type | Required | Description |
|---|---|---|---|
| `messages` | list[dict] | yes | Message history |
| `system_prompt` | str | no | System instructions |
| `memory` | bool | no | Enable session memory |
| `session_id` | str | no | Session ID for memory |
| `provider_priority` | list[str] | no | Ordered provider names to try |

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| "Service unreachable" | LLM-Freeway not running | Start the service on port 4545 |
| No providers in dropdown | Service running but no keys configured | Check `.env` on the service side |
| "Rate limited" errors | Exceeded provider quota | Wait or switch providers via ContinueChat |
| Chat returns empty | Model doesn't support chat | Try a different model from the model list |
