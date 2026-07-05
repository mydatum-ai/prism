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
    priority: int = 0
    role: str | None = None
    purpose: str | None = None
    direction: str | None = None
    app_id: str | None = None
    environment: str | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
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


class PolicyDecisionContext(BaseModel):
    app_id: str | None = None
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None


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


def decide(
    policy: Policy,
    detection: EntityDetection,
    context: PolicyDecisionContext | None = None,
) -> PolicyDecision:
    matched_rules = [
        (index, rule)
        for index, rule in enumerate(policy.rules)
        if _rule_matches(rule, detection, context or PolicyDecisionContext())
    ]
    if matched_rules:
        _, rule = sorted(matched_rules, key=_rule_sort_key)[0]
        return PolicyDecision(
            action=rule.action,
            token_prefix=rule.token_prefix,
            replacement=rule.replacement,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            rule_id=rule.rule_id,
            reason="conflict_resolved" if len(matched_rules) > 1 else "rule_matched",
        )
    return PolicyDecision(
        action="tokenize",
        token_prefix=detection.entity_type.upper(),
        policy_id=policy.policy_id,
        policy_version=policy.version,
        reason="default_tokenize",
    )


def _rule_matches(
    rule: PolicyRule, detection: EntityDetection, context: PolicyDecisionContext
) -> bool:
    if rule.entity_type != detection.entity_type:
        return False
    if rule.min_confidence is not None and detection.confidence < rule.min_confidence:
        return False
    if rule.role is not None and rule.role != detection.metadata.get("role"):
        return False
    if rule.purpose is not None and rule.purpose != context.purpose:
        return False
    if rule.direction is not None and rule.direction != context.direction:
        return False
    if rule.app_id is not None and rule.app_id != context.app_id:
        return False
    if rule.environment is not None and rule.environment != context.environment:
        return False
    return True


def _rule_sort_key(indexed_rule: tuple[int, PolicyRule]) -> tuple[int, int, int, int]:
    index, rule = indexed_rule
    deny_rank = 0 if rule.action in {"deny", "block"} else 1
    return (deny_rank, -rule.priority, -_specificity(rule), index)


def _specificity(rule: PolicyRule) -> int:
    return sum(
        value is not None
        for value in (
            rule.role,
            rule.purpose,
            rule.direction,
            rule.app_id,
            rule.environment,
            rule.min_confidence,
        )
    )
