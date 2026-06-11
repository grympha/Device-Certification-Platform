import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, FileText, LayoutDashboard, RefreshCw, Save, Search, UserPen } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const APK_DOWNLOAD_URL = "/downloads/app-debug.apk";

const sampleReport = {
  id: 1,
  device_id: 1,
  created_at: "2026-06-09T13:00:00Z",
  final_status: "Not Recommended",
  score: 50,
  final_recommendation: "Not Recommended",
  device_report_summary: {
    overall_summary: "Device is not recommended for LMX Content deployment until failed checks are resolved.",
    good_points: [
      "Android 11 or above is supported.",
      "RAM is sufficient.",
      "Internet connectivity is available.",
      "LMX Content app is installed.",
      "LMX Content app is launchable."
    ],
    warning_points: [
      "Android System WebView is between version 100 and 109.",
      "Programmatic/VAST readiness is limited with WebView 100 to 109."
    ],
    failed_points: [
      "Available storage is below 2GB.",
      "Android LMX version is below 2.9.1.2 native."
    ],
    likely_causes: [
      "Low available storage can prevent updates, cached content, or normal app operation.",
      "Older Android System WebView versions may have limited compatibility with HTML, URL, or VAST playback.",
      "The installed LMX Content version may be below the Pull To Content requirement."
    ],
    recommended_actions: [
      "Free device storage or use a device with at least 5GB available storage.",
      "Update Android System WebView where possible.",
      "Update LMX Content to Android version 2.9.1.2 native or newer."
    ]
  },
  summary: "Device is not recommended for LMX Content deployment until failed checks are resolved.",
  recommendations:
    "Available storage is below 2GB. Android LMX version is below 2.9.1.2 native. Resolve failed checks and review limitations before production deployment.",
  raw_json: {
    device_name: "Solum Box",
    platform: "Android",
    manufacturer: "Solum",
    model: "Box",
    media_owner: "",
    os_version: "15",
    webview_version: "106.0.5249.126",
    lmx_app_package: "com.qruize.quad42.media.app",
    lmx_app_version: "1.4.2",
    lmx_app_installed: true,
    lmx_app_launchable: true,
    ram_total_gb: 4,
    storage_available_gb: 1.2,
    internet_connected: true,
    timezone: "Asia/Kuala_Lumpur",
    final_recommendation: "Not Recommended",
    checks: {
      android_version: { status: "PASS", message: "Android 11 or above is supported." },
      ram: { status: "PASS", message: "RAM is sufficient." },
      storage: { status: "FAIL", message: "Available storage is below 2GB." },
      webview: { status: "WARNING", message: "Android System WebView is between version 100 and 109." },
      network: { status: "PASS", message: "Internet connectivity is available." },
      time_timezone: { status: "PASS", message: "System date, time, and timezone are present." },
      lmx_app_installed: { status: "PASS", message: "LMX Content app is installed." },
      lmx_app_launch: { status: "PASS", message: "LMX Content app is launchable." },
      lmx_version: { status: "PASS", message: "LMX Content version detected: 1.4.2." },
      programmatic_vast: { status: "WARNING", message: "Programmatic/VAST readiness is limited with WebView 100 to 109." },
      pull_to_content: { status: "FAIL", message: "Android LMX version is below 2.9.1.2 native." }
    }
  }
};

const sampleDevice = {
  id: 1,
  device_name: "Solum Box",
  platform: "Android",
  manufacturer: "Solum",
  model: "Box",
  media_owner: "",
  os_version: "15",
  webview_version: "106.0.5249.126",
  lmx_app_version: "1.4.2",
  latest_status: "Not Recommended",
  latest_score: 50,
  last_seen: "2026-06-09T13:00:00Z",
  reports: [sampleReport]
};

function App() {
  const [devices, setDevices] = useState([sampleDevice]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(1);
  const [deviceDetail, setDeviceDetail] = useState(sampleDevice);
  const [report, setReport] = useState(sampleReport);
  const [apiOnline, setApiOnline] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [ownerFilter, setOwnerFilter] = useState("All");
  const [editingOwner, setEditingOwner] = useState(false);
  const [ownerDraft, setOwnerDraft] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) || devices[0],
    [devices, selectedDeviceId]
  );

  const filteredDevices = useMemo(() => {
    const search = searchTerm.trim().toLowerCase();
    return devices.filter((device) => {
      const owner = displayOwner(device).toLowerCase();
      const nameMatch = !search || device.device_name.toLowerCase().includes(search);
      const statusMatch = statusFilter === "All" || device.latest_status === statusFilter;
      const ownerMatch = ownerFilter === "All" || owner === ownerFilter.toLowerCase();
      return nameMatch && statusMatch && ownerMatch;
    });
  }, [devices, ownerFilter, searchTerm, statusFilter]);

  const ownerOptions = useMemo(() => {
    return Array.from(new Set(devices.map(displayOwner))).sort((a, b) => a.localeCompare(b));
  }, [devices]);

  const summary = useMemo(() => {
    const approved = devices.filter((device) => device.latest_status === "Approved").length;
    const limited = devices.filter((device) => device.latest_status === "Approved with Limitation").length;
    const notRecommended = devices.filter((device) => device.latest_status === "Not Recommended").length;
    const lastUpload = devices
      .map((device) => new Date(device.last_seen))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => b - a)[0];
    return {
      total: devices.length,
      approved,
      limited,
      notRecommended,
      lastUpload: lastUpload ? formatMalaysiaTime(lastUpload.toISOString()) : "-"
    };
  }, [devices]);

  async function refresh() {
    try {
      const deviceResponse = await fetch(`${API_BASE_URL}/api/devices`);
      if (!deviceResponse.ok) throw new Error("API unavailable");
      const nextDevices = await deviceResponse.json();
      setApiOnline(true);
      setDevices(nextDevices.length ? nextDevices : [sampleDevice]);
      const nextSelected = nextDevices.find((device) => device.id === selectedDeviceId) || nextDevices[0];
      if (nextSelected) await loadDevice(nextSelected.id);
    } catch {
      setApiOnline(false);
      setDevices([sampleDevice]);
      setDeviceDetail(sampleDevice);
      setReport(sampleReport);
    }
  }

  async function loadDevice(deviceId) {
    setSelectedDeviceId(deviceId);
    setEditingOwner(false);
    setSaveMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/devices/${deviceId}`);
      if (!response.ok) throw new Error("Device unavailable");
      const detail = await response.json();
      setDeviceDetail(detail);
      setOwnerDraft(displayOwner(detail) === "Unassigned" ? "" : displayOwner(detail));
      if (detail.reports?.[0]) await loadReport(detail.reports[0].id);
    } catch {
      setDeviceDetail(sampleDevice);
      setReport(sampleReport);
      setOwnerDraft("");
    }
  }

  async function loadReport(reportId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}`);
      if (!response.ok) throw new Error("Report unavailable");
      setReport(await response.json());
    } catch {
      setReport(sampleReport);
    }
  }

  async function saveOwner() {
    if (!apiOnline) {
      setSaveMessage("Backend required to save client name.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/devices/${deviceDetail.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ media_owner: ownerDraft })
      });
      if (!response.ok) throw new Error("Save failed");
      const updated = await response.json();
      setDeviceDetail((current) => ({ ...current, media_owner: updated.media_owner }));
      setDevices((current) => current.map((device) => (device.id === updated.id ? updated : device)));
      setEditingOwner(false);
      setSaveMessage("Client saved.");
    } catch (error) {
      setSaveMessage(error.message || "Save failed.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LMX Device Certification Platform</p>
          <h1>Device Readiness Dashboard</h1>
        </div>
        <button className="icon-button" onClick={refresh} title="Refresh">
          <RefreshCw size={18} />
        </button>
      </header>

      <section className="status-row">
        <div>
          <span className={apiOnline ? "dot online" : "dot"} />
          {apiOnline ? "Backend connected" : "Showing sample data"}
        </div>
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">API docs</a>
      </section>

      <section className="apk-download-strip">
        <div>
          <strong>Android Agent APK</strong>
          <span>Install this app on Android test devices to upload certification reports.</span>
        </div>
        <a className="download-apk-button prominent" href={APK_DOWNLOAD_URL} download="lmx-android-agent-debug.apk">
          <Download size={18} />
          Download APK
        </a>
      </section>

      <SummaryCards summary={summary} />

      <DeviceList
        devices={filteredDevices}
        allDevices={devices}
        selectedId={selectedDevice?.id}
        searchTerm={searchTerm}
        statusFilter={statusFilter}
        ownerFilter={ownerFilter}
        ownerOptions={ownerOptions}
        onSearch={setSearchTerm}
        onStatusFilter={setStatusFilter}
        onOwnerFilter={setOwnerFilter}
        onSelect={loadDevice}
      />

      <section className="detail-grid">
        <DeviceDetail
          device={deviceDetail}
          report={report}
          editingOwner={editingOwner}
          ownerDraft={ownerDraft}
          saveMessage={saveMessage}
          onEdit={() => {
            setOwnerDraft(displayOwner(deviceDetail) === "Unassigned" ? "" : displayOwner(deviceDetail));
            setEditingOwner(true);
            setSaveMessage("");
          }}
          onCancel={() => setEditingOwner(false)}
          onOwnerChange={setOwnerDraft}
          onSave={saveOwner}
        />
        <ReportPage device={deviceDetail} report={report} />
        <DiagnosticHistory device={deviceDetail} onSelectReport={loadReport} />
      </section>
    </main>
  );
}

function SummaryCards({ summary }) {
  return (
    <section className="summary-cards">
      <MetricCard label="Total Devices" value={summary.total} />
      <MetricCard label="Approved" value={summary.approved} tone="pass" />
      <MetricCard label="Approved with Limitation" value={summary.limited} tone="warning" />
      <MetricCard label="Not Recommended" value={summary.notRecommended} tone="fail" />
      <MetricCard label="Last Upload Time" value={summary.lastUpload} helper="MYT (UTC+8)" wide />
    </section>
  );
}

function MetricCard({ label, value, helper = "", tone = "", wide = false }) {
  return (
    <section className={`metric-card ${tone} ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {helper && <small>{helper}</small>}
    </section>
  );
}

function DeviceList({
  devices,
  allDevices,
  selectedId,
  searchTerm,
  statusFilter,
  ownerFilter,
  ownerOptions,
  onSearch,
  onStatusFilter,
  onOwnerFilter,
  onSelect
}) {
  return (
    <section className="panel device-list full-width">
      <div className="panel-title row-title">
        <div>
          <LayoutDashboard size={18} />
          <h2>Device List</h2>
        </div>
        <span>{devices.length} of {allDevices.length} devices</span>
      </div>
      <div className="filters">
        <label className="search-box">
          <Search size={16} />
          <input value={searchTerm} onChange={(event) => onSearch(event.target.value)} placeholder="Search device name" />
        </label>
        <select value={statusFilter} onChange={(event) => onStatusFilter(event.target.value)}>
          <option>All</option>
          <option>Approved</option>
          <option>Approved with Limitation</option>
          <option>Not Recommended</option>
        </select>
        <select value={ownerFilter} onChange={(event) => onOwnerFilter(event.target.value)}>
          <option>All</option>
          {ownerOptions.map((owner) => <option key={owner}>{owner}</option>)}
        </select>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Media Owner / Client</th>
              <th>Device</th>
              <th>Platform</th>
              <th>Model</th>
              <th>OS</th>
              <th>WebView</th>
              <th>LMX App</th>
              <th>Status</th>
              <th>Score</th>
              <th>Last Check</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.id} className={device.id === selectedId ? "selected" : ""} onClick={() => onSelect(device.id)}>
                <td>{displayOwner(device)}</td>
                <td>{device.device_name}</td>
                <td>{device.platform}</td>
                <td>{device.manufacturer} {device.model}</td>
                <td>{device.os_version}</td>
                <td>{device.webview_version || "-"}</td>
                <td>{device.lmx_app_version || "-"}</td>
                <td><StatusPill status={device.latest_status} /></td>
                <td>{device.latest_score}</td>
                <td>{formatMalaysiaTime(device.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DeviceDetail({ device, report, editingOwner, ownerDraft, saveMessage, onEdit, onCancel, onOwnerChange, onSave }) {
  const checks = report?.raw_json?.checks || {};
  return (
    <section className="panel">
      <div className="panel-title">
        <FileText size={18} />
        <h2>Device Detail</h2>
      </div>
      <div className="summary-strip">
        <strong>{device.device_name}</strong>
        <span>{device.platform} - {device.manufacturer} {device.model}</span>
      </div>
      <div className="owner-editor">
        <div>
          <span className="label">Media Owner / Client</span>
          {editingOwner ? (
            <input value={ownerDraft} onChange={(event) => onOwnerChange(event.target.value)} placeholder="Client name" />
          ) : (
            <strong>{displayOwner(device)}</strong>
          )}
        </div>
        {editingOwner ? (
          <div className="button-row">
            <button onClick={onSave}><Save size={15} />Save</button>
            <button className="secondary" onClick={onCancel}>Cancel</button>
          </div>
        ) : (
          <button onClick={onEdit}><UserPen size={15} />Edit Client</button>
        )}
      </div>
      {saveMessage && <p className="save-message">{saveMessage}</p>}
      <h3>Device Compatibility</h3>
      <div className="check-grid">
        {deviceCompatibilityKeys.map((key) => <CheckRow key={key} label={checkLabels[key]} check={checks[key]} />)}
      </div>
      <h3>LMX Content Readiness</h3>
      <div className="check-grid">
        {lmxReadinessKeys.map((key) => <CheckRow key={key} label={checkLabels[key]} check={checks[key]} />)}
      </div>
    </section>
  );
}

function ReportPage({ device, report }) {
  const raw = report.raw_json || {};
  const checks = Object.values(raw.checks || {});
  const failed = checks.filter((check) => check.status === "FAIL");
  const limitations = checks.filter((check) => check.status === "WARNING");
  const finalRecommendation = report.final_recommendation || raw.final_recommendation || finalRecommendationFrom(report.final_status);
  const deviceSummary = report.device_report_summary || raw.device_report_summary || buildDeviceReportSummary(report, raw);

  return (
    <section className="panel report">
      <div className="panel-title">
        <Download size={18} />
        <h2>Report</h2>
      </div>
      <div className="report-head">
        <div>
          <p className="eyebrow">Device Certification Result</p>
          <h3>{report.final_status}</h3>
        </div>
        <div className="score">{report.score}</div>
      </div>
      <div className="result-grid">
        <section>
          <span>Final Recommendation</span>
          <strong>{finalRecommendation}</strong>
        </section>
      </div>
      <div className="export-row report-actions">
        <a href={`${API_BASE_URL}/api/reports/${report.id}/pdf`} target="_blank" rel="noreferrer">
          <Download size={16} />
          Download PDF
        </a>
        <a href={`${API_BASE_URL}/api/reports/${report.id}/docx`} target="_blank" rel="noreferrer">
          <FileText size={16} />
          Download DOCX
        </a>
        <button className="secondary" onClick={() => window.print()}>Print Report</button>
      </div>
      <DeviceReportSummary summary={deviceSummary} />
      <dl>
        <dt>Media Owner / Client</dt><dd>{displayOwner(device, raw)}</dd>
        <dt>Device</dt><dd>{raw.device_name}</dd>
        <dt>Platform</dt><dd>{raw.platform}</dd>
        <dt>Report Time</dt><dd>{formatMalaysiaTime(report.created_at)}</dd>
        <dt>Android Version</dt><dd>{raw.os_version}</dd>
        <dt>WebView Version</dt><dd>{raw.webview_version}</dd>
        <dt>RAM</dt><dd>{raw.ram_total_gb}GB</dd>
        <dt>Storage Available</dt><dd>{raw.storage_available_gb}GB</dd>
        <dt>LMX Content Version</dt><dd>{raw.lmx_app_version || "Not detected"}</dd>
      </dl>
      <h3>Device Compatibility</h3>
      <div className="check-grid">
        {deviceCompatibilityKeys.map((key) => <CheckRow key={key} label={checkLabels[key]} check={raw.checks?.[key]} />)}
      </div>
      <h3>LMX Content Readiness</h3>
      <div className="check-grid">
        {lmxReadinessKeys.map((key) => <CheckRow key={key} label={checkLabels[key]} check={raw.checks?.[key]} />)}
      </div>
      <h3>Failed Checks</h3>
      <ListOrNone items={failed.map((check) => check.message)} />
      <h3>Limitations</h3>
      <ListOrNone items={limitations.map((check) => check.message)} />
      <h3>Recommended Action</h3>
      <p><strong>{finalRecommendation}.</strong> {report.recommendations}</p>
      <div className="export-row">
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=html`} target="_blank" rel="noreferrer">HTML</a>
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=json`} target="_blank" rel="noreferrer">JSON</a>
      </div>
    </section>
  );
}

function DeviceReportSummary({ summary }) {
  return (
    <section className="report-summary">
      <h3>Device Report Summary</h3>
      <div className="summary-block">
        <span>Overall Summary</span>
        <p>{summary.overall_summary || "-"}</p>
      </div>
      <SummaryList title="Good Points" items={summary.good_points} tone="pass" />
      <SummaryList title="Warning Points" items={summary.warning_points} tone="warning" />
      <SummaryList title="Problem Points" items={summary.failed_points} tone="fail" />
      <SummaryList title="Likely Causes" items={summary.likely_causes} />
      <SummaryList title="Recommended Actions" items={summary.recommended_actions} />
    </section>
  );
}

function SummaryList({ title, items = [], tone = "" }) {
  return (
    <div className={`summary-block ${tone}`}>
      <span>{title}</span>
      <ListOrNone items={items} />
    </div>
  );
}

function DiagnosticHistory({ device, onSelectReport }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <FileText size={18} />
        <h2>Diagnostic History</h2>
      </div>
      <div className="history-list">
        {(device.reports || []).map((item) => (
          <button key={item.id} onClick={() => onSelectReport(item.id)}>
            <span>{formatMalaysiaTime(item.created_at)}</span>
            <strong>{item.final_status} - {item.score}</strong>
            <small>{item.summary}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

const deviceCompatibilityKeys = ["android_version", "ram", "storage", "webview", "network", "time_timezone"];
const lmxReadinessKeys = ["lmx_app_installed", "lmx_app_launch", "lmx_version", "programmatic_vast", "pull_to_content"];

const checkLabels = {
  android_version: "Android Version",
  ram: "RAM",
  storage: "Storage",
  webview: "WebView",
  network: "Network",
  time_timezone: "Time/Timezone",
  lmx_app_installed: "LMX App Installed",
  lmx_app_launch: "LMX App Launch",
  lmx_version: "LMX Version",
  programmatic_vast: "Programmatic/VAST Readiness",
  pull_to_content: "Pull To Content Readiness"
};

function CheckRow({ label, check }) {
  return (
    <div className="check-row">
      <span>{label}</span>
      <StatusPill status={check?.status || "UNKNOWN"} />
    </div>
  );
}

function StatusPill({ status }) {
  const key = String(status).toLowerCase().replaceAll(" ", "-");
  return <span className={`pill ${key}`}>{status}</span>;
}

function ListOrNone({ items }) {
  if (!items.length) return <p>None</p>;
  return <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>;
}

function displayOwner(device = {}, raw = {}) {
  return device.media_owner || raw.media_owner || raw.client_name || "Unassigned";
}

function finalRecommendationFrom(deviceStatus) {
  if (deviceStatus === "Approved") return "Certified for LMX Content";
  if (deviceStatus === "Approved with Limitation") return "Certified with Limitation";
  return "Not Recommended";
}

function buildDeviceReportSummary(report, raw) {
  const checks = raw.checks || {};
  const values = Object.values(checks);
  return {
    overall_summary: report.summary || "-",
    good_points: values.filter((check) => check.status === "PASS").map((check) => check.message),
    warning_points: values.filter((check) => check.status === "WARNING").map((check) => check.message),
    failed_points: values.filter((check) => check.status === "FAIL").map((check) => check.message),
    likely_causes: likelyCauses(checks),
    recommended_actions: recommendedActions(checks, report.recommendations)
  };
}

function likelyCauses(checks) {
  const map = {
    android_version: "Android OS version may be below the supported baseline for stable LMX Content deployment.",
    ram: "Low device memory may limit smooth HTML, URL, or VAST rendering.",
    storage: "Low available storage can prevent updates, cached content, or normal app operation.",
    webview: "Older Android System WebView versions may have limited compatibility with HTML, URL, or VAST playback.",
    network: "Network connectivity may be unavailable or unstable during validation.",
    time_timezone: "Incorrect device time or timezone can affect scheduled content and reporting.",
    lmx_app_installed: "LMX Content may not be installed on the device.",
    lmx_app_launch: "LMX Content may be installed but not launchable from Android.",
    lmx_version: "The LMX Content version could not be detected.",
    programmatic_vast: "Programmatic/VAST readiness may be limited by Android version, WebView, RAM, or network state.",
    pull_to_content: "The installed LMX Content version may be below the Pull To Content requirement."
  };
  const items = Object.entries(checks)
    .filter(([, check]) => ["WARNING", "FAIL"].includes(check.status))
    .map(([key]) => map[key])
    .filter(Boolean);
  return items.length ? Array.from(new Set(items)) : ["No likely causes identified from the current assessment."];
}

function recommendedActions(checks, recommendations) {
  const map = {
    android_version: "Upgrade the device OS or select a device running Android 11 or above where possible.",
    ram: "Use a device with at least 4GB RAM for best LMX Content readiness.",
    storage: "Free device storage or use a device with at least 5GB available storage.",
    webview: "Update Android System WebView where possible.",
    network: "Confirm the device has stable internet connectivity before deployment.",
    time_timezone: "Correct the device date, time, and timezone settings.",
    lmx_app_installed: "Install LMX Content package com.qruize.quad42.media.app.",
    lmx_app_launch: "Reinstall or update LMX Content, then confirm the app can launch.",
    lmx_version: "Install a supported LMX Content build and rerun certification.",
    programmatic_vast: "Update WebView and verify Android version, RAM, and internet connectivity.",
    pull_to_content: "Update LMX Content to Android version 2.9.1.2 native or newer, or Windows version 1.0.34 or newer."
  };
  const items = Object.entries(checks)
    .filter(([, check]) => ["WARNING", "FAIL"].includes(check.status))
    .map(([key]) => map[key])
    .filter(Boolean);
  if (items.length) return Array.from(new Set(items));
  return recommendations ? [recommendations] : ["No action required before deployment."];
}

function formatMalaysiaTime(timestamp) {
  if (!timestamp) return "-";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "-";
  const formatted = new Intl.DateTimeFormat("en-MY", {
    timeZone: "Asia/Kuala_Lumpur",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  }).format(date);
  return `${formatted.replace(/\b(am|pm)\b/i, (value) => value.toUpperCase())} MYT`;
}

createRoot(document.getElementById("root")).render(<App />);
