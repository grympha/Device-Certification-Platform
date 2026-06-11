from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_BACKEND_URL = "https://device-certification-platform.onrender.com/api/reports"
DEFAULT_DASHBOARD_URL = "https://device-certification-dashboard.onrender.com/"
PASS = "PASS"
WARNING = "WARNING"
FAIL = "FAIL"
WINDOWS_SCORE_WEIGHTS = {
    "windows_os": 15,
    "cpu": 10,
    "ram": 15,
    "storage": 10,
    "gpu": 10,
    "network": 10,
    "time_timezone": 5,
    "lmx_app_installed": 10,
    "lmx_version": 10,
    "lmx_app_launch": 10,
    "pull_to_content": 5,
}
LMX_CANDIDATE_PATHS = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "mac-media-player",
]
LMX_EXECUTABLE_NAMES = ("MW Content.exe", "mac-media-player.exe")


def main() -> int:
    parser = argparse.ArgumentParser(description="LMX Windows Device Certification Agent")
    parser.add_argument("--backend-url", default=os.environ.get("LMX_BACKEND_URL", DEFAULT_BACKEND_URL))
    parser.add_argument("--output", default="report.json")
    parser.add_argument("--upload", action="store_true", help="Upload report to backend after generating JSON")
    args = parser.parse_args()

    report = collect_report()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {output_path.resolve()}")

    if args.upload:
        status, body = upload_report(args.backend_url, report)
        print(f"Upload result: HTTP {status}")
        if body:
            print(body[:1000])
    return 0


def collect_report() -> dict[str, Any]:
    system = _powershell_json(
        "Get-CimInstance Win32_ComputerSystem | "
        "Select-Object Manufacturer,Model,SystemType,TotalPhysicalMemory"
    )
    os_info = _powershell_json(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,Version,BuildNumber,LastBootUpTime"
    )
    cpu_info = _powershell_json("Get-CimInstance Win32_Processor | Select-Object -First 1 Name,Architecture")
    disk_info = _powershell_json(
        "Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\" | "
        "Select-Object Size,FreeSpace"
    )
    gpu_info = _powershell_json("Get-CimInstance Win32_VideoController | Select-Object -First 1 Name")
    screen = _powershell_json(
        "Add-Type -AssemblyName System.Windows.Forms; "
        "[PSCustomObject]@{Width=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width;"
        "Height=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height}"
    )

    lmx_executable = _find_lmx_executable()
    lmx_version = _detect_lmx_version(lmx_executable)
    online = _internet_available()

    report = {
        "platform": "Windows",
        "device_name": socket.gethostname(),
        "computer_name": socket.gethostname(),
        "manufacturer": _get(system, "Manufacturer"),
        "model": _get(system, "Model"),
        "windows_edition": _get(os_info, "Caption"),
        "windows_version": _get(os_info, "Version") or platform.version(),
        "os_version": _get(os_info, "Caption") or platform.platform(),
        "windows_build_number": _get(os_info, "BuildNumber"),
        "system_type": _get(system, "SystemType"),
        "cpu": _get(cpu_info, "Name") or platform.processor(),
        "cpu_architecture": platform.machine(),
        "ram_total_gb": _bytes_to_gb(_get(system, "TotalPhysicalMemory")),
        "storage_total_gb": _bytes_to_gb(_get(disk_info, "Size")),
        "storage_available_gb": _bytes_to_gb(_get(disk_info, "FreeSpace")),
        "gpu": _get(gpu_info, "Name"),
        "screen_resolution": _screen_resolution(screen),
        "hostname": socket.gethostname(),
        "ip_address": _local_ip(),
        "timezone": datetime.now().astimezone().tzname(),
        "system_time": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "internet_connected": online,
        "lmx_app_installed": lmx_executable is not None,
        "lmx_app_path": str(lmx_executable.parent) if lmx_executable else "",
        "lmx_app_executable": str(lmx_executable) if lmx_executable else "",
        "lmx_app_version": lmx_version,
        "lmx_app_launchable": lmx_executable is not None,
    }
    return enrich_report(report)


def enrich_report(report: dict[str, Any]) -> dict[str, Any]:
    evaluation = evaluate_windows_report(report)
    report = dict(report)
    report.update({
        "checks": evaluation["checks"],
        "final_status": evaluation["final_status"],
        "score": evaluation["score"],
        "score_label": evaluation["score_label"],
        "summary": evaluation["summary"],
        "recommendations": evaluation["recommendations"],
        "final_recommendation": evaluation["final_recommendation"],
        "failed_checks": evaluation["failed_checks"],
        "limitations": evaluation["limitations"],
        "device_report_summary": evaluation["device_report_summary"],
    })
    return report


def evaluate_windows_report(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "windows_os": _windows_os_check(report),
        "cpu": _windows_cpu_check(report),
        "ram": _windows_ram_check(report),
        "storage": _windows_storage_check(report),
        "gpu": _windows_gpu_check(report),
        "network": _network_check(report),
        "time_timezone": _time_check(report),
        "lmx_app_installed": _lmx_installed_check(report),
        "lmx_version": _windows_lmx_version_check(report),
        "lmx_app_launch": _lmx_launch_check(report),
        "pull_to_content": _pull_to_content_check(report),
    }
    statuses = [item["status"] for item in checks.values()]
    score = _certification_score(checks)
    if FAIL in statuses:
        final_status = "Not Recommended"
    elif WARNING in statuses:
        final_status = "Approved with Limitation"
    else:
        final_status = "Approved"
    failed = [item["message"] for item in checks.values() if item["status"] == FAIL]
    warnings = [item["message"] for item in checks.values() if item["status"] == WARNING]
    recommendations = _recommendations(checks)
    return {
        "final_status": final_status,
        "score": score,
        "score_label": _score_label(score),
        "summary": _summary(final_status),
        "recommendations": " ".join(recommendations),
        "final_recommendation": _final_recommendation(final_status),
        "checks": checks,
        "failed_checks": failed,
        "limitations": warnings,
        "device_report_summary": {
            "overall_summary": _summary(final_status),
            "good_points": [item["message"] for item in checks.values() if item["status"] == PASS],
            "warning_points": warnings,
            "failed_points": failed,
            "likely_causes": _likely_causes(checks),
            "recommended_actions": recommendations,
        },
    }


def _certification_score(checks: dict[str, dict[str, str]]) -> int:
    total = sum(WINDOWS_SCORE_WEIGHTS.values()) or 100
    score = 0.0
    for key, check in checks.items():
        weight = WINDOWS_SCORE_WEIGHTS.get(key, 0)
        if check["status"] == PASS:
            score += weight
        elif check["status"] == WARNING:
            score += weight * 0.5
    return int(round(score / total * 100))


def _score_label(score: int) -> str:
    if score >= 95:
        return "Excellent"
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Limited"
    return "Not Recommended"


def _final_recommendation(final_status: str) -> str:
    if final_status == "Approved":
        return "Certified for LMX Content"
    if final_status == "Approved with Limitation":
        return "Certified with Limitation"
    return "Not Recommended"


def _summary(final_status: str) -> str:
    if final_status == "Approved":
        return "This Windows device meets the current LMX Content certification requirements."
    if final_status == "Approved with Limitation":
        return "This Windows device can run LMX Content with limitations that should be reviewed before deployment."
    return "This Windows device is not recommended for LMX Content deployment until failed checks are resolved."


def _recommendations(checks: dict[str, dict[str, str]]) -> list[str]:
    actions = {
        "windows_os": "Use Windows 10 or Windows 11 non-server editions.",
        "cpu": "Use an Intel Core i5/i7 class CPU or AMD Ryzen class CPU where possible.",
        "ram": "Use at least 8GB RAM for best Windows LMX Content readiness.",
        "storage": "Free storage or use a device with at least 10GB available storage.",
        "gpu": "Install the correct graphics driver or use supported graphics hardware.",
        "network": "Confirm stable internet connectivity before deployment.",
        "time_timezone": "Correct the system date, time, and timezone settings.",
        "lmx_app_installed": "Install LMX Content on this Windows device.",
        "lmx_version": "Update Windows LMX Content to version 1.0.34 or newer.",
        "lmx_app_launch": "Repair, reinstall, or update LMX Content, then confirm it launches.",
        "pull_to_content": "Update Windows LMX Content to version 1.0.34 or newer.",
    }
    items = [
        actions[key]
        for key, check in checks.items()
        if check["status"] in {WARNING, FAIL} and key in actions
    ]
    return list(dict.fromkeys(items)) or ["No action required before deployment."]


def _likely_causes(checks: dict[str, dict[str, str]]) -> list[str]:
    causes = {
        "windows_os": "Windows edition or version may be unsupported.",
        "cpu": "CPU class may be below the recommended baseline.",
        "ram": "Low memory may affect stable playback.",
        "storage": "Limited free storage may affect future downloads and updates.",
        "gpu": "Graphics adapter may be missing, generic, or unsupported.",
        "network": "Internet connectivity may be unavailable.",
        "time_timezone": "Incorrect system time or timezone can affect scheduling and reporting.",
        "lmx_app_installed": "LMX Content may not be installed.",
        "lmx_version": "LMX Content version may be below the required baseline.",
        "lmx_app_launch": "LMX Content may be installed but not launchable.",
        "pull_to_content": "Installed LMX Content version may not support Pull To Content.",
    }
    items = [
        causes[key]
        for key, check in checks.items()
        if check["status"] in {WARNING, FAIL} and key in causes
    ]
    return list(dict.fromkeys(items)) or ["No likely causes identified from the current assessment."]


def _check(status: str, message: str) -> dict[str, str]:
    return {"status": status, "message": message}


def _version_parts(value: Any) -> list[int]:
    parts: list[int] = []
    for item in str(value or "").split("."):
        digits = "".join(char for char in item if char.isdigit())
        parts.append(int(digits or 0))
    return parts


def _version_at_least(value: Any, minimum: str) -> bool:
    current = _version_parts(value)
    required = _version_parts(minimum)
    length = max(len(current), len(required))
    current += [0] * (length - len(current))
    required += [0] * (length - len(required))
    return current >= required


def _windows_os_check(report: dict[str, Any]) -> dict[str, str]:
    edition = str(report.get("windows_edition") or report.get("os_version") or "").lower()
    version = str(report.get("windows_version") or "").lower()
    combined = f"{edition} {version}"
    if "server" in combined or "windows 7" in combined or "windows 8" in combined:
        return _check(FAIL, "Windows edition is not supported.")
    if "windows 10" in combined or "windows 11" in combined or version.startswith(("10", "11")):
        return _check(PASS, "Windows 10 or Windows 11 is supported.")
    return _check(FAIL, "Windows version could not be confirmed as Windows 10 or Windows 11.")


def _windows_cpu_check(report: dict[str, Any]) -> dict[str, str]:
    cpu = str(report.get("cpu") or "").lower()
    if any(item in cpu for item in ["core i5", "core(tm) i5", "core i7", "core(tm) i7", "core i9", "core(tm) i9", "ryzen"]):
        return _check(PASS, "CPU meets Windows LMX Content requirements.")
    if "pentium" in cpu or "celeron" in cpu:
        return _check(WARNING, "CPU is Intel Pentium or Celeron class.")
    return _check(FAIL, "CPU is unsupported or could not be identified.")


def _windows_ram_check(report: dict[str, Any]) -> dict[str, str]:
    ram = _float_value(report.get("ram_total_gb"))
    if ram < 4:
        return _check(FAIL, "RAM is below 4GB.")
    if ram < 8:
        return _check(WARNING, "RAM is between 4GB and 7.99GB.")
    return _check(PASS, "RAM is 8GB or above.")


def _windows_storage_check(report: dict[str, Any]) -> dict[str, str]:
    storage = _float_value(report.get("storage_available_gb"))
    if storage < 5:
        return _check(FAIL, "Available storage is below 5GB.")
    if storage < 10:
        return _check(WARNING, "Available storage is between 5GB and 9.99GB.")
    return _check(PASS, "Available storage is 10GB or above.")


def _windows_gpu_check(report: dict[str, Any]) -> dict[str, str]:
    gpu = str(report.get("gpu") or "").lower()
    if not gpu:
        return _check(FAIL, "GPU was not detected.")
    supported = ["nvidia", "geforce", "quadro", "rtx", "gtx", "radeon", "intel uhd", "intel iris", "amd vega"]
    if any(item in gpu for item in supported):
        return _check(PASS, "GPU is supported for Windows LMX Content.")
    if "generic" in gpu or "basic display" in gpu:
        return _check(WARNING, "Generic display adapter detected.")
    return _check(PASS, "GPU detected.")


def _network_check(report: dict[str, Any]) -> dict[str, str]:
    if report.get("internet_connected"):
        return _check(PASS, "Internet connectivity is available.")
    return _check(FAIL, "Device has no internet connectivity.")


def _time_check(report: dict[str, Any]) -> dict[str, str]:
    if not report.get("system_time"):
        return _check(FAIL, "System time is invalid or missing.")
    if not report.get("timezone"):
        return _check(WARNING, "Timezone could not be verified.")
    return _check(PASS, "System date, time, and timezone are present.")


def _lmx_installed_check(report: dict[str, Any]) -> dict[str, str]:
    if report.get("lmx_app_installed"):
        return _check(PASS, "LMX Content is installed.")
    return _check(FAIL, "LMX Content is not installed.")


def _windows_lmx_version_check(report: dict[str, Any]) -> dict[str, str]:
    version = report.get("lmx_app_version") or report.get("lmx_version")
    if not version:
        return _check(WARNING, "Version Unknown")
    if _version_at_least(version, "1.0.34"):
        return _check(PASS, f"Windows LMX Content version {version} is supported.")
    return _check(WARNING, f"Windows LMX Content version {version} is below 1.0.34.")


def _lmx_launch_check(report: dict[str, Any]) -> dict[str, str]:
    if report.get("lmx_app_launchable"):
        return _check(PASS, "LMX Content is launchable.")
    return _check(FAIL, "LMX Content launch failed.")


def _pull_to_content_check(report: dict[str, Any]) -> dict[str, str]:
    version = report.get("lmx_app_version") or report.get("lmx_version")
    if _version_at_least(version, "1.0.34"):
        return _check(PASS, "Windows LMX version supports Pull To Content.")
    return _check(FAIL, "Windows LMX version is below 1.0.34.")


def upload_report(url: str, report: dict[str, Any]) -> tuple[int, str]:
    payload = json.dumps(report).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def _powershell_json(command: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"{command} | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception:
        return {}
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def _get(data: dict[str, Any], key: str) -> Any:
    return data.get(key) if isinstance(data, dict) else None


def _bytes_to_gb(value: Any) -> float:
    try:
        return round(float(value) / (1024 ** 3), 2)
    except (TypeError, ValueError):
        return 0.0


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _screen_resolution(screen: dict[str, Any]) -> str:
    width = _get(screen, "Width")
    height = _get(screen, "Height")
    return f"{width}x{height}" if width and height else ""


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return ""


def _internet_available() -> bool:
    try:
        urllib.request.urlopen("https://www.google.com/generate_204", timeout=5)
        return True
    except Exception:
        return False


def _find_lmx_executable() -> Path | None:
    for folder in LMX_CANDIDATE_PATHS:
        for name in LMX_EXECUTABLE_NAMES:
            executable = folder / name
            if executable.exists():
                return executable
    return None


def _detect_lmx_version(executable: Path | None) -> str:
    if not executable:
        return ""
    escaped = str(executable).replace("'", "''")
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"(Get-Item -LiteralPath '{escaped}').VersionInfo.FileVersion",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return ""
    return result.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
