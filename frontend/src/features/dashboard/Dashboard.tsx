import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { API_URL } from "../../lib/apiConfig";
import {
  BarChart3,
  Upload,
  Database,
  ArrowUpRight,
  RefreshCw,
  Server,
} from "lucide-react";

interface HealthState {
  status: "checking" | "online" | "offline";
  latencyMs: number | null;
  service: string | null;
  version: string | null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({
    status: "checking",
    latencyMs: null,
    service: null,
    version: null,
  });

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data } = await supabase.auth.getUser();
        if (data.user) {
          setUserName(
            data.user.user_metadata?.full_name ||
              data.user.email?.split("@")[0] ||
              null
          );
        }
      } catch {
        // Unauthenticated visitor
      }
    };
    fetchUser();
  }, []);

  const checkHealth = useCallback(async () => {
    setHealth((prev) => ({ ...prev, status: "checking" }));
    const started = performance.now();
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 8000);

    try {
      const res = await fetch(`${API_URL}/health`, { signal: controller.signal });
      const elapsed = Math.round(performance.now() - started);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setHealth({
        status: data?.status === "healthy" ? "online" : "offline",
        latencyMs: elapsed,
        service: data?.service || "Vectronyx API",
        version: data?.version || null,
      });
    } catch {
      setHealth({
        status: "offline",
        latencyMs: null,
        service: null,
        version: null,
      });
    } finally {
      window.clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Workspace Header */}
      <div className="rounded-3xl glass-card p-6 sm:p-8 border border-violet-500/20 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-display">
            {userName ? (
              <>
                Welcome back, <span className="text-gradient-vb">{userName}</span>
              </>
            ) : (
              "Vectronyx Workspace"
            )}
          </h1>

          <p className="text-sm text-violet-200/75 leading-relaxed">
            Upload CSV or TSV files for automated statistical profiling, IsolationForest anomaly
            detection, adaptive visualizations, and Power BI (.pbip) or Tableau (.twbx) exports.
          </p>

          <div className="pt-1">
            <button
              onClick={() => navigate("/data-analyst")}
              className="px-4 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-gradient-to-r from-violet-700 via-purple-800 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] shadow-lg shadow-violet-950/40 transition-all inline-flex items-center gap-2 cursor-pointer active:scale-95 border border-[#E8A276]/30"
            >
              <BarChart3 className="w-4 h-4 text-[#E8A276]" />
              <span>Open Data Analyst</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Live Backend Health Check */}
        <div className="lg:w-72 shrink-0 p-4 rounded-2xl glass-card-bronze border border-amber-500/25 space-y-2.5">
          <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
            <span className="text-xs font-bold text-amber-200 flex items-center gap-1.5 font-mono">
              <Server className="w-3.5 h-3.5 text-amber-400" />
              <span>Backend Status</span>
            </span>

            <button
              type="button"
              onClick={checkHealth}
              disabled={health.status === "checking"}
              className="text-[11px] font-mono text-amber-300 hover:text-white inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
              title="Re-check /health endpoint"
            >
              <RefreshCw
                className={`w-3 h-3 ${health.status === "checking" ? "animate-spin" : ""}`}
              />
              <span>Refresh</span>
            </button>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-violet-300/70 font-mono">State:</span>
              {health.status === "online" ? (
                <span className="inline-flex items-center gap-1.5 font-mono font-semibold text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Online
                </span>
              ) : health.status === "checking" ? (
                <span className="font-mono text-amber-300">Checking...</span>
              ) : (
                <span className="inline-flex items-center gap-1.5 font-mono font-semibold text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-400" />
                  Offline
                </span>
              )}
            </div>

            {health.latencyMs !== null && (
              <div className="flex justify-between items-center">
                <span className="text-violet-300/70 font-mono">Response Time:</span>
                <span className="font-mono font-semibold text-white">{health.latencyMs} ms</span>
              </div>
            )}

            <div className="flex justify-between items-center gap-2">
              <span className="text-violet-300/70 font-mono shrink-0">Endpoint:</span>
              <span className="font-mono text-[11px] text-amber-200/85 truncate" title={API_URL || "Same Origin"}>
                {API_URL || "Same Origin"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <button
          type="button"
          onClick={() => navigate("/data-analyst")}
          className="text-left p-6 rounded-2xl glass-card glass-card-hover border border-violet-500/20 flex flex-col justify-between gap-4 cursor-pointer group"
        >
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-violet-900/40 text-amber-400 flex items-center justify-center border border-violet-500/25">
              <Upload className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-white font-display flex items-center gap-2">
              <span>Analyze CSV / TSV Dataset</span>
              <ArrowUpRight className="w-4 h-4 text-violet-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </h2>
            <p className="text-xs text-violet-200/75 leading-relaxed">
              Ingest tabular data for quantile diagnostics, correlation heatmaps, ANOVA cohort
              variance, outlier detection, and BI project export.
            </p>
          </div>
          <span className="text-xs font-mono font-semibold text-amber-300">
            Open Data Analyst →
          </span>
        </button>

        <div className="p-6 rounded-2xl glass-card border border-amber-500/20 flex flex-col justify-between gap-4">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-amber-950/50 text-amber-400 flex items-center justify-center border border-amber-500/25">
              <Database className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-white font-display">
              Launch With Sample Dataset
            </h2>
            <p className="text-xs text-violet-200/75 leading-relaxed">
              Load a pre-configured SaaS or FinTech CSV directly into the Data Analyst workbench to
              inspect reports and export formats.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => navigate("/data-analyst?sample=saas")}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-violet-100 bg-violet-950/60 hover:bg-violet-900/60 border border-violet-500/30 transition cursor-pointer"
            >
              SaaS ARR Sample
            </button>
            <button
              type="button"
              onClick={() => navigate("/data-analyst?sample=fintech")}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-amber-200 bg-[#3D1C0B]/60 hover:bg-[#542A13]/60 border border-[#884F2E]/30 transition cursor-pointer"
            >
              FinTech Liquidity Sample
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
