from prism_compiler.schemas import TransformRequest
from prism_policy_runtime import load_policy
from prism_transformers import transform
from prism_vault_core import GLOBAL_VAULT


def test_phase3_same_prompt_transforms_differently_under_different_policies() -> None:
    GLOBAL_VAULT.clear()
    request = TransformRequest(
        tenant_id="tenant_dev",
        app_id="pulse",
        session_id="session_1",
        text="John Smith emailed john@email.com about INV-1001",
    )

    pulse_response = transform(request, policy=load_policy("examples/policies/pulse.yaml"))
    support_response = transform(request, policy=load_policy("examples/policies/support.yaml"))

    assert pulse_response.transformed_text == "RESIDENT_1 emailed EMAIL_1 about INV-1001"
    assert support_response.transformed_text == ("customer emailed [MASKED_EMAIL] about CASE_1")


def test_phase3_policy_version_appears_in_audit_event() -> None:
    response = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="John Smith emailed john@email.com",
        ),
        policy=load_policy("examples/policies/pulse.yaml"),
    )

    assert response.audit_event.policy_id == "pulse"
    assert response.audit_event.policy_version == "1"
