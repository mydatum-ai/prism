# Prism Implementation Task And Action Packs

This document converts `main-implementation-plan.md` into executable phase packs for the public `prism` repo and the private `prism-enterprise` repo.

Repository split:

- `C:\Users\john_\Desktop\prism`: open-core runtime, gateway, compiler, detectors, transformations, vault, policy runtime, evaluation, CLI, SDK.
- `C:\Users\john_\Desktop\prism-enterprise`: private semantic intelligence, domain packs, enterprise vault, enterprise evaluation, optimizer, analytics, dashboard, compliance.

Primary product loop:

```text
Transform -> Vault -> Provider -> Rehydrate -> Evaluate
```

## Naming Alignment

Current placeholders and target architecture differ in a few places. Use these canonical implementation names going forward:

| Current placeholder | Canonical target | Action |
| --- | --- | --- |
| `packages/gateway` | `apps/gateway` | Move gateway app when Phase 0 starts. |
| `packages/mapping-vault` | `packages/vault-core` | Rename before Phase 2 implementation. |
| `packages/sdk` | `packages/sdk-python` | Rename before SDK implementation. |
| `packages/cli` | `packages/cli` | Keep. |
| `prism-enterprise/packages/analytics` | `packages/analytics` | Keep for later enterprise reporting services. |
| `prism-enterprise/packages/compliance` | `packages/compliance` | Keep for policy packs, audit, and governance workflows. |
| missing `docs-private` | `docs-private` | Create in enterprise repo before enterprise planning work. |
| missing `tests` in enterprise | `tests` | Create before enterprise code work. |

## Phase 0: Foundation

Goal: create a runnable, testable open-core skeleton and enterprise extension skeleton.

Repos: `prism`, `prism-enterprise`

Tasks:

- Normalize public repo layout to `apps/gateway`, `packages/vault-core`, and `packages/sdk-python`.
- Add Python workspace tooling with `pyproject.toml`, `ruff`, `mypy`, and `pytest`.
- Add basic package modules with explicit import boundaries.
- Add FastAPI gateway skeleton with `/healthz`.
- Add shared Pydantic schemas for transform, rehydrate, chat, provider, policy, vault, audit, and evaluation objects.
- Add Docker Compose for gateway plus optional Redis.
- Add enterprise skeleton interfaces only, without private behavior.
- Add CI-equivalent local commands documented in `docs/execution-commands.md`.

Actions:

- Create `apps/gateway/src/prism_gateway`.
- Create each public package with `src/prism_<package_name>` modules.
- Create public namespace packages for interfaces that enterprise can implement.
- In enterprise, create `docs-private`, `tests`, and package skeletons under `packages/*/src/prism_enterprise_*`.
- Keep `prism` free of direct imports from `prism_enterprise`.

Validation:

- `pytest` passes in both repos.
- `ruff check .` passes in both repos.
- `mypy` passes for implemented modules.
- `uvicorn prism_gateway.main:app` starts and serves `/healthz`.

Exit criteria:

- Both repos have a reliable local development loop.
- Public interfaces are stable enough for Phase 1.

## Phase 1: Public Transformation MVP

Goal: transform sensitive values, store mappings, and rehydrate without an external LLM.

Repo: `prism`

Tasks:

- Implement `POST /v1/transform`.
- Implement `POST /v1/rehydrate`.
- Implement `POST /v1/chat/mock`.
- Implement deterministic detectors for email, phone, simple names, and invoices.
- Implement token generator with stable per-request counters.
- Implement in-memory vault.
- Implement audit event object.

Actions:

- Add detector protocol and detector registry in `packages/detectors`.
- Add transformation pipeline in `packages/compiler` or `packages/transformers`.
- Add `InMemoryVault` in `packages/vault-core`.
- Add rehydration resolver in `packages/rehydration`.
- Wire gateway endpoints to the package APIs.
- Add example request/response fixtures in `examples`.

Validation:

- Unit tests cover `John Smith -> PERSON_1`, `john@email.com -> EMAIL_1`, and `INV-1001 -> INVOICE_1`.
- Integration test transforms one prompt and rehydrates it back.
- `/v1/chat/mock` runs `transform -> mock provider -> rehydrate`.

Exit criteria:

- No external LLM is required.
- The MVP proves the product loop works end to end.

## Phase 2: Mapping Vault

Goal: secure short-term mapping memory.

Repo: `prism`

Tasks:

- Rename `packages/mapping-vault` to `packages/vault-core`.
- Define `Vault` interface.
- Implement `InMemoryVault`.
- Implement `RedisVault`.
- Add TTL expiry.
- Add tenant, app, session, request, and mapping metadata.
- Fail closed when mappings are missing or expired.

Actions:

- Define vault key format using `tenant_id`, `app_id`, `session_id`, and `mapping_id`.
- Add vault exceptions for expired, missing, and forbidden mappings.
- Make rehydration consume only vault references, never raw external mappings.
- Add Redis integration tests with Docker Compose.

Validation:

- Expired mappings cannot be rehydrated.
- Cross-tenant lookup fails.
- Vault internals are never returned by public API responses.

Exit criteria:

- Vault behavior is deterministic and safe under expiry.

## Phase 3: Policy Runtime

Goal: policies decide how entities transform.

Repo: `prism`

Tasks:

- Implement YAML policy loader and validator.
- Support actions: `preserve`, `tokenize`, `mask`, `generalize`, `abstract`, `block`.
- Add policy version to audit events.
- Support domain-specific rule matching.

Actions:

- Add `Policy`, `PolicyRule`, and `PolicyDecision` models.
- Add rule matching by entity type, role, domain, sensitivity, and metadata.
- Add default public policy.
- Wire policy decisions into transformation pipeline.

Validation:

- Same prompt transforms differently under two policies.
- Invalid YAML fails validation with actionable errors.
- Audit event includes policy id and version.

Exit criteria:

- Transformation behavior is policy-driven rather than detector-driven only.

## Phase 4: Gateway And Provider Adapter

Goal: Prism can operate as an AI proxy.

Repo: `prism`

Tasks:

- Implement OpenAI-compatible `POST /v1/chat/completions`.
- Add optional `POST /v1/responses` later behind a feature flag.
- Implement `MockProvider`.
- Implement `OpenAIProvider`.
- Add provider request/response normalization.

Actions:

- Define provider protocol in public interfaces.
- Add configuration for provider selection and API keys.
- Run request flow as `transform -> provider -> rehydrate -> response`.
- Preserve request IDs and audit events across the full flow.

Validation:

- OpenAI-compatible client can call the gateway.
- Mock provider integration tests pass without network.
- OpenAI provider tests use mocked HTTP responses.

Exit criteria:

- A MyDatum app can target Prism instead of calling OpenAI directly.

## Phase 5: Evaluation Core

Goal: prove leakage, rehydration, and quality behavior.

Repo: `prism`

Tasks:

- Build dataset loader.
- Build evaluation runner.
- Build leakage scanner.
- Build rehydration validator.
- Build basic semantic comparator.
- Emit JSON and Markdown reports.
- Add CLI command `prism eval`.

Actions:

- Add datasets under `datasets/synthetic_pii`, `datasets/pulse_sample`, and `datasets/customer_support`.
- Define metric schema for `identity_leakage_score`, `rehydration_accuracy`, `transformation_correctness`, `quality_delta`, and `latency_overhead`.
- Add fixtures for raw, redacted, tokenized, and Prism-transformed prompts.

Validation:

- CLI produces stable JSON and Markdown reports.
- Metrics are covered by unit tests.
- Sample datasets can run in CI-equivalent local commands.

Exit criteria:

- Public repo can demonstrate measurable privacy and utility outcomes.

## Phase 6: Enterprise Plugin Loading

Goal: private implementations plug into public interfaces cleanly.

Repos: `prism`, `prism-enterprise`

Tasks:

- Define public interfaces: `SemanticAnalyzer`, `SemanticGraphBuilder`, `TransformationOptimizer`, `DomainPack`, `EnterpriseVault`, and `AdvancedEvaluator`.
- Add plugin loading by import path.
- Add config variables for enterprise implementations.
- Add compatibility tests using local fake plugins.

Actions:

- Implement import-string loader in `prism`.
- Require graceful fallback when enterprise plugin config is absent.
- Add example config:

```env
PRISM_SEMANTIC_ANALYZER=prism_enterprise_semantic_engine.engine.Engine
PRISM_DOMAIN_PACKS=pulse,logsentry
```

Validation:

- Community edition runs without enterprise repo installed.
- Enterprise fake plugin loads through public interface tests.
- `prism` never imports `prism_enterprise` directly.

Exit criteria:

- Enterprise packages can depend on `prism`; `prism` does not depend on enterprise.

## Phase 7: Local SLM Semantic Engine

Goal: enterprise semantic recommendations augment public policy decisions.

Repo: `prism-enterprise`

Tasks:

- Implement Ollama connector.
- Implement JSON-only extraction prompt.
- Support Qwen, Llama, and Gemma model configuration.
- Add entity role classifier.
- Add sensitivity classifier.
- Add recommendation generator.

Actions:

- Implement the public `SemanticAnalyzer` interface.
- Return recommendations only; do not override policy decisions.
- Add deterministic test doubles for model output.

Validation:

- Malformed model output fails closed.
- Recommendations include entity text, type, role, sensitivity, recommendation, and confidence.
- Policy remains the final decision authority.

Exit criteria:

- Enterprise semantic engine can be loaded by Phase 6 plugin config.

## Phase 8: Semantic Graph

Goal: preserve relationships and context, not just isolated entities.

Repo: `prism-enterprise`

Tasks:

- Build entity nodes.
- Build relationship edges.
- Infer roles from context.
- Extract graph context.
- Produce graph-to-transformation hints.

Actions:

- Implement `SemanticGraphBuilder`.
- Add graph schema and serialization.
- Add tests for resident/address/incident relationships.

Validation:

- Example `Juan Dela Cruz` is linked as resident.
- Private residence context is preserved without leaking exact address.
- Graph hints can influence transformation recommendations.

Exit criteria:

- Relationship-aware transformation is available to enterprise policy packs.

## Phase 9: Domain Packs

Goal: encode domain-specific policy intelligence.

Repo: `prism-enterprise`

Tasks:

- Implement `pulse`, `logsentry`, and `customer_support` packs.
- Add domain policy fixtures.
- Add tests for role-specific transformation.

Actions:

- Pulse: residents, reporters, officials, private addresses, places, money, counts, and dates.
- LogSentry: API keys, JWTs, private IPs, CVEs, timestamps, and usernames.
- Customer support: customer names, account IDs, order IDs, addresses, emails, phone numbers, and sentiment context.

Validation:

- Real MyDatum app examples can select domain packs by config.
- Packs emit only public interface types.
- Domain tests verify expected token prefixes and preserve rules.

Exit criteria:

- Domain-specific policies are usable without changing public repo code.

## Phase 10: Enterprise Evaluation

Goal: prove enterprise semantic value beyond simple redaction.

Repo: `prism-enterprise`

Tasks:

- Build golden datasets.
- Build semantic retention scorer.
- Add optional LLM-as-judge integration.
- Add expert-labelled expected outputs.
- Add domain benchmark reports.
- Feed evaluation outcomes to optimizer.

Actions:

- Implement `AdvancedEvaluator`.
- Add benchmark reports for Pulse, LogSentry, and customer support.
- Track semantic retention, identity leakage, rehydration accuracy, and quality delta.

Validation:

- Pulse dataset target: semantic retention 95 percent or higher.
- Identity leakage target: under 1 percent.
- Rehydration accuracy target: 99 percent or higher.
- Quality delta target: under 10 percent.

Exit criteria:

- Enterprise repo can demonstrate measurable semantic retention improvements.

## Phase 11: Dashboard

Goal: give enterprise users policy, audit, and evaluation workflows.

Repo: `prism-enterprise`

Tasks:

- Build tenant dashboard.
- Build policy editor.
- Build transformation viewer.
- Build audit search.
- Build evaluation report views.
- Build leakage and semantic retention dashboards.

Actions:

- Implement API surface for dashboard data.
- Add read-only first workflow before write workflows.
- Add authentication and tenant scoping before exposing sensitive data.

Validation:

- Dashboard never displays raw vault mappings unless explicitly authorized for a secure local inspection workflow.
- Tenant scoping tests pass.
- Evaluation reports render from stored JSON outputs.

Exit criteria:

- Enterprise user can manage policies and inspect transformations safely.

## Phase 12: Analytics And Compliance

Goal: operationalize enterprise reporting and governance.

Repo: `prism-enterprise`

Tasks:

- Build analytics event ingestion.
- Build aggregate privacy and quality metrics.
- Build compliance export formats.
- Build audit retention policies.

Actions:

- Add append-only audit event store adapter.
- Add reporting schemas for customer review.
- Add compliance pack tests for data minimization and retention.

Validation:

- Reports derive from audit metadata, not raw private mappings.
- Compliance exports exclude secrets and raw PII by default.

Exit criteria:

- Enterprise deployments have auditable, privacy-preserving reporting.

## Implementation Rules

- Implement public interfaces in `prism` first; enterprise code implements them later.
- Never add a direct `prism_enterprise` import to `prism`.
- Keep provider tests network-free unless explicitly running integration tests.
- Keep vault behavior fail-closed.
- Keep semantic SLM output advisory; policy runtime remains authoritative.
- Each phase must include tests and command documentation updates before moving to the next phase.

