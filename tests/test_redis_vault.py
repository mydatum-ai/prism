from prism_vault_core import RedisVault, VaultKey


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, name: str, value: str, ex: int | None = None) -> object:
        _ = ex
        self.values[name] = value
        return True

    def get(self, name: str) -> bytes | str | None:
        return self.values.get(name)

    def delete(self, *names: str) -> object:
        for name in names:
            self.values.pop(name, None)
        return len(names)


def test_phase2_redis_vault_round_trip_with_metadata() -> None:
    vault = RedisVault(FakeRedis())
    key = VaultKey("tenant_a", "pulse", "session_1", "INVOICE_1")

    vault.put(key, "INV-1001", "invoice", ttl_seconds=60, metadata={"request_id": "request_1"})

    assert vault.get(key) == "INV-1001"
    record = vault.get_record(key)
    assert record is not None
    assert record.entity_type == "invoice"
    assert record.metadata == {"request_id": "request_1"}
