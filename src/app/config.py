from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: SecretStr | None = None

    groq_model: str = "openai/gpt-oss-120b"

    llm_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
    )
