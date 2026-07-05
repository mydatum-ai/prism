from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_policy_runtime import Policy
from prism_rehydration import rehydrate
from prism_transformers import transform
from prism_vault_core import GLOBAL_VAULT


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
