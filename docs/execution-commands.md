# Prism Execution Commands

Use this command guide while implementing `prism`. Run commands from `C:\Users\john_\Desktop\prism` unless a command says otherwise.

## Repo Checks

```powershell
git status --short --branch
git pull --ff-only origin main
rg --files
```

## Required Phase Workflow

Use this workflow for every phase before starting the next one.

```powershell
git status --short --branch
git pull --ff-only origin main
```

Implement the phase tasks, then run the phase-specific verification commands below. Finish every phase with:

```powershell
ruff format .
ruff format --check .
ruff check .
mypy .
pytest
git status --short
git add .
git commit -m "Implement Phase <number>: <short phase name>"
git push origin main
git status --short --branch
```

If a phase includes generated reports, datasets, or local-only outputs, confirm `.gitignore` before staging.

## Phase 0: Bootstrap Layout

```powershell
New-Item -ItemType Directory -Force apps/gateway
if (Test-Path packages/gateway) { git mv packages/gateway apps/gateway-package-placeholder }
if (Test-Path packages/mapping-vault) { git mv packages/mapping-vault packages/vault-core }
if (Test-Path packages/sdk) { git mv packages/sdk packages/sdk-python }
New-Item -ItemType Directory -Force packages/vault-core,packages/sdk-python
New-Item -ItemType Directory -Force datasets,apps/gateway/src/prism_gateway
```

Use `git mv` only when the source path exists. The `apps/gateway-package-placeholder` path is temporary; replace it with the real app package layout during Phase 0.

Phase 0 implementation guide:

```powershell
New-Item -ItemType Directory -Force apps/gateway/src/prism_gateway
New-Item -ItemType Directory -Force packages/compiler/src/prism_compiler
New-Item -ItemType Directory -Force packages/detectors/src/prism_detectors
New-Item -ItemType Directory -Force packages/transformers/src/prism_transformers
New-Item -ItemType Directory -Force packages/policy-runtime/src/prism_policy_runtime
New-Item -ItemType Directory -Force packages/vault-core/src/prism_vault_core
New-Item -ItemType Directory -Force packages/rehydration/src/prism_rehydration
New-Item -ItemType Directory -Force packages/evaluation/src/prism_evaluation
New-Item -ItemType Directory -Force packages/sdk-python/src/prism_sdk
New-Item -ItemType Directory -Force packages/cli/src/prism_cli
New-Item -ItemType Directory -Force tests,examples,docs,docker
```

Phase 0 verification:

```powershell
pytest tests/test_health.py -q
ruff check .
mypy .
```

## Python Environment

Prefer `uv` when available. Fall back to `python -m venv` and `pip` if needed.

```powershell
uv --version
uv venv
uv pip install -e ".[dev]"
```

Fallback:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Local Quality Gate

```powershell
ruff format .
ruff check .
mypy .
pytest
```

Run a narrower test while developing:

```powershell
pytest tests/test_transform_mvp.py -q
pytest tests/test_vault_core.py -q
pytest tests/test_policy_runtime.py -q
pytest tests/test_gateway.py -q
```

## Run Gateway

```powershell
$env:PRISM_PROVIDER="mock"
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/healthz
```

## Transform MVP Requests

Transform:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/transform -ContentType "application/json" -Body '{
  "tenant_id": "tenant_dev",
  "app_id": "pulse",
  "session_id": "session_1",
  "text": "John Smith emailed john@email.com about INV-1001"
}'
```

## Phase 1: Public Transformation MVP

Implement: `/v1/transform`, `/v1/rehydrate`, `/v1/chat/mock`, deterministic detectors, token generation, in-memory vault, basic rehydration, and audit events.

Recommended file work:

```powershell
New-Item -ItemType Directory -Force examples/requests
New-Item -ItemType Directory -Force tests/fixtures
```

Focused verification:

```powershell
pytest tests/test_detectors.py -q
pytest tests/test_transform_mvp.py -q
pytest tests/test_rehydration.py -q
pytest tests/test_chat_mock.py -q
```

Manual smoke:

```powershell
$env:PRISM_PROVIDER="mock"
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8000
```

In another shell, run the transform, rehydrate, and mock chat requests in this document. Then finish with the required phase workflow commit and push:

```powershell
git add .
git commit -m "Implement Phase 1: public transformation MVP"
git push origin main
```

Rehydrate:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/rehydrate -ContentType "application/json" -Body '{
  "tenant_id": "tenant_dev",
  "app_id": "pulse",
  "session_id": "session_1",
  "text": "PERSON_1 emailed EMAIL_1 about INVOICE_1"
}'
```

Mock chat:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/chat/mock -ContentType "application/json" -Body '{
  "tenant_id": "tenant_dev",
  "app_id": "pulse",
  "session_id": "session_1",
  "messages": [
    { "role": "user", "content": "John Smith emailed john@email.com about INV-1001" }
  ]
}'
```

## Redis Vault

```powershell
docker compose -f docker/docker-compose.yml up -d redis
$env:PRISM_VAULT_BACKEND="redis"
$env:PRISM_REDIS_URL="redis://127.0.0.1:6379/0"
pytest tests/test_redis_vault.py -q
pytest tests/integration/test_redis_vault_integration.py -q
docker compose -f docker/docker-compose.yml down
```

## Phase 2: Mapping Vault

Implement: `Vault` interface, `InMemoryVault`, `RedisVault`, TTL expiry, tenant/app/session scoping, mapping metadata, and fail-closed expired mapping behavior.

Layout and implementation prep:

```powershell
if (Test-Path packages/mapping-vault) { git mv packages/mapping-vault packages/vault-core }
New-Item -ItemType Directory -Force packages/vault-core/src/prism_vault_core
New-Item -ItemType Directory -Force tests/integration
```

Focused verification:

```powershell
pytest tests/test_vault_core.py -q
pytest tests/test_vault_ttl.py -q
pytest tests/test_vault_tenant_scope.py -q
docker compose -f docker/docker-compose.yml up -d redis
pytest tests/integration/test_redis_vault_integration.py -q
docker compose -f docker/docker-compose.yml down
```

Commit and push:

```powershell
git add .
git commit -m "Implement Phase 2: mapping vault"
git push origin main
```

## Policy Runtime

```powershell
pytest tests/test_policy_runtime.py -q
pytest tests/test_policy_transform_integration.py -q
```

Manual policy smoke test:

```powershell
$env:PRISM_POLICY_PATH="examples/policies/pulse.yaml"
pytest tests/test_gateway_policy.py -q
```

## Phase 3: Policy Runtime

Implement: YAML policy loader, schema validation, actions `preserve`, `tokenize`, `mask`, `generalize`, `abstract`, `block`, rule matching, and policy version audit metadata.

Implementation prep:

```powershell
New-Item -ItemType Directory -Force examples/policies
New-Item -ItemType Directory -Force packages/policy-runtime/src/prism_policy_runtime
```

Focused verification:

```powershell
pytest tests/test_policy_runtime.py -q
pytest tests/test_policy_actions.py -q
pytest tests/test_policy_transform_integration.py -q
pytest tests/test_audit_policy_version.py -q
```

Commit and push:

```powershell
git add .
git commit -m "Implement Phase 3: policy runtime"
git push origin main
```

## Provider Adapter

Mock provider:

```powershell
$env:PRISM_PROVIDER="mock"
pytest tests/test_provider_mock.py -q
```

OpenAI provider with mocked HTTP:

```powershell
pytest tests/test_provider_openai.py -q
```

Manual OpenAI-compatible gateway smoke:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/chat/completions -ContentType "application/json" -Body '{
  "model": "mock",
  "messages": [
    { "role": "user", "content": "John Smith emailed john@email.com" }
  ],
  "metadata": {
    "tenant_id": "tenant_dev",
    "app_id": "pulse",
    "session_id": "session_1"
  }
}'
```

## Phase 4: Gateway And Provider Adapter

Implement: OpenAI-compatible `/v1/chat/completions`, provider protocol, `MockProvider`, `OpenAIProvider`, provider config, request normalization, response normalization, and full `transform -> provider -> rehydrate` flow.

Focused verification:

```powershell
pytest tests/test_gateway.py -q
pytest tests/test_provider_mock.py -q
pytest tests/test_provider_openai.py -q
pytest tests/test_chat_completions_compat.py -q
pytest tests/test_proxy_flow.py -q
```

Manual smoke:

```powershell
$env:PRISM_PROVIDER="mock"
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8000
```

Run the OpenAI-compatible gateway request above, then commit and push:

```powershell
git add .
git commit -m "Implement Phase 4: gateway provider adapter"
git push origin main
```

## Evaluation

```powershell
prism eval --dataset datasets/synthetic_pii --output reports/synthetic_pii
Get-Content reports/synthetic_pii/report.json
Get-Content reports/synthetic_pii/report.md
```

CI-equivalent:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
prism eval --dataset datasets/synthetic_pii --output reports/ci_synthetic_pii
```

## Phase 5: Evaluation Core

Implement: dataset loader, test runner, leakage scanner, rehydration validator, semantic comparator, JSON report, Markdown report, and `prism eval`.

Implementation prep:

```powershell
New-Item -ItemType Directory -Force datasets/synthetic_pii
New-Item -ItemType Directory -Force datasets/pulse_sample
New-Item -ItemType Directory -Force datasets/customer_support
New-Item -ItemType Directory -Force packages/evaluation/src/prism_evaluation
```

Focused verification:

```powershell
pytest tests/test_eval_dataset_loader.py -q
pytest tests/test_eval_leakage_scanner.py -q
pytest tests/test_eval_rehydration_validator.py -q
pytest tests/test_eval_reports.py -q
pytest tests/test_cli_eval.py -q
prism eval --dataset datasets/synthetic_pii --output reports/synthetic_pii
```

Commit and push:

```powershell
git add .
git commit -m "Implement Phase 5: evaluation core"
git push origin main
```

## Enterprise Plugin Loading Smoke

Use this after public interfaces exist and enterprise exposes compatible classes.

```powershell
$env:PRISM_SEMANTIC_ANALYZER="prism_enterprise_semantic_engine.engine.Engine"
$env:PRISM_DOMAIN_PACKS="pulse,logsentry"
pytest tests/test_plugin_loading.py -q
```

Cross-repo editable install during local integration:

```powershell
uv pip install -e C:\Users\john_\Desktop\prism-enterprise
pytest tests/test_enterprise_plugin_contract.py -q
```

## Phase 6: Enterprise Plugin Loading

Implement in `prism`: public plugin interfaces, import-string plugin loader, config variables, community fallback behavior, and fake plugin tests. Enterprise repo implements real classes separately.

Implementation prep:

```powershell
New-Item -ItemType Directory -Force packages/compiler/src/prism_compiler/interfaces
New-Item -ItemType Directory -Force tests/fixtures/plugins
```

Focused verification:

```powershell
pytest tests/test_plugin_interfaces.py -q
pytest tests/test_plugin_loading.py -q
pytest tests/test_community_without_enterprise.py -q
pytest tests/test_no_enterprise_imports.py -q
```

Optional cross-repo smoke after enterprise Phase E6:

```powershell
uv pip install -e C:\Users\john_\Desktop\prism-enterprise
$env:PRISM_SEMANTIC_ANALYZER="prism_enterprise_semantic_engine.engine.Engine"
$env:PRISM_DOMAIN_PACKS="pulse,logsentry"
pytest tests/test_enterprise_plugin_contract.py -q
```

Commit and push:

```powershell
git add .
git commit -m "Implement Phase 6: enterprise plugin loading"
git push origin main
```

## Phases 7-12: Enterprise-Driven Features

Phases 7-12 are implemented primarily in `prism-enterprise`. For public `prism`, add only interface extensions, compatibility fixtures, and cross-repo smoke tests required by those enterprise phases.

Public compatibility verification for each enterprise phase:

```powershell
uv pip install -e C:\Users\john_\Desktop\prism-enterprise
pytest tests/test_plugin_loading.py -q
pytest tests/test_enterprise_plugin_contract.py -q
pytest
```

Commit and push any public compatibility change after each enterprise phase:

```powershell
git add .
git commit -m "Support Phase <number>: <enterprise feature>"
git push origin main
```

## Git Workflow

```powershell
git status --short
git add .
git commit -m "Implement <phase or feature>"
git push origin main
```

Before every push:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
```

After every push:

```powershell
git status --short --branch
```
