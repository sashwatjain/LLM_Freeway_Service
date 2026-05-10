from typing import Optional

from app.providers.registry import registry
from app.providers.base import BaseProvider, RateLimitError, AuthError
from app.schemas import ChatRequest, ChatResponse, Message
from app.services.limit_tracker import limit_tracker
from app.services.memory_service import memory_service


async def chat(
    provider_name: str,
    model: str,
    messages: list[Message],
    system_prompt: Optional[str] = None,
    memory: bool = False,
    session_id: Optional[str] = None,
) -> ChatResponse:
    provider = registry.get(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    if not provider.configured:
        raise ValueError(f"Provider '{provider_name}' is not configured (missing API key)")

    allowed, reason = limit_tracker.check(provider_name, model)
    if not allowed:
        raise RateLimitError(f"{provider_name}/{model}: {reason}")

    if memory and session_id:
        ctx = memory_service.get_or_create(session_id)
        ctx.add_messages(messages)
        context_messages = ctx.get_context()
    else:
        context_messages = messages

    try:
        response = await provider.chat(
            messages=context_messages,
            model=model,
            system_prompt=system_prompt,
        )
    except Exception:
        raise

    limit_tracker.increment(provider_name, model)

    if memory and session_id:
        ctx = memory_service.get_or_create(session_id)
        assistant_content = ""
        for choice in response.choices:
            if choice.get("message", {}).get("role") == "assistant":
                assistant_content = choice["message"].get("content", "")
        if assistant_content:
            ctx.add_messages([Message(role="assistant", content=assistant_content)])

    return response
