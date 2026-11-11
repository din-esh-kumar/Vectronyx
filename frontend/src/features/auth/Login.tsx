import React, { useState, useEffect } from "react";
import { FcGoogle } from "react-icons/fc";
import { FaGithub } from "react-icons/fa";
import { supabase } from "../../lib/supabase";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ArrowRight, ArrowLeft, Lock, Mail, User } from "lucide-react";

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    const checkUser = async () => {
      try {
        const { data } = await supabase.auth.getSession();
        if (data.session) {
          navigate("/");
        }
      } catch {
        // Ignore session lookup error
      }
    };
    checkUser();
  }, [navigate]);

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session) {
        toast.success("Signed in");
        navigate("/");
      }
    });

    return () => {
      listener?.subscription?.unsubscribe();
    };
  }, [navigate]);

  const handleGoogleLogin = async () => {
    try {
      await supabase.auth.signInWithOAuth({ provider: "google" });
    } catch (err: any) {
      toast.error(err.message || "Google sign-in unavailable");
    }
  };

  const handleGithubLogin = async () => {
    try {
      await supabase.auth.signInWithOAuth({ provider: "github" });
    } catch (err: any) {
      toast.error(err.message || "GitHub sign-in unavailable");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password) {
      toast.error("Email & password required");
      return;
    }

    if (!isLogin && !name) {
      toast.error("Full name is required");
      return;
    }

    setLoading(true);

    try {
      if (isLogin) {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) throw error;

        if (data.session) {
          toast.success("Signed in");
          navigate("/");
        }
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: name },
          },
        });

        if (error) throw error;
        toast.success("Account created. Check your email or sign in.");
        setIsLogin(true);
      }
    } catch (err: any) {
      toast.error(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="w-full max-w-md rounded-3xl glass-panel border border-violet-500/25 overflow-hidden shadow-2xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 via-purple-700 to-amber-600 flex items-center justify-center font-bold text-white shadow-md border border-amber-400/30 font-mono text-base">
              V
            </div>
            <span className="text-lg font-extrabold text-white font-display tracking-tight">
              Vectronyx
            </span>
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-1 text-xs text-violet-300/80 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </Link>
        </div>

        <div>
          <h1 className="text-xl font-bold text-white font-display">
            {isLogin ? "Sign In" : "Create Account"}
          </h1>
          <p className="text-xs text-violet-300/70 mt-1">
            {isLogin
              ? "Sign in to your Vectronyx account."
              : "Register an account to access your workspace."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {!isLogin && (
            <div>
              <label className="block text-violet-300 font-medium mb-1">Full Name</label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Your full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-violet-950/50 border border-violet-500/25 text-white placeholder-violet-400/40 focus-vb"
                />
                <User className="w-4 h-4 text-violet-400 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>
          )}

          <div>
            <label className="block text-violet-300 font-medium mb-1">Email Address</label>
            <div className="relative">
              <input
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-violet-950/50 border border-violet-500/25 text-white placeholder-violet-400/40 focus-vb font-mono text-xs"
              />
              <Mail className="w-4 h-4 text-violet-400 absolute left-3 top-1/2 -translate-y-1/2" />
            </div>
          </div>

          <div>
            <label className="block text-violet-300 font-medium mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-violet-950/50 border border-violet-500/25 text-white placeholder-violet-400/40 focus-vb"
              />
              <Lock className="w-4 h-4 text-violet-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-violet-400 hover:text-white cursor-pointer"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl font-bold text-xs sm:text-sm text-white bg-gradient-to-r from-violet-600 via-purple-700 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-lg shadow-violet-900/40 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95 disabled:opacity-50"
          >
            <span>{loading ? "Authenticating..." : isLogin ? "Sign In" : "Create Account"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="flex items-center">
          <hr className="grow border-violet-500/20" />
          <span className="px-3 text-violet-400/60 text-[11px] font-mono">OR</span>
          <hr className="grow border-violet-500/20" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="py-2.5 px-3 rounded-xl border border-violet-500/20 hover:border-violet-400/40 bg-violet-950/30 hover:bg-violet-900/30 text-xs font-medium text-white flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <FcGoogle className="w-4 h-4" />
            <span>Google</span>
          </button>

          <button
            type="button"
            onClick={handleGithubLogin}
            className="py-2.5 px-3 rounded-xl border border-violet-500/20 hover:border-violet-400/40 bg-violet-950/30 hover:bg-violet-900/30 text-xs font-medium text-white flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <FaGithub className="w-4 h-4" />
            <span>GitHub</span>
          </button>
        </div>

        <div className="pt-3 border-t border-violet-500/15 text-center text-xs text-violet-300/70">
          {isLogin ? "Need an account?" : "Already registered?"}{" "}
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="text-amber-400 hover:underline font-semibold cursor-pointer ml-1"
          >
            {isLogin ? "Create one" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
