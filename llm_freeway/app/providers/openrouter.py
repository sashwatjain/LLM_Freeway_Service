from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def configured(self) -> bool:
        return bool(settings.openrouter_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            headers={
                "HTTP-Referer": "https://github.com/free_chat_completion_service",
                "X-Title": "LLM-Freeway",
            },
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return await self._list_known_free_models()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("data", []):
            pricing = float(m.get("pricing", {}).get("completion", "1")) + float(
                m.get("pricing", {}).get("prompt", "1")
            )
            if pricing != 0:
                continue
            if ":free" not in m["id"]:
                continue
            models.append(
                ModelInfo(
                    id=m["id"],
                    name=m["id"].split("/")[-1].replace(":free", ""),
                    provider=self.name,
                    limits=ModelLimits(
                        requests_per_minute=20,
                        requests_per_day=50,
                    ),
                )
            )
        return sorted(models, key=lambda x: x.name)

    async def _list_known_free_models(self) -> list[ModelInfo]:
        known = [
            "nousresearch/hermes-3-llama-3.1-405b:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-4-26b-a4b-it:free",
            "google/gemma-4-31b-it:free",
            "minimax/minimax-m2.5:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "qwen/qwen3-coder:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
        ]
        return [
            ModelInfo(
                id=m,
                name=m.split("/")[-1].replace(":free", ""),
                provider=self.name,
                limits=ModelLimits(requests_per_minute=20, requests_per_day=50),
            )
            for m in known
        ]
