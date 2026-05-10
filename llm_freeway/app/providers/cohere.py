from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class CohereProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "cohere"

    @property
    def configured(self) -> bool:
        return bool(settings.cohere_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        api_key = settings.cohere_api_key
        url = "https://api.cohere.com/v1/chat"

        chat_history = []
        first_user_msg = ""
        for i, m in enumerate(messages):
            if i == 0 and m.role == "user":
                first_user_msg = m.content
            elif m.role == "user":
                chat_history.append({"role": "USER", "message": m.content})
            elif m.role == "assistant":
                chat_history.append({"role": "CHATBOT", "message": m.content})

        payload = {
            "model": model,
            "message": first_user_msg or (messages[0].content if messages else ""),
        }
        if chat_history:
            payload["chat_history"] = chat_history
        if system_prompt:
            payload["preamble_override"] = system_prompt

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
                json=payload,
            )

        if resp.status_code == 429:
            raise RateLimit(f"Cohere rate limited: {resp.text}")
        resp.raise_for_status()
        data = resp.json()

        text = data.get("text", "")
        choices = [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": text,
            },
        }]
        return ChatResponse(
            choices=choices,
            usage=data.get("usage"),
            provider=self.name,
            model=model,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.cohere.com/v1/models",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {settings.cohere_api_key}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            if m.get("is_deprecated"):
                continue
            endpoints = set(m.get("endpoints") or []) | set(m.get("default_endpoints") or [])
            if "chat" not in endpoints:
                continue
            models.append(
                ModelInfo(
                    id=m["name"],
                    name=m["name"],
                    provider=self.name,
                    limits=ModelLimits(requests_per_minute=20, requests_per_day=1000),
                )
            )
        return sorted(models, key=lambda x: x.name)

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "command-a-03-2025", "command-a-reasoning-08-2025",
            "command-r-08-2024", "command-r-plus-08-2024",
            "command-r7b-12-2024", "c4ai-aya-expanse-32b",
        ]
        return [
            ModelInfo(id=m, name=m, provider=self.name, limits=ModelLimits(requests_per_minute=20, requests_per_day=1000))
            for m in known
        ]


class RateLimit(Exception):
    pass
