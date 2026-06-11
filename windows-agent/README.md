# Windows Certification Agent

Phase 2 adds a Python-based Windows certification agent for Windows 10 and Windows 11 devices.

## Run Locally

```powershell
cd windows-agent
python windows_certification_agent.py
```

This creates:

```text
report.json
```

## Upload To Backend

Local backend:

```powershell
python windows_certification_agent.py --upload --backend-url http://127.0.0.1:8000/api/reports
```

Render backend:

```powershell
python windows_certification_agent.py --upload --backend-url https://device-certification-platform.onrender.com/api/reports
```

## Collected Fields

- Computer name
- Manufacturer and model
- Windows edition, version, and build number
- System type
- CPU and CPU architecture
- RAM
- Total and available storage
- GPU
- Screen resolution
- Hostname and IP address
- Timezone and report date
- Internet connectivity
- LMX Content installed status
- LMX Content version
- LMX launch readiness

## Deployment Readiness

The agent also reports non-scoring deployment readiness fields:

- Auto Login
- Auto Startup
- Power Settings
- Display Scaling
- Wake Timers
- Windows Update Status

Some readiness fields may return `WARNING` when Windows cannot verify them safely without administrator access.
