from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .certification import evaluate_report
from .database import Base, engine, get_db
from .models import Device, DiagnosticReport
from .schemas import DeviceDetail, DeviceOut, ReportOut

Base.metadata.create_all(bind=engine)

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
    now = datetime.utcnow()
    device = _find_or_create_device(payload, db)

    device.device_name = payload.get("device_name") or device.device_name
    device.platform = payload.get("platform") or device.platform
    device.manufacturer = payload.get("manufacturer") or ""
    device.model = payload.get("model") or ""
    device.os_version = str(payload.get("os_version") or "")
    device.webview_version = str(payload.get("webview_version") or "")
    device.lmx_app_version = str(payload.get("lmx_app_version") or "")
    device.latest_status = evaluation["final_status"]
    device.latest_score = evaluation["score"]
    device.last_seen = now

    raw_with_checks = dict(payload)
    raw_with_checks["checks"] = evaluation["checks"]

    report = DiagnosticReport(
        device=device,
        created_at=now,
        raw_json=json.dumps(raw_with_checks),
        final_status=evaluation["final_status"],
        score=evaluation["score"],
        summary=evaluation["summary"],
        recommendations=evaluation["recommendations"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {"report_id": report.id, "device_id": device.id, **evaluation}


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


def _report_out(report: DiagnosticReport) -> ReportOut:
    return ReportOut(
        id=report.id,
        device_id=report.device_id,
        created_at=report.created_at,
        final_status=report.final_status,
        score=report.score,
        summary=report.summary,
        recommendations=report.recommendations,
        raw_json=json.loads(report.raw_json),
    )


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
