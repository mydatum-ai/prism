from prism_compiler.schemas import TransformRequest
from prism_transformers import transform
from prism_vault_core import GLOBAL_VAULT


def test_phase1_transforms_prompt_and_stores_mappings() -> None:
    GLOBAL_VAULT.clear()

    response = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="John Smith emailed john@email.com about INV-1001",
        )
    )

    assert response.transformed_text == "PERSON_1 emailed EMAIL_1 about INVOICE_1"
    assert [(mapping.token, mapping.entity_type) for mapping in response.mappings] == [
        ("PERSON_1", "person"),
        ("EMAIL_1", "email"),
        ("INVOICE_1", "invoice"),
    ]
    assert "John Smith" not in response.model_dump_json()
    assert response.audit_event.event_type == "transform"
