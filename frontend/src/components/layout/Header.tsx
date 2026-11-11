import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { useAppStore } from "../../store/useAppStore";
import { Menu, Sun, Moon, LogOut, LogIn } from "lucide-react";

interface HeaderProps {
  setMobileOpen: (open: boolean) => void;
}

interface AuthUser {
  name: string;
  email: string;
}

export default function Header({ setMobileOpen }: HeaderProps) {
  const { theme, toggleTheme } = useAppStore();

  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const extractUser = (rawUser: {
      email?: string;
      user_metadata?: Record<string, any>;
    }): AuthUser => ({
      name:
        rawUser.user_metadata?.full_name ||
        rawUser.email?.split("@")[0] ||
        "Account",
      email: rawUser.email || "",
    });

    const fetchUser = async () => {
      try {
        const { data } = await supabase.auth.getUser();
        if (data.user) {
          setUser(extractUser(data.user));
        }
      } catch {
        // Leave signed-out state when no active session exists
      }
    };
    fetchUser();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser(extractUser(session.user));
      } else {
        setUser(null);
      }
    });

    return () => {
      listener?.subscription?.unsubscribe();
    };
  }, []);

  const handleLogout = async () => {
    setProfileOpen(false);
    try {
      await supabase.auth.signOut();
    } finally {
      setUser(null);
      navigate("/login");
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-16 glass-panel z-40 flex items-center justify-between px-4 md:px-6 transition-colors border-b border-violet-500/15">
      {/* Left: Mobile toggle & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileOpen(true)}
          className="md:hidden p-2 rounded-xl text-violet-300 hover:text-white hover:bg-violet-900/40 transition-colors cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <Link
          to="/"
          className="flex items-center gap-2.5 select-none"
        >
          <div className="w-8 h-8 rounded-xl flex items-center justify-center shadow-md border border-violet-400/30 bg-gradient-to-br from-violet-600 via-purple-900 to-amber-700">
            <span className="text-white font-extrabold text-base tracking-wider font-mono">V</span>
          </div>
          <span className="text-lg font-bold tracking-tight text-white font-display">
            Vectronyx
          </span>
        </Link>
      </div>

      {/* Right: Theme switch & Auth */}
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light mode" : "Switch to Dark mode"}
          className="p-2 rounded-xl text-violet-300 hover:text-amber-400 hover:bg-violet-900/30 transition-colors border border-transparent hover:border-violet-500/20 cursor-pointer"
          aria-label="Toggle Theme"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {user ? (
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen((prev) => !prev)}
              className="flex items-center gap-2.5 p-1.5 pr-2.5 rounded-xl hover:bg-violet-900/30 transition-all border border-transparent hover:border-violet-500/25 cursor-pointer"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-violet-700 via-purple-600 to-amber-600 flex items-center justify-center font-bold text-white text-xs shadow-sm border border-amber-400/30">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span className="hidden sm:inline text-xs font-semibold text-violet-100">
                {user.name}
              </span>
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-52 rounded-2xl glass-panel shadow-2xl border border-violet-500/25 overflow-hidden z-50 animate-fadeIn">
                <div className="p-3 border-b border-violet-500/15 bg-violet-950/40">
                  <p className="text-xs font-bold text-white truncate">{user.name}</p>
                  {user.email && (
                    <p className="text-[11px] text-violet-300/65 font-mono truncate mt-0.5">
                      {user.email}
                    </p>
                  )}
                </div>

                <div className="p-1 text-xs">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-rose-300 hover:text-rose-200 hover:bg-rose-950/30 transition-colors text-left cursor-pointer"
                  >
                    <LogOut className="w-4 h-4 text-rose-400" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-violet-100 bg-violet-950/60 hover:bg-violet-900/60 border border-violet-500/30 transition-colors"
          >
            <LogIn className="w-3.5 h-3.5 text-amber-400" />
            <span>Sign In</span>
          </Link>
        )}
      </div>
    </header>
  );
}
