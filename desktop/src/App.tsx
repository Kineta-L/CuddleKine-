import { Routes, Route, Link, useLocation } from "react-router-dom";
import OrderList from "./pages/OrderList";
import OrderDetail from "./pages/OrderDetail";
import GenerationPanel from "./pages/GenerationPanel";
import SystemStatusBar from "./components/SystemStatusBar";

const NAV_ITEMS = [
  { path: "/", label: "订单管理" },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">CuddleKine</h1>
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-link ${location.pathname === item.path ? "active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <SystemStatusBar />
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<OrderList />} />
          <Route path="/orders/:orderId" element={<OrderDetail />} />
          <Route path="/orders/:orderId/generate" element={<GenerationPanel />} />
        </Routes>
      </main>
    </div>
  );
}
