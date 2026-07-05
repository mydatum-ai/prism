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
