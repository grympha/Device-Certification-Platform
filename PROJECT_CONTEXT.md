# Project Context

## Purpose

LMX Device Certification Platform helps teams test Android and Windows media player devices before production deployment. It collects device diagnostics, applies LMX Content compatibility rules, stores reports, and presents a client-ready certification result.

## Certification Results

Only three final statuses are used:

- Approved
- Approved with Limitation
- Not Recommended

## Android Compatibility Rules

- Android below 7: FAIL
- Android 7 to 10: WARNING / basic playback only
- Android 11 and above: PASS
- Android System WebView below 120: FAIL for VAST/programmatic
- RAM below 2GB: FAIL
- RAM 2GB to 4GB: WARNING
- RAM 4GB and above: PASS
- Available storage below 2GB: FAIL
- Available storage 2GB to 5GB: WARNING
- Available storage above 5GB: PASS
- No internet: FAIL
- Wrong date/time/timezone: WARNING
- LMX Content not installed: FAIL
- LMX Content installed but cannot launch: FAIL

## Architecture

1. Android Agent APK runs on Android media players and uploads JSON diagnostics.
2. Backend API receives reports, calculates status, and stores data in SQLite.
3. Web Dashboard lists tested devices and shows report details.
4. Report Generator exports JSON and HTML reports.
5. Windows Agent will be added after Android MVP.

## Future Roadmap

- Add Windows diagnostic agent.
- Add device groups and deployment locations.
- Add signed report exports.
- Add optional authentication.
- Add scheduled retesting.
- Add richer LMX Content app integration.

