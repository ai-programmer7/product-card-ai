import pytest
from pydantic import ValidationError

from app.schemas.card import ProductCard
from app.schemas.product import ProductInput


def test_product_input_valid() -> None:
    product = ProductInput(
        name="Манометр DM 02",
        manufacturer="Манотомь",
        specs={"диапазон": "0–1,6 МПа"},
        description="Измерение давления",
    )

    assert product.name == "Манометр DM 02"
    assert product.specs["диапазон"] == "0–1,6 МПа"


def test_product_name_is_required() -> None:
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"manufacturer": "Манотомь"})


def test_product_name_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": "   "})


def test_optional_fields() -> None:
    product = ProductInput(name="Манометр")

    assert product.manufacturer is None
    assert product.description is None
    assert product.specs == {}


def test_empty_optional_text_normalized() -> None:
    product = ProductInput(
        name="Манометр",
        manufacturer="   ",
        description="",
    )

    assert product.manufacturer is None
    assert product.description is None


def test_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductInput.model_validate(
            {
                "name": "Манометр",
                "unknown_field": "value",
            }
        )


def test_invalid_specs_type() -> None:
    with pytest.raises(ValidationError):
        ProductInput.model_validate(
            {
                "name": "Манометр",
                "specs": ["invalid"],
            }
        )


def test_empty_specification_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductInput(
            name="Манометр",
            specs={"   ": "100 мм"},
        )


def valid_card_data() -> dict[str, object]:
    return {
        "seo_title": "Манометр DM 02",
        "seo_description": "А" * 800,
        "specifications": {
            "диапазон": "0–1,6 МПа",
        },
        "search_queries": [
            "манометр DM 02",
            "манометр давления",
            "манометр промышленный",
        ],
        "commercial_block": "Для измерения давления.",
    }


def test_product_card_valid() -> None:
    card = ProductCard.model_validate(valid_card_data())

    assert len(card.seo_description) == 800
    assert len(card.search_queries) == 3


@pytest.mark.parametrize(
    "title",
    ["", "А" * 71],
)
def test_invalid_seo_title(title: str) -> None:
    data = valid_card_data()
    data["seo_title"] = title

    with pytest.raises(ValidationError):
        ProductCard.model_validate(data)


@pytest.mark.parametrize(
    "length",
    [799, 1201],
)
def test_invalid_description_length(length: int) -> None:
    data = valid_card_data()
    data["seo_description"] = "А" * length

    with pytest.raises(ValidationError):
        ProductCard.model_validate(data)


@pytest.mark.parametrize(
    "count",
    [0, 2, 6],
)
def test_invalid_search_queries_count(count: int) -> None:
    data = valid_card_data()
    data["search_queries"] = ["запрос"] * count

    with pytest.raises(ValidationError):
        ProductCard.model_validate(data)
