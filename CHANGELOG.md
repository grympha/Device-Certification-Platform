# Changelog

## 0.1.13

- Simplified the platform back to Device Compatibility and LMX Content Readiness.
- Removed Android storage permission, All Files Access, and SAF folder picker workflows.
- Removed media folder, playback audit, log validation, and overall playback health fields from active API/dashboard output.
- Updated Pull To Content readiness rules: Android requires LMX `2.9.1.2 native` or newer; Windows requires LMX `1.0.34` or newer.
- Updated dashboard, Android Agent, API docs, README, and sample report for the simplified certification workflow.

## 0.1.0

- Initial MVP scaffold.
- Added FastAPI backend with SQLite.
- Added sample Android diagnostic report.
- Added simple React dashboard.
- Added Android Kotlin agent skeleton.
- Added docs and roadmap.

## 0.1.1

- Validated backend API endpoints and report export flow.
- Fixed dashboard sample status/score mismatch.
- Fixed dashboard text encoding artifacts.
- Made Android agent package name and backend URL configurable through Gradle BuildConfig.
- Avoided newer Android time/WebView API crashes on older supported devices.

## 0.1.2

- Added dashboard `.env.example` for local backend configuration.
- Added `scripts/smoke_test_v1.py` for local backend/report/export validation.
- Added dashboard validation checklist.
- Added Android build and physical device test checklist.
- Added Android agent debug output for backend URL, LMX package name, diagnostic time, upload status, and upload errors.
- Enabled cleartext HTTP in the Android MVP agent for local LAN backend testing.
- Updated README with V1.1 validation steps.

## 0.1.3

- Fixed Android Agent upload flow to use 10 second connect/read timeouts.
- Added explicit upload success/failure UI messages with HTTP status or real exception details.
- Added Logcat upload success/error logging with tag `LMXCertification`.
- Added a `Show Backend URL` button to confirm the exact `BuildConfig.BACKEND_URL` used by the APK.

## 0.1.4

- Added `media_owner` support for devices and diagnostic uploads.
- Added `PATCH /api/devices/{device_id}` to edit Media Owner / Client metadata.
- Added startup-safe SQLite migration for the `devices.media_owner` column.
- Reworked dashboard layout with summary cards, full-width device table, separate detail/report/history sections, filters, and Edit Client controls.

## 0.1.5

- Standardized backend timestamp output as UTC ISO 8601 strings ending in `Z`.
- Added dashboard `formatMalaysiaTime(timestamp)` utility for `Asia/Kuala_Lumpur`.
- Displayed dashboard timestamps with `MYT` and `MYT (UTC+8)` labels while preserving UTC-based sorting.

## 0.1.6

- Added `DATABASE_URL` backend support for PostgreSQL while keeping local SQLite fallback.
- Added `psycopg2-binary` PostgreSQL driver.
- Guarded SQLite-only migration logic so it does not run against PostgreSQL.
- Added Neon PostgreSQL setup documentation for persistent Render history.

## 0.1.7

- Added Android LMX Playback Health diagnostics for app status, content download folder, audit playback file, and logs.
- Added overall LMX health status and troubleshooting recommendation to the Android JSON report.
- Added defensive Android file access handling so restricted folders report `UNKNOWN` instead of crashing.

## 0.1.8

- Added backend persistence for Android LMX Playback Health report fields.
- Added migration-safe health columns for `diagnostic_reports`.
- Added dashboard LMX Playback Health cards and latest health columns in Device List.
- Added sample LMX Playback Health report payload.

## 0.1.9

- Added Android All Files Access permission flow for LMX Playback Health checks.
- Added `storage_access_status` to Android diagnostic reports.
- Returned `UNKNOWN` for media, playback, and log checks when storage access is denied.
- Added a Storage Access card/status line to the Android LMX Playback Health output.

## 0.1.10

- Added a dashboard `Download APK` button for installing the Android Agent on test devices.
- Added the debug APK to dashboard static assets at `dashboard/public/downloads/app-debug.apk`.

## 0.1.11

- Updated Device Compatibility rules for Android version, RAM, storage, WebView, Programmatic/VAST, and Pull To Content readiness.
- Separated Device Certification Result, LMX Playback Health, and Final Recommendation in backend and dashboard output.
- Added `final_recommendation` to report responses.
- Updated dashboard behavior so denied storage access shows `LMX Playback Health Unavailable` instead of failed playback health cards.

## 0.1.12

- Added Android SAF folder picker fallback using `ACTION_OPEN_DOCUMENT_TREE`.
- Added persistent selected LMX folder support with `DocumentFile` reads for `QUAD42MEDIA`, `QUAD42AUDIT`, and `QUAD42LOG`.
- Added `storage_access_method`, `saf_access_status`, `selected_lmx_tree_uri`, and `selected_lmx_folder_valid` to Android reports.
- Added `Select LMX Folder` and `Clear Selected LMX Folder` Android Agent actions.
