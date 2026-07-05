# Prism Product Execution Commands

Run each phase only after the previous phase passes.

## Phase P1: Core Web UI

```powershell
cd C:\Users\john_\Desktop\prism\apps\web
npm install
npm run lint
npm run test -- --run
npm run build
```

## Phase P2: Authentication And Tenant Isolation

```powershell
cd C:\Users\john_\Desktop\prism
ruff format --check .
ruff check .
mypy .
pytest tests\test_gateway_auth.py
pytest tests\test_gateway_mydatum_auth.py
```

## Phase P3: Persisted Storage

```powershell
cd C:\Users\john_\Desktop\prism
pytest tests\test_gateway_storage.py tests\test_gateway_auth.py
```

## Phase P4: CI And Deployment Profiles

```powershell
cd C:\Users\john_\Desktop\prism
docker compose -f docker\docker-compose.yml --profile dev config
docker compose -f docker\docker-compose.yml --profile staging config
docker compose -f docker\docker-compose.yml --profile prod config
```

## Final Gate And Push

```powershell
cd C:\Users\john_\Desktop\prism
ruff format --check .
ruff check .
mypy .
pytest -q
cd apps\web
npm run lint
npm run test -- --run
npm run build
cd ..\..
git status --short
git add .
git commit -m "Implement Prism product web auth storage and deployment"
git push origin main
```
