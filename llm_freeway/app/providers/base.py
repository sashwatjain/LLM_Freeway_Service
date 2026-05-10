from abc import ABC, abstractmethod
from typing import Optional
import httpx

from app.schemas import ModelInfo, ChatResponse, Message


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]: ...

    @property
    def configured(self) -> bool:
        return True

    def _format_messages(
        self, messages: list[Message], system_prompt: Optional[str] = None
    ) -> list[dict]:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted.extend(
            {"role": m.role, "content": m.content} for m in messages
        )
        return formatted

    async def _openai_chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> ChatResponse:
        formatted = self._format_messages(messages, system_prompt)
        payload = {"model": model, "messages": formatted}

        request_headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            request_headers["Authorization"] = f"Bearer {api_key}"
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=request_headers,
                json=payload,
            )

        if resp.status_code == 429:
            raise RateLimitError(
                f"Rate limited by {self.name}: {resp.text}"
            )
        if resp.status_code == 401:
            raise AuthError(
                f"Authentication failed for {self.name}: {resp.text}"
            )
        resp.raise_for_status()
        data = resp.json()

        return ChatResponse(
            choices=data.get("choices", []),
            usage=data.get("usage"),
            provider=self.name,
            model=model,
        )


class RateLimitError(Exception):
    pass


class AuthError(Exception):
    pass


class ProviderError(Exception):
    pass
