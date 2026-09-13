import { useEffect, useState } from "react";
import Topbar from "../components/Topbar";
import { TopProgress } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { getAnomalies, updateAnomalyStatus } from "../api";

const SEVERITY_STYLE = {
  high: { bg: "#fff1ee", border: "#ffc7ba", text: "#c23b2c", dot: "#ff6b6b" },
  medium: { bg: "#fff8ea", border: "#ffe2a3", text: "#a06a00", dot: "#ffb703" },
  low: { bg: "#f1f6ff", border: "#c9dcff", text: "#2a5fb0", dot: "#3a86ff" },
};

const STATUS_OPTIONS = ["open", "acknowledged", "resolved"];

export default function Anomalies() {
  const { showToast } = useToast();
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    getAnomalies(statusFilter === "all" ? {} : { status: statusFilter })
      .then(setItems)
      .catch(() => showToast("Couldn't load anomalies — check the API.", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter, showToast]);

  const handleStatus = async (id, status) => {
    try {
      await updateAnomalyStatus(id, status);
      showToast(`Marked as ${status}.`, "success");
      load();
    } catch {
      showToast("Couldn't update that anomaly — try again.", "error");
    }
  };

  return (
    <div>
      <Topbar
        title="Anomaly Watch"
        subtitle="Control-chart baseline combined with an autoencoder trained on normal consumption."
      />

      <TopProgress active={loading} />

      <div className="card" style={{ display: "flex", gap: 8, marginBottom: 20, width: "fit-content" }}>
        {["open", "acknowledged", "resolved", "all"].map((s) => (
          <button
            key={s}
            className={`btn btn-ghost ${statusFilter === s ? "active" : ""}`}
            onClick={() => setStatusFilter(s)}
            style={{ textTransform: "capitalize" }}
          >
            {s}
          </button>
        ))}
      </div>

      {!loading && items.length === 0 && (
        <div className="card" style={{ color: "var(--ink-soft)" }}>
          No {statusFilter !== "all" ? statusFilter : ""} anomalies detected in this window.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((a) => {
          const s = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.low;
          return (
            <div
              key={a.id}
              className="card fade-in"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
                background: s.bg,
                borderColor: s.border,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: s.dot,
                    flexShrink: 0,
                    boxShadow: `0 0 0 5px ${s.dot}22`,
                  }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14.5, color: s.text }}>
                    Floor {a.floor} · {a.value.toFixed(2)} kWh vs. expected {a.expected.toFixed(2)} kWh
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 3 }}>
                    {new Date(a.ts).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} · detected via{" "}
                    <strong>{a.method.replace("_", " ")}</strong> · score {a.score.toFixed(2)}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
                <span
                  className="pill"
                  style={{ background: "white", color: s.text, border: `1px solid ${s.border}`, textTransform: "capitalize" }}
                >
                  {a.severity}
                </span>
                <select
                  value={a.status}
                  onChange={(e) => handleStatus(a.id, e.target.value)}
                  style={{
                    border: `1px solid ${s.border}`,
                    borderRadius: 999,
                    padding: "7px 10px",
                    fontSize: 12.5,
                    fontWeight: 600,
                    background: "white",
                    color: "var(--ink)",
                  }}
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
