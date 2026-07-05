import pytest
from prism_vault_core import RedisVault, VaultKey
from redis import Redis


def test_phase2_redis_vault_integration_round_trip() -> None:
    url = "redis://127.0.0.1:6379/0"
    try:
        Redis.from_url(url).ping()
    except Exception as exc:
        pytest.skip(f"Redis integration service is unavailable: {exc}")

    vault = RedisVault.from_url(url)
    key = VaultKey("tenant_integration", "pulse", "session_1", "EMAIL_1")
    vault.clear_key(key)

    vault.put(key, "john@email.com", "email", ttl_seconds=60)

    assert vault.get(key) == "john@email.com"
    vault.clear_key(key)
