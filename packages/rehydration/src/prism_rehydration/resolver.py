import re
from uuid import uuid4

from prism_compiler.schemas import AuditEvent, RehydrateRequest, RehydrateResponse
from prism_vault_core import GLOBAL_VAULT, InMemoryVault, VaultKey

TOKEN_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]*_[A-Z0-9]+\b")


def rehydrate(request: RehydrateRequest, vault: InMemoryVault = GLOBAL_VAULT) -> RehydrateResponse:
    request_id = str(uuid4())

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        value = vault.get(VaultKey(request.tenant_id, request.app_id, request.session_id, token))
        return value or token

    audit_event = AuditEvent(
        event_type="rehydrate",
        tenant_id=request.tenant_id,
        app_id=request.app_id,
        session_id=request.session_id,
        request_id=request_id,
    )
    return RehydrateResponse(
        request_id=request_id,
        text=TOKEN_PATTERN.sub(replace, request.text),
        audit_event=audit_event,
    )
