from collections.abc import Iterable

from prism_compiler.providers import ProviderResponse
from prism_compiler.schemas import ChatMessage, OpenAIChatCompletionRequest
from prism_gateway.routes import chat_completions_endpoint
from prism_vault_core import GLOBAL_VAULT


class EchoTokenProvider:
    def complete(self, model: str, messages: Iterable[ChatMessage]) -> ProviderResponse:
        latest = ""
        for message in messages:
            latest = message.content
        return ProviderResponse(model=model, content=f"Provider saw {latest}")


def test_phase4_proxy_flow_transforms_provider_input_and_rehydrates_output() -> None:
    GLOBAL_VAULT.clear()

    response = chat_completions_endpoint(
        OpenAIChatCompletionRequest(
            model="mock",
            messages=[ChatMessage(role="user", content="John Smith emailed john@email.com")],
            metadata={
                "tenant_id": "tenant_dev",
                "app_id": "pulse",
                "session_id": "session_1",
            },
        ),
        provider=EchoTokenProvider(),
    )

    assert response.choices[0].message.content == "Provider saw John Smith emailed john@email.com"
