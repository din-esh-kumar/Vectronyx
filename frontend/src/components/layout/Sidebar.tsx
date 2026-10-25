import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  Sparkles,
  Database,
  Settings,
  X,
  HardDrive,
  Cpu,
  Layers
} from "lucide-react";
import { useAppStore } from "../../store/useAppStore";

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

export default function Sidebar({ mobileOpen, setMobileOpen }: SidebarProps) {
  const { systemStatus } = useAppStore();

  const navItems = [
    {
      name: "Dashboard",
      path: "/",
      icon: LayoutDashboard,
      badge: "Live",
      badgeColor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    },
    {
      name: "Data Analyst",
      path: "/data-analyst",
      icon: BarChart3,
      badge: "Econometric",
      badgeColor: "bg-amber-600/15 text-amber-300 border-amber-600/30",
    },
    {
      name: "Research Agent",
      path: "/research",
      icon: Sparkles,
      badge: "ReAct 1M",
      badgeColor: "bg-violet-600/15 text-violet-300 border-violet-500/30",
    },
    {
      name: "Memory System",
      path: "/memory",
      icon: Database,
      badge: "pgvector",
      badgeColor: "bg-purple-600/15 text-purple-300 border-purple-500/30",
    },
    {
      name: "Settings & Keys",
      path: "/settings",
      icon: Settings,
      badge: "Config",
      badgeColor: "bg-stone-500/15 text-stone-300 border-stone-500/30",
    },
  ];

  return (
    <>
      {/* DESKTOP COLLAPSIBLE SIDEBAR */}
      <aside className="hidden md:flex flex-col group fixed top-16 left-0 bottom-0 glass-panel w-16 hover:w-64 transition-all duration-300 z-30 border-r border-violet-500/15 overflow-hidden shadow-xl">
        {/* Navigation Content */}
        <div className="flex-1 py-4 px-2 space-y-5 overflow-y-auto overflow-x-hidden">
          <div className="space-y-1">
            <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-violet-400/50 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              Autonomous Intelligence
            </div>

            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.name}
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-3.5 px-3 py-2.5 rounded-xl transition-all duration-200 group/item relative ${
                      isActive
                        ? "bg-gradient-to-r from-violet-900/70 via-purple-950/50 to-amber-950/40 text-white border border-violet-500/30 shadow-[0_0_16px_rgba(168,85,247,0.22)]"
                        : "text-violet-300/70 hover:text-violet-100 hover:bg-violet-900/20 border border-transparent"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {/* Active indicator bar */}
                      {isActive && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b from-amber-400 to-violet-500" />
                      )}

                      <div
                        className={`p-1.5 rounded-lg shrink-0 transition-colors ${
                          isActive
                            ? "text-amber-400 bg-amber-950/50"
                            : "text-violet-400 group-hover/item:text-violet-200"
                        }`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>

                      <span className="text-xs font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex-1">
                        {item.name}
                      </span>

                      {/* Pill Badge visible on expand */}
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded-full border opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ${item.badgeColor}`}
                      >
                        {item.badge}
                      </span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        </div>

        {/* Bottom Hardware Gauge on Expand */}
        <div className="p-3 border-t border-violet-500/15 bg-violet-950/30 opacity-0 group-hover:opacity-100 transition-opacity duration-200 overflow-hidden shrink-0">
          <div className="flex items-center justify-between text-[11px] font-mono text-violet-300 mb-1.5">
            <span className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-amber-400" />
              <span>pgvector</span>
            </span>
            <span className="text-amber-400 font-semibold">{systemStatus.pgvectorCount} dims</span>
          </div>
          <div className="w-full h-1.5 bg-violet-950 rounded-full overflow-hidden border border-violet-500/20">
            <div
              className="h-full bg-gradient-to-r from-violet-500 via-purple-500 to-amber-500 rounded-full"
              style={{ width: "72%" }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-violet-400/60 mt-1 font-mono">
            <span>Alloc: 768d HNSW</span>
            <span>98.6% recall</span>
          </div>
        </div>
      </aside>

      {/* MOBILE BACKDROP */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/65 backdrop-blur-sm z-50 md:hidden animate-fadeIn"
        />
      )}

      {/* MOBILE DRAWER */}
      <div
        className={`fixed top-0 left-0 bottom-0 w-[85%] max-w-xs glass-panel z-50 transform transition-transform duration-300 ease-out md:hidden flex flex-col border-r border-violet-500/25 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{
          boxShadow: "0 0 50px rgba(126, 34, 206, 0.35), 0 0 20px rgba(180, 83, 9, 0.2)",
        }}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between p-4 border-b border-violet-500/15 bg-violet-950/40">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 via-purple-800 to-amber-700 flex items-center justify-center font-bold text-white shadow-md border border-amber-400/30">
              V
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide font-display">
                Vectronyx AI
              </h2>
              <span className="text-[10px] text-amber-400/80 font-mono">
                Autonomous Workbench
              </span>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1.5 rounded-lg text-violet-300 hover:text-white hover:bg-violet-900/30 cursor-pointer"
            aria-label="Close navigation drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Menu */}
        <div className="flex-1 p-3 space-y-2 overflow-y-auto">
          <p className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-violet-400/50">
            Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === "/"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center justify-between p-3 rounded-xl transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-violet-900/80 to-amber-950/50 text-white border border-violet-500/30 shadow-md"
                      : "text-violet-200/80 hover:bg-violet-900/25"
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-amber-400" />
                  <span className="text-sm font-medium">{item.name}</span>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${item.badgeColor}`}>
                  {item.badge}
                </span>
              </NavLink>
            );
          })}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-violet-500/15 bg-violet-950/40">
          <div className="flex items-center gap-2 text-xs text-violet-300 font-mono">
            <Cpu className="w-4 h-4 text-amber-400" />
            <span>Groq LPU 248 tok/s</span>
          </div>
          <p className="text-[10px] text-violet-400/60 mt-1 font-mono">
            Vectronyx Workbench • Dual Engine Active
          </p>
        </div>
      </div>
    </>
  );
}
