
from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, ForeignKey
)
from sqlalchemy.sql import func

from app.core.database import Base


class CustomerRegistration(Base):
    __tablename__ = "customer_registrations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    registration_status = Column(
        String(30),
        default="PENDING",
        nullable=False
    )

    email_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    verification_token = Column(
        String(255),
        unique=True,
        nullable=True
    )

    verification_expires_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    phone = Column(String(20), nullable=True)
    

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
