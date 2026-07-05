from datetime import UTC, datetime

import pytest
from prism_transaction_events import (
    DetectionSummary,
    MappingSummary,
    PolicyDecisionSummary,
    RehydrationDecisionSummary,
    RehydrationTransactionEvent,
    ReviewScores,
    TransactionPrivacy,
    TransformTransactionEvent,
)
from prism_transaction_events.events import fingerprint_text
from pydantic import ValidationError


def test_p18_transform_transaction_event_serializes_stable_contract() -> None:
    event = TransformTransactionEvent(
        event_id="txn_1",
        tenant_id="tenant_dev",
        app_id="pulse",
        session_id="session_1",
        request_id="request_1",
        policy_id="pulse",
        policy_version="7",
        policy_source="enterprise",
        input_fingerprint=fingerprint_text("Maria emailed maria@example.com"),
        created_at=datetime(2026, 7, 5, tzinfo=UTC),
        transformed_preview="PERSON_1 emailed EMAIL_1",
        detections=[DetectionSummary(entity_type="person", start=0, end=8, confidence=0.99)],
        mappings=[MappingSummary(token="PERSON_1", entity_type="person")],
        decisions=[
            PolicyDecisionSummary(
                entity_type="person",
                action="tokenize",
                policy_id="pulse",
                policy_version="7",
                rule_id="resident_token",
                reason="rule_matched",
                token="PERSON_1",
            )
        ],
        scores=ReviewScores(
            detection_confidence=0.99,
            policy_coverage=1.0,
            leakage_risk=0.0,
            explanations=["all detected entities covered by policy"],
        ),
    )

    payload = event.model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["event_type"] == "transform"
    assert payload["policy_source"] == "enterprise"
    assert payload["raw_input_text"] is None
    assert payload["detections"][0]["text_preview"] is None
    assert payload["scores"]["explanations"] == ["all detected entities covered by policy"]


def test_p18_rehydration_transaction_event_records_allowed_and_blocked_decisions() -> None:
    event = RehydrationTransactionEvent(
        event_id="txn_2",
        tenant_id="tenant_dev",
        app_id="pulse",
        session_id="session_1",
        request_id="request_2",
        input_fingerprint=fingerprint_text("PERSON_1"),
        requested_text_preview="PERSON_1",
        rehydrated_preview="PERSON_1",
        requester_roles=["viewer"],
        decisions=[
            RehydrationDecisionSummary(
                token="PERSON_1",
                entity_type="person",
                allowed=False,
                reason="role_not_allowed",
                status="policy_blocked",
            )
        ],
        scores=ReviewScores(rehydration_risk=0.8, unresolved_token_count=1),
    )

    payload = event.model_dump(mode="json")

    assert payload["event_type"] == "rehydrate"
    assert payload["decisions"][0]["allowed"] is False
    assert payload["scores"]["unresolved_token_count"] == 1


def test_p18_transaction_event_requires_runtime_context() -> None:
    with pytest.raises(ValidationError):
        TransformTransactionEvent.model_validate(
            {
                "app_id": "pulse",
                "session_id": "session_1",
                "request_id": "request_1",
                "input_fingerprint": "abc",
                "transformed_preview": "PERSON_1",
            }
        )


def test_p18_raw_input_text_requires_explicit_capture() -> None:
    with pytest.raises(ValidationError, match="raw_input_text requires"):
        TransformTransactionEvent(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            request_id="request_1",
            input_fingerprint="abc",
            transformed_preview="PERSON_1",
            raw_input_text="Maria Santos",
        )

    event = TransformTransactionEvent(
        tenant_id="tenant_dev",
        app_id="pulse",
        session_id="session_1",
        request_id="request_1",
        input_fingerprint="abc",
        transformed_preview="PERSON_1",
        raw_input_text="Maria Santos",
        privacy=TransactionPrivacy(raw_text_capture_enabled=True, raw_text_retention_days=1),
    )

    assert event.raw_input_text == "Maria Santos"
