import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_card_service, get_settings
from app.config import Settings
from app.integrations.llm_client import (
    LLMClientError,
    LLMTimeoutError,
)
from app.main import app
from app.services.card_generator import CardGenerationService


class FakeLLMClient:
    def __init__(
        self,
        response: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls = 0

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.calls += 1

        if self.error is not None:
            raise self.error

        if self.response is None:
            raise RuntimeError("Fake response not configured")

        return self.response


def valid_product() -> dict[str, object]:
    return {
        "name": "Манометр DM 02",
        "manufacturer": "Манотомь",
        "specs": {
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
        },
        "description": "Прибор для измерения давления.",
    }


def valid_llm_response() -> str:
    return json.dumps(
        {
            "seo_title": "Манометр DM 02",
            "seo_description": "А" * 800,
            "search_queries": [
                "манометр DM 02",
                "манометр давления",
                "промышленный манометр",
            ],
            "commercial_block": "Прибор для измерения давления.",
        },
        ensure_ascii=False,
    )


def override_llm(fake_llm: FakeLLMClient) -> None:
    def get_test_service() -> CardGenerationService:
        return CardGenerationService(llm_client=fake_llm)

    app.dependency_overrides[get_card_service] = get_test_service


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_card_success(client: TestClient) -> None:
    fake_llm = FakeLLMClient(response=valid_llm_response())

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json=valid_product(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["seo_title"] == "Манометр DM 02"
    assert data["specifications"] == valid_product()["specs"]
    assert data["missing_fields"] == []
    assert fake_llm.calls == 1


def test_generate_card_missing_fields(client: TestClient) -> None:
    fake_llm = FakeLLMClient(response=valid_llm_response())

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json={
            "name": "Манометр",
            "specs": {"диапазон": "0–1,6 МПа"},
        },
    )

    assert response.status_code == 200

    data = response.json()

    missing = {field["field"] for field in data["missing_fields"]}

    assert missing == {
        "manufacturer",
        "description",
    }


def test_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cards/generate",
        content="{invalid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_missing_product_name(client: TestClient) -> None:
    fake_llm = FakeLLMClient(
        response=valid_llm_response(),
    )

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json={"specs": {"диапазон": "0–1,6 МПа"}},
    )

    assert response.status_code == 422
    assert fake_llm.calls == 0


def test_insufficient_product_data(client: TestClient) -> None:
    fake_llm = FakeLLMClient(response=valid_llm_response())

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json={"name": "Манометр"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == ("Insufficient product data")
    assert fake_llm.calls == 0


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (LLMClientError("Provider failed"), 502),
        (LLMTimeoutError("Timed out"), 504),
    ],
)
def test_llm_errors(
    client: TestClient,
    error: Exception,
    expected_status: int,
) -> None:
    fake_llm = FakeLLMClient(error=error)

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json=valid_product(),
    )

    assert response.status_code == expected_status


def test_invalid_llm_output(client: TestClient) -> None:
    fake_llm = FakeLLMClient(response="invalid json")

    override_llm(fake_llm)

    response = client.post(
        "/api/v1/cards/generate",
        json=valid_product(),
    )

    assert response.status_code == 502
    assert fake_llm.calls == 2


def test_missing_api_key(client: TestClient) -> None:
    def get_test_settings() -> Settings:
        return Settings(groq_api_key=None)

    app.dependency_overrides[get_settings] = get_test_settings

    response = client.post(
        "/api/v1/cards/generate",
        json=valid_product(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == ("GROQ_API_KEY is not configured")


def test_index_page(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text

    # Основные элементы интерфейса
    assert 'id="generate-btn"' in html
    assert 'id="example-btn"' in html

    # Кнопки копирования
    assert 'id="copy-text-btn"' in html
    assert 'id="copy-md-btn"' in html
    assert 'id="copy-json-btn"' in html

    # Обработка ошибок
    assert 'id="error"' in html
    assert 'id="status"' in html

    # Тестовая кнопка отсутствует в финальном интерфейсе
    assert 'id="demo-btn"' not in html
