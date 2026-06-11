# Dashboard Validation

Use this checklist on a Windows machine with Node.js installed.

## Requirements

- Node.js 20 or newer
- npm available in PowerShell or Command Prompt
- Backend running at `http://localhost:8000`

Check Node and npm:

```bash
node --version
npm --version
```

## Configure API URL

Copy the example environment file:

```bash
cd dashboard
copy .env.example .env
```

Default value:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Install and Run

```bash
cd dashboard
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Expected Pages

- Device List
- Device Detail
- Report
- Diagnostic History

## Expected UI Result

With backend running and a sample report uploaded:

- Status row shows `Backend connected`
- Device List shows the uploaded Android device
- Summary cards show total devices, status counts, and last upload time
- Device List can be searched by device name
- Device List can be filtered by status and Media Owner / Client
- Device Detail shows PASS/WARNING/FAIL checks
- `Edit Client` saves Media Owner / Client metadata
- Report page shows final result, failed checks, limitations, recommendations, and HTML/JSON export links
- Report page shows Device Compatibility and LMX Content Readiness checks
- Diagnostic History shows date, status, score, and summary

With backend unavailable:

- Status row shows `Showing sample data`
- Dashboard still renders the bundled sample device and report

## Common Errors and Fixes

- `npm is not recognized`: install Node.js from the official Node.js website and reopen the terminal.
- Dashboard shows sample data only: confirm backend is running at `http://localhost:8000`.
- Browser blocks API calls: confirm backend CORS middleware is enabled and API URL matches `.env`.
- Port `5173` is busy: Vite will offer another port; use the URL printed in the terminal.
- Export links fail: upload a report to the backend first, then refresh the dashboard.
