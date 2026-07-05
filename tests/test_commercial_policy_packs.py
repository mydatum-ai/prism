from pathlib import Path

from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_policy_runtime import load_policy
from prism_rehydration import rehydrate
from prism_transformers import transform
from prism_vault_core import InMemoryVault

COMMERCIAL_PACKS = [
    "civic_reports",
    "customer_support",
    "finance",
    "healthcare",
    "hr",
]


def test_p16_commercial_policy_packs_load() -> None:
    for pack in COMMERCIAL_PACKS:
        policy = load_policy(Path("examples/policies/commercial") / f"{pack}.yaml")

        assert policy.domain == pack
        assert policy.rules


def test_p16_commercial_policy_packs_transform_and_rehydrate() -> None:
    sample = "Maria Santos emailed maria@example.com about INV-1001 and called 555-010-0000"

    for pack in COMMERCIAL_PACKS:
        vault = InMemoryVault()
        policy = load_policy(Path("examples/policies/commercial") / f"{pack}.yaml")
        transformed = transform(
            TransformRequest(
                tenant_id="tenant_dev",
                app_id=pack,
                session_id="session_1",
                text=sample,
            ),
            vault=vault,
            policy=policy,
        )

        assert "Maria Santos" not in transformed.transformed_text
        assert transformed.decisions

        rehydrated = rehydrate(
            RehydrateRequest(
                tenant_id="tenant_dev",
                app_id=pack,
                session_id="session_1",
                text=transformed.transformed_text,
                roles=["enterprise_admin", "finance_admin", "clinician", "hr_admin"],
            ),
            vault=vault,
            policy=policy,
        )

        assert rehydrated.diagnostics
