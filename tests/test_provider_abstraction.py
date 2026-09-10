import pytest
from llm_provider import (
    GeminiProvider,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMMessage,
    LLMRequest,
    MockProvider,
    OllamaProvider,
    get_llm_provider,
)
from pydantic import BaseModel


class DummySettings(BaseModel):
    class DummyLLM(BaseModel):
        provider: str = "mock"
        model: str = "mock-model"
        base_url: str = "http://localhost:11434"
        api_key: str = ""
        temperature: float = 0.75
        top_p: float = 0.9
        num_ctx: int = 8192
        timeout_seconds: float = 1.0

    llm: DummyLLM = DummyLLM()


@pytest.mark.asyncio
async def test_mock_provider_execution():
    provider = MockProvider(model="mock-qwen3.6", default_response="Court answer.")
    assert provider.provider_name == "mock"
    assert provider.model_name == "mock-qwen3.6"

    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        temperature=0.7,
    )
    res = await provider.chat(req)

    assert res.content == "Court answer."
    assert res.provider == "mock"
    assert res.model == "mock-qwen3.6"
    assert res.latency_ms > 0
    assert len(provider.calls) == 1

    health = await provider.health_check()
    assert health.healthy is True
    assert health.name == "mock"


@pytest.mark.asyncio
async def test_ollama_provider_connection_error_mapping():
    # Use a non-existent port to force connection failure
    provider = OllamaProvider(
        base_url="http://127.0.0.1:59999",
        model="qwen3.6:latest",
        timeout_seconds=0.5,
    )
    assert provider.provider_name == "ollama"
    assert provider.model_name == "qwen3.6:latest"

    req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

    with pytest.raises(LLMConnectionError) as exc_info:
        await provider.chat(req)

    assert exc_info.value.provider == "ollama"
    assert "Unable to connect to Ollama" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_provider_missing_key_error():
    provider = GeminiProvider(api_key="", model="gemini-1.5-flash")
    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-1.5-flash"

    req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.chat(req)

    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


def test_provider_factory_dynamic_selection():
    # 1. Mock selection
    cfg_mock = DummySettings(llm=DummySettings.DummyLLM(provider="mock", model="qwen-mock"))
    p_mock = get_llm_provider(cfg_mock)
    assert isinstance(p_mock, MockProvider)
    assert p_mock.provider_name == "mock"

    # 2. Ollama selection
    cfg_ollama = DummySettings(llm=DummySettings.DummyLLM(provider="ollama", model="qwen3.6:latest"))
    p_ollama = get_llm_provider(cfg_ollama)
    assert isinstance(p_ollama, OllamaProvider)
    assert p_ollama.provider_name == "ollama"
    assert p_ollama.model_name == "qwen3.6:latest"

    # 3. Gemini selection
    cfg_gemini = DummySettings(llm=DummySettings.DummyLLM(provider="gemini", model="gemini-1.5-flash", api_key="secret"))
    p_gemini = get_llm_provider(cfg_gemini)
    assert isinstance(p_gemini, GeminiProvider)
    assert p_gemini.provider_name == "gemini"

    # 4. Unsupported provider raises ValueError
    cfg_invalid = DummySettings(llm=DummySettings.DummyLLM(provider="unsupported_brain"))
    with pytest.raises(ValueError) as exc:
        get_llm_provider(cfg_invalid)
    assert "Unsupported LLM provider" in str(exc.value)
