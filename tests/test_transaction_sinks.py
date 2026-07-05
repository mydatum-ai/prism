import httpx
from prism_compiler.schemas import RehydrateRequest, TransformRequest
from prism_policy_runtime import Policy
from prism_rehydration import rehydrate
from prism_transaction_events import (
    HttpTransactionSink,
    InMemoryTransactionSink,
    TransactionEvent,
)
from prism_transformers import transform
from prism_vault_core import InMemoryVault


class FailingSink:
    def emit(self, event: TransactionEvent) -> None:
        raise RuntimeError("sink unavailable")


def test_p18_transform_emits_transaction_event_without_raw_input() -> None:
    sink = InMemoryTransactionSink()

    response = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="Maria Santos emailed maria@example.com",
        ),
        vault=InMemoryVault(),
        policy=Policy.model_validate(
            {
                "domain": "pulse",
                "version": "3",
                "rules": [
                    {
                        "entity_type": "person",
                        "action": "tokenize",
                        "token_prefix": "RESIDENT",
                    }
                ],
            }
        ),
        transaction_sink=sink,
    )

    assert response.transformed_text.startswith("RESIDENT_1")
    event = sink.events[0]
    assert event.event_type == "transform"
    assert event.tenant_id == "tenant_dev"
    assert event.raw_input_text is None
    assert event.model_dump()["scores"]["policy_coverage"] == 1.0


def test_p18_rehydrate_emits_transaction_event_with_blocked_decision() -> None:
    sink = InMemoryTransactionSink()
    vault = InMemoryVault()
    policy = Policy.model_validate(
        {
            "domain": "pulse",
            "rules": [
                {
                    "entity_type": "person",
                    "action": "tokenize",
                    "rehydrate_roles": ["case_worker"],
                }
            ],
        }
    )
    transformed = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="Maria Santos",
        ),
        vault=vault,
        policy=policy,
    )

    response = rehydrate(
        RehydrateRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text=transformed.transformed_text,
            roles=["viewer"],
        ),
        vault=vault,
        policy=policy,
        transaction_sink=sink,
    )

    assert response.diagnostics[0].status == "policy_blocked"
    event = sink.events[0]
    assert event.event_type == "rehydrate"
    assert event.scores.unresolved_token_count == 1
    assert event.raw_input_text is None


def test_p18_transaction_sink_failure_does_not_fail_transform() -> None:
    response = transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_1",
            text="Maria Santos",
        ),
        vault=InMemoryVault(),
        transaction_sink=FailingSink(),
    )

    assert response.transformed_text == "PERSON_1"


def test_p18_http_transaction_sink_posts_event_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(202)

    memory_sink = InMemoryTransactionSink()
    transform(
        TransformRequest(
            tenant_id="tenant_dev",
            app_id="pulse",
            session_id="session_2",
            text="Maria Santos",
        ),
        vault=InMemoryVault(),
        transaction_sink=memory_sink,
    )

    transport = httpx.MockTransport(handler)
    sink = HttpTransactionSink(
        "https://enterprise.example.test/transactions",
        api_key="secret",
        transport=transport,
    )
    sink.emit(memory_sink.events[0])

    headers = captured["headers"]
    assert isinstance(headers, httpx.Headers)
    assert headers["X-Prism-Tenant"] == "tenant_dev"
    assert headers["X-Prism-API-Key"] == "secret"
    assert '"event_type":"transform"' in str(captured["body"])
