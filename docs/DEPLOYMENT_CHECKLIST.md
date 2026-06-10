# Deployment Checklist

## Backend

- [ ] Render backend service deployed
- [ ] `/health` works
- [ ] `/docs` works
- [ ] Sample `POST /api/reports` works
- [ ] `/api/devices` returns uploaded device
- [ ] `/api/export/{report_id}?format=html` works
- [ ] `/api/export/{report_id}?format=json` works

## Dashboard

- [ ] Render static site deployed
- [ ] `VITE_API_BASE_URL` set to backend Render URL
- [ ] Dashboard opens
- [ ] Device list loads backend data
- [ ] Device detail loads
- [ ] Report panel loads
- [ ] Diagnostic history appears in its own section
- [ ] Search by device name works
- [ ] Status filter works
- [ ] Media Owner / Client filter works
- [ ] Edit Client saves `media_owner`
- [ ] Export links work

## Android

- [ ] `BACKEND_URL` updated to Render API `/api/reports`
- [ ] `LMX_PACKAGE_NAME` remains `com.qruize.quad42.media.app`
- [ ] APK rebuilt
- [ ] APK installed on real device
- [ ] `Show Backend URL` shows Render backend URL
- [ ] Real device upload returns `Upload success: HTTP 200`
- [ ] Backend logs show `POST /api/reports 200 OK`
- [ ] Dashboard shows uploaded real device

## Known MVP Limitations

- [ ] SQLite persistence limitation accepted for MVP testing
- [ ] Render free service sleeping accepted
- [ ] No authentication enabled yet
