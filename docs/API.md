# API Reference

## POST /api/reports

Receives one diagnostic report JSON payload from Android Agent or Windows Agent.

## GET /api/devices

Lists all tested devices with latest status and score.

## GET /api/devices/{id}

Shows full diagnostic history for one device.

## GET /api/reports/{id}

Shows one full diagnostic report.

## GET /api/export/{id}

Exports report.

Query parameters:

- `format=html`
- `format=json`

## Local Smoke Test

Start the backend at `http://127.0.0.1:8000`, then run:

```bash
python scripts/smoke_test_v1.py
```

The script uploads `reports/sample_android_report.json` and validates the core V1 API flow.

Optional custom API URL:

```powershell
$env:LMX_API_BASE_URL="http://127.0.0.1:8010"; python scripts/smoke_test_v1.py
```
