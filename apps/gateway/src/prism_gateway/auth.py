import logging
import os
import secrets
from dataclasses import dataclass
from typing import Any, cast

import httpx
from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from authlib.jose import JsonWebKey, jwt  # type: ignore[import-untyped]
from fastapi import Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response

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


logger = logging.getLogger(__name__)
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
    internal_base_url = setting("MYDATUM_INTERNAL_BASE_URL")
    if not internal_base_url and setting("MYDATUM_DISCOVERY_URL"):
        internal_base_url = setting("MYDATUM_DISCOVERY_URL").removesuffix(
            "/.well-known/openid-configuration"
        )
    server_base_url = (internal_base_url or issuer).rstrip("/")
    return oauth.create_client("mydatum") or oauth.register(
        name="mydatum",
        client_id=setting("MYDATUM_CLIENT_ID"),
        client_secret=setting("MYDATUM_CLIENT_SECRET"),
        authorize_url=f"{issuer}/o/authorize",
        access_token_url=f"{server_base_url}/o/token",
        userinfo_endpoint=f"{server_base_url}/o/userinfo",
        jwks_uri=f"{server_base_url}/.well-known/jwks.json",
        client_kwargs={"scope": setting("MYDATUM_SCOPES", "openid email")},
    )


async def id_token_claims(token: dict[str, Any]) -> dict[str, Any]:
    claims = token.get("userinfo") or token.get("id_token_claims")
    if isinstance(claims, dict) and claims:
        return cast(dict[str, Any], claims)

    id_token = token.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        return {}

    issuer = setting("MYDATUM_ISSUER").rstrip("/")
    server_base_url = (
        setting("MYDATUM_INTERNAL_BASE_URL")
        or setting("MYDATUM_DISCOVERY_URL").removesuffix("/.well-known/openid-configuration")
        or issuer
    ).rstrip("/")
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{server_base_url}/.well-known/jwks.json")
        response.raise_for_status()
    key_set = JsonWebKey.import_key_set(response.json())
    decoded = jwt.decode(id_token, key_set)
    return dict(decoded)


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
        claims = await id_token_claims(cast(dict[str, Any], token))
        userinfo = cast(dict[str, Any] | None, token.get("userinfo"))
        validate_claims(
            claims,
            issuer=setting("MYDATUM_ISSUER"),
            client_id=setting("MYDATUM_CLIENT_ID"),
            nonce=nonce,
        )
        validate_userinfo_subject(claims, userinfo)
    except Exception as error:
        logger.warning(
            "event=mydatum.callback_failed error_type=%s error=%s",
            type(error).__name__,
            str(error),
        )
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


def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
