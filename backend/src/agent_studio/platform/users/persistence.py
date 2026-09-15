import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agent_studio.platform.database import Base


class AppUserModel(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        UniqueConstraint("auth_issuer", "auth_subject", name="uq_app_user_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    auth_issuer: Mapped[str] = mapped_column(Text)
    auth_subject: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
