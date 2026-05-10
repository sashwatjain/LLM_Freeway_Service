from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class KlusterProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "kluster"

    @property
    def configured(self) -> bool:
        return bool(settings.kluster_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.kluster.ai/v1",
            api_key=settings.kluster_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.kluster.ai/v1/models",
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        raw = data.get("data", data if isinstance(data, list) else [])
        if isinstance(raw, dict):
            raw = [raw]

        return [
            ModelInfo(id=m["id"], name=m.get("name", m["id"]), provider=self.name)
            for m in raw
            if "id" in m
        ]

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "deepseek-ai/DeepSeek-R1",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ]
        return [
            ModelInfo(id=m, name=m.split("/")[-1], provider=self.name) for m in known
        ]
