import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Download,
  Eye,
  FileText,
  Info,
  Monitor,
  MoreVertical,
  Printer,
  RefreshCw,
  Save,
  ShieldCheck,
  Smartphone,
  TriangleAlert,
  UserPen,
  XCircle
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const APK_DOWNLOAD_URL = "/downloads/app-debug.apk";
const WINDOWS_AGENT_DOWNLOAD_URL = "/downloads/LMX-Windows-Certification.exe";

const sampleReport = {
  id: 1,
  device_id: 1,
  created_at: "2026-06-09T13:00:00Z",
  final_status: "Not Recommended",
  score: 75,
  final_recommendation: "Not Recommended",
  device_report_summary: {
    overall_summary: "Device is not recommended for LMX Content deployment until failed checks are resolved.",
    good_points: [
      "Android 11 or above is supported.",
      "RAM is sufficient.",
      "Internet connectivity is available.",
      "System date, time, and timezone are present.",
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
    cpu_architecture: "arm64-v8a",
    screen_resolution: "1920x1080",
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
    score_label: "Limited",
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
  latest_score: 75,
  last_seen: "2026-06-09T13:00:00Z",
  reports: [sampleReport]
};

function App() {
  const [devices, setDevices] = useState([sampleDevice]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [deviceDetail, setDeviceDetail] = useState(sampleDevice);
  const [report, setReport] = useState(sampleReport);
  const [apiOnline, setApiOnline] = useState(false);
  const [editingOwner, setEditingOwner] = useState(false);
  const [ownerDraft, setOwnerDraft] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

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
      const nextSelected = (selectedDeviceId && nextDevices.find((device) => device.id === selectedDeviceId)) || nextDevices[0];
      if (nextSelected) await loadDevice(nextSelected.id);
    } catch {
      setApiOnline(false);
      setDevices([sampleDevice]);
      setDeviceDetail(sampleDevice);
      setReport(sampleReport);
    }
  }

  async function loadDevice(deviceId) {
    setSelectedDeviceId(Number(deviceId));
    setEditingOwner(false);
    setSaveMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/devices/${deviceId}`);
      if (!response.ok) throw new Error("Device unavailable");
      const detail = await response.json();
      setDeviceDetail(detail);
      setOwnerDraft(displayOwner(detail) === "Unassigned" ? "" : displayOwner(detail));
      if (detail.reports?.[0]) {
        setReport(detail.reports[0]);
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

  useEffect(() => {
    if (selectedDevice?.id && selectedDevice.id !== deviceDetail?.id) {
      loadDevice(selectedDevice.id);
    }
  }, [selectedDevice?.id, deviceDetail?.id]);

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <div className="brand-mark">
            <ShieldCheck size={30} />
          </div>
          <div>
            <p className="eyebrow">LMX Device Certification Platform</p>
            <h1>Device Certification Dashboard</h1>
          </div>
        </div>
        <div className="header-actions">
          <label>
            <span>Current Device</span>
            <select value={selectedDevice?.id || ""} onChange={(event) => loadDevice(event.target.value)}>
              {devices.map((device) => (
                <option key={device.id} value={device.id}>{device.device_name}</option>
              ))}
            </select>
          </label>
          <button className="secondary icon-button" onClick={refresh} title="Refresh">
            <RefreshCw size={17} />
          </button>
          <a className="top-action" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
            <FileText size={16} />
            API Docs
          </a>
          <div className="agent-downloads" aria-label="Certification Agents">
            <span>Certification Agents</span>
            <a className="top-action" href={APK_DOWNLOAD_URL} download="lmx-android-agent-debug.apk" title="Download Android Agent">
              <Smartphone size={16} />
              Android Agent
            </a>
            <a className="top-action" href={WINDOWS_AGENT_DOWNLOAD_URL} download="LMX-Windows-Certification.exe" title="Download Windows Agent">
              <Monitor size={16} />
              Windows Agent
            </a>
          </div>
        </div>
      </header>

      <ExecutiveSummary report={report} apiOnline={apiOnline} />
      <CertificationConclusion report={report} />
      <div className="split-grid split-grid-halves">
        <DeviceInformation
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
        <CompatibilityAssessment report={report} />
      </div>
      <DeviceReportSummary report={report} />
      <DeploymentReadiness report={report} />
      <DeviceHistory device={deviceDetail} report={report} onSelectReport={loadReport} />

      <footer className="dashboard-footer">
        <strong>Developed by Grympha</strong>
        <span>&copy; 2026 Grympha. Internal Use Only.</span>
      </footer>
    </main>
  );
}

function ExecutiveSummary({ report, apiOnline }) {
  const raw = report.raw_json || {};
  const checks = raw.checks || {};
  const primaryReadinessKey = isWindows(raw) ? "lmx_version" : "programmatic_vast";
  return (
    <section className="section-card executive-summary">
      <SectionHeader title="Executive Summary">
        <div className="backend-status">
          <span className={apiOnline ? "dot online" : "dot"} />
          {apiOnline ? "Backend Connected" : "Showing Sample Data"}
        </div>
      </SectionHeader>
      <div className="executive-grid">
        <SummaryCard
          icon={<ShieldCheck size={24} />}
          label="Device Certification Result"
          value={report.final_status}
          tone={statusTone(report.final_status)}
        />
        <SummaryCard
          icon={<BarChart3 size={24} />}
          label="Certification Score"
          value={`${report.score} / 100`}
          helper={scoreLabel(report, raw)}
          tone={scoreTone(report.score)}
        />
        <SummaryCard
          icon={<ClipboardCheck size={24} />}
          label="LMX Version Readiness"
          value={checks[primaryReadinessKey]?.status || "UNKNOWN"}
          tone={statusTone(checks[primaryReadinessKey]?.status)}
        />
        <SummaryCard
          icon={<FileText size={24} />}
          label="Pull To Content Readiness"
          value={checks.pull_to_content?.status || "UNKNOWN"}
          tone={statusTone(checks.pull_to_content?.status)}
        />
      </div>
    </section>
  );
}

function CertificationConclusion({ report }) {
  const raw = report.raw_json || {};
  const finalRecommendation = report.final_recommendation || raw.final_recommendation || finalRecommendationFrom(report.final_status);
  return (
    <section className={`section-card conclusion-card ${statusTone(report.final_status)}`}>
      <div>
        <span>Conclusion</span>
        <strong>{finalRecommendation}</strong>
        <p>{conclusionText(report.final_status)}</p>
      </div>
      <ExportActions reportId={report.id} iconOnly />
    </section>
  );
}

function SummaryCard({ icon, label, value, helper, tone = "", wide = false, children }) {
  return (
    <article className={`summary-card ${tone} ${wide ? "wide" : ""}`}>
      {icon && <div className="summary-icon">{icon}</div>}
      <div className="summary-content">
        <span>{label}</span>
        <strong>{value || "-"}</strong>
        {helper && <small>{helper}</small>}
        {children}
      </div>
    </article>
  );
}

function DeviceInformation({ device, report, editingOwner, ownerDraft, saveMessage, onEdit, onCancel, onOwnerChange, onSave }) {
  const raw = report.raw_json || {};
  const rows = deviceInfoRows(raw, device, report);

  return (
    <section className="section-card">
      <SectionHeader title="Device Information">
        <PlatformBadge platform={raw.platform || device.platform} />
      </SectionHeader>
      <div className="owner-row compact-owner">
        <div>
          <span>Media Owner / Client</span>
          {editingOwner ? (
            <input value={ownerDraft} onChange={(event) => onOwnerChange(event.target.value)} placeholder="Client name" />
          ) : (
            <strong>{displayOwner(device, raw)}</strong>
          )}
        </div>
        {editingOwner ? (
          <div className="button-row">
            <button onClick={onSave}><Save size={15} />Save</button>
            <button className="secondary" onClick={onCancel}>Cancel</button>
          </div>
        ) : (
          <button className="secondary" onClick={onEdit}><UserPen size={15} />Edit Client</button>
        )}
      </div>
      {saveMessage && <p className="save-message">{saveMessage}</p>}
      <div className="info-grid">
        {rows.map(([label, value]) => (
          <InfoItem key={label} label={label} value={value || "-"} />
        ))}
      </div>
    </section>
  );
}

function CompatibilityAssessment({ report }) {
  const raw = report.raw_json || {};
  const checks = raw.checks || {};
  const keys = (isWindows(raw) ? windowsCompatibilityKeys : [...deviceCompatibilityKeys, ...lmxReadinessKeys])
    .filter((key) => checkLabels[key]);
  return (
    <section className="section-card">
      <SectionHeader title="Device Compatibility" />
      <div className="assessment-grid">
        {keys.map((key) => (
          <AssessmentCard key={key} label={checkLabels[key]} check={checks[key]} />
        ))}
      </div>
    </section>
  );
}

function DeviceReportSummary({ report }) {
  const raw = report.raw_json || {};
  const summary = report.device_report_summary || raw.device_report_summary || buildDeviceReportSummary(report, raw);
  const displaySummary = sanitizeSummaryForPlatform(summary, raw);
  return (
    <section className="section-card report-summary-section">
      <SectionHeader title="Device Report Summary" />
      <div className="summary-focus">
        <span>Overall Summary</span>
        <p>{displaySummary.overall_summary || "-"}</p>
      </div>
      <div className="summary-grid">
        <SummaryList title="Strengths" items={displaySummary.good_points} tone="pass" />
        <SummaryList title="Warnings" items={displaySummary.warning_points} tone="warning" />
        <SummaryList title="Problems" items={displaySummary.failed_points} tone="fail" />
        <SummaryList title="Recommended Actions" items={displaySummary.recommended_actions} tone="neutral" />
      </div>
    </section>
  );
}

function DeploymentReadiness({ report }) {
  const raw = report.raw_json || {};
  const readiness = raw.deployment_readiness;
  if (!isWindows(raw) || !readiness) return null;
  return (
    <section className="section-card">
      <SectionHeader title="Deployment Readiness" />
      <div className="assessment-grid deployment-grid">
        {Object.entries(readiness).map(([key, check]) => (
          <AssessmentCard key={key} label={deploymentLabels[key] || key} check={check} />
        ))}
      </div>
    </section>
  );
}

function DeviceHistory({ device, report, onSelectReport }) {
  const reports = device.reports?.length ? device.reports : [report];
  return (
    <section className="section-card history-card">
      <SectionHeader title="Device History" />
      <div className="history-table-wrap">
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Device</th>
              <th>Result</th>
              <th>Score</th>
              <th>Recommendation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((item) => (
              <tr key={item.id}>
                <td>{formatMalaysiaTime(item.created_at)}</td>
                <td>
                  <div className="device-cell">
                    <span>{device.device_name}</span>
                    <PlatformBadge platform={device.platform || report.raw_json?.platform} />
                  </div>
                </td>
                <td><StatusPill status={item.final_status} /></td>
                <td>{item.score} / 100</td>
                <td>{item.final_recommendation || report.final_recommendation || "-"}</td>
                <td className="table-actions">
                  <button className="table-button" onClick={() => onSelectReport(item.id)}>
                    <Eye size={15} />
                    View Report
                  </button>
                  <button className="ghost-icon" title="More actions">
                    <MoreVertical size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ExportActions({ reportId, iconOnly = false }) {
  return (
    <div className={`export-actions ${iconOnly ? "icon-only" : ""}`}>
      <a href={`${API_BASE_URL}/api/reports/${reportId}/pdf`} target="_blank" rel="noreferrer" title="Download PDF" aria-label="Download PDF">
        <Download size={16} />
        {!iconOnly && "Download PDF"}
      </a>
      <a href={`${API_BASE_URL}/api/reports/${reportId}/docx`} target="_blank" rel="noreferrer" title="Download DOCX" aria-label="Download DOCX">
        <FileText size={16} />
        {!iconOnly && "Download DOCX"}
      </a>
      <button className="secondary" onClick={() => window.print()} title="Print Report" aria-label="Print Report">
        <Printer size={16} />
        {!iconOnly && "Print Report"}
      </button>
    </div>
  );
}

function SectionHeader({ title, children }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div className="info-item">
      {label.toLowerCase().includes("windows") || label.toLowerCase().includes("computer") ? <Monitor size={15} /> : <Smartphone size={15} />}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PlatformBadge({ platform }) {
  const label = String(platform || "Android").toUpperCase();
  return <span className={`platform-badge ${label.toLowerCase()}`}>{label}</span>;
}

function AssessmentCard({ label, check }) {
  const status = check?.status || "UNKNOWN";
  return (
    <article className={`assessment-card ${statusTone(status)}`}>
      <div>
        <StatusIcon status={status} />
        <strong>{label}</strong>
      </div>
      <StatusPill status={status} />
    </article>
  );
}

function SummaryList({ title, items = [], tone = "", wide = false }) {
  return (
    <article className={`summary-list ${tone} ${wide ? "wide" : ""}`}>
      <h3>{title}</h3>
      <ListOrNone items={items} />
    </article>
  );
}

function StatusPill({ status }) {
  const key = String(status || "UNKNOWN").toLowerCase().replaceAll(" ", "-");
  return <span className={`pill ${key}`}>{status || "UNKNOWN"}</span>;
}

function StatusIcon({ status }) {
  const tone = statusTone(status);
  if (tone === "pass") return <CheckCircle2 className="status-icon pass" size={17} />;
  if (tone === "warning") return <TriangleAlert className="status-icon warning" size={17} />;
  if (tone === "fail") return <XCircle className="status-icon fail" size={17} />;
  return <Info className="status-icon neutral" size={17} />;
}

function ListOrNone({ items }) {
  if (!items?.length) return <p className="empty-text">None</p>;
  return <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>;
}

const deviceCompatibilityKeys = ["android_version", "ram", "storage", "webview", "network", "time_timezone"];
const lmxReadinessKeys = ["lmx_app_installed", "lmx_app_launch", "programmatic_vast", "pull_to_content"];
const windowsCompatibilityKeys = [
  "windows_os",
  "cpu",
  "ram",
  "storage",
  "gpu",
  "network",
  "time_timezone",
  "lmx_app_installed",
  "lmx_version",
  "lmx_app_launch",
  "pull_to_content"
];

const checkLabels = {
  android_version: "Android Version",
  windows_os: "Windows Version",
  cpu: "CPU",
  ram: "RAM",
  storage: "Storage",
  gpu: "GPU",
  webview: "WebView",
  network: "Network",
  time_timezone: "Time / Timezone",
  lmx_app_installed: "LMX Installed",
  lmx_app_launch: "LMX Launch",
  lmx_version: "LMX Version",
  programmatic_vast: "Programmatic / VAST Readiness",
  pull_to_content: "Pull To Content Readiness"
};

const deploymentLabels = {
  auto_login: "Auto Login",
  auto_startup: "Auto Startup",
  power_settings: "Power Settings",
  display_scaling: "Display Scaling",
  wake_timers: "Wake Timers",
  windows_update_status: "Windows Update Status"
};

function deviceInfoRows(raw, device, report) {
  if (isWindows(raw)) {
    const manufacturer = normalizeWindowsHardwareName(raw.manufacturer || device.manufacturer);
    const model = normalizeWindowsHardwareName(raw.model || device.model);
    return [
      ["Computer Name", raw.computer_name || raw.device_name || device.device_name],
      ["Manufacturer", manufacturer],
      ["Model", model],
      ["Windows Edition", raw.windows_edition],
      ["Windows Version", formatWindowsVersion(raw, device)],
      ["System Type", raw.system_type],
      ["CPU", raw.cpu],
      ["CPU Architecture", raw.cpu_architecture],
      ["RAM", gb(raw.ram_total_gb)],
      ["Storage Available", gb(raw.storage_available_gb)],
      ["GPU", raw.gpu],
      ["Screen Resolution", raw.screen_resolution],
      ["IP Address", raw.ip_address],
      ["Timezone", raw.timezone],
      ["LMX Version", raw.lmx_app_version || device.lmx_app_version],
      ["Report Date", formatMalaysiaTime(report.created_at)]
    ];
  }
  return [
    ["Device Name", raw.device_name || device.device_name],
    ["Manufacturer", raw.manufacturer || device.manufacturer],
    ["Model", raw.model || device.model],
    ["Android Version", raw.os_version || device.os_version],
    ["CPU Architecture", raw.cpu_architecture],
    ["RAM", gb(raw.ram_total_gb)],
    ["Available Storage", gb(raw.storage_available_gb)],
    ["Screen Resolution", raw.screen_resolution],
    ["WebView Version", raw.webview_version || device.webview_version],
    ["LMX Version", raw.lmx_app_version || device.lmx_app_version],
    ["Report Date", formatMalaysiaTime(report.created_at)]
  ];
}

function normalizeWindowsHardwareName(value) {
  const text = String(value || "").trim();
  if (["system manufacturer", "system product name"].includes(text.toLowerCase())) {
    return "Custom Built PC";
  }
  return text;
}

function formatWindowsVersion(raw = {}, device = {}) {
  const edition = String(raw.windows_edition || raw.os_version || device.os_version || "").toLowerCase();
  const version = String(raw.windows_version || "");
  const build = Number.parseInt(raw.windows_build_number || version.split(".").pop(), 10);
  if (!build) return raw.windows_version || raw.os_version || device.os_version || "-";

  if (edition.includes("windows 11") || build >= 22000) {
    if (build >= 26100) return `Windows 11 24H2 - Build ${build}`;
    if (build >= 22631) return `Windows 11 23H2 - Build ${build}`;
    if (build >= 22621) return `Windows 11 22H2 - Build ${build}`;
    return `Windows 11 21H2 - Build ${build}`;
  }

  if (build >= 19045) return `Windows 10 22H2 - Build ${build}`;
  if (build >= 19044) return `Windows 10 21H2 - Build ${build}`;
  if (build >= 19043) return `Windows 10 21H1 - Build ${build}`;
  if (build >= 19042) return `Windows 10 20H2 - Build ${build}`;
  return `Windows 10 - Build ${build}`;
}

function isWindows(raw = {}) {
  return String(raw.platform || "").toLowerCase() === "windows";
}

function displayOwner(device = {}, raw = {}) {
  return device.media_owner || raw.media_owner || raw.client_name || "Unassigned";
}

function finalRecommendationFrom(deviceStatus) {
  if (deviceStatus === "Approved") return "Certified for LMX Content";
  if (deviceStatus === "Approved with Limitation") return "Certified with Limitation";
  return "Not Recommended";
}

function scoreLabel(report, raw = {}) {
  return raw.score_label || scoreLabelFromValue(report.score);
}

function scoreLabelFromValue(score) {
  if (score >= 95) return "Excellent";
  if (score >= 80) return "Good";
  if (score >= 60) return "Limited";
  return "Not Recommended";
}

function scoreTone(score) {
  if (score >= 95) return "pass";
  if (score >= 80) return "good";
  if (score >= 60) return "warning";
  return "fail";
}

function statusTone(status = "") {
  const value = String(status).toLowerCase();
  if (value.includes("approved") || value === "pass" || value.includes("certified for")) return "pass";
  if (value.includes("limitation") || value === "warning") return "warning";
  if (value.includes("not recommended") || value === "fail") return "fail";
  return "neutral";
}

function conclusionText(status) {
  if (status === "Approved") {
    return "This device meets all LMX Content certification requirements and is suitable for deployment.";
  }
  if (status === "Approved with Limitation") {
    return "This device can be used for LMX Content but has one or more limitations that should be reviewed before deployment.";
  }
  return "This device does not meet the minimum LMX Content requirements and is not recommended for deployment.";
}

function buildDeviceReportSummary(report, raw) {
  const checks = raw.checks || {};
  const values = Object.values(checks);
  return {
    overall_summary: report.summary || "-",
    good_points: values.filter((check) => check.status === "PASS").map((check) => check.message),
    warning_points: values.filter((check) => check.status === "WARNING").map((check) => check.message),
    failed_points: values.filter((check) => check.status === "FAIL").map((check) => check.message),
    likely_causes: likelyCauses(checks, raw),
    recommended_actions: recommendedActions(checks, report.recommendations, raw)
  };
}

function likelyCauses(checks, raw = {}) {
  const windows = isWindows(raw);
  const map = {
    android_version: "Android OS version may be below the supported baseline for stable LMX Content deployment.",
    windows_os: "Windows edition or version may be unsupported for LMX Content deployment.",
    cpu: "CPU class may be below the recommended baseline for reliable playback.",
    ram: "Low device memory may limit smooth HTML, URL, or VAST rendering.",
    storage: "Low available storage can prevent updates, cached content, or normal app operation.",
    gpu: "Graphics adapter may be missing, generic, or below the recommended display capability.",
    webview: "Older Android System WebView versions may have limited compatibility with HTML, URL, or VAST playback.",
    network: "Network connectivity may be unavailable or unstable during validation.",
    time_timezone: "Incorrect device time or timezone can affect scheduled content and reporting.",
    lmx_app_installed: windows
      ? "LMX Content for Windows may not be installed in C:\\Program Files\\mac-media-player."
      : "LMX Content may not be installed on the device.",
    lmx_app_launch: windows
      ? "LMX Content for Windows may be installed but MW Content.exe or mac-media-player.exe may not be launchable."
      : "LMX Content may be installed but not launchable from Android.",
    lmx_version: windows
      ? "The LMX Content for Windows executable version could not be detected."
      : "The LMX Content version could not be detected.",
    programmatic_vast: "Programmatic/VAST readiness may be limited by Android version, WebView, RAM, or network state.",
    pull_to_content: "The installed LMX Content version may be below the Pull To Content requirement."
  };
  const items = Object.entries(checks)
    .filter(([, check]) => ["WARNING", "FAIL"].includes(check.status))
    .map(([key]) => map[key])
    .filter(Boolean);
  return items.length ? Array.from(new Set(items)) : ["No likely causes identified from the current assessment."];
}

function recommendedActions(checks, recommendations, raw = {}) {
  const windows = isWindows(raw);
  const map = {
    android_version: "Upgrade the device OS or select a device running Android 11 or above where possible.",
    windows_os: "Use Windows 10 or Windows 11 non-server editions for Windows LMX Content deployment.",
    cpu: "Use an Intel Core i5/i7 class CPU or AMD Ryzen class CPU where possible.",
    ram: null,
    storage: "Free device storage or use a device with at least 5GB available storage.",
    gpu: "Install the correct graphics driver or use supported Intel UHD/Iris, AMD Vega, or dedicated graphics.",
    webview: "Update Android System WebView where possible.",
    network: "Confirm the device has stable internet connectivity before deployment.",
    time_timezone: "Correct the device date, time, and timezone settings.",
    lmx_app_installed: windows
      ? "Install LMX Content for Windows in C:\\Program Files\\mac-media-player using MW Content.exe or mac-media-player.exe."
      : "Install LMX Content package com.qruize.quad42.media.app.",
    lmx_app_launch: windows
      ? "Reinstall or update LMX Content for Windows, then confirm MW Content.exe or mac-media-player.exe can launch."
      : "Reinstall or update LMX Content, then confirm the app can launch.",
    lmx_version: windows
      ? "Install or update LMX Content for Windows and confirm the executable file version can be detected."
      : "Install a supported LMX Content build and rerun certification.",
    programmatic_vast: "Update WebView and verify Android version, RAM, and internet connectivity.",
    pull_to_content: windows
      ? "Update LMX Content for Windows to version 1.0.34 or newer."
      : "Update LMX Content to Android version 2.9.1.2 native or newer."
  };
  const items = Object.entries(checks)
    .filter(([, check]) => ["WARNING", "FAIL"].includes(check.status))
    .map(([key, check]) => key === "ram" ? ramRecommendation(check) : map[key])
    .filter(Boolean);
  if (items.length) return Array.from(new Set(items));
  return recommendations ? [recommendations] : ["No action required before deployment."];
}

function ramRecommendation(check = {}) {
  if (check.status === "FAIL") return "Use a device with at least 4GB RAM.";
  if (check.status === "WARNING") return "Use 8GB RAM or above for optimal LMX Content performance.";
  return null;
}

function sanitizeSummaryForPlatform(summary = {}, raw = {}) {
  if (!isWindows(raw)) return summary;
  const sanitize = (value) => sanitizeWindowsText(value);
  const sanitizeList = (items) => (items || []).map(sanitize);
  return {
    ...summary,
    overall_summary: sanitize(summary.overall_summary),
    good_points: sanitizeList(summary.good_points),
    warning_points: sanitizeList(summary.warning_points),
    failed_points: sanitizeList(summary.failed_points),
    likely_causes: sanitizeList(summary.likely_causes),
    recommended_actions: sanitizeList(summary.recommended_actions)
  };
}

function sanitizeWindowsText(value = "") {
  return String(value)
    .replace(/Install LMX Content package com\.qruize\.quad42\.media\.app\./g, "Install LMX Content for Windows in C:\\Program Files\\mac-media-player using MW Content.exe or mac-media-player.exe.")
    .replace(/com\.qruize\.quad42\.media\.app/g, "LMX Content for Windows")
    .replace(/LMX Content may be installed but not launchable from Android\./g, "LMX Content for Windows may be installed but MW Content.exe or mac-media-player.exe may not be launchable.")
    .replace(/Reinstall or update LMX Content, then confirm the app can launch\./g, "Reinstall or update LMX Content for Windows, then confirm MW Content.exe or mac-media-player.exe can launch.")
    .replace(/Update LMX Content to Android version 2\.9\.1\.2 native or newer, or Windows version 1\.0\.34 or newer\./g, "Update LMX Content for Windows to version 1.0.34 or newer.");
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

function gb(value) {
  if (value === undefined || value === null || value === "") return "-";
  return `${value} GB`;
}

createRoot(document.getElementById("root")).render(<App />);
