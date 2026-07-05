# Policy Conflict Resolution

Prism evaluates every policy rule that matches the detected entity and request context. When more than one rule matches, the policy runtime chooses the winner with one deterministic algorithm:

1. `deny` and legacy `block` rules win before other actions.
2. Higher `priority` wins.
3. More specific rules win. Specificity counts matched `role`, `purpose`, `direction`, `app_id`, `environment`, and `min_confidence`.
4. If rules are still tied, earlier declaration order wins.

Rule conditions are evaluated in the public policy runtime, so gateways, providers, and enterprise integrations all share the same behavior. If no rule matches, Prism falls back to the existing default tokenization behavior for the detected entity type.
