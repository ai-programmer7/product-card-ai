from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1)
    manufacturer: str | None = None
    specs: dict[str, str] = Field(default_factory=dict)
    description: str | None = None

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("specs")
    @classmethod
    def validate_specs(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}

        for key, item in value.items():
            clean_key = key.strip()
            clean_value = item.strip()

            if not clean_key:
                raise ValueError("Specification name cannot be empty")

            normalized[clean_key] = clean_value

        return normalized
