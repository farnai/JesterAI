from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from persona import *  # noqa
from jester_core import PersonaManager, ContextBuilder, OutputFilter
from llm_provider import OllamaProvider
from conversation import InMemoryStore
from .routes import create_api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="JESTER - Standalone Court Jester Chat",
        description="Local LLaMA powered witty court jester conversation service",
        version="0.1.0",
    )

    # Enable CORS for flexible integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Initialize Persona Manager & Safety Filter
    persona_manager = PersonaManager(persona_dir=settings.persona_dir)
    output_filter = OutputFilter(additional_patterns=persona_manager.get_strip_patterns())

    # 2. Initialize Context Builder
    context_builder = ContextBuilder(
        persona_manager=persona_manager,
        max_history_messages=settings.conversation.max_history_messages,
    )

    # 3. Initialize LLM Provider (Ollama)
    llm_provider = OllamaProvider(
        base_url=settings.llm.base_url,
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        top_p=settings.llm.top_p,
        num_ctx=settings.llm.num_ctx,
    )

    # 4. Initialize Conversation Memory
    memory = InMemoryStore()

    # 5. Mount API Routes
    api_router = create_api_router(
        persona_manager=persona_manager,
        context_builder=context_builder,
        llm_provider=llm_provider,
        memory=memory,
        output_filter=output_filter,
    )
    app.include_router(api_router)

    # 6. Mount Frontend Static Files
    frontend_dir = settings.project_root / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()
