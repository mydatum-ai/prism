import pytest
from prism_compiler.schemas import EntityDetection
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    decide,
    load_policy,
    load_policy_provider,
    resolve_policy,
)


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
