from dataclasses import dataclass
import json
from time import time
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.providers.base import AuthError, ProviderError, RateLimitError
from app.providers.registry import registry
from app.schemas import Message
from app.services.chat_service import chat as chat_service
from app.services.response_utils import content_to_text


@dataclass(frozen=True)
class CompatModel:
    compat_id: str
    name: str
    provider: str
    backend_model: str
    owned_by: str


COMPAT_MODELS: tuple[CompatModel, ...] = (
    CompatModel(
        compat_id="cf-gpt-oss-120b",
        name="Cloudflare GPT OSS 120B",
        provider="cloudflare",
        backend_model="@cf/openai/gpt-oss-120b",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-gpt-oss-20b",
        name="Cloudflare GPT OSS 20B",
        provider="cloudflare",
        backend_model="@cf/openai/gpt-oss-20b",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-deepseek-coder-6.7b-base",
        name="Cloudflare DeepSeek Coder 6.7B Base",
        provider="cloudflare",
        backend_model="@hf/thebloke/deepseek-coder-6.7b-base-awq",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-deepseek-coder-6.7b-instruct",
        name="Cloudflare DeepSeek Coder 6.7B Instruct",
        provider="cloudflare",
        backend_model="@hf/thebloke/deepseek-coder-6.7b-instruct-awq",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-qwen2.5-coder-32b",
        name="Cloudflare Qwen2.5 Coder 32B",
        provider="cloudflare",
        backend_model="@cf/qwen/qwen2.5-coder-32b-instruct",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-qwen3-30b",
        name="Cloudflare Qwen3 30B",
        provider="cloudflare",
        backend_model="@cf/qwen/qwen3-30b-a3b-fp8",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="cf-sqlcoder-7b",
        name="Cloudflare SQLCoder 7B",
        provider="cloudflare",
        backend_model="@cf/defog/sqlcoder-7b-2",
        owned_by="cloudflare",
    ),
    CompatModel(
        compat_id="gh-codestral-25-01",
        name="GitHub Codestral 25.01",
        provider="github",
        backend_model="Codestral-25.01",
        owned_by="github",
    ),
    CompatModel(
        compat_id="gh-gpt-oss-120b",
        name="GitHub GPT OSS 120B",
        provider="github",
        backend_model="gpt-oss-120b",
        owned_by="github",
    ),
    CompatModel(
        compat_id="gh-gpt-oss-20b",
        name="GitHub GPT OSS 20B",
        provider="github",
        backend_model="gpt-oss-20b",
        owned_by="github",
    ),
    CompatModel(
        compat_id="groq-gpt-oss-120b",
        name="Groq GPT OSS 120B",
        provider="groq",
        backend_model="openai/gpt-oss-120b",
        owned_by="groq",
    ),
    CompatModel(
        compat_id="groq-gpt-oss-20b",
        name="Groq GPT OSS 20B",
        provider="groq",
        backend_model="openai/gpt-oss-20b",
        owned_by="groq",
    ),
    CompatModel(
        compat_id="groq-qwen3-32b",
        name="Groq Qwen3 32B",
        provider="groq",
        backend_model="qwen/qwen3-32b",
        owned_by="groq",
    ),
)

COMPAT_MODEL_MAP = {model.compat_id: model for model in COMPAT_MODELS}

router = APIRouter()


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[Message]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


def _model_payload(model: CompatModel) -> dict[str, Any]:
    return {
        "id": model.compat_id,
        "object": "model",
        "created": 0,
        "owned_by": model.owned_by,
    }


def _normalize_choices(choices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for idx, choice in enumerate(choices):
        original_message = choice.get("message") or {
            "role": "assistant",
            "content": choice.get("text", ""),
        }
        message = {
            "role": original_message.get("role", "assistant"),
            "content": content_to_text(original_message.get("content", "")),
        }
        if original_message.get("tool_calls"):
            message["tool_calls"] = original_message["tool_calls"]
        normalized.append(
            {
                "index": choice.get("index", idx),
                "message": message,
                "finish_reason": choice.get("finish_reason", "stop"),
            }
        )
    return normalized


def _resolve_provider_for_request(
    compat_model: CompatModel, extra_payload: dict[str, Any]
) -> tuple[str, str]:
    provider_name = compat_model.provider
    backend_model = compat_model.backend_model

    has_tools = any(
        key in extra_payload for key in ("tools", "tool_choice", "parallel_tool_calls")
    )
    is_cloudflare_gpt_oss = (
        compat_model.provider == "cloudflare"
        and compat_model.backend_model in ("@cf/openai/gpt-oss-120b", "@cf/openai/gpt-oss-20b")
    )

    # Cloudflare gpt-oss is currently unreliable for tool-style chat-completions
    # requests in this compat bridge. Prefer GitHub, then Groq, for those cases.
    if has_tools and is_cloudflare_gpt_oss:
        if "120b" in compat_model.backend_model:
            fallback_candidates = [
                ("github", "gpt-oss-120b"),
                ("groq", "openai/gpt-oss-120b"),
            ]
        else:
            fallback_candidates = [
                ("github", "gpt-oss-20b"),
                ("groq", "openai/gpt-oss-20b"),
            ]

        for candidate_provider, candidate_model in fallback_candidates:
            provider = registry.get(candidate_provider)
            if provider and provider.configured:
                print(
                    "openai_compat rerouting tool request:",
                    {
                        "requested_model": compat_model.compat_id,
                        "from_provider": compat_model.provider,
                        "to_provider": candidate_provider,
                        "to_model": candidate_model,
                    },
                )
                return candidate_provider, candidate_model

    return provider_name, backend_model


async def _run_chat(req: OpenAIChatRequest) -> tuple[CompatModel, dict[str, Any]]:
    print("openai_compat request payload:", req.model_dump())
    compat_model = COMPAT_MODEL_MAP.get(req.model)
    if not compat_model:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown compatibility model: {req.model}",
        )

    extra_payload = req.model_dump(exclude_none=True)
    extra_payload.pop("model", None)
    extra_payload.pop("messages", None)
    extra_payload.pop("stream", None)
    extra_payload.pop("stream_options", None)
    provider_name, backend_model = _resolve_provider_for_request(compat_model, extra_payload)

    try:
        response = await chat_service(
            provider_name=provider_name,
            model=backend_model,
            messages=req.messages,
            extra_payload=extra_payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    payload = {
        "id": f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion",
        "created": int(time()),
        "model": compat_model.compat_id,
        "choices": _normalize_choices(response.choices),
        "usage": response.usage or {},
    }
    print("openai_compat response payload:", payload)
    return compat_model, payload


def _sse_event(data: dict[str, Any] | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"data: {payload}\n\n"


def _streaming_content(payload: dict[str, Any]):
    content = ""
    finish_reason = "stop"
    tool_calls = []
    if payload["choices"]:
        message = payload["choices"][0].get("message", {})
        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", []) or []
        finish_reason = payload["choices"][0].get("finish_reason", "stop")

    yield _sse_event(
        {
            "id": payload["id"],
            "object": "chat.completion.chunk",
            "created": payload["created"],
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None,
                }
            ],
        }
    )

    if content:
        yield _sse_event(
            {
                "id": payload["id"],
                "object": "chat.completion.chunk",
                "created": payload["created"],
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content},
                        "finish_reason": None,
                    }
                ],
            }
        )

    for index, tool_call in enumerate(tool_calls):
        yield _sse_event(
            {
                "id": payload["id"],
                "object": "chat.completion.chunk",
                "created": payload["created"],
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": index,
                                    "id": tool_call.get("id"),
                                    "type": tool_call.get("type", "function"),
                                    "function": {
                                        "name": tool_call.get("function", {}).get("name"),
                                        "arguments": tool_call.get("function", {}).get("arguments", ""),
                                    },
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            }
        )

    yield _sse_event(
        {
            "id": payload["id"],
            "object": "chat.completion.chunk",
            "created": payload["created"],
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": payload.get("usage", {}),
        }
    )
    yield _sse_event("[DONE]")


@router.get("/v1/models")
@router.get("/models")
async def list_openai_models():
    return {
        "object": "list",
        "data": [_model_payload(model) for model in COMPAT_MODELS],
    }


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def chat_completions(req: OpenAIChatRequest):
    _, payload = await _run_chat(req)
    if req.stream:
        return StreamingResponse(
            _streaming_content(payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    return payload
