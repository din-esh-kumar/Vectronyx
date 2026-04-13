// frontend/src/app/router.tsx
import { Routes, Route } from "react-router-dom";
import Dashboard from "../features/dashboard/Dashboard";
import DataAnalyst from "../features/data-analyst/DataAnalyst";
import ResearchAgent from "../features/research/ResearchAgent";
import MemorySystem from "../features/memory/MemorySystem";
import NotFound from "../pages/NotFound";
import Login from "../features/auth/Login";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/login" element={<Login />} />
      <Route path="/data-analyst" element={<DataAnalyst />} />
      <Route path="/research" element={<ResearchAgent />} />
      <Route path="/memory" element={<MemorySystem />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
