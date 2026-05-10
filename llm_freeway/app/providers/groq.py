from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "groq"

    @property
    def configured(self) -> bool:
        return bool(settings.groq_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        limits_map = {
            "llama-3.3-70b-versatile": ModelLimits(requests_per_day=1000, tokens_per_minute=12000),
            "llama-3.1-8b-instant": ModelLimits(requests_per_day=14400, tokens_per_minute=6000),
            "llama-guard-3-8b": ModelLimits(requests_per_day=14400, tokens_per_minute=6000),
            "mixtral-8x7b-32768": ModelLimits(requests_per_day=14400, tokens_per_minute=6000),
            "gemma2-9b-it": ModelLimits(requests_per_day=14400, tokens_per_minute=6000),
            "whisper-large-v3": ModelLimits(requests_per_day=2000),
            "whisper-large-v3-turbo": ModelLimits(requests_per_day=2000),
        }

        models = []
        for m in data.get("data", []):
            mid = m["id"]
            models.append(
                ModelInfo(
                    id=mid,
                    name=mid,
                    provider=self.name,
                    limits=limits_map.get(mid, ModelLimits(requests_per_day=1000)),
                )
            )
        return sorted(models, key=lambda x: x.name)

    def _known_models(self) -> list[ModelInfo]:
        known = [
            ("llama-3.3-70b-versatile", "Llama 3.3 70B", ModelLimits(requests_per_day=1000, tokens_per_minute=12000)),
            ("llama-3.1-8b-instant", "Llama 3.1 8B", ModelLimits(requests_per_day=14400, tokens_per_minute=6000)),
            ("mixtral-8x7b-32768", "Mixtral 8x7B", ModelLimits(requests_per_day=14400, tokens_per_minute=6000)),
            ("gemma2-9b-it", "Gemma 2 9B", ModelLimits(requests_per_day=14400, tokens_per_minute=6000)),
        ]
        return [
            ModelInfo(id=mid, name=name, provider=self.name, limits=lim)
            for mid, name, lim in known
        ]
