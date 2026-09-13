import { createContext, useContext, useEffect, useState } from "react";

const FloorContext = createContext(null);

export function FloorProvider({ children }) {
  const [floor, setFloor] = useState(() => {
    const saved = window.localStorage.getItem("gridsentry.floor");
    return saved ? Number(saved) : 1;
  });
  const [horizon, setHorizon] = useState(() => window.localStorage.getItem("gridsentry.horizon") || "24h");

  useEffect(() => {
    window.localStorage.setItem("gridsentry.floor", String(floor));
  }, [floor]);

  useEffect(() => {
    window.localStorage.setItem("gridsentry.horizon", horizon);
  }, [horizon]);

  return (
    <FloorContext.Provider value={{ floor, setFloor, horizon, setHorizon }}>
      {children}
    </FloorContext.Provider>
  );
}

export function useFloor() {
  const ctx = useContext(FloorContext);
  if (!ctx) throw new Error("useFloor must be used within FloorProvider");
  return ctx;
}
