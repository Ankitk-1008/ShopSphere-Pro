from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TransferCreate(BaseModel):
    source_warehouse_id: int = Field(gt=0)
    destination_warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    variant_id: Optional[int] = Field(default=None, gt=0)
    requested_quantity: int = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class TransferDispatch(BaseModel):
    quantity: int = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class TransferReceipt(BaseModel):
    quantity: int = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")