import base64
import hashlib
import hmac
import time
from typing import Any


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def validate_claims(
    claims: dict[str, Any],
    *,
    issuer: str,
    client_id: str,
    nonce: str,
    now: int | None = None,
) -> dict[str, Any]:
    current_time = int(time.time()) if now is None else now
    if claims.get("iss") != issuer.rstrip("/"):
        raise ValueError("issuer validation failed")
    audience = claims.get("aud", [])
    audience = [audience] if isinstance(audience, str) else audience
    if client_id not in audience:
        raise ValueError("audience validation failed")
    if not isinstance(claims.get("exp"), int) or claims["exp"] <= current_time:
        raise ValueError("expiry validation failed")
    if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise ValueError("nonce validation failed")
    if not claims.get("sub"):
        raise ValueError("subject validation failed")
    return claims


def validate_userinfo_subject(id_claims: dict[str, Any], userinfo: dict[str, Any] | None) -> None:
    if userinfo and not hmac.compare_digest(str(id_claims["sub"]), str(userinfo.get("sub", ""))):
        raise ValueError("userinfo subject validation failed")


def external_identity_key(issuer: str, subject: str) -> str:
    return hashlib.sha256(f"{issuer.rstrip('/')}\0{subject}".encode()).hexdigest()


def public_account(claims: dict[str, Any], issuer: str, default_tenant: str) -> dict[str, Any]:
    tenant_id = str(claims.get("tenant_id") or claims.get("mydatum_tenant") or default_tenant)
    roles = claims.get("roles", [])
    return {
        "external_identity_key": external_identity_key(issuer, str(claims["sub"])),
        "subject": str(claims["sub"]),
        "tenant_id": tenant_id,
        "roles": roles if isinstance(roles, list) else [],
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified") is True,
        "name": claims.get("name"),
    }
