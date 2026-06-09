package com.lmx.certification

import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
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
import java.util.Locale
import java.util.TimeZone
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val logTag = "LMXCertification"
    private val lmxPackage = BuildConfig.LMX_PACKAGE_NAME
    private val backendUrl = BuildConfig.BACKEND_URL
    private lateinit var output: TextView
    private lateinit var status: TextView
    private lateinit var debugInfo: TextView
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
        val finalStatus = evaluation.getString("final_status")
        lastDiagnosticTime = latestReport.optString("system_time", currentIsoTime())
        status.text = finalStatus
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

        return JSONObject()
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
}
