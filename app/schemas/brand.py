
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=500)
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=500)
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")
