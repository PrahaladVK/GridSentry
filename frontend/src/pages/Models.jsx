import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Topbar from "../components/Topbar";
import { TopProgress } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { getModelRuns } from "../api";

export default function Models() {
  const { showToast } = useToast();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getModelRuns()
      .then(setRuns)
      .catch(() => showToast("Couldn't load model runs — check the API.", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const chartData = [...runs]
    .reverse()
    .slice(-12)
    .map((r) => ({
      version: r.version.replace("v", "").slice(4, 12),
      "Ensemble RMSE": r.rmse,
      "Baseline RMSE": r.baseline_rmse,
    }));

  return (
    <div>
      <Topbar
        title="Model Lab"
        subtitle="Every training run - GRU + XGBoost ensemble vs. the naive persistence baseline it must beat."
      />

      <TopProgress active={loading} />

      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 16, marginBottom: 14 }}>RMSE over recent training runs</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <CartesianGrid stroke="#ffe9cc" strokeDasharray="4 6" vertical={false} />
            <XAxis dataKey="version" tick={{ fontSize: 10.5, fill: "#9a91ab" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9a91ab" }} axisLine={false} tickLine={false} width={36} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #ffe4bf", fontSize: 12.5 }} />
            <Legend wrapperStyle={{ fontSize: 12.5 }} />
            <Bar dataKey="Ensemble RMSE" fill="#ffb703" radius={[6, 6, 0, 0]} />
            <Bar dataKey="Baseline RMSE" fill="#8338ec" radius={[6, 6, 0, 0]} opacity={0.55} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              {["Version", "Trained at", "RMSE", "MAE", "MAPE", "Baseline RMSE", "Improvement"].map((h) => (
                <th key={h} style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const improvement = r.baseline_rmse ? ((r.baseline_rmse - r.rmse) / r.baseline_rmse) * 100 : null;
              return (
                <tr key={r.version} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 16px", fontWeight: 600 }}>{r.version}</td>
                  <td style={{ padding: "10px 16px", color: "var(--ink-faint)" }}>
                    {new Date(r.trained_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                  </td>
                  <td style={{ padding: "10px 16px" }}>{r.rmse?.toFixed(3)}</td>
                  <td style={{ padding: "10px 16px" }}>{r.mae?.toFixed(3)}</td>
                  <td style={{ padding: "10px 16px" }}>{r.mape?.toFixed(2)}%</td>
                  <td style={{ padding: "10px 16px", color: "var(--ink-faint)" }}>{r.baseline_rmse?.toFixed(3)}</td>
                  <td style={{ padding: "10px 16px" }}>
                    {improvement !== null && (
                      <span style={{ color: improvement >= 0 ? "#0a9f74" : "#c23b2c", fontWeight: 700 }}>
                        {improvement >= 0 ? "▲" : "▼"} {Math.abs(improvement).toFixed(1)}%
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
