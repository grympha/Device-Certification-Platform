# Android Build and Device Test

Use this checklist on a machine with Android Studio and a physical Android media player or Android test device.

## 1. Open Project

1. Open Android Studio.
2. Select `Open`.
3. Choose the `android-agent` folder.
4. Wait for Gradle sync to finish.

## 2. Configure Backend URL

Open:

```text
android-agent/app/build.gradle
```

Set:

```gradle
buildConfigField "String", "BACKEND_URL", "\"https://device-certification-platform.onrender.com/api/reports\""
```

For local LAN testing, you may temporarily use:

```gradle
buildConfigField "String", "BACKEND_URL", "\"http://YOUR_PC_LAN_IP:8000/api/reports\""
```

Do not use `127.0.0.1` when testing on a physical Android device. On Android, `127.0.0.1` means the Android device itself, not your PC.

The V1 Android agent allows cleartext HTTP traffic so local `http://YOUR_PC_LAN_IP:8000` testing works. For production, use HTTPS.

## 3. Configure LMX Package Name

In the same file, set:

```gradle
buildConfigField "String", "LMX_PACKAGE_NAME", "\"com.qruize.quad42.media.app\""
```

Keep this package name unless the LMX Content APK package changes.

## 4. Build Debug APK

In Android Studio:

```text
Build > Build Bundle(s) / APK(s) > Build APK(s)
```

Or with local Gradle:

```bash
cd android-agent
gradlew assembleDebug
```

## 5. Install APK

Example path may vary:

```bash
adb install app-debug.apk
```

If using the Android Studio output folder:

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 6. Run Diagnostic

1. Open `LMX Certification` on the Android device.
2. Confirm the screen shows a certification result.
3. Review the JSON output on screen.
4. Confirm the debug section shows backend URL, LMX package name, last diagnostic time, and upload status.

## 7. Confirm Device Signals

Check the on-screen JSON for:

- WebView version detected
- Total RAM and available RAM
- Total storage and available storage
- Screen resolution and density
- Internet connectivity
- System date, time, and timezone
- LMX app installed status
- LMX app version if installed
- LMX app launchable status

## 8. Test LMX Launch

Tap `Launch LMX Content`.

Expected:

- If LMX Content is installed and launchable, it opens.
- If it is not installed, the app stays open and shows `LMX Content not launchable`.

## 9. Test Report Upload

1. Make sure the Render backend `/health` endpoint works.
2. Tap `Show Backend URL` and confirm the app shows the expected `https://device-certification-platform.onrender.com/api/reports` URL.
3. For local LAN testing only, make sure Android device and PC are on the same network.
4. Tap `Upload Report`.
5. Confirm upload status changes from `Uploading...` to `Upload success: HTTP 200`.
6. If upload fails, read the on-screen `Last upload error` and check Logcat with tag `LMXCertification`.

Expected backend log:

```text
POST /api/reports 200 OK
```

## 10. Confirm Dashboard

1. Open dashboard at `http://localhost:5173`.
2. Confirm the real Android device appears in Device List.
3. Open Device Detail.
4. Confirm checklist values match the Android device.
5. Open the Report panel.
6. Confirm HTML and JSON export links work.

## Upload Troubleshooting

- If the Android browser can open `/docs` but upload hangs, rebuild the APK and confirm the app's `Show Backend URL` value matches the working browser URL plus `/api/reports`.
- If the app shows a timeout, confirm Windows Firewall allows inbound connections to the backend port.
- If the backend log has no `POST /api/reports`, the APK is likely using an old `BACKEND_URL` or the device cannot reach that port.
- If the backend returns an HTTP error, the app displays the HTTP status and backend error body when available.
- If Render is sleeping, the first upload may be slow. Open `/health` once, then retry upload.
