import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { FloorProvider } from "./context/FloorContext";
import { ToastProvider } from "./context/ToastContext";
import Dashboard from "./pages/Dashboard";
import ForecastExplorer from "./pages/ForecastExplorer";
import Anomalies from "./pages/Anomalies";
import Recommendations from "./pages/Recommendations";
import Models from "./pages/Models";
import Reports from "./pages/Reports";

export default function App() {
  return (
    <ToastProvider>
      <FloorProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/forecast" element={<ForecastExplorer />} />
            <Route path="/anomalies" element={<Anomalies />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/models" element={<Models />} />
          </Route>
        </Routes>
      </FloorProvider>
    </ToastProvider>
  );
}
