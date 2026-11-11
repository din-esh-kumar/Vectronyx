import { NavLink } from "react-router-dom";
import { LayoutDashboard, BarChart3, X } from "lucide-react";

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

const NAV_ITEMS = [
  {
    name: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Data Analyst",
    path: "/data-analyst",
    icon: BarChart3,
  },
];

export default function Sidebar({ mobileOpen, setMobileOpen }: SidebarProps) {
  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 sticky top-16 h-[calc(100vh-4rem)] glass-panel border-r border-[#6E3B1E]/20 z-20 overflow-hidden shadow-xl">
        <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto overflow-x-hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative ${
                    isActive
                      ? "bg-gradient-to-r from-violet-900/80 via-purple-900/60 to-[#4E2512]/90 text-white border border-[#A36B4A]/40 shadow-[0_0_16px_rgba(168,85,247,0.2)]"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[#2A160E]/30 border border-transparent"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b from-[#E8A276] to-violet-500" />
                    )}
                    <div
                      className={`p-1.5 rounded-lg shrink-0 transition-colors ${
                        isActive
                          ? "text-[#F3E8DC] bg-[#542A13]/80 shadow-sm"
                          : "text-violet-400 group-hover:text-white"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-semibold whitespace-nowrap">{item.name}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 md:hidden animate-fadeIn"
        />
      )}

      {/* Mobile Drawer */}
      <div
        className={`fixed top-0 left-0 bottom-0 w-72 max-w-[82%] glass-panel z-50 transform transition-transform duration-300 ease-out md:hidden flex flex-col border-r border-[#6E3B1E]/30 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-[#6E3B1E]/20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-700 via-purple-800 to-[#884F2E] flex items-center justify-center font-bold text-white shadow-md border border-[#E8A276]/30 font-mono">
              V
            </div>
            <span className="text-sm font-bold text-white tracking-wide font-display">
              Vectronyx
            </span>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1.5 rounded-lg text-violet-300 hover:text-white hover:bg-violet-900/30 cursor-pointer"
            aria-label="Close navigation drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === "/"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 p-3 rounded-xl transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-violet-900/80 to-[#4E2512]/80 text-white border border-[#A36B4A]/40 shadow-md"
                      : "text-[var(--text-secondary)] hover:bg-[#2A160E]/30"
                  }`
                }
              >
                <Icon className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </>
  );
}
