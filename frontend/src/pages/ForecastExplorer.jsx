import { useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Topbar from "../components/Topbar";
import KpiCard from "../components/KpiCard";
import { Skeleton, TopProgress } from "../components/Skeleton";
import { useFloor } from "../context/FloorContext";
import { useToast } from "../context/ToastContext";
import { getForecast, getForecastHistory } from "../api";

const HORIZONS = [
  { key: "1h", label: "1 hour" },
  { key: "24h", label: "24 hours" },
  { key: "7d", label: "7 days" },
];

export default function ForecastExplorer() {
  const { floor, horizon, setHorizon } = useFloor();
  const { showToast } = useToast();
  const [forecast, setForecast] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getForecast(floor, horizon), getForecastHistory(floor, horizon, 60)])
      .then(([f, h]) => {
        if (cancelled) return;
        setForecast(f);
        setHistory(h);
      })
      .catch(() => {
        if (!cancelled) showToast("Couldn't load the forecast — retrying shortly.", "error");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
        setInitialLoad(false);
      });
    return () => {
      cancelled = true;
    };
  }, [floor, horizon, showToast]);

  const chartData = history.map((row) => ({
    label: new Date(row.target_ts).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit" }),
    predicted: row.predicted,
    band: [row.lower, row.upper],
    baseline: row.baseline_persistence,
    actual: row.actual,
  }));

  return (
    <div>
      <Topbar
        title="Forecast Explorer"
        subtitle="Ensemble point forecast with prediction interval, benchmarked against naive persistence."
      />

      <TopProgress active={loading} />

      <div className="card" style={{ display: "flex", gap: 8, marginBottom: 20, width: "fit-content" }}>
        {HORIZONS.map((h) => (
          <button
            key={h.key}
            className={`btn btn-ghost ${horizon === h.key ? "active" : ""}`}
            onClick={() => setHorizon(h.key)}
          >
            {h.label}
          </button>
        ))}
      </div>

      {forecast && (
        <div style={{ opacity: loading ? 0.55 : 1, transition: "opacity 0.2s ease" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 20 }}>
            <KpiCard
              label="Predicted"
              value={forecast.predicted.toFixed(2)}
              unit="kWh"
              accent="var(--sun)"
              hint={`target ${new Date(forecast.target_ts).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })}`}
            />
            <KpiCard
              label="80% interval"
              value={`${forecast.lower.toFixed(1)} – ${forecast.upper.toFixed(1)}`}
              unit="kWh"
              accent="var(--sky)"
            />
            <KpiCard
              label="GRU vs. XGBoost"
              value={`${forecast.components.gru.toFixed(2)} / ${forecast.components.xgb.toFixed(2)}`}
              unit="kWh"
              accent="var(--violet)"
              hint="component forecasts"
            />
            <KpiCard
              label="Naive persistence"
              value={forecast.naive_persistence.toFixed(2)}
              unit="kWh"
              accent="var(--coral)"
              hint="baseline"
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
            <div className="card">
              <h3 style={{ fontSize: 16, marginBottom: 12 }}>Predicted vs. baseline vs. actual</h3>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={chartData}>
                  <defs>
                    <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ffb703" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#ffb703" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#ffe9cc" strokeDasharray="4 6" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 10.5, fill: "#9a91ab" }} minTickGap={30} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#9a91ab" }} axisLine={false} tickLine={false} width={36} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #ffe4bf", fontSize: 12.5 }} />
                  <Area dataKey="band" name="Prediction interval" stroke="none" fill="url(#bandGrad)" />
                  <Line type="monotone" dataKey="predicted" name="Ensemble" stroke="#ffb703" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="baseline" name="Naive baseline" stroke="#8338ec" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                  <Line type="monotone" dataKey="actual" name="Actual" stroke="#06d6a0" strokeWidth={2} dot={{ r: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="card">
                <h3 style={{ fontSize: 16, marginBottom: 12 }}>SHAP · top drivers</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {forecast.top_features.map((f) => (
                    <div key={f.feature}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                        <span style={{ fontWeight: 600 }}>{f.feature}</span>
                        <span style={{ color: f.impact >= 0 ? "#0a9f74" : "#e0526b" }}>
                          {f.impact >= 0 ? "+" : ""}
                          {f.impact}
                        </span>
                      </div>
                      <div style={{ height: 6, borderRadius: 6, background: "#fff1da", overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${Math.min(100, Math.abs(f.impact) * 120)}%`,
                            background: f.impact >= 0 ? "linear-gradient(90deg,#06d6a0,#3ee6b3)" : "linear-gradient(90deg,#ff6b6b,#ff9b8f)",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <h3 style={{ fontSize: 16, marginBottom: 12 }}>Accuracy: ensemble vs. baseline</h3>
                {["rmse", "mae", "mape"].map((k) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "6px 0", borderBottom: "1px dashed #ffe4bf" }}>
                    <span style={{ color: "var(--ink-soft)", textTransform: "uppercase", fontWeight: 700, fontSize: 11.5 }}>{k}</span>
                    <span>
                      <strong>{forecast.model_metrics?.[k]?.toFixed?.(3) ?? "—"}</strong>
                      <span style={{ color: "var(--ink-faint)" }}> vs {forecast.baseline_metrics?.[k]?.toFixed?.(3) ?? "—"}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {loading && initialLoad && !forecast && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 20 }}>
          {[0, 1, 2, 3].map((i) => (
            <div className="card" key={i}>
              <Skeleton width={90} height={12} />
              <Skeleton width={70} height={28} style={{ marginTop: 10 }} />
              <Skeleton width={110} height={11} style={{ marginTop: 8 }} />
            </div>
          ))}
        </div>
      )}

      {!loading && !forecast && (
        <div className="card">No model trained yet for this floor/horizon. Click "Retrain models" in the top bar.</div>
      )}
    </div>
  );
}
