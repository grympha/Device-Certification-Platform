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

Or use the lightweight desktop app:

```text
windows-agent\dist\LMX-Windows-Certification.exe
```

User flow:

1. Open the EXE.
2. Click `Run Certification`.
3. Click `Upload Report`.
4. Review the full report in the web dashboard.

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

The Windows app checks for LMX Content in:

```text
C:\Program Files\mac-media-player\MW Content.exe
C:\Program Files\mac-media-player\mac-media-player.exe
```

If either executable exists, LMX Installed is `PASS`. If the executable version cannot be read from Windows file version information, LMX Version is `WARNING` with `Version Unknown`.

Windows Pull To Content readiness:

- `PASS`: LMX Content version `1.0.34` or newer.
- `FAIL`: LMX Content version below `1.0.34`.

## Sample Payload

Use:

```text
reports/sample_windows_report.json
```

Post it to:

```text
POST /api/reports
```

The dashboard will show a `WINDOWS` platform badge, Windows-specific device information, Windows checks, and PDF/DOCX exports.
