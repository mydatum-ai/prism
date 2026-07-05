from collections.abc import Iterable, Mapping
from typing import Protocol

from prism_compiler.schemas import EntityDetection


class Detector(Protocol):
    """Detects candidate sensitive entities in text."""

    def detect(self, text: str) -> Iterable[EntityDetection]:
        """Return detected entities for the given text."""


class Provider(Protocol):
    """LLM provider interface used by the gateway."""

    def complete(self, messages: Iterable[Mapping[str, str]]) -> str:
        """Return a provider response for normalized chat messages."""


class Vault(Protocol):
    """Stores private mappings between source values and Prism tokens."""

    def put(
        self,
        key: str,
        value: str,
        entity_type: str = "unknown",
        ttl_seconds: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Store a value under a key."""

    def get(self, key: str) -> str | None:
        """Return a stored value, or None when unavailable."""
