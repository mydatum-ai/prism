from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock


@dataclass(frozen=True)
class VaultKey:
    tenant_id: str
    app_id: str
    session_id: str
    token: str

    def as_string(self) -> str:
        return f"{self.tenant_id}:{self.app_id}:{self.session_id}:{self.token}"


@dataclass(frozen=True)
class VaultRecord:
    value: str
    entity_type: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def expired(self) -> bool:
        return self.expires_at is not None and datetime.now(UTC) >= self.expires_at


class InMemoryVault:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[str, VaultRecord] = {}

    def put(
        self,
        key: VaultKey,
        value: str,
        entity_type: str = "unknown",
        ttl_seconds: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        with self._lock:
            self._values[key.as_string()] = VaultRecord(
                value=value,
                entity_type=entity_type,
                expires_at=expires_at,
                metadata=metadata or {},
            )

    def get(self, key: VaultKey) -> str | None:
        record = self.get_record(key)
        return record.value if record is not None else None

    def get_record(self, key: VaultKey) -> VaultRecord | None:
        with self._lock:
            key_string = key.as_string()
            record = self._values.get(key_string)
            if record is None:
                return None
            if record.expired:
                del self._values[key_string]
                return None
            return record

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


GLOBAL_VAULT = InMemoryVault()
