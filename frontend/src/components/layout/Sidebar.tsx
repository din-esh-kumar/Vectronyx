import { NavLink } from "react-router-dom";
import { MdDashboard, MdAnalytics, MdSupportAgent } from "react-icons/md";
import { FaDatabase } from "react-icons/fa";
import { IoMdSettings } from "react-icons/io";
import { FiX } from "react-icons/fi";
// import { supabase } from "../../lib/supabase";

export default function Sidebar({ mobileOpen, setMobileOpen }: any) {
  const menu = [
    { name: "Dashboard", path: "/", icon: MdDashboard },
    { name: "Data Analyst", path: "/data-analyst", icon: MdAnalytics },
    { name: "Research Agent", path: "/research", icon: MdSupportAgent },
    { name: "Memory System", path: "/memory", icon: FaDatabase },
    { name: "Settings", path: "/settings", icon: IoMdSettings },
  ];

  //     // 🔥 LOGOUT
  // const handleLogout = async () => {
  //   await supabase.auth.signOut();
  //   window.location.href = "/login";
  // };


return (
    <>
      {/* ✅ DESKTOP (UNCHANGED) */}
      <div className="hidden md:block group fixed top-16 left-0 h-[calc(100vh-4rem)] bg-white shadow-md w-16 hover:w-60 transition-all duration-300 z-40">
        <div className="p-2 space-y-2">
          {menu.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 p-3 rounded-lg ${
                    isActive
                      ? "bg-[#f3e8ff] text-[#6d28d9]"
                      : "text-gray-600 hover:bg-gray-100"
                  }`
                }
              >
                <Icon size={18} className="min-w-4.5" />

                <span className="text-sm font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition">
                  {item.name}
                </span>
              </NavLink>
            );
          })}
        </div>
      </div>

      {/* 🔥 MOBILE OVERLAY */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/30 z-40 md:hidden"
        />
      )}

      {/* 🔥 MOBILE DRAWER */}
      <div
        className={`fixed top-0 left-0 h-full w-[85%] max-w-sm bg-white z-50 transform transition-transform duration-300 md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200/50 shadow-[0_4px_20px_rgba(0,0,0,0.05)] bg-white/80 backdrop-blur">
          <h1 className="text-lg font-bold text-purple-500">Vectronyx</h1>
          <button onClick={() => setMobileOpen(false)}>
            <FiX size={22} />
          </button>
        </div>

        {/* MENU */}
        <div className="p-4 space-y-2">
          {menu.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 p-3 rounded-lg ${
                    isActive
                      ? "bg-[#f3e8ff] text-[#6d28d9]"
                      : "text-gray-700 hover:bg-gray-100"
                  }`
                }
              >
                <Icon size={20} />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>

        {/* PROFILE + LOGOUT
        <div className="absolute bottom-6 w-full px-4 border-t pt-4">
          <button className="w-full text-left py-2">Profile</button>
          <button
            onClick={handleLogout}
            className="w-full text-left py-2 text-red-500"
          >
            Logout
          </button>
        </div> */}
      </div>
    </>
  );
}

