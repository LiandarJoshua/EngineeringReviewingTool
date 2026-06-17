import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import NewReview from "./pages/NewReview";
import ReviewDetail from "./pages/ReviewDetail";
import Progress from "./pages/Progress";
import PRReviews from "./pages/PRReviews";
import Schedules from "./pages/Schedules";
import { isAuthenticated, logout } from "./api/client";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

const IconGrid = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
  </svg>
);
const IconPlus = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
  </svg>
);
const IconChart = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);
const IconGitPR = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>
    <path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>
  </svg>
);
const IconClock = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/>
  </svg>
);
const IconCode = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
  </svg>
);

function Sidebar() {
  const location = useLocation();

  const navItems = [
    { to: "/", label: "Dashboard", icon: <IconGrid />, exact: true },
    { to: "/review/new", label: "New Review", icon: <IconPlus />, exact: false },
    { to: "/pr-reviews", label: "PR Reviews", icon: <IconGitPR />, exact: false },
    { to: "/schedules", label: "Schedules", icon: <IconClock />, exact: false },
    { to: "/progress/me", label: "Progress", icon: <IconChart />, exact: false },
  ];

  return (
    <aside style={{
      width: 220,
      minWidth: 220,
      background: "#0a0a14",
      borderRight: "1px solid rgba(255,255,255,0.05)",
      display: "flex",
      flexDirection: "column",
      padding: "20px 12px",
      gap: 4,
      position: "fixed",
      top: 0,
      left: 0,
      bottom: 0,
      zIndex: 40,
    }}>
      {/* Logo */}
      <div style={{ padding: "4px 10px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "white", flexShrink: 0,
          }}>
            <IconCode />
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", fontWeight: 700, fontFamily: "Syne, sans-serif", color: "#e8e8f0", lineHeight: 1.1 }}>
              ERP
            </div>
            <div style={{ fontSize: "0.6rem", color: "#4a4a68", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Review Platform
            </div>
          </div>
        </div>
      </div>

      {/* Section label */}
      <div style={{ fontSize: "0.6rem", color: "#4a4a68", letterSpacing: "0.1em", textTransform: "uppercase", padding: "0 10px 6px" }}>
        Navigation
      </div>

      {/* Nav items */}
      {navItems.map((item) => {
        const isActive = item.exact
          ? location.pathname === item.to
          : location.pathname.startsWith(item.to) && item.to !== "/";
        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={`sidebar-link ${isActive ? "active" : ""}`}
          >
            <span style={{ opacity: isActive ? 1 : 0.6 }}>{item.icon}</span>
            {item.label}
          </NavLink>
        );
      })}

      {/* Bottom */}
      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.04)" }}>
        <div style={{ fontSize: "0.7rem", color: "#4a4a68", lineHeight: 1.6, padding: "0 10px" }}>
          <div style={{ color: "#6a6a88", marginBottom: 2 }}>Powered by</div>
          <div>LangGraph · Ollama · ChromaDB</div>
        </div>
        <button
          onClick={logout}
          style={{
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 8,
            padding: "7px 10px",
            color: "#6a6a88",
            fontSize: "0.72rem",
            cursor: "pointer",
            textAlign: "left",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          Sign out
        </button>
      </div>
    </aside>
  );
}

function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{
        marginLeft: 220,
        flex: 1,
        minHeight: "100vh",
        background: "#090912",
        overflowX: "hidden",
      }}>
        <Routes>
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/review/new" element={<ProtectedRoute><NewReview /></ProtectedRoute>} />
          <Route path="/review/:reviewId" element={<ProtectedRoute><ReviewDetail /></ProtectedRoute>} />
          <Route path="/pr-reviews" element={<ProtectedRoute><PRReviews /></ProtectedRoute>} />
          <Route path="/schedules" element={<ProtectedRoute><Schedules /></ProtectedRoute>} />
          <Route path="/progress/:userId" element={<ProtectedRoute><Progress /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<Layout />} />
      </Routes>
    </BrowserRouter>
  );
}
