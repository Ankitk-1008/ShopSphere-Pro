from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    location: str = Field(min_length=2, max_length=255)
    capacity: int = Field(ge=0)
    status: Literal["active", "inactive", "maintenance"] = "active"

    model_config = ConfigDict(extra="forbid")


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    location: Optional[str] = Field(default=None, max_length=255)
    capacity: Optional[int] = Field(default=None, ge=0)
    status: Optional[
        Literal["active", "inactive", "maintenance"]
    ] = None

    model_config = ConfigDict(extra="forbid")


class WarehouseStockAction(BaseModel):
    product_id: int = Field(gt=0)
    variant_id: Optional[int] = Field(default=None, gt=0)
    quantity: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")