import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("LMX_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT = ROOT / "reports" / "sample_android_report.json"


def request(method, path, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.status, json.loads(body)
        return response.status, body


def run_step(label, fn):
    try:
        result = fn()
        print(f"PASS {label}")
        return result
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        print(f"FAIL {label}: {error}")
        return None


def main():
    uploaded = {}

    run_step("backend health", lambda: request("GET", "/health"))
    run_step("api docs reachable", lambda: request("GET", "/docs"))

    sample_payload = json.loads(SAMPLE_REPORT.read_text(encoding="utf-8"))

    def upload_report():
        status, body = request("POST", "/api/reports", sample_payload)
        uploaded.update(body)
        if status != 200 or "report_id" not in body:
            raise ValueError(f"unexpected response: {body}")
        return body

    run_step("upload sample Android report", upload_report)
    run_step("fetch device list", lambda: request("GET", "/api/devices"))

    report_id = uploaded.get("report_id")
    if not report_id:
        print("FAIL fetch uploaded report: no report_id from upload step")
        print("FAIL export JSON report: no report_id from upload step")
        print("FAIL export HTML report: no report_id from upload step")
        return 1

    run_step("fetch uploaded report", lambda: request("GET", f"/api/reports/{report_id}"))
    run_step("export JSON report", lambda: request("GET", f"/api/export/{report_id}?format=json"))
    run_step("export HTML report", lambda: request("GET", f"/api/export/{report_id}?format=html"))

    print("V1 smoke test completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
