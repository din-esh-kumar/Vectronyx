// frontend/src/app/router.tsx
import { Routes, Route } from 'react-router-dom'
import Dashboard from '../pages/Dashboard'
import DataAnalyst from '../pages/DataAnalyst'
import ResearchAgent from '../pages/ResearchAgent'
import MemorySystem from '../pages/MemorySystem'
import NotFound from '../pages/NotFound'

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/"             element={<Dashboard />} />
      <Route path="/data-analyst" element={<DataAnalyst />} />
      <Route path="/research"     element={<ResearchAgent />} />
      <Route path="/memory"       element={<MemorySystem />} />
      <Route path="*"             element={<NotFound />} />
    </Routes>
  )
}