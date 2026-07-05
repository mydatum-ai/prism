import pytest
from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_policy_packs import (
    PolicyPackage,
    PolicyPackageExample,
    UnknownPolicyPackageError,
    list_policy_packages,
    load_policy_package,
)
from prism_policy_runtime import PolicyRule
from prism_rehydration import rehydrate
from prism_transformers import transform
from prism_vault_core import InMemoryVault

REQUIRED_PACKAGE_IDS = {
    "healthcare.default",
    "government.civic-services",
    "community.pulse",
    "cybersecurity.logsentry",
    "personal.default",
    "financial.default",
    "customer-support.default",
    "hr.default",
}


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
    assert {package.package_id for package in list_policy_packages()} == REQUIRED_PACKAGE_IDS


def test_p17_unknown_policy_package_fails_clearly() -> None:
    with pytest.raises(UnknownPolicyPackageError, match="Unknown policy package"):
        load_policy_package("missing.package")


def test_p17_policy_packages_transform_and_rehydrate_with_allowed_roles() -> None:
    sample = "Maria Santos emailed maria@example.com about INV-1001 and called 555-010-0000"

    for package_id in REQUIRED_PACKAGE_IDS:
        package = load_policy_package(package_id)
        policy = package.to_policy()
        vault = InMemoryVault()
        transformed = transform(
            TransformRequest(
                tenant_id="tenant_dev",
                app_id=package.package_id,
                session_id="session_1",
                text=sample,
            ),
            vault=vault,
            policy=policy,
        )

        assert transformed.decisions
        for expected in package.examples[0].expected_transform_contains:
            assert expected in transformed.transformed_text

        rehydrated = rehydrate(
            RehydrateRequest(
                tenant_id="tenant_dev",
                app_id=package.package_id,
                session_id="session_1",
                text=transformed.transformed_text,
                roles=package.examples[0].expected_rehydration_roles,
            ),
            vault=vault,
            policy=policy,
        )

        assert rehydrated.diagnostics


def test_p17_policy_packages_block_unapproved_rehydration_roles() -> None:
    package = load_policy_package("financial.default")
    policy = package.to_policy()
    vault = InMemoryVault()
    transformed = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id=package.package_id,
            session_id="session_1",
            text="Maria Santos emailed maria@example.com about INV-1001.",
        ),
        vault=vault,
        policy=policy,
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_dev",
            app_id=package.package_id,
            session_id="session_1",
            text=transformed.transformed_text,
            roles=["viewer"],
        ),
        vault=vault,
        policy=policy,
    )

    assert any(item.status == "policy_blocked" for item in response.diagnostics)
