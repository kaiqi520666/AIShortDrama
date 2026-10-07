import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        Index("ix_generation_tasks_node_created_at", "node_id", "created_at"),
        Index("ix_generation_tasks_status", "status"),
        Index("ix_generation_tasks_provider_task_id", "provider_task_id"),
        Index(
            "uq_generation_tasks_provider_client",
            "provider", "client_request_id",
            unique=True,
            postgresql_where=text("client_request_id IS NOT NULL"),
        ),
        Index(
            "uq_generation_tasks_provider_remote",
            "provider", "task_type", "provider_task_id",
            unique=True,
            postgresql_where=text("provider_task_id IS NOT NULL"),
        ),
        Index("ix_generation_tasks_workspace_status_created_at", "workspace_id", "status", "created_at"),
        Index("ix_generation_tasks_user_status_created_at", "user_id", "status", "created_at"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'timeout', 'cancelled', 'needs_review')",
            name="ck_generation_tasks_status",
        ),
        CheckConstraint(
            "credit_status IN ('none', 'frozen', 'consumed', 'refunded')",
            name="ck_generation_tasks_credit_status",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="ck_generation_tasks_progress"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64))
    task_type: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default=text("'queued'"))
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))
    prompt: Mapped[str | None] = mapped_column(Text)
    provider_task_id: Mapped[str | None] = mapped_column(String(128))
    client_request_id: Mapped[str | None] = mapped_column(
        String(128), default=lambda: str(uuid.uuid4())
    )
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    submission_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    worker_lease_token: Mapped[str | None] = mapped_column(String(36))
    worker_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    frozen_credits: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    charged_credits: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    credit_status: Mapped[str] = mapped_column(String(20), default="none", server_default=text("'none'"))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    diagnostic_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retry_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    recovery_attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
