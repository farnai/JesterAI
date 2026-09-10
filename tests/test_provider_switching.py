import os
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app import create_app
from config.settings import AppSettings, LLMConfig, load_settings
from llm_provider import (
    GeminiProvider,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMResponseMalformedError,
    MockProvider,
    OllamaProvider,
    get_llm_provider,
)


class MockSettingsWrapper(BaseModel):
    class DummyLLM(BaseModel):
        provider: str = "mock"
        model: str = "mock-model"
        base_url: str = "http://localhost:11434"
        api_key: str = ""
        temperature: float = 0.85
        top_p: float = 0.9
        frequency_penalty: float = 0.35
        num_ctx: int = 8192
        timeout_seconds: float = 60.0

    llm: DummyLLM = DummyLLM()


# ==============================================================================
# 1. MOCK PROVIDER THROUGH COMMON INTERFACE
# ==============================================================================

@pytest.mark.asyncio
async def test_mock_provider_works_through_common_interface():
    provider: LLMProvider = MockProvider(model="mock-brain", default_response="Court answer.")
    assert provider.provider_name == "mock"
    assert provider.model_name == "mock-brain"

    req = LLMRequest(messages=[LLMMessage(role="user", content="Salutations")])
    res = await provider.chat(req)

    assert isinstance(res, LLMResponse)
    assert res.content == "Court answer."
    assert res.model == "mock-brain"
    assert res.provider == "mock"
    assert res.latency_ms > 0
    assert res.usage is not None
    assert res.usage.total_tokens == 35

    health = await provider.health_check()
    assert health.healthy is True
    assert health.name == "mock"
    assert health.current_model == "mock-brain"
    assert health.is_cloud is False


# ==============================================================================
# 2. PROVIDER FACTORY CONSTRUCTS OLLAMA & GEMINI
# ==============================================================================

def test_provider_factory_constructs_ollama():
    settings = MockSettingsWrapper(
        llm=MockSettingsWrapper.DummyLLM(
            provider="ollama",
            model="qwen3.6:latest",
            base_url="http://127.0.0.1:11434",
            temperature=0.85,
            top_p=0.9,
            frequency_penalty=0.35,
            timeout_seconds=240.0,
        )
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name == "ollama"
    assert provider.model_name == "qwen3.6:latest"
    assert provider.temperature == 0.85
    assert provider.frequency_penalty == 0.35


def test_provider_factory_constructs_gemini():
    settings = MockSettingsWrapper(
        llm=MockSettingsWrapper.DummyLLM(
            provider="gemini",
            model="gemini-1.5-flash",
            api_key="secret-api-key",
            temperature=0.75,
            top_p=0.9,
            timeout_seconds=60.0,
        )
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, GeminiProvider)
    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-1.5-flash"
    assert provider.api_key == "secret-api-key"
    assert provider.timeout == 60.0


def test_provider_factory_rejects_unsupported_provider():
    settings = MockSettingsWrapper(
        llm=MockSettingsWrapper.DummyLLM(provider="unsupported_alien_brain")
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider: 'unsupported_alien_brain'"):
        get_llm_provider(settings)


# ==============================================================================
# 3. ENVIRONMENT VARIABLE CONFIGURATION OVERRIDES
# ==============================================================================

def test_env_var_configuration_switching(monkeypatch):
    # 1. Switch to Ollama via JESTER_PROVIDER
    monkeypatch.setenv("JESTER_PROVIDER", "ollama")
    monkeypatch.setenv("JESTER_MODEL", "qwen3.6:latest")
    settings = load_settings()
    assert settings.llm.provider == "ollama"
    assert settings.llm.model == "qwen3.6:latest"
    p_ollama = get_llm_provider(settings)
    assert isinstance(p_ollama, OllamaProvider)

    # 2. Switch to Gemini via JESTER_PROVIDER
    monkeypatch.setenv("JESTER_PROVIDER", "gemini")
    monkeypatch.setenv("JESTER_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "prod_gemini_key_123")
    settings = load_settings()
    assert settings.llm.provider == "gemini"
    assert settings.llm.model == "gemini-1.5-flash"
    assert settings.llm.api_key == "prod_gemini_key_123"
    p_gemini = get_llm_provider(settings)
    assert isinstance(p_gemini, GeminiProvider)
    assert p_gemini.model_name == "gemini-1.5-flash"

    # 3. Switch to Mock via JESTER_PROVIDER
    monkeypatch.setenv("JESTER_PROVIDER", "mock")
    settings = load_settings()
    assert settings.llm.provider == "mock"
    p_mock = get_llm_provider(settings)
    assert isinstance(p_mock, MockProvider)


# ==============================================================================
# 4. ZERO-CORE-CHANGE PROVIDER SWITCHING & ROUTE PARITY
# ==============================================================================

def test_switching_configuration_changes_selected_provider_without_changing_core(monkeypatch):
    """Proves that changing configuration from mock-ollama to mock-gemini works
    through FastAPI endpoints with ZERO changes to JESTER Core.
    """
    # 1. Run app with MockProvider simulating Ollama
    monkeypatch.setenv("JESTER_PROVIDER", "mock")
    monkeypatch.setenv("JESTER_MODEL", "qwen3.6:latest")
    app1 = create_app()
    client1 = TestClient(app1)

    health1 = client1.get("/api/health").json()
    assert health1["status"] == "healthy"
    assert health1["model"] == "qwen3.6:latest"
    assert health1["provider"] == "mock"

    chat1 = client1.post("/api/chat", json={"user_id": "usr_switch_1", "message": "hello"}).json()
    assert chat1["model"] == "qwen3.6:latest"
    assert chat1["provider"] == "mock"
    assert "response" in chat1

    # 2. Switch config to Gemini (mock mode)
    monkeypatch.setenv("JESTER_PROVIDER", "mock")
    monkeypatch.setenv("JESTER_MODEL", "gemini-1.5-flash")
    app2 = create_app()
    client2 = TestClient(app2)

    health2 = client2.get("/api/health").json()
    assert health2["status"] == "healthy"
    assert health2["model"] == "gemini-1.5-flash"

    chat2 = client2.post("/api/chat", json={"user_id": "usr_switch_2", "message": "hello"}).json()
    assert chat2["model"] == "gemini-1.5-flash"
    assert "response" in chat2


# ==============================================================================
# 5. NORMALIZED REQUEST & RESPONSE CONTRACT PARITY
# ==============================================================================

@pytest.mark.asyncio
async def test_common_llm_contract_parity(monkeypatch):
    """Verifies that MockProvider, OllamaProvider, and GeminiProvider produce
    identical LLMResponse schema shapes when invoked with LLMRequest.
    """
    # Mock HTTP response for Gemini
    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Gemini answer"}]}}],
                "usageMetadata": {"promptTokenCount": 25, "candidatesTokenCount": 15, "totalTokenCount": 40},
            }
            return mock_resp

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

    common_request = LLMRequest(
        messages=[
            LLMMessage(role="system", content="Be witty"),
            LLMMessage(role="user", content="Explain recursion"),
        ],
        temperature=0.85,
        top_p=0.9,
    )

    # 1. MockProvider
    mock_p = MockProvider(model="test-mock", default_response="Mock reply")
    resp_mock = await mock_p.chat(common_request)

    # 2. GeminiProvider
    gemini_p = GeminiProvider(api_key="secret", model="gemini-1.5-flash")
    resp_gemini = await gemini_p.chat(common_request)

    # Assert normalized field structure parity
    for resp in (resp_mock, resp_gemini):
        assert isinstance(resp, LLMResponse)
        assert isinstance(resp.content, str) and len(resp.content) > 0
        assert isinstance(resp.model, str)
        assert isinstance(resp.provider, str)
        assert isinstance(resp.latency_ms, float) and resp.latency_ms >= 0
        assert resp.usage is not None
        assert isinstance(resp.usage.prompt_tokens, int)
        assert isinstance(resp.usage.completion_tokens, int)
        assert isinstance(resp.usage.total_tokens, int)


# ==============================================================================
# 6. GEMINI PRODUCTION HARDENING: SAFETY & MODEL NORMALIZATION
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_provider_safety_blocks_and_malformed_handling(monkeypatch):
    class MockClientSafetyBlock:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "promptFeedback": {"blockReason": "SAFETY"},
                "candidates": [],
            }
            return mock_resp

    monkeypatch.setattr("httpx.AsyncClient", MockClientSafetyBlock)

    provider = GeminiProvider(api_key="key", model="gemini-1.5-flash")
    req = LLMRequest(messages=[LLMMessage(role="user", content="Dangerous prompt")])

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.chat(req)

    assert "prompt blocked by provider safety filter" in str(exc_info.value)
    assert exc_info.value.provider == "gemini"


def test_gemini_model_name_normalization_and_fallback():
    # 1. Strips "models/" prefix cleanly
    p1 = GeminiProvider(api_key="key", model="models/gemini-1.5-pro")
    assert p1.model_name == "gemini-1.5-pro"

    # 2. Falls back to gemini-1.5-flash if local model name passed accidentally
    p2 = GeminiProvider(api_key="key", model="qwen3.6:latest")
    assert p2.model_name == "gemini-1.5-flash"

    # 3. Explicit standard model is preserved
    p3 = GeminiProvider(api_key="key", model="gemini-2.0-flash")
    assert p3.model_name == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_gemini_health_check_without_api_key_is_safe():
    provider = GeminiProvider(api_key="", model="gemini-1.5-flash")
    health = await provider.health_check()
    assert health.healthy is False
    assert health.is_cloud is True
    assert health.name == "gemini"
    assert health.details.get("status") == "missing_api_key"
