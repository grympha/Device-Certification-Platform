package com.lmx.certification

import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.StatFs
import android.provider.Settings
import android.util.Log
import android.view.Gravity
import android.view.View
import android.webkit.WebView
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.LinkedHashSet
import java.util.Locale
import java.util.TimeZone
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val logTag = "LMXCertification"
    private val lmxPackage = BuildConfig.LMX_PACKAGE_NAME
    private val backendUrl = BuildConfig.BACKEND_URL
    private val mediaDirPath = "/sdcard/Android/data/$lmxPackage/files/QUAD42MEDIA/"
    private val logDirPath = "/sdcard/Android/data/$lmxPackage/files/QUAD42LOG/"
    private val auditFilePath = "/sdcard/Android/data/$lmxPackage/files/QUAD42AUDIT/appender.csv"
    private lateinit var output: TextView
    private lateinit var status: TextView
    private lateinit var debugInfo: TextView
    private lateinit var lmxHealthOutput: TextView
    private lateinit var latestReport: JSONObject
    private var lastDiagnosticTime = "Not run"
    private var lastUploadStatus = "Not uploaded"
    private var lastUploadError = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        runDiagnostics()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        status = TextView(this).apply {
            textSize = 28f
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 24)
        }

        output = TextView(this).apply {
            textSize = 14f
            setTextIsSelectable(true)
        }

        debugInfo = TextView(this).apply {
            textSize = 13f
            setPadding(0, 0, 0, 24)
            setTextIsSelectable(true)
        }

        lmxHealthOutput = TextView(this).apply {
            textSize = 15f
            setPadding(0, 0, 0, 24)
            setTextIsSelectable(true)
        }

        val uploadButton = Button(this).apply {
            text = "Upload Report"
            setOnClickListener { uploadReport() }
        }

        val backendUrlButton = Button(this).apply {
            text = "Show Backend URL"
            setOnClickListener { showBackendUrl() }
        }

        val launchButton = Button(this).apply {
            text = "Launch LMX Content"
            setOnClickListener { launchLmxContent() }
        }

        val scroll = ScrollView(this).apply {
            addView(output)
        }

        root.addView(status)
        root.addView(debugInfo)
        root.addView(lmxHealthOutput)
        root.addView(uploadButton)
        root.addView(backendUrlButton)
        root.addView(launchButton)
        root.addView(scroll)
        setContentView(root)
        updateDebugInfo()
    }

    private fun runDiagnostics() {
        latestReport = collectReport()
        val evaluation = evaluate(latestReport)
        latestReport.put("checks", evaluation.getJSONObject("checks"))
        latestReport.put("device_compatibility", evaluation)
        val finalStatus = evaluation.getString("final_status")
        lastDiagnosticTime = latestReport.optString("system_time", currentIsoTime())
        status.text = finalStatus
        lmxHealthOutput.text = buildLmxHealthSummary(latestReport)
        output.text = latestReport.toString(2)
        saveReport(latestReport)
        updateDebugInfo()
    }

    private fun collectReport(): JSONObject {
        val memory = ActivityManager.MemoryInfo()
        (getSystemService(ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(memory)
        val storage = StatFs(Environment.getDataDirectory().path)
        val metrics = resources.displayMetrics
        val packageInfo = getPackageInfo(lmxPackage)
        val launchIntent = packageManager.getLaunchIntentForPackage(lmxPackage)

        val report = JSONObject()
            .put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}")
            .put("platform", "Android")
            .put("manufacturer", Build.MANUFACTURER)
            .put("model", Build.MODEL)
            .put("os_version", Build.VERSION.RELEASE)
            .put("android_sdk", Build.VERSION.SDK_INT)
            .put("cpu_architecture", Build.SUPPORTED_ABIS.firstOrNull() ?: "")
            .put("ram_total_gb", bytesToGb(memory.totalMem))
            .put("ram_available_gb", bytesToGb(memory.availMem))
            .put("storage_total_gb", bytesToGb(storage.blockCountLong * storage.blockSizeLong))
            .put("storage_available_gb", bytesToGb(storage.availableBlocksLong * storage.blockSizeLong))
            .put("screen_resolution", "${metrics.widthPixels}x${metrics.heightPixels}")
            .put("screen_density", metrics.densityDpi)
            .put("internet_connected", isOnline())
            .put("system_time", currentIsoTime())
            .put("timezone", TimeZone.getDefault().id)
            .put("webview_version", getWebViewVersion())
            .put("hardware_acceleration_ready", window.decorView.layerType != View.LAYER_TYPE_SOFTWARE)
            .put("lmx_app_package", lmxPackage)
            .put("lmx_app_installed", packageInfo != null)
            .put("lmx_app_version", packageInfo?.versionName ?: "")
            .put("lmx_app_launchable", launchIntent != null)
            .put("permission_status", JSONObject()
                .put("internet", permissionStatus(android.Manifest.permission.INTERNET))
                .put("network_state", permissionStatus(android.Manifest.permission.ACCESS_NETWORK_STATE))
            )
            .put("android_id", Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID))

        val lmxAppStatus = collectLmxAppStatus(packageInfo, launchIntent)
        val contentDownloadStatus = collectContentDownloadStatus()
        val playbackValidation = collectPlaybackValidation()
        val logValidation = collectLogValidation()
        val overallHealth = calculateOverallHealth(lmxAppStatus, contentDownloadStatus, playbackValidation, logValidation)

        return report
            .put("lmx_app_status", lmxAppStatus)
            .put("content_download_status", contentDownloadStatus)
            .put("playback_validation", playbackValidation)
            .put("log_validation", logValidation)
            .put("overall_health_status", overallHealth.getString("status"))
            .put("overall_health", overallHealth)
            .put("troubleshooting_recommendation", overallHealth.getString("recommendation"))
    }

    private fun collectLmxAppStatus(packageInfo: PackageInfo?, launchIntent: Intent?): JSONObject {
        val installed = packageInfo != null
        val launchable = launchIntent != null
        val status = if (installed && launchable) "PASS" else "FAIL"
        val message = when {
            !installed -> "LMX Content is not installed."
            !launchable -> "LMX Content is installed but cannot be launched."
            else -> "LMX Content is installed and launchable."
        }

        return JSONObject()
            .put("status", status)
            .put("message", message)
            .put("installed", installed)
            .put("package_name", lmxPackage)
            .put("version_name", packageInfo?.versionName ?: "")
            .put("launchable", launchable)
    }

    private fun collectContentDownloadStatus(): JSONObject {
        val mediaDir = File(mediaDirPath)
        if (!mediaDir.exists()) {
            return JSONObject()
                .put("status", "FAIL")
                .put("message", "Media folder is missing.")
                .put("media_folder_path", mediaDirPath)
                .put("media_folder_exists", false)
                .put("downloaded_file_count", 0)
                .put("total_download_size_bytes", 0)
        }

        val files = safeCollectFiles(mediaDir) ?: return unknownResult(
            "Content Download",
            "Media folder exists but cannot be read. Android storage restrictions may be blocking access."
        )
            .put("media_folder_path", mediaDirPath)
            .put("media_folder_exists", true)

        val mediaFiles = files.filter { it.isFile }
        val totalSize = mediaFiles.sumOf { safeFileLength(it) }
        val lastModified = mediaFiles.maxOfOrNull { it.lastModified() } ?: 0L
        val minutesSinceUpdate = if (lastModified > 0) (System.currentTimeMillis() - lastModified) / 60_000 else null
        val recent = minutesSinceUpdate != null && minutesSinceUpdate <= 1_440
        val status = when {
            mediaFiles.isEmpty() || totalSize <= 0 -> "FAIL"
            !recent -> "WARNING"
            else -> "PASS"
        }
        val message = when (status) {
            "PASS" -> "Media files are present and recently updated."
            "WARNING" -> "Media files are present but no recent content update was detected."
            else -> "Media folder exists but no media files were found."
        }

        return JSONObject()
            .put("status", status)
            .put("message", message)
            .put("media_folder_path", mediaDirPath)
            .put("media_folder_exists", true)
            .put("downloaded_file_count", mediaFiles.size)
            .put("total_download_size_bytes", totalSize)
            .put("total_download_size_mb", bytesToMb(totalSize))
            .put("last_content_update_timestamp", if (lastModified > 0) formatMillis(lastModified) else "")
            .put("minutes_since_last_update", minutesSinceUpdate ?: JSONObject.NULL)
            .put("recent_update_threshold_minutes", 1_440)
    }

    private fun collectPlaybackValidation(): JSONObject {
        val auditFile = File(auditFilePath)
        if (!auditFile.exists()) {
            return JSONObject()
                .put("status", "FAIL")
                .put("message", "Audit file is missing.")
                .put("audit_file_path", auditFilePath)
                .put("audit_file_exists", false)
                .put("total_playback_records", 0)
        }

        val rows = try {
            auditFile.readLines().filter { it.isNotBlank() }
        } catch (error: Exception) {
            Log.w(logTag, "Unable to read audit file: $auditFilePath", error)
            return unknownResult(
                "Playback",
                "Audit file exists but cannot be read. Android storage restrictions may be blocking access."
            )
                .put("audit_file_path", auditFilePath)
                .put("audit_file_exists", true)
        }

        if (rows.size <= 1) {
            return JSONObject()
                .put("status", "FAIL")
                .put("message", "Audit file exists but no playback records were found.")
                .put("audit_file_path", auditFilePath)
                .put("audit_file_exists", true)
                .put("total_playback_records", 0)
        }

        val records = rows.drop(1).mapNotNull { parseAuditRecord(it) }
        if (records.isEmpty()) {
            return JSONObject()
                .put("status", "FAIL")
                .put("message", "Audit file exists but no valid playback records were found.")
                .put("audit_file_path", auditFilePath)
                .put("audit_file_exists", true)
                .put("total_playback_records", 0)
        }

        val latestRecord = records.maxByOrNull { it.timestampMillis ?: 0L } ?: records.last()
        val uniqueContents = LinkedHashSet<String>()
        val contentTypes = LinkedHashSet<String>()
        records.forEach { record ->
            if (record.content.isNotBlank()) uniqueContents.add(record.content)
            if (record.contentType.isNotBlank()) contentTypes.add(record.contentType)
        }
        val minutesSincePlayback = latestRecord.timestampMillis?.let { (System.currentTimeMillis() - it) / 60_000 }
        val active = minutesSincePlayback != null && minutesSincePlayback <= 30
        val status = if (active) "PASS" else "WARNING"
        val message = if (active) {
            "Playback records are active."
        } else {
            "Playback records exist but last playback is older than 30 minutes."
        }

        return JSONObject()
            .put("status", status)
            .put("message", message)
            .put("audit_file_path", auditFilePath)
            .put("audit_file_exists", true)
            .put("total_playback_records", records.size)
            .put("last_playback_date_time", latestRecord.displayDateTime)
            .put("minutes_since_last_playback", minutesSincePlayback ?: JSONObject.NULL)
            .put("last_played_content", latestRecord.content)
            .put("current_or_last_playlist", latestRecord.playlist)
            .put("unique_content_count", uniqueContents.size)
            .put("content_types_played", contentTypes.joinToString(", "))
            .put("active_playback_threshold_minutes", 30)
    }

    private fun collectLogValidation(): JSONObject {
        val logDir = File(logDirPath)
        if (!logDir.exists()) {
            return JSONObject()
                .put("status", "FAIL")
                .put("message", "Log folder is missing.")
                .put("log_folder_path", logDirPath)
                .put("log_folder_exists", false)
        }

        val files = safeCollectFiles(logDir) ?: return unknownResult(
            "Logs",
            "Log folder exists but cannot be read. Android storage restrictions may be blocking access."
        )
            .put("log_folder_path", logDirPath)
            .put("log_folder_exists", true)

        val logFiles = files.filter { it.isFile }
        val crashFiles = logFiles.filter { file ->
            val name = file.name.lowercase(Locale.US)
            name.contains("crash") || name.contains("exception") || name.contains("fatal")
        }
        val latestLog = logFiles.maxOfOrNull { it.lastModified() } ?: 0L
        val latestCrash = crashFiles.maxOfOrNull { it.lastModified() } ?: 0L
        val status = when {
            crashFiles.isNotEmpty() -> "WARNING"
            logFiles.isNotEmpty() -> "PASS"
            else -> "WARNING"
        }
        val message = when {
            crashFiles.isNotEmpty() -> "Crash log files were found."
            logFiles.isNotEmpty() -> "Normal log files were found."
            else -> "Log folder exists but no log files were found."
        }

        return JSONObject()
            .put("status", status)
            .put("message", message)
            .put("log_folder_path", logDirPath)
            .put("log_folder_exists", true)
            .put("log_files_found", logFiles.size)
            .put("crash_log_files_found", crashFiles.size)
            .put("latest_log_update_timestamp", if (latestLog > 0) formatMillis(latestLog) else "")
            .put("latest_crash_log_timestamp", if (latestCrash > 0) formatMillis(latestCrash) else "")
    }

    private fun calculateOverallHealth(
        lmxAppStatus: JSONObject,
        contentDownloadStatus: JSONObject,
        playbackValidation: JSONObject,
        logValidation: JSONObject
    ): JSONObject {
        val lmxInstalled = lmxAppStatus.optBoolean("installed", false)
        val contentStatus = contentDownloadStatus.optString("status")
        val mediaPresent = contentStatus == "PASS" || contentStatus == "WARNING"
        val playbackStatus = playbackValidation.optString("status")
        val playbackActive = playbackStatus == "PASS"
        val playbackOld = playbackStatus == "WARNING"
        val crashFound = logValidation.optInt("crash_log_files_found", 0) > 0
        val hasUnknown = listOf(lmxAppStatus, contentDownloadStatus, playbackValidation, logValidation)
            .any { it.optString("status") == "UNKNOWN" }

        val status = when {
            !lmxInstalled || contentStatus == "FAIL" || playbackStatus == "FAIL" -> "RED"
            playbackActive && crashFound -> "YELLOW"
            mediaPresent && playbackOld -> "ORANGE"
            hasUnknown -> "UNKNOWN"
            playbackActive && !crashFound -> "GREEN"
            else -> "RED"
        }
        val recommendation = when (status) {
            "GREEN" -> "LMX Content appears healthy. No immediate action required."
            "YELLOW" -> "Playback is active, but crash logs were found. Review QUAD42LOG before production deployment."
            "ORANGE" -> "Media files are present, but playback is old. Confirm scheduling and player runtime state."
            "RED" -> "Resolve missing LMX app, media files, or playback records before deployment."
            else -> "Some LMX folders or files could not be accessed. Check Android storage permissions or run on the target media player."
        }

        return JSONObject()
            .put("status", status)
            .put("recommendation", recommendation)
            .put("lmx_installed", lmxInstalled)
            .put("media_present", mediaPresent)
            .put("playback_active", playbackActive)
            .put("crash_logs_found", crashFound)
    }

    private data class AuditRecord(
        val playlist: String,
        val contentType: String,
        val content: String,
        val displayDateTime: String,
        val timestampMillis: Long?
    )

    private fun parseAuditRecord(line: String): AuditRecord? {
        val columns = parseCsvLine(line)
        if (columns.size < 11) return null
        val playlist = columns[0].trim()
        val contentType = columns[3].trim()
        val content = columns[4].trim()
        val date = columns[5].trim()
        val startTime = columns[6].trim()
        val endTime = columns[7].trim()
        val displayTime = endTime.ifBlank { startTime }
        val timestamp = parseAuditTimestamp(date, displayTime)
        return AuditRecord(
            playlist = playlist,
            contentType = contentType,
            content = content,
            displayDateTime = listOf(date, displayTime).filter { it.isNotBlank() }.joinToString(" "),
            timestampMillis = timestamp
        )
    }

    private fun parseCsvLine(line: String): List<String> {
        val values = mutableListOf<String>()
        val current = StringBuilder()
        var inQuotes = false
        var index = 0
        while (index < line.length) {
            val char = line[index]
            when {
                char == '"' && index + 1 < line.length && line[index + 1] == '"' -> {
                    current.append('"')
                    index += 1
                }
                char == '"' -> inQuotes = !inQuotes
                char == ',' && !inQuotes -> {
                    values.add(current.toString())
                    current.clear()
                }
                else -> current.append(char)
            }
            index += 1
        }
        values.add(current.toString())
        return values
    }

    private fun parseAuditTimestamp(date: String, time: String): Long? {
        if (date.isBlank()) return null
        val candidates = listOf(
            "$date $time" to listOf(
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd hh:mm:ss a",
                "dd/MM/yyyy HH:mm:ss",
                "dd/MM/yyyy hh:mm:ss a",
                "MM/dd/yyyy HH:mm:ss",
                "MM/dd/yyyy hh:mm:ss a"
            ),
            date to listOf("yyyy-MM-dd", "dd/MM/yyyy", "MM/dd/yyyy")
        )
        for ((value, patterns) in candidates) {
            for (pattern in patterns) {
                try {
                    val parser = SimpleDateFormat(pattern, Locale.US)
                    parser.timeZone = TimeZone.getDefault()
                    return parser.parse(value)?.time
                } catch (_: Exception) {
                }
            }
        }
        return null
    }

    private fun safeCollectFiles(root: File): List<File>? {
        return try {
            val children = root.listFiles() ?: return null
            val files = mutableListOf<File>()
            children.forEach { child ->
                files.add(child)
                if (child.isDirectory) {
                    val nested = safeCollectFiles(child)
                    if (nested != null) files.addAll(nested)
                }
            }
            files
        } catch (error: Exception) {
            Log.w(logTag, "Unable to read ${root.absolutePath}", error)
            null
        }
    }

    private fun safeFileLength(file: File): Long {
        return try {
            file.length()
        } catch (_: Exception) {
            0L
        }
    }

    private fun unknownResult(module: String, message: String): JSONObject {
        return JSONObject()
            .put("status", "UNKNOWN")
            .put("message", message)
            .put("module", module)
    }

    private fun buildLmxHealthSummary(report: JSONObject): String {
        val lmx = report.getJSONObject("lmx_app_status")
        val content = report.getJSONObject("content_download_status")
        val playback = report.getJSONObject("playback_validation")
        val logs = report.getJSONObject("log_validation")
        val overall = report.getJSONObject("overall_health")

        return """
            LMX Playback Health

            LMX App: ${lmx.optString("status")} - ${lmx.optString("message")}
            Package: ${lmx.optString("package_name")}
            Version: ${lmx.optString("version_name", "Not detected")}

            Content Download: ${content.optString("status")} - ${content.optString("message")}
            Files: ${content.optInt("downloaded_file_count", 0)}
            Size: ${content.optDouble("total_download_size_mb", 0.0)} MB
            Last Update: ${content.optString("last_content_update_timestamp", "Unknown")}

            Playback: ${playback.optString("status")} - ${playback.optString("message")}
            Records: ${playback.optInt("total_playback_records", 0)}
            Last Played: ${playback.optString("last_played_content", "Unknown")}
            Playlist: ${playback.optString("current_or_last_playlist", "Unknown")}
            Last Playback: ${playback.optString("last_playback_date_time", "Unknown")}

            Logs: ${logs.optString("status")} - ${logs.optString("message")}
            Log Files: ${logs.optInt("log_files_found", 0)}
            Crash Logs: ${logs.optInt("crash_log_files_found", 0)}

            Overall Status: ${overall.optString("status")}
            Recommendation: ${overall.optString("recommendation")}
        """.trimIndent()
    }

    private fun evaluate(report: JSONObject): JSONObject {
        val checks = JSONObject()
        checks.put("android_version", checkAndroid())
        checks.put("ram", checkRam(report.getDouble("ram_total_gb")))
        checks.put("storage", checkStorage(report.getDouble("storage_available_gb")))
        checks.put("webview", checkWebView(report.optString("webview_version")))
        checks.put("network", checkBoolean(report.getBoolean("internet_connected"), "Internet connectivity is available.", "Device has no internet connectivity."))
        checks.put("time_timezone", checkBoolean(report.optString("timezone").isNotBlank(), "System date, time, and timezone are present.", "System date, time, or timezone could not be verified.", "WARNING"))
        checks.put("lmx_app_installed", checkBoolean(report.getBoolean("lmx_app_installed"), "LMX Content app is installed.", "LMX Content app is not installed."))
        checks.put("lmx_app_launch", checkBoolean(report.getBoolean("lmx_app_launchable"), "LMX Content app is launchable.", "LMX Content app cannot be launched."))
        checks.put("programmatic_vast", checkWebView(report.optString("webview_version"), "Programmatic/VAST playback is ready.", "Programmatic/VAST playback is not ready because WebView is below 120."))

        var fails = 0
        var warnings = 0
        checks.keys().forEach { key ->
            when (checks.getJSONObject(key).getString("status")) {
                "FAIL" -> fails += 1
                "WARNING" -> warnings += 1
            }
        }

        val finalStatus = when {
            fails > 0 -> "Not Recommended"
            warnings > 0 -> "Approved with Limitation"
            else -> "Approved"
        }
        val score = maxOf(0, 100 - fails * 25 - warnings * 10)
        return JSONObject().put("final_status", finalStatus).put("score", score).put("checks", checks)
    }

    private fun checkAndroid(): JSONObject {
        return when {
            Build.VERSION.SDK_INT < Build.VERSION_CODES.N -> result("FAIL", "Android version is below 7.")
            Build.VERSION.SDK_INT <= Build.VERSION_CODES.Q -> result("WARNING", "Android 7 to 10 supports basic playback only.")
            else -> result("PASS", "Android version is supported.")
        }
    }

    private fun checkRam(ramGb: Double): JSONObject {
        return when {
            ramGb < 2 -> result("FAIL", "RAM is below 2GB.")
            ramGb < 4 -> result("WARNING", "RAM is between 2GB and 4GB.")
            else -> result("PASS", "RAM is sufficient.")
        }
    }

    private fun checkStorage(storageGb: Double): JSONObject {
        return when {
            storageGb < 2 -> result("FAIL", "Available storage is below 2GB.")
            storageGb <= 5 -> result("WARNING", "Available storage is between 2GB and 5GB.")
            else -> result("PASS", "Available storage is sufficient.")
        }
    }

    private fun checkWebView(version: String, pass: String = "Android System WebView is ready.", fail: String = "Android System WebView is below version 120."): JSONObject {
        val major = version.takeWhile { it.isDigit() }.toIntOrNull() ?: 0
        return if (major < 120) result("FAIL", fail) else result("PASS", pass)
    }

    private fun checkBoolean(value: Boolean, pass: String, fail: String, failStatus: String = "FAIL"): JSONObject {
        return if (value) result("PASS", pass) else result(failStatus, fail)
    }

    private fun result(status: String, message: String): JSONObject {
        return JSONObject().put("status", status).put("message", message)
    }

    private fun uploadReport() {
        status.text = "Uploading..."
        lastUploadStatus = "Uploading to $backendUrl"
        lastUploadError = ""
        updateDebugInfo()
        Log.i(logTag, "Uploading diagnostic report to $backendUrl")
        thread {
            var connection: HttpURLConnection? = null
            try {
                val requestBody = latestReport.toString()
                connection = (URL(backendUrl).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10_000
                    readTimeout = 10_000
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                    doOutput = true
                    outputStream.use { stream ->
                        stream.write(requestBody.toByteArray(Charsets.UTF_8))
                        stream.flush()
                    }
                }

                val code = connection.responseCode
                val responseBody = readResponseBody(connection, code)
                Log.i(logTag, "Upload completed with HTTP $code. Response: $responseBody")
                runOnUiThread {
                    if (code in 200..299) {
                        lastUploadStatus = "Upload success: HTTP $code"
                        lastUploadError = ""
                    } else {
                        lastUploadStatus = "Upload failed: HTTP $code"
                        lastUploadError = responseBody.ifBlank { "Backend returned HTTP $code without an error body." }
                    }
                    status.text = lastUploadStatus
                    updateDebugInfo()
                }
            } catch (error: Exception) {
                Log.e(logTag, "Upload failed for $backendUrl", error)
                runOnUiThread {
                    lastUploadStatus = "Upload failed"
                    lastUploadError = "${error.javaClass.simpleName}: ${error.message ?: "Unknown error"}"
                    status.text = "Upload failed: $lastUploadError"
                    updateDebugInfo()
                }
            } finally {
                connection?.disconnect()
            }
        }
    }

    private fun readResponseBody(connection: HttpURLConnection, code: Int): String {
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        return stream?.bufferedReader()?.use { it.readText() } ?: ""
    }

    private fun showBackendUrl() {
        val message = "Backend URL: $backendUrl"
        status.text = message
        Log.i(logTag, message)
        updateDebugInfo()
    }

    private fun launchLmxContent() {
        val launchIntent = packageManager.getLaunchIntentForPackage(lmxPackage)
        if (launchIntent != null) startActivity(launchIntent) else status.text = "LMX Content not launchable"
    }

    private fun saveReport(report: JSONObject) {
        val file = File(getExternalFilesDir(null), "lmx_diagnostic_report.json")
        file.writeText(report.toString(2))
    }

    private fun getPackageInfo(packageName: String) = try {
        packageManager.getPackageInfo(packageName, 0)
    } catch (_: PackageManager.NameNotFoundException) {
        null
    }

    private fun getWebViewVersion(): String {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WebView.getCurrentWebViewPackage()?.versionName ?: ""
            } else {
                getPackageInfo("com.google.android.webview")?.versionName
                    ?: getPackageInfo("com.android.webview")?.versionName
                    ?: ""
            }
        } catch (_: Exception) {
            ""
        }
    }

    private fun currentIsoTime(): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        return formatter.format(Date())
    }

    private fun updateDebugInfo() {
        val errorLine = if (lastUploadError.isBlank()) "" else "\nLast upload error: $lastUploadError"
        debugInfo.text = """
            Backend URL: $backendUrl
            LMX package name: $lmxPackage
            Last diagnostic time: $lastDiagnosticTime
            Last upload status: $lastUploadStatus$errorLine
        """.trimIndent()
    }

    private fun isOnline(): Boolean {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun permissionStatus(permission: String): String {
        return if (checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED) "granted" else "denied"
    }

    private fun bytesToGb(bytes: Long): Double {
        return Math.round((bytes.toDouble() / 1024 / 1024 / 1024) * 10.0) / 10.0
    }

    private fun bytesToMb(bytes: Long): Double {
        return Math.round((bytes.toDouble() / 1024 / 1024) * 10.0) / 10.0
    }

    private fun formatMillis(value: Long): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        return formatter.format(Date(value))
    }
}
