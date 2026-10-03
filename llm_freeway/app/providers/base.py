from abc import ABC, abstractmethod
from typing import Any, Optional
import httpx

from app.schemas import ModelInfo, ChatResponse, Message
from app.services.response_utils import extract_response_text, normalize_choices_text


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
        extra_payload: Optional[dict[str, Any]] = None,
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
        extra_payload: Optional[dict[str, Any]] = None,
        headers: Optional[dict] = None,
    ) -> ChatResponse:
        formatted = self._format_messages(messages, system_prompt)
        payload = {"model": model, "messages": formatted}
        if extra_payload:
            payload.update(extra_payload)

        request_headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            request_headers["Authorization"] = f"Bearer {api_key}"
        if headers:
            request_headers.update(headers)

        debug_headers = {
            key: ("<redacted>" if key.lower() == "authorization" else value)
            for key, value in request_headers.items()
        }
        print(
            "----------------------------------------openai upstream request:",
            {
                "provider": self.name,
                "base_url": base_url,
                "model": model,
                "headers": debug_headers,
                "payload": payload,
            },
        )

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=request_headers,
                json=payload,
            )

        print(
            "----------------------------------------openai upstream response status:",
            {
                "provider": self.name,
                "model": model,
                "status_code": resp.status_code,
                "body": resp.text,
            },
        )

        if resp.status_code == 429:
            raise RateLimitError(
                f"Rate limited by {self.name}: {resp.text}"
            )
        if resp.status_code == 400:
            raise ProviderError(
                f"Bad request to {self.name}: {resp.text}"
            )
        if resp.status_code == 401:
            raise AuthError(
                f"Authentication failed for {self.name}: {resp.text}"
            )
        resp.raise_for_status()
        data = resp.json()
        print("----------------------------------------openai upstream raw response:", data)
        fallback_text = extract_response_text(data)
        choices = normalize_choices_text(data.get("choices", []))

        # Some providers, including Cloudflare-hosted gpt-oss variants, may put
        # the final answer in a top-level response field while leaving
        # choices[*].message.content empty. Fill that gap so OpenAI-compatible
        # clients receive assistant text.
        if fallback_text:
            if choices:
                for choice in choices:
                    message = choice.get("message", {})
                    if not message.get("content"):
                        message["content"] = fallback_text
                        choice["message"] = message
            else:
                choices = [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": fallback_text},
                        "finish_reason": "stop",
                    }
                ]

        if fallback_text and any(not c.get("message", {}).get("content") for c in choices):
            print("----------------------------------------openai upstream fallback response text:", fallback_text)
        if fallback_text:
            print("openai upstream response field:", fallback_text)

        return ChatResponse(
            choices=choices,
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
