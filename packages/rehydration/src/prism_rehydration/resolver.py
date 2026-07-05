import re
from typing import Literal
from uuid import uuid4

from prism_compiler.schemas import (
    AuditEvent,
    RehydrateRequest,
    RehydrateResponse,
    RehydrationDiagnostic,
)
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    RehydrationDecisionContext,
    decide_rehydration,
)
from prism_transaction_events import (
    RehydrationDecisionSummary,
    RehydrationTransactionEvent,
    ReviewScores,
    TransactionEventSink,
    emit_transaction_event,
)
from prism_transaction_events.events import fingerprint_text
from prism_vault_core import GLOBAL_VAULT, InMemoryVault, VaultKey

TOKEN_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]*_[A-Z0-9]+\b")


def rehydrate(
    request: RehydrateRequest,
    vault: InMemoryVault = GLOBAL_VAULT,
    policy: Policy = DEFAULT_POLICY,
    transaction_sink: TransactionEventSink | None = None,
) -> RehydrateResponse:
    request_id = str(uuid4())
    diagnostics: list[RehydrationDiagnostic] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        key = VaultKey(request.tenant_id, request.app_id, request.session_id, token)
        record = vault.get_record(key, include_expired=True)
        if record is None:
            status: Literal["missing_mapping", "wrong_scope"] = "missing_mapping"
            reason = "mapping_not_found"
            if hasattr(vault, "token_exists_outside_scope") and vault.token_exists_outside_scope(
                key
            ):
                status = "wrong_scope"
                reason = "token_found_outside_requested_scope"
            diagnostics.append(RehydrationDiagnostic(token=token, status=status, reason=reason))
            return token
        if record.expired:
            diagnostics.append(
                RehydrationDiagnostic(
                    token=token,
                    entity_type=record.entity_type,
                    status="expired",
                    reason="mapping_expired",
                )
            )
            return token
        if (
            request.allowed_entity_types is not None
            and record.entity_type not in request.allowed_entity_types
        ):
            diagnostics.append(
                RehydrationDiagnostic(
                    token=token,
                    entity_type=record.entity_type,
                    status="denied",
                    reason="entity_type_not_allowed",
                )
            )
            return token
        decision = decide_rehydration(
            policy,
            entity_type=record.entity_type,
            created_at=record.created_at,
            context=RehydrationDecisionContext(
                app_id=request.app_id,
                roles=request.roles,
                purpose=request.purpose,
                direction=request.direction,
                environment=request.environment,
            ),
        )
        if not decision.allowed:
            diagnostics.append(
                RehydrationDiagnostic(
                    token=token,
                    entity_type=record.entity_type,
                    status="policy_blocked",
                    reason=decision.reason,
                )
            )
            return token
        diagnostics.append(
            RehydrationDiagnostic(
                token=token,
                entity_type=record.entity_type,
                status="allowed",
                reason=decision.reason,
            )
        )
        return record.value

    audit_event = AuditEvent(
        event_type="rehydrate",
        tenant_id=request.tenant_id,
        app_id=request.app_id,
        session_id=request.session_id,
        request_id=request_id,
    )
    text = TOKEN_PATTERN.sub(replace, request.text)
    audit_event.metadata.update(
        {
            "token_count": str(len(diagnostics)),
            "allowed_count": str(sum(1 for item in diagnostics if item.status == "allowed")),
            "blocked_count": str(sum(1 for item in diagnostics if item.status != "allowed")),
        }
    )
    response = RehydrateResponse(
        request_id=request_id,
        text=text,
        diagnostics=diagnostics,
        audit_event=audit_event,
    )
    emit_transaction_event(
        _transaction_event_for_rehydrate(request, response, policy),
        transaction_sink,
    )
    return response


def _transaction_event_for_rehydrate(
    request: RehydrateRequest,
    response: RehydrateResponse,
    policy: Policy,
) -> RehydrationTransactionEvent:
    blocked = [item for item in response.diagnostics if item.status != "allowed"]
    return RehydrationTransactionEvent(
        tenant_id=request.tenant_id,
        app_id=request.app_id,
        session_id=request.session_id,
        request_id=response.request_id,
        environment=request.environment,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        input_fingerprint=fingerprint_text(request.text),
        requested_text_preview=request.text,
        rehydrated_preview=response.text,
        requester_roles=request.roles,
        purpose=request.purpose,
        decisions=[
            RehydrationDecisionSummary(
                token=item.token,
                entity_type=item.entity_type,
                allowed=item.status == "allowed",
                reason=item.reason,
                status=item.status,
            )
            for item in response.diagnostics
        ],
        warnings=[f"{item.entity_type or 'unknown'}:{item.status}" for item in blocked],
        scores=ReviewScores(
            rehydration_risk=0.8 if blocked else 0.0,
            unresolved_token_count=len(blocked),
            explanations=[f"{item.token}:{item.status}:{item.reason}" for item in blocked]
            or ["rehydration completed without blocked tokens"],
        ),
    )
