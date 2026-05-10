from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class CloudflareProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "cloudflare"

    @property
    def configured(self) -> bool:
        return bool(settings.cloudflare_account_id and settings.cloudflare_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/v1",
            api_key=settings.cloudflare_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/models/search?search=Text+Generation",
                headers={
                    "Authorization": f"Bearer {settings.cloudflare_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            ModelInfo(
                id=m["name"],
                name=m["name"].split("/")[-1],
                provider=self.name,
                limits=ModelLimits(requests_per_day=10000),
            )
            for m in data.get("result", [])
        ]

    def _known_models(self) -> list[ModelInfo]:
        known = [
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            "@cf/mistral/mistral-small-3.1-24b-instruct",
            "@cf/qwen/qwen3-30b-a3b-fp8",
            "@cf/google/gemma-4-26b-a4b-it",
            "@cf/nvidia/nemotron-3-120b-a12b",
            "@cf/moonshotai/kimi-k2.5",
        ]
        return [
            ModelInfo(id=m, name=m.split("/")[-1], provider=self.name, limits=ModelLimits(requests_per_day=10000))
            for m in known
        ]
