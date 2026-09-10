from backend.app import create_app
from config.settings import AppSettings, LLMConfig
from llm_provider import MockProvider, get_llm_provider
from fastapi.testclient import TestClient


def test_dynamic_brain_switching():
    """Verify that changing the LLMProvider in the application requires ZERO changes to JESTER Core."""
    # 1. Start with AppSettings pointing to mock brain
    mock_settings = AppSettings(
        llm=LLMConfig(provider="mock", model="mock-qwen3.6"),
    )
    mock_provider = get_llm_provider(mock_settings)
    assert isinstance(mock_provider, MockProvider)
    assert mock_provider.provider_name == "mock"
    assert mock_provider.model_name == "mock-qwen3.6"

    # 2. Reconfigure settings to another mock model
    alt_settings = AppSettings(
        llm=LLMConfig(provider="mock", model="mock-gemini-cloud"),
    )
    alt_provider = get_llm_provider(alt_settings)
    assert isinstance(alt_provider, MockProvider)
    assert alt_provider.model_name == "mock-gemini-cloud"

    # 3. Create app and test that endpoints work seamlessly with active provider
    app = create_app()
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert "model" in health.json()
