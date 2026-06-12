from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .certification import build_device_report_summary, evaluate_report
from .database import Base, engine, get_db
from .models import Device, DiagnosticReport
from .report_exports import build_docx_report, build_pdf_report
from .schemas import DeviceDetail, DeviceNameUpdate, DeviceOut, DeviceUpdate, ReportOut, SuccessResponse

Base.metadata.create_all(bind=engine)


REPORT_EXTRA_COLUMNS = {
    "final_recommendation": "VARCHAR(100)",
}


def _ensure_missing_columns() -> None:
    inspector = inspect(engine)

    with engine.begin() as connection:
        device_columns = _table_columns(inspector, "devices")
        if "media_owner" not in device_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN media_owner TEXT"))
        if "custom_device_name" not in device_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN custom_device_name TEXT"))

        report_columns = _table_columns(inspector, "diagnostic_reports")
        for column_name, column_type in REPORT_EXTRA_COLUMNS.items():
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
    allow_origin_regex=r"(https://.*\.onrender\.com|http://(localhost|127\.0\.0\.1):\d+)",
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
    raw_with_checks["final_recommendation"] = evaluation["final_recommendation"]
    raw_with_checks["device_report_summary"] = evaluation["device_report_summary"]
    raw_with_checks["score_label"] = evaluation["score_label"]
    if "deployment_readiness" in evaluation:
        raw_with_checks["deployment_readiness"] = evaluation["deployment_readiness"]

    report = DiagnosticReport(
        device=device,
        created_at=now,
        raw_json=json.dumps(raw_with_checks),
        final_status=evaluation["final_status"],
        score=evaluation["score"],
        summary=evaluation["summary"],
        recommendations=evaluation["recommendations"],
        final_recommendation=evaluation["final_recommendation"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "device_id": device.id,
        **evaluation,
        "final_recommendation": evaluation["final_recommendation"],
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


@app.put("/api/devices/{device_id}/name", response_model=SuccessResponse)
def update_device_name(device_id: int, payload: DeviceNameUpdate, db: Session = Depends(get_db)) -> dict[str, bool]:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    custom_name = payload.device_name.strip()
    if not custom_name:
        raise HTTPException(status_code=400, detail="Device name is required")

    device.custom_device_name = custom_name
    db.commit()
    return {"success": True}


@app.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportOut:
    report = db.get(DiagnosticReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(report)


@app.get("/api/reports/{report_id}/pdf")
def get_report_pdf(report_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    report = db.get(DiagnosticReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    context = _export_context(report)
    pdf_bytes = build_pdf_report(context)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lmx-device-certification-report-{report_id}.pdf"'},
    )


@app.get("/api/reports/{report_id}/docx")
def get_report_docx(report_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    report = db.get(DiagnosticReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    context = _export_context(report)
    docx_bytes = build_docx_report(context)
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="lmx-device-certification-report-{report_id}.docx"'},
    )


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
    summary = _device_report_summary(report, raw)
    return ReportOut(
        id=report.id,
        device_id=report.device_id,
        created_at=report.created_at,
        final_status=report.final_status,
        score=report.score,
        summary=report.summary,
        recommendations=report.recommendations,
        raw_json=raw,
        final_recommendation=report.final_recommendation or raw.get("final_recommendation"),
        device_report_summary=summary,
    )


def _device_report_summary(report: DiagnosticReport, raw: dict[str, Any]) -> dict[str, Any]:
    existing = raw.get("device_report_summary")
    if isinstance(existing, dict):
        return _sanitize_windows_summary(existing, raw)
    checks = raw.get("checks") if isinstance(raw.get("checks"), dict) else {}
    return _sanitize_windows_summary(
        build_device_report_summary(report.final_status, checks, report.recommendations),
        raw,
    )


def _export_context(report: DiagnosticReport) -> dict[str, Any]:
    raw = json.loads(report.raw_json)
    return {
        "id": report.id,
        "raw": raw,
        "device_name": _display_device_name(report.device, raw),
        "checks": raw.get("checks") if isinstance(raw.get("checks"), dict) else {},
        "created_at": _format_export_date(report.created_at),
        "final_status": report.final_status,
        "final_recommendation": report.final_recommendation or raw.get("final_recommendation") or "Not Recommended",
        "score": report.score,
        "score_label": raw.get("score_label") or _score_label(report.score),
        "summary": report.summary,
        "recommendations": report.recommendations,
        "device_report_summary": _device_report_summary(report, raw),
    }


def _format_export_date(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _score_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Limited"
    return "Not Recommended"


def _sanitize_windows_summary(summary: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    if str(raw.get("platform") or "").lower() != "windows":
        return summary

    def sanitize(value: Any) -> str:
        return (
            str(value or "")
            .replace(
                "Install LMX Content package com.qruize.quad42.media.app.",
                "Install LMX Content for Windows in C:\\Program Files\\mac-media-player using MW Content.exe or mac-media-player.exe.",
            )
            .replace("com.qruize.quad42.media.app", "LMX Content for Windows")
            .replace(
                "LMX Content may be installed but not launchable from Android.",
                "LMX Content for Windows may be installed but MW Content.exe or mac-media-player.exe may not be launchable.",
            )
            .replace(
                "Reinstall or update LMX Content, then confirm the app can launch.",
                "Reinstall or update LMX Content for Windows, then confirm MW Content.exe or mac-media-player.exe can launch.",
            )
            .replace(
                "Update LMX Content to Android version 2.9.1.2 native or newer, or Windows version 1.0.34 or newer.",
                "Update LMX Content for Windows to version 1.0.34 or newer.",
            )
        )

    sanitized = dict(summary)
    for key in ["good_points", "warning_points", "failed_points", "likely_causes", "recommended_actions"]:
        sanitized[key] = [sanitize(item) for item in summary.get(key) or []]
    sanitized["overall_summary"] = sanitize(summary.get("overall_summary"))
    return sanitized


def _html_report(report: DiagnosticReport) -> str:
    raw = json.loads(report.raw_json)
    checks = raw.get("checks", {})
    final_recommendation = report.final_recommendation or raw.get("final_recommendation") or "Not Recommended"
    failed = [value["message"] for value in checks.values() if value.get("status") == "FAIL"]
    limitations = [value["message"] for value in checks.values() if value.get("status") == "WARNING"]
    failed_html = "".join(f"<li>{item}</li>" for item in failed) or "<li>None</li>"
    limitations_html = "".join(f"<li>{item}</li>" for item in limitations) or "<li>None</li>"
    recommendations = _sanitize_windows_text(report.recommendations, raw)
    manufacturer = _normalize_windows_hardware_name(raw.get("manufacturer", ""), raw)
    model = _normalize_windows_hardware_name(raw.get("model", ""), raw)
    os_version = _format_windows_version(raw) if str(raw.get("platform") or "").lower() == "windows" else raw.get("os_version", "")
    device_name = _display_device_name(report.device, raw)

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
          <tr><th>Device Certification Result</th><td>{report.final_status}</td></tr>
          <tr><th>Final Recommendation</th><td>{final_recommendation}</td></tr>
          <tr><th>Device</th><td>{device_name}</td></tr>
          <tr><th>Media Owner / Client</th><td>{raw.get("media_owner") or raw.get("client_name") or "Unassigned"}</td></tr>
          <tr><th>Platform</th><td>{raw.get("platform", "")}</td></tr>
          <tr><th>Manufacturer</th><td>{manufacturer}</td></tr>
          <tr><th>Model</th><td>{model}</td></tr>
          <tr><th>OS Version</th><td>{os_version}</td></tr>
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
        <p>{recommendations}</p>
      </body>
    </html>
    """


def _sanitize_windows_text(value: Any, raw: dict[str, Any]) -> str:
    if str(raw.get("platform") or "").lower() != "windows":
        return str(value or "")
    return (
        str(value or "")
        .replace(
            "Install LMX Content package com.qruize.quad42.media.app.",
            "Install LMX Content for Windows in C:\\Program Files\\mac-media-player using MW Content.exe or mac-media-player.exe.",
        )
        .replace("com.qruize.quad42.media.app", "LMX Content for Windows")
        .replace(
            "LMX Content may be installed but not launchable from Android.",
            "LMX Content for Windows may be installed but MW Content.exe or mac-media-player.exe may not be launchable.",
        )
        .replace(
            "Update LMX Content to Android version 2.9.1.2 native or newer, or Windows version 1.0.34 or newer.",
            "Update LMX Content for Windows to version 1.0.34 or newer.",
        )
    )


def _normalize_windows_hardware_name(value: Any, raw: dict[str, Any]) -> str:
    text = str(value or "")
    if str(raw.get("platform") or "").lower() == "windows" and text.strip().lower() in {"system manufacturer", "system product name"}:
        return "Custom Built PC"
    return text


def _format_windows_version(raw: dict[str, Any]) -> str:
    version = str(raw.get("windows_version") or raw.get("os_version") or "")
    try:
        build = int(raw.get("windows_build_number") or version.split(".")[-1])
    except (TypeError, ValueError):
        return version
    if build >= 26100:
        return f"Windows 11 24H2 - Build {build}"
    if build >= 22631:
        return f"Windows 11 23H2 - Build {build}"
    if build >= 22621:
        return f"Windows 11 22H2 - Build {build}"
    if build >= 22000:
        return f"Windows 11 21H2 - Build {build}"
    if build >= 19045:
        return f"Windows 10 22H2 - Build {build}"
    if build >= 19044:
        return f"Windows 10 21H2 - Build {build}"
    if build >= 19043:
        return f"Windows 10 21H1 - Build {build}"
    if build >= 19042:
        return f"Windows 10 20H2 - Build {build}"
    return f"Windows 10 - Build {build}"


def _display_device_name(device: Device, raw: dict[str, Any]) -> str:
    return (
        device.custom_device_name
        or raw.get("device_name")
        or raw.get("computer_name")
        or raw.get("model")
        or device.device_name
        or "Unknown Device"
    )
