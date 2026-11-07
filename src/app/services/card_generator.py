from pydantic import ValidationError

from app.integrations.llm_client import LLMClient
from app.prompts.product_card import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.schemas.card import (
    GeneratedCardContent,
    ProductCard,
)
from app.schemas.missing_field import MissingField
from app.schemas.product import ProductInput


class CardGenerationError(Exception):
    """Base exception for card generation."""


class CardGenerationOutputError(CardGenerationError):
    """LLM returned invalid generated content."""


class InsufficientProductDataError(CardGenerationError):
    """Not enough source data to generate a reliable card."""

    def __init__(
        self,
        missing_fields: list[MissingField],
    ) -> None:
        self.missing_fields = missing_fields

        super().__init__("Insufficient product data for card generation")


class CardGenerationService:
    def __init__(
        self,
        llm_client: LLMClient,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self._llm_client = llm_client
        self._max_attempts = max_attempts

    async def generate(
        self,
        product: ProductInput,
    ) -> ProductCard:
        missing_fields = self._collect_missing_fields(product)

        # Без характеристик и технического описания
        # невозможно подготовить достоверную карточку.
        if not any(product.specs.values()) and not product.description:
            raise InsufficientProductDataError(
                missing_fields=missing_fields,
            )

        user_prompt = build_user_prompt(product)

        for attempt in range(self._max_attempts):
            raw_response = await self._llm_client.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            try:
                content = GeneratedCardContent.model_validate_json(
                    raw_response,
                )

            except ValidationError as exc:
                if attempt == self._max_attempts - 1:
                    raise CardGenerationOutputError(
                        "LLM returned invalid card content"
                    ) from exc

                user_prompt = self._build_retry_prompt(
                    product=product,
                    previous_response=raw_response,
                    validation_error=str(exc),
                )

                continue

            return self._build_product_card(
                product=product,
                content=content,
                missing_fields=missing_fields,
            )

        raise CardGenerationOutputError("Card generation attempts exhausted")

    @staticmethod
    def _collect_missing_fields(
        product: ProductInput,
    ) -> list[MissingField]:
        missing_fields: list[MissingField] = []

        if not product.manufacturer:
            missing_fields.append(
                MissingField(
                    field="manufacturer",
                    reason="Производитель не указан",
                )
            )

        if not product.description:
            missing_fields.append(
                MissingField(
                    field="description",
                    reason="Описание товара отсутствует",
                )
            )

        if not any(product.specs.values()):
            missing_fields.append(
                MissingField(
                    field="specs",
                    reason="Технические характеристики не предоставлены",
                )
            )

        for name, value in product.specs.items():
            if not value:
                missing_fields.append(
                    MissingField(
                        field=f"specs.{name}",
                        reason=f"{name}: данных нет",
                    )
                )

        return missing_fields

    @staticmethod
    def _build_retry_prompt(
        product: ProductInput,
        previous_response: str,
        validation_error: str,
    ) -> str:
        base_prompt = build_user_prompt(product)

        return (
            f"{base_prompt}\n\n"
            "Предыдущий ответ не прошёл валидацию.\n"
            f"Ошибка: {validation_error[:2000]}\n"
            "Предыдущий ответ:\n"
            f"{previous_response[:4000]}\n\n"
            "Исправь ответ и верни корректный JSON."
        )

    @staticmethod
    def _build_product_card(
        product: ProductInput,
        content: GeneratedCardContent,
        missing_fields: list[MissingField],
    ) -> ProductCard:
        warnings: list[str] = []

        if missing_fields:
            warnings.append(
                "Исходные данные неполные. "
                "Перед публикацией необходимо проверить карточку."
            )

        return ProductCard(
            seo_title=content.seo_title,
            seo_description=content.seo_description,
            specifications={
                name: value or "Данных нет" for name, value in product.specs.items()
            },
            search_queries=content.search_queries,
            commercial_block=content.commercial_block,
            missing_fields=missing_fields,
            warnings=warnings,
        )
