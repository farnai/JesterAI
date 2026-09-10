from pathlib import Path
import os
import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.75
    top_p: float = 0.9
    num_ctx: int = 8192


class ConversationConfig(BaseModel):
    max_history_messages: int = 20


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class AppSettings(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    project_root: Path = PROJECT_ROOT
    persona_dir: Path = PROJECT_ROOT / "persona"


def load_settings() -> AppSettings:
    raw_data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

    llm_data = raw_data.get("llm", {})
    conv_data = raw_data.get("conversation", {})
    server_data = raw_data.get("server", {})

    # Environment variable overrides
    if "JESTER_MODEL" in os.environ:
        llm_data["model"] = os.environ["JESTER_MODEL"]
    if "OLLAMA_BASE_URL" in os.environ:
        llm_data["base_url"] = os.environ["OLLAMA_BASE_URL"]
    if "JESTER_TEMPERATURE" in os.environ:
        llm_data["temperature"] = float(os.environ["JESTER_TEMPERATURE"])
    if "JESTER_PORT" in os.environ:
        server_data["port"] = int(os.environ["JESTER_PORT"])

    return AppSettings(
        llm=LLMConfig(**llm_data),
        conversation=ConversationConfig(**conv_data),
        server=ServerConfig(**server_data),
        project_root=PROJECT_ROOT,
        persona_dir=PROJECT_ROOT / "persona",
    )


settings = load_settings()
