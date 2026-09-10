from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from typing import Optional
from config import AppSettings, load_settings, settings
from persona import *  # noqa
from jester_core import PersonaManager, ContextBuilder, OutputFilter, InMemoryQuotaService
from llm_provider import get_llm_provider
from conversation import InMemoryStore
from .routes import create_api_router


def create_app(app_settings: Optional[AppSettings] = None) -> FastAPI:
    active_settings = app_settings or load_settings()

    app = FastAPI(
        title="JESTER - Standalone Court Jester AI Service",
        description="Provider-agnostic witty royal court jester conversation microservice",
        version="0.2.0",
    )

    # Enable CORS for flexible integration with Main App and local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Initialize Persona Manager & Safety Filter
    persona_manager = PersonaManager(persona_dir=active_settings.persona_dir)
    output_filter = OutputFilter(additional_patterns=persona_manager.get_strip_patterns())

    # 2. Initialize Context Builder
    context_builder = ContextBuilder(
        persona_manager=persona_manager,
        max_history_messages=active_settings.conversation.max_history_messages,
    )

    # 3. Initialize Swappable LLM Provider via Factory
    llm_provider = get_llm_provider(active_settings)

    # 4. Initialize Conversation Memory
    memory = InMemoryStore()

    # 5. Initialize Quota & Entitlements Service
    quota_service = InMemoryQuotaService(
        free_questions_limit=active_settings.quota.free_questions_limit,
        enforce=active_settings.quota.enforce_quota,
    )

    # 6. Mount API Routes
    api_router = create_api_router(
        persona_manager=persona_manager,
        context_builder=context_builder,
        llm_provider=llm_provider,
        memory=memory,
        output_filter=output_filter,
        quota_service=quota_service,
        api_key=active_settings.security.api_key,
        require_auth=active_settings.security.require_auth,
    )
    app.include_router(api_router)

    # Attach instances to app state for testing / introspection
    app.state.llm_provider = llm_provider
    app.state.quota_service = quota_service
    app.state.memory = memory
    app.state.context_builder = context_builder
    app.state.persona_manager = persona_manager

    # 7. Mount Frontend Static Files (Local UI harness)
    frontend_dir = active_settings.project_root / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()
