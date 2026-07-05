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

## Pending

- Phase 2: Mapping Vault
- Phase 3: Policy Runtime
- Phase 4: Gateway And Provider Adapter
- Phase 5: Evaluation Core
- Phase 6: Enterprise Plugin Loading
- Phases 7-12: Enterprise-driven compatibility work
