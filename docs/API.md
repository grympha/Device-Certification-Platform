# API Reference

## POST /api/reports

Receives one diagnostic report JSON payload from Android Agent or Windows Agent.

## GET /api/devices

Lists all tested devices with latest status and score.

## GET /api/devices/{id}

Shows full diagnostic history for one device.

## PATCH /api/devices/{id}

Updates editable device metadata.

Request body:

```json
{
  "media_owner": "Client Name"
}
```

Response:

```json
{
  "id": 1,
  "device_name": "Solum Box",
  "platform": "Android",
  "manufacturer": "Solum",
  "model": "Box",
  "media_owner": "Client Name",
  "os_version": "15",
  "webview_version": "120.0.0.0",
  "lmx_app_version": "1.0.0",
  "latest_status": "Approved",
  "latest_score": 100,
  "last_seen": "2026-06-10T00:00:00"
}
```

Diagnostic uploads may also include either `media_owner` or `client_name`. If both are present, `media_owner` is used. If neither is present, the dashboard shows `Unassigned`.

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
