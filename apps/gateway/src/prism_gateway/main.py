from fastapi import FastAPI
from prism_compiler.schemas import HealthResponse

app = FastAPI(
    title="Prism Gateway",
    version="0.1.0",
    description="Open-core privacy transformation gateway.",
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="prism-gateway")
