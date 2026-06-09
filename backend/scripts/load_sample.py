import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "reports" / "sample_android_report.json"


def main() -> None:
    report = json.loads(SAMPLE.read_text())
    response = httpx.post("http://127.0.0.1:8000/api/reports", json=report, timeout=10)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()

