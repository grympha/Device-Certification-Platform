# Windows Device Certification

Phase 2 extends the LMX Device Certification Platform to support Windows 10 and Windows 11 devices.

## Goal

Answer:

```text
Can this Windows device run LMX Content reliably and is it ready for deployment?
```

## Windows Agent

Run from a Windows test machine:

```powershell
cd windows-agent
python windows_certification_agent.py
```

Upload to local backend:

```powershell
python windows_certification_agent.py --upload --backend-url http://127.0.0.1:8000/api/reports
```

Upload to Render:

```powershell
python windows_certification_agent.py --upload --backend-url https://device-certification-platform.onrender.com/api/reports
```

## Scored Checks

| Check | Weight |
| --- | ---: |
| Operating System | 15 |
| CPU | 10 |
| RAM | 15 |
| Available Storage | 10 |
| GPU | 10 |
| Network Connectivity | 10 |
| Time / Timezone | 5 |
| LMX Installed | 10 |
| LMX Version | 10 |
| LMX Launch | 10 |
| Pull To Content | 5 |

Total score: `100`

## Certification Result

- `Approved`: no FAIL and no WARNING.
- `Approved with Limitation`: no FAIL and at least one WARNING.
- `Not Recommended`: any FAIL.

## LMX Version Rule

Windows Pull To Content readiness:

- `PASS`: LMX Content version `1.0.34` or newer.
- `FAIL`: LMX Content version below `1.0.34`.

## Deployment Readiness

Deployment Readiness is displayed separately and does not affect the score yet.

Checks:

- Auto Login
- Auto Startup
- Power Settings
- Display Scaling
- Wake Timers
- Windows Update Status

Some fields may return `WARNING` when Windows cannot verify the setting safely without administrator access.

## Sample Payload

Use:

```text
reports/sample_windows_report.json
```

Post it to:

```text
POST /api/reports
```

The dashboard will show a `WINDOWS` platform badge, Windows-specific device information, Windows checks, deployment readiness, and PDF/DOCX exports.
