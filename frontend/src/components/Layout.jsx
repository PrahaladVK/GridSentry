import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  const location = useLocation();
  return (
    <div style={{ display: "flex", minHeight: "100vh", maxWidth: 1440, margin: "0 auto" }}>
      <Sidebar />
      <main className="scrollpane" style={{ flex: 1, padding: "26px 34px 60px", minWidth: 0 }}>
        <div key={location.pathname} className="fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
