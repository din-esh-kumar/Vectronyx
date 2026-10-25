import { useState } from "react";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import CommandPalette from "./CommandPalette";

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] transition-colors duration-200 relative selection:bg-violet-600/30 selection:text-violet-200">
      {/* Ambient background lighting */}
      <div className="ambient-glow" />

      {/* Global Command Palette (Ctrl+K) */}
      <CommandPalette />

      {/* FIXED HEADER */}
      <Header setMobileOpen={setMobileOpen} />

      <div className="flex pt-16 relative z-10 min-h-screen">
        {/* SIDEBAR */}
        <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

        {/* MAIN APPLICATION CONTAINER (NEVER OVERLAPPED) */}
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full transition-all">
          <Outlet />
        </main>
      </div>
    </div>
  );
}