import json

import pytest

from app.schemas.product import ProductInput
from app.services.card_generator import (
    CardGenerationOutputError,
    CardGenerationService,
    InsufficientProductDataError,
)


class FakeLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.calls += 1

        if not self._responses:
            raise AssertionError("No fake responses left")

        return self._responses.pop(0)


def make_valid_response() -> str:
    response = {
        "seo_title": "Манометр DM 02",
        "seo_description": "А" * 800,
        "search_queries": [
            "манометр DM 02",
            "манометр давления",
            "манометр промышленный",
        ],
        "commercial_block": "Прибор для измерения давления.",
    }

    return json.dumps(response, ensure_ascii=False)


@pytest.mark.asyncio
async def test_generate_card_success() -> None:
    fake_llm = FakeLLMClient(
        responses=[make_valid_response()],
    )

    service = CardGenerationService(fake_llm)

    product = ProductInput(
        name="Манометр DM 02",
        manufacturer="Манотомь",
        specs={
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
        },
        description="Прибор для измерения давления.",
    )

    card = await service.generate(product)

    assert card.seo_title == "Манометр DM 02"

    # Характеристики должны полностью совпадать
    # с исходными данными.
    assert card.specifications == product.specs

    assert card.missing_fields == []
    assert card.warnings == []

    assert fake_llm.calls == 1


@pytest.mark.asyncio
async def test_missing_fields_are_reported() -> None:
    fake_llm = FakeLLMClient(
        responses=[make_valid_response()],
    )

    service = CardGenerationService(fake_llm)

    product = ProductInput(
        name="Манометр DM 02",
        specs={
            "диапазон измерений": "0–1,6 МПа",
        },
    )

    card = await service.generate(product)

    missing = {item.field for item in card.missing_fields}

    assert missing == {
        "manufacturer",
        "description",
    }

    assert len(card.warnings) > 0


@pytest.mark.asyncio
async def test_insufficient_data_prevents_generation() -> None:
    fake_llm = FakeLLMClient(responses=[])

    service = CardGenerationService(fake_llm)

    product = ProductInput(
        name="Манометр DM 02",
    )

    with pytest.raises(InsufficientProductDataError) as exc_info:
        await service.generate(product)

    missing = {item.field for item in exc_info.value.missing_fields}

    assert missing == {
        "manufacturer",
        "description",
        "specs",
    }

    # LLM вообще не вызывалась.
    assert fake_llm.calls == 0


@pytest.mark.asyncio
async def test_invalid_response_triggers_retry() -> None:
    fake_llm = FakeLLMClient(
        responses=[
            "invalid json",
            make_valid_response(),
        ],
    )

    service = CardGenerationService(fake_llm)

    product = ProductInput(
        name="Манометр",
        specs={
            "диапазон": "0–1,6 МПа",
        },
    )

    card = await service.generate(product)

    assert card.seo_title == "Манометр DM 02"
    assert fake_llm.calls == 2


@pytest.mark.asyncio
async def test_invalid_response_after_retry_raises_error() -> None:
    fake_llm = FakeLLMClient(
        responses=[
            "invalid json",
            "still invalid",
        ],
    )

    service = CardGenerationService(fake_llm)

    product = ProductInput(
        name="Манометр",
        specs={
            "диапазон": "0–1,6 МПа",
        },
    )

    with pytest.raises(CardGenerationOutputError):
        await service.generate(product)

    assert fake_llm.calls == 2
