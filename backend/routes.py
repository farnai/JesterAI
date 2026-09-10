import uuid
from fastapi import APIRouter, HTTPException
from .schemas import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    HealthResponse,
    PersonaResponse,
    MessageItem,
)
from jester_core import ContextBuilder, OutputFilter, PersonaManager
from llm_provider import LLMProvider
from conversation import ConversationMemory

def create_api_router(
    persona_manager: PersonaManager,
    context_builder: ContextBuilder,
    llm_provider: LLMProvider,
    memory: ConversationMemory,
    output_filter: OutputFilter,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(payload: ChatRequest):
        # 1. Determine or generate conversation ID
        conv_id = payload.conversation_id or str(uuid.uuid4())
        user_message = payload.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        # 2. Retrieve existing history for this conversation
        history = memory.get_history(conv_id)

        # 3. Assemble full prompt context (system + examples + history + current message)
        messages = context_builder.build_messages(
            current_message=user_message,
            history=history,
            include_examples=True,
        )

        # 4. Call LLM provider
        try:
            raw_response = await llm_provider.chat(messages)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"LLM Provider connection failed: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Inference error: {e}")

        # 5. Sanitize and enforce style constraints (filter out any accidental stage directions)
        sanitized_response = output_filter.sanitize(raw_response)

        # 6. Save both user message and sanitized JESTER response into memory
        memory.add_message(conv_id, "user", user_message)
        memory.add_message(conv_id, "assistant", sanitized_response)

        # 7. Return clean structured response
        return ChatResponse(
            conversation_id=conv_id,
            response=sanitized_response,
            model=getattr(llm_provider, "model", "local-llama"),
        )

    @router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
    async def get_conversation(conversation_id: str):
        history = memory.get_history(conversation_id)
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=[MessageItem(role=m["role"], content=m["content"]) for m in history],
        )

    @router.delete("/conversations/{conversation_id}")
    async def clear_conversation(conversation_id: str):
        memory.clear(conversation_id)
        return {"status": "cleared", "conversation_id": conversation_id}

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        ollama_status = await llm_provider.health_check()
        return HealthResponse(
            status="healthy" if ollama_status.get("status") == "healthy" else "degraded",
            model=getattr(llm_provider, "model", "unknown"),
            ollama=ollama_status,
        )

    @router.get("/persona", response_model=PersonaResponse)
    async def get_persona_details():
        return PersonaResponse(
            system_prompt=persona_manager.get_compiled_system_prompt(),
            rules_summary=persona_manager.get_rules_summary(),
        )

    @router.post("/persona/reload")
    async def reload_persona():
        persona_manager.reload()
        return {
            "status": "reloaded",
            "message": "Persona configuration files reloaded successfully from disk.",
        }

    return router
