
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class StockAction(BaseModel):

    product_id: int = Field(gt=0)

    variant_id: Optional[int] = Field(
        default=None,
        gt=0
    )

    quantity: int = Field(gt=0)

    reason: Optional[str] = Field(
        default=None,
        max_length=500
    )

    reference: Optional[str] = Field(
        default=None,
        max_length=100
    )

    model_config = ConfigDict(extra="forbid")
