from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


def _version_parts(value: Any) -> list[int]:
    text = str(value or "").lower().replace("native", "").strip()
    parts: list[int] = []
    for item in text.split("."):
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
        _pull_to_content_check(report),
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
    final_recommendation = _final_recommendation(final_status, report)

    return {
        "final_status": final_status,
        "score": score,
        "summary": _summary(final_status, failed, limitations),
        "recommendations": recommendations,
        "final_recommendation": final_recommendation,
        "checks": {check.name: {"status": check.status, "message": check.message} for check in checks},
        "failed_checks": failed,
        "limitations": limitations,
    }


def _android_version_check(report: dict[str, Any]) -> CheckResult:
    version = _major_version(report.get("os_version"))
    if version < 9:
        return CheckResult("android_version", FAIL, "Android version is below 9.")
    if version <= 10:
        return CheckResult("android_version", WARNING, "Android 9 to 10 supports limited deployment.")
    return CheckResult("android_version", PASS, "Android 11 or above is supported.")


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
    if storage < 5:
        return CheckResult("storage", WARNING, "Available storage is between 2GB and 4.99GB.")
    return CheckResult("storage", PASS, "Available storage is 5GB or above.")


def _webview_check(report: dict[str, Any]) -> CheckResult:
    version = _major_version(report.get("webview_version"))
    if version < 100:
        return CheckResult("webview", FAIL, "Android System WebView is below version 100.")
    if version < 110:
        return CheckResult("webview", WARNING, "Android System WebView is between version 100 and 109.")
    return CheckResult("webview", PASS, "Android System WebView is version 110 or above.")


def _network_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("internet_connected"):
        return CheckResult("network", FAIL, "Device has no internet connectivity.")
    return CheckResult("network", PASS, "Internet connectivity is available.")


def _time_check(report: dict[str, Any]) -> CheckResult:
    if not report.get("system_time"):
        return CheckResult("time_timezone", FAIL, "Device time is invalid or missing.")
    try:
        datetime.fromisoformat(str(report.get("system_time")).replace("Z", "+00:00"))
    except ValueError:
        return CheckResult("time_timezone", FAIL, "Device time is invalid.")
    if not report.get("timezone"):
        return CheckResult("time_timezone", WARNING, "Timezone could not be verified.")
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
    if report.get("vast_playback_success") or report.get("programmatic_vast_playback_success"):
        return CheckResult("programmatic_vast", PASS, "Successful VAST playback validation was detected.")
    android = _major_version(report.get("os_version"))
    ram = _float_value(report, "ram_total_gb")
    webview = _major_version(report.get("webview_version"))
    online = bool(report.get("internet_connected"))
    if android < 11 or webview < 100:
        return CheckResult("programmatic_vast", FAIL, "Programmatic/VAST readiness requires Android 11+ and WebView 100+.")
    if android >= 11 and webview >= 110 and ram >= 3 and online:
        return CheckResult("programmatic_vast", PASS, "Programmatic/VAST readiness requirements are met.")
    if android >= 11 and 100 <= webview <= 109:
        return CheckResult("programmatic_vast", WARNING, "Programmatic/VAST readiness is limited with WebView 100 to 109.")
    return CheckResult("programmatic_vast", WARNING, "Programmatic/VAST readiness has unverified RAM, network, or WebView requirements.")


def _pull_to_content_check(report: dict[str, Any]) -> CheckResult:
    platform = str(report.get("platform") or "Android").lower()
    version = report.get("lmx_app_version") or report.get("lmx_version")
    if platform == "windows":
        if _version_at_least(version, "1.0.34"):
            return CheckResult("pull_to_content", PASS, "Windows LMX version supports Pull To Content.")
        return CheckResult("pull_to_content", FAIL, "Windows LMX version is below 1.0.34.")
    if _version_at_least(version, "2.9.1.2"):
        if report.get("pairing_verified") is True:
            return CheckResult("pull_to_content", PASS, "Android LMX version and pairing support Pull To Content.")
        return CheckResult("pull_to_content", WARNING, "Android LMX version supports Pull To Content, but pairing cannot be verified.")
    return CheckResult("pull_to_content", FAIL, "Android LMX version is below 2.9.1.2 native.")


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


def _final_recommendation(device_status: str, report: dict[str, Any]) -> str:
    overall_health = str(report.get("overall_health_status") or "UNKNOWN").upper()
    if overall_health == "UNKNOWN" and isinstance(report.get("overall_health"), dict):
        overall_health = str(report["overall_health"].get("status") or "UNKNOWN").upper()
    if overall_health == "UNKNOWN":
        return "Unable to Validate"
    if device_status == "Approved" and overall_health == "GREEN":
        return "Certified for LMX Content"
    if device_status == "Approved with Limitation" or overall_health == "YELLOW":
        return "Certified with Limitation"
    if device_status == "Not Recommended" or overall_health in {"ORANGE", "RED"}:
        return "Not Recommended"
    return "Unable to Validate"
