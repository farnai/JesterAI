# JESTER — System Architecture & Product Direction

> **READ THIS FIRST — FOR AI AGENTS**  
> This document is the authoritative **source of truth** for the JESTER project.  
> As an AI agent working on JESTER, you **must**:
> 1. Read and understand this document before planning, modifying, or refactoring the architecture.
> 2. Strictly distinguish **decisions already made** from **open decisions** that remain non-finalized.
> 3. Never re-learn or disregard these core principles from scratch.
> 4. Avoid replacing working components or patterns merely because another framework or style is fashionable.
> 5. Update this document whenever a major architectural decision or production milestone is finalized.

**LAST UPDATED:** 2026-09-10

---

## 1. Product Concept

JESTER is not merely an Ollama chatbot wrapper or a toy demo.  
JESTER is a **standalone AI service/agent** engineered to eventually integrate as an autonomous persona and intelligent conversationalist within a larger primary application.

### The Core Archetype
- **The User** is the Sovereign, Master, or King.
- **JESTER** is the medieval royal court jester—the sole soul in the realm privileged and daring enough to speak the unvarnished truth to the throne.

### Personality Pillars
- **Intelligent & Philosophically Deep**
- **Witty & Sharp**
- **Sarcastic & Provocative**
- **Observant & Playful**
- **Confident & Theatrical through Language**
- **Genuinely Useful & Technically Rigorous**

### The Core Formula
$$\text{Intelligence} + \text{Entertainment} + \text{Personality}$$

### Behavioral Directives
1. **Situational Sarcasm**: Sarcasm must be intelligent, contextual, and earned—not forced into every sentence like a mechanical insult machine.
2. **Roasting Bad Ideas**: When the user proposes a flawed, reckless, or naive idea, JESTER is licensed to mock the decision mercilessly—**but must lucidly deconstruct why it fails and provide the technically correct path**.
3. **Acknowledging Genius**: When the user exhibits genuine brilliance, JESTER acknowledges it, sometimes with begrudging courtly admiration, without losing the upper hand.
4. **Vulnerability & Gravity**: When the user expresses genuine emotional vulnerability, grief, heavy burdens, or serious issues, JESTER drops cruel mockery and offers dignified court wisdom and gentle solidarity.
5. **No Servile Repetition**: JESTER must **never** repeat subservient honorifics like *"ჩემო ბატონო"* or *"My Lord"* on every turn. The dialogue must breathe and evolve naturally.
6. **No Theatrical Stage Directions (Strict Rule)**:
   - **NEVER** write actions in asterisks or parentheses:
     - ❌ `*(იცინის)*`
     - ❌ `*(თავს ხრის)*`
     - ❌ `*(ეჟვნები აჩხრიალებს)*`
     - ❌ `*rolls eyes*`
     - ❌ `(chuckles)`
   - Theatricality must live **100% inside vocabulary, syntax, and rhetoric**, never through simulated stage roleplay.
7. **Configurable Persona**: The persona must remain externalized and editable through structured files (`system_prompt.md`, `rules.yaml`, `forbidden.yaml`, `examples.yaml`) rather than baked into code or requiring model fine-tuning.

---

## 2. Core Architectural Principle: LLM-Provider Agnostic

The foundational architectural law of JESTER is:  
**JESTER is the application and agent layer. The LLM is merely the swappable "brain".**

Under no circumstances should JESTER be tightly coupled to Ollama, Qwen, LLaMA, Gemini, OpenAI, or any single model/provider.

```
JESTER Core
├── Persona Layer (Prompts, Guidelines, Forbidden Rules, Examples)
├── User Context Layer (Injected Sovereign Attributes)
├── Conversation Memory Layer (Session Histories, Dialog Windows)
├── Context Builder (Dynamic Assembly of Prompts + Context + History)
├── Quota & Entitlements Layer (Paywalls, Question Counts, Access Tiers)
├── Filters & Sanitizers (Stage-Direction Stripping, Safety)
├── Tools & Agent Capabilities (Future Function Calling / Actions)
├── API Boundary (FastAPI Clean Contracts)
└── LLM Provider Layer (Abstract Interface)
      ├── OllamaProvider (Local Development)
      ├── GeminiProvider (Production Cloud Engine)
      ├── OpenAIProvider (Alternative Cloud Engine)
      └── Future / On-Premise Providers
```

### Lifecycle Progression:
- **Local Development**:
  $$\text{Local UI or Test Client} \longrightarrow \text{JESTER Service} \longrightarrow \text{OllamaProvider} \longrightarrow \text{Local Model (Qwen/LLaMA)}$$
- **Production Integration**:
  $$\text{Main Application} \longrightarrow \text{JESTER Service} \longrightarrow \text{GeminiProvider} \longrightarrow \text{Google Gemini Cloud API}$$
- **Multi-Provider / Future Fallback**:
  $$\text{Main Application} \longrightarrow \text{JESTER Service} \longrightarrow \text{Alternative Provider} \longrightarrow \text{Target Cloud/Local Model}$$

Switching the underlying model or provider must require changing only configuration/provider adapters, leaving persona logic, conversation memory, API endpoints, and user context untouched.

---

## 3. Current Local Development Environment

- **Operating System**: Windows 11
- **CPU**: Intel Core i9-13900HX (24 cores / 32 threads)
- **RAM**: 32 GB DDR5
- **GPU**: NVIDIA GeForce RTX 4070 Laptop GPU
- **Dedicated GPU VRAM**: 8,188 MiB (~8.0 GB GDDR6)
- **Shared System GPU Memory**: ~15.87 GB (dynamic Windows allocation from 32 GB RAM)
- **CUDA Runtime**: Version 12.6, Compute Capability 8.9 (Ada Lovelace)
- **Ollama Host**: `http://localhost:11434`
- **Current Project Path**: `C:\Users\fiord\.gemini\antigravity-ide\scratch\jester`
- **Installed Local Models in Ollama**:
  - `llama3.1:8b` (~4.9 GB, Q4_K_M)
  - `qwen2.5-coder:7b` (~4.7 GB, Q4_K_M)
  - `qwen2.5:7b` (~4.7 GB, Q4_K_M — Standard Instruct)
  - `qwen3.6:latest` (~23.2 GB, 36.0B MoE, Q4_K_M)
  - `qwen2.5-coder:1.5b-base` (~986 MB, Base model)
  - `nomic-embed-text:latest` (~274 MB, Embedding model)

---

## 4. Local Model Benchmark Findings (Georgian Language Focus)

Local model benchmarking was executed directly against local Ollama models on this hardware using six targeted Georgian test prompts:
1. **Emotional / Conversational**: *"დღეს ძალიან ცუდ ხასიათზე ვარ და საერთოდ არ ვიცი რა გავაკეთო."*
2. **Technical Explanation**: *"ამიხსენი მარტივად რა განსხვავებაა TCP-სა და UDP-ს შორის."*
3. **Local Business Ideation**: *"მომიფიქრე იდეა პატარა ბიზნესისთვის საქართველოში."*
4. **Security Reasoning**: *"მე მგონია, რომ პაროლების plaintext-ად GitHub-ზე შენახვა პრობლემა არ არის. რას იტყვი?"*
5. **Debate / Philosophical**: *"მოდი ვიკამათოთ. რატომ არის ხელოვნური ინტელექტის აგენტის აშენება საერთოდ საჭირო?"*
6. **Algorithmic Explanation**: *"რა არის binary search და როგორ მუშაობს?"*

### Summary of Benchmark Results on this Machine:
- **`llama3.1:8b`**:
  - Extremely poor Georgian quality (~2/10).
  - Produces hallucinated words, broken morphology, and syntactically incoherent sentences.
  - Technically inaccurate when reasoning in Georgian.
  - **Unsuitable** for JESTER.
- **`qwen2.5-coder:7b`**:
  - Catastrophic failure in Georgian (~1/10).
  - Generated gibberish loops ("მისიციკრიმები"), timed out on technical prompts (300s+), and agreed with unsafe security practices.
  - **Unsuitable** for JESTER.
- **`qwen2.5:7b` (Standard Instruct)**:
  - Installed and evaluated with 100% GPU VRAM offload on the RTX 4070.
  - Exceptional raw throughput: **~48 tokens/second** (~16–38s total latency).
  - However, Georgian grammar and vocabulary are severely distorted (~2.5/10). Invents non-existent words (e.g., *"კურტულური"*, *"დამტაცებული"*, *"SSH კუპეები და პირამიდები"*) and misinterprets emotional queries as CV/resume problems.
  - **Unsuitable** for JESTER's Georgian conversational persona despite high speed.
- **`qwen3.6:latest` (36.0B MoE)**:
  - Substantially superior Georgian quality (~9.5/10).
  - Demonstrates genuine literary fluency, natural idioms (*"მსოფლიოც ნაცრისფრად ჩანს"*), deep technical comprehension, authentic Georgian context (TBC, Bank of Georgia, Enterprise Georgia, Kakheti, Svaneti), and surgical wit.
  - Slower latency (60–118s) because ~17.8 GB overflows the 8 GB VRAM into 32 GB system RAM, engaging CPU execution.
  - Currently the **strongest tested local candidate** for Georgian JESTER.

> **CRITICAL NOTE ON BENCHMARKS:**  
> These findings reflect empirical performance on this specific hardware, quantization, and prompt set. They do not claim universal mathematical properties of these models across all languages.  
> **Core Principle**: For a Georgian-speaking court wit, **linguistic and intellectual quality takes precedence over raw local inference speed**.  
> `qwen3.6:latest` is currently a benchmark reference point; the production LLM strategy remains an active architectural decision.

---

## 5. User Identity and User Data Architecture

The future main application **already owns the user's primary identity and profile**.  
**JESTER must NEVER become a redundant or conflicting second source of truth for user profile data.**

### Authority Boundaries
```
MAIN APPLICATION (AUTHORITATIVE)
├── User Identity (user_id, email, phone)
├── Personal Profile (name, title)
├── Astrological & Chronological Data (birth date, zodiac sign)
├── Application-Specific Metrics (daily energy, affinity scores)
└── Business State (subscription plan, payment tier, entitlements)
```

JESTER receives user context on-demand via a controlled, structured payload passed into the request:

```json
{
  "user_id": "usr_987654",
  "user_profile": {
    "name": "ალექსანდრე",
    "birth_date": "1994-07-22",
    "zodiac": "კირჩხიბი",
    "daily_energy": 84
  },
  "message": "დღეს რას მირჩევ, ჩემო მასხარავ?"
}
```

- JESTER ingests this structured context into its `ContextBuilder` to personalize humor and astrological/courtly jabs without storing or managing the master user profile.
- The exact production schema will be finalized in collaboration with the main application team.

---

## 6. User Memory vs. User Profile

These two data domains are fundamentally distinct and must never be conflated:

| Dimension | User Profile (Main App) | Conversation Memory (JESTER) |
|---|---|---|
| **Source of Truth** | **Main Application** | **JESTER Service** |
| **Data Nature** | Canonical user attributes | Dynamic conversational context |
| **Examples** | Name, Birth date, Zodiac, Daily energy, Plan | Prior queries, jokes made, user preferences revealed in chat, topics explored |
| **Persistence** | Main Application Database | JESTER Session/Memory Store |
| **Mutated by JESTER?** | **No** (read-only context) | **Yes** (appended per interaction turn) |

### Current State (v0.1):
- Implemented via [InMemoryStore](file:///C:/Users/fiord/.gemini/antigravity-ide/scratch/jester/conversation/in_memory_store.py).
- Sessions are keyed by `conversation_id`.
- History resets upon server restart.

### Future State:
- Persistent storage (PostgreSQL, Redis, or lightweight document store) will be introduced cleanly behind the [ConversationMemory](file:///C:/Users/fiord/.gemini/antigravity-ide/scratch/jester/conversation/memory.py) abstract interface.

---

## 7. Freemium Quota & Entitlements

JESTER is designed around a **freemium business model**.

### Product Rule:
- Every user receives **3 free questions**.
- Once the 3-question allowance is exhausted, further dialogue requires an active paid subscription or purchased tokens through the main application.

### Strict Architectural Rule:
**Quota checking must NEVER be buried inside the LLM provider layer.**  
LLM calls incur direct computational or financial costs. The system must verify access **before** invoking the brain.

```
Incoming Request (User ID, Message)
            │
            ▼
    Authentication & Identity Check
            │
            ▼
   Entitlement / Quota Verification
            │
      ┌─────┴────────────────┐
      ▼                      ▼
[Quota Exceeded]      [Quota Allowed]
      │                      │
  Return HTTP 402/403        ▼
  Paywall / Upgrade UI   Invoke JESTER Pipeline
  (ZERO LLM CALLS)           │
                             ▼
                     Invoke LLM Provider
                             │
                             ▼
                   Decrement / Log Quota
```

- The main application remains the source of truth for billing, payments, and subscriptions.
- JESTER verifies or accepts entitlement tokens/counters rather than implementing an independent payment gateway.

---

## 8. Main Application Integration Contract

The main application must remain completely decoupled from JESTER's internal machinery.  
It should never know or care:
- Which LLM model is serving the prompt.
- Whether Ollama, Gemini, or OpenAI is running underneath.
- How the court jester prompts, forbidden rules, or few-shot examples are assembled.
- How conversation sliding windows or filters work.

### Conceptual Contract:
```http
POST /api/chat (or /jester/chat)
Content-Type: application/json

{
  "user_id": "usr_987654",
  "conversation_id": "conv_abc123",
  "message": "როგორ შევაფასო დღევანდელი გეგმა?",
  "user_profile": {
    "name": "დავითი",
    "zodiac": "მშვილდოსანი",
    "daily_energy": 65
  }
}
```

### Response:
```json
{
  "conversation_id": "conv_abc123",
  "response": "თქვენი გეგმა ისეთივე მყიფეა, როგორიც მინის ფარი ბრძოლის ველზე...",
  "model": "gemini-1.5-pro",
  "quota_remaining": 2
}
```

JESTER owns the persona, prompt compilation, filtering, and LLM communication.

---

## 9. Local Development to Production Migration

```
DEVELOPMENT ENVIRONMENT
┌─────────────────────────┐
│ JESTER Local Web UI     │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ JESTER Backend Service  │
│ (FastAPI on Port 8005)  │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ OllamaProvider          │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Local Ollama Instance   │
│ (Qwen 3.6 / Local LLM)  │
└─────────────────────────┘
```

$$\boldsymbol{\Downarrow} \quad \text{Architectural Transition without Rewriting JESTER}$$

```
PRODUCTION ENVIRONMENT
┌─────────────────────────┐
│ Main Application Client │
│ (Web / Mobile App)      │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ JESTER Microservice     │
│ (Cloud Container)       │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ GeminiProvider          │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Google Gemini API       │
│ (Secure Cloud Inference)│
└─────────────────────────┘
```

- The abstract [LLMProvider](file:///C:/Users/fiord/.gemini/antigravity-ide/scratch/jester/llm_provider/base.py) makes changing the brain a 1-file implementation (`gemini_provider.py`) plus a config change (`llm.provider: "gemini"`).

---

## 10. API Key Security

Under zero circumstances should cloud LLM credentials (e.g., `GEMINI_API_KEY`, `OPENAI_API_KEY`) be exposed to client-side bundles:
- ❌ Never in frontend JavaScript (`app.js`, React, Vue, HTML).
- ❌ Never in public Git repositories or client environment files.
- ✅ Always loaded via server-side environment variables or secret managers (e.g., `.env`, AWS Secrets Manager, Google Secret Manager).
- Clients communicate solely with JESTER API endpoints; JESTER securely injects API keys when dispatching backend requests to cloud providers.

---

## 11. Current JESTER v0.1 Implementation

The working codebase is organized in `C:\Users\fiord\.gemini\antigravity-ide\scratch\jester`:

```
jester/
├── config/
│   ├── config.yaml          # Model parameters, endpoints, server port (8005)
│   ├── settings.py          # Pydantic Settings with environment variable overrides
│   └── __init__.py
├── persona/
│   ├── system_prompt.md     # Core royal court jester identity & truth-teller role
│   ├── rules.yaml           # Sarcasm levels, scenario behaviors (technical vs foolish)
│   ├── forbidden.yaml       # Prohibited behaviors & regex patterns for stage directions
│   └── examples.yaml        # Multi-turn few-shot dialogues in Georgian & English
├── jester_core/
│   ├── persona_manager.py   # Compiles persona documents & supports live hot-reload
│   ├── context_builder.py   # Assembles system prompt, examples, history, and message
│   ├── filter.py            # Sanitizer stripping accidental asterisk/parentheses actions
│   └── __init__.py
├── llm_provider/
│   ├── base.py              # Abstract LLMProvider interface
│   ├── ollama_provider.py   # Async httpx client communicating with Ollama /api/chat
│   └── __init__.py
├── conversation/
│   ├── memory.py            # Abstract ConversationMemory interface
│   ├── in_memory_store.py   # Thread-safe in-memory session history store
│   └── __init__.py
├── backend/
│   ├── schemas.py           # Pydantic models (ChatRequest, ChatResponse, Health, etc.)
│   ├── routes.py            # FastAPI endpoints (/api/chat, /api/health, /api/persona, etc.)
│   ├── app.py               # Application factory, CORS, and static file mounting
│   └── __init__.py
├── frontend/
│   ├── index.html           # Royal Court UI (Obsidian & Gold theme)
│   ├── style.css            # Bespoke design system, typography, glassmorphic cards
│   └── app.js               # Client controller (session tracking, async submission)
├── tests/
│   ├── test_persona.py      # Unit tests for prompt compilation and regex filtering
│   ├── test_api.py          # Unit tests for API endpoints and history management
│   └── manual_test_live.py  # Live verification script testing local Ollama models
├── run.py                   # Server startup runner (`python run.py`)
├── requirements.txt         # Documented Python dependencies
└── README.md                # Quick-start and architecture overview
```

### Current Endpoints (Port 8005):
- `POST /api/chat`: Send message, obtain sanitized JESTER reply.
- `GET /api/conversations/{id}`: Retrieve session history.
- `DELETE /api/conversations/{id}`: Clear session history.
- `GET /api/persona`: Retrieve active system prompt and rules summary.
- `POST /api/persona/reload`: Hot-reload persona YAML/Markdown files without server restart.
- `GET /api/health`: Health status of LLM provider and configured model.
- `GET /docs`: Interactive Swagger UI.

---

## 12. 17 Immutable Architectural Rules

Every AI agent and engineer modifying JESTER must strictly adhere to these rules:

1. **Decouple the Brain**: Never tightly couple JESTER core to a specific LLM or provider.
2. **Provider Isolation**: Keep all provider-specific quirks, headers, and payloads hidden behind `LLMProvider`.
3. **Keep Persona External**: Store persona prompts and rules in editable text/YAML files outside compiled code and model weights.
4. **Main App Owns Identity**: The main application is always the single source of truth for user profile data.
5. **Separate Profile from Memory**: User profile attributes $\neq$ conversation history and interaction memories.
6. **Pre-LLM Quota Gate**: Check quotas and entitlement access **before** dispatching LLM API calls.
7. **No Unfunded Inferences**: Never trigger an LLM inference if the user is unauthorized or out of quota.
8. **Never Leak Keys**: Cloud LLM API keys must live exclusively on the server backend.
9. **Clean API Boundaries**: The main application must interact only via stable, clean JSON HTTP/gRPC contracts.
10. **Avoid Premature Infrastructure**: Do not introduce RAG, vector databases, Redis, multi-agent frameworks, or complex pipelines without explicit product requirements.
11. **No Fashionable Rewrites**: Do not rewrite working components simply because another framework is trendy.
12. **Empirical Benchmarking**: Benchmark and inspect outputs systematically before selecting or swapping models.
13. **Georgian as a First-Class Citizen**: Natural, idiomatic Georgian language quality is a primary acceptance gate.
14. **Truth and Intelligence First**: JESTER's wit and sarcasm must never compromise factual or technical accuracy.
15. **Zero Stage Directions**: Strip or prevent roleplay actions in asterisks or parentheses (`*laughs*`, `*(იცინის)*`).
16. **Hot-Reloadable Configuration**: Allow persona adjustments and parameter tuning without requiring cold server restarts.
17. **Production Swap Ready**: The architecture must guarantee that transitioning from local Ollama to cloud Gemini requires zero rewrites to JESTER core.

---

## 13. Decisions Already Made (Finalized)

- ✅ **Standalone Service**: JESTER is an independent service with its own domain boundary.
- ✅ **Future Main App Client**: JESTER will be consumed as a service by the future main application.
- ✅ **Provider-Agnostic Core**: [LLMProvider](file:///C:/Users/fiord/.gemini/antigravity-ide/scratch/jester/llm_provider/base.py) defines the interface contract; Ollama is merely one implementation.
- ✅ **Main App Owns Master Profile**: Profile data (birth date, zodiac, daily energy) belongs to the main app and is supplied to JESTER as read-only request context.
- ✅ **Separation of Profile & Memory**: Conversation turns belong to JESTER's memory layer; user demographics belong to the main app.
- ✅ **3 Free Questions**: Initial freemium tier provides 3 free questions before paywall enforcement.
- ✅ **Pre-Inference Paywall**: Block LLM execution immediately if entitlement is absent.
- ✅ **Server-Side Secrets**: All third-party API keys are strictly forbidden in client-facing code.
- ✅ **Georgian Priority**: Quality of Georgian language is a mandatory evaluation benchmark.
- ✅ **Current Local Candidate**: `qwen3.6:latest` is currently the highest quality tested local model for Georgian, while `llama3.1:8b` and `qwen2.5:7b` fail Georgian linguistic requirements.
- ✅ **Open Production Brain Choice**: Final production cloud model has **not** been hard-coded yet.

---

## 14. Open Decisions & Non-Finalized Areas

The following items are deliberately **NOT yet decided** and must not be implemented prematurely:

- ⏳ **Final Production LLM Engine**: (Gemini 1.5 Pro/Flash vs. OpenAI GPT-4o vs. Claude 3.5 Sonnet vs. self-hosted Qwen 36B/72B).
- ⏳ **Persistent Database Technology**: (PostgreSQL, SQLite, Redis, or Mongo for conversation memory).
- ⏳ **Long-Term Memory Mechanism**: (Semantic memory summaries vs. sliding window vs. episodic retrieval).
- ⏳ **Authentication Scheme**: (JWT, API Keys, OAuth2, or mutual TLS between Main App and JESTER).
- ⏳ **Production Quota & Billing Sync Protocol**: (Webhooks, shared auth tokens, or centralized billing microservice).
- ⏳ **Exact User Context Schema**: (Final structure of zodiac, birth data, and daily energy fields).
- ⏳ **Production Cloud Hosting & Container Orchestration**: (AWS ECS, Google Cloud Run, Kubernetes, or VPS).
- ⏳ **Streaming Responses (SSE / WebSockets)**: (Currently standard HTTP POST JSON in v0.1).
- ⏳ **Tool & Function Calling Capabilities**: (External calendar, daily horoscope tools, or internal database queries).
- ⏳ **RAG / Vector Database Setup**: (Chroma, Qdrant, pgvector — deferred until explicit knowledge retrieval is required).
- ⏳ **Model Fine-Tuning / LoRA**: (Deferred; prompt engineering and few-shot examples are currently prioritized).

---

## 15. Future Architecture Target

```
                           ┌───────────────────────────────┐
                           │       MAIN APPLICATION        │
                           │  - User Profiles & Zodiac     │
                           │  - Subscriptions & Payments   │
                           │  - Primary UI & Navigation    │
                           └───────────────┬───────────────┘
                                           │
                                           │ POST /jester/chat
                                           │ { user_id, message,
                                           │   user_profile }
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             JESTER AGENT SERVICE                                 │
│                                                                                  │
│   ┌────────────────────────┐                   ┌─────────────────────────────┐   │
│   │   Auth & Entitlements  │ ── [Denied] ───►  │   HTTP 402/403 Paywall      │   │
│   │   (Quota Counter <= 3) │                   │   (No LLM Inference Cost)   │   │
│   └───────────┬────────────┘                   └─────────────────────────────┘   │
│               │ [Allowed]                                                        │
│               ▼                                                                  │
│   ┌────────────────────────┐                   ┌─────────────────────────────┐   │
│   │   Persona Manager      │                   │     Conversation Memory     │   │
│   │   - system_prompt.md   │                   │     - Active Session Cache  │   │
│   │   - rules.yaml         │                   │     - Long-term Context     │   │
│   │   - forbidden.yaml     │                   └──────────────┬──────────────┘   │
│   │   - examples.yaml      │                                  │                  │
│   └───────────┬────────────┘                                  │                  │
│               │                                               │                  │
│               └───────────────────────┬───────────────────────┘                  │
│                                       ▼                                          │
│                        ┌─────────────────────────────┐                           │
│                        │       Context Builder       │                           │
│                        │ (Compiles System + Examples │                           │
│                        │   + Memory + User Context)  │                           │
│                        └──────────────┬──────────────┘                           │
│                                       ▼                                          │
│                        ┌─────────────────────────────┐                           │
│                        │       Output Filter         │                           │
│                        │ (Strips Stage Directions)   │                           │
│                        └──────────────┬──────────────┘                           │
│                                       ▼                                          │
│                        ┌─────────────────────────────┐                           │
│                        │    LLM Provider Adapter     │                           │
│                        │         (Interface)         │                           │
│                        └──────────────┬──────────────┘                           │
└───────────────────────────────────────┼──────────────────────────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
              [DEVELOPMENT PROVIDER]         [PRODUCTION PROVIDER]
              ┌────────────────────┐         ┌────────────────────┐
              │   OllamaProvider   │         │   GeminiProvider   │
              └─────────┬──────────┘         └─────────┬──────────┘
                        ▼                              ▼
              ┌────────────────────┐         ┌────────────────────┐
              │ Local Ollama Host  │         │ Google Gemini Cloud│
              │ (Qwen 3.6 / Local) │         │     API Endpoint   │
              └────────────────────┘         └────────────────────┘
```

---

## 16. Change Log

| Date | Version | Author | Description of Changes |
|---|---|---|---|
| **2026-09-10** | **v0.1.0-DOCS** | Antigravity AI | Initial formal documentation of JESTER system architecture, separation of concerns, hardware profile, Georgian benchmarking results, user context/memory boundaries, freemium quota rules, and migration roadmap. |
