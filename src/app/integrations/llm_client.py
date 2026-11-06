from typing import Protocol

from openai import APIError, AsyncOpenAI
from pydantic import SecretStr


class LLMClient(Protocol):
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str: ...


class LLMClientError(Exception):
    """Error during communication with an LLM provider."""


class GroqLLMClient:
    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        secret = api_key.get_secret_value()

        if not secret:
            raise ValueError("GROQ_API_KEY is not configured")

        self._model = model

        self._client = AsyncOpenAI(
            api_key=secret,
            base_url="https://api.groq.com/openai/v1",
            timeout=timeout_seconds,
            max_retries=0,
        )

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=1800,
            )

        except APIError as exc:
            raise LLMClientError("Failed to communicate with LLM provider") from exc

        if not response.choices:
            raise LLMClientError("LLM returned an empty response")

        content = response.choices[0].message.content

        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("LLM returned an empty response")

        return content

    async def close(self) -> None:
        await self._client.close()
