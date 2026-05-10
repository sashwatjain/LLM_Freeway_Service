from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class NVIDIAProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "nvidia"

    @property
    def configured(self) -> bool:
        return True

    def _api_key(self) -> str:
        return settings.nvidia_api_key

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self._api_key(),
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://integrate.api.nvidia.com/v1/models",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        ModelInfo(
                            id=m["id"],
                            name=m.get("name", m["id"]),
                            provider=self.name,
                            limits=ModelLimits(requests_per_minute=40),
                        )
                        for m in data.get("data", [])
                    ]
        except Exception:
            pass
        return self._known_models()

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "meta/llama-3.3-70b-instruct",
            "mistralai/mistral-small-3.1-24b-instruct",
            "google/gemma-4-26b-a4b-it",
            "nvidia/nemotron-3-nano-30b-a3b",
            "qwen/qwen3-235b-a22b-instruct",
        ]
        return [
            ModelInfo(id=m, name=m.split("/")[-1], provider=self.name, limits=ModelLimits(requests_per_minute=40))
            for m in known
        ]
