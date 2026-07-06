from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_policy_runtime import Policy
from prism_rehydration import rehydrate
from prism_transformers import transform
from prism_vault_core import GLOBAL_VAULT, InMemoryVault, VaultKey


def test_phase1_rehydrates_transformed_prompt() -> None:
    GLOBAL_VAULT.clear()
    transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="John Smith emailed john@email.com about INV-1001",
        )
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="PERSON_1 emailed EMAIL_1 about INVOICE_1",
        )
    )

    assert response.text == "John Smith emailed john@email.com about INV-1001"
    assert response.audit_event.event_type == "rehydrate"


def test_p16_rehydrates_non_numeric_stable_tokens() -> None:
    GLOBAL_VAULT.clear()
    transformed = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="john@email.com",
        ),
        policy=Policy.model_validate(
            {
                "domain": "tokens",
                "rules": [
                    {
                        "entity_type": "email",
                        "action": "tokenize",
                        "token_strategy": "session_stable",
                    }
                ],
            }
        ),
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text=transformed.transformed_text,
        )
    )

    assert response.text == "john@email.com"


def test_p16_rehydration_policy_allows_authorized_role() -> None:
    vault = InMemoryVault()
    vault.put(VaultKey("tenant_a", "pulse", "session_1", "EMAIL_1"), "a@example.com", "email")
    policy = Policy.model_validate(
        {
            "domain": "rehydrate",
            "rules": [
                {
                    "rule_id": "admin_email",
                    "entity_type": "email",
                    "action": "tokenize",
                    "rehydrate_roles": ["admin"],
                }
            ],
        }
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="EMAIL_1",
            roles=["admin"],
        ),
        vault=vault,
        policy=policy,
    )

    assert response.text == "a@example.com"
    assert response.diagnostics[0].status == "allowed"
    assert response.diagnostics[0].policy_id == "rehydrate"
    assert response.diagnostics[0].policy_version == "1"
    assert response.diagnostics[0].rule_id == "admin_email"
    assert response.diagnostics[0].requester_roles == ["admin"]
    assert response.diagnostics[0].required_roles == ["admin"]
    assert response.diagnostics[0].matched_constraints == {"roles": "admin"}
    assert response.audit_event.metadata["allowed_count"] == "1"


def test_p16_rehydration_policy_blocks_unauthorized_role() -> None:
    vault = InMemoryVault()
    vault.put(VaultKey("tenant_a", "pulse", "session_1", "EMAIL_1"), "a@example.com", "email")
    policy = Policy.model_validate(
        {
            "domain": "rehydrate",
            "rules": [
                {
                    "rule_id": "admin_email",
                    "entity_type": "email",
                    "action": "tokenize",
                    "rehydrate_roles": ["admin"],
                }
            ],
        }
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="EMAIL_1",
            roles=["viewer"],
        ),
        vault=vault,
        policy=policy,
    )

    assert response.text == "EMAIL_1"
    assert response.diagnostics[0].status == "policy_blocked"
    assert response.diagnostics[0].reason == "role_not_allowed"
    assert response.diagnostics[0].policy_id == "rehydrate"
    assert response.diagnostics[0].policy_version == "1"
    assert response.diagnostics[0].rule_id == "admin_email"
    assert response.diagnostics[0].requester_roles == ["viewer"]
    assert response.diagnostics[0].required_roles == ["admin"]
    assert response.diagnostics[0].matched_constraints == {"roles": "admin"}


def test_p16_rehydration_reports_wrong_scope_and_expired_tokens() -> None:
    vault = InMemoryVault()
    vault.put(VaultKey("tenant_a", "pulse", "session_1", "EMAIL_1"), "a@example.com", "email")
    vault.put(
        VaultKey("tenant_a", "pulse", "session_2", "EMAIL_2"),
        "expired@example.com",
        "email",
        ttl_seconds=0,
    )

    wrong_scope = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_b",
            app_id="pulse",
            session_id="session_1",
            text="EMAIL_1",
        ),
        vault=vault,
    )
    expired = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_2",
            text="EMAIL_2",
        ),
        vault=vault,
    )

    assert wrong_scope.diagnostics[0].status == "wrong_scope"
    assert expired.diagnostics[0].status == "expired"


def test_p16_rehydration_allowed_entity_types_filter() -> None:
    vault = InMemoryVault()
    vault.put(VaultKey("tenant_a", "pulse", "session_1", "EMAIL_1"), "a@example.com", "email")

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="EMAIL_1",
            allowed_entity_types=["person"],
        ),
        vault=vault,
    )

    assert response.text == "EMAIL_1"
    assert response.diagnostics[0].status == "denied"
    assert response.diagnostics[0].reason == "entity_type_not_allowed"
