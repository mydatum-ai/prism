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

Run deployment profiles:

```powershell
docker compose -f docker\docker-compose.yml --profile dev up --build
docker compose -f docker\docker-compose.yml --profile staging up --build
docker compose -f docker\docker-compose.yml --profile prod up --build
```

