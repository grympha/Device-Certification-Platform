from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_name: Mapped[str] = mapped_column(String(200), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    media_owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    os_version: Mapped[str] = mapped_column(String(50), default="")
    webview_version: Mapped[str] = mapped_column(String(100), default="")
    lmx_app_version: Mapped[str] = mapped_column(String(100), default="")
    latest_status: Mapped[str] = mapped_column(String(50), default="Not Recommended")
    latest_score: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reports: Mapped[list["DiagnosticReport"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(DiagnosticReport.created_at)",
    )


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_json: Mapped[str] = mapped_column(Text)
    final_status: Mapped[str] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[str] = mapped_column(Text)

    device: Mapped[Device] = relationship(back_populates="reports")
