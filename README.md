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
$env:MYDATUM_SCOPES="openid email mydatum.roles"
$env:PRISM_SESSION_SECRET="<generate-at-least-50-random-characters>"
```

The web UI can use MyDatum session cookies. Leave `VITE_PRISM_API_KEY` empty in browser deployments
that should rely on MyDatum sessions instead of service API keys.

Run deployment profiles:

```powershell
docker compose -f docker\docker-compose.yml --profile dev up --build
docker compose -f docker\docker-compose.yml --profile staging up --build
docker compose -f docker\docker-compose.yml --profile prod up --build
```

