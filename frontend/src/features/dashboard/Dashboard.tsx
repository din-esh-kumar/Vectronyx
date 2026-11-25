import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import {
  BarChart3,
  Upload,
  Database,
  ArrowUpRight,
} from "lucide-react";

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState<string | null>(null);

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
