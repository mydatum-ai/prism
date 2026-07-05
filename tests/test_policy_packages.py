import pytest
from prism_policy_packs import (
    PolicyPackage,
    PolicyPackageExample,
    UnknownPolicyPackageError,
    list_policy_packages,
    load_policy_package,
)
from prism_policy_runtime import PolicyRule


def test_p17_policy_package_contract_converts_to_runtime_policy() -> None:
    package = PolicyPackage(
        package_id="personal.default",
        name="Personal default",
        version="1.0.0",
        family="personal",
        intended_use="Personal productivity prompts",
        risk_level="medium",
        supported_entity_types=["person", "email"],
        rules=[
            PolicyRule(
                rule_id="personal_name",
                entity_type="person",
                action="tokenize",
                token_prefix="PERSON",
            )
        ],
        examples=[
            PolicyPackageExample(
                name="contact",
                prompt="Maria emailed maria@example.com",
                expected_transform_contains=["PERSON_1"],
                expected_rehydration_roles=["owner"],
            )
        ],
    )

    policy = package.to_policy()

    assert policy.domain == "personal.default"
    assert policy.version == "1.0.0"
    assert policy.rules[0].rule_id == "personal_name"


def test_p17_policy_package_discovery_contract_is_stable() -> None:
    assert list_policy_packages() == []


def test_p17_unknown_policy_package_fails_clearly() -> None:
    with pytest.raises(UnknownPolicyPackageError, match="Unknown policy package"):
        load_policy_package("missing.package")
