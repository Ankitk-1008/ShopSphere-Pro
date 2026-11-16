
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=500)
    description: Optional[str] = None
    sku: str = Field(min_length=2, max_length=500)
    category_id: Optional[int] = Field(default=None, gt=0)
    brand_id: Optional[int] = Field(default=None, gt=0)
    base_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=500)
    description: Optional[str] = None
    sku: Optional[str] = Field(default=None, min_length=2, max_length=500)
    category_id: Optional[int] = Field(default=None, gt=0)
    brand_id: Optional[int] = Field(default=None, gt=0)
    base_price: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")
