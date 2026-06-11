# API Reference

## POST /api/reports

Receives one diagnostic report JSON payload from the Android Agent or future Windows Agent.

Required and commonly used fields:

```json
{
  "device_name": "Solum Box",
  "platform": "Android",
  "manufacturer": "Solum",
  "model": "Box",
  "os_version": "15",
  "ram_total_gb": 4,
  "storage_available_gb": 8,
  "webview_version": "120.0.0.0",
  "internet_connected": true,
  "system_time": "2026-06-10T00:02:20Z",
  "timezone": "Asia/Kuala_Lumpur",
  "lmx_app_package": "com.qruize.quad42.media.app",
  "lmx_app_installed": true,
  "lmx_app_launchable": true,
  "lmx_app_version": "2.9.3.6 native"
}
```

The backend evaluates:

- Device Compatibility: Android Version, RAM, Storage, WebView, Network, Time/Timezone.
- LMX Content Readiness: LMX App Installed, LMX App Launch, LMX Version, Programmatic/VAST Readiness, Pull To Content Readiness.

## Certification Outcomes

Device Certification Result values:

- `Approved`
- `Approved with Limitation`
- `Not Recommended`

Final Recommendation values:

- `Certified for LMX Content`
- `Certified with Limitation`
- `Not Recommended`

Pull To Content Readiness:

- Android: `PASS` when LMX Version is `2.9.1.2 native` or newer, otherwise `FAIL`.
- Windows: `PASS` when LMX Version is `1.0.34` or newer, otherwise `FAIL`.

The platform does not check device pairing, inventory mapping, playback, CMS connectivity, or another app's local media/log folders.

## GET /api/devices

Lists all tested devices with latest certification status, score, and last check time.

## GET /api/devices/{id}

Shows one device plus its diagnostic report history.

## PATCH /api/devices/{id}

Updates editable device metadata.

Request body:

```json
{
  "media_owner": "Client Name"
}
```

Diagnostic uploads may also include either `media_owner` or `client_name`. If both are present, `media_owner` is used. If neither is present, the dashboard shows `Unassigned`.

## GET /api/reports/{id}

Shows one full diagnostic report with checks, failed checks, limitations, score, status, and final recommendation.

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

The script uploads `reports/sample_android_report.json` and validates the core API flow.
