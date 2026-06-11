from datetime import datetime, timezone
import json
from typing import Any

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
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reports: Mapped[list["DiagnosticReport"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(DiagnosticReport.created_at)",
    )

    @property
    def latest_overall_health_status(self) -> str | None:
        report = self.reports[0] if self.reports else None
        if not report:
            return None
        return report.overall_health_status or _raw_value(report.raw_json, "overall_health_status")

    @property
    def latest_content_download_status(self) -> str | None:
        report = self.reports[0] if self.reports else None
        return _status_from_report(report, "content_download_status")

    @property
    def latest_playback_status(self) -> str | None:
        report = self.reports[0] if self.reports else None
        return _status_from_report(report, "playback_validation")

    @property
    def latest_log_status(self) -> str | None:
        report = self.reports[0] if self.reports else None
        return _status_from_report(report, "log_validation")


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    raw_json: Mapped[str] = mapped_column(Text)
    final_status: Mapped[str] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[str] = mapped_column(Text)
    lmx_app_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_download_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    playback_validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_health_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    overall_health: Mapped[str | None] = mapped_column(Text, nullable=True)
    troubleshooting_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_compatibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_recommendation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    device: Mapped[Device] = relationship(back_populates="reports")


def _status_from_report(report: DiagnosticReport | None, field_name: str) -> str | None:
    if not report:
        return None
    value = getattr(report, field_name, None)
    if value:
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed.get("status")
        except json.JSONDecodeError:
            return None
    raw_field = _raw_value(report.raw_json, field_name)
    if isinstance(raw_field, dict):
        return raw_field.get("status")
    return None


def _raw_value(raw_json: str | None, field_name: str) -> Any:
    if not raw_json:
        return None
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    return parsed.get(field_name)
