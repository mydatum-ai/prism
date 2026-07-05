import httpx
import pytest
from prism_compiler.schemas import EntityDetection
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    PolicyDecisionContext,
    PublishedPolicyProvider,
    clear_policy_cache,
    decide,
    load_policy,
    load_policy_provider,
    resolve_policy,
    resolve_policy_with_metadata,
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


def test_phase_p17_policy_resolution_reports_enterprise_source(
    monkeypatch: MonkeyPatch,
) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    provider = SequencePolicyProvider([policy_with_prefix("tenant_dev", "pulse", "FIRST")])

    resolution = resolve_policy_with_metadata("tenant_dev", "pulse", provider=provider)

    assert resolution.source == "enterprise"
    assert resolution.cache_hit is False
    assert resolution.cache_stale is False
    assert resolution.provider_latency_ms >= 0


def test_phase_p17_policy_resolution_reports_cache_hit(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    provider = SequencePolicyProvider([policy_with_prefix("tenant_dev", "pulse", "FIRST")])

    resolve_policy_with_metadata("tenant_dev", "pulse", provider=provider)
    cached = resolve_policy_with_metadata("tenant_dev", "pulse", provider=provider)

    assert cached.source == "cache"
    assert cached.cache_hit is True
    assert cached.cache_stale is False
    assert cached.provider_latency_ms == 0


def test_phase_p17_policy_resolution_reports_fallback(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")

    resolution = resolve_policy_with_metadata(
        "tenant_dev",
        "pulse",
        provider=SequencePolicyProvider([None]),
    )

    assert resolution.policy == DEFAULT_POLICY
    assert resolution.source == "fallback"
    assert resolution.cache_hit is False
    assert resolution.cache_stale is False


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

    resolution = resolve_policy_with_metadata("tenant_dev", "pulse", provider=provider)

    assert resolution.policy.rules[0].token_prefix == "CACHED"
    assert resolution.source == "cache"
    assert resolution.cache_hit is True
    assert resolution.cache_stale is True
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


def test_p16_conflict_resolution_deny_wins() -> None:
    policy = Policy.model_validate(
        {
            "domain": "conflict",
            "rules": [
                {
                    "rule_id": "high_priority_tokenize",
                    "entity_type": "email",
                    "action": "tokenize",
                    "priority": 100,
                    "token_prefix": "EMAIL",
                },
                {
                    "rule_id": "deny_email",
                    "entity_type": "email",
                    "action": "deny",
                    "priority": 1,
                },
            ],
        }
    )

    decision = decide(
        policy,
        EntityDetection(text="john@email.com", entity_type="email", start=0, end=14),
    )

    assert decision.action == "deny"
    assert decision.rule_id == "deny_email"
    assert decision.reason == "conflict_resolved"


def test_p16_conflict_resolution_uses_priority_then_specificity_then_order() -> None:
    detection = EntityDetection(
        text="Maria Santos",
        entity_type="person",
        start=0,
        end=12,
        metadata={"role": "reporter"},
    )
    policy = Policy.model_validate(
        {
            "domain": "conflict",
            "rules": [
                {
                    "rule_id": "first_equal_priority",
                    "entity_type": "person",
                    "action": "tokenize",
                    "priority": 10,
                    "token_prefix": "FIRST",
                },
                {
                    "rule_id": "role_specific",
                    "entity_type": "person",
                    "role": "reporter",
                    "action": "tokenize",
                    "priority": 10,
                    "token_prefix": "REPORTER",
                },
                {
                    "rule_id": "highest_priority",
                    "entity_type": "person",
                    "role": "reporter",
                    "action": "tokenize",
                    "priority": 20,
                    "token_prefix": "HIGH",
                },
            ],
        }
    )

    decision = decide(policy, detection)

    assert decision.rule_id == "highest_priority"
    assert decision.token_prefix == "HIGH"

    lower_priority_policy = policy.model_copy(update={"rules": policy.rules[:2]})
    lower_priority_decision = decide(lower_priority_policy, detection)

    assert lower_priority_decision.rule_id == "role_specific"
    assert lower_priority_decision.token_prefix == "REPORTER"


def test_p16_rule_matching_uses_context_and_confidence_threshold() -> None:
    policy = Policy.model_validate(
        {
            "domain": "context",
            "rules": [
                {
                    "rule_id": "analytics_app_rule",
                    "entity_type": "email",
                    "action": "redact",
                    "app_id": "analytics",
                    "purpose": "reporting",
                    "direction": "outbound",
                    "environment": "prod",
                    "min_confidence": 0.9,
                },
                {
                    "rule_id": "fallback_email",
                    "entity_type": "email",
                    "action": "mask",
                },
            ],
        }
    )
    detection = EntityDetection(
        text="john@email.com",
        entity_type="email",
        start=0,
        end=14,
        confidence=0.95,
    )

    decision = decide(
        policy,
        detection,
        PolicyDecisionContext(
            app_id="analytics",
            purpose="reporting",
            direction="outbound",
            environment="prod",
        ),
    )

    assert decision.rule_id == "analytics_app_rule"
    assert decision.action == "redact"

    low_confidence = detection.model_copy(update={"confidence": 0.5})
    fallback = decide(
        policy,
        low_confidence,
        PolicyDecisionContext(
            app_id="analytics",
            purpose="reporting",
            direction="outbound",
            environment="prod",
        ),
    )

    assert fallback.rule_id == "fallback_email"
    assert fallback.action == "mask"


def test_phase_p15_default_policy_provider_preserves_current_policy() -> None:
    policy = resolve_policy("tenant_dev", "pulse")

    assert policy == DEFAULT_POLICY


def test_phase_p15_import_string_policy_provider_override() -> None:
    provider = load_policy_provider("prism_policy_runtime.testing:StaticPolicyProvider")

    policy = resolve_policy("tenant_dev", "pulse", provider=provider)

    assert policy.domain == "pulse"
    assert policy.rules[0].token_prefix == "TEST"


def test_phase_p18_legacy_enterprise_provider_import_uses_builtin_provider() -> None:
    provider = load_policy_provider(
        "prism_enterprise_dashboard.policy_provider:PublishedPolicyProvider"
    )

    assert isinstance(provider, PublishedPolicyProvider)


def test_phase_p18_builtin_published_policy_provider_calls_enterprise_runtime() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Prism-Tenant"] == "tenant_dev"
        assert request.headers["X-Prism-API-Key"] == "dev"
        assert request.url.path == "/tenants/tenant_dev/policies/active/pulse/runtime"
        return httpx.Response(
            200,
            json={
                "domain": "pulse",
                "version": "7",
                "rules": [{"entity_type": "person", "action": "tokenize", "token_prefix": "LIVE"}],
            },
        )

    provider = PublishedPolicyProvider(
        base_url="http://enterprise.test",
        api_key="dev",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    policy = provider.resolve_policy("tenant_dev", "pulse")

    assert policy is not None
    assert policy.version == "7"
    assert policy.rules[0].token_prefix == "LIVE"


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
