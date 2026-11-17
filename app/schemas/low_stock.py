from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ThresholdCreate(BaseModel):
    warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    variant_id: Optional[int] = Field(default=None, gt=0)
    minimum_quantity: int = Field(ge=0)
    reason: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class ThresholdUpdate(BaseModel):
    minimum_quantity: int = Field(ge=0)
    reason: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")