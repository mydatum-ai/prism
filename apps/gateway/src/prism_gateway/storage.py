import json
import os
import sqlite3
from pathlib import Path

from prism_compiler.schemas import AuditEvent


def default_storage_path() -> Path:
    return Path(os.getenv("PRISM_AUDIT_DB", ".prism/audit.sqlite3"))


class AuditStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_storage_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    app_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS audit_events_tenant_created_idx
                ON audit_events (tenant_id, created_at)
                """
            )

    def record(self, event: AuditEvent) -> None:
        payload = event.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO audit_events (
                    request_id, tenant_id, app_id, session_id, event_type, created_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.request_id,
                    event.tenant_id,
                    event.app_id,
                    event.session_id,
                    event.event_type,
                    event.created_at.isoformat(),
                    json.dumps(payload, sort_keys=True),
                ),
            )

    def list_for_tenant(self, tenant_id: str, limit: int = 100) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM audit_events
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]


def active_audit_store() -> AuditStore:
    return AuditStore()
