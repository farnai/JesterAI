from pathlib import Path
import os
import yaml
from pydantic import BaseModel, Field, model_validator

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = "qwen3.6:latest"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    temperature: float = 0.85
    top_p: float = 0.9
    frequency_penalty: float = 0.35
    num_ctx: int = 8192
    timeout_seconds: float = 240.0


class QuotaConfig(BaseModel):
    free_questions_limit: int = 3
    enforce_quota: bool = True


class ConversationConfig(BaseModel):
    max_history_messages: int = 20


class SecurityConfig(BaseModel):
    api_key: str = ""
    require_auth: bool = False

    @model_validator(mode="after")
    def validate_auth_key(self) -> "SecurityConfig":
        if self.require_auth and not self.api_key.strip():
            raise ValueError(
                "Security configuration error: require_auth=True requires a non-empty JESTER_API_KEY. "
                "Refusing to start in an insecure or misconfigured state."
            )
        return self


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8005


class AppSettings(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    project_root: Path = PROJECT_ROOT
    persona_dir: Path = PROJECT_ROOT / "persona"


def load_settings() -> AppSettings:
    raw_data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

    llm_data = raw_data.get("llm", {})
    quota_data = raw_data.get("quota", {})
    conv_data = raw_data.get("conversation", {})
    security_data = raw_data.get("security", {})
    server_data = raw_data.get("server", {})

    # Environment variable overrides
    if "JESTER_PROVIDER" in os.environ:
        llm_data["provider"] = os.environ["JESTER_PROVIDER"]
    elif "JESTER_LLM_PROVIDER" in os.environ:
        llm_data["provider"] = os.environ["JESTER_LLM_PROVIDER"]
    if "JESTER_MODEL" in os.environ:
        llm_data["model"] = os.environ["JESTER_MODEL"]
    if "OLLAMA_BASE_URL" in os.environ:
        llm_data["base_url"] = os.environ["OLLAMA_BASE_URL"]
    if "GEMINI_API_KEY" in os.environ:
        llm_data["api_key"] = os.environ["GEMINI_API_KEY"]
    elif "JESTER_GEMINI_API_KEY" in os.environ:
        llm_data["api_key"] = os.environ["JESTER_GEMINI_API_KEY"]
    if "OPENAI_API_KEY" in os.environ:
        llm_data["api_key"] = os.environ["OPENAI_API_KEY"]
    if "JESTER_API_KEY" in os.environ:
        security_data["api_key"] = os.environ["JESTER_API_KEY"]
    if "JESTER_REQUIRE_AUTH" in os.environ:
        security_data["require_auth"] = os.environ["JESTER_REQUIRE_AUTH"].lower() in ("true", "1", "yes")
    if "JESTER_TEMPERATURE" in os.environ:
        llm_data["temperature"] = float(os.environ["JESTER_TEMPERATURE"])
    if "JESTER_TOP_P" in os.environ:
        llm_data["top_p"] = float(os.environ["JESTER_TOP_P"])
    if "JESTER_FREQUENCY_PENALTY" in os.environ:
        llm_data["frequency_penalty"] = float(os.environ["JESTER_FREQUENCY_PENALTY"])
    if "JESTER_ENFORCE_QUOTA" in os.environ:
        quota_data["enforce_quota"] = os.environ["JESTER_ENFORCE_QUOTA"].lower() in ("true", "1", "yes")
    if "JESTER_PORT" in os.environ:
        server_data["port"] = int(os.environ["JESTER_PORT"])

    return AppSettings(
        llm=LLMConfig(**llm_data),
        quota=QuotaConfig(**quota_data),
        conversation=ConversationConfig(**conv_data),
        security=SecurityConfig(**security_data),
        server=ServerConfig(**server_data),
        project_root=PROJECT_ROOT,
        persona_dir=PROJECT_ROOT / "persona",
    )


settings = load_settings()
