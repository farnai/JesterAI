# JESTER (v0.1)

**JESTER** is a standalone, local AI chat application powered by a local LLM model (such as Qwen) running via Ollama. It breathes life into the archetype of the medieval royal court jester: razor-sharp, sarcastic, intellectually rigorous, and granted total license to speak the unvarnished truth to the throne.

---

## 🏛️ Architectural Separation of Concerns

JESTER is built with strict decoupling across 7 distinct tiers:

1. **Chat UI (`/frontend`)**
   - High-aesthetic web interface styled in dark obsidian and burnished gold.
   - Responsible strictly for rendering dialogues, managing audience IDs, and user input.
2. **API & Server (`/backend`)**
   - Built on FastAPI. Exposes a clean REST API (`POST /api/chat`, `GET /api/health`, `GET /api/conversations/{id}`, `POST /api/persona/reload`).
   - Treats the web UI merely as one client; any third-party app can consume the API.
3. **JESTER Core (`/jester_core`)**
   - `PersonaManager`: Loads, compiles, and dynamically hot-reloads persona definitions.
   - `ContextBuilder`: Assembles system prompts, few-shot examples, and sliding-window conversation history.
   - `OutputFilter`: Post-processing regex filter ensuring that **no stage directions** (e.g. `*laughs*`, `*(იცინის)*`) slip into responses.
4. **LLM Provider (`/llm_provider`)**
   - Abstract `LLMProvider` interface.
   - `OllamaProvider`: Asynchronous HTTP client communicating directly with Ollama's native `/api/chat` endpoint.
   - Easily swappable for vLLM, llama.cpp, or OpenAI-compatible backends without touching JESTER core.
5. **Persona & Prompts (`/persona`)**
   - Stored in human-readable YAML and Markdown files completely independent of application code:
     - `system_prompt.md`: Base identity, voice, royal court relationship.
     - `rules.yaml`: Sarcasm intensity, situational behavior directives.
     - `forbidden.yaml`: Prohibited behavioral patterns, repetitive phrases, and stage direction regexes.
     - `examples.yaml`: Few-shot dialogues showing ideal tone and format in Georgian and English.
6. **Conversation Memory (`/conversation`)**
   - Abstract `ConversationMemory` interface with a thread-safe `InMemoryStore`.
   - Isolates conversation state from persona and LLM logic.
7. **Configuration (`/config`)**
   - Configurable via `config.yaml` or environment variables (`JESTER_MODEL`, `OLLAMA_BASE_URL`, `JESTER_TEMPERATURE`, `JESTER_PORT`).

---

## 🚀 How to Run

### Prerequisites
1. Ensure Ollama is running (`ollama serve` or Ollama desktop app).
2. Verify that `qwen3.6:latest` is installed:
   ```bash
   ollama list
   ```

### Launching JESTER
From the project root (`jester/`):
```bash
python run.py
```
Open your browser at:
- **Web UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🎭 Modifying the JESTER Personality

You can fine-tune JESTER without touching any Python code:

1. **Adjust Sarcasm & Situational Directives**:
   Edit `persona/rules.yaml`. You can change `sarcasm_intensity`, adjust how JESTER handles foolish ideas, good insights, or technical questions.
2. **Add Few-Shot Examples**:
   Add new user/assistant pairs to `persona/examples.yaml`.
3. **Ban Words or Habits**:
   Add phrases or patterns to `persona/forbidden.yaml`.
4. **Hot Reload**:
   Trigger a hot reload without restarting the server:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/persona/reload
   ```

---

## 🔌 Integrating with Another Application

Any third-party service can communicate with JESTER using standard JSON HTTP calls:

### Send a Message
```http
POST /api/chat
Content-Type: application/json

{
  "conversation_id": "optional-uuid-string",
  "message": "Your question or command here"
}
```

### Response
```json
{
  "conversation_id": "optional-uuid-string",
  "response": "The JESTER retort or technical answer...",
  "model": "qwen3.6:latest"
}
```

### Check Status
```http
GET /api/health
```
