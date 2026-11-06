from pydantic import BaseModel, ConfigDict


class MissingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str
