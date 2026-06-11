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

For local LAN testing, temporarily use:

```gradle
buildConfigField "String", "BACKEND_URL", "\"http://YOUR_PC_LAN_IP:8000/api/reports\""
```

Do not use `127.0.0.1` when testing on a physical Android device. On Android, `127.0.0.1` means the Android device itself.

## 3. Configure LMX Package Name

In the same file, set:

```gradle
buildConfigField "String", "LMX_PACKAGE_NAME", "\"com.qruize.quad42.media.app\""
```

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

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 6. Run Diagnostic

1. Open `LMX Certification` on the Android device.
2. Confirm the screen shows a certification result.
3. Review the JSON output on screen.
4. Confirm the debug section shows backend URL, LMX package name, last diagnostic time, and upload status.

## 7. Confirm Device Compatibility Signals

Check the on-screen JSON for:

- Android version
- Total RAM and available RAM
- Total storage and available storage
- WebView version
- Internet connectivity
- System date, time, and timezone

## 8. Confirm LMX Content Readiness

Check:

- LMX app installed status
- LMX package name: `com.qruize.quad42.media.app`
- LMX version if installed
- LMX app launchable status
- Programmatic/VAST Readiness
- Pull To Content Readiness

Pull To Content Readiness rules:

- Android: `PASS` when LMX Version is `2.9.1.2 native` or newer.
- Windows: `PASS` when LMX Version is `1.0.34` or newer.

The Android Agent does not read another app's media, audit, or log folders.

## 9. Test LMX Launch

Tap `Launch LMX Content`.

Expected:

- If LMX Content is installed and launchable, it opens.
- If it is not installed, the app stays open and shows `LMX Content not launchable`.

## 10. Test Report Upload

1. Make sure the Render backend `/health` endpoint works.
2. Tap `Show Backend URL` and confirm the app shows the expected `https://device-certification-platform.onrender.com/api/reports` URL.
3. Tap `Upload Report`.
4. Confirm upload status changes from `Uploading...` to `Upload success: HTTP 200`.
5. If upload fails, read the on-screen `Last upload error` and check Logcat with tag `LMXCertification`.

Expected backend log:

```text
POST /api/reports 200 OK
```

## 11. Confirm Dashboard

1. Open dashboard at `http://localhost:5173` or the Render static site URL.
2. Confirm the real Android device appears in Device List.
3. Open Device Detail.
4. Confirm Device Compatibility and LMX Content Readiness values match the Android device.
5. Open the Report panel.
6. Confirm HTML and JSON export links work.
