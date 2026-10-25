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
      badgeColor: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
    },
    {
      name: "Data Analyst",
      path: "/data-analyst",
      icon: BarChart3,
      badge: "Econometric",
      badgeColor: "bg-[#542A13]/60 text-[#E8A276] border-[#A36B4A]/40",
    },
    {
      name: "Research Agent",
      path: "/research",
      icon: Sparkles,
      badge: "ReAct 1M",
      badgeColor: "bg-violet-950/70 text-violet-300 border-violet-500/40",
    },
    {
      name: "Memory System",
      path: "/memory",
      icon: Database,
      badge: "pgvector",
      badgeColor: "bg-purple-950/70 text-purple-300 border-purple-500/40",
    },
    {
      name: "Settings & Keys",
      path: "/settings",
      icon: Settings,
      badge: "Config",
      badgeColor: "bg-[#3D1C0B]/60 text-[#D4B39B] border-[#884F2E]/40",
    },
  ];

  return (
    <>
      {/* DESKTOP PERMANENT NON-OVERLAPPING EXECUTIVE SIDEBAR */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 sticky top-16 h-[calc(100vh-4rem)] glass-panel border-r border-[#6E3B1E]/20 z-20 overflow-hidden shadow-xl">
        {/* Navigation Content */}
        <div className="flex-1 py-5 px-3 space-y-5 overflow-y-auto overflow-x-hidden">
          <div className="space-y-1.5">
            <div className="px-3 py-1.5 text-[10px] uppercase font-bold tracking-wider text-[#A36B4A] font-mono">
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
                    `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative ${
                      isActive
                        ? "bg-gradient-to-r from-violet-900/80 via-purple-900/60 to-[#4E2512]/90 text-white border border-[#A36B4A]/40 shadow-[0_0_16px_rgba(168,85,247,0.25)]"
                        : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[#2A160E]/30 border border-transparent"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {/* Active indicator bar */}
                      {isActive && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b from-[#E8A276] to-violet-500" />
                      )}

                      <div
                        className={`p-1.5 rounded-lg shrink-0 transition-colors ${
                          isActive
                            ? "text-[#F3E8DC] bg-[#542A13]/80 shadow-sm"
                            : "text-[#C084FC] group-hover:text-white"
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>

                      <span className="text-xs font-semibold whitespace-nowrap flex-1">
                        {item.name}
                      </span>

                      {/* Pill Badge */}
                      <span
                        className={`text-[9px] font-mono px-2 py-0.5 rounded-full border shrink-0 ${item.badgeColor}`}
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

        {/* Bottom Hardware Gauge */}
        <div className="p-3.5 border-t border-[#6E3B1E]/20 bg-[#1A0E08]/40 shrink-0">
          <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-secondary)] mb-1.5">
            <span className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-[#E8A276]" />
              <span>pgvector</span>
            </span>
            <span className="text-[#E8A276] font-semibold">{systemStatus.pgvectorCount} dims</span>
          </div>
          <div className="w-full h-1.5 bg-[#120A07] rounded-full overflow-hidden border border-[#6E3B1E]/30">
            <div
              className="h-full bg-gradient-to-r from-violet-500 via-purple-600 to-[#BD8E70] rounded-full"
              style={{ width: "72%" }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-[var(--text-muted)] mt-1.5 font-mono">
            <span>Alloc: 768d HNSW</span>
            <span>98.6% recall</span>
          </div>
        </div>
      </aside>

      {/* MOBILE BACKDROP */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 md:hidden animate-fadeIn"
        />
      )}

      {/* MOBILE DRAWER */}
      <div
        className={`fixed top-0 left-0 bottom-0 w-[85%] max-w-xs glass-panel z-50 transform transition-transform duration-300 ease-out md:hidden flex flex-col border-r border-[#6E3B1E]/30 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{
          boxShadow: "0 0 50px rgba(126, 34, 206, 0.4), 0 0 25px rgba(136, 79, 46, 0.25)",
        }}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#6E3B1E]/20 bg-[#1E110A]/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-700 via-purple-800 to-[#884F2E] flex items-center justify-center font-bold text-white shadow-md border border-[#E8A276]/30">
              V
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide font-display">
                Vectronyx AI
              </h2>
              <span className="text-[10px] text-[#E8A276] font-mono">
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
          <p className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-[#A36B4A]">
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
                      ? "bg-gradient-to-r from-violet-900/80 to-[#4E2512]/80 text-white border border-[#A36B4A]/40 shadow-md"
                      : "text-[var(--text-secondary)] hover:bg-[#2A160E]/30"
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-[#E8A276]" />
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
        <div className="p-4 border-t border-[#6E3B1E]/20 bg-[#1E110A]/80">
          <div className="flex items-center gap-2 text-xs text-[#E8A276] font-mono">
            <Cpu className="w-4 h-4 text-[#E8A276]" />
            <span>Groq LPU 248 tok/s</span>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] mt-1 font-mono">
            Vectronyx Workbench • Dual Engine Active
          </p>
        </div>
      </div>
    </>
  );
}
