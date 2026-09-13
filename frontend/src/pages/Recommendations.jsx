import { useEffect, useState } from "react";
import Topbar from "../components/Topbar";
import { TopProgress } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { getRecommendations } from "../api";
import { IconAlertTriangle, IconBarChart, IconSnowflake, IconWrench } from "../components/icons";

const TYPE_META = {
  weather_driven_load: { Icon: IconSnowflake, label: "Weather-driven load" },
  standby_load: { Icon: IconWrench, label: "Standby load" },
  capacity_review: { Icon: IconBarChart, label: "Capacity review" },
  inspect_anomaly: { Icon: IconAlertTriangle, label: "Inspect equipment" },
};

const PRIORITY_STYLE = {
  high: { bg: "linear-gradient(135deg,#fff1ee,#ffe4dd)", border: "#ffc2b3", accent: "#c23b2c" },
  medium: { bg: "linear-gradient(135deg,#fff8ea,#fff1cf)", border: "#ffe2a3", accent: "#a06a00" },
};

export default function Recommendations() {
  const { showToast } = useToast();
  const [tips, setTips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecommendations()
      .then(setTips)
      .catch(() => showToast("Couldn't load recommendations — check the API.", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const grouped = tips.reduce((acc, t) => {
    acc[t.floor] = acc[t.floor] || [];
    acc[t.floor].push(t);
    return acc;
  }, {});

  return (
    <div>
      <Topbar
        title="Recommendations"
        subtitle="Rule-based tips generated from the forecast, occupancy, and anomaly state of each floor."
      />

      <TopProgress active={loading} />

      {!loading && tips.length === 0 && (
        <div className="card" style={{ color: "var(--ink-soft)" }}>
          No recommendations at this time - consumption is within expected bounds on every floor.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {Object.entries(grouped).map(([floor, floorTips]) => (
          <div key={floor}>
            <h3 style={{ fontSize: 15, marginBottom: 10, color: "var(--ink-soft)" }}>Floor {floor}</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14 }}>
              {floorTips.map((t, i) => {
                const meta = TYPE_META[t.type] || { Icon: IconAlertTriangle, label: t.type };
                const style = PRIORITY_STYLE[t.priority] || PRIORITY_STYLE.medium;
                const { Icon } = meta;
                return (
                  <div
                    key={i}
                    className="card"
                    style={{ background: style.bg, borderColor: style.border }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                      <span
                        style={{
                          display: "inline-flex",
                          color: style.accent,
                          background: "white",
                          borderRadius: 9,
                          padding: 6,
                        }}
                      >
                        <Icon width={15} height={15} />
                      </span>
                      <span style={{ fontWeight: 700, fontSize: 13.5 }}>{meta.label}</span>
                      <span
                        className="pill"
                        style={{
                          marginLeft: "auto",
                          background: "white",
                          textTransform: "capitalize",
                          fontSize: 11,
                        }}
                      >
                        {t.priority}
                      </span>
                    </div>
                    <p style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--ink)" }}>{t.message}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
