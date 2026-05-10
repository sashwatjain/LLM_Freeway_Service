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
| `/chat` | POST | Chat with a specific provider/model |
| `/continuechat` | POST | Chat with auto-fallback across providers |
| `/health` | GET | Service health check |
| `/memory/{session_id}` | DELETE | Clear a memory session |

Full documentation with example payloads is available at **/docs** (Swagger UI) when the service is running.

## Project Status

- **13 providers** — 12 configured (Kluster API key missing)
- **371+ models** across all providers
- Service and client actively running and functional
