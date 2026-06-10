import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, FileText, LayoutDashboard, RefreshCw, Save, Search, UserPen } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sampleReport = {
  id: 1,
  device_id: 1,
  created_at: "2026-06-09T13:00:00Z",
  final_status: "Not Recommended",
  score: 25,
  summary: "Device is not recommended for LMX Content deployment until failed checks are resolved.",
  recommendations:
    "Available storage is below 2GB. Android System WebView is below version 120. Programmatic/VAST playback is not ready because WebView is below 120. Resolve failed checks and review limitations before production deployment.",
  lmx_app_status: {
    status: "PASS",
    installed: true,
    package_name: "com.qruize.quad42.media.app",
    version: "2.9.3.6 native",
    launchable: true
  },
  content_download_status: {
    status: "PASS",
    media_folder_found: true,
    downloaded_file_count: 7,
    download_size_bytes: 133169152,
    download_size_readable: "127 MB",
    last_content_update: "2026-06-10 19:32"
  },
  playback_validation: {
    status: "PASS",
    audit_file_found: true,
    total_playback_records: 1250,
    last_playback_time: "2026-06-10 21:08",
    last_played_content: "Food_Panda_KLS_19062020.mp4",
    playlist: "Chennai Test",
    unique_content_count: 6
  },
  log_validation: {
    status: "WARNING",
    log_folder_found: true,
    log_files_found: true,
    crash_logs_found: true,
    latest_log_update: "2026-06-10 22:04",
    latest_crash_timestamp: "2026-06-10 22:04"
  },
  overall_health_status: "YELLOW",
  overall_health: { status: "YELLOW", recommendation: "Playback active but crash logs found" },
  troubleshooting_recommendation:
    "Review crash logs. If playback is stable, monitor device. If crashes continue, restart player or update LMX Content.",
  raw_json: {
    device_name: "Solum Box",
    platform: "Android",
    manufacturer: "Solum",
    model: "Box",
    media_owner: "",
    os_version: "15",
    webview_version: "106.0.5249.126",
    lmx_app_version: "1.4.2",
    ram_total_gb: 4,
    storage_available_gb: 1.2,
    checks: {
      android_version: { status: "PASS", message: "Android version is supported." },
      ram: { status: "PASS", message: "RAM is sufficient." },
      storage: { status: "FAIL", message: "Available storage is below 2GB." },
      webview: { status: "FAIL", message: "Android System WebView is below version 120." },
      network: { status: "PASS", message: "Internet connectivity is available." },
      time_timezone: { status: "PASS", message: "System date, time, and timezone are present." },
      lmx_app_installed: { status: "PASS", message: "LMX Content app is installed." },
      lmx_app_launch: { status: "PASS", message: "LMX Content app is launchable." },
      programmatic_vast: {
        status: "FAIL",
        message: "Programmatic/VAST playback is not ready because WebView is below 120."
      }
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
  latest_score: 25,
  latest_overall_health_status: "YELLOW",
  latest_content_download_status: "PASS",
  latest_playback_status: "PASS",
  latest_log_status: "WARNING",
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
      if (detail.reports?.[0]) {
        await loadReport(detail.reports[0].id);
      }
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
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          API docs
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
          {ownerOptions.map((owner) => (
            <option key={owner}>{owner}</option>
          ))}
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
              <th>Overall Health</th>
              <th>Content Download</th>
              <th>Playback</th>
              <th>Logs</th>
              <th>Status</th>
              <th>Score</th>
              <th>Last Check</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr
                key={device.id}
                className={device.id === selectedId ? "selected" : ""}
                onClick={() => onSelect(device.id)}
              >
                <td>{displayOwner(device)}</td>
                <td>{device.device_name}</td>
                <td>{device.platform}</td>
                <td>{device.manufacturer} {device.model}</td>
                <td>{device.os_version}</td>
                <td>{device.webview_version || "-"}</td>
                <td>{device.lmx_app_version || "-"}</td>
                <td><HealthPill status={device.latest_overall_health_status || "UNKNOWN"} /></td>
                <td><StatusPill status={device.latest_content_download_status || "UNKNOWN"} /></td>
                <td><StatusPill status={device.latest_playback_status || "UNKNOWN"} /></td>
                <td><StatusPill status={device.latest_log_status || "UNKNOWN"} /></td>
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
      <div className="check-grid">
        {Object.entries(checkLabels).map(([key, label]) => (
          <CheckRow key={key} label={label} check={checks[key]} />
        ))}
      </div>
    </section>
  );
}

function ReportPage({ device, report }) {
  const raw = report.raw_json || {};
  const checks = Object.values(raw.checks || {});
  const failed = checks.filter((check) => check.status === "FAIL");
  const limitations = checks.filter((check) => check.status === "WARNING");
  const lmxApp = healthSection(report, raw, "lmx_app_status");
  const content = healthSection(report, raw, "content_download_status");
  const playback = healthSection(report, raw, "playback_validation");
  const logs = healthSection(report, raw, "log_validation");
  const overallStatus = report.overall_health_status || raw.overall_health_status || "UNKNOWN";
  const recommendation = report.troubleshooting_recommendation || raw.troubleshooting_recommendation || report.recommendations;

  return (
    <section className="panel report">
      <div className="panel-title">
        <Download size={18} />
        <h2>Report</h2>
      </div>
      <div className="report-head">
        <div>
          <p className="eyebrow">Compatibility Result</p>
          <h3>{report.final_status}</h3>
        </div>
        <div className="score">{report.score}</div>
      </div>
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
      <h3>LMX Playback Health</h3>
      <div className="health-grid">
        <HealthCard title="LMX App Status" status={statusOf(lmxApp)} items={[
          ["Installed", yesNo(valueOf(lmxApp, "installed"))],
          ["Version", valueOf(lmxApp, "version") || valueOf(lmxApp, "version_name") || raw.lmx_app_version || "-"],
          ["Launchable", yesNo(valueOf(lmxApp, "launchable"))]
        ]} />
        <HealthCard title="Content Download Status" status={statusOf(content)} items={[
          ["Media Folder", yesNo(valueOf(content, "media_folder_found") ?? valueOf(content, "media_folder_exists"))],
          ["Files", valueOf(content, "downloaded_file_count") ?? "-"],
          ["Size", valueOf(content, "download_size_readable") || readableBytes(valueOf(content, "download_size_bytes") ?? valueOf(content, "total_download_size_bytes"))],
          ["Last Update", valueOf(content, "last_content_update") || valueOf(content, "last_content_update_timestamp") || "-"]
        ]} />
        <HealthCard title="Playback Validation" status={statusOf(playback)} items={[
          ["Audit File", yesNo(valueOf(playback, "audit_file_found") ?? valueOf(playback, "audit_file_exists"))],
          ["Records", valueOf(playback, "total_playback_records") ?? "-"],
          ["Last Playback", valueOf(playback, "last_playback_time") || valueOf(playback, "last_playback_date_time") || "-"],
          ["Last Content", valueOf(playback, "last_played_content") || "-"]
        ]} />
        <HealthCard title="Log Validation" status={statusOf(logs)} items={[
          ["Log Files", yesNo(valueOf(logs, "log_files_found"))],
          ["Crash Logs", yesNo(valueOf(logs, "crash_logs_found"))],
          ["Latest Log", valueOf(logs, "latest_log_update") || valueOf(logs, "latest_log_update_timestamp") || "-"],
          ["Latest Crash", valueOf(logs, "latest_crash_timestamp") || valueOf(logs, "latest_crash_log_timestamp") || "-"]
        ]} />
        <section className="health-card overall-health">
          <div className="health-card-head">
            <strong>Overall Health Status</strong>
            <HealthPill status={overallStatus} />
          </div>
          <p>{healthSummary(report.overall_health) || healthSummary(raw.overall_health) || recommendation}</p>
        </section>
      </div>
      <h3>Failed Checks</h3>
      <ListOrNone items={failed.map((check) => check.message)} />
      <h3>Limitations</h3>
      <ListOrNone items={limitations.map((check) => check.message)} />
      <h3>Recommended Action</h3>
      <p>{recommendation}</p>
      <div className="export-row">
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=html`} target="_blank" rel="noreferrer">HTML</a>
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=json`} target="_blank" rel="noreferrer">JSON</a>
      </div>
    </section>
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

const checkLabels = {
  android_version: "Android Version",
  ram: "RAM",
  storage: "Storage",
  webview: "WebView",
  network: "Network",
  time_timezone: "Time/Timezone",
  lmx_app_installed: "LMX App Installed",
  lmx_app_launch: "LMX App Launch",
  programmatic_vast: "Programmatic/VAST Readiness"
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

function HealthPill({ status }) {
  const key = String(status || "UNKNOWN").toLowerCase();
  return <span className={`health-pill ${key}`}>{status || "UNKNOWN"}</span>;
}

function HealthCard({ title, status, items }) {
  return (
    <section className="health-card">
      <div className="health-card-head">
        <strong>{title}</strong>
        <StatusPill status={status || "UNKNOWN"} />
      </div>
      <dl>
        {items.map(([label, value]) => (
          <React.Fragment key={label}>
            <dt>{label}</dt>
            <dd>{value ?? "-"}</dd>
          </React.Fragment>
        ))}
      </dl>
    </section>
  );
}

function ListOrNone({ items }) {
  if (!items.length) return <p>None</p>;
  return <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>;
}

function displayOwner(device = {}, raw = {}) {
  return device.media_owner || raw.media_owner || raw.client_name || "Unassigned";
}

function healthSection(report, raw, key) {
  return report?.[key] || raw?.[key] || null;
}

function statusOf(section) {
  return valueOf(section, "status") || "UNKNOWN";
}

function valueOf(section, key) {
  if (!section || typeof section !== "object") return undefined;
  return section[key];
}

function yesNo(value) {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "Unknown";
}

function readableBytes(value) {
  const size = Number(value || 0);
  if (!size) return "-";
  return `${Math.round(size / 1024 / 1024)} MB`;
}

function healthSummary(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return value.recommendation || value.message || value.status || "";
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
