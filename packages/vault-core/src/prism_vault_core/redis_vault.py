import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol, cast

from redis import Redis

from prism_vault_core.memory import VaultKey, VaultRecord


class RedisClient(Protocol):
    def set(self, name: str, value: str, ex: int | None = None) -> object:
        """Set a Redis key."""

    def get(self, name: str) -> bytes | str | None:
        """Get a Redis key."""

    def delete(self, *names: str) -> object:
        """Delete Redis keys."""


class RedisVault:
    def __init__(self, client: RedisClient) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisVault":
        return cls(cast(RedisClient, Redis.from_url(url, decode_responses=True)))

    def put(
        self,
        key: VaultKey,
        value: str,
        entity_type: str = "unknown",
        ttl_seconds: int | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        payload = {
            "value": value,
            "entity_type": entity_type,
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": dict(metadata or {}),
        }
        self._client.set(key.as_string(), json.dumps(payload), ex=ttl_seconds)

    def get(self, key: VaultKey) -> str | None:
        record = self.get_record(key)
        return record.value if record is not None else None

    def get_record(self, key: VaultKey) -> VaultRecord | None:
        raw = self._client.get(key.as_string())
        if raw is None:
            return None
        payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        return VaultRecord(
            value=str(payload["value"]),
            entity_type=str(payload["entity_type"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            metadata={str(k): str(v) for k, v in payload.get("metadata", {}).items()},
        )

    def clear_key(self, key: VaultKey) -> None:
        self._client.delete(key.as_string())
