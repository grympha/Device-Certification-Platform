# Render Deployment

This guide deploys the V1 MVP on Render free tier using only free/open-source project components.

## Services

Render will create two services from `render.yaml`:

- `device-certification-api`: FastAPI backend web service
- `device-certification-dashboard`: React/Vite static site

## 1. Connect GitHub Repo

1. Log in to Render.
2. Choose `New` > `Blueprint`.
3. Connect GitHub repo:

```text
https://github.com/grympha/Device-Certification-Platform
```

4. Select the repository and let Render read `render.yaml`.

## 2. Backend Service Settings

If creating manually instead of Blueprint:

```text
Name: device-certification-api
Type: Web Service
Runtime: Python
Python Version: 3.12.7
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Plan: Free
```

The repo includes `runtime.txt` files at the repo root and inside `backend/` with:

```text
python-3.12.7
```

Render must use Python 3.12 for this MVP. Do not deploy the backend with Python 3.14 because pinned dependencies such as `pydantic-core` may fail during installation.

After deployment, verify:

```text
https://device-certification-platform.onrender.com/health
https://device-certification-platform.onrender.com/docs
```

If Render assigns a different URL, use that actual URL in all later steps.

## 3. Dashboard Static Site Settings

If creating manually instead of Blueprint:

```text
Name: device-certification-dashboard
Type: Static Site
Root Directory: dashboard
Build Command: npm install && npm run build
Publish Directory: dist
Plan: Free
```

Environment variable:

```text
VITE_API_BASE_URL=https://device-certification-platform.onrender.com
```

The dashboard must use the backend service URL, not the dashboard URL.

## 4. CORS

The backend currently allows:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `https://*.onrender.com` through a regular expression

If your Render dashboard still shows a CORS error, add the final dashboard URL explicitly in `backend/app/main.py`.

## 5. Android Agent URL

After the backend URL is confirmed, open:

```text
android-agent/app/build.gradle
```

Set:

```gradle
buildConfigField "String", "BACKEND_URL", "\"https://device-certification-platform.onrender.com/api/reports\""
```

Keep the LMX package name:

```gradle
buildConfigField "String", "LMX_PACKAGE_NAME", "\"com.qruize.quad42.media.app\""
```

Then rebuild and reinstall the APK.

## 6. Rebuild APK

In Android Studio:

```text
Build > Build Bundle(s) / APK(s) > Build APK(s)
```

Or:

```bash
cd android-agent
gradlew assembleDebug
```

Install:

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 7. Smoke Test Checklist

Backend:

- Open `/health`
- Open `/docs`
- POST `reports/sample_android_report.json` to `/api/reports`
- Confirm `/api/devices` returns the uploaded device
- Confirm `/api/export/{report_id}?format=html` works
- Confirm `/api/export/{report_id}?format=json` works

Dashboard:

- Open the Render dashboard URL
- Confirm it shows `Backend connected`
- Confirm device list loads backend data
- Confirm report export links point to the backend URL

Android:

- Tap `Show Backend URL`
- Confirm it uses `https://device-certification-platform.onrender.com/api/reports`
- Tap `Upload Report`
- Confirm `Upload success: HTTP 200`
- Confirm the dashboard shows the uploaded Android device

## Common Issues

- Render free services sleep after inactivity. The first request may be slow.
- If `/health` is slow or times out, wait and refresh once.
- If dashboard data does not load, confirm `VITE_API_BASE_URL` is the backend URL.
- If CORS fails, add the final dashboard URL explicitly in backend CORS settings.
- SQLite on Render free tier may not persist across redeploys/restarts unless a persistent disk is configured.
- SQLite is acceptable for MVP testing. Future production upgrade should use PostgreSQL.
