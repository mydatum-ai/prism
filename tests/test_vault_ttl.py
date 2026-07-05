from time import sleep

from prism_compiler.schemas import RehydrateRequest
from prism_rehydration import rehydrate
from prism_vault_core import InMemoryVault, VaultKey


def test_phase2_expired_mapping_fails_closed() -> None:
    vault = InMemoryVault()
    vault.put(
        VaultKey("tenant_a", "pulse", "session_1", "PERSON_1"),
        "John Smith",
        "person",
        ttl_seconds=0,
    )

    assert vault.get(VaultKey("tenant_a", "pulse", "session_1", "PERSON_1")) is None


def test_phase2_rehydration_leaves_expired_token_in_place() -> None:
    vault = InMemoryVault()
    vault.put(
        VaultKey("tenant_a", "pulse", "session_1", "PERSON_1"),
        "John Smith",
        "person",
        ttl_seconds=1,
    )
    sleep(1.1)

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="PERSON_1 reported flooding",
        ),
        vault=vault,
    )

    assert response.text == "PERSON_1 reported flooding"
