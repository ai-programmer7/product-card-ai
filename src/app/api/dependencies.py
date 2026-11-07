from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.config import Settings
from app.integrations.llm_client import (
    GroqLLMClient,
    LLMClient,
)
from app.services.card_generator import CardGenerationService


def get_settings() -> Settings:
    return Settings()


async def get_llm_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[LLMClient]:
    api_key = settings.groq_api_key

    if api_key is None or not api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured",
        )

    client = GroqLLMClient(
        api_key=api_key,
        model=settings.groq_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )

    try:
        yield client
    finally:
        await client.close()


def get_card_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> CardGenerationService:
    return CardGenerationService(
        llm_client=llm_client,
        max_attempts=2,
    )
