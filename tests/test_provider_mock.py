from prism_compiler.providers import MockProvider
from prism_compiler.schemas import ChatMessage


def test_phase4_mock_provider_returns_latest_message() -> None:
    provider = MockProvider()

    response = provider.complete(
        "mock",
        [
            ChatMessage(role="system", content="Be brief"),
            ChatMessage(role="user", content="PERSON_1 emailed EMAIL_1"),
        ],
    )

    assert response.model == "mock"
    assert response.content == "Mock response for: PERSON_1 emailed EMAIL_1"
