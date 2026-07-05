import importlib
import os
from typing import Protocol, cast

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


def resolve_policy(
    tenant_id: str,
    app_id: str,
    provider: PolicyProvider | None = None,
    fallback: Policy = DEFAULT_POLICY,
) -> Policy:
    active_provider = provider or load_policy_provider()
    policy = active_provider.resolve_policy(tenant_id, app_id)
    return policy or fallback
