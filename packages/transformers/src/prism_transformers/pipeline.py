from collections import Counter
from collections.abc import Iterable
from typing import Protocol
from uuid import uuid4

from prism_compiler.schemas import (
    AuditEvent,
    EntityDetection,
    TokenMapping,
    TransformRequest,
    TransformResponse,
)
from prism_detectors import EmailDetector, InvoiceDetector, PhoneDetector, SimpleNameDetector
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


def transform(request: TransformRequest, vault: InMemoryVault = GLOBAL_VAULT) -> TransformResponse:
    request_id = str(uuid4())
    detections = detect_entities(request.text)
    counters: Counter[str] = Counter()
    mappings: list[TokenMapping] = []
    response_detections: list[EntityDetection] = []
    transformed_parts: list[str] = []
    cursor = 0
    transformed_cursor = 0

    for detection in detections:
        unchanged = request.text[cursor : detection.start]
        transformed_parts.append(unchanged)
        transformed_cursor += len(unchanged)
        counters[detection.entity_type] += 1
        token = _token_for(detection.entity_type, counters[detection.entity_type])
        transformed_parts.append(token)
        cursor = detection.end
        token_start = transformed_cursor
        transformed_cursor += len(token)

        vault.put(
            VaultKey(request.tenant_id, request.app_id, request.session_id, token),
            detection.text,
            entity_type=detection.entity_type,
            metadata={"request_id": request_id},
        )
        mappings.append(TokenMapping(token=token, entity_type=detection.entity_type))
        response_detections.append(
            EntityDetection(
                text=token,
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
        policy_id=request.policy_id,
    )
    return TransformResponse(
        request_id=request_id,
        transformed_text="".join(transformed_parts),
        detections=response_detections,
        mappings=mappings,
        audit_event=audit_event,
    )


def _token_for(entity_type: str, index: int) -> str:
    prefix = TOKEN_PREFIXES.get(entity_type, entity_type.upper())
    return f"{prefix}_{index}"


def _remove_overlaps(detections: list[EntityDetection]) -> list[EntityDetection]:
    accepted: list[EntityDetection] = []
    occupied_until = -1
    for detection in detections:
        if detection.start < occupied_until:
            continue
        accepted.append(detection)
        occupied_until = detection.end
    return accepted
