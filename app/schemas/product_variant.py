
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductVariantCreate(BaseModel):
    product_id: int = Field(gt=0)
    sku: str = Field(min_length=2, max_length=500)
    size: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=2, max_length=500)
    size: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, max_length=500)
    price: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    stock: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")
