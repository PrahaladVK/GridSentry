import { Skeleton } from "./Skeleton";

export default function KpiCard({ label, value, unit, accent = "var(--sun)", hint, loading = false }) {
  return (
    <div className="card" style={{ position: "relative", overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          top: -30,
          right: -30,
          width: 100,
          height: 100,
          borderRadius: "50%",
          background: accent,
          opacity: 0.12,
        }}
      />
      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-soft)" }}>{label}</div>
      {loading ? (
        <>
          <Skeleton width={72} height={28} style={{ marginTop: 10 }} />
          <Skeleton width={100} height={11} style={{ marginTop: 8 }} />
        </>
      ) : (
        <>
          <div
            key={value}
            className="fade-in"
            style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 8 }}
          >
            <span style={{ fontSize: 30, fontWeight: 800, fontFamily: "Sora, sans-serif" }}>{value}</span>
            {unit && <span style={{ fontSize: 14, color: "var(--ink-faint)", fontWeight: 600 }}>{unit}</span>}
          </div>
          {hint && <div style={{ fontSize: 12.5, color: "var(--ink-faint)", marginTop: 6 }}>{hint}</div>}
        </>
      )}
    </div>
  );
}
