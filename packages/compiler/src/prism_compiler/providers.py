from collections.abc import Iterable
from typing import Protocol

import httpx
from pydantic import BaseModel

from prism_compiler.schemas import ChatMessage


class ProviderResponse(BaseModel):
    content: str
    model: str


class Provider(Protocol):
    def complete(self, model: str, messages: Iterable[ChatMessage]) -> ProviderResponse:
        """Return a provider response for normalized chat messages."""


class MockProvider:
    def complete(self, model: str, messages: Iterable[ChatMessage]) -> ProviderResponse:
        latest = ""
        for message in messages:
            latest = message.content
        return ProviderResponse(content=f"Mock response for: {latest}", model=model)


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = client

    def complete(self, model: str, messages: Iterable[ChatMessage]) -> ProviderResponse:
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
        }
        if self._client is not None:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
        else:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        response.raise_for_status()
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        returned_model = str(data.get("model", model))
        return ProviderResponse(content=content, model=returned_model)
