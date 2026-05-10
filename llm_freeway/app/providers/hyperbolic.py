from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class HyperbolicProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "hyperbolic"

    @property
    def configured(self) -> bool:
        return bool(settings.hyperbolic_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.hyperbolic.xyz/v1",
            api_key=settings.hyperbolic_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.hyperbolic.xyz/v1/models",
                headers={
                    "accept": "application/json",
                    "authorization": f"Bearer {settings.hyperbolic_api_key}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            ModelInfo(
                id=m["id"],
                name=m["id"],
                provider=self.name,
                limits=ModelLimits(requests_per_minute=60),
            )
            for m in data.get("data", [])
        ]

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "deepseek-ai/DeepSeek-V3-0324",
            "meta-llama/Llama-3.3-70B-Instruct",
            "deepseek-ai/deepseek-r1-0528",
            "Qwen/Qwen3-Coder-480B-A35B-Instruct",
        ]
        return [
            ModelInfo(id=m, name=m.split("/")[-1], provider=self.name, limits=ModelLimits(requests_per_minute=60))
            for m in known
        ]
