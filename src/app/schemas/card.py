from pydantic import BaseModel, ConfigDict, Field

from app.schemas.missing_field import MissingField


class ProductCard(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    seo_title: str = Field(
        min_length=1,
        max_length=70,
    )

    seo_description: str = Field(
        min_length=800,
        max_length=1200,
    )

    specifications: dict[str, str]

    search_queries: list[str] = Field(
        min_length=3,
        max_length=5,
    )

    commercial_block: str = Field(min_length=1)

    missing_fields: list[MissingField] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )
