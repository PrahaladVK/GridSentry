import { useState } from "react";
import { useFloor } from "../context/FloorContext";
import { useToast } from "../context/ToastContext";
import { triggerRetrain } from "../api";
import { IconRefresh } from "./icons";

export default function Topbar({ title, subtitle, floors = [1, 2, 3, 4] }) {
  const { floor, setFloor } = useFloor();
  const { showToast } = useToast();
  const [retraining, setRetraining] = useState(false);

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      await triggerRetrain();
      showToast("Retrain triggered — models will refresh shortly.", "success");
    } catch {
      showToast("Couldn't trigger retrain — check that the API is running.", "error");
    } finally {
      setTimeout(() => setRetraining(false), 2500);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        marginBottom: 26,
      }}
    >
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 800 }}>{title}</h1>
        {subtitle && (
          <p style={{ color: "var(--ink-soft)", marginTop: 4, fontSize: 14.5 }}>{subtitle}</p>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <div className="card" style={{ padding: 6, display: "flex", gap: 4 }}>
          {floors.map((f) => (
            <button
              key={f}
              onClick={() => setFloor(f)}
              className={`btn btn-ghost ${floor === f ? "active" : ""}`}
              style={{ padding: "7px 14px" }}
            >
              Floor {f}
            </button>
          ))}
        </div>

        <span
          className="pill"
          style={{ background: "rgba(6,214,160,0.12)", color: "#0a9f74" }}
        >
          <span className="pill-dot" style={{ background: "#06d6a0" }} />
          Live
        </span>

        <button
          className="btn btn-primary"
          onClick={handleRetrain}
          disabled={retraining}
          style={{ display: "inline-flex", alignItems: "center", gap: 7 }}
        >
          <IconRefresh width={14} height={14} strokeWidth={2.5} className={retraining ? "spin" : ""} />
          {retraining ? "Retraining…" : "Retrain models"}
        </button>
      </div>
    </div>
  );
}
