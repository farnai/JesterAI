# JESTER (v0.2)

**JESTER** is an autonomous, high-intelligence Royal Court AI service engineered for standalone operation and seamless microservice integration into larger applications (e.g. social, astrology, and conversational platforms). 

Rooted in the timeless archetype of the **medieval royal court jester**, JESTER serves as the monarch's sole licensed truth-teller: razor-sharp, sarcastic, intellectually rigorous, culturally nuanced, and strictly forbidden from servile flattery.

---

## 📚 Documentation & Deep Dives

* 🇬🇪 **[პროექტის სრული დეტალური აღწერა (PROJECT_OVERVIEW.md)](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/PROJECT_OVERVIEW.md)** — სრული ქართულენოვანი დოკუმენტაცია: არქეტიპის ფილოსოფია, 6 ქცევითი დირექტივა, ლოკალური მოდელების ბენჩმარკინგი, კვოტების სისტემა და ინტეგრაცია.
* 🏛️ **[System Architecture & Source of Truth (JESTER_ARCHITECTURE.md)](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/docs/JESTER_ARCHITECTURE.md)** — The 17 immutable architectural rules, hardware benchmark findings, authority boundaries, and production roadmap.
* 📋 **[v0.2 Implementation Plan & Audit (JESTER_V0.2_IMPLEMENTATION_PLAN.md)](file:///c:/Users/fiord/.gemini/antigravity-ide/scratch/jester/docs/JESTER_V0.2_IMPLEMENTATION_PLAN.md)** — Architectural discrepancy audit and v0.2 enterprise hardening specifications.

---

## ⚡ Key Capabilities in v0.2

1. **True LLM-Provider Agnosticism**
   - The application core is completely decoupled from any single AI backend.
   - Switch between **Ollama** (`qwen3.6:latest` for local inference), **Google Gemini Cloud API** (`gemini-1.5-flash` / `gemini-1.5-pro`), and **MockProvider** purely via configuration (`config/config.yaml` or env vars).
2. **Atomic Pre-Inference Quota Gate (Freemium Model)**
   - Every sovereign user receives **3 free questions**.
   - Quotas are checked and reserved **before** dispatching to the LLM. If exhausted, returns `HTTP 402 Payment Required` with **zero token / compute expenditure**.
   - Automatic quota rollback occurs if the provider encounters a connection or runtime error.
3. **Structured Sovereign User Context**
   - The Main Application remains the authoritative owner of user demographics.
   - JESTER ingests read-only, ephemeral context (`name`, `zodiac`, `daily_energy`, `birth_date`) per request to tailor royal court jabs and astrological insights dynamically.
4. **Externalized Persona & Live Hot-Reload**
   - Persona definitions live in clean, human-editable YAML/Markdown files in `/persona`:
     - `system_prompt.md`: Royal court truth-teller identity and philosophy.
     - `rules.yaml`: Sarcasm intensity and situational behavior directives.
     - `forbidden.yaml`: Prohibited behavioral patterns, servile repetition, and regex rules.
     - `examples.yaml`: High-quality few-shot dialogues in Georgian and English.
   - Dynamically reload personality files at runtime via `POST /api/persona/reload` without restarting the server.
5. **Stage Direction Sanitizer (`OutputFilter`)**
   - Strictly enforces rhetorical theatricality: removes accidental roleplay actions in asterisks or parentheses (e.g., `*(იცინის)*`, `*rolls eyes*`). Theatricality lives 100% inside vocabulary and syntax.
6. **Zero API Key Leakage & Enterprise Security**
   - Cloud credentials (`GEMINI_API_KEY`) are kept strictly on the backend.
   - Optional inter-service authentication via `X-Jester-API-Key` header.
7. **Production Observability**
   - High-resolution audit logging capturing latency, token usage (`prompt_tokens`, `completion_tokens`), quota changes, and provider status per turn.

---

## 🏛️ Architectural Separation of Concerns

```
JESTER v0.2
├── 1. Client & Web UI (/frontend)
│      High-aesthetic Obsidian & Gold royal court theme.
├── 2. API & Security Boundary (/backend)
│      FastAPI REST layer, Pydantic v2 schemas, auth guards, centralized error handling.
├── 3. Pre-Inference Quota Service (/jester_core/quota)
│      3-free-questions freemium gate, atomic reservations, rollback protection.
├── 4. Conversation Memory (/conversation)
│      Sliding dialog window (default: 20 turns) via thread-safe InMemoryStore.
├── 5. JESTER Core (/jester_core)
│      PersonaManager (hot-reload), ContextBuilder (prompt + sovereign context compilation).
├── 6. Output Filter (/jester_core/filter.py)
│      Post-processing regex filter stripping roleplay asterisks and stage directions.
├── 7. LLM Provider Layer (/llm_provider)
│      Abstract interface with OllamaProvider, GeminiProvider, and MockProvider.
└── 8. Configuration (/config)
       YAML file + Pydantic BaseSettings with environment variable overrides.
```

---

## 🚀 How to Run

### 1. Prerequisites
* **Python 3.10+** installed.
* **For Local Ollama Execution:**
  - Ollama running locally (`http://localhost:11434`).
  - Model `qwen3.6:latest` installed:
    ```bash
    ollama run qwen3.6:latest
    ```
* **For Cloud Gemini Execution:**
  - Google Gemini API key (`GEMINI_API_KEY`).

### 2. Installation
From the project root:
```bash
pip install -r requirements.txt
```

### 3. Launching JESTER
```bash
python run.py
```
By default, JESTER boots on port **`8005`**:
* **Web UI**: [http://127.0.0.1:8005](http://127.0.0.1:8005)
* **Interactive Swagger API Docs**: [http://127.0.0.1:8005/docs](http://127.0.0.1:8005/docs)

---

## ⚙️ Configuration & Switching Providers

Configuration is loaded from `config/config.yaml` and can be overridden with environment variables prefixed with `JESTER_`:

### Running with Local Ollama (Default):
```yaml
# config/config.yaml
llm:
  provider: "ollama"
  model: "qwen3.6:latest"
  base_url: "http://localhost:11434"
server:
  host: "127.0.0.1"
  port: 8005
```

### Running with Google Gemini Cloud API:
Set your API key in the environment and switch the provider:
```bash
# Windows PowerShell:
$env:GEMINI_API_KEY="your-google-gemini-api-key"
$env:JESTER_LLM_PROVIDER="gemini"
$env:JESTER_LLM_MODEL="gemini-1.5-flash"
python run.py
```
Or edit `config/config.yaml`:
```yaml
llm:
  provider: "gemini"
  model: "gemini-1.5-flash"
  api_key: "your-api-key-here"
```

---

## 🔌 API Reference & Integration Contract

The Main Application communicates with JESTER via standardized JSON HTTP calls:

### 1. Send Message (`POST /api/chat`)
**Request:**
```http
POST /api/chat
Content-Type: application/json
X-Jester-API-Key: optional-service-key

{
  "user_id": "usr_king_alexander",
  "conversation_id": "conv_royal_chamber_01",
  "message": "მგონია, რომ მონაცემთა ბაზის პაროლები Git-ში უნდა შევინახო.",
  "user_context": {
    "name": "ალექსანდრე",
    "zodiac": "კირჩხიბი",
    "daily_energy": 84
  }
}
```

**Success Response (`HTTP 200 OK`):**
```json
{
  "conversation_id": "conv_royal_chamber_01",
  "response": "თქვენო უდიდებულესობავ, კირჩხიბის ჯავშანი აშკარად სუსტია საინჟინრო უსაფრთხოებაში...",
  "model": "qwen3.6:latest",
  "provider": "ollama",
  "usage": {
    "remaining_free_questions": 2,
    "is_paid_user": false,
    "prompt_tokens": 1420,
    "completion_tokens": 98,
    "latency_ms": 3840.12
  }
}
```

**Paywall Response (`HTTP 402 Payment Required` — Zero LLM Cost):**
```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "თქვენი 3 უფასო შეკითხვის ლიმიტი ამოიწურა. სამეფო მასხარასთან საუბრის გასაგრძელებლად საჭიროა პრემიუმ გამოწერა.",
  "user_id": "usr_king_alexander",
  "remaining_free_questions": 0,
  "upgrade_url": "/billing/plans"
}
```

### 2. Check User Quota (`GET /api/quota/{user_id}`)
```http
GET /api/quota/usr_king_alexander
```
```json
{
  "user_id": "usr_king_alexander",
  "remaining_free_questions": 2,
  "is_paid_user": false,
  "allowed": true
}
```

### 3. Retrieve Conversation History (`GET /api/conversations/{id}`)
```http
GET /api/conversations/conv_royal_chamber_01
```

### 4. Clear Conversation History (`DELETE /api/conversations/{id}`)
```http
DELETE /api/conversations/conv_royal_chamber_01
```

### 5. Health Check (`GET /api/health`)
```http
GET /api/health
```
```json
{
  "status": "healthy",
  "model": "qwen3.6:latest",
  "provider": "ollama",
  "provider_details": {
    "version": "0.17.0"
  }
}
```

### 6. Live Persona Hot-Reload (`POST /api/persona/reload`)
```http
POST /api/persona/reload
```

---

## 🎭 Modifying the JESTER Personality

Fine-tune JESTER without touching any Python code:

1. **Adjust Sarcasm & Scenario Logic**: Edit `persona/rules.yaml` (e.g. adjust `sarcasm_intensity`, handling of naive vs brilliant ideas).
2. **Add Multi-Turn Examples**: Add new dialog pairs to `persona/examples.yaml`.
3. **Ban Unwanted Words / Clichés**: Add phrases or patterns to `persona/forbidden.yaml`.
4. **Hot Reload**: Execute `POST /api/persona/reload` or click reload in the debug console.

---

## 🧪 Automated Testing

JESTER includes a comprehensive test suite (42 automated tests) validating all critical architectural guarantees:
* **Quota & Paywalls**: Ensures zero unfunded LLM calls occur when quota is exhausted.
* **Provider Abstraction**: Tests seamless switching and error translation between providers.
* **Persona & Regex Sanitizer**: Confirms stage directions (`*(იცინის)*`, `*rolls eyes*`) are purged.
* **Sovereign Context**: Tests dynamic formatting of sovereign profile attributes.
* **Hardening**: Tests concurrent atomic quota reservations and authentication guards.

Run tests:
```bash
pytest
```
*All 42 tests pass.*

---

## 📁 Repository Structure

```
jester/
├── config/
│   ├── config.yaml              # Master runtime configuration (port 8005, models)
│   ├── settings.py              # Pydantic Settings with env var support
│   └── __init__.py
├── persona/
│   ├── system_prompt.md         # Royal Court Jester truth-teller identity
│   ├── rules.yaml               # Sarcasm levels & situational behavior directives
│   ├── forbidden.yaml           # Prohibited words, phrases & regex patterns
│   └── examples.yaml            # Multi-turn few-shot dialogues (Georgian & English)
├── jester_core/
│   ├── persona_manager.py       # Compiles persona docs & supports hot-reloading
│   ├── context_builder.py       # Assembles prompt, sovereign context & sliding history
│   ├── filter.py                # Regex sanitizer stripping stage directions
│   ├── observability.py         # Structured audit logging
│   ├── quota/                   # Atomic pre-inference quota & entitlement service
│   │   ├── in_memory_quota.py
│   │   └── service.py
│   └── __init__.py
├── llm_provider/
│   ├── base.py                  # Abstract LLMProvider interface & typed models
│   ├── factory.py               # Provider factory (ollama, gemini, mock)
│   ├── exceptions.py            # Standardized domain exceptions
│   ├── ollama_provider.py       # Ollama async HTTP provider
│   ├── gemini_provider.py       # Google Gemini Cloud provider
│   ├── mock_provider.py         # Fast mock provider for unit testing
│   └── __init__.py
├── conversation/
│   ├── memory.py                # Abstract ConversationMemory interface
│   ├── in_memory_store.py       # Thread-safe in-memory session history
│   └── __init__.py
├── backend/
│   ├── schemas.py               # Pydantic models (UserContext, UsageInfo, ChatRequest)
│   ├── routes.py                # API router & endpoints with auth and error mapping
│   ├── app.py                   # FastAPI application factory
│   └── __init__.py
├── frontend/
│   ├── index.html               # Royal Court Obsidian & Gold Web Interface
│   ├── style.css                # Bespoke glassmorphism styling
│   └── app.js                   # Client controller with session & quota tracking
├── tests/                       # 42 automated tests (quota, hardening, providers, persona)
├── docs/
│   ├── JESTER_ARCHITECTURE.md   # Authoritative system architecture & source of truth
│   └── JESTER_V0.2_IMPLEMENTATION_PLAN.md
├── PROJECT_OVERVIEW.md          # Comprehensive Georgian project overview & guide
├── requirements.txt             # Project dependencies
├── run.py                       # Server entry point (`python run.py`)
└── README.md                    # This document
```
