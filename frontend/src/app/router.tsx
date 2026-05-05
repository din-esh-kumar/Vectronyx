// frontend/src/app/router.tsx
import { Routes, Route } from "react-router-dom";
import Dashboard from "../features/dashboard/Dashboard";
import DataAnalyst from "../features/data-analyst/DataAnalyst";
import ResearchAgent from "../features/research/ResearchAgent";
import MemorySystem from "../features/memory/MemorySystem";
import Settings from "../features/settings/settings";
import NotFound from "../pages/NotFound";
import Login from "../features/auth/Login";
import Layout from "../components/layout/Layout";

export default function AppRouter() {
  return (
   <Routes>
      {/* 🔐 Login (no layout) */}
      <Route path="/login" element={<Login />} />

      {/* 🔥 Layout applied to all pages */}
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/data-analyst" element={<DataAnalyst />} />
        <Route path="/research" element={<ResearchAgent />} />
        <Route path="/memory" element={<MemorySystem />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      {/* ❌ 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
