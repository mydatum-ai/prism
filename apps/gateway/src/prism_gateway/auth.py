import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    api_key_id: str


def configured_api_keys() -> dict[str, str]:
    raw = os.getenv("PRISM_API_KEYS", "")
    pairs: dict[str, str] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        tenant_id, separator, api_key = item.partition(":")
        if separator and tenant_id and api_key:
            pairs[api_key] = tenant_id
    return pairs


def authenticate(
    x_prism_tenant: str | None = Header(default=None),
    x_prism_api_key: str | None = Header(default=None),
) -> Principal:
    keys = configured_api_keys()
    if not keys:
        return Principal(tenant_id=x_prism_tenant or "tenant_dev", api_key_id="dev")
    if not x_prism_tenant or not x_prism_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_prism_auth_headers",
        )
    tenant_id = keys.get(x_prism_api_key)
    if tenant_id != x_prism_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_not_allowed",
        )
    return Principal(tenant_id=tenant_id, api_key_id=x_prism_api_key[:8])


def require_tenant(principal: Principal, tenant_id: str) -> None:
    if principal.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_scope_mismatch",
        )
