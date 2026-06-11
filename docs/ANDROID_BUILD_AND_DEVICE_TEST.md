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
- LMX Playback Health section
- Content media folder status
- Audit playback status
- Log/crash status

## 7A. Storage Access and SAF Folder Picker

Android 11-15 may block direct access to another app's `Android/data` folder even when All Files Access is enabled.

1. If the app shows `Storage Access: DENIED`, tap `Grant All Files Access`.
2. Return to the app and confirm diagnostics rerun.
3. If Content Download, Playback, or Log validation is still unavailable, tap `Select LMX Folder`.
4. Select this folder:

```text
Android/data/com.qruize.quad42.media.app/files
```

The selected folder should contain:

- `QUAD42MEDIA`
- `QUAD42AUDIT`
- `QUAD42LOG`

If the app warns that the folder does not appear to be the LMX Content files folder, select the exact `files` folder above. The app also accepts selecting `Android/data/com.qruize.quad42.media.app` if it contains a `files` child folder with the required LMX subfolders.

The report should show:

- `storage_access_method`: `DIRECT_FILE_ACCESS`, `SAF_FOLDER_ACCESS`, or `UNAVAILABLE`
- `saf_access_status`: `GRANTED`, `DENIED`, or `NOT_SELECTED`
- `selected_lmx_folder_valid`: `true` when the selected folder is valid

Tap `Clear Selected LMX Folder` to remove the saved SAF permission and select again.

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

## LMX Playback Health Checks

The Android agent checks these local LMX paths:

```text
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42MEDIA/
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42LOG/
/sdcard/Android/data/com.qruize.quad42.media.app/files/QUAD42AUDIT/appender.csv
```

Expected checks:

- `LMX App`: installed, package name, version, launchable
- `Content Download`: media folder, file count, total size, last update
- `Playback`: audit file, playback record count, last playback, playlist, content types
- `Logs`: log file count, crash log count, latest log/crash timestamps
- `Overall Status`: `GREEN`, `YELLOW`, `ORANGE`, `RED`, or `UNKNOWN`

If Android blocks access to another app's storage, the agent should show `UNKNOWN` instead of crashing. `UNKNOWN` means the folder or file could not be verified from this APK context.
