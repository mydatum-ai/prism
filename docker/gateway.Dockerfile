FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir -e .

EXPOSE 8004
CMD ["uvicorn", "prism_gateway.main:app", "--app-dir", "apps/gateway/src", "--host", "0.0.0.0", "--port", "8004"]


