from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    primary_color: Mapped[str] = mapped_column(String(16), default="#0F2A4A")
    accent_color: Mapped[str] = mapped_column(String(16), default="#22D3B7")
    font_heading: Mapped[str] = mapped_column(String(64), default="Inter")
    font_body: Mapped[str] = mapped_column(String(64), default="Inter")
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    intro_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    outro_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    voice: Mapped[str] = mapped_column(String(64), default="alloy-en-female")
    tone: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
