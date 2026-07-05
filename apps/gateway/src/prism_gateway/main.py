from fastapi import FastAPI
from prism_compiler.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    RehydrateRequest,
    RehydrateResponse,
    TransformRequest,
    TransformResponse,
)

from prism_gateway.routes import chat_mock_endpoint, rehydrate_endpoint, transform_endpoint

app = FastAPI(
    title="Prism Gateway",
    version="0.1.0",
    description="Open-core privacy transformation gateway.",
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="prism-gateway")


@app.post("/v1/transform", response_model=TransformResponse)
def transform_route(request: TransformRequest) -> TransformResponse:
    return transform_endpoint(request)


@app.post("/v1/rehydrate", response_model=RehydrateResponse)
def rehydrate_route(request: RehydrateRequest) -> RehydrateResponse:
    return rehydrate_endpoint(request)


@app.post("/v1/chat/mock", response_model=ChatResponse)
def chat_mock_route(request: ChatRequest) -> ChatResponse:
    return chat_mock_endpoint(request)
