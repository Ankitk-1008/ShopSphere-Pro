
from pydantic import BaseModel, Field, ConfigDict


class WishlistCreate(BaseModel):
    product_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")
