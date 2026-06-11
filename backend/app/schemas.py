from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_name: str
    platform: str
    manufacturer: str
    model: str
    media_owner: str | None = None
    os_version: str
    webview_version: str
    lmx_app_version: str
    latest_status: str
    latest_score: int
    last_seen: datetime
    latest_overall_health_status: str | None = None
    latest_content_download_status: str | None = None
    latest_playback_status: str | None = None
    latest_log_status: str | None = None

    @field_serializer("last_seen")
    def serialize_last_seen(self, value: datetime) -> str:
        return format_utc_timestamp(value)


class ReportOut(BaseModel):
    id: int
    device_id: int
    created_at: datetime
    final_status: str
    score: int
    summary: str
    recommendations: str
    raw_json: dict[str, Any]
    lmx_app_status: dict[str, Any] | None = None
    content_download_status: dict[str, Any] | None = None
    playback_validation: dict[str, Any] | None = None
    log_validation: dict[str, Any] | None = None
    overall_health_status: str | None = None
    overall_health: dict[str, Any] | str | None = None
    troubleshooting_recommendation: str | None = None
    device_compatibility: dict[str, Any] | None = None
    final_recommendation: str | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return format_utc_timestamp(value)


class DeviceDetail(DeviceOut):
    reports: list[ReportOut]


class DeviceUpdate(BaseModel):
    media_owner: str | None = None


def format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        utc_value = value
    else:
        utc_value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_value.isoformat(timespec="seconds") + "Z"
