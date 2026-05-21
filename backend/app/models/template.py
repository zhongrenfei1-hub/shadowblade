from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(
        String(32)
    )  # marketing | training | product_demo | social | onboarding
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=30)
    description: Mapped[str] = mapped_column(Text, default="")
    preview_url: Mapped[str] = mapped_column(String(512))
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
