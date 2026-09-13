import { useEffect, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
import { getAnomalies, getBuildings, getForecast, getLiveSeries, getRecommendations } from "../api";
import { FLOOR_LABELS } from "../constants";

const FLOORS = [1, 2, 3, 4];
const FLOOR_COLORS = ["#ffb703", "#ff6b6b", "#3a86ff", "#8338ec"];

function fmt(ts) {
  const d = new Date(ts);
  return d.toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Dashboard() {
  const { floor } = useFloor();
  const { showToast } = useToast();
  const [live, setLive] = useState([]);
  const [forecast1h, setForecast1h] = useState(null);
  const [forecast24h, setForecast24h] = useState(null);
  const [floorSnapshot, setFloorSnapshot] = useState([]);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [tips, setTips] = useState([]);
  const [error, setError] = useState(null);
  const [building, setBuilding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const hadError = useRef(false);

  useEffect(() => {
    getBuildings()
      .then((rows) => setBuilding(rows[0] || null))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [liveData, f1, f24, anomalies, recs] = await Promise.all([
          getLiveSeries(floor, 96),
          getForecast(floor, "1h").catch(() => null),
          getForecast(floor, "24h").catch(() => null),
          getAnomalies({ status: "open", floor }),
          getRecommendations().catch(() => []),
        ]);
        if (cancelled) return;
        setLive(liveData);
        setForecast1h(f1);
        setForecast24h(f24);
        setAnomalyCount(anomalies.length);
        setTips(recs.filter((t) => t.floor === floor).slice(0, 3));
        if (hadError.current) showToast("Reconnected to the backend.", "success");
        hadError.current = false;
        setError(null);
      } catch {
        if (!cancelled) {
          const msg = "Backend not reachable yet - run seed.py then start the API.";
          if (!hadError.current) showToast(msg, "error");
          hadError.current = true;
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setInitialLoad(false);
        }
      }
    }

    async function loadSnapshot() {
      const results = await Promise.all(
        FLOORS.map((f) => getLiveSeries(f, 1).then((d) => d[d.length - 1]).catch(() => null))
      );
      if (!cancelled) setFloorSnapshot(results);
    }

    load();
    loadSnapshot();
    const interval = setInterval(() => {
      load();
      loadSnapshot();
    }, 45000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [floor, showToast]);

  const chartData = live.map((row) => ({
    ts: row.ts,
    label: fmt(row.ts),
    total: row.total_kwh,
    hvac: row.hvac_kwh,
  }));

  const currentLoad = live.length ? live[live.length - 1].total_kwh : null;

  return (
    <div>
      <Topbar
        title={`${building?.name || "Loading building…"} · Floor ${floor} — ${FLOOR_LABELS[floor]}`}
        subtitle="Live consumption vs. forecast, with occupancy-aware anomaly watch."
      />

      {error && (
        <div
          className="card"
          style={{ marginBottom: 20, borderColor: "var(--coral)", color: "#b3271f", background: "#fff3f0" }}
        >
          {error}
        </div>
      )}

      <TopProgress active={loading && !initialLoad} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 20 }}>
        <KpiCard
          label="Current load"
          loading={initialLoad && currentLoad === null}
          value={currentLoad !== null ? currentLoad.toFixed(2) : "—"}
          unit="kWh"
          accent="var(--sun)"
          hint="Latest reading"
        />
        <KpiCard
          label="Next-hour forecast"
          loading={initialLoad && !forecast1h}
          value={forecast1h ? forecast1h.predicted.toFixed(2) : "—"}
          unit="kWh"
          accent="var(--sky)"
          hint={forecast1h ? `±${(forecast1h.upper - forecast1h.predicted).toFixed(2)} interval` : "Training…"}
        />
        <KpiCard
          label="24h model vs. baseline"
          loading={initialLoad && !forecast24h}
          value={
            forecast24h?.model_metrics?.rmse != null
              ? `${forecast24h.model_metrics.rmse.toFixed(2)}`
              : "—"
          }
          unit="RMSE"
          accent="var(--teal)"
          hint={
            forecast24h?.baseline_metrics?.rmse != null
              ? `baseline ${forecast24h.baseline_metrics.rmse.toFixed(2)}`
              : ""
          }
        />
        <KpiCard
          label="Open anomalies"
          loading={initialLoad && live.length === 0}
          value={anomalyCount}
          unit={anomalyCount === 1 ? "alert" : "alerts"}
          accent="var(--coral)"
          hint="This floor"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ fontSize: 16 }}>Live consumption — last 96 hours</h3>
            <span style={{ fontSize: 12.5, color: "var(--ink-faint)" }}>Total vs. HVAC (kWh)</span>
          </div>
          {initialLoad && chartData.length === 0 ? (
            <Skeleton height={280} radius={14} />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ffb703" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#ffb703" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="hvacGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3a86ff" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#3a86ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#ffe9cc" strokeDasharray="4 6" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#9a91ab" }} minTickGap={40} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#9a91ab" }} axisLine={false} tickLine={false} width={36} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "1px solid #ffe4bf", fontSize: 12.5 }}
                  labelStyle={{ fontWeight: 700 }}
                />
                <Area type="monotone" dataKey="total" name="Total" stroke="#ffb703" strokeWidth={2.5} fill="url(#totalGrad)" />
                <Area type="monotone" dataKey="hvac" name="HVAC" stroke="#3a86ff" strokeWidth={2} fill="url(#hvacGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <h3 style={{ fontSize: 16, marginBottom: 12 }}>Per-floor snapshot</h3>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={floorSnapshot.map((r, i) => ({ floor: `F${FLOORS[i]}`, total: r?.total_kwh ?? 0 }))}>
                <XAxis dataKey="floor" tick={{ fontSize: 12, fill: "#9a91ab" }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #ffe4bf", fontSize: 12.5 }} />
                <Bar dataKey="total" radius={[8, 8, 0, 0]}>
                  {floorSnapshot.map((_, i) => (
                    <Cell key={i} fill={FLOOR_COLORS[i % FLOOR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 16, marginBottom: 12 }}>Top tips for Floor {floor}</h3>
            {tips.length === 0 && (
              <p style={{ color: "var(--ink-faint)", fontSize: 13.5 }}>No recommendations right now — all clear.</p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {tips.map((t, i) => (
                <div
                  key={i}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 12,
                    background: t.priority === "high" ? "#fff1ee" : "#fff8ea",
                    border: `1px solid ${t.priority === "high" ? "#ffd2c7" : "#ffe9b8"}`,
                    fontSize: 13,
                    lineHeight: 1.45,
                  }}
                >
                  {t.message}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
