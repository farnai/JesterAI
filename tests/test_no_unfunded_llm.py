import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from backend.routes import create_api_router
from conversation import InMemoryStore
from jester_core import ContextBuilder, InMemoryQuotaService, OutputFilter, PersonaManager
from llm_provider import MockProvider


def test_zero_llm_invocation_when_quota_exhausted():
    """CRITICAL ARCHITECTURAL TEST:
    
    Proves that when a user has exhausted their 3 free questions,
    JESTER returns HTTP 402 Payment Required and the LLM provider is
    invoked ZERO times. No unfunded inferences are ever executed.
    """
    app = FastAPI()
    persona_dir = Path(__file__).resolve().parent.parent / "persona"
    pm = PersonaManager(persona_dir=persona_dir)
    cb = ContextBuilder(persona_manager=pm, max_history_messages=10)
    provider = MockProvider(model="mock-qwen3.6", default_response="Court response.")
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
    )
    app.include_router(router)
    client = TestClient(app)

    user_id = "usr_sovereign_exhausted"

    # Pre-exhaust the quota to 0 remaining free questions
    quota.set_usage(user_id, 3)

    # Initial spy assertion: provider calls must be 0
    assert len(provider.calls) == 0

    # Attempt chat request with exhausted user
    response = client.post(
        "/api/chat",
        json={
            "user_id": user_id,
            "message": "ამიხსენი რამე ძვირადღირებული მსჯელობა.",
        },
    )

    # 1. Assert HTTP 402 Payment Required
    assert response.status_code == 402

    # 2. Assert structured paywall payload
    data = response.json()
    assert data["error"] == "QUOTA_EXCEEDED"
    assert data["user_id"] == user_id
    assert data["remaining_free_questions"] == 0
    assert "upgrade_url" in data
    assert "ამოწურეთ" in data["message"]

    # 3. CRITICAL PROOF: The LLM provider was NEVER called!
    assert len(provider.calls) == 0, (
        f"CRITICAL FAILURE: LLM provider was invoked {len(provider.calls)} times for a user with exhausted quota!"
    )
