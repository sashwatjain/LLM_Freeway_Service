from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider, AuthError


class GeminiProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "gemini"

    @property
    def configured(self) -> bool:
        return bool(settings.google_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        api_key = settings.google_api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        contents = []
        for m in messages:
            role = "model" if m.role == "assistant" else m.role
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {"contents": contents}
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 429:
            data = resp.json()
            pm = data.get("error", {}).get("details", [{}])[0].get("policyViolation", {})
            raise LimitExceeded(
                f"Gemini rate limited: {data.get('error', {}).get('message', resp.text)}",
                violations=pm,
            )
        if resp.status_code == 403:
            raise AuthError(f"Gemini auth failed: {resp.text}")
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        choices = []
        for c in candidates:
            text = ""
            for part in c.get("content", {}).get("parts", []):
                text += part.get("text", "")
            choices.append({
                "index": c.get("index", 0),
                "message": {
                    "role": "assistant",
                    "content": text,
                },
                "finish_reason": c.get("finishReason", "stop"),
            })

        usage = data.get("usageMetadata")
        return ChatResponse(
            choices=choices,
            usage=usage,
            provider=self.name,
            model=model,
        )

    async def list_models(self) -> list[ModelInfo]:
        known = [
            ("gemini-2.5-flash", "Gemini 2.5 Flash", ModelLimits(requests_per_minute=5, requests_per_day=20, tokens_per_minute=250000)),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite", ModelLimits(requests_per_minute=10, requests_per_day=20, tokens_per_minute=250000)),
            ("gemini-3-flash-preview", "Gemini 3 Flash", ModelLimits(requests_per_minute=5, requests_per_day=20, tokens_per_minute=250000)),
            ("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash-Lite", ModelLimits(requests_per_minute=15, requests_per_day=500, tokens_per_minute=250000)),
            ("gemma-3-27b-it", "Gemma 3 27B", ModelLimits(requests_per_minute=30, requests_per_day=14400, tokens_per_minute=15000)),
            ("gemma-3-12b-it", "Gemma 3 12B", ModelLimits(requests_per_minute=30, requests_per_day=14400, tokens_per_minute=15000)),
            ("gemma-3-4b-it", "Gemma 3 4B", ModelLimits(requests_per_minute=30, requests_per_day=14400, tokens_per_minute=15000)),
        ]
        return [
            ModelInfo(id=mid, name=name, provider=self.name, limits=lim)
            for mid, name, lim in known
        ]


class LimitExceeded(Exception):
    def __init__(self, message: str, violations: Optional[dict] = None):
        super().__init__(message)
        self.violations = violations or {}
