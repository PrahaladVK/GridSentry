import { NavLink } from "react-router-dom";
import { IconAlertTriangle, IconClipboard, IconFlask, IconGrid, IconShield, IconTrendingUp } from "./icons";

const NAV = [
  { to: "/", label: "Dashboard", Icon: IconGrid, end: true },
  { to: "/forecast", label: "Forecast", Icon: IconTrendingUp },
  { to: "/anomalies", label: "Anomalies", Icon: IconAlertTriangle },
  { to: "/recommendations", label: "Recommendations", Icon: IconClipboard },
  { to: "/models", label: "Model Lab", Icon: IconFlask },
];

export default function Sidebar() {
  return (
    <aside
      style={{
        width: 236,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 28,
        padding: "26px 18px",
        position: "sticky",
        top: 0,
        height: "100vh",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 8px" }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 14,
            background: "linear-gradient(135deg, var(--sun), var(--coral))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            boxShadow: "var(--shadow-soft)",
          }}
        >
          <IconShield width={21} height={21} strokeWidth={2.2} />
        </div>
        <div>
          <div style={{ fontFamily: "Sora, sans-serif", fontWeight: 800, fontSize: 19, lineHeight: 1 }}>
            GridSentry
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-faint)", fontWeight: 600, letterSpacing: 0.3 }}>
            ENERGY FORECASTING
          </div>
        </div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {NAV.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}
          >
            <Icon width={17} height={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div style={{ marginTop: "auto" }}>
        <div
          className="card"
          style={{
            padding: 16,
            background: "linear-gradient(160deg, #fff, var(--surface-soft))",
          }}
        >
          <div style={{ fontSize: 12.5, color: "var(--ink-soft)", lineHeight: 1.5 }}>
            Ensemble: <strong style={{ color: "var(--ink)" }}>GRU + XGBoost</strong>, blended
            against a naive-persistence baseline. Anomalies via control chart + autoencoder.
          </div>
        </div>
      </div>
    </aside>
  );
}
