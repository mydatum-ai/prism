import logging
import os
from typing import Protocol

import httpx

from prism_transaction_events.events import (
    RehydrationTransactionEvent,
    TransformTransactionEvent,
)

TransactionEvent = TransformTransactionEvent | RehydrationTransactionEvent

LOGGER = logging.getLogger(__name__)


class TransactionEventSink(Protocol):
    def emit(self, event: TransactionEvent) -> None:
        """Emit one transaction event."""


class NoopTransactionSink:
    def emit(self, event: TransactionEvent) -> None:
        return None


class InMemoryTransactionSink:
    def __init__(self) -> None:
        self.events: list[TransactionEvent] = []

    def emit(self, event: TransactionEvent) -> None:
        self.events.append(event)


class HttpTransactionSink:
    def __init__(
        self,
        endpoint: str,
        *,
        tenant_header: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 1.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.tenant_header = tenant_header or "X-Prism-Tenant"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def emit(self, event: TransactionEvent) -> None:
        headers = {"Content-Type": "application/json", self.tenant_header: event.tenant_id}
        if self.api_key:
            headers["X-Prism-API-Key"] = self.api_key
        with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
            client.post(
                self.endpoint,
                headers=headers,
                content=event.model_dump_json(),
            ).raise_for_status()


def load_transaction_sink_from_env() -> TransactionEventSink:
    enabled = os.getenv("PRISM_TRANSACTION_LOGGING_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if not enabled:
        return NoopTransactionSink()
    endpoint = os.getenv("PRISM_TRANSACTION_INGEST_URL", "").strip()
    if not endpoint:
        return NoopTransactionSink()
    timeout = float(os.getenv("PRISM_TRANSACTION_SINK_TIMEOUT_SECONDS", "1.0"))
    return HttpTransactionSink(
        endpoint,
        tenant_header=os.getenv("PRISM_TRANSACTION_TENANT_HEADER") or None,
        api_key=os.getenv("PRISM_TRANSACTION_API_KEY") or None,
        timeout_seconds=timeout,
    )


def emit_transaction_event(
    event: TransactionEvent,
    sink: TransactionEventSink | None = None,
) -> None:
    active_sink = sink or load_transaction_sink_from_env()
    try:
        active_sink.emit(event)
    except Exception as error:  # pragma: no cover - logging path depends on sink implementation
        LOGGER.warning(
            "event=transaction_event.emit_failed event_type=%s tenant_id=%s error_type=%s",
            event.event_type,
            event.tenant_id,
            type(error).__name__,
        )
