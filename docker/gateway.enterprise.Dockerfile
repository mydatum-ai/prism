FROM python:3.12-slim

WORKDIR /workspace
COPY prism /workspace/prism
COPY prism-enterprise /workspace/prism-enterprise

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e /workspace/prism \
    && python -m pip install --no-cache-dir -e /workspace/prism-enterprise

WORKDIR /workspace/prism
EXPOSE 8004
CMD ["uvicorn", "prism_gateway.main:app", "--app-dir", "apps/gateway/src", "--host", "0.0.0.0", "--port", "8004"]
