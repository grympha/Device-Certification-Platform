from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_name: str
    platform: str
    manufacturer: str
    model: str
    os_version: str
    webview_version: str
    lmx_app_version: str
    latest_status: str
    latest_score: int
    last_seen: datetime


class ReportOut(BaseModel):
    id: int
    device_id: int
    created_at: datetime
    final_status: str
    score: int
    summary: str
    recommendations: str
    raw_json: dict[str, Any]


class DeviceDetail(DeviceOut):
    reports: list[ReportOut]

