# LMX Device Certification Platform

Free/open-source MVP for checking whether Android and Windows devices are healthy and compatible for running LMX Content.

## Stack

- Android Agent: Kotlin
- Windows Agent: PowerShell
- Backend API: Python FastAPI
- Database: SQLite locally, PostgreSQL in production
- Dashboard: React with Vite
- Reports: JSON and HTML export

## Environment Variables

| Variable | Required | Used By | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | Optional locally, required on Render for persistent history | Backend | PostgreSQL connection string. If missing, backend uses local SQLite. |
| `VITE_API_BASE_URL` | Required for deployed dashboard | Dashboard | Backend API base URL, for example `https://device-certification-platform.onrender.com`. |

## Run Backend Locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend runs at `http://127.0.0.1:8000`.

API docs are available at `http://127.0.0.1:8000/docs`.

Local backend uses SQLite by default:

```text
backend/lmx_certification.db
```

To test PostgreSQL locally, set `DATABASE_URL` before starting the backend.

Health check:

```text
http://127.0.0.1:8000/health
```

## Load Sample Report

```bash
cd backend
python scripts/load_sample.py
```

Or post manually:

```bash
curl -X POST http://127.0.0.1:8000/api/reports ^
  -H "Content-Type: application/json" ^
  --data-binary "@../reports/sample_android_report.json"
```

## Run Dashboard Locally

Copy the dashboard environment example first:

```bash
cd dashboard
copy .env.example .env
```

The default dashboard API URL is:

```text
VITE_API_BASE_URL=http://localhost:8000
```

```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs at `http://127.0.0.1:5173`.

Set a custom API URL with:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"; npm run dev
```

On macOS/Linux:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## Build Android APK

Open `android-agent` in Android Studio, then build the debug APK:

```bash
cd android-agent
gradle assembleDebug
```

This repo includes a Gradle wrapper. You can also use Android Studio's built-in Gradle tooling.

Before installing on a device, update the backend URL in `android-agent/app/build.gradle` if the backend is not reachable at the default local network address.

The Android agent reads these values from Gradle `BuildConfig` fields:

- `LMX_PACKAGE_NAME`
- `BACKEND_URL`

They are configured in:

```text
android-agent/app/build.gradle
```

Example:

```gradle
buildConfigField "String", "LMX_PACKAGE_NAME", "\"com.qruize.quad42.media.app\""
buildConfigField "String", "BACKEND_URL", "\"https://device-certification-platform.onrender.com/api/reports\""
```

For local LAN testing only, use your PC LAN IP:

```gradle
buildConfigField "String", "BACKEND_URL", "\"http://YOUR_PC_LAN_IP:8000/api/reports\""
```

## Run V1 Smoke Test

Start the backend first, then run:

```bash
python scripts/smoke_test_v1.py
```

The smoke test checks backend health, uploads the sample Android report, fetches devices, fetches the uploaded report, and verifies JSON/HTML export.

If you run the backend on another port:

```powershell
$env:LMX_API_BASE_URL="http://127.0.0.1:8010"; python scripts/smoke_test_v1.py
```

## Validation Guides

- Dashboard checklist: `docs/DASHBOARD_VALIDATION.md`
- Android build and device checklist: `docs/ANDROID_BUILD_AND_DEVICE_TEST.md`
- Render deployment guide: `docs/RENDER_DEPLOYMENT.md`
- Deployment checklist: `docs/DEPLOYMENT_CHECKLIST.md`
- Neon PostgreSQL setup: `docs/NEON_POSTGRES_SETUP.md`

## Media Owner / Client

Devices support optional `media_owner` metadata. Android uploads may include either:

```json
{
  "media_owner": "Client Name"
}
```

or:

```json
{
  "client_name": "Client Name"
}
```

If both are present, `media_owner` is used. If neither is present, the dashboard shows `Unassigned`.

You can edit the selected device in the dashboard with `Edit Client`, or call:

```http
PATCH /api/devices/{device_id}
Content-Type: application/json

{
  "media_owner": "Client Name"
}
```

The dashboard also supports search by device name plus filters for status and Media Owner / Client.

## Timezone Handling

The backend stores and returns timestamps in UTC ISO 8601 format, for example:

```text
2026-06-10T00:02:20Z
```

The dashboard displays all timestamps in Malaysia time:

```text
10/06/2026, 08:02:20 AM MYT
```

Dashboard sorting still uses the original UTC timestamps from the API. Display formatting uses `Asia/Kuala_Lumpur` / `MYT (UTC+8)`.

## Deploy on Render Free Tier

The repo includes `render.yaml` for a Render Blueprint with:

- Backend web service: `device-certification-api`
- Dashboard static site: `device-certification-dashboard`

Backend settings:

```text
Type: Web Service
Runtime: Python
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Plan: Free
```

Backend environment variable for persistent history:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Use Neon PostgreSQL free tier for persistent history. If `DATABASE_URL` is not set, the backend falls back to SQLite, and history can disappear after Render redeploys/restarts.

Dashboard settings:

```text
Type: Static Site
Root Directory: dashboard
Build Command: npm install && npm run build
Publish Directory: dist
Environment Variable: VITE_API_BASE_URL=https://device-certification-platform.onrender.com
Plan: Free
```

After backend deployment, update Android `BACKEND_URL` to:

```gradle
buildConfigField "String", "BACKEND_URL", "\"https://device-certification-platform.onrender.com/api/reports\""
```

Then rebuild and reinstall the Android APK.

## Android LMX Playback Health

The Android agent also validates LMX Content local health.

LMX package:

```text
com.qruize.quad42.media.app
```

Known local paths:

```text
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42MEDIA/
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42LOG/
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42AUDIT/appender.csv
```

The APK report includes:

- `lmx_app_status`
- `content_download_status`
- `playback_validation`
- `log_validation`
- `overall_health_status`
- `troubleshooting_recommendation`

If Android storage restrictions prevent reading another app's folder, the agent returns `UNKNOWN` for that module instead of crashing.

The backend stores these LMX Playback Health sections for report history and exposes them through report detail APIs and the dashboard. A test payload is available at:

```text
reports/sample_lmx_playback_health_report.json
```

The dashboard shows LMX Playback Health cards for:

- LMX App Status
- Content Download Status
- Playback Validation
- Log Validation
- Overall Health Status

Device List also includes latest health columns for Overall Health, Content Download, Playback, and Logs.

## Upload Troubleshooting

- If Android upload fails, tap `Show Backend URL` in the APK and confirm it matches the backend URL plus `/api/reports`.
- If backend `/docs` opens but Android upload fails, verify the APK was rebuilt after changing `BACKEND_URL`.
- If dashboard does not load devices, confirm `VITE_API_BASE_URL` points to the backend Render URL, not the dashboard URL.
- If browser console shows CORS errors, add the final dashboard URL explicitly in `backend/app/main.py`.
- Render free services may sleep after inactivity; the first request can be slow.

## MVP Notes

- No paid APIs or paid infrastructure are required.
- SQLite is used locally by default.
- Neon PostgreSQL free tier is recommended on Render for persistent history.
- Authentication is intentionally omitted for the MVP.
- Dashboard can show bundled sample data if the backend is not running.
- Android devices cannot reach a laptop backend through `127.0.0.1`; use the laptop LAN IP or deployed API URL in `BACKEND_URL`.
- The V1 Android agent allows cleartext HTTP for local LAN testing. Use HTTPS for production.
- The Windows Agent is intentionally a Phase 2 placeholder.
- Physical Android testing is required before treating APK diagnostics as production-ready.

## Render Free Tier

The included `render.yaml` deploys the backend and dashboard on Render free tier. SQLite is suitable for local development, but Render free service storage is ephemeral. Use `DATABASE_URL` with Neon PostgreSQL to keep device history after redeploys/restarts.
