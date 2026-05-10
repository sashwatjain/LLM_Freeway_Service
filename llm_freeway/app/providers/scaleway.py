from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class ScalewayProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "scaleway"

    @property
    def configured(self) -> bool:
        return bool(settings.scaleway_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.scaleway.ai/v1",
            api_key=settings.scaleway_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.scaleway.ai/v1/models",
                headers={
                    "Authorization": f"Bearer {settings.scaleway_api_key}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            ModelInfo(id=m["id"], name=m["id"], provider=self.name)
            for m in data.get("data", [])
        ]

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "llama-3.3-70b-instruct", "gemma-3-27b-it",
            "qwen3-235b-a22b-instruct", "mistral-small-3.2-24b-instruct",
            "gpt-oss-120b", "pixtral-12b-2409",
        ]
        return [ModelInfo(id=m, name=m, provider=self.name) for m in known]
