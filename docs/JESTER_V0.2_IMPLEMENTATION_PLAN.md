# JESTER v0.2 — Technical Architecture & Implementation Plan

> **READ THIS FIRST — IMPLEMENTATION AGENT**  
> 
> As an AI coding agent assigned to implement JESTER v0.2, you **must**:
> 1. Read [JESTER_ARCHITECTURE.md](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/docs/JESTER_ARCHITECTURE.md) first. That file is the authoritative source of truth for the core product concept, persona pillars, hardware profile, and 17 immutable architectural rules.
> 2. Read this document ([JESTER_V0.2_IMPLEMENTATION_PLAN.md](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/docs/JESTER_V0.2_IMPLEMENTATION_PLAN.md)) completely before writing or modifying any code.
> 3. Strictly distinguish **finalized architectural decisions** (which must be implemented as specified) from **open decisions** (marked clearly with `[OPEN DECISION]`, which must not be prematurely committed).
> 4. Implement **only what is approved** for v0.2.
> 5. **Do NOT introduce unnecessary dependencies or speculative infrastructure**: No LangChain, LlamaIndex, AutoGen, CrewAI, Redis, Celery, Vector DBs, ChromaDB, Pinecone, or unrequested database engines. Keep JESTER lean, modular, and fast.

---

## 1. Executive Summary

JESTER v0.1 established the foundational persona, prompt compiler, stage-direction sanitizer, and a local FastAPI + Ollama chat prototype.

**JESTER v0.2 elevates JESTER from a local chat prototype into an enterprise-ready, standalone AI microservice.**

The core mandate of v0.2 is:
1. **True Provider Agnosticism**: The "brain" (LLM) must be swappable via configuration (`ollama` $\to$ `gemini` $\to$ `openai`) without touching JESTER's core persona, memory, or routing logic.
2. **Pre-Inference Quota Gating**: Strict enforcement of the 3-free-questions rule *before* any LLM inference occurs, preventing unfunded API cost.
3. **Structured Sovereign Context**: Clean ingestion of read-only user attributes (name, zodiac, daily energy) supplied ephemerally by the Main Application.
4. **Decoupled Main App Contract**: A robust, secure HTTP API contract allowing the future Main Application to consume JESTER seamlessly as an external service.
5. **Zero API Key Leakage**: Cloud credentials remain strictly server-side and are never exposed to any frontend or client bundle.

---

## 2. Current v0.1 State vs. Target v0.2 Architecture

### Current Implementation vs Target Architecture (Discrepancy Audit)

| Component | Current v0.1 Codebase | Target v0.2 Architecture | Migration Action Required |
|---|---|---|---|
| **Chat Request Schema** | `ChatRequest` only accepts `message` and optional `conversation_id`. | Accepts `user_id` (mandatory), `message` (mandatory), `conversation_id` (optional), and `user_context` (optional). | Update [backend/schemas.py](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/backend/schemas.py) to validate `user_id` and nested `UserContext`. |
| **Chat Response Schema** | Returns only `conversation_id`, `response`, `model`. | Returns `conversation_id`, `response`, `model`, and structured `usage` containing `quota` details and token metrics. | Extend [backend/schemas.py](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/backend/schemas.py) with `UsageInfo` and `QuotaStatus`. |
| **Quota & Paywall Enforcement** | **Non-existent**. Any caller can query endlessly without identity or limit. | Pre-LLM gate intercepts requests. If `user_id` has 0 quota, returns `HTTP 402 Payment Required` with zero LLM execution. | Introduce `EntitlementService` and integrate into route handler before LLM call. |
| **LLM Provider Interface** | `LLMProvider.chat(messages, options)` takes raw dictionaries and returns raw `str`. | `LLMProvider.chat(request: LLMRequest) -> LLMResponse` with structured token counts, model metadata, latency, and standard error types. | Refactor [llm_provider/base.py](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/llm_provider/base.py) to use typed request/response models and a provider factory. |
| **Context Builder** | Ingests only system prompt, few-shot examples, and history. | Ingests system prompt, few-shot examples, history, current message, AND formatted `UserContext` (Sovereign Attributes). | Update [jester_core/context_builder.py](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/jester_core/context_builder.py) to inject sovereign context dynamically. |
| **Health Check Schema** | `HealthResponse` hardcodes an `ollama: Dict[str, Any]` field. | Provider-agnostic health model returning `provider: str`, `model: str`, `status: str`, and generic `provider_details: Dict[str, Any]`. | Refactor `HealthResponse` to decouple health checks from Ollama-specific terminology. |
| **Default Model Config** | `config.yaml` specifies `llama3.1:8b` (which failed Georgian benchmarks in `docs/JESTER_ARCHITECTURE.md`). | `config.yaml` defaults to `qwen3.6:latest` for local Ollama, with explicit hooks for `gemini` cloud deployment. | Align default config in [config/config.yaml](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/config/config.yaml) and [config/settings.py](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/config/settings.py). |
| **Port Default Mismatch** | `config.yaml` sets port `8005`, but `settings.py` default class fallback specifies `8000`. | Harmonize default port to `8005` consistently across all configuration layers. | Harmonize fallback default in `ServerConfig` to `8005`. |

---

## 3. Target v0.2 Architecture

```
                                  MAIN APPLICATION
                          (Authoritative User Profile & Billing)
                                         │
                                         │ POST /api/chat
                                         │ Headers: X-Jester-API-Key
                                         │ Body: { user_id, message,
                                         │         conversation_id, user_context }
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   JESTER SERVICE (v0.2)                                │
│                                                                                        │
│  1. AUTH & SECURITY MIDDLEWARE                                                         │
│     └── Validates Service API Key & Sanitizes Payload                                  │
│                                                                                        │
│  2. QUOTA & ENTITLEMENT SERVICE (Pre-Inference Gate)                                   │
│     ├── Evaluates user_id quota (3 free questions limit)                               │
│     └── [EXCEEDED / UNPAID] ──► HTTP 402 Payment Required (ZERO LLM Invocations)       │
│                                                                                        │
│  3. [ALLOWED] CONVERSATION MEMORY MANAGER                                              │
│     └── Retrieves sliding session history for conversation_id                          │
│                                                                                        │
│  4. CONTEXT BUILDER (Dynamic Prompt Compilation)                                       │
│     ├── System Prompt (Truth-teller court persona)                                     │
│     ├── Sovereign UserContext (Name, Zodiac, Daily Energy)                             │
│     ├── Behavioral Guidelines & Forbidden Constraints                                  │
│     ├── Curated Multi-Turn Few-Shot Examples                                           │
│     ├── Sliding Conversation History                                                   │
│     └── Current User Message                                                           │
│                                                                                        │
│  5. LLM PROVIDER FACTORY & ADAPTER (Abstract Execution)                                │
│     └── Dispatches unified LLMRequest to active provider                               │
│                                                                                        │
│  6. OUTPUT FILTER & SAFETY SANITIZER                                                   │
│     └── Strips accidental stage directions (*laughs*, *(იღიმის)*)                      │
│                                                                                        │
│  7. STATE UPDATE & OBSERVABILITY                                                       │
│     ├── Commits turn to Conversation Memory                                            │
│     ├── Decrements / registers quota usage in Quota Store                              │
│     └── Emits structured audit log (latency, tokens, provider)                         │
└────────────────────────────────────────┼───────────────────────────────────────────────┘
                                         │
                       ┌─────────────────┴─────────────────┐
                       ▼                                   ▼
             [DEVELOPMENT RUNTIME]                [PRODUCTION RUNTIME]
             ┌───────────────────┐                ┌───────────────────┐
             │   OllamaProvider  │                │   GeminiProvider  │
             └─────────┬─────────┘                └─────────┬─────────┘
                       ▼                                    ▼
             Local Ollama Engine                  Google Cloud Gemini API
             (qwen3.6:latest)                     (gemini-1.5-flash / pro)
```

---

## 4. Component Responsibilities

1. **API Boundary (`backend/`)**:
   - Ingests incoming HTTP requests.
   - Enforces service authentication and request schema validation.
   - Converts domain errors into standardized HTTP responses (400, 401, 402, 503).
2. **Quota & Entitlements (`jester_core/quota/` or `quota/`)**:
   - Manages question quotas per user.
   - Enforces the 3-free-questions rule.
   - Intercepts requests before the LLM layer is invoked.
3. **User Context Ingestion (`jester_core/context/` or `backend/schemas.py`)**:
   - Validates incoming user profile attributes from the Main App.
   - Formats user attributes into court-appropriate Sovereign context.
4. **Conversation Memory (`conversation/`)**:
   - Tracks session turns per `conversation_id`.
   - Provides sliding history to `ContextBuilder`.
   - Exposes clear interfaces for future persistent database backends.
5. **Persona Manager (`jester_core/persona_manager.py`)**:
   - Loads and compiles `system_prompt.md`, `rules.yaml`, `forbidden.yaml`, and `examples.yaml`.
   - Supports hot-reloading at runtime.
6. **Context Builder (`jester_core/context_builder.py`)**:
   - Coordinates prompt assembly into the final message array.
7. **Output Filter (`jester_core/filter.py`)**:
   - Enforces style constraints; cleans stage directions and unwanted artifacts.
8. **LLM Provider Abstraction (`llm_provider/`)**:
   - Standardizes communication with various AI inference engines.
   - Handles retries, timeouts, and standardized error translation.

---

## 5. Detailed Request & Data Flow

```
Main App              API Route           QuotaService         ContextBuilder        LLMProvider        Memory
   │                      │                    │                     │                    │                │
   │── POST /api/chat ───►│                    │                     │                    │                │
   │   (payload)          │                    │                     │                    │                │
   │                      │── check_access() ─►│                     │                    │                │
   │                      │   (user_id)        │                     │                    │                │
   │                      │                    │                     │                    │                │
   │                      │◄── DENIED ─────────│                     │                    │                │
   │◄── HTTP 402 ─────────│   (quota=0)        │                     │                    │                │
   │   (Paywall response) │                    │                     │                    │                │
   │   [ZERO LLM CALLS]   │                    │                     │                    │                │
   │                      │                    │                     │                    │                │
   │                      │                    │                     │                    │                │
   │ (If ALLOWED):        │                    │                     │                    │                │
   │                      │◄── ALLOWED ────────│                     │                    │                │
   │                      │                    │                     │                    │                │
   │                      │── get_history(conv_id) ───────────────────────────────────────────────────────►│
   │                      │◄── history items ─────────────────────────────────────────────────────────────│
   │                      │                    │                     │                    │                │
   │                      │── build_messages(user_context, history, msg) ─►│              │                │
   │                      │◄── compiled message list ──────────────────────│              │                │
   │                      │                    │                     │                    │                │
   │                      │── chat(llm_request) ─────────────────────────────────────────►│                │
   │                      │◄── llm_response (text, tokens, latency) ──────────────────────│                │
   │                      │                    │                     │                    │                │
   │                      │── sanitize(raw_text) ─► [OutputFilter]                        │                │
   │                      │◄── clean_text ─────────                                       │                │
   │                      │                    │                     │                    │                │
   │                      │── consume_quota(user_id) ────────────────                     │                │
   │                      │── add_message(user & assistant) ──────────────────────────────────────────────►│
   │                      │                    │                     │                    │                │
   │◄── HTTP 200 (OK) ────│                    │                     │                    │                │
   │   (response + usage) │                    │                     │                    │                │
```

---

## 6. LLM Provider Abstraction

### Interface Contract

The abstraction lives in `llm_provider/base.py`. It decouples JESTER core from any vendor-specific SDK or payload.

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class LLMRequest(BaseModel):
    messages: List[LLMMessage]
    temperature: Optional[float] = 0.75
    top_p: Optional[float] = 0.9
    max_tokens: Optional[int] = 2048
    stream: bool = False
    extra_options: Dict[str, Any] = Field(default_factory=dict)


class LLMTokenUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    latency_ms: float
    usage: Optional[LLMTokenUsage] = None
    raw_response: Optional[Dict[str, Any]] = None


class ProviderMetadata(BaseModel):
    name: str
    current_model: str
    is_cloud: bool
    healthy: bool


class LLMProvider(ABC):
    """Abstract interface for all JESTER brain implementations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'ollama', 'gemini', 'openai')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the configured active model."""
        pass

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Executes a completion/chat request against the model engine."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderMetadata:
        """Checks connectivity and operational status."""
        pass
```

### Standardized Error Hierarchy

Providers must raise normalized exceptions defined in `llm_provider/exceptions.py`:

- `LLMProviderError`: Base exception for all provider issues.
- `LLMConnectionError`: Cannot connect to provider endpoint or daemon (mapped to HTTP 503).
- `LLMAuthenticationError`: Invalid or expired API credentials (mapped to HTTP 500/502).
- `LLMRateLimitError`: Provider rate limit or resource exhaustion encountered (mapped to HTTP 429/503).
- `LLMTimeoutError`: Provider failed to respond within configured timeout (mapped to HTTP 504).
- `LLMResponseMalformedError`: Provider returned invalid or unparseable payload (mapped to HTTP 502).

### Provider Factory & Configuration

A factory function initializes the provider dynamically based on application configuration:

```python
# llm_provider/factory.py
from config.settings import AppSettings
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


def get_llm_provider(settings: AppSettings) -> LLMProvider:
    provider_type = settings.llm.provider.lower()
    
    if provider_type == "ollama":
        return OllamaProvider(
            base_url=settings.llm.base_url,
            model=settings.llm.model,
            timeout=settings.llm.timeout_seconds,
        )
    elif provider_type == "gemini":
        return GeminiProvider(
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            timeout=settings.llm.timeout_seconds,
        )
    elif provider_type == "openai":
        return OpenAIProvider(
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            timeout=settings.llm.timeout_seconds,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")
```

### Switching the Brain
To switch from local development to production Gemini, **zero application code changes are made**. The deployment environment only modifies environment variables:
```bash
# Local Development (.env or environment)
JESTER_LLM_PROVIDER=ollama
JESTER_MODEL=qwen3.6:latest
OLLAMA_BASE_URL=http://localhost:11434

# Production Cloud Deployment
JESTER_LLM_PROVIDER=gemini
JESTER_MODEL=gemini-1.5-flash
GEMINI_API_KEY=AIzaSy...secret...
```

---

## 7. UserContext Architecture

### Conceptual Authority
The Main Application owns canonical user profile data (identity, billing, birth information). JESTER never duplicates or stores this data in a persistent user table.

### Schema Specification
In `backend/schemas.py` or `jester_core/models.py`:

```python
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Ephemeral sovereign attributes provided by the Main Application."""
    name: Optional[str] = Field(default=None, max_length=100, description="The user's display name or court title")
    birth_date: Optional[str] = Field(default=None, description="ISO format date YYYY-MM-DD")
    zodiac: Optional[str] = Field(default=None, max_length=50, description="Astrological sign (e.g. ლომი, მშვილდოსანი)")
    daily_energy: Optional[int] = Field(default=None, ge=0, le=100, description="Calculated daily vitality index 0-100")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Safe forward-compatible metadata")
```

### Ingestion and Injection
1. **Entry Point**: Ingested via `POST /api/chat` as part of `ChatRequest`.
2. **Validation**: Pydantic validates boundaries and types.
3. **Prompt Formatting in `ContextBuilder`**:
   The `ContextBuilder` converts non-null attributes into a dedicated system prompt block:

```markdown
### THE CURRENT SOVEREIGN (USER ATTRIBUTES)
- Name / Title: დავითი
- Zodiac Sign: მშვილდოსანი (Sagittarius)
- Daily Energy Score: 84 / 100
*Court Instruction*: Use these personal attributes subtly to craft targeted witticisms, royal banter, and philosophical observations when relevant. Do not recite them mechanically like an automated database read.
```

4. **Security & Privacy Boundary**:
   - Sensitive PII (passwords, payment cards, national IDs, precise GPS) must **never** be accepted or forwarded to the LLM prompt.
   - The Main App sanitizes data before sending it to JESTER.

---

## 8. User Profile vs. Conversation Memory

| Dimension | User Profile (`UserContext`) | Conversation Memory (`ConversationMemory`) |
|---|---|---|
| **Authoritative Owner** | Main Application | JESTER Service |
| **Persistence** | Main App Database (PostgreSQL/User DB) | JESTER Memory Store (Session/In-Memory/Cache) |
| **Lifecycle** | Lifetime of User Account | Sliding window or configurable session duration |
| **Mutability by JESTER** | **Read-only** context per request | **Appended** on every user and assistant turn |
| **Purpose** | Informs personality adjustments and royal flavor | Maintains conversational continuity across turns |

### Storage Abstraction
The memory abstraction in `conversation/memory.py` is extended to support user-scoped sessions:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ConversationMemory(ABC):
    @abstractmethod
    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """Appends a message turn."""
        pass

    @abstractmethod
    def get_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Fetches history turns in chronological order."""
        pass

    @abstractmethod
    def clear(self, conversation_id: str) -> None:
        """Removes session history."""
        pass

    @abstractmethod
    def list_conversations(self, user_id: Optional[str] = None) -> List[str]:
        """Lists active conversation identifiers."""
        pass
```

- **v0.2 Implementation**: `InMemoryStore` remains the default, with thread-safe lock protection and LRU cache eviction to prevent memory leaks.
- **Future Transition**: When persistent storage is approved, a `PersistentConversationStore` (e.g. PostgreSQL or Redis) will implement `ConversationMemory` without modifying routes or `ContextBuilder`.

---

## 9. Quota & Entitlements Architecture

### Business Rule
1. Every distinct `user_id` is granted **3 free JESTER questions**.
2. Beyond 3 questions, access requires an active paid entitlement from the Main App.
3. **Pre-Inference Interception**: Quota verification runs **before** prompt compilation and before any LLM provider invocation.

### Entitlement Architecture & Service Interface

```python
# jester_core/quota/service.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional


class QuotaDecision(BaseModel):
    allowed: bool
    remaining_free_questions: int
    is_subscribed: bool
    rejection_code: Optional[str] = None  # e.g., "QUOTA_EXCEEDED", "UNAUTHORIZED"
    rejection_message: Optional[str] = None


class EntitlementService(ABC):
    """Abstract gatekeeper protecting LLM inference resources."""

    @abstractmethod
    async def check_access(self, user_id: str, entitlement_token: Optional[str] = None) -> QuotaDecision:
        """Evaluates whether the user is permitted to invoke the LLM."""
        pass

    @abstractmethod
    async def consume_quota(self, user_id: str) -> None:
        """Deducts or registers one successful question execution."""
        pass
```

### v0.2 Implementations
1. **`InMemoryQuotaService` (Default for v0.2)**:
   - Stores usage counts in memory: `Dict[user_id, count]`.
   - If `count < 3`: `allowed = True`, `remaining = 3 - count`.
   - If `count >= 3`: `allowed = False`, `remaining = 0`, rejection `QUOTA_EXCEEDED`.
2. **`RemoteEntitlementService` (Future Main App Integration)**:
   - Queries Main App internal endpoint: `GET /api/internal/users/{user_id}/entitlement`.
   - JESTER receives a simple boolean flag: `{ "allowed": true, "remaining_free": 0, "is_vip": true }`.
   - JESTER contains **no Stripe, credit card, or payment gateway logic**. The Main App remains the sole billing authority.

---

## 10. Main App ↔ JESTER API Contract

### Authentication & Service Boundary
Communication between Main App and JESTER is authenticated via a shared service secret header:
```http
X-Jester-API-Key: <SECRET_SERVICE_TOKEN>
```
If missing or invalid, JESTER returns `401 Unauthorized`.

---

### Endpoint: `POST /api/chat`

#### Request Payload
```json
{
  "user_id": "usr_alpha_9921",
  "conversation_id": "conv_88412a-33b",
  "message": "როგორ ფიქრობ, დღეს ღირს ახალი პროექტის დაწყება?",
  "user_context": {
    "name": "დავით",
    "birth_date": "1992-04-14",
    "zodiac": "ვერძი",
    "daily_energy": 78
  }
}
```

#### Response: Success (`200 OK`)
```json
{
  "conversation_id": "conv_88412a-33b",
  "response": "ვერძის შემართება გაქვს, მაგრამ გეგმა ისეთივე მყიფეა, როგორც შუშის მუზარადი...",
  "model": "qwen3.6:latest",
  "provider": "ollama",
  "usage": {
    "remaining_free_questions": 2,
    "is_paid_user": false,
    "prompt_tokens": 820,
    "completion_tokens": 145,
    "latency_ms": 1240.5
  }
}
```

#### Response: Paywall Rejection (`402 Payment Required`)
*Returned immediately when user has exhausted free questions. ZERO LLM calls are made.*
```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "თქვენ ამოწურეთ 3 უფასო შეკითხვა. მასხარასთან საუბრის გასაგრძელებლად საჭიროა წვდომის განახლება.",
  "user_id": "usr_alpha_9921",
  "remaining_free_questions": 0,
  "upgrade_url": "/billing/plans"
}
```

#### Response: Provider Failure (`503 Service Unavailable`)
```json
{
  "error": "PROVIDER_UNAVAILABLE",
  "message": "მასხარა დროებით დადუმდა: სააზროვნო ძრავთან კავშირი შეწყდა.",
  "provider": "ollama",
  "retryable": true
}
```

---

### Auxiliary Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Provider-agnostic health probe returning engine status and active model. |
| `GET` | `/api/conversations/{id}` | Retrieves session message turns for the conversation. |
| `DELETE` | `/api/conversations/{id}` | Clears session turns. |
| `GET` | `/api/persona` | Returns active compiled system prompt and rules summary. |
| `POST` | `/api/persona/reload` | Hot-reloads persona YAML and Markdown files from disk. |
| `GET` | `/api/quota/{user_id}` | Checks remaining questions without submitting a message. |

---

## 11. Security Model

1. **Cloud API Key Isolation**:
   - `GEMINI_API_KEY` and `OPENAI_API_KEY` reside exclusively in server-side environment variables or cloud secret stores.
   - Neither the web frontend nor client HTTP responses ever receive or disclose cloud keys.
2. **Inter-Service Authentication**:
   - Main App $\to$ JESTER requests are authenticated via `X-Jester-API-Key`.
   - In local development mode (`ENVIRONMENT=development`), auth enforcement can be made optional via config.
3. **Input Sanitization**:
   - User queries are bound to maximum string length (e.g., 2,000 characters).
   - Prompt injection guardrails: `ContextBuilder` wraps user input with clear delimiters and instructs the persona to maintain court composure regardless of user command overrides.
4. **CORS Configuration**:
   - Restrict allowed origins to Main App domains in production.

---

## 12. Configuration Strategy

Configuration uses Pydantic Settings with YAML file defaults and environment variable overrides.

### Target `config/config.yaml`
```yaml
llm:
  provider: "ollama"           # "ollama" | "gemini" | "openai"
  model: "qwen3.6:latest"      # or "gemini-1.5-flash", "gpt-4o-mini"
  base_url: "http://localhost:11434"
  api_key: ""
  temperature: 0.75
  top_p: 0.9
  max_tokens: 2048
  timeout_seconds: 60.0

quota:
  free_questions_limit: 3
  enforce_quota: true

conversation:
  max_history_messages: 20
  in_memory_ttl_seconds: 86400

security:
  api_key: ""                  # If non-empty, requires X-Jester-API-Key header
  require_auth: false

server:
  host: "127.0.0.1"
  port: 8005
```

### Environment Variable Overrides
```bash
JESTER_LLM_PROVIDER=gemini
JESTER_MODEL=gemini-1.5-flash
GEMINI_API_KEY=AIzaSy...
JESTER_API_KEY=secret_jester_token_123
JESTER_PORT=8005
JESTER_ENFORCE_QUOTA=true
```

---

## 13. Error Handling Architecture

```
Exception Type                HTTP Code   User-Facing Georgian Message
────────────────────────────────────────────────────────────────────────────────
QuotaExceededError            402         თქვენ ამოწურეთ 3 უფასო შეკითხვა.
InvalidApiKeyError            401         ავტორიზაცია ვერ მოხერხდა.
ValidationError (Pydantic)    422 / 400   არასწორი მონაცემთა ფორმატი.
LLMConnectionError            503         სააზროვნო ძრავთან დაკავშირება ვერ მოხერხდა.
LLMTimeoutError               504         პასუხის მოლოდინის დრო ამოიწურა.
LLMResponseMalformedError     502         მიღებულია დაზიანებული პასუხი.
InternalServerError           500         სისტემური შეცდომა სასახლეში.
```

All errors are handled through FastAPI exception handlers to produce consistent, structured JSON responses.

---

## 14. Testing Strategy

The test suite must ensure correctness across all decoupled layers before deployment.

### Required Test Matrix for v0.2

| Test Suite | File Path | Focus & Assertions |
|---|---|---|
| **A. Provider Abstraction** | `tests/test_provider_abstraction.py` | Verify `MockProvider`, `OllamaProvider`, and `GeminiProvider` conform to `LLMProvider` interface; test error mapping. |
| **B. UserContext Ingestion** | `tests/test_user_context.py` | Validate Pydantic schema constraints; test formatting of name, zodiac, and daily energy inside `ContextBuilder`. |
| **C. Quota Enforcement** | `tests/test_quota.py` | Verify users get exactly 3 free questions; verify 4th attempt transitions to paywall. |
| **D. Pre-Inference Gate [CRITICAL]** | `tests/test_no_unfunded_llm.py` | **Spy/Mock test**: When `user_id` has 0 remaining quota, assert `llm_provider.chat` was called **0 times**. |
| **E. Conversation Memory** | `tests/test_memory.py` | Test multi-turn appending, sliding window trimming, and clear operations. |
| **F. API Contracts** | `tests/test_api_v02.py` | Test `POST /api/chat` with full payload, minimal payload, missing fields, and status codes (200, 400, 401, 402, 503). |
| **G. Persona & Sanitizer** | `tests/test_persona.py` | Test hot-reloading, prompt assembly, and regex removal of stage directions (`*rolls eyes*`, `*(იცინის)*`). |
| **H. Provider Failure Resilience** | `tests/test_provider_failure.py` | Mock connection drops and verify graceful HTTP 503 without server crash. |
| **I. Dynamic Brain Switching** | `tests/test_provider_switching.py` | Reconfigure app settings from `ollama` to `mock` dynamically; verify response originates from new provider. |

---

## 15. Observability & Cost Control

A lightweight logging interceptor (`jester_core/observability.py`) records request metadata without requiring an external heavy monitoring service:

```json
{
  "timestamp": "2026-09-11T00:15:00Z",
  "request_id": "req_881290",
  "user_id": "usr_alpha_9921",
  "conversation_id": "conv_88412a-33b",
  "provider": "ollama",
  "model": "qwen3.6:latest",
  "latency_ms": 1420.2,
  "prompt_tokens": 745,
  "completion_tokens": 120,
  "quota_status": "free_tier_active",
  "remaining_free_questions": 2,
  "http_status": 200
}
```

### Metrics Tracked:
1. **Total Ingestion Requests** vs. **Actual LLM Invocations** (demonstrating paywall savings).
2. **Per-Provider Latency** (comparing Ollama local vs. Cloud Gemini).
3. **Token Consumption** (enabling exact cost projection for Cloud Gemini).
4. **Failure Rate & Error Types**.

---

## 16. Target Project Structure for v0.2

```
jester/
├── config/
│   ├── __init__.py
│   ├── config.yaml               # Target multi-provider configuration
│   └── settings.py               # Pydantic Settings with env var overrides
├── persona/
│   ├── system_prompt.md          # Core royal court jester identity
│   ├── rules.yaml                # Behavioral & scenario rules
│   ├── forbidden.yaml            # Forbidden patterns (stage directions)
│   └── examples.yaml             # Multi-turn few-shot Georgian/English examples
├── jester_core/
│   ├── __init__.py
│   ├── context_builder.py        # Prompts + UserContext + History compiler
│   ├── filter.py                 # Stage direction regex sanitizer
│   ├── persona_manager.py        # Hot-reloadable persona compiler
│   └── quota/                    # [NEW v0.2] Quota & entitlement layer
│       ├── __init__.py
│       ├── service.py            # EntitlementService & QuotaDecision
│       └── in_memory_quota.py    # Default 3-free-questions in-memory tracker
├── llm_provider/
│   ├── __init__.py
│   ├── base.py                   # LLMProvider, LLMRequest, LLMResponse
│   ├── exceptions.py             # [NEW v0.2] Standardized provider error classes
│   ├── factory.py                # [NEW v0.2] Provider instantiation factory
│   ├── ollama_provider.py        # Ollama local async provider implementation
│   ├── gemini_provider.py        # [NEW v0.2] Google Gemini cloud provider adapter
│   └── mock_provider.py          # [NEW v0.2] Mock provider for deterministic tests
├── conversation/
│   ├── __init__.py
│   ├── memory.py                 # Abstract ConversationMemory interface
│   └── in_memory_store.py        # Thread-safe in-memory sliding store
├── backend/
│   ├── __init__.py
│   ├── app.py                    # FastAPI application factory & middleware
│   ├── routes.py                 # Clean REST endpoints (/api/chat, /api/health, etc.)
│   ├── schemas.py                # Updated Pydantic models (UserContext, Quota, etc.)
│   └── dependencies.py           # [NEW v0.2] FastAPI dependency injection wiring
├── frontend/                     # Retained as local test harness UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   ├── __init__.py
│   ├── test_api_v02.py           # [NEW v0.2] Comprehensive API contract tests
│   ├── test_quota.py             # [NEW v0.2] Quota & paywall unit tests
│   ├── test_no_unfunded_llm.py   # [NEW v0.2] Critical pre-LLM gate verification test
│   ├── test_provider_abstraction.py # [NEW v0.2] LLMProvider interface compliance
│   ├── test_user_context.py      # [NEW v0.2] UserContext injection tests
│   ├── test_persona.py           # Existing persona & regex tests
│   └── manual_test_live.py       # Live validation utility
├── docs/
│   ├── JESTER_ARCHITECTURE.md    # Authoritative architectural source of truth
│   └── JESTER_V0.2_IMPLEMENTATION_PLAN.md # This document
├── requirements.txt              # Documented dependencies
├── run.py                        # Entrypoint script
└── README.md                     # Project overview & quickstart
```

---

## 17. Migration Plan (v0.1 $\to$ v0.2)

The implementation must proceed in five non-breaking phases:

```
Phase 1: Foundation & Schemas
├── Define LLMRequest, LLMResponse, and Provider Exceptions
├── Define UserContext and updated ChatRequest / ChatResponse schemas
└── Create EntitlementService interface and InMemoryQuotaStore

Phase 2: Provider Layer Refactoring
├── Refactor base.py to typed request/response models
├── Update OllamaProvider to new interface
├── Implement MockProvider for unit testing
├── Implement GeminiProvider adapter (using google-genai or httpx REST client)
└── Create ProviderFactory

Phase 3: Core Pipeline & Ingestion Update
├── Update ContextBuilder to format UserContext sovereign attributes
├── Implement Pre-Inference Quota Gate in routes.py
└── Integrate dependency injection in backend/dependencies.py

Phase 4: Test Suite & Verification
├── Implement test_no_unfunded_llm.py (0 LLM call verification)
├── Implement test_quota.py, test_user_context.py, test_provider_abstraction.py
└── Run complete pytest suite and verify 100% pass rate

Phase 5: Configuration & Docs Finalization
├── Update config.yaml and settings.py with multi-provider defaults
└── Validate local web UI functionality against updated backend
```

---

## 18. Implementation Checklist for Next Agent

- [ ] **Step 1**: Create `llm_provider/exceptions.py` with the standardized error hierarchy.
- [ ] **Step 2**: Refactor `llm_provider/base.py` to use `LLMRequest`, `LLMResponse`, `LLMTokenUsage`, and `ProviderMetadata`.
- [ ] **Step 3**: Update `llm_provider/ollama_provider.py` to accept `LLMRequest` and return `LLMResponse`.
- [ ] **Step 4**: Create `llm_provider/mock_provider.py` for testing.
- [ ] **Step 5**: Create `llm_provider/gemini_provider.py` (via HTTP API or official SDK).
- [ ] **Step 6**: Create `llm_provider/factory.py` to instantiate providers via config.
- [ ] **Step 7**: Create `jester_core/quota/service.py` and `jester_core/quota/in_memory_quota.py`.
- [ ] **Step 8**: Update `backend/schemas.py` with `UserContext`, updated `ChatRequest`, `ChatResponse`, and `QuotaExceededResponse`.
- [ ] **Step 9**: Update `jester_core/context_builder.py` to inject `UserContext` into prompt messages.
- [ ] **Step 10**: Update `backend/routes.py` to enforce pre-inference quota check, calling LLM only when allowed.
- [ ] **Step 11**: Update `config/config.yaml` and `config/settings.py` for provider selection and default port `8005`.
- [ ] **Step 12**: Implement full test suite in `tests/` and run `pytest`.
- [ ] **Step 13**: Verify that when quota is 0, the LLM provider is never invoked.

---

## 19. Open Decisions

The following items are designated as **`[OPEN DECISION]`** and must **NOT** be finalized or hard-coded without explicit user instruction:

1. **`[OPEN DECISION]` Production Cloud Model Selection**:
   - Whether to use `gemini-1.5-flash` (cost-optimized, fast) vs. `gemini-1.5-pro` (higher intellectual depth) vs. `gpt-4o-mini`. Local benchmark reference remains `qwen3.6:latest`.
2. **`[OPEN DECISION]` Inter-Service Authentication Protocol**:
   - Static secret token (`X-Jester-API-Key`) vs. Signed JWTs vs. mTLS between Main App and JESTER container.
3. **`[OPEN DECISION]` Remote Quota Sync Mechanism**:
   - Direct synchronous HTTP webhook from JESTER to Main App vs. Main App forwarding signed quota claims in the request token.
4. **`[OPEN DECISION]` Streaming Transport**:
   - Server-Sent Events (SSE) vs. WebSockets for token-by-token streaming in production.
5. **`[OPEN DECISION]` Production Conversation Database**:
   - PostgreSQL (relational) vs. Redis (in-memory TTL) vs. DynamoDB/MongoDB when moving off `InMemoryStore`.

---

## 20. Explicit Non-Goals for v0.2

To preserve codebase simplicity, stability, and speed, the following are strictly **NON-GOALS** for v0.2:

- ❌ **No LangChain or Framework Wrappers**: Keep standard Python and lightweight async clients.
- ❌ **No Vector Databases or RAG**: No ChromaDB, Pinecone, or pgvector until specific knowledge retrieval is required.
- ❌ **No Redis or External Database Dependency**: v0.2 runs standalone without requiring external DB containers.
- ❌ **No Payment Gateway / Stripe Code in JESTER**: JESTER does not handle cards, subscriptions, or checkouts.
- ❌ **No Fine-Tuning or Model Training**: Persona is steered strictly through externalized prompt engineering.
- ❌ **No Multi-Agent Autonomous Swarms**: JESTER is a dedicated conversational intellect, not an unbounded agent swarm.

---

**LAST UPDATED:** 2026-09-11  
**CHANGE LOG:**
- **2026-09-11 (v0.2.0-PLAN)**: Initial technical architecture and implementation plan created for JESTER v0.2. Defined LLMProvider abstraction, UserContext schema, pre-inference quota gating, Main App contract, test matrix, and phased migration path.
