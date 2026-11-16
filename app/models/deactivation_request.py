from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AccountDeactivationRequest(Base):
    __tablename__ = "account_deactivation_requests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    reason = Column(Text, nullable=True)

    status = Column(
        String(20),
        default="PENDING",
        nullable=False
    )

    reviewed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    reviewed_at = Column(DateTime(timezone=True), nullable=True)