Prism is the open-core runtime for privacy-preserving AI transformation.

The implementation plan lives in [docs/main-implementation-plan.md](docs/main-implementation-plan.md).
Current implementation progress is tracked in [docs/phase-status.md](docs/phase-status.md).

## Development

Install locally:

```powershell
python -m pip install -e ".[dev]"
```

Run the Phase 0 quality gate:

```powershell
ruff format --check .
ruff check .
mypy .
pytest
```

Run the gateway:

```powershell
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8004
```

Run the Prism web UI:

```powershell
cd C:\Users\john_\Desktop\prism\apps\web
npm install
npm run dev
```

Open `http://127.0.0.1:3004`. For local development without configured keys, the gateway accepts
tenant `tenant_dev` with API key `dev`. Set `PRISM_API_KEYS=tenant_a:secret-a,tenant_b:secret-b`
to enable API-key tenant isolation.

MyDatum login is available through the gateway when these values are configured:

```powershell
$env:MYDATUM_ISSUER="http://localhost:8000"
$env:MYDATUM_CLIENT_ID="<client-id>"
$env:MYDATUM_CLIENT_SECRET="<client-secret>"
$env:MYDATUM_REDIRECT_URI="http://127.0.0.1:8004/auth/callback"
$env:MYDATUM_INTERNAL_BASE_URL="http://host.docker.internal:8000"
$env:MYDATUM_SCOPES="openid email mydatum.roles"
$env:PRISM_SESSION_SECRET="<generate-at-least-50-random-characters>"
```

Use `MYDATUM_INTERNAL_BASE_URL` when Prism runs in Docker and MyDatum runs on the host. Keep
`MYDATUM_ISSUER` as the public issuer registered with MyDatum, usually `http://localhost:8000`.

The web UI can use MyDatum session cookies. Leave `VITE_PRISM_API_KEY` empty in browser deployments
that should rely on MyDatum sessions instead of service API keys.

Run deployment profiles:

```powershell
docker compose -f docker\docker-compose.yml --profile dev up --build
docker compose -f docker\docker-compose.yml --profile staging up --build
docker compose -f docker\docker-compose.yml --profile prod up --build
```

## Published Enterprise Policies

Prism can resolve runtime policies from a sibling `prism-enterprise` checkout by loading the
enterprise policy provider:

```powershell
$env:PRISM_POLICY_PROVIDER="prism_policy_runtime.providers:PublishedPolicyProvider"
$env:PRISM_ENTERPRISE_POLICY_API_URL="http://127.0.0.1:8005"
$env:PRISM_ENTERPRISE_POLICY_API_KEY="dev"
$env:PRISM_ENTERPRISE_POLICY_TIMEOUT_SECONDS="2"
$env:PRISM_POLICY_CACHE_TTL_SECONDS="30"
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8004
```

When Prism runs in Docker and Prism Enterprise runs on the host, use the enterprise compose
override:

```powershell
docker compose -f docker\docker-compose.yml -f docker\docker-compose.enterprise.yml --profile dev up --build gateway web
```

If the enterprise provider is unavailable or returns no active policy for the tenant/app pair,
Prism falls back to its local policy behavior. The older provider import string
`prism_enterprise_dashboard.policy_provider:PublishedPolicyProvider` is still accepted as a
compatibility alias, but new deployments should use
`prism_policy_runtime.providers:PublishedPolicyProvider` so the Prism gateway does not need the
private Enterprise package installed.

Policy runtime cache invalidation is available through the gateway:

```powershell
$headers = @{
  "X-Prism-Tenant"="tenant_dev"
  "X-Prism-API-Key"="dev"
}

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8004/v1/policies/cache/invalidate -Headers $headers -ContentType "application/json" -Body '{
  "tenant_id": "tenant_dev",
  "app_id": "pulse"
}'
```

Set `PRISM_POLICY_CACHE_TTL_SECONDS=0` to disable policy caching. When caching is enabled, Prism
keeps a last-known-good policy for each tenant/app pair and uses it if the configured provider
temporarily returns no policy.

Runtime policy observability is available per tenant/app:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8004/v1/policies/runtime/status?tenant_id=tenant_dev&app_id=pulse" -Headers $headers
```

Transform and chat audit events include `policy_source`, `policy_cache_hit`,
`policy_cache_stale`, and `policy_provider_latency_ms` metadata so operators can distinguish fresh
enterprise policy, cache hits, stale cache use, local policy, and fallback behavior.

