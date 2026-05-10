from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class MistralProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "mistral"

    @property
    def configured(self) -> bool:
        return bool(settings.mistral_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.mistral.ai/v1",
            api_key=settings.mistral_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.mistral.ai/v1/models",
                headers={
                    "Authorization": f"Bearer {settings.mistral_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            ModelInfo(
                id=m["id"],
                name=m["id"],
                provider=self.name,
                limits=ModelLimits(
                    requests_per_minute=60,
                    tokens_per_minute=500000,
                ),
            )
            for m in data.get("data", [])
        ]

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "mistral-small-2503", "mistral-medium-2505",
            "mistral-large-2504", "codestral-2505",
            "pixtral-12b-2409",
        ]
        return [
            ModelInfo(id=m, name=m, provider=self.name, limits=ModelLimits(requests_per_minute=60))
            for m in known
        ]
