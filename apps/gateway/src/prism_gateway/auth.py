import os
import secrets
from dataclasses import dataclass
from typing import Any, cast

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from fastapi import Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from prism_gateway.mydatum_security import (
    pkce_challenge,
    public_account,
    validate_claims,
    validate_userinfo_subject,
)


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    api_key_id: str
    auth_method: str = "api_key"


oauth = OAuth()


def setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def mydatum_enabled() -> bool:
    return all(
        setting(name)
        for name in (
            "MYDATUM_ISSUER",
            "MYDATUM_CLIENT_ID",
            "MYDATUM_CLIENT_SECRET",
            "MYDATUM_REDIRECT_URI",
        )
    )


def mydatum_provider() -> Any:
    if not mydatum_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="mydatum_not_configured"
        )
    issuer = setting("MYDATUM_ISSUER").rstrip("/")
    return oauth.create_client("mydatum") or oauth.register(
        name="mydatum",
        client_id=setting("MYDATUM_CLIENT_ID"),
        client_secret=setting("MYDATUM_CLIENT_SECRET"),
        server_metadata_url=f"{issuer}/.well-known/openid-configuration",
        client_kwargs={"scope": setting("MYDATUM_SCOPES", "openid email")},
    )


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
    request: Request,
    x_prism_tenant: str | None = Header(default=None),
    x_prism_api_key: str | None = Header(default=None),
) -> Principal:
    keys = configured_api_keys()
    if x_prism_tenant and x_prism_api_key:
        tenant_id = keys.get(x_prism_api_key)
        if keys and tenant_id != x_prism_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="tenant_not_allowed",
            )
        if not keys:
            tenant_id = x_prism_tenant
        assert tenant_id is not None
        return Principal(tenant_id=tenant_id, api_key_id=x_prism_api_key[:8])

    account = request.session.get("account")
    if isinstance(account, dict) and account.get("tenant_id"):
        return Principal(
            tenant_id=str(account["tenant_id"]),
            api_key_id=str(account.get("subject", "session"))[:8],
            auth_method="mydatum",
        )

    if not keys:
        return Principal(tenant_id=x_prism_tenant or "tenant_dev", api_key_id="dev")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not_authenticated",
    )


def require_tenant(principal: Principal, tenant_id: str) -> None:
    if principal.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_scope_mismatch",
        )


async def login(request: Request) -> RedirectResponse:
    verifier = secrets.token_urlsafe(64)
    nonce = secrets.token_urlsafe(32)
    request.session["pkce_verifier"] = verifier
    request.session["oidc_nonce"] = nonce
    return cast(
        RedirectResponse,
        await mydatum_provider().authorize_redirect(
            request,
            setting("MYDATUM_REDIRECT_URI"),
            nonce=nonce,
            code_challenge=pkce_challenge(verifier),
            code_challenge_method="S256",
        ),
    )


async def callback(request: Request) -> RedirectResponse:
    verifier = str(request.session.pop("pkce_verifier", ""))
    nonce = str(request.session.pop("oidc_nonce", ""))
    if not verifier or not nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_or_replayed_authorization_transaction",
        )
    try:
        token = await mydatum_provider().authorize_access_token(request, code_verifier=verifier)
        claims = cast(dict[str, Any], token.get("userinfo") or token.get("id_token_claims") or {})
        userinfo = cast(dict[str, Any] | None, token.get("userinfo"))
        validate_claims(
            claims,
            issuer=setting("MYDATUM_ISSUER"),
            client_id=setting("MYDATUM_CLIENT_ID"),
            nonce=nonce,
        )
        validate_userinfo_subject(claims, userinfo)
    except Exception as error:
        raise HTTPException(status_code=400, detail="authentication_failed") from error
    request.session.clear()
    request.session["account"] = public_account(
        claims,
        setting("MYDATUM_ISSUER"),
        setting("PRISM_DEFAULT_TENANT", "tenant_dev"),
    )
    return RedirectResponse(
        setting("PRISM_AUTH_SUCCESS_REDIRECT", "http://127.0.0.1:3004"), status_code=303
    )


def me(request: Request) -> dict[str, object]:
    account = request.session.get("account")
    if not isinstance(account, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return {"authenticated": True, "account": account}


def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({}, status_code=204)
