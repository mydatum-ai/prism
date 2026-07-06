from collections import Counter
from collections.abc import Iterable
from hashlib import sha256
from typing import Literal, Protocol, cast
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
from prism_transaction_events import (
    DetectionSummary,
    MappingSummary,
    PolicyDecisionSummary,
    ReviewScores,
    TransactionEventSink,
    TransformTransactionEvent,
    emit_transaction_event,
)
from prism_transaction_events.events import fingerprint_text
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
    transaction_sink: TransactionEventSink | None = None,
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
        replacement = _replacement_for(
            detection,
            counters[detection.entity_type],
            decision,
            request=request,
        )
        transformed_parts.append(replacement)
        cursor = detection.end
        token_start = transformed_cursor
        transformed_cursor += len(replacement)

        if decision.action == "tokenize":
            metadata = {
                "tenant_id": request.tenant_id,
                "app_id": request.app_id,
                "session_id": request.session_id,
                "request_id": request_id,
                "policy_id": decision.policy_id,
                "policy_version": decision.policy_version,
                "policy_source": request.policy_source or "unknown",
                "entity_type": detection.entity_type,
                "decision_reason": decision.reason,
                "token_strategy": decision.token_strategy,
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
                policy_source=request.policy_source or "unknown",
                policy_cache_hit=request.policy_cache_hit,
                policy_cache_stale=request.policy_cache_stale,
                rule_id=decision.rule_id,
                reason=decision.reason,
                token=replacement if decision.action == "tokenize" else None,
                token_strategy=decision.token_strategy,
                app_id=request.app_id,
                role=decision.role,
                purpose=request.purpose or decision.purpose,
                direction=request.direction or decision.direction,
                environment=request.environment or decision.environment,
                matched_constraints=decision.matched_constraints,
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
        metadata={
            "policy_source": request.policy_source or "unknown",
            "policy_cache_hit": str(request.policy_cache_hit).lower()
            if request.policy_cache_hit is not None
            else "unknown",
            "policy_cache_stale": str(request.policy_cache_stale).lower()
            if request.policy_cache_stale is not None
            else "unknown",
            "policy_provider_latency_ms": f"{request.policy_provider_latency_ms:.3f}"
            if request.policy_provider_latency_ms is not None
            else "unknown",
        },
    )
    response = TransformResponse(
        request_id=request_id,
        transformed_text="".join(transformed_parts),
        detections=response_detections,
        mappings=mappings,
        decisions=decisions,
        audit_event=audit_event,
    )
    emit_transaction_event(
        _transaction_event_for_transform(request, response, policy),
        transaction_sink,
    )
    return response


def _transaction_event_for_transform(
    request: TransformRequest,
    response: TransformResponse,
    policy: Policy,
) -> TransformTransactionEvent:
    warning_actions = {"deny", "block", "redact"}
    confidence = (
        min((decision.confidence for decision in response.decisions), default=1.0)
        if response.decisions
        else 1.0
    )
    warnings = [
        f"{decision.entity_type}:{decision.action}"
        for decision in response.decisions
        if decision.action in warning_actions
    ]
    return TransformTransactionEvent(
        tenant_id=request.tenant_id,
        app_id=request.app_id,
        session_id=request.session_id,
        request_id=response.request_id,
        environment=request.environment,
        policy_id=response.audit_event.policy_id or policy.policy_id,
        policy_version=response.audit_event.policy_version or policy.version,
        policy_source=_policy_source(response.audit_event.metadata.get("policy_source")),
        input_fingerprint=fingerprint_text(request.text),
        transformed_preview=response.transformed_text,
        detections=[
            DetectionSummary(
                entity_type=detection.entity_type,
                start=detection.start,
                end=detection.end,
                confidence=detection.confidence,
            )
            for detection in response.detections
        ],
        mappings=[
            MappingSummary(token=mapping.token, entity_type=mapping.entity_type)
            for mapping in response.mappings
        ],
        decisions=[
            PolicyDecisionSummary(
                entity_type=decision.entity_type,
                action=decision.action,
                policy_id=decision.policy_id,
                policy_version=decision.policy_version,
                policy_source=decision.policy_source,
                rule_id=decision.rule_id,
                reason=decision.reason,
                token=decision.token,
                token_strategy=decision.token_strategy,
                app_id=decision.app_id,
                role=decision.role,
                purpose=decision.purpose,
                direction=decision.direction,
                environment=decision.environment,
                matched_constraints=decision.matched_constraints,
                confidence=decision.confidence,
            )
            for decision in response.decisions
        ],
        warnings=warnings,
        scores=ReviewScores(
            detection_confidence=confidence,
            policy_coverage=1.0 if response.decisions else 0.0,
            leakage_risk=0.8 if warnings else 0.0,
            unresolved_token_count=0,
            explanations=warnings or ["transform completed without policy warnings"],
        ),
    )


def _token_for(entity_type: str, index: int) -> str:
    prefix = TOKEN_PREFIXES.get(entity_type, entity_type.upper())
    return f"{prefix}_{index}"


def _policy_source(
    value: str | None,
) -> Literal["enterprise", "cache", "fallback", "local", "package", "unknown"]:
    allowed = {"enterprise", "cache", "fallback", "local", "package", "unknown"}
    if value in allowed:
        return cast(
            Literal["enterprise", "cache", "fallback", "local", "package", "unknown"], value
        )
    return "unknown"


def _replacement_for(
    detection: EntityDetection,
    index: int,
    decision: PolicyDecision,
    *,
    request: TransformRequest,
) -> str:
    action = decision.action
    if action == "preserve":
        return detection.text
    if action == "tokenize":
        prefix = decision.token_prefix or TOKEN_PREFIXES.get(
            detection.entity_type, detection.entity_type.upper()
        )
        if decision.token_strategy == "session_stable":
            digest = _stable_digest(
                request.tenant_id,
                request.app_id,
                request.session_id,
                detection.entity_type,
                detection.text,
            )
            return f"{prefix}_{digest}"
        if decision.token_strategy == "tenant_stable":
            digest = _stable_digest(
                request.tenant_id,
                detection.entity_type,
                detection.text,
            )
            return f"{prefix}_{digest}"
        if decision.token_strategy == "random_opaque":
            return f"{prefix}_{uuid4().hex[:12].upper()}"
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


def _stable_digest(*parts: str) -> str:
    normalized = "\x1f".join(parts)
    return sha256(normalized.encode("utf-8")).hexdigest()[:12].upper()


def _remove_overlaps(detections: list[EntityDetection]) -> list[EntityDetection]:
    accepted: list[EntityDetection] = []
    occupied_until = -1
    for detection in detections:
        if detection.start < occupied_until:
            continue
        accepted.append(detection)
        occupied_until = detection.end
    return accepted
