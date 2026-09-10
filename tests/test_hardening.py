import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import create_api_router
from backend.schemas import ChatRequest, UserContext
from config.settings import SecurityConfig
from conversation import InMemoryStore
from jester_core import ContextBuilder, OutputFilter, PersonaManager
from jester_core.quota import InMemoryQuotaService, QuotaDecision
from llm_provider.base import LLMMessage, LLMProvider, LLMRequest, LLMResponse, LLMTokenUsage
from llm_provider.exceptions import (
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from llm_provider.gemini_provider import GeminiProvider


class DelayedMockProvider(LLMProvider):
    """Mock provider with simulated latency and call counting for concurrency testing."""

    def __init__(self, delay_seconds: float = 0.05, response_text: str = "Jester witty response"):
        self.delay_seconds = delay_seconds
        self.response_text = response_text
        self.call_count = 0
        self.simulated_error: Optional[Exception] = None

    @property
    def provider_name(self) -> str:
        return "mock_delayed"

    @property
    def model_name(self) -> str:
        return "mock-concurrency-v1"

    async def chat(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.simulated_error:
            raise self.simulated_error
        return LLMResponse(
            content=self.response_text,
            model=self.model_name,
            provider=self.provider_name,
            latency_ms=self.delay_seconds * 1000,
            usage=LLMTokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    async def health_check(self):
        from llm_provider.base import ProviderMetadata
        return ProviderMetadata(
            name=self.provider_name,
            current_model=self.model_name,
            is_cloud=False,
            healthy=True,
            details={"status": "ready"},
        )


@pytest.fixture
def base_components():
    persona_dir = Path(__file__).resolve().parent.parent / "persona"
    pm = PersonaManager(persona_dir=persona_dir)
    cb = ContextBuilder(persona_manager=pm)
    flt = OutputFilter()
    memory = InMemoryStore()
    return {"pm": pm, "cb": cb, "flt": flt, "memory": memory}


# ==============================================================================
# 1. HIGH — GEMINI API KEY TRANSMISSION (HEADER VS URL)
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_provider_uses_header_and_never_leaks_key_in_url(monkeypatch):
    captured_requests = []

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_requests.append(("POST", str(url), headers, json))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Gemini witty answer"}]}}],
                "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10, "totalTokenCount": 30},
            }
            return mock_resp

        async def get(self, url, headers=None):
            captured_requests.append(("GET", str(url), headers, None))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "displayName": "gemini-1.5-flash",
                "inputTokenLimit": 1048576,
                "outputTokenLimit": 8192,
            }
            return mock_resp

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

    api_key_secret = "AIzaSyD_TEST_SECRET_KEY_999888"
    provider = GeminiProvider(api_key=api_key_secret, model="gemini-1.5-flash")

    # 1. Verify chat() uses x-goog-api-key header and NOT query string ?key=
    chat_req = LLMRequest(messages=[LLMMessage(role="user", content="Royal salute")])
    chat_resp = await provider.chat(chat_req)
    assert chat_resp.content == "Gemini witty answer"

    assert len(captured_requests) >= 1
    method, url, headers, _ = captured_requests[0]
    assert method == "POST"
    assert api_key_secret not in url
    assert "?key=" not in url
    assert headers.get("x-goog-api-key") == api_key_secret

    # 2. Verify health_check() uses x-goog-api-key header and NOT query string ?key=
    meta = await provider.health_check()
    assert meta.healthy is True
    assert len(captured_requests) >= 2
    method, url, headers, _ = captured_requests[1]
    assert method == "GET"
    assert api_key_secret not in url
    assert "?key=" not in url
    assert headers.get("x-goog-api-key") == api_key_secret


# ==============================================================================
# 2. HIGH — SERVICE AUTHENTICATION (FAIL-FAST & ENDPOINT PROTECTION)
# ==============================================================================

def test_service_auth_fail_fast_when_key_missing_or_empty(base_components):
    # 1. Pydantic SecurityConfig validation fail-fast
    with pytest.raises(ValueError, match="require_auth=True requires a non-empty JESTER_API_KEY"):
        SecurityConfig(require_auth=True, api_key="")

    with pytest.raises(ValueError, match="require_auth=True requires a non-empty JESTER_API_KEY"):
        SecurityConfig(require_auth=True, api_key="   ")

    # 2. Router creation fail-fast
    quota = InMemoryQuotaService(free_questions_limit=3)
    provider = DelayedMockProvider(delay_seconds=0)

    with pytest.raises(ValueError, match="require_auth=True requires a non-empty JESTER_API_KEY"):
        create_api_router(
            persona_manager=base_components["pm"],
            context_builder=base_components["cb"],
            llm_provider=provider,
            memory=base_components["memory"],
            output_filter=base_components["flt"],
            quota_service=quota,
            api_key="",
            require_auth=True,
        )


def test_service_auth_protects_all_required_endpoints(base_components):
    quota = InMemoryQuotaService(free_questions_limit=3)
    provider = DelayedMockProvider(delay_seconds=0)
    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        api_key="valid_sovereign_key_456",
        require_auth=True,
    )
    app.include_router(router)
    client = TestClient(app)

    # Protected Endpoints list
    # POST /api/chat
    # GET /api/quota/{user_id}
    # GET /api/conversations/{id}
    # DELETE /api/conversations/{id}
    # POST /api/persona/reload

    # Test 1: POST /api/chat rejected without auth header
    res = client.post("/api/chat", json={"user_id": "usr_test", "message": "hello"})
    assert res.status_code == 401
    assert res.json()["detail"]["error"] == "UNAUTHORIZED"

    # Test 2: POST /api/chat rejected with wrong auth header
    res = client.post(
        "/api/chat",
        headers={"X-Jester-API-Key": "wrong_key"},
        json={"user_id": "usr_test", "message": "hello"},
    )
    assert res.status_code == 401

    # Test 3: POST /api/chat allowed with valid auth header
    res = client.post(
        "/api/chat",
        headers={"X-Jester-API-Key": "valid_sovereign_key_456"},
        json={"user_id": "usr_test", "message": "hello"},
    )
    assert res.status_code == 200

    # Test 4: GET /api/quota/{user_id}
    res_unauth = client.get("/api/quota/usr_test")
    assert res_unauth.status_code == 401
    res_auth = client.get("/api/quota/usr_test", headers={"X-Jester-API-Key": "valid_sovereign_key_456"})
    assert res_auth.status_code == 200

    # Test 5: GET /api/conversations/{id}
    res_unauth = client.get("/api/conversations/conv_123")
    assert res_unauth.status_code == 401
    res_auth = client.get("/api/conversations/conv_123", headers={"X-Jester-API-Key": "valid_sovereign_key_456"})
    assert res_auth.status_code == 200

    # Test 6: DELETE /api/conversations/{id}
    res_unauth = client.delete("/api/conversations/conv_123")
    assert res_unauth.status_code == 401
    res_auth = client.delete("/api/conversations/conv_123", headers={"X-Jester-API-Key": "valid_sovereign_key_456"})
    assert res_auth.status_code == 200

    # Test 7: POST /api/persona/reload
    res_unauth = client.post("/api/persona/reload")
    assert res_unauth.status_code == 401
    res_auth = client.post("/api/persona/reload", headers={"X-Jester-API-Key": "valid_sovereign_key_456"})
    assert res_auth.status_code == 200

    # Test 8: GET /api/health and GET /api/persona remain unauthenticated
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/persona").status_code == 200


def test_service_auth_disabled_allows_unauthenticated_requests(base_components):
    quota = InMemoryQuotaService(free_questions_limit=3)
    provider = DelayedMockProvider(delay_seconds=0)
    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        api_key="",
        require_auth=False,
    )
    app.include_router(router)
    client = TestClient(app)

    # All endpoints are accessible without X-Jester-API-Key header
    assert client.post("/api/chat", json={"user_id": "usr_dev", "message": "hi"}).status_code == 200
    assert client.get("/api/quota/usr_dev").status_code == 200
    assert client.post("/api/persona/reload").status_code == 200


# ==============================================================================
# 3. MEDIUM — ATOMIC QUOTA RESERVATION & CONCURRENCY
# ==============================================================================

def test_concurrent_quota_reservation_race_condition(base_components):
    """Specifically tests:
    - User has quota = 1
    - 3 concurrent requests arrive simultaneously
    - Expected:
      * at most 1 request reaches the LLM provider
      * other requests are rejected by quota (HTTP 402)
      * quota cannot become negative
      * no duplicate consumption occurs (exact usage = 1)
    """
    # User gets exactly 1 free question
    quota = InMemoryQuotaService(free_questions_limit=1, enforce=True)
    # 100ms inference delay ensures concurrent requests overlap during inference
    provider = DelayedMockProvider(delay_seconds=0.10, response_text="Only one shall pass!")

    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        require_auth=False,
    )
    app.include_router(router)

    client = TestClient(app)
    user_id = "usr_concurrent_race_test"

    def send_request(msg_num: int):
        return client.post(
            "/api/chat",
            json={"user_id": user_id, "message": f"Concurrent query #{msg_num}"},
        )

    # Launch 3 simultaneous requests across threads
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, 4)]
        responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]

    # Exactly 1 request must succeed (HTTP 200)
    assert status_codes.count(200) == 1, f"Expected exactly 1 success, got {status_codes}"

    # Exactly 2 requests must be blocked by quota paywall (HTTP 402)
    assert status_codes.count(402) == 2, f"Expected 2 quota rejections, got {status_codes}"

    # Verify provider call count was at most 1
    assert provider.call_count == 1, f"Provider was called {provider.call_count} times, expected 1"

    # Verify quota cannot become negative and exact usage is 1
    assert quota.get_usage(user_id) == 1
    assert quota.get_active_reservations(user_id) == 0

    quota_check = client.get(f"/api/quota/{user_id}").json()
    assert quota_check["remaining_free_questions"] == 0
    assert quota_check["allowed"] is False


def test_quota_reservation_released_on_provider_failure(base_components):
    """When LLM inference fails, the reserved quota turn is released back to the user."""
    quota = InMemoryQuotaService(free_questions_limit=1, enforce=True)
    provider = DelayedMockProvider(delay_seconds=0)
    provider.simulated_error = LLMConnectionError("Network connection dropped", provider="mock")

    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        require_auth=False,
    )
    app.include_router(router)
    client = TestClient(app)
    user_id = "usr_failure_release_test"

    # Send request that fails
    res = client.post("/api/chat", json={"user_id": user_id, "message": "Will fail"})
    assert res.status_code == 503

    # Reservation was released: usage is 0, active reservations is 0, user still has 1 remaining
    assert quota.get_usage(user_id) == 0
    assert quota.get_active_reservations(user_id) == 0

    quota_check = client.get(f"/api/quota/{user_id}").json()
    assert quota_check["remaining_free_questions"] == 1
    assert quota_check["allowed"] is True


# ==============================================================================
# 4. LOW — FAILURE OBSERVABILITY AUDIT LOGGING
# ==============================================================================

def test_failure_observability_audit_logging(base_components):
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)
    provider = DelayedMockProvider(delay_seconds=0)

    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        require_auth=False,
    )
    app.include_router(router)
    client = TestClient(app)

    with patch("backend.routes.log_request_audit") as mock_audit:
        # 1. Connection Error -> 503
        provider.simulated_error = LLMConnectionError("Connection refused", provider="mock")
        res1 = client.post("/api/chat", json={"user_id": "usr_obs", "message": "test connection error"})
        assert res1.status_code == 503
        assert mock_audit.called
        last_call_kwargs = mock_audit.call_args.kwargs
        assert last_call_kwargs["http_status"] == 503
        assert last_call_kwargs["error"] == "PROVIDER_UNAVAILABLE"
        assert last_call_kwargs["quota_status"] == "reservation_released"

        # 2. Timeout Error -> 504
        provider.simulated_error = LLMTimeoutError("Timed out", provider="mock")
        res2 = client.post("/api/chat", json={"user_id": "usr_obs", "message": "test timeout"})
        assert res2.status_code == 504
        last_call_kwargs = mock_audit.call_args.kwargs
        assert last_call_kwargs["http_status"] == 504
        assert last_call_kwargs["error"] == "PROVIDER_TIMEOUT"

        # 3. Rate Limit Error -> 429
        provider.simulated_error = LLMRateLimitError("Rate limit hit", provider="mock")
        res3 = client.post("/api/chat", json={"user_id": "usr_obs", "message": "test rate limit"})
        assert res3.status_code == 429
        last_call_kwargs = mock_audit.call_args.kwargs
        assert last_call_kwargs["http_status"] == 429
        assert last_call_kwargs["error"] == "PROVIDER_RATE_LIMIT"


# ==============================================================================
# 5. LOW — MANDATORY USER_ID
# ==============================================================================

def test_mandatory_user_id_enforcement(base_components):
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)
    provider = DelayedMockProvider(delay_seconds=0)

    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        require_auth=False,
    )
    app.include_router(router)
    client = TestClient(app)

    # Missing user_id in JSON payload -> HTTP 422 Unprocessable Entity
    res_missing = client.post("/api/chat", json={"message": "Query without user_id"})
    assert res_missing.status_code == 422

    # Empty user_id in JSON payload -> HTTP 422 (min_length=1)
    res_empty = client.post("/api/chat", json={"user_id": "", "message": "Query with empty user_id"})
    assert res_empty.status_code == 422

    # Valid user_id -> HTTP 200
    res_valid = client.post("/api/chat", json={"user_id": "usr_explicit_100", "message": "Valid query"})
    assert res_valid.status_code == 200


# ==============================================================================
# 6. LOW — ERROR RESPONSE CONSISTENCY (STANDARDIZED 500)
# ==============================================================================

def test_generic_500_error_response_shape(base_components):
    quota = InMemoryQuotaService(free_questions_limit=3, enforce=True)
    provider = DelayedMockProvider(delay_seconds=0)
    # Simulate an unexpected generic internal error
    provider.simulated_error = RuntimeError("Unexpected internal crash in provider runtime")

    app = FastAPI()
    router = create_api_router(
        persona_manager=base_components["pm"],
        context_builder=base_components["cb"],
        llm_provider=provider,
        memory=base_components["memory"],
        output_filter=base_components["flt"],
        quota_service=quota,
        require_auth=False,
    )
    app.include_router(router)
    client = TestClient(app)

    res = client.post("/api/chat", json={"user_id": "usr_err_test", "message": "crash"})
    assert res.status_code == 500
    err_body = res.json()
    assert "detail" in err_body
    detail = err_body["detail"]
    assert isinstance(detail, dict)
    assert detail.get("error") == "INTERNAL_ERROR"
    # Ensure raw Python traceback / exception details are NOT exposed to caller
    assert "Unexpected internal crash in provider runtime" not in str(err_body)


# ==============================================================================
# 7. CUSTOM_ATTRIBUTES SENSITIVE KEY SAFEGUARD
# ==============================================================================

def test_custom_attributes_sensitive_keys_are_filtered(base_components):
    cb = base_components["cb"]

    user_context = UserContext(
        name="მეფე გიორგი",
        zodiac="ლომი",
        custom_attributes={
            "session_id": "sess_secret_xyz123",
            "access_token": "bearer_jwt_sensitive_token",
            "api_key": "raw_service_api_key_val",
            "user_password": "super_secret_pw",
            "auth_credential": "cred_internal_payload",
            "favorite_drink": "ღვინო საფერავი",
            "favorite_flower": "ვარდი",
        },
    )

    formatted = cb.format_sovereign_context(user_context)

    # Sensitive attributes must be filtered out
    assert "session_id" not in formatted.lower()
    assert "sess_secret_xyz123" not in formatted
    assert "access_token" not in formatted.lower()
    assert "bearer_jwt_sensitive_token" not in formatted
    assert "api_key" not in formatted.lower()
    assert "raw_service_api_key_val" not in formatted
    assert "user_password" not in formatted.lower()
    assert "super_secret_pw" not in formatted
    assert "auth_credential" not in formatted.lower()

    # Legitimate attributes must be preserved
    assert "Favorite Drink: ღვინო საფერავი" in formatted
    assert "Favorite Flower: ვარდი" in formatted
