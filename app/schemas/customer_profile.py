from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CustomerProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    email: EmailStr | None = None

    phone: str | None = Field(
        default=None,
        pattern=r"^[6-9]\d{9}$"
    )

    model_config = ConfigDict(extra="forbid")


class DeactivationRequestCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class DeactivationRequestReview(BaseModel):
    status: str = Field(pattern=r"^(APPROVED|REJECTED)$")