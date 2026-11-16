
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=500)
    slug: str = Field(min_length=2, max_length=500)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=500)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=500)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")
