# Prism Phase Status

This file records only phases with code actually implemented and verified in this repo.

## Completed

### Phase 0: Foundation

Status: completed

Implemented:

- Canonical public layout with `apps/gateway`, `packages/vault-core`, and `packages/sdk-python`.
- Python project metadata and package discovery.
- FastAPI gateway skeleton with `GET /healthz`.
- Shared Pydantic contract schemas.
- Initial public interfaces for detectors, providers, and vaults.
- Package skeletons for compiler, detectors, transformers, policy runtime, vault core, rehydration, evaluation, SDK, and CLI.
- Docker Compose and gateway Dockerfile.
- Phase 0 import and health tests.

Verified:

```powershell
ruff format --check .
ruff check .
mypy .
pytest -q
```

### Phase 1: Public Transformation MVP

Status: completed

Implemented:

- `POST /v1/transform`.
- `POST /v1/rehydrate`.
- `POST /v1/chat/mock`.
- Deterministic detectors for email, phone, simple names, and invoices.
- Per-request deterministic token generation.
- In-memory vault storage scoped by tenant, app, session, and token.
- Basic rehydration from stored mappings.
- Audit events for transform, rehydrate, and mock chat flows.
- Example transform request fixture.

Verified:

```powershell
ruff format --check .
ruff check .
mypy .
pytest -q
```

### Phase 2: Mapping Vault

Status: completed

Implemented:

- `VaultKey` scoped by tenant, app, session, and token.
- `VaultRecord` with entity type, created timestamp, optional expiry, and metadata.
- `InMemoryVault` with TTL expiry and fail-closed missing or expired mapping behavior.
- `RedisVault` with JSON record serialization, TTL support, and metadata round-trip.
- Rehydration behavior that leaves unresolved or expired tokens in place.
- Sanitized transform responses so original values remain in the vault and are not exposed through mappings or response detections.

Verified:

```powershell
ruff format --check .
ruff check .
mypy .
pytest -q
pytest tests/integration/test_redis_vault_integration.py -q
```

### Phase 3: Policy Runtime

Status: completed

Implemented:

- YAML policy loader and Pydantic validation.
- Policy rules with entity type, role, action, token prefix, and replacement fields.
- Actions: `preserve`, `tokenize`, `mask`, `generalize`, `abstract`, and `block`.
- Default policy matching Phase 1 token behavior.
- Policy-driven transformation pipeline.
- Gateway policy loading through `PRISM_POLICY_PATH`.
- Policy id and version in transform audit events.
- Example `pulse` and `support` policies.

Verified:

```powershell
ruff format --check .
ruff check .
mypy .
pytest -q
```

### Phase 4: Gateway And Provider Adapter

Status: completed

Implemented:

- OpenAI-compatible `POST /v1/chat/completions`.
- Provider protocol and normalized provider response model.
- `MockProvider`.
- `OpenAIProvider` using the OpenAI chat completions API shape.
- Gateway provider selection through `PRISM_PROVIDER`.
- OpenAI API key and base URL configuration.
- Full proxy flow: transform request messages, call provider, rehydrate provider output, return OpenAI-compatible response.
- Network-free OpenAI provider tests using an HTTP mock transport.

Verified:

```powershell
ruff format --check .
ruff check .
mypy .
pytest -q
```

## Pending

- Phase 5: Evaluation Core
- Phase 6: Enterprise Plugin Loading
- Phases 7-12: Enterprise-driven compatibility work
