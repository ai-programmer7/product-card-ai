from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_card_service
from app.integrations.llm_client import (
    LLMClientError,
    LLMTimeoutError,
)
from app.schemas.card import ProductCard
from app.schemas.product import ProductInput
from app.services.card_generator import (
    CardGenerationOutputError,
    CardGenerationService,
    InsufficientProductDataError,
)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/v1/cards/generate",
    response_model=ProductCard,
    status_code=status.HTTP_200_OK,
)
async def generate_product_card(
    product: ProductInput,
    service: Annotated[
        CardGenerationService,
        Depends(get_card_service),
    ],
) -> ProductCard:
    try:
        return await service.generate(product)

    except InsufficientProductDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Insufficient product data",
                "missing_fields": [field.model_dump() for field in exc.missing_fields],
            },
        ) from exc

    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM provider request timed out",
        ) from exc

    except (LLMClientError, CardGenerationOutputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate product card",
        ) from exc
