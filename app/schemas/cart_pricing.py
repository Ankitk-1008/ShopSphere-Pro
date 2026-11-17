
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class CheckoutCalculate(BaseModel):
    discount_code: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")


class DiscountCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    discount_type: str
    discount_value: Decimal = Field(gt=0)
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0)
    max_discount: Optional[Decimal] = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class CheckoutSettingsUpdate(BaseModel):
    shipping_charge: Decimal = Field(ge=0)
    free_shipping_threshold: Decimal = Field(ge=0)
    tax_percentage: Decimal = Field(ge=0, le=100)

    model_config = ConfigDict(extra="forbid")
