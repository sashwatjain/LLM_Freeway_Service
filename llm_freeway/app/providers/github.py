from typing import Any, Optional
import httpx

from app.config import settings
from app.schemas import ModelInfo, ChatResponse, Message, ModelLimits
from app.providers.base import BaseProvider


class GitHubProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "github"

    @property
    def configured(self) -> bool:
        return True

    def _api_key(self) -> str:
        return settings.github_token

    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
        extra_payload: Optional[dict[str, Any]] = None,
    ) -> ChatResponse:
        return await self._openai_chat(
            base_url="https://models.inference.ai.azure.com",
            api_key=self._api_key(),
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            extra_payload=extra_payload,
        )

    async def list_models(self) -> list[ModelInfo]:
        known = [
            "gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
            "o3-mini", "o4-mini", "DeepSeek-R1", "DeepSeek-V3-0324",
            "Llama-3.3-70B-Instruct", "Llama-4-Scout-17B-16E-Instruct",
            "Llama-4-Maverick-17B-128E-Instruct",
            "Mistral-Small-3.1", "Ministral-3B", "Codestral-25.01",
            "Phi-4", "Phi-4-mini-instruct", "Phi-4-reasoning",
            "Cohere-Command-A", "Cohere-Command-R-08-2024",
            "AI21-Jamba-1.5-Large",
        ]
        return [
            ModelInfo(id=m, name=m, provider=self.name) for m in known
        ]
