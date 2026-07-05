import importlib
import os
from dataclasses import dataclass
from time import monotonic
from typing import Literal, Protocol, cast

from prism_policy_runtime.policy import DEFAULT_POLICY, Policy, load_policy


class PolicyProvider(Protocol):
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        """Return a policy for tenant/app, or None to use the default fallback."""


class DefaultPolicyProvider:
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        policy_path = os.getenv("PRISM_POLICY_PATH")
        if policy_path:
            return load_policy(policy_path)
        return DEFAULT_POLICY


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
