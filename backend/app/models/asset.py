import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_user_media_created_at", "user_id", "media_type", "created_at"),
        Index("ix_assets_workspace_id", "workspace_id"),
        Index("ix_assets_generation_task_id", "generation_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL")
    )
    generation_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generation_tasks.id", ondelete="SET NULL")
    )
    node_id: Mapped[str | None] = mapped_column(String(64))
    media_type: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str | None] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(2048))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column(Float)
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
