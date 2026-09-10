import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from typing import Any, Dict, List

from backend.routes import create_api_router
from jester_core import PersonaManager, ContextBuilder, OutputFilter
from llm_provider import LLMProvider
from conversation import InMemoryStore
from fastapi import FastAPI


class MockLLMProvider(LLMProvider):
    def __init__(self):
        self.model = "mock-llama3.1:8b"
        self.calls = []

    async def chat(self, messages: List[Dict[str, str]], options: Dict[str, Any] | None = None) -> str:
        self.calls.append(messages)
        return "*chuckles* I am the mock jester of the court."

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "provider": "mock", "model": self.model}


@pytest.fixture
def client():
    app = FastAPI()
    persona_dir = Path(__file__).resolve().parent.parent / "persona"
    pm = PersonaManager(persona_dir=persona_dir)
    cb = ContextBuilder(persona_manager=pm, max_history_messages=10)
    provider = MockLLMProvider()
    memory = InMemoryStore()
    flt = OutputFilter()

    router = create_api_router(
        persona_manager=pm,
        context_builder=cb,
        llm_provider=provider,
        memory=memory,
        output_filter=flt,
    )
    app.include_router(router)
    return TestClient(app)


def test_api_chat_and_history(client):
    # 1. Send chat message
    res = client.post("/api/chat", json={"message": "Hello, Jester!"})
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert data["model"] == "mock-llama3.1:8b"
    # Notice *chuckles* should be stripped by OutputFilter!
    assert "*chuckles*" not in data["response"]
    assert "I am the mock jester" in data["response"]

    conv_id = data["conversation_id"]

    # 2. Check conversation history
    res_hist = client.get(f"/api/conversations/{conv_id}")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert len(hist_data["messages"]) == 2
    assert hist_data["messages"][0]["role"] == "user"
    assert hist_data["messages"][0]["content"] == "Hello, Jester!"
    assert hist_data["messages"][1]["role"] == "assistant"

    # 3. Clear conversation
    res_del = client.delete(f"/api/conversations/{conv_id}")
    assert res_del.status_code == 200

    # 4. Verify cleared
    res_hist_after = client.get(f"/api/conversations/{conv_id}")
    assert len(res_hist_after.json()["messages"]) == 0


def test_api_persona_and_health(client):
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_persona = client.get("/api/persona")
    assert res_persona.status_code == 200
    assert "JESTER" in res_persona.json()["system_prompt"]
