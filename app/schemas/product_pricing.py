
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class ProductPricingCreate(BaseModel):

    base_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    sale_price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    valid_from: datetime

    valid_until: Optional[datetime] = None

    reason: Optional[str] = Field(
        default=None,
        max_length=500
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_prices(self):

        if (
            self.sale_price is not None
            and self.sale_price >= self.base_price
        ):
            raise ValueError(
                "Sale price must be less than base price"
            )

        if (
            self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError(
                "valid_until must be later than valid_from"
            )

        return self


class ProductPricingUpdate(BaseModel):

    base_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    sale_price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    valid_from: datetime

    valid_until: Optional[datetime] = None

    reason: Optional[str] = Field(
        default=None,
        max_length=500
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_prices(self):

        if (
            self.sale_price is not None
            and self.sale_price >= self.base_price
        ):
            raise ValueError(
                "Sale price must be less than base price"
            )

        if (
            self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError(
                "valid_until must be later than valid_from"
            )

        return self
