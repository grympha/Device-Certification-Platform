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


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000/api/reports"
LMX_CANDIDATE_PATHS = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "LMX Content",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "LMX Content",
    Path(r"C:\LMX Content"),
]


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

    lmx_path = _find_lmx_path()
    lmx_version = _detect_lmx_version(lmx_path)
    online = _internet_available()

    return {
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
        "lmx_app_installed": lmx_path is not None,
        "lmx_app_path": str(lmx_path) if lmx_path else "",
        "lmx_app_version": lmx_version,
        "lmx_app_launchable": lmx_path is not None,
        "deployment_readiness": collect_deployment_readiness(),
    }


def collect_deployment_readiness() -> dict[str, str]:
    return {
        "auto_login": "WARNING",
        "auto_startup": _startup_status(),
        "power_settings": _sleep_status(),
        "display_scaling": _display_scaling(),
        "wake_timers": "WARNING",
        "windows_update_status": "WARNING",
    }


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


def _find_lmx_path() -> Path | None:
    for path in LMX_CANDIDATE_PATHS:
        if path.exists():
            return path
    return None


def _detect_lmx_version(path: Path | None) -> str:
    if not path:
        return ""
    version_files = list(path.glob("**/version*.*"))
    for version_file in version_files[:3]:
        try:
            text = version_file.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if text:
            return text.splitlines()[0][:80]
    exe_files = list(path.glob("*.exe"))
    return exe_files[0].stem if exe_files else ""


def _startup_status() -> str:
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if startup.exists() and any("lmx" in item.name.lower() for item in startup.iterdir()):
        return "PASS"
    return "WARNING"


def _sleep_status() -> str:
    try:
        result = subprocess.run(["powercfg", "/a"], capture_output=True, text=True, timeout=10, check=False)
    except Exception:
        return "WARNING"
    text = result.stdout.lower()
    if "standby" in text and "not available" not in text:
        return "FAIL"
    return "PASS"


def _display_scaling() -> str:
    value = _powershell_json(
        "Get-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop\\WindowMetrics' | "
        "Select-Object AppliedDPI"
    ).get("AppliedDPI")
    try:
        dpi = int(value)
    except (TypeError, ValueError):
        return ""
    return f"{round(dpi / 96 * 100)}%"


if __name__ == "__main__":
    sys.exit(main())
