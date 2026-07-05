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
uvicorn prism_gateway.main:app --reload --app-dir apps/gateway/src --host 127.0.0.1 --port 8000
```
