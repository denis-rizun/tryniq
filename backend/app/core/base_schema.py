from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UpdateSchema(BaseSchema):
    @model_validator(mode="after")
    def check_at_least_one_field(self) -> Self:
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self


class ErrorResponse(BaseSchema):
    detail: str
