from prism_vault_core import InMemoryVault, VaultKey


def test_phase2_in_memory_vault_scopes_by_tenant_app_session() -> None:
    vault = InMemoryVault()
    token = "PERSON_1"
    vault.put(VaultKey("tenant_a", "pulse", "session_1", token), "John Smith", "person")

    assert vault.get(VaultKey("tenant_a", "pulse", "session_1", token)) == "John Smith"
    assert vault.get(VaultKey("tenant_b", "pulse", "session_1", token)) is None
    assert vault.get(VaultKey("tenant_a", "other", "session_1", token)) is None
    assert vault.get(VaultKey("tenant_a", "pulse", "session_2", token)) is None


def test_phase2_in_memory_vault_keeps_metadata_internal() -> None:
    vault = InMemoryVault()
    key = VaultKey("tenant_a", "pulse", "session_1", "EMAIL_1")

    vault.put(key, "john@email.com", "email", metadata={"request_id": "request_1"})

    record = vault.get_record(key)
    assert record is not None
    assert record.value == "john@email.com"
    assert record.entity_type == "email"
    assert record.metadata == {"request_id": "request_1"}
