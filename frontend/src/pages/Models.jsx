import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Topbar from "../components/Topbar";
import KpiCard from "../components/KpiCard";
import { TopProgress } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { getAnomalyEvaluation, getBenchmark, getModelRuns } from "../api";

const BASE_PAPER_MODELS = [
  { key: "A", label: "Model A (Temp + Occupancy)", rmse: 0.25374, mse: 0.06438, mae: 0.09306, mape: 0.04135, r2: 0.98901, adj_r2: 0.98899 },
  { key: "B", label: "Model B (Occupancy only)", rmse: 0.36216, mse: 0.13116, mae: 0.21339, mape: 0.10975, r2: 0.97762, adj_r2: 0.97757 },
  { key: "C", label: "Model C (Temperature only)", rmse: 0.29156, mse: 0.08501, mae: 0.15018, mape: 0.07802, r2: 0.98549, adj_r2: 0.98546 },
];

const MODEL_LABELS = {
  persistence: "Persistence (last value)",
  arima: "ARIMA(2,0,1)",
  svr: "SVR (RBF)",
  lightgbm: "LightGBM",
  xgboost: "XGBoost",
  gru: "GRU",
  ensemble: "GRU + XGBoost ensemble",
};
const MODEL_ORDER = ["persistence", "arima", "svr", "lightgbm", "xgboost", "gru", "ensemble"];
const HORIZON_ORDER = ["1h", "24h", "7d"];

const METRIC_ROWS = [
  { key: "rmse", label: "RMSE", digits: 4 },
  { key: "mse", label: "MSE", digits: 4 },
  { key: "mae", label: "MAE", digits: 4 },
  { key: "mape", label: "MAPE", digits: 3, suffix: "%" },
  { key: "r2", label: "R²", digits: 4 },
  { key: "adj_r2", label: "Adjusted R²", digits: 4 },
];

function avg(list, key) {
  const vals = list.map((r) => r[key]).filter((v) => v != null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export default function Models() {
  const { showToast } = useToast();
  const [runs, setRuns] = useState([]);
  const [evals, setEvals] = useState([]);
  const [benchmark, setBenchmark] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    Promise.all([getModelRuns(), getAnomalyEvaluation(), getBenchmark()])
      .then(([runData, evalData, benchData]) => {
        setRuns(runData);
        setEvals(evalData);
        setBenchmark(benchData);
      })
      .catch(() => showToast("Couldn't load model lab data — check the API.", "error"))
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

  const hourlyByFloor = {};
  for (const r of runs) {
    if (r.horizon === "1h" && !hourlyByFloor[r.floor]) hourlyByFloor[r.floor] = r;
  }
  const hourlyRuns = Object.values(hourlyByFloor);
  const ours = {
    rmse: avg(hourlyRuns, "rmse"),
    mse: avg(hourlyRuns, "mse"),
    mae: avg(hourlyRuns, "mae"),
    mape: avg(hourlyRuns, "mape"),
    r2: avg(hourlyRuns, "r2"),
    adj_r2: avg(hourlyRuns, "adj_r2"),
  };

  const fmt = (v, digits, suffix = "") => (v == null ? "—" : `${v.toFixed(digits)}${suffix}`);

  const improvements = runs
    .filter((r) => r.baseline_rmse)
    .map((r) => ((r.baseline_rmse - r.rmse) / r.baseline_rmse) * 100);
  const avgImprovement = improvements.length
    ? improvements.reduce((a, b) => a + b, 0) / improvements.length
    : null;

  const comparison = MODEL_ORDER.map((model) => {
    const row = { model };
    for (const h of HORIZON_ORDER) {
      const rows = benchmark.filter((b) => b.model === model && b.horizon === h);
      row[`${h}_rmse`] = avg(rows, "rmse");
      row[`${h}_r2`] = avg(rows, "r2");
    }
    return row;
  }).filter((row) => HORIZON_ORDER.some((h) => row[`${h}_rmse`] != null));
  const bestRmse = {};
  for (const h of HORIZON_ORDER) {
    const vals = comparison.map((r) => r[`${h}_rmse`]).filter((v) => v != null);
    bestRmse[h] = vals.length ? Math.min(...vals) : null;
  }

  const avgRecall = evals.length ? evals.reduce((a, e) => a + e.recall, 0) / evals.length : null;
  const avgPrecision = evals.length ? evals.reduce((a, e) => a + e.precision, 0) / evals.length : null;
  const bestFloor = evals.length ? [...evals].sort((a, b) => b.f1 - a.f1)[0] : null;

  return (
    <div>
      <Topbar
        title="Model Lab"
        subtitle="Every training run - GRU + XGBoost ensemble vs. the naive persistence baseline it must beat."
      />

      <TopProgress active={loading} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
        <KpiCard
          label="Forecast accuracy vs. a simple guess"
          loading={loading && avgImprovement == null}
          value={avgImprovement != null ? `${avgImprovement >= 0 ? "+" : ""}${avgImprovement.toFixed(0)}` : "—"}
          unit="%"
          accent="var(--teal)"
          hint="Averaged across every floor and horizon trained so far"
        />
        <KpiCard
          label="Unusual spikes caught"
          loading={loading && avgRecall == null}
          value={avgRecall != null ? (avgRecall * 100).toFixed(0) : "—"}
          unit="% of test spikes"
          accent="var(--coral)"
          hint={
            avgPrecision != null
              ? `${(avgPrecision * 100).toFixed(0)}% of flagged spikes were real, not false alarms`
              : "Tested with known planted spikes"
          }
        />
      </div>

      <button
        className="btn btn-ghost"
        onClick={() => setShowAdvanced((v) => !v)}
        style={{ marginBottom: 20 }}
      >
        {showAdvanced ? "Hide technical details" : "Show technical details"}
      </button>

      {!showAdvanced && bestFloor && (
        <div className="card" style={{ color: "var(--ink-soft)", fontSize: 13.5 }}>
          Floor {bestFloor.floor} has the most reliable anomaly detection right now, catching{" "}
          {(bestFloor.recall * 100).toFixed(0)}% of planted test spikes. Click "Show technical details" above for
          the full accuracy breakdown, per-floor numbers, and how GridSentry compares to the published research
          it's based on.
        </div>
      )}

      {showAdvanced && (
        <>
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

      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 20 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              {["Version", "Floor", "Horizon", "Trained at", "RMSE", "MAE", "MAPE", "Baseline RMSE", "Improvement"].map((h) => (
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
                  <td style={{ padding: "10px 16px" }}>{r.floor ?? "—"}</td>
                  <td style={{ padding: "10px 16px" }}>{r.horizon ?? "—"}</td>
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

      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 20 }}>
        <div style={{ padding: "18px 22px 4px" }}>
          <h3 style={{ fontSize: 16 }}>Model comparison</h3>
          <p style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 4 }}>
            Every model is scored on the same held-out validation window, averaged across the four floors. Lower RMSE
            is better; the best value in each horizon is highlighted.
          </p>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              <th style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                Model
              </th>
              {HORIZON_ORDER.flatMap((h) => [
                <th key={`${h}-rmse`} style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                  {h} RMSE
                </th>,
                <th key={`${h}-r2`} style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                  {h} R²
                </th>,
              ])}
            </tr>
          </thead>
          <tbody>
            {comparison.map((row) => (
              <tr key={row.model} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 16px", fontWeight: 600 }}>{MODEL_LABELS[row.model]}</td>
                {HORIZON_ORDER.flatMap((h) => {
                  const best = row[`${h}_rmse`] != null && row[`${h}_rmse`] === bestRmse[h];
                  return [
                    <td key={`${h}-rmse`} style={{ padding: "10px 16px", fontWeight: best ? 800 : 400, color: best ? "#0a9f74" : "inherit" }}>
                      {fmt(row[`${h}_rmse`], 4)}
                    </td>,
                    <td key={`${h}-r2`} style={{ padding: "10px 16px", color: "var(--ink-soft)" }}>
                      {fmt(row[`${h}_r2`], 3)}
                    </td>,
                  ];
                })}
              </tr>
            ))}
            {comparison.length === 0 && !loading && (
              <tr>
                <td colSpan={7} style={{ padding: "16px", color: "var(--ink-faint)" }}>
                  No comparison yet - trigger a retrain to benchmark the models.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 20 }}>
        <div style={{ padding: "18px 22px 4px" }}>
          <h3 style={{ fontSize: 16 }}>Forecasting vs. base paper (Anan et al., 2024)</h3>
          <p style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 4 }}>
            Same metric set the base paper reports for its occupancy-aware LSTM models. GridSentry's column is the
            live GRU + XGBoost ensemble, 1-hour horizon, averaged across all four floors.
          </p>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              <th style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                Metric
              </th>
              {BASE_PAPER_MODELS.map((m) => (
                <th key={m.key} style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)" }}>
                  {m.label}
                </th>
              ))}
              <th style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--sun)", fontWeight: 800 }}>
                GridSentry
              </th>
            </tr>
          </thead>
          <tbody>
            {METRIC_ROWS.map((row) => (
              <tr key={row.key} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 16px", fontWeight: 700, color: "var(--ink-soft)" }}>{row.label}</td>
                {BASE_PAPER_MODELS.map((m) => (
                  <td key={m.key} style={{ padding: "10px 16px" }}>
                    {fmt(m[row.key], row.digits, row.suffix)}
                  </td>
                ))}
                <td style={{ padding: "10px 16px", fontWeight: 700 }}>{fmt(ours[row.key], row.digits, row.suffix)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "18px 22px 4px" }}>
          <h3 style={{ fontSize: 16 }}>Anomaly detection evaluation</h3>
          <p style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 4 }}>
            Precision, recall, and F1 aren't meaningful for the forecasting task above (it's regression, not
            classification) - but they are for anomaly detection. Computed each retrain by injecting known synthetic
            spikes (3.5x the reading, at random timestamps) into a copy of each floor's real data, then checking
            whether the control-chart + autoencoder detector catches them.
          </p>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
          <thead>
            <tr style={{ background: "var(--surface-soft)", textAlign: "left" }}>
              {["Floor", "Injected", "True Positives", "False Positives", "False Negatives", "Precision", "Recall", "F1"].map((h) => (
                <th key={h} style={{ padding: "12px 16px", fontSize: 11.5, color: "var(--ink-soft)", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {evals.map((e) => (
              <tr key={e.floor} className="data-row" style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 16px", fontWeight: 600 }}>Floor {e.floor}</td>
                <td style={{ padding: "10px 16px" }}>{e.n_injected}</td>
                <td style={{ padding: "10px 16px", color: "#0a9f74" }}>{e.true_positives}</td>
                <td style={{ padding: "10px 16px", color: "#c23b2c" }}>{e.false_positives}</td>
                <td style={{ padding: "10px 16px", color: "#c23b2c" }}>{e.false_negatives}</td>
                <td style={{ padding: "10px 16px", fontWeight: 700 }}>{(e.precision * 100).toFixed(1)}%</td>
                <td style={{ padding: "10px 16px", fontWeight: 700 }}>{(e.recall * 100).toFixed(1)}%</td>
                <td style={{ padding: "10px 16px", fontWeight: 700 }}>{(e.f1 * 100).toFixed(1)}%</td>
              </tr>
            ))}
            {evals.length === 0 && !loading && (
              <tr>
                <td colSpan={8} style={{ padding: "16px", color: "var(--ink-faint)" }}>
                  No evaluation yet - trigger a retrain to run it.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
        </>
      )}
    </div>
  );
}
