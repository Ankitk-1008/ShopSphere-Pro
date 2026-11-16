
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class CustomerRegisterSchema(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(
        pattern=r"^(?:\+91[- ]?)?[6-9]\d{9}$"
    )
    password: str = Field(min_length=8, max_length=128)


class CustomerRegistrationResponse(BaseModel):
    message: str
    user_id: int
    registration_status: str
    email_verified: bool


class EmailVerificationSchema(BaseModel):
    token: str


class CustomerRegistrationUpdateSchema(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        pattern=r"^[6-9]\d{9}$"
    )

    model_config = ConfigDict(extra="forbid")