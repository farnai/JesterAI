import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from backend.routes import create_api_router
from conversation import InMemoryStore
from jester_core import ContextBuilder, InMemoryQuotaService, OutputFilter, PersonaManager
from llm_provider import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMTimeoutError,
    MockProvider,
)


@pytest.fixture
def v02_setup():
    app = FastAPI()
    persona_dir = Path(__file__).resolve().parent.parent / "persona"
    pm = PersonaManager(persona_dir=persona_dir)
    cb = ContextBuilder(persona_manager=pm, max_history_messages=10)
    provider = MockProvider(
        model="mock-qwen3.6",
        default_response="*laughs* You dare question the court jester?",
    )
    memory = InMemoryStore()
    flt = OutputFilter()
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)

    router = create_api_router(
        persona_manager=pm,
        context_builder=cb,
        llm_provider=provider,
        memory=memory,
        output_filter=flt,
        quota_service=quota,
        api_key="secret_test_key_123",
        require_auth=False,
    )
    app.include_router(router)
    return {
        "client": TestClient(app),
        "provider": provider,
        "quota": quota,
        "pm": pm,
        "cb": cb,
        "memory": memory,
        "flt": flt,
    }


def test_api_chat_with_full_user_context(v02_setup):
    client = v02_setup["client"]

    payload = {
        "user_id": "usr_king_david",
        "message": "რა მელის დღეს?",
        "user_context": {
            "name": "მეფე დავითი",
            "zodiac": "მშვილდოსანი",
            "daily_energy": 88,
        },
    }

    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Sanitizer removed *laughs*
    assert "*laughs*" not in data["response"]
    assert "You dare question the court jester?" in data["response"]

    # Usage metadata verification
    assert data["usage"]["remaining_free_questions"] == 2
    assert data["usage"]["is_paid_user"] is False
    assert data["usage"]["prompt_tokens"] == 20
    assert data["usage"]["completion_tokens"] == 15
    assert data["usage"]["latency_ms"] is not None


def test_api_get_quota_endpoint(v02_setup):
    client = v02_setup["client"]
    user_id = "usr_check_quota_99"

    res = client.get(f"/api/quota/{user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == user_id
    assert data["remaining_free_questions"] == 3
    assert data["allowed"] is True


def test_api_provider_connection_error_handling(v02_setup):
    client = v02_setup["client"]
    provider = v02_setup["provider"]

    # Simulate connection error from LLM provider
    provider.simulated_error = LLMConnectionError("Ollama daemon down", provider="mock")

    res = client.post("/api/chat", json={"message": "Help me!", "user_id": "usr_test"})
    assert res.status_code == 503
    err = res.json()["detail"]
    assert err["error"] == "PROVIDER_UNAVAILABLE"
    assert "სააზროვნო ძრავთან კავშირი შეწყდა" in err["message"]


def test_api_provider_timeout_error_handling(v02_setup):
    client = v02_setup["client"]
    provider = v02_setup["provider"]

    # Simulate timeout error
    provider.simulated_error = LLMTimeoutError("Request timed out", provider="mock")

    res = client.post("/api/chat", json={"message": "Fast response please", "user_id": "usr_test"})
    assert res.status_code == 504
    err = res.json()["detail"]
    assert err["error"] == "PROVIDER_TIMEOUT"


def test_api_persona_and_reload(v02_setup):
    client = v02_setup["client"]

    res_p = client.get("/api/persona")
    assert res_p.status_code == 200
    assert "JESTER" in res_p.json()["system_prompt"]

    res_r = client.post("/api/persona/reload")
    assert res_r.status_code == 200
    assert res_r.json()["status"] == "reloaded"


def test_api_service_auth_enforcement(v02_setup):
    app = FastAPI()
    router = create_api_router(
        persona_manager=v02_setup["pm"],
        context_builder=v02_setup["cb"],
        llm_provider=v02_setup["provider"],
        memory=v02_setup["memory"],
        output_filter=v02_setup["flt"],
        quota_service=v02_setup["quota"],
        api_key="secret_test_key_123",
        require_auth=True,  # Auth enabled
    )
    app.include_router(router)
    client = TestClient(app)

    # 1. Request without auth header -> 401
    res_unauth = client.post("/api/chat", json={"message": "Secret query", "user_id": "usr_test"})
    assert res_unauth.status_code == 401
    assert res_unauth.json()["detail"]["error"] == "UNAUTHORIZED"

    # 2. Request with invalid key -> 401
    res_bad = client.post(
        "/api/chat",
        headers={"X-Jester-API-Key": "wrong_key"},
        json={"message": "Secret query", "user_id": "usr_test"},
    )
    assert res_bad.status_code == 401

    # 3. Request with correct key -> 200
    res_ok = client.post(
        "/api/chat",
        headers={"X-Jester-API-Key": "secret_test_key_123"},
        json={"message": "Authorized query", "user_id": "usr_test"},
    )
    assert res_ok.status_code == 200
