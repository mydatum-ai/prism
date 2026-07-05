from collections import Counter
from collections.abc import Iterable
from typing import Protocol
from uuid import uuid4

from prism_compiler.schemas import (
    AuditEvent,
    EntityDetection,
    TokenMapping,
    TransformationDecision,
    TransformRequest,
    TransformResponse,
)
from prism_detectors import EmailDetector, InvoiceDetector, PhoneDetector, SimpleNameDetector
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    PolicyDecision,
    PolicyDecisionContext,
    decide,
)
from prism_vault_core import GLOBAL_VAULT, InMemoryVault, VaultKey

TOKEN_PREFIXES = {
    "email": "EMAIL",
    "invoice": "INVOICE",
    "person": "PERSON",
    "phone": "PHONE",
}


class EntityDetector(Protocol):
    def detect(self, text: str) -> Iterable[EntityDetection]:
        """Return entity detections for text."""


def default_detectors() -> list[EntityDetector]:
    return [EmailDetector(), PhoneDetector(), InvoiceDetector(), SimpleNameDetector()]


def detect_entities(
    text: str, detectors: Iterable[EntityDetector] | None = None
) -> list[EntityDetection]:
    active_detectors = detectors or default_detectors()
    detections: list[EntityDetection] = []
    for detector in active_detectors:
        detections.extend(detector.detect(text))
    return _remove_overlaps(sorted(detections, key=lambda item: (item.start, item.end)))


def transform(
    request: TransformRequest,
    vault: InMemoryVault = GLOBAL_VAULT,
    policy: Policy = DEFAULT_POLICY,
) -> TransformResponse:
    request_id = str(uuid4())
    detections = detect_entities(request.text)
    counters: Counter[str] = Counter()
    mappings: list[TokenMapping] = []
    decisions: list[TransformationDecision] = []
    response_detections: list[EntityDetection] = []
    transformed_parts: list[str] = []
    cursor = 0
    transformed_cursor = 0

    for detection in detections:
        unchanged = request.text[cursor : detection.start]
        transformed_parts.append(unchanged)
        transformed_cursor += len(unchanged)
        decision = decide(
            policy,
            detection,
            PolicyDecisionContext(
                app_id=request.app_id,
                purpose=request.purpose,
                direction=request.direction,
                environment=request.environment,
            ),
        )
        counters[detection.entity_type] += 1
        replacement = _replacement_for(detection, counters[detection.entity_type], decision)
        transformed_parts.append(replacement)
        cursor = detection.end
        token_start = transformed_cursor
        transformed_cursor += len(replacement)

        if decision.action == "tokenize":
            metadata = {
                "request_id": request_id,
                "policy_id": decision.policy_id,
                "policy_version": decision.policy_version,
                "decision_reason": decision.reason,
            }
            if decision.rule_id is not None:
                metadata["rule_id"] = decision.rule_id
            vault.put(
                VaultKey(request.tenant_id, request.app_id, request.session_id, replacement),
                detection.text,
                entity_type=detection.entity_type,
                metadata=metadata,
            )
            mappings.append(
                TokenMapping(
                    token=replacement, entity_type=detection.entity_type, metadata=metadata
                )
            )
        decisions.append(
            TransformationDecision(
                entity_type=detection.entity_type,
                action=decision.action,
                policy_id=decision.policy_id,
                policy_version=decision.policy_version,
                rule_id=decision.rule_id,
                reason=decision.reason,
                token=replacement if decision.action == "tokenize" else None,
                start=token_start,
                end=transformed_cursor,
                confidence=detection.confidence,
            )
        )
        response_detections.append(
            EntityDetection(
                text=replacement,
                entity_type=detection.entity_type,
                start=token_start,
                end=transformed_cursor,
                confidence=detection.confidence,
            )
        )

    transformed_parts.append(request.text[cursor:])
    audit_event = AuditEvent(
        event_type="transform",
        tenant_id=request.tenant_id,
        app_id=request.app_id,
        session_id=request.session_id,
        request_id=request_id,
        policy_id=request.policy_id or policy.policy_id,
        policy_version=policy.version,
    )
    return TransformResponse(
        request_id=request_id,
        transformed_text="".join(transformed_parts),
        detections=response_detections,
        mappings=mappings,
        decisions=decisions,
        audit_event=audit_event,
    )


def _token_for(entity_type: str, index: int) -> str:
    prefix = TOKEN_PREFIXES.get(entity_type, entity_type.upper())
    return f"{prefix}_{index}"


def _replacement_for(detection: EntityDetection, index: int, decision: PolicyDecision) -> str:
    action = decision.action
    if action == "preserve":
        return detection.text
    if action == "tokenize":
        prefix = decision.token_prefix or TOKEN_PREFIXES.get(
            detection.entity_type, detection.entity_type.upper()
        )
        return f"{prefix}_{index}"
    if action == "mask":
        return decision.replacement or f"[MASKED_{detection.entity_type.upper()}]"
    if action == "redact":
        return decision.replacement or f"[REDACTED_{detection.entity_type.upper()}]"
    if action == "generalize":
        return decision.replacement or detection.entity_type
    if action == "abstract":
        return decision.replacement or f"[{detection.entity_type.upper()}]"
    if action == "deny":
        return decision.replacement or "[DENIED]"
    if action == "block":
        return decision.replacement or "[BLOCKED]"
    return _token_for(detection.entity_type, index)


def _remove_overlaps(detections: list[EntityDetection]) -> list[EntityDetection]:
    accepted: list[EntityDetection] = []
    occupied_until = -1
    for detection in detections:
        if detection.start < occupied_until:
            continue
        accepted.append(detection)
        occupied_until = detection.end
    return accepted
