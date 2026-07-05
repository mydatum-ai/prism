import httpx
from prism_compiler.providers import OpenAIProvider
from prism_compiler.schemas import ChatMessage


def test_phase4_openai_provider_uses_chat_completions_api() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "model": "gpt-test",
                "choices": [{"message": {"content": "Hello PERSON_1"}}],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAIProvider(api_key="test-key", base_url="https://example.test/v1", client=client)

    response = provider.complete("gpt-test", [ChatMessage(role="user", content="Hi PERSON_1")])

    assert response.content == "Hello PERSON_1"
    assert response.model == "gpt-test"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert "Hi PERSON_1" in str(captured["body"])
