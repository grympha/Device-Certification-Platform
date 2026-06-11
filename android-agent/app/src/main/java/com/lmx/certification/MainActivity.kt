package com.lmx.certification

import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageInfo
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.StatFs
import android.util.Log
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
    private val lmxPackageName = BuildConfig.LMX_PACKAGE_NAME
    private val backendUrl = BuildConfig.BACKEND_URL

    private lateinit var statusView: TextView
    private lateinit var readinessView: TextView
    private lateinit var outputView: TextView
    private lateinit var debugView: TextView
    private var latestReport = JSONObject()
    private var lastDiagnosticTime = "Not run yet"
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
            setPadding(28, 28, 28, 28)
        }

        root.addView(TextView(this).apply {
            text = "LMX Device Certification"
            textSize = 24f
            setPadding(0, 0, 0, 12)
        })

        statusView = TextView(this).apply {
            text = "Preparing diagnostics..."
            textSize = 18f
            setPadding(0, 0, 0, 16)
        }
        root.addView(statusView)

        val actions = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 0, 0, 18)
        }

        actions.addView(Button(this).apply {
            text = "Upload Report"
            setOnClickListener { uploadReport() }
        })
        actions.addView(Button(this).apply {
            text = "Show Backend URL"
            setOnClickListener {
                lastUploadStatus = "Backend URL: $backendUrl"
                updateDebugInfo()
            }
        })
        actions.addView(Button(this).apply {
            text = "Launch LMX Content"
            setOnClickListener { launchLmxContent() }
        })
        root.addView(actions)

        readinessView = TextView(this).apply {
            textSize = 15f
            setPadding(0, 0, 0, 16)
        }
        root.addView(readinessView)

        debugView = TextView(this).apply {
            textSize = 14f
            setPadding(0, 0, 0, 16)
        }
        root.addView(debugView)

        outputView = TextView(this).apply {
            textSize = 13f
            setTextIsSelectable(true)
            setPadding(0, 10, 0, 0)
        }
        root.addView(outputView)

        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun runDiagnostics() {
        latestReport = collectReport()
        val evaluation = evaluate(latestReport)
        latestReport.put("checks", evaluation.getJSONObject("checks"))
        latestReport.put("final_status", evaluation.getString("final_status"))
        latestReport.put("score", evaluation.getInt("score"))
        latestReport.put("summary", evaluation.getString("summary"))
        latestReport.put("recommendations", evaluation.getString("recommendations"))
        latestReport.put("final_recommendation", finalRecommendation(evaluation.getString("final_status")))
        lastDiagnosticTime = latestReport.optString("system_time", currentIsoTime())

        statusView.text = "${evaluation.getString("final_status")} - Score ${evaluation.getInt("score")}"
        readinessView.text = buildReadinessSummary(latestReport, evaluation)
        outputView.text = latestReport.toString(2)
        updateDebugInfo()
        saveReport(latestReport)
    }

    private fun collectReport(): JSONObject {
        val metrics = memoryMetrics()
        val storage = storageMetrics()
        val packageInfo = packageInfo(lmxPackageName)
        val launchable = packageManager.getLaunchIntentForPackage(lmxPackageName) != null

        return JSONObject()
            .put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            .put("platform", "Android")
            .put("manufacturer", Build.MANUFACTURER ?: "")
            .put("model", Build.MODEL ?: "")
            .put("os_version", Build.VERSION.RELEASE ?: "")
            .put("android_sdk", Build.VERSION.SDK_INT)
            .put("cpu_architecture", Build.SUPPORTED_ABIS.firstOrNull() ?: "")
            .put("ram_total_gb", metrics.first)
            .put("ram_available_gb", metrics.second)
            .put("storage_total_gb", storage.first)
            .put("storage_available_gb", storage.second)
            .put("screen_resolution", screenResolution())
            .put("screen_density", resources.displayMetrics.densityDpi)
            .put("internet_connected", isOnline())
            .put("system_time", currentIsoTime())
            .put("timezone", TimeZone.getDefault().id)
            .put("webview_version", webViewVersion())
            .put("hardware_acceleration_ready", true)
            .put("lmx_app_package", lmxPackageName)
            .put("lmx_app_installed", packageInfo != null)
            .put("lmx_app_version", packageInfo?.versionName?.toString() ?: "")
            .put("lmx_app_launchable", launchable)
            .put(
                "permission_status",
                JSONObject()
                    .put("internet", "declared")
                    .put("network_state", "declared")
            )
    }

    private fun evaluate(report: JSONObject): JSONObject {
        val checks = JSONObject()
            .put("android_version", androidVersionCheck(report))
            .put("ram", ramCheck(report))
            .put("storage", storageCheck(report))
            .put("webview", webViewCheck(report))
            .put("network", networkCheck(report))
            .put("time_timezone", timeCheck(report))
            .put("lmx_app_installed", lmxInstalledCheck(report))
            .put("lmx_app_launch", lmxLaunchCheck(report))
            .put("lmx_version", lmxVersionCheck(report))
            .put("programmatic_vast", programmaticCheck(report))
            .put("pull_to_content", pullToContentCheck(report))

        var failures = 0
        var warnings = 0
        checks.keys().forEach { key ->
            when (checks.getJSONObject(key).getString("status")) {
                "FAIL" -> failures += 1
                "WARNING" -> warnings += 1
            }
        }

        val score = (100 - failures * 25 - warnings * 10).coerceAtLeast(0)
        val finalStatus = when {
            failures > 0 -> "Not Recommended"
            warnings > 0 -> "Approved with Limitation"
            else -> "Approved"
        }

        return JSONObject()
            .put("checks", checks)
            .put("final_status", finalStatus)
            .put("score", score)
            .put("summary", summary(finalStatus))
            .put("recommendations", recommendations(checks))
    }

    private fun androidVersionCheck(report: JSONObject): JSONObject {
        val version = majorVersion(report.optString("os_version"))
        return when {
            version < 9 -> check("FAIL", "Android version is below 9.")
            version <= 10 -> check("WARNING", "Android 9 to 10 supports limited deployment.")
            else -> check("PASS", "Android 11 or above is supported.")
        }
    }

    private fun ramCheck(report: JSONObject): JSONObject {
        val ram = report.optDouble("ram_total_gb", 0.0)
        return when {
            ram < 2.0 -> check("FAIL", "RAM is below 2GB.")
            ram < 4.0 -> check("WARNING", "RAM is between 2GB and 4GB.")
            else -> check("PASS", "RAM is sufficient.")
        }
    }

    private fun storageCheck(report: JSONObject): JSONObject {
        val storage = report.optDouble("storage_available_gb", 0.0)
        return when {
            storage < 2.0 -> check("FAIL", "Available storage is below 2GB.")
            storage < 5.0 -> check("WARNING", "Available storage is between 2GB and 4.99GB.")
            else -> check("PASS", "Available storage is 5GB or above.")
        }
    }

    private fun webViewCheck(report: JSONObject): JSONObject {
        val version = majorVersion(report.optString("webview_version"))
        return when {
            version < 100 -> check("FAIL", "Android System WebView is below version 100.")
            version < 110 -> check("WARNING", "Android System WebView is between version 100 and 109.")
            else -> check("PASS", "Android System WebView is version 110 or above.")
        }
    }

    private fun networkCheck(report: JSONObject): JSONObject {
        return if (report.optBoolean("internet_connected")) {
            check("PASS", "Internet connectivity is available.")
        } else {
            check("FAIL", "Device has no internet connectivity.")
        }
    }

    private fun timeCheck(report: JSONObject): JSONObject {
        return if (report.optString("system_time").isBlank()) {
            check("FAIL", "Device time is invalid or missing.")
        } else if (report.optString("timezone").isBlank()) {
            check("WARNING", "Timezone could not be verified.")
        } else {
            check("PASS", "System date, time, and timezone are present.")
        }
    }

    private fun lmxInstalledCheck(report: JSONObject): JSONObject {
        return if (report.optBoolean("lmx_app_installed")) {
            check("PASS", "LMX Content app is installed.")
        } else {
            check("FAIL", "LMX Content app is not installed.")
        }
    }

    private fun lmxLaunchCheck(report: JSONObject): JSONObject {
        return if (report.optBoolean("lmx_app_launchable")) {
            check("PASS", "LMX Content app is launchable.")
        } else {
            check("FAIL", "LMX Content app cannot be launched.")
        }
    }

    private fun lmxVersionCheck(report: JSONObject): JSONObject {
        val version = report.optString("lmx_app_version")
        return if (version.isBlank()) {
            check("FAIL", "LMX Content version could not be detected.")
        } else {
            check("PASS", "LMX Content version detected: $version.")
        }
    }

    private fun programmaticCheck(report: JSONObject): JSONObject {
        val android = majorVersion(report.optString("os_version"))
        val ram = report.optDouble("ram_total_gb", 0.0)
        val webView = majorVersion(report.optString("webview_version"))
        val online = report.optBoolean("internet_connected")
        return when {
            android < 11 || webView < 100 -> check("FAIL", "Programmatic/VAST readiness requires Android 11+ and WebView 100+.")
            android >= 11 && webView >= 110 && ram >= 3.0 && online -> check("PASS", "Programmatic/VAST readiness requirements are met.")
            android >= 11 && webView in 100..109 -> check("WARNING", "Programmatic/VAST readiness is limited with WebView 100 to 109.")
            else -> check("WARNING", "Programmatic/VAST readiness has unverified RAM, network, or WebView requirements.")
        }
    }

    private fun pullToContentCheck(report: JSONObject): JSONObject {
        val version = report.optString("lmx_app_version")
        return if (versionAtLeast(version, "2.9.1.2")) {
            check("PASS", "Android LMX version supports Pull To Content.")
        } else {
            check("FAIL", "Android LMX version is below 2.9.1.2 native.")
        }
    }

    private fun check(status: String, message: String): JSONObject {
        return JSONObject().put("status", status).put("message", message)
    }

    private fun summary(finalStatus: String): String {
        return when (finalStatus) {
            "Approved" -> "Device meets the current LMX Content compatibility requirements."
            "Approved with Limitation" -> "Device can run LMX Content with limitations."
            else -> "Device is not recommended for LMX Content deployment until failed checks are resolved."
        }
    }

    private fun recommendations(checks: JSONObject): String {
        val items = mutableListOf<String>()
        checks.keys().forEach { key ->
            val item = checks.getJSONObject(key)
            if (item.optString("status") != "PASS") {
                items.add(item.optString("message"))
            }
        }
        return if (items.isEmpty()) {
            "No action required before deployment."
        } else {
            items.joinToString(" ") + " Resolve failed checks and review limitations before production deployment."
        }
    }

    private fun finalRecommendation(finalStatus: String): String {
        return when (finalStatus) {
            "Approved" -> "Certified for LMX Content"
            "Approved with Limitation" -> "Certified with Limitation"
            else -> "Not Recommended"
        }
    }

    private fun buildReadinessSummary(report: JSONObject, evaluation: JSONObject): String {
        val checks = evaluation.getJSONObject("checks")
        return """
            Device Compatibility
            Android Version: ${checks.getJSONObject("android_version").getString("status")}
            RAM: ${checks.getJSONObject("ram").getString("status")}
            Storage: ${checks.getJSONObject("storage").getString("status")}
            WebView: ${checks.getJSONObject("webview").getString("status")}
            Network: ${checks.getJSONObject("network").getString("status")}
            Time/Timezone: ${checks.getJSONObject("time_timezone").getString("status")}

            LMX Content Readiness
            Package: ${report.optString("lmx_app_package")}
            Installed: ${yesNo(report.optBoolean("lmx_app_installed"))}
            Launchable: ${yesNo(report.optBoolean("lmx_app_launchable"))}
            Version: ${report.optString("lmx_app_version", "Not detected")}
            LMX Version: ${checks.getJSONObject("lmx_version").getString("status")}
            Programmatic/VAST Readiness: ${checks.getJSONObject("programmatic_vast").getString("status")}
            Pull To Content Readiness: ${checks.getJSONObject("pull_to_content").getString("status")}
            Final Recommendation: ${finalRecommendation(evaluation.getString("final_status"))}
        """.trimIndent()
    }

    private fun uploadReport() {
        lastUploadStatus = "Uploading..."
        lastUploadError = ""
        updateDebugInfo()

        val payload = latestReport.toString()
        thread {
            try {
                Log.i(logTag, "Uploading report to $backendUrl")
                val connection = (URL(backendUrl).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10_000
                    readTimeout = 10_000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
                connection.outputStream.use { output ->
                    output.write(payload.toByteArray(Charsets.UTF_8))
                }
                val code = connection.responseCode
                val body = if (code in 200..299) {
                    connection.inputStream.bufferedReader().use { it.readText() }
                } else {
                    connection.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                }
                connection.disconnect()
                runOnUiThread {
                    lastUploadStatus = "Upload success: HTTP $code"
                    lastUploadError = if (code in 200..299) "" else body.take(300)
                    updateDebugInfo()
                }
            } catch (error: Exception) {
                Log.e(logTag, "Upload failed", error)
                runOnUiThread {
                    lastUploadStatus = "Upload failed"
                    lastUploadError = error.message ?: error.javaClass.simpleName
                    updateDebugInfo()
                }
            }
        }
    }

    private fun launchLmxContent() {
        val intent = packageManager.getLaunchIntentForPackage(lmxPackageName)
        if (intent == null) {
            lastUploadStatus = "LMX Content not launchable"
            updateDebugInfo()
            return
        }
        startActivity(intent)
    }

    private fun updateDebugInfo() {
        debugView.text = """
            Backend URL: $backendUrl
            LMX package name: $lmxPackageName
            Last diagnostic time: $lastDiagnosticTime
            Last upload status: $lastUploadStatus
            Last upload error: ${if (lastUploadError.isBlank()) "None" else lastUploadError}
        """.trimIndent()
    }

    private fun packageInfo(packageName: String): PackageInfo? {
        return try {
            packageManager.getPackageInfo(packageName, 0)
        } catch (_: Exception) {
            null
        }
    }

    private fun memoryMetrics(): Pair<Double, Double> {
        val info = ActivityManager.MemoryInfo()
        (getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(info)
        return Pair(bytesToGb(info.totalMem), bytesToGb(info.availMem))
    }

    private fun storageMetrics(): Pair<Double, Double> {
        val stat = StatFs(Environment.getDataDirectory().path)
        return Pair(bytesToGb(stat.totalBytes), bytesToGb(stat.availableBytes))
    }

    private fun screenResolution(): String {
        val metrics = resources.displayMetrics
        return "${metrics.widthPixels}x${metrics.heightPixels}"
    }

    private fun isOnline(): Boolean {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun webViewVersion(): String {
        return try {
            WebView.getCurrentWebViewPackage()?.versionName ?: ""
        } catch (error: Exception) {
            Log.w(logTag, "WebView version unavailable", error)
            ""
        }
    }

    private fun currentIsoTime(): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        formatter.timeZone = TimeZone.getDefault()
        return formatter.format(Date())
    }

    private fun saveReport(report: JSONObject) {
        try {
            File(filesDir, "latest_report.json").writeText(report.toString(2))
        } catch (error: Exception) {
            Log.w(logTag, "Could not save local report", error)
        }
    }

    private fun majorVersion(value: String): Int {
        val match = Regex("(\\d+)").find(value)
        return match?.value?.toIntOrNull() ?: 0
    }

    private fun versionAtLeast(value: String, minimum: String): Boolean {
        val current = versionParts(value)
        val required = versionParts(minimum)
        val max = maxOf(current.size, required.size)
        val normalizedCurrent = current + List(max - current.size) { 0 }
        val normalizedRequired = required + List(max - required.size) { 0 }
        return normalizedCurrent.zip(normalizedRequired).firstOrNull { it.first != it.second }?.let {
            it.first > it.second
        } ?: true
    }

    private fun versionParts(value: String): List<Int> {
        return value.lowercase(Locale.US)
            .replace("native", "")
            .split(".")
            .map { part -> part.filter { it.isDigit() }.toIntOrNull() ?: 0 }
    }

    private fun bytesToGb(value: Long): Double {
        return String.format(Locale.US, "%.2f", value / 1024.0 / 1024.0 / 1024.0).toDouble()
    }

    private fun yesNo(value: Boolean): String = if (value) "Yes" else "No"
}
