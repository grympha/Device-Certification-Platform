# LMX Windows Certification

Standalone lightweight Windows certification utility for Windows 10 and Windows 11 devices.

End-user flow:

1. Download `LMX-Windows-Certification.exe`.
2. Open the app.
3. Click `Run Certification`.
4. Review the small result summary.
5. Click `Upload Report`.
6. Refresh the web dashboard.

The Windows app does not generate PDF or DOCX files. PDF and DOCX exports remain available from the web dashboard.

## Run From Source

```powershell
cd windows-agent
python -m pip install -r requirements.txt
python windows_certification_ui.py
```

## Build EXE

```powershell
cd windows-agent
build_windows_exe.bat
```

Output:

```text
dist\LMX-Windows-Certification.exe
```

## Use The EXE

Double click:

```text
LMX-Windows-Certification.exe
```

Then:

1. Click `Run Certification`.
2. Confirm the small summary.
3. Click `Upload Report`.
4. Review full details in the web dashboard.

Default backend URL:

```text
https://device-certification-platform.onrender.com/api/reports
```

Dashboard URL shown after successful upload:

```text
https://device-certification-dashboard.onrender.com/
```

To override the backend URL before launching from source:

```powershell
$env:LMX_BACKEND_URL="http://127.0.0.1:8000/api/reports"
python windows_certification_ui.py
```

## LMX Content Detection

The app checks:

```text
C:\Program Files\mac-media-player\MW Content.exe
C:\Program Files\mac-media-player\mac-media-player.exe
```

If either executable exists, LMX Content detection passes. The app reads Windows file version information from the detected executable. If the version cannot be read, the report marks LMX Version as `WARNING` with `Version Unknown`.

## Local Report File

After `Run Certification`, the app saves:

```text
windows_certification_report.json
```

```text
%USERPROFILE%\Documents\LMX-Windows-Certification\windows_certification_report.json
```

## CLI Agent

The original CLI flow remains available:

```powershell
python windows_certification_agent.py
python windows_certification_agent.py --upload --backend-url https://device-certification-platform.onrender.com/api/reports
```

## Notes

- If LMX Content is not installed, the app shows `LMX Content is not installed` and still generates a report.
- If upload fails, the app displays the real error message instead of crashing.
- If some system data cannot be collected, the app returns `WARNING`, `UNKNOWN`, or a failed check instead of crashing.
- The Windows app intentionally stays small. PDF, DOCX, detailed report review, and deployment decisions are handled in the web dashboard.
