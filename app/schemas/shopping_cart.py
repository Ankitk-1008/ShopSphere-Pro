from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    variant_id: Optional[int] = Field(default=None, gt=0)
    quantity: int = Field(default=1, gt=0)

    model_config = ConfigDict(extra="forbid")


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")