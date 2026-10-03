import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class FreewayClientError(Exception):
    pass


class FreewayClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("LLM_FREEWAY_URL", "http://localhost:4545")).rstrip("/")
        self._client = httpx.Client(timeout=120)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def health(self) -> dict:
        resp = self._client.get(self._url("/health"))
        resp.raise_for_status()
        return resp.json()

    def list_providers(self) -> list[dict]:
        resp = self._client.get(self._url("/providers"))
        resp.raise_for_status()
        return resp.json()

    def list_models(self, provider: str) -> list[dict]:
        resp = self._client.get(self._url(f"/models/{provider}"))
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()

    def stats(self) -> dict:
        resp = self._client.get(self._url("/stats"))
        resp.raise_for_status()
        return resp.json()

    def chat(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        memory: bool = False,
        session_id: Optional[str] = None,
    ) -> dict:
        payload = {
            "provider": provider,
            "model": model,
            "messages": messages,
            "memory": memory,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if session_id:
            payload["session_id"] = session_id

        resp = self._client.post(self._url("/chat"), json=payload)
        if resp.status_code == 400:
            raise FreewayClientError(resp.json().get("detail", "Bad request"))
        if resp.status_code == 429:
            raise FreewayClientError(resp.json().get("detail", "Rate limited"))
        if resp.status_code == 401:
            raise FreewayClientError(resp.json().get("detail", "Authentication failed"))
        resp.raise_for_status()
        return resp.json()

    def continue_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        memory: bool = False,
        session_id: Optional[str] = None,
        provider_priority: Optional[list[str]] = None,
    ) -> dict:
        payload = {
            "messages": messages,
            "memory": memory,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if session_id:
            payload["session_id"] = session_id
        if provider_priority:
            payload["provider_priority"] = provider_priority

        resp = self._client.post(self._url("/continuechat"), json=payload)
        if resp.status_code == 507:
            detail = resp.json().get("detail", {})
            raise FreewayClientError(
                f"All providers exhausted: {detail.get('error', 'unknown')}"
            )
        if resp.status_code == 400:
            raise FreewayClientError(resp.json().get("detail", "Bad request"))
        resp.raise_for_status()
        return resp.json()

    def clear_memory(self, session_id: str) -> dict:
        resp = self._client.delete(self._url(f"/memory/{session_id}"))
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()
