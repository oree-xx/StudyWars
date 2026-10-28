from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    llm_provider: str = "gemini"
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GEMINI_KEY"),
    )
    gemini_model: str = "gemini-3.5-flash-lite"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    frontend_origin: str = "http://localhost:5173"
    frontend_dist: str = ""
    room_storage: str = "auto"
    redis_url: str = ""
    redis_key_prefix: str = "studywars"
    room_ttl_seconds: int = Field(default=86400, ge=60, le=604800)


settings = Settings()
