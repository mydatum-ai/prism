import pytest
from prism_compiler.schemas import EntityDetection
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    clear_policy_cache,
    decide,
    load_policy,
    load_policy_provider,
    resolve_policy,
)
from pytest import MonkeyPatch


def test_phase_p16_policy_cache_reuses_provider_result(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    provider = SequencePolicyProvider(
        [
            policy_with_prefix("tenant_dev", "pulse", "FIRST"),
            policy_with_prefix("tenant_dev", "pulse", "SECOND"),
        ]
    )

    first = resolve_policy("tenant_dev", "pulse", provider=provider)
    second = resolve_policy("tenant_dev", "pulse", provider=provider)

    assert first.rules[0].token_prefix == "FIRST"
    assert second.rules[0].token_prefix == "FIRST"
    assert provider.calls == 1


def test_phase_p16_policy_cache_expires(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "10")
    current_time = 100.0
    monkeypatch.setattr("prism_policy_runtime.providers.monotonic", lambda: current_time)
    provider = SequencePolicyProvider(
        [
            policy_with_prefix("tenant_dev", "pulse", "FIRST"),
            policy_with_prefix("tenant_dev", "pulse", "SECOND"),
        ]
    )

    assert resolve_policy("tenant_dev", "pulse", provider=provider).rules[0].token_prefix == "FIRST"
    current_time = 111.0

    assert (
        resolve_policy("tenant_dev", "pulse", provider=provider).rules[0].token_prefix == "SECOND"
    )
    assert provider.calls == 2


def test_phase_p16_policy_cache_is_tenant_isolated(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    provider = TenantPolicyProvider()

    tenant_a = resolve_policy("tenant_a", "pulse", provider=provider)
    tenant_b = resolve_policy("tenant_b", "pulse", provider=provider)

    assert tenant_a.rules[0].token_prefix == "TENANT_A"
    assert tenant_b.rules[0].token_prefix == "TENANT_B"
    assert provider.calls == 2


def test_phase_p16_policy_cache_keeps_last_known_good(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "10")
    current_time = 100.0
    monkeypatch.setattr("prism_policy_runtime.providers.monotonic", lambda: current_time)
    provider = SequencePolicyProvider([policy_with_prefix("tenant_dev", "pulse", "CACHED"), None])

    assert (
        resolve_policy("tenant_dev", "pulse", provider=provider).rules[0].token_prefix == "CACHED"
    )
    current_time = 111.0

    assert (
        resolve_policy("tenant_dev", "pulse", provider=provider).rules[0].token_prefix == "CACHED"
    )
    assert provider.calls == 2


def test_phase_p16_policy_cache_can_be_cleared(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    provider = SequencePolicyProvider(
        [
            policy_with_prefix("tenant_dev", "pulse", "FIRST"),
            policy_with_prefix("tenant_dev", "pulse", "SECOND"),
        ]
    )

    resolve_policy("tenant_dev", "pulse", provider=provider)
    removed = clear_policy_cache(tenant_id="tenant_dev", app_id="pulse")
    policy = resolve_policy("tenant_dev", "pulse", provider=provider)

    assert removed == 1
    assert policy.rules[0].token_prefix == "SECOND"


def test_phase3_loads_yaml_policy() -> None:
    policy = load_policy("examples/policies/pulse.yaml")

    assert policy.domain == "pulse"
    assert policy.version == "1"
    assert policy.rules[0].token_prefix == "RESIDENT"


def test_phase3_policy_decides_matching_action() -> None:
    policy = Policy.model_validate(
        {
            "domain": "test",
            "version": "2",
            "rules": [{"entity_type": "email", "action": "mask"}],
        }
    )

    decision = decide(
        policy,
        EntityDetection(text="john@email.com", entity_type="email", start=0, end=14),
    )

    assert decision.action == "mask"
    assert decision.policy_id == "test"
    assert decision.policy_version == "2"


def test_phase_p15_default_policy_provider_preserves_current_policy() -> None:
    policy = resolve_policy("tenant_dev", "pulse")

    assert policy == DEFAULT_POLICY


def test_phase_p15_import_string_policy_provider_override() -> None:
    provider = load_policy_provider("prism_policy_runtime.testing:StaticPolicyProvider")

    policy = resolve_policy("tenant_dev", "pulse", provider=provider)

    assert policy.domain == "pulse"
    assert policy.rules[0].token_prefix == "TEST"


def test_phase_p15_invalid_policy_provider_path_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Invalid policy provider import path"):
        load_policy_provider("not-a-provider")


def policy_with_prefix(tenant_id: str, app_id: str, prefix: str) -> Policy:
    return Policy.model_validate(
        {
            "domain": app_id,
            "version": tenant_id,
            "rules": [{"entity_type": "person", "action": "tokenize", "token_prefix": prefix}],
        }
    )


class SequencePolicyProvider:
    def __init__(self, policies: list[Policy | None]) -> None:
        self.policies = policies
        self.calls = 0

    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        policy = self.policies[min(self.calls, len(self.policies) - 1)]
        self.calls += 1
        return policy


class TenantPolicyProvider:
    def __init__(self) -> None:
        self.calls = 0

    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        self.calls += 1
        return policy_with_prefix(tenant_id, app_id, tenant_id.upper())
