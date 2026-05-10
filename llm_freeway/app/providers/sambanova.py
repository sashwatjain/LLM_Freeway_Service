from typing import Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class SambaNovaProvider(BaseProvider):
    CHAT_MODELS = {
        "Meta-Llama-3.3-70B-Instruct": "Meta-Llama-3.3-70B-Instruct",
        "Llama-4-Maverick-17B-128E-Instruct": "Llama-4-Maverick-17B-128E-Instruct",
        "DeepSeek-V3.1": "DeepSeek-V3.1",
        "DeepSeek-V3.2": "DeepSeek-V3.2",
        "Qwen3-Coder-480B-A35B": "Qwen3-Coder-480B-A35B",
        "gemma-3-12b-it": "gemma-3-12b-it",
        "gpt-oss-120b": "gpt-oss-120b",
        "MiniMax-M2.5": "MiniMax-M2.5",
        "MiniMax-M2.7": "MiniMax-M2.7",
    }

    @property
    def name(self) -> str:
        return "sambanova"

    @property
    def configured(self) -> bool:
        return bool(settings.samba_api_key)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://api.sambanova.ai/v1",
            api_key=settings.samba_api_key,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self.configured:
            return self._known_models()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://cloud.sambanova.ai/api/pricing")
                resp.raise_for_status()
                data = resp.json()

            models = []
            for m in data.get("prices", []):
                mid = m["model_id"]
                name = m.get("model_name") or mid
                if mid in self.CHAT_MODELS:
                    models.append(
                        ModelInfo(
                            id=self.CHAT_MODELS[mid],
                            name=name,
                            provider=self.name,
                            limits=ModelLimits(requests_per_minute=30),
                        )
                    )
            return sorted(models, key=lambda x: x.name) if models else self._known_models()
        except Exception:
            return self._known_models()

    def _known_models(self) -> list[ModelInfo]:
        models = [
            ("Meta-Llama-3.3-70B-Instruct", "Llama 3.3 70B"),
            ("Llama-4-Maverick-17B-128E-Instruct", "Llama 4 Maverick"),
            ("DeepSeek-V3.1", "DeepSeek V3.1"),
            ("DeepSeek-V3.2", "DeepSeek V3.2"),
            ("MiniMax-M2.5", "MiniMax M2.5"),
            ("MiniMax-M2.7", "MiniMax M2.7"),
            ("gpt-oss-120b", "GPT-OSS 120B"),
            ("gemma-3-12b-it", "Gemma 3 12B"),
        ]
        return [
            ModelInfo(id=mid, name=name, provider=self.name, limits=ModelLimits(requests_per_minute=30))
            for mid, name in models
        ]
