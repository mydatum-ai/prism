from prism_compiler.schemas import TransformRequest
from prism_policy_runtime import Policy
from prism_transformers import transform
from prism_vault_core import InMemoryVault


def test_p16_decisions_include_policy_rule_and_reason_metadata() -> None:
    policy = Policy.model_validate(
        {
            "domain": "commercial",
            "version": "4",
            "rules": [
                {
                    "rule_id": "rule_person_tokenize",
                    "entity_type": "person",
                    "action": "tokenize",
                    "token_prefix": "REPORTER",
                }
            ],
        }
    )
    vault = InMemoryVault()

    response = transform(
        TransformRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="Maria Santos emailed maria@example.com",
        ),
        vault=vault,
        policy=policy,
    )

    assert response.transformed_text.startswith("REPORTER_1")
    assert response.decisions[0].action == "tokenize"
    assert response.decisions[0].policy_id == "commercial"
    assert response.decisions[0].policy_version == "4"
    assert response.decisions[0].rule_id == "rule_person_tokenize"
    assert response.decisions[0].reason == "rule_matched"
    assert response.mappings[0].metadata["rule_id"] == "rule_person_tokenize"


def test_p16_policy_actions_transform_expected_output() -> None:
    cases = [
        ("preserve", None, "Maria Santos"),
        ("redact", None, "[REDACTED_PERSON]"),
        ("generalize", None, "person"),
        ("mask", None, "[MASKED_PERSON]"),
        ("deny", None, "[DENIED]"),
    ]

    for action, replacement, expected in cases:
        policy = Policy.model_validate(
            {
                "domain": "commercial",
                "rules": [
                    {
                        "entity_type": "person",
                        "action": action,
                        "replacement": replacement,
                    }
                ],
            }
        )

        response = transform(
            TransformRequest(
                tenant_id="tenant_a",
                app_id="pulse",
                session_id="session_1",
                text="Maria Santos emailed maria@example.com",
            ),
            vault=InMemoryVault(),
            policy=policy,
        )

        assert response.transformed_text.startswith(expected)
        assert response.decisions[0].action == action


def test_p16_unmatched_entities_keep_default_tokenize_decision() -> None:
    response = transform(
        TransformRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="maria@example.com",
        ),
        vault=InMemoryVault(),
        policy=Policy(domain="empty", rules=[]),
    )

    assert response.transformed_text == "EMAIL_1"
    assert response.decisions[0].reason == "default_tokenize"


def test_p16_transform_uses_request_context_for_policy_conditions() -> None:
    policy = Policy.model_validate(
        {
            "domain": "context",
            "rules": [
                {
                    "rule_id": "prod_outbound_email",
                    "entity_type": "email",
                    "action": "redact",
                    "app_id": "pulse",
                    "purpose": "analytics",
                    "direction": "outbound",
                    "environment": "prod",
                },
                {"rule_id": "email_default", "entity_type": "email", "action": "tokenize"},
            ],
        }
    )

    response = transform(
        TransformRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="maria@example.com",
            purpose="analytics",
            direction="outbound",
            environment="prod",
        ),
        vault=InMemoryVault(),
        policy=policy,
    )

    assert response.transformed_text == "[REDACTED_EMAIL]"
    assert response.decisions[0].rule_id == "prod_outbound_email"


def test_p16_session_stable_tokens_repeat_within_session_only() -> None:
    policy = Policy.model_validate(
        {
            "domain": "tokens",
            "rules": [
                {
                    "entity_type": "email",
                    "action": "tokenize",
                    "token_prefix": "EMAIL",
                    "token_strategy": "session_stable",
                }
            ],
        }
    )
    request = TransformRequest(
        tenant_id="tenant_a",
        app_id="pulse",
        session_id="session_1",
        text="maria@example.com",
    )

    first = transform(request, vault=InMemoryVault(), policy=policy)
    second = transform(request, vault=InMemoryVault(), policy=policy)
    other_session = transform(
        request.model_copy(update={"session_id": "session_2"}),
        vault=InMemoryVault(),
        policy=policy,
    )

    assert first.transformed_text == second.transformed_text
    assert first.transformed_text != other_session.transformed_text
    assert first.mappings[0].metadata["token_strategy"] == "session_stable"


def test_p16_tenant_stable_tokens_ignore_app_and_session_scope() -> None:
    policy = Policy.model_validate(
        {
            "domain": "tokens",
            "rules": [
                {
                    "entity_type": "email",
                    "action": "tokenize",
                    "token_prefix": "EMAIL",
                    "token_strategy": "tenant_stable",
                }
            ],
        }
    )
    request = TransformRequest(
        tenant_id="tenant_a",
        app_id="pulse",
        session_id="session_1",
        text="maria@example.com",
    )

    first = transform(request, vault=InMemoryVault(), policy=policy)
    other_app = transform(
        request.model_copy(update={"app_id": "other", "session_id": "session_2"}),
        vault=InMemoryVault(),
        policy=policy,
    )
    other_tenant = transform(
        request.model_copy(update={"tenant_id": "tenant_b"}),
        vault=InMemoryVault(),
        policy=policy,
    )

    assert first.transformed_text == other_app.transformed_text
    assert first.transformed_text != other_tenant.transformed_text


def test_p16_random_opaque_tokens_do_not_repeat() -> None:
    policy = Policy.model_validate(
        {
            "domain": "tokens",
            "rules": [
                {
                    "entity_type": "email",
                    "action": "tokenize",
                    "token_prefix": "EMAIL",
                    "token_strategy": "random_opaque",
                }
            ],
        }
    )
    request = TransformRequest(
        tenant_id="tenant_a",
        app_id="pulse",
        session_id="session_1",
        text="maria@example.com",
    )

    first = transform(request, vault=InMemoryVault(), policy=policy)
    second = transform(request, vault=InMemoryVault(), policy=policy)

    assert first.transformed_text.startswith("EMAIL_")
    assert second.transformed_text.startswith("EMAIL_")
    assert first.transformed_text != second.transformed_text


def test_p16_mapping_metadata_contains_scope_policy_and_decision_fields() -> None:
    policy = Policy.model_validate(
        {
            "domain": "tokens",
            "version": "9",
            "rules": [
                {
                    "rule_id": "email_token",
                    "entity_type": "email",
                    "action": "tokenize",
                    "token_prefix": "EMAIL",
                }
            ],
        }
    )

    response = transform(
        TransformRequest(
            tenant_id="tenant_a",
            app_id="pulse",
            session_id="session_1",
            text="maria@example.com",
        ),
        vault=InMemoryVault(),
        policy=policy,
    )

    metadata = response.mappings[0].metadata
    assert metadata["tenant_id"] == "tenant_a"
    assert metadata["app_id"] == "pulse"
    assert metadata["session_id"] == "session_1"
    assert metadata["policy_id"] == "tokens"
    assert metadata["policy_version"] == "9"
    assert metadata["rule_id"] == "email_token"
    assert metadata["decision_reason"] == "rule_matched"
    assert metadata["token_strategy"] == "sequence"
