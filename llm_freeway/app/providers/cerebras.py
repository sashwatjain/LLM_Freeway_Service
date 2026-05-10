from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class CerebrasProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "cerebras"

    @property
    def configured(self) -> bool:
        return bool(settings.cerebras_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.cerebras.ai/v1",
            api_key=settings.cerebras_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        known = [
            ("llama3.1-8b", "Llama 3.1 8B", ModelLimits(requests_per_minute=30, tokens_per_minute=60000, requests_per_day=14400)),
            ("llama3.1-70b", "Llama 3.1 70B", ModelLimits(requests_per_minute=30, tokens_per_minute=60000, requests_per_day=14400)),
            ("llama-3.3-70b", "Llama 3.3 70B", ModelLimits(requests_per_minute=30, tokens_per_minute=60000, requests_per_day=14400)),
        ]
        return [
            ModelInfo(id=mid, name=name, provider=self.name, limits=lim)
            for mid, name, lim in known
        ]
