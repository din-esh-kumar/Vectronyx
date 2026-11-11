// frontend/src/app/router.tsx
import { Routes, Route } from "react-router-dom";
import Dashboard from "../features/dashboard/Dashboard";
import DataAnalyst from "../features/data-analyst/DataAnalyst";
import NotFound from "../pages/NotFound";
import Login from "../features/auth/Login";
import Layout from "../components/layout/Layout";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/data-analyst" element={<DataAnalyst />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
