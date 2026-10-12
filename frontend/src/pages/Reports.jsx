import { useCallback, useEffect, useState } from "react";
import Topbar from "../components/Topbar";
import KpiCard from "../components/KpiCard";
import { TopProgress } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import {
  generateReport,
  getAlertSettings,
  getAlerts,
  getSavedReports,
  getWeeklyReport,
  reportDownloadUrl,
  sendTestAlert,
} from "../api";

const th = { padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" };
const td = { padding: "10px 16px" };

const STATUS_COLOR = { sent: "#0a9f74", logged: "#0a9f74", failed: "#c23b2c", suppressed: "#a06a00" };

const fmt = (v, digits = 1, suffix = "") => (v == null ? "—" : `${v.toFixed(digits)}${suffix}`);

export default function Reports() {
  const { showToast } = useToast();
  const [report, setReport] = useState(null);
  const [saved, setSaved] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertSettings, setAlertSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    return Promise.all([getWeeklyReport(), getSavedReports(), getAlerts(), getAlertSettings()])
      .then(([r, s, a, cfg]) => {
        setReport(r);
        setSaved(s);
        setAlerts(a);
        setAlertSettings(cfg);
      })
      .catch(() => showToast("Couldn't load the report - check the API.", "error"));
  }, [showToast]);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  const onSave = async () => {
    setBusy(true);
    try {
      const out = await generateReport();
      showToast(`Saved ${out.pdf} and ${out.csv}`, "success");
      setSaved(await getSavedReports());
    } catch {
      showToast("Couldn't save the report.", "error");
    } finally {
      setBusy(false);
    }
  };

  const onTestAlert = async () => {
    setBusy(true);
    try {
      const out = await sendTestAlert();
      showToast(`Test alert: ${out.map((o) => `${o.channel} ${o.status}`).join(", ")}`, "success");
      setAlerts(await getAlerts());
    } catch {
      showToast("Couldn't send the test alert.", "error");
    } finally {
      setBusy(false);
    }
  };

  const total = report?.total;
  const channels = alertSettings
    ? [alertSettings.email_enabled && "email", alertSettings.sms_enabled && "SMS"].filter(Boolean)
    : [];

  return (
    <div>
      <Topbar
        title="Reports & Alerts"
        subtitle="A weekly consumption summary for facility managers, and the alerts sent on high-severity anomalies."
      />

      <TopProgress active={loading} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 20 }}>
        <KpiCard
          label="Energy used this week"
          loading={loading}
          value={total ? total.week_kwh.toFixed(0) : "—"}
          unit="kWh"
          accent="var(--sun)"
          hint={report ? `${report.period_start.slice(0, 10)} to ${report.period_end.slice(0, 10)}` : ""}
        />
        <KpiCard
          label="Change vs. last week"
          loading={loading}
          value={total?.change_pct != null ? `${total.change_pct > 0 ? "+" : ""}${total.change_pct.toFixed(1)}` : "—"}
          unit="%"
          accent="var(--teal)"
          hint={total ? `Previous week: ${total.previous_week_kwh.toFixed(0)} kWh` : ""}
        />
        <KpiCard
          label="Anomalies this week"
          loading={loading}
          value={total ? String(total.anomalies) : "—"}
          unit=""
          accent="var(--coral)"
          hint={total ? `${total.high_anomalies} high severity` : ""}
        />
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
        <a className="btn btn-primary" href={reportDownloadUrl("pdf")} style={{ textDecoration: "none" }}>
          Download PDF
        </a>
        <a className="btn btn-ghost" href={reportDownloadUrl("csv")} style={{ textDecoration: "none" }}>
          Download CSV
        </a>
        <button className="btn btn-ghost" onClick={onSave} disabled={busy}>
          Save this week's report
        </button>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 20 }}>
        <div style={{ padding: "18px 22px 4px" }}>
          <h3 style={{ fontSize: 16 }}>Weekly summary by floor</h3>
          <p style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 4 }}>
            Forecast accuracy is checked against the readings that arrived after each forecast was served. A report
            is also saved automatically every Monday at 06:00.
          </p>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              {["Floor", "Week kWh", "Change", "Avg kWh/h", "Peak kWh", "Anomalies (high)", "Open", "Forecast MAE"].map((h) => (
                <th key={h} style={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(report?.floors || []).map((f) => (
              <tr key={f.floor} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ ...td, fontWeight: 600 }}>Floor {f.floor}</td>
                <td style={td}>{fmt(f.week_kwh)}</td>
                <td style={{ ...td, color: f.change_pct > 0 ? "#c23b2c" : "#0a9f74", fontWeight: 700 }}>
                  {f.change_pct != null ? `${f.change_pct > 0 ? "+" : ""}${f.change_pct.toFixed(1)}%` : "—"}
                </td>
                <td style={td}>{fmt(f.avg_kwh_per_hour, 3)}</td>
                <td style={td}>{fmt(f.peak_kwh, 3)}</td>
                <td style={td}>
                  {f.high_anomalies + f.medium_anomalies} ({f.high_anomalies})
                </td>
                <td style={td}>{f.open_anomalies}</td>
                <td style={td}>{fmt(f.forecast_mae, 3)}</td>
              </tr>
            ))}
            {!report && !loading && (
              <tr>
                <td colSpan={8} style={{ padding: 16, color: "var(--ink-faint)" }}>
                  No readings yet - nothing to report on.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 20 }}>
        <div style={{ padding: "18px 22px 4px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <h3 style={{ fontSize: 16 }}>Alert log</h3>
            <p style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 4 }}>
              {alertSettings
                ? `${channels.length ? `Sending by ${channels.join(" and ")}` : "No email or SMS configured, so alerts are only logged"}. `
                : ""}
              Limits: one alert per floor every {alertSettings?.cooldown_minutes ?? 60} minutes, at most{" "}
              {alertSettings?.max_per_hour ?? 6} per hour.
            </p>
          </div>
          <button className="btn btn-ghost" onClick={onTestAlert} disabled={busy}>
            Send test alert
          </button>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              {["When", "Floor", "Channel", "Status", "Message"].map((h) => (
                <th key={h} style={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ ...td, color: "var(--ink-faint)" }}>
                  {new Date(`${a.created_at}Z`).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                </td>
                <td style={td}>{a.floor || "—"}</td>
                <td style={td}>{a.channel}</td>
                <td style={{ ...td, fontWeight: 700, color: STATUS_COLOR[a.status] || "inherit" }}>
                  {a.status}
                  {a.detail ? <span style={{ fontWeight: 400, color: "var(--ink-faint)" }}> ({a.detail})</span> : null}
                </td>
                <td style={td}>{a.subject}</td>
              </tr>
            ))}
            {alerts.length === 0 && !loading && (
              <tr>
                <td colSpan={5} style={{ padding: 16, color: "var(--ink-faint)" }}>
                  No alerts yet. One is raised when a new high-severity anomaly is detected.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {saved.length > 0 && (
        <div className="card" style={{ color: "var(--ink-soft)", fontSize: 13 }}>
          <strong style={{ color: "var(--ink)" }}>Saved on the server:</strong>{" "}
          {saved.slice(0, 6).map((s) => s.name).join(", ")}
        </div>
      )}
    </div>
  );
}
