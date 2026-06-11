# API Reference

## POST /api/reports

Receives one diagnostic report JSON payload from Android Agent or Windows Agent.

LMX Playback Health fields are optional and backwards compatible. New Android Agent reports may include:

```json
{
  "lmx_app_status": {},
  "content_download_status": {},
  "playback_validation": {},
  "log_validation": {},
  "overall_health_status": "YELLOW",
  "overall_health": {
    "status": "YELLOW",
    "recommendation": "Playback active but crash logs found"
  },
  "storage_access_status": "GRANTED",
  "final_recommendation": "Certified with Limitation",
  "troubleshooting_recommendation": "Review crash logs.",
  "device_compatibility": {}
}
```

Missing health fields are returned as `null` or `UNKNOWN`. If storage access is denied by Android, file-based health sections should not be treated as certification failures. The dashboard displays `LMX Playback Health Unavailable`, Overall Health `UNKNOWN`, and Final Recommendation `Unable to Validate`.

## Certification Outcomes

The API separates:

- `final_status`: Device Certification Result.
- `overall_health_status`: LMX Playback Health result.
- `final_recommendation`: deployment recommendation.

Device Certification Result values:

- `Approved`
- `Approved with Limitation`
- `Not Recommended`

Final Recommendation values:

- `Certified for LMX Content`
- `Certified with Limitation`
- `Not Recommended`
- `Unable to Validate`

## GET /api/devices

Lists all tested devices with latest status and score.

Device list responses include the latest health status summary when available:

- `latest_overall_health_status`
- `latest_content_download_status`
- `latest_playback_status`
- `latest_log_status`

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

Report detail responses include persisted health sections:

- `lmx_app_status`
- `content_download_status`
- `playback_validation`
- `log_validation`
- `overall_health_status`
- `overall_health`
- `troubleshooting_recommendation`
- `device_compatibility`
- `final_recommendation`

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

LMX Playback Health sample payload:

```text
reports/sample_lmx_playback_health_report.json
```

Optional custom API URL:

```powershell
$env:LMX_API_BASE_URL="http://127.0.0.1:8010"; python scripts/smoke_test_v1.py
```
