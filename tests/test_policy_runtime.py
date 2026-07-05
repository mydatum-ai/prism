from prism_compiler.schemas import EntityDetection
from prism_policy_runtime import Policy, decide, load_policy


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
