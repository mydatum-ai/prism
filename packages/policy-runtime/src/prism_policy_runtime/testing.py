from prism_policy_runtime.policy import Policy


class StaticPolicyProvider:
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        return Policy.model_validate(
            {
                "domain": app_id,
                "version": "test",
                "rules": [{"entity_type": "person", "action": "tokenize", "token_prefix": "TEST"}],
            }
        )


class NullPolicyProvider:
    def resolve_policy(self, tenant_id: str, app_id: str) -> Policy | None:
        return None
