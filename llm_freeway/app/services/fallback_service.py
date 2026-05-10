import asyncio
from typing import Optional

from app.providers.registry import registry
from app.providers.base import RateLimitError, AuthError
from app.schemas import ChatResponse, Message
from app.services.chat_service import chat as chat_single


DEFAULT_PROVIDER_ORDER = [
    "openrouter",
    "groq",
    "gemini",
    "cohere",
    "cloudflare",
    "github",
    "nvidia",
    "hyperbolic",
    "sambanova",
    "scaleway",
    "mistral",
    "cerebras",
    "kluster",
]


async def continue_chat(
    messages: list[Message],
    system_prompt: Optional[str] = None,
    memory: bool = False,
    session_id: Optional[str] = None,
    provider_priority: Optional[list[str]] = None,
) -> ChatResponse:
    order = provider_priority or DEFAULT_PROVIDER_ORDER
    errors: list[dict] = []

    for provider_name in order:
        provider = registry.get(provider_name)
        if not provider or not provider.configured:
            continue

        try:
            models = await provider.list_models()
        except Exception:
            continue

        for model_info in models:
            try:
                return await chat_single(
                    provider_name=provider_name,
                    model=model_info.id,
                    messages=messages,
                    system_prompt=system_prompt,
                    memory=memory,
                    session_id=session_id,
                )
            except RateLimitError as e:
                errors.append({
                    "provider": provider_name,
                    "model": model_info.id,
                    "error": str(e),
                    "type": "rate_limit",
                })
                continue
            except AuthError as e:
                errors.append({
                    "provider": provider_name,
                    "model": model_info.id,
                    "error": str(e),
                    "type": "auth",
                })
                continue
            except Exception as e:
                errors.append({
                    "provider": provider_name,
                    "model": model_info.id,
                    "error": str(e),
                    "type": "unknown",
                })
                continue

    raise AllProvidersExhausted(
        "All providers/models exhausted",
        errors=errors,
    )


class AllProvidersExhausted(Exception):
    def __init__(self, message: str, errors: list[dict]):
        super().__init__(message)
        self.errors = errors
