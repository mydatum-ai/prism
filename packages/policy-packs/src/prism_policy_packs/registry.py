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


def _rule(
    entity_type: str,
    action: str,
    *,
    rule_id: str,
    token_prefix: str | None = None,
    token_strategy: str = "sequence",
    replacement: str | None = None,
    rehydrate_roles: list[str] | None = None,
    max_token_age_seconds: int | None = None,
) -> PolicyRule:
    return PolicyRule.model_validate(
        {
            "rule_id": rule_id,
            "entity_type": entity_type,
            "action": action,
            "token_prefix": token_prefix,
            "token_strategy": token_strategy,
            "replacement": replacement,
            "rehydrate_roles": rehydrate_roles,
            "max_token_age_seconds": max_token_age_seconds,
        }
    )


def _example(
    name: str,
    prompt: str,
    expected_transform_contains: list[str],
    expected_rehydration_roles: list[str],
) -> PolicyPackageExample:
    return PolicyPackageExample(
        name=name,
        prompt=prompt,
        expected_transform_contains=expected_transform_contains,
        expected_rehydration_roles=expected_rehydration_roles,
    )


def _packages() -> list[PolicyPackage]:
    return [
        PolicyPackage(
            package_id="healthcare.default",
            name="Healthcare Default",
            version="1.0.0",
            family="healthcare",
            intended_use="Patient-facing and clinical support prompts.",
            risk_level="restricted",
            supported_entity_types=["person", "email", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="healthcare_patient",
                    token_prefix="PATIENT",
                    token_strategy="random_opaque",
                    rehydrate_roles=["clinician", "care_coordinator", "enterprise_admin"],
                    max_token_age_seconds=86400,
                ),
                _rule(
                    "email",
                    "tokenize",
                    rule_id="healthcare_contact",
                    token_prefix="CONTACT",
                    rehydrate_roles=["clinician", "care_coordinator", "enterprise_admin"],
                ),
                _rule("phone", "redact", rule_id="healthcare_phone"),
            ],
            examples=[
                _example(
                    "patient-contact",
                    "Maria Santos emailed maria@example.com about follow up care.",
                    ["PATIENT_", "CONTACT_"],
                    ["clinician"],
                )
            ],
        ),
        PolicyPackage(
            package_id="government.civic-services",
            name="Government Civic Services",
            version="1.0.0",
            family="government",
            intended_use="Civic service requests and government case routing.",
            risk_level="high",
            supported_entity_types=["person", "email", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="government_resident",
                    token_prefix="RESIDENT",
                    token_strategy="session_stable",
                    rehydrate_roles=["case_worker", "public_official", "enterprise_admin"],
                ),
                _rule(
                    "email",
                    "tokenize",
                    rule_id="government_email",
                    token_prefix="CONTACT",
                    rehydrate_roles=["case_worker", "enterprise_admin"],
                ),
                _rule("phone", "mask", rule_id="government_phone"),
            ],
            examples=[
                _example(
                    "resident-report",
                    "Maria Santos emailed maria@example.com about flood cleanup.",
                    ["RESIDENT_", "CONTACT_"],
                    ["case_worker"],
                )
            ],
        ),
        PolicyPackage(
            package_id="community.pulse",
            name="Pulse Community Platform",
            version="1.0.0",
            family="community",
            intended_use="Community incident reporting and resident operations.",
            risk_level="high",
            supported_entity_types=["person", "email", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="pulse_reporter",
                    token_prefix="REPORTER",
                    token_strategy="session_stable",
                    rehydrate_roles=["pulse_operator", "case_worker", "enterprise_admin"],
                ),
                _rule(
                    "email",
                    "tokenize",
                    rule_id="pulse_email",
                    token_prefix="EMAIL",
                    rehydrate_roles=["pulse_operator", "enterprise_admin"],
                ),
                _rule("phone", "mask", rule_id="pulse_phone"),
            ],
            examples=[
                _example(
                    "pulse-incident",
                    "Maria Santos emailed maria@example.com about flooding.",
                    ["REPORTER_", "EMAIL_"],
                    ["pulse_operator"],
                )
            ],
        ),
        PolicyPackage(
            package_id="cybersecurity.logsentry",
            name="LogSentry Cybersecurity",
            version="1.0.0",
            family="cybersecurity",
            intended_use="Security investigation and telemetry analysis prompts.",
            risk_level="restricted",
            supported_entity_types=["person", "email", "phone", "invoice"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="logsentry_username",
                    token_prefix="USER",
                    token_strategy="tenant_stable",
                    rehydrate_roles=["security_admin"],
                ),
                _rule("email", "redact", rule_id="logsentry_email"),
                _rule("phone", "redact", rule_id="logsentry_phone"),
                _rule("invoice", "preserve", rule_id="logsentry_case_reference"),
            ],
            examples=[
                _example(
                    "security-ticket",
                    "Maria Santos emailed maria@example.com about INV-1001.",
                    ["USER_", "INV-1001"],
                    ["security_admin"],
                )
            ],
        ),
        PolicyPackage(
            package_id="personal.default",
            name="Personal Default",
            version="1.0.0",
            family="personal",
            intended_use="Personal productivity, notes, and task prompts.",
            risk_level="medium",
            supported_entity_types=["person", "email", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="personal_contact",
                    token_prefix="CONTACT",
                    token_strategy="session_stable",
                    rehydrate_roles=["owner"],
                ),
                _rule(
                    "email",
                    "tokenize",
                    rule_id="personal_email",
                    token_prefix="EMAIL",
                    rehydrate_roles=["owner"],
                ),
                _rule("phone", "mask", rule_id="personal_phone"),
            ],
            examples=[
                _example(
                    "personal-note",
                    "Maria Santos emailed maria@example.com about dinner plans.",
                    ["CONTACT_", "EMAIL_"],
                    ["owner"],
                )
            ],
        ),
        PolicyPackage(
            package_id="financial.default",
            name="Financial Default",
            version="1.0.0",
            family="financial",
            intended_use="Financial service and personal finance analysis prompts.",
            risk_level="restricted",
            supported_entity_types=["person", "email", "invoice", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="financial_account_holder",
                    token_prefix="ACCOUNT_HOLDER",
                    token_strategy="tenant_stable",
                    rehydrate_roles=["finance_admin"],
                ),
                _rule("email", "redact", rule_id="financial_email"),
                _rule(
                    "invoice",
                    "tokenize",
                    rule_id="financial_transaction",
                    token_prefix="TRANSACTION",
                    rehydrate_roles=["finance_admin"],
                ),
                _rule("phone", "mask", rule_id="financial_phone"),
            ],
            examples=[
                _example(
                    "finance-case",
                    "Maria Santos emailed maria@example.com about INV-1001.",
                    ["ACCOUNT_HOLDER_", "TRANSACTION_"],
                    ["finance_admin"],
                )
            ],
        ),
        PolicyPackage(
            package_id="customer-support.default",
            name="Customer Support Default",
            version="1.0.0",
            family="customer_support",
            intended_use="Customer support triage and response drafting.",
            risk_level="high",
            supported_entity_types=["person", "email", "phone", "invoice"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="support_customer",
                    token_prefix="CUSTOMER",
                    token_strategy="session_stable",
                    rehydrate_roles=["support_agent", "support_manager", "enterprise_admin"],
                ),
                _rule(
                    "email",
                    "tokenize",
                    rule_id="support_email",
                    token_prefix="EMAIL",
                    rehydrate_roles=["support_agent", "support_manager", "enterprise_admin"],
                ),
                _rule("invoice", "tokenize", rule_id="support_case", token_prefix="CASE"),
                _rule("phone", "mask", rule_id="support_phone"),
            ],
            examples=[
                _example(
                    "support-ticket",
                    "Maria Santos emailed maria@example.com about INV-1001.",
                    ["CUSTOMER_", "EMAIL_", "CASE_"],
                    ["support_agent"],
                )
            ],
        ),
        PolicyPackage(
            package_id="hr.default",
            name="HR Default",
            version="1.0.0",
            family="hr",
            intended_use="Employee operations, HR triage, and internal support prompts.",
            risk_level="restricted",
            supported_entity_types=["person", "email", "phone"],
            rules=[
                _rule(
                    "person",
                    "tokenize",
                    rule_id="hr_employee",
                    token_prefix="EMPLOYEE",
                    token_strategy="session_stable",
                    rehydrate_roles=["hr_admin", "legal_admin"],
                ),
                _rule("email", "mask", rule_id="hr_email"),
                _rule("phone", "redact", rule_id="hr_phone"),
            ],
            examples=[
                _example(
                    "employee-note",
                    "Maria Santos emailed maria@example.com about leave.",
                    ["EMPLOYEE_"],
                    ["hr_admin"],
                )
            ],
        ),
    ]


_PACKAGE_INDEX = {package.package_id: package for package in _packages()}
