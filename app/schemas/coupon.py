
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    discount_type: Literal["percentage", "fixed"]
    discount_value: Decimal = Field(gt=0)
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0)
    max_discount: Optional[Decimal] = Field(default=None, gt=0)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    model_config = ConfigDict(extra="forbid")


class CouponUpdate(BaseModel):
    discount_type: Optional[Literal["percentage", "fixed"]] = None
    discount_value: Optional[Decimal] = Field(default=None, gt=0)
    min_order_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_discount: Optional[Decimal] = Field(default=None, gt=0)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    model_config = ConfigDict(extra="forbid")
