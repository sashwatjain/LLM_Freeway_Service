from typing import Optional
from app.providers.base import BaseProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider):
        self._providers[provider.name.lower()] = provider

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name.lower())

    def list_all(self) -> list[BaseProvider]:
        return list(self._providers.values())

    def list_configured(self) -> list[BaseProvider]:
        return [p for p in self._providers.values() if p.configured]


registry = ProviderRegistry()
