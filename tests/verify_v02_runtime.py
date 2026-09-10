import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from backend.app import app

def run_verification():
    print("==================================================")
    print("  JESTER v0.2 RUNTIME VERIFICATION SUITE")
    print("==================================================")
    client = TestClient(app)

    # 1. Health Endpoint
    print("\n[1] Testing /api/health...")
    res_health = client.get("/api/health")
    print(f"    Status Code: {res_health.status_code}")
    print(f"    Body: {res_health.json()}")
    assert res_health.status_code == 200
    assert res_health.json()["provider"] == "ollama"
    assert res_health.json()["model"] == "qwen3.6:latest"
    print("    --> PASS: Provider-agnostic health check operational.")

    # 2. Persona Endpoints
    print("\n[2] Testing /api/persona and /api/persona/reload...")
    res_persona = client.get("/api/persona")
    assert res_persona.status_code == 200
    assert "JESTER" in res_persona.json()["system_prompt"]
    res_reload = client.post("/api/persona/reload")
    assert res_reload.status_code == 200
    assert res_reload.json()["status"] == "reloaded"
    print("    --> PASS: Persona inspection and hot-reload functional.")

    # 3. Quota Check Endpoint
    print("\n[3] Testing /api/quota/{user_id}...")
    user_id = "usr_runtime_verify_001"
    res_quota = client.get(f"/api/quota/{user_id}")
    assert res_quota.status_code == 200
    q_data = res_quota.json()
    print(f"    Initial Quota: {q_data}")
    assert q_data["remaining_free_questions"] == 3
    assert q_data["allowed"] is True
    print("    --> PASS: Quota inspection endpoint functional.")

    # 4. Chat with UserContext (Live Ollama test)
    print("\n[4] Testing /api/chat with Sovereign UserContext...")
    payload = {
        "user_id": user_id,
        "message": "მომესალმე ჩემო მასხარავ მოკლედ.",
        "user_context": {
            "name": "ალექსანდრე",
            "zodiac": "კირჩხიბი",
            "daily_energy": 85,
        }
    }
    print("    Sending live chat request to local Ollama (qwen3.6:latest)...")
    res_chat = client.post("/api/chat", json=payload)
    print(f"    Status Code: {res_chat.status_code}")
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    print(f"    Response snippet: {chat_data['response'][:120]}...")
    print(f"    Model: {chat_data['model']}")
    print(f"    Provider: {chat_data['provider']}")
    print(f"    Usage: {chat_data['usage']}")
    assert chat_data["usage"]["remaining_free_questions"] == 2
    conv_id = chat_data["conversation_id"]
    print("    --> PASS: Live chat turn completed successfully.")

    # 5. Conversation History Endpoints
    print("\n[5] Testing /api/conversations endpoints...")
    res_hist = client.get(f"/api/conversations/{conv_id}")
    assert res_hist.status_code == 200
    assert len(res_hist.json()["messages"]) == 2
    res_del = client.delete(f"/api/conversations/{conv_id}")
    assert res_del.status_code == 200
    assert len(client.get(f"/api/conversations/{conv_id}").json()["messages"]) == 0
    print("    --> PASS: Session history and clearance functional.")

    # 6. Quota Exhaustion & Paywall Verification
    print("\n[6] Testing Quota Exhaustion & Paywall (HTTP 402)...")
    # Consume remaining 2 questions
    app.state.quota_service.set_usage(user_id, 3)
    
    # Verify quota endpoint reflects 0 remaining
    q_exhausted = client.get(f"/api/quota/{user_id}").json()
    assert q_exhausted["remaining_free_questions"] == 0
    assert q_exhausted["allowed"] is False

    # Attempt to chat when quota is exhausted
    res_paywall = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "Can I have another answer?"}
    )
    print(f"    Paywall Status Code: {res_paywall.status_code}")
    assert res_paywall.status_code == 402
    paywall_data = res_paywall.json()
    print(f"    Paywall Body: {paywall_data}")
    assert paywall_data["error"] == "QUOTA_EXCEEDED"
    assert paywall_data["remaining_free_questions"] == 0
    print("    --> PASS: Pre-inference paywall blocks exhausted users.")

    # 7. Frontend Static Files & Docs
    print("\n[7] Testing Frontend Root & Swagger UI...")
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "JESTER" in res_index.text
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    print("    --> PASS: Web UI and interactive docs served properly.")

    # 8. Security Check: No secrets leaked
    print("\n[8] Testing Secret Isolation...")
    assert "GEMINI_API_KEY" not in res_index.text
    assert "api_key" not in res_health.text
    print("    --> PASS: Zero secrets leaked to client.")

    print("\n==================================================")
    print("  ALL RUNTIME VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
