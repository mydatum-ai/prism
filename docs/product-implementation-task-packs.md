# Prism Product Implementation Task Packs

## Phase P1: Core Web UI

Status: completed

### Actions

1. Add a Vite React TypeScript app under `apps/web`.
2. Build a real operations UI for transform, chat mock, audit, and gateway health.
3. Connect the UI to the gateway on port `8004`.
4. Add frontend tests and Docker packaging.

## Phase P2: Authentication And Tenant Isolation

Status: completed

### Actions

1. Add API-key based FastAPI dependencies for local/dev authentication.
2. Add MyDatum OIDC login, callback, current-user, and logout routes.
3. Support MyDatum session cookies for browser access.
4. Require tenant headers or MyDatum tenant claims on protected API routes.
5. Reject cross-tenant request bodies.
6. Add tests for accepted and rejected tenant access plus MyDatum claim mapping.

## Phase P3: Persisted Storage

Status: completed

### Actions

1. Add SQLite-backed audit event persistence.
2. Store transform, rehydrate, chat mock, and chat completion audit events.
3. Add tenant-scoped audit listing.
4. Add storage tests.

## Phase P4: CI And Deployment Profiles

Status: completed

### Actions

1. Add GitHub Actions for Python and web quality gates.
2. Add Docker Compose profiles for dev, staging, and prod.
3. Document local execution commands.
