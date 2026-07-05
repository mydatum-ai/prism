import importlib
import logging
import os
from dataclasses import dataclass
from time import monotonic
from typing import Literal, Protocol, cast

import httpx

from prism_policy_runtime.policy import DEFAULT_POLICY, Policy, load_policy

logger = logging.getLogger(__name__)
ENTERPRISE_PROVIDER_COMPAT_PATH = (
    "prism" + "_enterprise_dashboard.policy_provider:PublishedPolicyProvider"
)


class PolicyProvider(Protocol):
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        """Return a policy for tenant/app, or None to use the default fallback."""


class DefaultPolicyProvider:
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        policy_path = os.getenv("PRISM_POLICY_PATH")
        if policy_path:
            return load_policy(policy_path)
        return DEFAULT_POLICY


class PublishedPolicyProvider:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        configured_base_url = (
            base_url if base_url is not None else os.getenv("PRISM_ENTERPRISE_POLICY_API_URL", "")
        )
        self.base_url = configured_base_url.rstrip("/")
        self.api_key = (
            api_key if api_key is not None else os.getenv("PRISM_ENTERPRISE_POLICY_API_KEY", "")
        )
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("PRISM_ENTERPRISE_POLICY_TIMEOUT_SECONDS", "2")
        )
        self.client = client

    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        if not self.base_url or not self.api_key:
            return None
        path = f"/tenants/{tenant_id}/policies/active/{app_id}/runtime"
        headers = {"X-Prism-Tenant": tenant_id, "X-Prism-API-Key": self.api_key}
        try:
            if self.client is not None:
                response = self.client.get(f"{self.base_url}{path}", headers=headers)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.get(f"{self.base_url}{path}", headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return Policy.model_validate(response.json())
        except Exception as error:
            logger.warning(
                "event=published_policy_provider.resolve_failed "
                "tenant_id=%s app_id=%s error_type=%s",
                tenant_id,
                app_id,
                type(error).__name__,
            )
            return None


@dataclass
class CachedPolicy:
    policy: Policy
    expires_at: float
    source: str


PolicySource = Literal["enterprise", "cache", "fallback", "local"]


@dataclass(frozen=True)
class PolicyResolution:
    policy: Policy
    source: PolicySource
    cache_hit: bool
    cache_stale: bool
    provider_latency_ms: float


_POLICY_CACHE: dict[tuple[str, str, str], CachedPolicy] = {}


def _cache_ttl_seconds() -> float:
    raw_ttl = os.getenv("PRISM_POLICY_CACHE_TTL_SECONDS", "30").strip()
    try:
        return float(raw_ttl)
    except ValueError as error:
        raise ValueError("PRISM_POLICY_CACHE_TTL_SECONDS must be numeric") from error


def _provider_cache_key(provider: PolicyProvider | None) -> str:
    if provider is None:
        return (os.getenv("PRISM_POLICY_PROVIDER") or "default").strip() or "default"
    return f"{provider.__class__.__module__}.{provider.__class__.__qualname__}:{id(provider)}"


def clear_policy_cache(tenant_id: str | None = None, app_id: str | None = None) -> int:
    removed = 0
    for key in list(_POLICY_CACHE):
        _, cached_tenant_id, cached_app_id = key
        if tenant_id is not None and tenant_id != cached_tenant_id:
            continue
        if app_id is not None and app_id != cached_app_id:
            continue
        del _POLICY_CACHE[key]
        removed += 1
    return removed


def load_policy_provider(path: str | None = None) -> PolicyProvider:
    provider_path = (path or os.getenv("PRISM_POLICY_PROVIDER") or "default").strip()
    if not provider_path or provider_path == "default":
        return DefaultPolicyProvider()
    if provider_path == ENTERPRISE_PROVIDER_COMPAT_PATH:
        return PublishedPolicyProvider()
    module_name, separator, attribute = provider_path.partition(":")
    if not separator:
        module_name, separator, attribute = provider_path.rpartition(".")
    if not module_name or not attribute:
        raise ValueError(f"Invalid policy provider import path: {provider_path}")
    try:
        module = importlib.import_module(module_name)
        provider_factory = getattr(module, attribute)
        provider = provider_factory() if isinstance(provider_factory, type) else provider_factory
    except Exception as error:
        raise ValueError(f"Unable to load policy provider: {provider_path}") from error
    if not hasattr(provider, "resolve_policy"):
        raise ValueError(f"Policy provider missing resolve_policy: {provider_path}")
    return cast(PolicyProvider, provider)


def resolve_policy_with_metadata(
    tenant_id: str,
    app_id: str,
    provider: PolicyProvider | None = None,
    fallback: Policy = DEFAULT_POLICY,
) -> PolicyResolution:
    ttl_seconds = _cache_ttl_seconds()
    cache_key = (_provider_cache_key(provider), tenant_id, app_id)
    cached = _POLICY_CACHE.get(cache_key)
    now = monotonic()
    if ttl_seconds > 0 and cached is not None and cached.expires_at > now:
        return PolicyResolution(
            policy=cached.policy,
            source="cache",
            cache_hit=True,
            cache_stale=False,
            provider_latency_ms=0.0,
        )

    active_provider = provider or load_policy_provider()
    provider_started = monotonic()
    policy = active_provider.resolve_policy(tenant_id, app_id)
    provider_latency_ms = (monotonic() - provider_started) * 1000
    if policy is not None:
        source: PolicySource = (
            "local" if isinstance(active_provider, DefaultPolicyProvider) else "enterprise"
        )
        if ttl_seconds > 0:
            _POLICY_CACHE[cache_key] = CachedPolicy(
                policy=policy, expires_at=now + ttl_seconds, source=source
            )
        return PolicyResolution(
            policy=policy,
            source=source,
            cache_hit=False,
            cache_stale=False,
            provider_latency_ms=provider_latency_ms,
        )
    if cached is not None:
        return PolicyResolution(
            policy=cached.policy,
            source="cache",
            cache_hit=True,
            cache_stale=True,
            provider_latency_ms=provider_latency_ms,
        )
    return PolicyResolution(
        policy=fallback,
        source="fallback",
        cache_hit=False,
        cache_stale=False,
        provider_latency_ms=provider_latency_ms,
    )


def resolve_policy(
    tenant_id: str,
    app_id: str,
    provider: PolicyProvider | None = None,
    fallback: Policy = DEFAULT_POLICY,
) -> Policy:
    return resolve_policy_with_metadata(
        tenant_id,
        app_id,
        provider=provider,
        fallback=fallback,
    ).policy
