import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, FileText, LayoutDashboard, RefreshCw } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sampleReport = {
  id: 1,
  device_id: 1,
  created_at: "2026-06-09T13:00:00",
  final_status: "Not Recommended",
  score: 25,
  summary: "Device is not recommended for LMX Content deployment until failed checks are resolved.",
  recommendations:
    "Available storage is below 2GB. Android System WebView is below version 120. Programmatic/VAST playback is not ready because WebView is below 120. Resolve failed checks and review limitations before production deployment.",
  raw_json: {
    device_name: "Solum Box",
    platform: "Android",
    manufacturer: "Solum",
    model: "Box",
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
  os_version: "15",
  webview_version: "106.0.5249.126",
  lmx_app_version: "1.4.2",
  latest_status: "Not Recommended",
  latest_score: 25,
  last_seen: "2026-06-09T13:00:00",
  reports: [sampleReport]
};

function App() {
  const [devices, setDevices] = useState([sampleDevice]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(1);
  const [selectedReportId, setSelectedReportId] = useState(1);
  const [deviceDetail, setDeviceDetail] = useState(sampleDevice);
  const [report, setReport] = useState(sampleReport);
  const [apiOnline, setApiOnline] = useState(false);

  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) || devices[0],
    [devices, selectedDeviceId]
  );

  async function refresh() {
    try {
      const deviceResponse = await fetch(`${API_BASE_URL}/api/devices`);
      if (!deviceResponse.ok) throw new Error("API unavailable");
      const nextDevices = await deviceResponse.json();
      setApiOnline(true);
      setDevices(nextDevices.length ? nextDevices : [sampleDevice]);
      if (nextDevices[0]) {
        setSelectedDeviceId(nextDevices[0].id);
        await loadDevice(nextDevices[0].id);
      }
    } catch {
      setApiOnline(false);
      setDevices([sampleDevice]);
      setDeviceDetail(sampleDevice);
      setReport(sampleReport);
    }
  }

  async function loadDevice(deviceId) {
    setSelectedDeviceId(deviceId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/devices/${deviceId}`);
      if (!response.ok) throw new Error("Device unavailable");
      const detail = await response.json();
      setDeviceDetail(detail);
      if (detail.reports?.[0]) {
        setSelectedReportId(detail.reports[0].id);
        await loadReport(detail.reports[0].id);
      }
    } catch {
      setDeviceDetail(sampleDevice);
      setReport(sampleReport);
    }
  }

  async function loadReport(reportId) {
    setSelectedReportId(reportId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}`);
      if (!response.ok) throw new Error("Report unavailable");
      setReport(await response.json());
    } catch {
      setReport(sampleReport);
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

      <section className="grid">
        <DeviceList devices={devices} selectedId={selectedDevice?.id} onSelect={loadDevice} />
        <DeviceDetail device={deviceDetail} report={report} onSelectReport={loadReport} />
        <ReportPage report={report} />
      </section>
    </main>
  );
}

function DeviceList({ devices, selectedId, onSelect }) {
  return (
    <section className="panel device-list">
      <div className="panel-title">
        <LayoutDashboard size={18} />
        <h2>Device List</h2>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
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
              <tr
                key={device.id}
                className={device.id === selectedId ? "selected" : ""}
                onClick={() => onSelect(device.id)}
              >
                <td>{device.device_name}</td>
                <td>{device.platform}</td>
                <td>{device.manufacturer} {device.model}</td>
                <td>{device.os_version}</td>
                <td>{device.webview_version || "-"}</td>
                <td>{device.lmx_app_version || "-"}</td>
                <td><StatusPill status={device.latest_status} /></td>
                <td>{device.latest_score}</td>
                <td>{formatDate(device.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DeviceDetail({ device, report, onSelectReport }) {
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
      <div className="check-grid">
        {Object.entries(checkLabels).map(([key, label]) => (
          <CheckRow key={key} label={label} check={checks[key]} />
        ))}
      </div>
      <div className="reports">
        <h3>Diagnostic History</h3>
        {(device.reports || []).map((item) => (
          <button key={item.id} onClick={() => onSelectReport(item.id)}>
            {formatDate(item.created_at)} - {item.final_status} - {item.score}
          </button>
        ))}
      </div>
    </section>
  );
}

function ReportPage({ report }) {
  const raw = report.raw_json || {};
  const checks = Object.values(raw.checks || {});
  const failed = checks.filter((check) => check.status === "FAIL");
  const limitations = checks.filter((check) => check.status === "WARNING");

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
        <dt>Device</dt><dd>{raw.device_name}</dd>
        <dt>Platform</dt><dd>{raw.platform}</dd>
        <dt>Android Version</dt><dd>{raw.os_version}</dd>
        <dt>WebView Version</dt><dd>{raw.webview_version}</dd>
        <dt>RAM</dt><dd>{raw.ram_total_gb}GB</dd>
        <dt>Storage Available</dt><dd>{raw.storage_available_gb}GB</dd>
        <dt>LMX Content Version</dt><dd>{raw.lmx_app_version || "Not detected"}</dd>
      </dl>
      <h3>Failed Checks</h3>
      <ListOrNone items={failed.map((check) => check.message)} />
      <h3>Limitations</h3>
      <ListOrNone items={limitations.map((check) => check.message)} />
      <h3>Recommended Action</h3>
      <p>{report.recommendations}</p>
      <div className="export-row">
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=html`} target="_blank" rel="noreferrer">HTML</a>
        <a href={`${API_BASE_URL}/api/export/${report.id}?format=json`} target="_blank" rel="noreferrer">JSON</a>
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

function ListOrNone({ items }) {
  if (!items.length) return <p>None</p>;
  return <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>;
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

createRoot(document.getElementById("root")).render(<App />);
