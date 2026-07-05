from pathlib import Path
from typing import Literal

import yaml
from prism_compiler.schemas import EntityDetection
from pydantic import BaseModel, Field

PolicyAction = Literal[
    "preserve",
    "tokenize",
    "redact",
    "generalize",
    "mask",
    "deny",
    "abstract",
    "block",
]


class PolicyRule(BaseModel):
    rule_id: str | None = None
    entity_type: str
    action: PolicyAction
    role: str | None = None
    token_prefix: str | None = None
    replacement: str | None = None


class Policy(BaseModel):
    domain: str
    version: str = "1"
    rules: list[PolicyRule] = Field(default_factory=list)

    @property
    def policy_id(self) -> str:
        return self.domain


class PolicyDecision(BaseModel):
    action: PolicyAction
    token_prefix: str | None = None
    replacement: str | None = None
    policy_id: str
    policy_version: str
    rule_id: str | None = None
    reason: str


DEFAULT_POLICY = Policy(
    domain="default",
    version="1",
    rules=[
        PolicyRule(entity_type="person", action="tokenize", token_prefix="PERSON"),
        PolicyRule(entity_type="email", action="tokenize", token_prefix="EMAIL"),
        PolicyRule(entity_type="phone", action="tokenize", token_prefix="PHONE"),
        PolicyRule(entity_type="invoice", action="tokenize", token_prefix="INVOICE"),
    ],
)


def load_policy(path: str | Path) -> Policy:
    with Path(path).open("r", encoding="utf-8") as policy_file:
        data = yaml.safe_load(policy_file) or {}
    return Policy.model_validate(data)


def decide(policy: Policy, detection: EntityDetection) -> PolicyDecision:
    for rule in policy.rules:
        if rule.entity_type != detection.entity_type:
            continue
        role = detection.metadata.get("role")
        if rule.role is not None and rule.role != role:
            continue
        return PolicyDecision(
            action=rule.action,
            token_prefix=rule.token_prefix,
            replacement=rule.replacement,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            rule_id=rule.rule_id,
            reason="rule_matched",
        )
    return PolicyDecision(
        action="tokenize",
        token_prefix=detection.entity_type.upper(),
        policy_id=policy.policy_id,
        policy_version=policy.version,
        reason="default_tokenize",
    )
