from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class VaultKey:
    tenant_id: str
    app_id: str
    session_id: str
    token: str

    def as_string(self) -> str:
        return f"{self.tenant_id}:{self.app_id}:{self.session_id}:{self.token}"


class InMemoryVault:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[str, str] = {}

    def put(self, key: VaultKey, value: str) -> None:
        with self._lock:
            self._values[key.as_string()] = value

    def get(self, key: VaultKey) -> str | None:
        with self._lock:
            return self._values.get(key.as_string())

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


GLOBAL_VAULT = InMemoryVault()
