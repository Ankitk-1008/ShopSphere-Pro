
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class AddressCreate(BaseModel):
    address_type: Literal["BILLING", "SHIPPING"]

    line1: str = Field(min_length=5, max_length=500)
    line2: str | None = None

    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)

    postal_code: str = Field(pattern=r"^\d{6}$")
    country: str = Field(min_length=2, max_length=100)

    is_default: bool = False

    model_config = ConfigDict(extra="forbid")


class AddressUpdate(BaseModel):
    address_type: Literal["BILLING", "SHIPPING"] | None = None
    line1: str | None = Field(default=None, min_length=5, max_length=500)
    line2: str | None = None
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    postal_code: str | None = Field(default=None, pattern=r"^\d{6}$")
    country: str | None = Field(default=None, min_length=2, max_length=100)

    model_config = ConfigDict(extra="forbid")


class DefaultAddressUpdate(BaseModel):
    is_default: bool