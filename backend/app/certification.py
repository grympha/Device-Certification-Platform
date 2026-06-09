from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PASS = "PASS"
WARNING = "WARNING"
FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: str
    message: str


def _float_value(report: dict[str, Any], key: str, default: float = 0) -> float:
    try:
        return float(report.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _major_version(value: Any) -> int:
    text = str(value or "0")
    digits = ""
    for char in text:
        if char.isdigit():
            digits += char
        elif digits:
            break
    return int(digits or 0)


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _android_version_check(report),
        _ram_check(report),
        _storage_check(report),
        _webview_check(report),
        _network_check(report),
        _time_check(report),
        _lmx_installed_check(report),
        _lmx_launch_check(report),
        _programmatic_check(report),
    ]

    fail_count = sum(1 for check in checks if check.status == FAIL)
    warning_count = sum(1 for check in checks if check.status == WARNING)
    score = max(0, 100 - fail_count * 25 - warning_count * 10)

    if fail_count:
        final_status = "Not Recommended"
    elif warning_count:
        final_status = "Approved with Limitation"
    else:
        final_status = "Approved"

    failed = [check.message for check in checks if check.status == FAIL]
    limitations = [check.message for check in checks if check.status == WARNING]
    recommendations = _recommendations(failed, limitations)

    return {
        "final_status": final_status,
        "score": score,
        "summary": _summary(final_status, failed, limitations),
        "recommendations": recommendations,
        "checks": {check.name: {"status": check.status, "message": check.message} for check in checks},
        "failed_checks": failed,
        "limitations": limitations,
    }


def _android_version_check(report: dict[str, Any]) -> CheckResult:
    version = _major_version(report.get("os_version"))
    if version < 7:
        return CheckResult("android_version", FAIL, "Android version is below 7.")
    if version <= 10:
        return CheckResult("android_version", WARNING, "Android 7 to 10 supports basic playback only.")
    return CheckResult("android_version", PASS, "Android version is supported.")


def _ram_check(report: dict[str, Any]) -> CheckResult:
    ram = _float_value(report, "ram_total_gb")
    if ram < 2:
        return CheckResult("ram", FAIL, "RAM is below 2GB.")
    if ram < 4:
        return CheckResult("ram", WARNING, "RAM is between 2GB and 4GB.")
    return CheckResult("ram", PASS, "RAM is sufficient.")


def _storage_check(report: dict[str, Any]) -> CheckResult:
    storage = _float_value(report, "storage_available_gb")
    if storage < 2:
        return CheckResult("storage", FAIL, "Available storage is below 2GB.")
    if storage <= 5:
        return CheckResult("storage", WARNING, "Available storage is between 2GB and 5GB.")
    return CheckResult("storage", PASS, "Available storage is sufficient.")


def _webview_check(report: dict[str, Any]) -> CheckResult:
    version = _major_version(report.get("webview_version"))
    if version < 120:
        return CheckResult("webview", FAIL, "Android System WebView is below version 120.")
    return CheckResult("webview", PASS, "Android System WebView is ready.")


def _network_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("internet_connected"):
        return CheckResult("network", FAIL, "Device has no internet connectivity.")
    return CheckResult("network", PASS, "Internet connectivity is available.")


def _time_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("system_time") or not report.get("timezone"):
        return CheckResult("time_timezone", WARNING, "System date, time, or timezone could not be verified.")
    return CheckResult("time_timezone", PASS, "System date, time, and timezone are present.")


def _lmx_installed_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("lmx_app_installed"):
        return CheckResult("lmx_app_installed", FAIL, "LMX Content app is not installed.")
    return CheckResult("lmx_app_installed", PASS, "LMX Content app is installed.")


def _lmx_launch_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("lmx_app_launchable"):
        return CheckResult("lmx_app_launch", FAIL, "LMX Content app cannot be launched.")
    return CheckResult("lmx_app_launch", PASS, "LMX Content app is launchable.")


def _programmatic_check(report: dict[str, Any]) -> CheckResult:
    webview = _major_version(report.get("webview_version"))
    if webview < 120:
        return CheckResult("programmatic_vast", FAIL, "Programmatic/VAST playback is not ready because WebView is below 120.")
    return CheckResult("programmatic_vast", PASS, "Programmatic/VAST playback is ready.")


def _summary(final_status: str, failed: list[str], limitations: list[str]) -> str:
    if final_status == "Approved":
        return "Device meets the current LMX Content compatibility requirements."
    if final_status == "Approved with Limitation":
        return "Device can run LMX Content with limitations."
    return "Device is not recommended for LMX Content deployment until failed checks are resolved."


def _recommendations(failed: list[str], limitations: list[str]) -> str:
    items = failed + limitations
    if not items:
        return "No action required before deployment."
    return " ".join(items) + " Resolve failed checks and review limitations before production deployment."

