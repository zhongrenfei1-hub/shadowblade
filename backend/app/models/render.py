from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RenderTask(Base):
    __tablename__ = "render_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    priority: Mapped[str] = mapped_column(
        String(16), default="normal"
    )  # low | normal | high | rush
    status: Mapped[str] = mapped_column(
        String(32), default="queued"
    )  # queued | running | succeeded | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    worker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
