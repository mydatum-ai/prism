from typing import Literal

from prism_policy_runtime import Policy, PolicyRule
from pydantic import BaseModel, Field

PackageFamily = Literal[
    "healthcare",
    "government",
    "community",
    "cybersecurity",
    "personal",
    "financial",
    "customer_support",
    "hr",
]
RiskLevel = Literal["low", "medium", "high", "restricted"]


class UnknownPolicyPackageError(KeyError):
    pass


class PolicyPackageExample(BaseModel):
    name: str
    prompt: str
    expected_transform_contains: list[str] = Field(default_factory=list)
    expected_rehydration_roles: list[str] = Field(default_factory=list)


class PolicyPackage(BaseModel):
    package_id: str
    name: str
    version: str
    family: PackageFamily
    intended_use: str
    risk_level: RiskLevel
    supported_entity_types: list[str] = Field(default_factory=list)
    rules: list[PolicyRule] = Field(default_factory=list)
    examples: list[PolicyPackageExample] = Field(default_factory=list)
    supersedes: str | None = None

    def to_policy(self) -> Policy:
        return Policy(domain=self.package_id, version=self.version, rules=self.rules)


_PACKAGE_INDEX: dict[str, PolicyPackage] = {}


def list_policy_packages() -> list[PolicyPackage]:
    return sorted(_PACKAGE_INDEX.values(), key=lambda package: package.package_id)


def load_policy_package(package_id: str) -> PolicyPackage:
    try:
        return _PACKAGE_INDEX[package_id]
    except KeyError as error:
        raise UnknownPolicyPackageError(f"Unknown policy package: {package_id}") from error
