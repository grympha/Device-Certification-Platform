from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .certification import evaluate_report
from .database import Base, engine, get_db
from .models import Device, DiagnosticReport
from .schemas import DeviceDetail, DeviceOut, DeviceUpdate, ReportOut

Base.metadata.create_all(bind=engine)


REPORT_HEALTH_COLUMNS = {
    "lmx_app_status": "TEXT",
    "content_download_status": "TEXT",
    "playback_validation": "TEXT",
    "log_validation": "TEXT",
    "overall_health_status": "VARCHAR(50)",
    "overall_health": "TEXT",
    "troubleshooting_recommendation": "TEXT",
    "device_compatibility": "TEXT",
}


def _ensure_missing_columns() -> None:
    inspector = inspect(engine)

    with engine.begin() as connection:
        device_columns = _table_columns(inspector, "devices")
        if "media_owner" not in device_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN media_owner TEXT"))

        report_columns = _table_columns(inspector, "diagnostic_reports")
        for column_name, column_type in REPORT_HEALTH_COLUMNS.items():
            if column_name not in report_columns:
                connection.execute(text(f"ALTER TABLE diagnostic_reports ADD COLUMN {column_name} {column_type}"))


def _table_columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


_ensure_missing_columns()

app = FastAPI(title="LMX Device Certification API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/reports")
def create_report(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    evaluation = evaluate_report(payload)
    now = datetime.now(timezone.utc)
    device = _find_or_create_device(payload, db)

    device.device_name = payload.get("device_name") or device.device_name
    device.platform = payload.get("platform") or device.platform
    device.manufacturer = payload.get("manufacturer") or ""
    device.model = payload.get("model") or ""
    incoming_media_owner = _media_owner_from_payload(payload)
    if incoming_media_owner:
        device.media_owner = incoming_media_owner
    device.os_version = str(payload.get("os_version") or "")
    device.webview_version = str(payload.get("webview_version") or "")
    device.lmx_app_version = str(payload.get("lmx_app_version") or "")
    device.latest_status = evaluation["final_status"]
    device.latest_score = evaluation["score"]
    device.last_seen = now

    raw_with_checks = dict(payload)
    raw_with_checks["checks"] = evaluation["checks"]
    raw_with_checks["media_owner"] = device.media_owner
    health_fields = _extract_health_fields(payload)
    raw_with_checks.update({key: value for key, value in health_fields.items() if value is not None})

    report = DiagnosticReport(
        device=device,
        created_at=now,
        raw_json=json.dumps(raw_with_checks),
        final_status=evaluation["final_status"],
        score=evaluation["score"],
        summary=evaluation["summary"],
        recommendations=evaluation["recommendations"],
        lmx_app_status=_json_or_none(health_fields["lmx_app_status"]),
        content_download_status=_json_or_none(health_fields["content_download_status"]),
        playback_validation=_json_or_none(health_fields["playback_validation"]),
        log_validation=_json_or_none(health_fields["log_validation"]),
        overall_health_status=health_fields["overall_health_status"],
        overall_health=_json_or_none(health_fields["overall_health"]),
        troubleshooting_recommendation=health_fields["troubleshooting_recommendation"],
        device_compatibility=_json_or_none(health_fields["device_compatibility"]),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "device_id": device.id,
        **evaluation,
        "lmx_app_status": health_fields["lmx_app_status"],
        "content_download_status": health_fields["content_download_status"],
        "playback_validation": health_fields["playback_validation"],
        "log_validation": health_fields["log_validation"],
        "overall_health_status": health_fields["overall_health_status"],
        "overall_health": health_fields["overall_health"],
        "troubleshooting_recommendation": health_fields["troubleshooting_recommendation"],
        "device_compatibility": health_fields["device_compatibility"],
    }


@app.get("/api/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)) -> list[Device]:
    return list(db.scalars(select(Device).order_by(Device.last_seen.desc())).all())


@app.get("/api/devices/{device_id}", response_model=DeviceDetail)
def get_device(device_id: int, db: Session = Depends(get_db)) -> DeviceDetail:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceDetail(
        **DeviceOut.model_validate(device).model_dump(),
        reports=[_report_out(report) for report in device.reports],
    )


@app.patch("/api/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    media_owner = (payload.media_owner or "").strip()
    device.media_owner = media_owner or None
    db.commit()
    db.refresh(device)
    return device


@app.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportOut:
    report = db.get(DiagnosticReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(report)


@app.get("/api/export/{report_id}")
def export_report(
    report_id: int,
    format: str = Query("html", pattern="^(html|json)$"),
    db: Session = Depends(get_db),
):
    report = db.get(DiagnosticReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "json":
        return JSONResponse(_report_out(report).model_dump(mode="json"))

    return HTMLResponse(_html_report(report))


def _find_or_create_device(payload: dict[str, Any], db: Session) -> Device:
    device_name = payload.get("device_name") or "Unknown Device"
    platform = payload.get("platform") or "Android"
    manufacturer = payload.get("manufacturer") or ""
    model = payload.get("model") or ""

    existing = db.scalar(
        select(Device).where(
            Device.device_name == device_name,
            Device.platform == platform,
            Device.manufacturer == manufacturer,
            Device.model == model,
        )
    )
    if existing:
        return existing

    device = Device(
        device_name=device_name,
        platform=platform,
        manufacturer=manufacturer,
        model=model,
    )
    db.add(device)
    db.flush()
    return device


def _media_owner_from_payload(payload: dict[str, Any]) -> str:
    media_owner = str(payload.get("media_owner") or "").strip()
    if media_owner:
        return media_owner
    return str(payload.get("client_name") or "").strip()


def _report_out(report: DiagnosticReport) -> ReportOut:
    raw = json.loads(report.raw_json)
    return ReportOut(
        id=report.id,
        device_id=report.device_id,
        created_at=report.created_at,
        final_status=report.final_status,
        score=report.score,
        summary=report.summary,
        recommendations=report.recommendations,
        raw_json=raw,
        lmx_app_status=_json_from_column(report.lmx_app_status, raw.get("lmx_app_status")),
        content_download_status=_json_from_column(report.content_download_status, raw.get("content_download_status")),
        playback_validation=_json_from_column(report.playback_validation, raw.get("playback_validation")),
        log_validation=_json_from_column(report.log_validation, raw.get("log_validation")),
        overall_health_status=report.overall_health_status or raw.get("overall_health_status") or "UNKNOWN",
        overall_health=_json_from_column(report.overall_health, raw.get("overall_health")),
        troubleshooting_recommendation=report.troubleshooting_recommendation or raw.get("troubleshooting_recommendation"),
        device_compatibility=_json_from_column(report.device_compatibility, raw.get("device_compatibility")),
    )


def _extract_health_fields(payload: dict[str, Any]) -> dict[str, Any]:
    lmx_app = _normalize_lmx_app_status(payload.get("lmx_app_status"))
    content = _normalize_content_download_status(payload.get("content_download_status"))
    playback = _normalize_playback_validation(payload.get("playback_validation"))
    logs = _normalize_log_validation(payload.get("log_validation"))
    overall_health = payload.get("overall_health")
    overall_status = str(payload.get("overall_health_status") or "").strip()
    if not overall_status and isinstance(overall_health, dict):
        overall_status = str(overall_health.get("status") or "").strip()
    if not overall_status:
        overall_status = "UNKNOWN"

    return {
        "lmx_app_status": lmx_app,
        "content_download_status": content,
        "playback_validation": playback,
        "log_validation": logs,
        "overall_health_status": overall_status,
        "overall_health": overall_health,
        "troubleshooting_recommendation": payload.get("troubleshooting_recommendation"),
        "device_compatibility": payload.get("device_compatibility"),
    }


def _normalize_lmx_app_status(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    normalized.setdefault("version", normalized.get("version_name"))
    normalized.setdefault("version_name", normalized.get("version"))
    return normalized


def _normalize_content_download_status(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    normalized.setdefault("media_folder_found", normalized.get("media_folder_exists"))
    normalized.setdefault("download_size_bytes", normalized.get("total_download_size_bytes"))
    normalized.setdefault("download_size_readable", _readable_bytes(normalized.get("download_size_bytes")))
    normalized.setdefault("last_content_update", normalized.get("last_content_update_timestamp"))
    return normalized


def _normalize_playback_validation(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    normalized.setdefault("audit_file_found", normalized.get("audit_file_exists"))
    normalized.setdefault("last_playback_time", normalized.get("last_playback_date_time"))
    normalized.setdefault("playlist", normalized.get("current_or_last_playlist"))
    return normalized


def _normalize_log_validation(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    normalized.setdefault("log_folder_found", normalized.get("log_folder_exists"))
    if isinstance(normalized.get("log_files_found"), int):
        normalized.setdefault("log_file_count", normalized.get("log_files_found"))
        normalized["log_files_found"] = normalized["log_files_found"] > 0
    if isinstance(normalized.get("crash_logs_found"), int):
        normalized.setdefault("crash_log_file_count", normalized.get("crash_logs_found"))
        normalized["crash_logs_found"] = normalized["crash_logs_found"] > 0
    normalized.setdefault("latest_log_update", normalized.get("latest_log_update_timestamp"))
    normalized.setdefault("latest_crash_timestamp", normalized.get("latest_crash_log_timestamp"))
    return normalized


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _json_from_column(value: str | None, fallback: Any = None) -> Any:
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return fallback


def _readable_bytes(value: Any) -> str | None:
    try:
        size = int(value or 0)
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return "0 MB"
    return f"{round(size / 1024 / 1024)} MB"


def _html_report(report: DiagnosticReport) -> str:
    raw = json.loads(report.raw_json)
    checks = raw.get("checks", {})
    failed = [value["message"] for value in checks.values() if value.get("status") == "FAIL"]
    limitations = [value["message"] for value in checks.values() if value.get("status") == "WARNING"]
    failed_html = "".join(f"<li>{item}</li>" for item in failed) or "<li>None</li>"
    limitations_html = "".join(f"<li>{item}</li>" for item in limitations) or "<li>None</li>"

    return f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>LMX Device Certification Report</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; color: #172026; }}
          h1 {{ margin-bottom: 4px; }}
          .status {{ display: inline-block; padding: 8px 12px; border: 1px solid #172026; }}
          table {{ border-collapse: collapse; width: 100%; margin-top: 24px; }}
          th, td {{ border-bottom: 1px solid #dde3ea; text-align: left; padding: 10px; }}
        </style>
      </head>
      <body>
        <h1>LMX Device Certification Report</h1>
        <p class="status">{report.final_status} - Score {report.score}</p>
        <table>
          <tr><th>Device</th><td>{raw.get("device_name", "")}</td></tr>
          <tr><th>Media Owner / Client</th><td>{raw.get("media_owner") or raw.get("client_name") or "Unassigned"}</td></tr>
          <tr><th>Platform</th><td>{raw.get("platform", "")}</td></tr>
          <tr><th>Manufacturer</th><td>{raw.get("manufacturer", "")}</td></tr>
          <tr><th>Model</th><td>{raw.get("model", "")}</td></tr>
          <tr><th>OS Version</th><td>{raw.get("os_version", "")}</td></tr>
          <tr><th>WebView Version</th><td>{raw.get("webview_version", "")}</td></tr>
          <tr><th>RAM</th><td>{raw.get("ram_total_gb", "")}GB</td></tr>
          <tr><th>Storage Available</th><td>{raw.get("storage_available_gb", "")}GB</td></tr>
          <tr><th>LMX Content Version</th><td>{raw.get("lmx_app_version", "")}</td></tr>
        </table>
        <h2>Failed Checks</h2>
        <ul>{failed_html}</ul>
        <h2>Limitations</h2>
        <ul>{limitations_html}</ul>
        <h2>Recommendation</h2>
        <p>{report.recommendations}</p>
      </body>
    </html>
    """
