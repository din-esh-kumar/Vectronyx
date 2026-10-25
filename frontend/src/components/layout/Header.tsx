import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { useAppStore } from "../../store/useAppStore";
import {
  Menu,
  Search,
  Bell,
  Sun,
  Moon,
  Sparkles,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Info,
  LogOut,
  User,
  Shield,
  Activity
} from "lucide-react";

interface HeaderProps {
  setMobileOpen: (open: boolean) => void;
}

export default function Header({ setMobileOpen }: HeaderProps) {
  const {
    theme,
    toggleTheme,
    toggleCommandPalette,
    notifications,
    unreadCount,
    markAllNotificationsRead,
    systemStatus,
  } = useAppStore();

  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [name, setName] = useState("Edwin Samuel");
  const [userEmail, setUserEmail] = useState("developer@vectronyx.ai");

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Fetch Supabase user
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data } = await supabase.auth.getUser();
        if (data.user) {
          setName(data.user.user_metadata?.full_name || data.user.email?.split("@")[0] || "Edwin Samuel");
          setUserEmail(data.user.email || "developer@vectronyx.ai");
        }
      } catch (err) {
        // Fallback default
      }
    };
    fetchUser();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setName(session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Edwin Samuel");
        setUserEmail(session.user.email || "developer@vectronyx.ai");
      }
    });

    return () => {
      listener?.subscription?.unsubscribe();
    };
  }, []);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
    } finally {
      window.location.href = "/login";
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-16 glass-panel z-40 flex items-center justify-between px-4 md:px-6 transition-colors border-b border-violet-500/15">
      {/* LEFT: Mobile toggle & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileOpen(true)}
          className="md:hidden p-2 rounded-xl text-violet-300 hover:text-white hover:bg-violet-900/40 transition-colors cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Brand Logo with Violet + Roasted Brown Crest */}
        <div
          className="flex items-center gap-2.5 cursor-pointer select-none"
          onClick={() => navigate("/")}
        >
          <div className="relative w-9 h-9 rounded-xl flex items-center justify-center overflow-hidden shadow-lg border border-violet-400/30 bg-gradient-to-br from-violet-600 via-purple-900 to-amber-700">
            <span className="text-white font-extrabold text-lg tracking-wider font-mono">V</span>
            <div className="absolute inset-0 bg-gradient-to-t from-transparent via-transparent to-amber-400/25" />
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-400 rounded-full blur-[1px]" />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-bold tracking-tight text-white font-display">
                Vectronyx
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-gradient-to-r from-violet-950/80 to-amber-950/80 text-amber-300 border border-amber-600/30">
                2.0
              </span>
            </div>
            <span className="text-[10px] text-violet-300/60 font-mono hidden sm:inline-block leading-none">
              Autonomous AI Workbench
            </span>
          </div>
        </div>
      </div>

      {/* CENTER: Quick Command Search Bar */}
      <div className="hidden lg:flex items-center flex-1 max-w-md mx-8">
        <button
          onClick={toggleCommandPalette}
          className="w-full flex items-center justify-between px-3.5 py-2 rounded-xl bg-violet-950/30 border border-violet-500/20 text-violet-300/70 hover:text-violet-100 hover:border-violet-400/40 hover:bg-violet-900/30 transition-all text-xs group cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Search className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
            <span>Search datasets, vectors, or run ReAct query...</span>
          </span>
          <kbd className="px-2 py-0.5 font-mono text-[10px] bg-violet-900/50 text-violet-300 rounded border border-violet-500/20">
            Ctrl+K
          </kbd>
        </button>
      </div>

      {/* RIGHT: Status telemetry, Theme switch, Alerts, Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Live Telemetry Pill */}
        <div className="hidden xl:flex items-center gap-2 px-3 py-1 rounded-full bg-violet-950/50 border border-violet-500/25 text-xs font-mono shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span className="text-violet-200">Gemini 1M</span>
          <span className="text-violet-600">•</span>
          <span className="text-amber-400">{systemStatus.groqSpeed} tok/s</span>
          <span className="text-violet-600">•</span>
          <span className="text-emerald-400">{systemStatus.latencyMs}ms</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Warm Ivory Light" : "Switch to Obsidian Violet Dark"}
          className="p-2 rounded-xl text-violet-300 hover:text-amber-400 hover:bg-violet-900/30 transition-colors border border-transparent hover:border-violet-500/20 cursor-pointer"
          aria-label="Toggle Theme"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative p-2 rounded-xl text-violet-300 hover:text-white hover:bg-violet-900/30 transition-colors border border-transparent hover:border-violet-500/20 cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-500 ring-2 ring-[#0C0815] animate-pulse" />
            )}
          </button>

          {notificationsOpen && (
            <div
              className="absolute right-0 mt-3 w-80 sm:w-96 rounded-2xl glass-panel shadow-2xl border border-violet-500/25 overflow-hidden z-50 animate-fadeIn"
              style={{
                boxShadow: "0 16px 48px -8px rgba(126, 34, 206, 0.45), 0 0 16px rgba(180, 83, 9, 0.2)",
              }}
            >
              <div className="p-3.5 border-b border-violet-500/15 flex items-center justify-between bg-violet-950/40">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-violet-200">
                    System Alerts
                  </span>
                  {unreadCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllNotificationsRead}
                    className="text-[11px] text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
                  >
                    Mark read
                  </button>
                )}
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-violet-500/10 p-1">
                {notifications.map((item) => (
                  <div
                    key={item.id}
                    className={`p-3 rounded-xl transition-colors ${
                      item.read ? "opacity-75" : "bg-violet-900/20"
                    } hover:bg-violet-900/30`}
                  >
                    <div className="flex items-start gap-2.5">
                      {item.type === "warning" && (
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      )}
                      {item.type === "success" && (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      )}
                      {item.type === "info" && (
                        <Info className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="text-xs font-semibold text-violet-100 flex items-center justify-between">
                          <span>{item.title}</span>
                          <span className="text-[10px] text-violet-400/60 font-mono">
                            {item.timestamp}
                          </span>
                        </div>
                        <p className="text-[11px] text-violet-300/70 mt-0.5 leading-relaxed">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Profile Avatar & Dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2.5 p-1 rounded-xl hover:bg-violet-900/30 transition-all border border-transparent hover:border-violet-500/25 cursor-pointer"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-700 via-purple-600 to-amber-600 flex items-center justify-center font-bold text-white text-xs shadow-md border border-amber-400/30">
              {name.charAt(0).toUpperCase()}
            </div>
            <div className="hidden md:flex flex-col text-left">
              <span className="text-xs font-semibold text-violet-100 leading-none">
                {name}
              </span>
              <span className="text-[10px] font-mono text-amber-400/80 leading-none mt-1">
                Enterprise Pro
              </span>
            </div>
          </button>

          {profileOpen && (
            <div
              className="absolute right-0 mt-3 w-56 rounded-2xl glass-panel shadow-2xl border border-violet-500/25 overflow-hidden z-50 animate-fadeIn"
              style={{
                boxShadow: "0 16px 48px -8px rgba(126, 34, 206, 0.45), 0 0 16px rgba(180, 83, 9, 0.2)",
              }}
            >
              <div className="p-3.5 border-b border-violet-500/15 bg-violet-950/40">
                <p className="text-xs font-bold text-white">{name}</p>
                <p className="text-[11px] text-violet-300/60 font-mono truncate">{userEmail}</p>
                <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-500/30 text-[10px] font-mono">
                  <Shield className="w-3 h-3 text-amber-400" />
                  <span>Pro Workstation</span>
                </div>
              </div>

              <div className="p-1 space-y-0.5 text-xs">
                <Link
                  to="/settings"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-violet-200 hover:text-white hover:bg-violet-900/30 transition-colors"
                >
                  <User className="w-4 h-4 text-violet-400" />
                  <span>Account & Keys</span>
                </Link>
                <Link
                  to="/memory"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-violet-200 hover:text-white hover:bg-violet-900/30 transition-colors"
                >
                  <Activity className="w-4 h-4 text-amber-400" />
                  <span>Memory Analytics</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-rose-300 hover:text-rose-200 hover:bg-rose-950/30 transition-colors text-left cursor-pointer"
                >
                  <LogOut className="w-4 h-4 text-rose-400" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
