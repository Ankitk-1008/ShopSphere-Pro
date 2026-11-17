
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class ProductAttributeCreate(BaseModel):

    category_id: Optional[int] = None

    name: str = Field(
        min_length=2,
        max_length=100
    )

    code: str = Field(
        min_length=2,
        max_length=100
    )

    data_type: Literal[
        "text",
        "number",
        "boolean"
    ] = "text"

    allowed_values: Optional[list[str]] = None

    is_required: bool = False

    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class ProductAttributeUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    allowed_values: Optional[list[str]] = None

    is_required: Optional[bool] = None

    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class ProductAttributeValueCreate(BaseModel):

    attribute_id: int

    value: str = Field(
        min_length=1,
        max_length=500
    )

    model_config = ConfigDict(extra="forbid")
