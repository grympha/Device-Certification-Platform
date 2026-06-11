from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


PASS = "PASS"
WARNING = "WARNING"
FAIL = "FAIL"

SCORE_WEIGHTS = {
    "android_version": 15,
    "ram": 15,
    "storage": 10,
    "webview": 15,
    "network": 10,
    "time_timezone": 5,
    "lmx_app_installed": 10,
    "lmx_app_launch": 10,
    "programmatic_vast": 5,
    "pull_to_content": 5,
}


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
        _lmx_version_check(report),
        _programmatic_check(report),
        _pull_to_content_check(report),
    ]

    fail_count = sum(1 for check in checks if check.status == FAIL)
    warning_count = sum(1 for check in checks if check.status == WARNING)
    score = _certification_score(checks)

    if fail_count:
        final_status = "Not Recommended"
    elif warning_count:
        final_status = "Approved with Limitation"
    else:
        final_status = "Approved"

    failed = [check.message for check in checks if check.status == FAIL]
    limitations = [check.message for check in checks if check.status == WARNING]
    recommendations = _recommendations(failed, limitations)
    final_recommendation = _final_recommendation(final_status)
    checks_dict = {check.name: {"status": check.status, "message": check.message} for check in checks}
    device_report_summary = build_device_report_summary(final_status, checks_dict, recommendations)

    return {
        "final_status": final_status,
        "score": score,
        "score_label": _score_label(score),
        "summary": _summary(final_status, failed, limitations),
        "recommendations": recommendations,
        "final_recommendation": final_recommendation,
        "checks": checks_dict,
        "failed_checks": failed,
        "limitations": limitations,
        "device_report_summary": device_report_summary,
    }


def _certification_score(checks: list[CheckResult]) -> int:
    score = 0.0
    for check in checks:
        weight = SCORE_WEIGHTS.get(check.name, 0)
        if check.status == PASS:
            score += weight
        elif check.status == WARNING:
            score += weight * 0.5
    return int(round(score))


def _score_label(score: int) -> str:
    if score >= 95:
        return "Excellent"
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Limited"
    return "Not Recommended"


def build_device_report_summary(
    final_status: str,
    checks: dict[str, Any],
    recommendations: str | None = None,
) -> dict[str, Any]:
    good_points = _messages_for_status(checks, PASS)
    warning_points = _messages_for_status(checks, WARNING)
    failed_points = _messages_for_status(checks, FAIL)
    likely_causes = _likely_causes(checks)
    recommended_actions = _recommended_actions(checks, recommendations)

    return {
        "overall_summary": _summary(final_status, failed_points, warning_points),
        "good_points": good_points,
        "warning_points": warning_points,
        "failed_points": failed_points,
        "likely_causes": likely_causes,
        "recommended_actions": recommended_actions,
    }


def _messages_for_status(checks: dict[str, Any], status: str) -> list[str]:
    messages: list[str] = []
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") == status:
            message = str(check.get("message") or "").strip()
            if message:
                messages.append(message)
    return messages


def _likely_causes(checks: dict[str, Any]) -> list[str]:
    causes: list[str] = []
    cause_map = {
        "android_version": "Android OS version may be below the supported baseline for stable LMX Content deployment.",
        "ram": "Low device memory may limit smooth HTML, URL, or VAST rendering.",
        "storage": "Low available storage can prevent updates, cached content, or normal app operation.",
        "webview": "Older Android System WebView versions may have limited compatibility with HTML, URL, or VAST playback.",
        "network": "Network connectivity may be unavailable or unstable during validation.",
        "time_timezone": "Incorrect device time or timezone can affect scheduled content and reporting.",
        "lmx_app_installed": "LMX Content may not be installed on the device.",
        "lmx_app_launch": "LMX Content may be installed but not launchable from Android.",
        "lmx_version": "The LMX Content version could not be detected.",
        "programmatic_vast": "Programmatic/VAST readiness may be limited by Android version, WebView, RAM, or network state.",
        "pull_to_content": "The installed LMX Content version may be below the Pull To Content requirement.",
    }
    for key, check in checks.items():
        if isinstance(check, dict) and check.get("status") in {WARNING, FAIL}:
            cause = cause_map.get(key)
            if cause and cause not in causes:
                causes.append(cause)
    return causes or ["No likely causes identified from the current assessment."]


def _recommended_actions(checks: dict[str, Any], recommendations: str | None) -> list[str]:
    actions: list[str] = []
    action_map = {
        "android_version": "Upgrade the device OS or select a device running Android 11 or above where possible.",
        "ram": "Use a device with at least 4GB RAM for best LMX Content readiness.",
        "storage": "Free device storage or use a device with at least 5GB available storage.",
        "webview": "Update Android System WebView where possible.",
        "network": "Confirm the device has stable internet connectivity before deployment.",
        "time_timezone": "Correct the device date, time, and timezone settings.",
        "lmx_app_installed": "Install LMX Content package com.qruize.quad42.media.app.",
        "lmx_app_launch": "Reinstall or update LMX Content, then confirm the app can launch.",
        "lmx_version": "Install a supported LMX Content build and rerun certification.",
        "programmatic_vast": "Update WebView and verify Android version, RAM, and internet connectivity.",
        "pull_to_content": "Update LMX Content to Android version 2.9.1.2 native or newer, or Windows version 1.0.34 or newer.",
    }
    for key, check in checks.items():
        if isinstance(check, dict) and check.get("status") in {WARNING, FAIL}:
            action = action_map.get(key)
            if action and action not in actions:
                actions.append(action)
    if not actions and recommendations:
        actions.append(recommendations)
    return actions or ["No action required before deployment."]


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


def _lmx_version_check(report: dict[str, Any]) -> CheckResult:
    version = report.get("lmx_app_version") or report.get("lmx_version")
    if not version:
        return CheckResult("lmx_version", FAIL, "LMX Content version could not be detected.")
    return CheckResult("lmx_version", PASS, f"LMX Content version detected: {version}.")


def _programmatic_check(report: dict[str, Any]) -> CheckResult:
    if report.get("vast_playback_success") or report.get("programmatic_vast_playback_success"):
        return CheckResult("programmatic_vast", PASS, "Successful VAST readiness signal was detected.")
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
        return CheckResult("pull_to_content", PASS, "Android LMX version supports Pull To Content.")
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


def _final_recommendation(device_status: str) -> str:
    if device_status == "Approved":
        return "Certified for LMX Content"
    if device_status == "Approved with Limitation":
        return "Certified with Limitation"
    if device_status == "Not Recommended":
        return "Not Recommended"
    return "Not Recommended"
