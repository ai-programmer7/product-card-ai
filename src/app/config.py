from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: SecretStr | None = None

    groq_model: str = "llama-3.3-70b-versatile"

    llm_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
    )
