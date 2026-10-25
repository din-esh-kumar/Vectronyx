// frontend/src/features/data-analyst/DataAnalyst.tsx
import React, { useState } from "react";
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  Download,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Code2,
  Copy,
  Check,
  RefreshCw,
  Layers,
  Database,
  Briefcase,
  ShieldAlert,
  Target,
  Award,
  FileText,
  Activity,
  SlidersHorizontal,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

const API_BASE = "http://localhost:8000/api/analyst";

// Curated enterprise dataset for instant evaluation
const SAMPLE_SAAS_CSV = `Region,Category,Revenue,Profit,Transactions,ChurnRate
North America,Enterprise Cloud,245000,78000,124,0.04
Europe,Enterprise Cloud,189000,56000,98,0.05
Asia Pacific,AI Workspaces,142000,41000,82,0.08
Latin America,Developer Tools,48000,12500,45,0.12
North America,Developer Tools,85000,24000,110,0.06
Europe,AI Workspaces,112000,34000,74,0.07
Middle East,Enterprise Cloud,96000,29000,38,0.09
North America,AI Workspaces,165000,52000,95,0.05
Europe,Developer Tools,62000,18000,68,0.08
Asia Pacific,Enterprise Cloud,135000,39000,71,0.07
`;

interface KPISpec {
  id: string;
  title: string;
  value: string;
  change?: string;
  trend: string;
  benchmark?: string;
  variance?: string;
  executive_takeaway?: string;
  formula_dax: string;
  formula_tableau: string;
  rationale: string;
}

interface ChartVisual {
  id: string;
  title: string;
  chart_type: string;
  x_axis: string;
  y_axis: string;
  aggregation: string;
  description: string;
  series_data: Array<{ name: string; value: number }>;
}

interface AnomalyFinding {
  row_index: number;
  score: number;
  explanation: string;
  root_cause_attribution?: string;
  business_impact?: string;
  action_required?: string;
  features: Record<string, any>;
}

interface StatisticalDiagnostic {
  metric_name: string;
  mean: number;
  std: number;
  skewness: number;
  kurtosis: number;
  cv: number;
  interpretation: string;
}

interface ConcentrationAnalysis {
  dimension: string;
  metric: string;
  top_20_percent_share: number;
  hhi_index: number;
  market_classification: string;
  strategic_takeaway: string;
}

interface StrategicInitiative {
  priority: string;
  time_horizon: string;
  title: string;
  rationale: string;
  expected_financial_impact: string;
  operational_owner: string;
  risk_level: string;
}

interface RiskAssessment {
  risk_title: string;
  severity: string;
  probability: string;
  business_exposure: string;
  mitigation_protocol: string;
}

interface ExecutiveDossier {
  executive_verdict: string;
  situation: string;
  complication: string;
  resolution: string;
  data_integrity_score: number;
  statistical_diagnostics: StatisticalDiagnostic[];
  concentration_risk?: ConcentrationAnalysis;
  strategic_initiatives: StrategicInitiative[];
  risk_matrix: RiskAssessment[];
  methodological_notes: string[];
}

interface DashboardPlan {
  title: string;
  summary: string;
  dataset_name: string;
  kpis: KPISpec[];
  visuals: ChartVisual[];
  anomalies: AnomalyFinding[];
  dossier?: ExecutiveDossier;
  dax_script: string;
  powerquery_m: string;
  tableau_calculated_fields: Array<{ caption: string; formula: string }>;
}

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"];

export default function DataAnalyst() {
  const [csvContent, setCsvContent] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [userPrompt, setUserPrompt] = useState<string>(
    "Comprehensive C-Suite econometric diagnosis: evaluate unit economics, concentration vulnerabilities, volatility tail-risks, and prioritized capital allocation initiatives."
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [dashboard, setDashboard] = useState<DashboardPlan | null>(null);
  const [activeTab, setActiveTab] = useState<"dossier" | "visuals" | "bi">("dossier");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  // Load sample dataset
  const handleLoadSample = () => {
    setCsvContent(SAMPLE_SAAS_CSV);
    setFileName("saas_enterprise_q3.csv");
    setErrorMsg("");
  };

  // Handle file drop/upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCsvContent(text);
      setErrorMsg("");
    };
    reader.readAsText(file);
  };

  // Generate Dashboard Plan via Backend API
  const handleGenerateDashboard = async () => {
    if (!csvContent.trim()) {
      setErrorMsg("Please upload a CSV or load the sample dataset first.");
      return;
    }
    setLoading(true);
    setErrorMsg("");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent);
      formData.append("prompt", userPrompt);
      formData.append("dataset_name", fileName || "dataset.csv");

      const res = await fetch(`${API_BASE}/generate-dashboard`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate dashboard");
      }

      const plan: DashboardPlan = await res.json();
      setDashboard(plan);
      setActiveTab("dossier"); // Default to the 30-year veteran dossier!
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to generate dashboard plan");
    } finally {
      setLoading(false);
    }
  };

  // Export Executive Dossier (.md)
  const handleExportDossier = async () => {
    if (!dashboard) return;
    setDownloadingFormat("dossier");

    try {
      const formData = new FormData();
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/dossier`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Exporting Executive Dossier failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Executive_Dossier.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Dossier export failed: ${err.message}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Export to Power BI (.pbip)
  const handleExportPowerBI = async () => {
    if (!dashboard || !csvContent) return;
    setDownloadingFormat("powerbi");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent);
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/powerbi`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Export to Power BI failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_PowerBI_Dashboard.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Power BI export failed: ${err.message}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Export to Tableau (.twbx)
  const handleExportTableau = async () => {
    if (!dashboard || !csvContent) return;
    setDownloadingFormat("tableau");

    try {
      const formData = new FormData();
      formData.append("raw_csv", csvContent);
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/tableau`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Export to Tableau failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dashboard.dataset_name.replace(".csv", "")}_Tableau_Dashboard.twbx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Tableau export failed: ${err.message}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const dossier = dashboard?.dossier;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-20">
      {/* 🏛️ Principal Analytics Header */}
      <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 border border-slate-800 rounded-3xl p-7 shadow-2xl backdrop-blur-md relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-semibold tracking-wider uppercase mb-2.5">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              Chief Analytics Officer • Principal Strategic Dossier
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Tabular Intelligence & Boardroom Dossier
            </h1>
            <p className="text-slate-400 text-sm mt-1.5 max-w-2xl leading-relaxed">
              Synthesize raw datasets through a 30-year veteran econometric lens:
              McKinsey SCR frameworks, Herfindahl-Hirschman concentration forensics,
              tail-risk diagnostics, and native Power BI (.pbip) & Tableau (.twbx) architectures.
            </p>
          </div>

          <button
            onClick={handleLoadSample}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-slate-700/80 text-xs font-medium transition shadow-sm self-start md:self-auto cursor-pointer"
          >
            <Database className="w-4 h-4 text-indigo-400" />
            Load Enterprise SaaS Data
          </button>
        </div>
      </div>

      {/* 📥 Ingestion & Strategic Mandate Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* CSV Dropzone */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <FileSpreadsheet className="w-4 h-4 text-indigo-600" />
              1. Empirical Data Ingestion
            </h2>

            <label className="border-2 border-dashed border-slate-300 hover:border-indigo-500 transition rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer bg-slate-50/50 hover:bg-indigo-50/20">
              <Upload className="w-8 h-8 text-indigo-600 mb-2" />
              <span className="text-sm font-medium text-slate-700 text-center">
                {fileName ? fileName : "Upload CSV / TSV Dataset"}
              </span>
              <span className="text-xs text-slate-400 mt-1">
                Zero local disk persistence • In-memory stream
              </span>
              <input
                type="file"
                accept=".csv,.tsv,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>

          {csvContent && (
            <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800 font-medium">
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-600" />
                Loaded: {fileName || "dataset.csv"}
              </span>
              <span>{csvContent.split("\n").filter(Boolean).length} observations</span>
            </div>
          )}
        </div>

        {/* Strategic Mandate & Prompt Box */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-violet-600" />
              2. Strategic Analytical Mandate
            </h2>

            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={3}
              placeholder="State the strategic inquiry or capital allocation question..."
              className="w-full text-sm border border-slate-200 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-800 resize-none font-sans"
            />

            {/* Strategic Quick Presets */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[
                "C-Suite Capital Allocation & Unit Margin Forensics",
                "Portfolio Concentration, HHI & Volatility Skew",
                "Customer Churn Risk & IsolationForest Outliers",
              ].map((chip) => (
                <button
                  key={chip}
                  onClick={() => setUserPrompt(chip)}
                  className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-indigo-50 text-slate-600 hover:text-indigo-600 transition"
                >
                  + {chip}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-100">
            <span className="text-xs text-slate-400">
              Generates Board Dossier + Recharts + Power BI PBIP + Tableau TWBX
            </span>
            <button
              onClick={handleGenerateDashboard}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-indigo-600 disabled:opacity-50 text-white font-medium text-sm transition shadow-md shadow-indigo-600/20 cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                  Synthesizing Dossier...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Generate Executive Dossier
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* 📑 Generated C-Suite Intelligence Suite */}
      {dashboard && (
        <div className="space-y-6 animate-fade-in">
          {/* Executive Header & Export Tray */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Data Integrity: {dossier?.data_integrity_score || 100}%
                </span>
                <span className="text-xs text-slate-400">
                  Source: {dashboard.dataset_name}
                </span>
              </div>
              <h2 className="text-2xl font-extrabold text-slate-900 mt-1">
                {dashboard.title}
              </h2>
              <p className="text-sm text-slate-600 mt-1 max-w-3xl leading-relaxed">
                {dashboard.summary}
              </p>
            </div>

            {/* Primary Action Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleExportDossier}
                disabled={downloadingFormat === "dossier"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs shadow-sm transition cursor-pointer"
                title="Download comprehensive McKinsey-style Board Dossier in Markdown"
              >
                <FileText className="w-3.5 h-3.5 text-amber-400" />
                {downloadingFormat === "dossier" ? "Exporting..." : "Download Dossier (.md)"}
              </button>

              <button
                onClick={handleExportPowerBI}
                disabled={downloadingFormat === "powerbi"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-medium text-xs shadow-sm transition cursor-pointer"
                title="Download complete Power BI Project (.pbip) package"
              >
                <Download className="w-3.5 h-3.5" />
                Power BI (.pbip)
              </button>

              <button
                onClick={handleExportTableau}
                disabled={downloadingFormat === "tableau"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition cursor-pointer"
                title="Download Tableau Workbook (.twbx) package"
              >
                <Download className="w-3.5 h-3.5" />
                Tableau (.twbx)
              </button>
            </div>
          </div>

          {/* 🧭 Navigation View Tabs */}
          <div className="flex border-b border-slate-200 gap-6 text-sm font-semibold text-slate-500">
            <button
              onClick={() => setActiveTab("dossier")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "dossier"
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent hover:text-slate-800"
              }`}
            >
              <Briefcase className="w-4 h-4" />
              1. C-Suite Strategic Dossier
            </button>
            <button
              onClick={() => setActiveTab("visuals")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "visuals"
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent hover:text-slate-800"
              }`}
            >
              <Activity className="w-4 h-4" />
              2. Visual Command Center
            </button>
            <button
              onClick={() => setActiveTab("bi")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "bi"
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent hover:text-slate-800"
              }`}
            >
              <Code2 className="w-4 h-4" />
              3. BI Code & Architecture
            </button>
          </div>

          {/* ============================================================== */}
          {/* TAB 1: 🏛️ C-SUITE STRATEGIC DOSSIER                             */}
          {/* ============================================================== */}
          {activeTab === "dossier" && dossier && (
            <div className="space-y-6">
              {/* Boardroom Executive Verdict */}
              <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-md border-l-4 border-amber-400">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-widest mb-1.5">
                  <Award className="w-4 h-4" />
                  Boardroom Executive Directive
                </div>
                <p className="text-base sm:text-lg font-medium text-slate-100 leading-relaxed">
                  "{dossier.executive_verdict}"
                </p>
              </div>

              {/* McKinsey SCR Framework (Situation - Complication - Resolution) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Situation */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700">
                    Situation (Baseline)
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Operational Reality</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {dossier.situation}
                  </p>
                </div>

                {/* Complication */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700">
                    Complication (Headwinds)
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Structural Vulnerabilities</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {dossier.complication}
                  </p>
                </div>

                {/* Resolution */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700">
                    Resolution (Intervention)
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Strategic Playbook</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {dossier.resolution}
                  </p>
                </div>
              </div>

              {/* Concentration Risk (HHI & Pareto 80/20) */}
              {dossier.concentration_risk && (
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="w-5 h-5 text-indigo-600" />
                      <h3 className="text-base font-bold text-slate-900">
                        Herfindahl-Hirschman (HHI) Concentration & Pareto Forensics
                      </h3>
                    </div>
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                      {dossier.concentration_risk.market_classification}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
                      <span className="text-xs text-slate-500 font-medium">Top 20% Quantile Concentration</span>
                      <div className="text-2xl font-black text-indigo-600 mt-1">
                        {dossier.concentration_risk.top_20_percent_share}%
                      </div>
                      <span className="text-[11px] text-slate-400">Share of total {dossier.concentration_risk.metric}</span>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
                      <span className="text-xs text-slate-500 font-medium">HHI Concentration Index</span>
                      <div className="text-2xl font-black text-slate-800 mt-1">
                        {dossier.concentration_risk.hhi_index}
                      </div>
                      <span className="text-[11px] text-slate-400">&gt;2,500 indicates acute single-point risk</span>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
                      <span className="text-xs text-slate-500 font-medium">Dimension Explored</span>
                      <div className="text-xl font-bold text-slate-800 mt-1 truncate">
                        {dossier.concentration_risk.dimension}
                      </div>
                      <span className="text-[11px] text-slate-400">Portfolio segment axis</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-700 bg-indigo-50/50 p-3.5 rounded-xl border border-indigo-100 leading-relaxed">
                    💡 <strong>Principal Takeaway:</strong> {dossier.concentration_risk.strategic_takeaway}
                  </p>
                </div>
              )}

              {/* Econometric Distribution Diagnostics */}
              {dossier.statistical_diagnostics.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm overflow-hidden">
                  <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-600" />
                    Econometric Distribution Diagnostics
                  </h3>
                  <p className="text-xs text-slate-500 mb-4">
                    Evaluates non-normal distribution behaviors, Pearson's skewness, and Coefficient of Variation ($CV = \sigma / \mu$).
                  </p>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-400 font-semibold uppercase tracking-wider">
                          <th className="py-2.5 px-3">Metric</th>
                          <th className="py-2.5 px-3">Mean</th>
                          <th className="py-2.5 px-3">Std Dev</th>
                          <th className="py-2.5 px-3">Skewness</th>
                          <th className="py-2.5 px-3">Kurtosis</th>
                          <th className="py-2.5 px-3">CV (Dispersion)</th>
                          <th className="py-2.5 px-3">Econometric Verdict</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {dossier.statistical_diagnostics.map((diag, i) => (
                          <tr key={i} className="hover:bg-slate-50/80 transition">
                            <td className="py-2.5 px-3 font-bold text-slate-900">{diag.metric_name}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.mean.toLocaleString()}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.std.toLocaleString()}</td>
                            <td className="py-2.5 px-3 font-mono font-semibold text-indigo-600">{diag.skewness}</td>
                            <td className="py-2.5 px-3 font-mono">{diag.kurtosis}</td>
                            <td className="py-2.5 px-3 font-mono font-semibold text-amber-600">{diag.cv}</td>
                            <td className="py-2.5 px-3 text-slate-500 max-w-xs">{diag.interpretation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Prioritized Strategic Action Roadmap (P0, P1, P2) */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-indigo-600" />
                    <h3 className="text-base font-bold text-slate-900">
                      Prioritized Strategic Action Roadmap
                    </h3>
                  </div>
                  <span className="text-xs text-slate-400">Boardroom Action Register</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {dossier.strategic_initiatives.map((init, i) => (
                    <div
                      key={i}
                      className="border border-slate-200 rounded-2xl p-4 flex flex-col justify-between hover:shadow-md transition bg-slate-50/40"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className={`px-2.5 py-0.5 rounded-full font-extrabold ${
                            init.priority.includes("P0")
                              ? "bg-rose-100 text-rose-800"
                              : init.priority.includes("P1")
                              ? "bg-amber-100 text-amber-800"
                              : "bg-blue-100 text-blue-800"
                          }`}>
                            {init.priority}
                          </span>
                          <span className="text-slate-400 text-[11px] font-medium">{init.time_horizon}</span>
                        </div>

                        <h4 className="text-sm font-bold text-slate-900 leading-snug">
                          {init.title}
                        </h4>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {init.rationale}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-200/80 space-y-1 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Expected Impact:</span>
                          <span className="font-bold text-emerald-700">{init.expected_financial_impact}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span>Owner: {init.operational_owner}</span>
                          <span>Risk: {init.risk_level}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk Mitigation Matrix */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-rose-600" />
                  <h3 className="text-base font-bold text-slate-900">
                    Governance & Downside Risk Matrix
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {dossier.risk_matrix.map((risk, i) => (
                    <div
                      key={i}
                      className="border border-rose-100 bg-rose-50/30 rounded-xl p-4 text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 text-sm">{risk.risk_title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-rose-200 text-rose-800">
                          {risk.severity} Severity
                        </span>
                      </div>
                      <p className="text-slate-700">
                        <strong>Exposure:</strong> {risk.business_exposure}
                      </p>
                      <div className="p-2.5 bg-white rounded-lg border border-rose-100 text-slate-600">
                        🛡️ <strong>Mitigation Protocol:</strong> {risk.mitigation_protocol}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 2: 📊 VISUAL COMMAND CENTER                                 */}
          {/* ============================================================== */}
          {activeTab === "visuals" && (
            <div className="space-y-6">
              {/* Executive KPI Scorecard */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {dashboard.kpis.map((kpi, idx) => (
                  <div
                    key={kpi.id || idx}
                    className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                      <span className="font-medium truncate">{kpi.title}</span>
                      {kpi.trend === "up" ? (
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                      ) : kpi.trend === "down" ? (
                        <TrendingDown className="w-4 h-4 text-rose-500" />
                      ) : (
                        <Layers className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">
                      {kpi.value}
                    </div>
                    {kpi.variance && (
                      <div className="text-xs font-semibold text-emerald-600 mt-1">
                        {kpi.variance} vs benchmark ({kpi.benchmark})
                      </div>
                    )}
                    <div className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500 line-clamp-2" title={kpi.executive_takeaway}>
                      💡 {kpi.executive_takeaway || kpi.rationale}
                    </div>
                  </div>
                ))}
              </div>

              {/* Visual Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {dashboard.visuals.map((vis, idx) => {
                  const color = CHART_COLORS[idx % CHART_COLORS.length];
                  return (
                    <div
                      key={vis.id || idx}
                      className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between min-h-[380px]"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h3 className="text-base font-bold text-slate-800">
                            {vis.title}
                          </h3>
                          <p className="text-xs text-slate-500">{vis.description}</p>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-slate-100 text-slate-600">
                          {vis.chart_type}
                        </span>
                      </div>

                      {/* Recharts Render */}
                      <div className="h-64 w-full mt-4">
                        {vis.series_data && vis.series_data.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                            {vis.chart_type === "line" ? (
                              <LineChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                                <YAxis stroke="#94a3b8" fontSize={11} />
                                <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px" }} />
                                <Line
                                  type="monotone"
                                  dataKey="value"
                                  stroke={color}
                                  strokeWidth={2.5}
                                  dot={{ r: 4 }}
                                />
                              </LineChart>
                            ) : vis.chart_type === "area" ? (
                              <AreaChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                                <YAxis stroke="#94a3b8" fontSize={11} />
                                <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px" }} />
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke={color}
                                  fill={color}
                                  fillOpacity={0.2}
                                />
                              </AreaChart>
                            ) : vis.chart_type === "pie" ? (
                              <PieChart>
                                <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px" }} />
                                <Pie
                                  data={vis.series_data}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={80}
                                  innerRadius={45}
                                >
                                  {vis.series_data.map((_, i) => (
                                    <Cell
                                      key={`cell-${i}`}
                                      fill={CHART_COLORS[i % CHART_COLORS.length]}
                                    />
                                  ))}
                                </Pie>
                                <Legend wrapperStyle={{ fontSize: "11px" }} />
                              </PieChart>
                            ) : (
                              <BarChart data={vis.series_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                                <YAxis stroke="#94a3b8" fontSize={11} />
                                <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px" }} />
                                <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} />
                              </BarChart>
                            )}
                          </ResponsiveContainer>
                        ) : (
                          <div className="h-full flex items-center justify-center text-xs text-slate-400">
                            No series data computed for {vis.title}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* IsolationForest Forensic Outlier Tray */}
              {dashboard.anomalies && dashboard.anomalies.length > 0 && (
                <div className="bg-amber-50/70 border border-amber-200/80 rounded-2xl p-5 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <h3 className="text-sm font-bold text-amber-900">
                      Scikit-Learn IsolationForest: Outlier Forensics
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {dashboard.anomalies.map((anom, i) => (
                      <div
                        key={i}
                        className="p-3.5 bg-white border border-amber-200 rounded-xl text-xs space-y-1.5 shadow-xs"
                      >
                        <div className="flex items-center justify-between font-bold text-slate-900">
                          <span>Observation #{anom.row_index + 1}</span>
                          <span className="text-amber-600 font-mono text-[11px]">Score: {anom.score}</span>
                        </div>
                        <p className="text-slate-600 text-[11px]">{anom.explanation}</p>
                        {anom.root_cause_attribution && (
                          <p className="text-[11px] text-slate-700">
                            <strong>Root Cause:</strong> {anom.root_cause_attribution}
                          </p>
                        )}
                        {anom.action_required && (
                          <div className="p-2 bg-amber-50/60 rounded border border-amber-100 text-[10px] text-amber-900 font-medium">
                            🚨 <strong>Action:</strong> {anom.action_required}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 3: ⚡ BI DEPLOYMENT (POWER BI & TABLEAU)                   */}
          {/* ============================================================== */}
          {activeTab === "bi" && (
            <div className="space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      Enterprise BI Deployment Architecture
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Export compiled native project packages or inspect DAX and Tableau calculations directly.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleExportPowerBI}
                      disabled={downloadingFormat === "powerbi"}
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-medium text-xs shadow-sm transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Power BI (.pbip)
                    </button>
                    <button
                      onClick={handleExportTableau}
                      disabled={downloadingFormat === "tableau"}
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Tableau (.twbx)
                    </button>
                  </div>
                </div>

                {/* Staging & Code blocks */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
                  {/* Power BI DAX & M */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Code2 className="w-4 h-4 text-amber-500" />
                        Power BI DAX Measures
                      </span>
                      <button
                        onClick={() => copyToClipboard(dashboard.dax_script, "dax_tab")}
                        className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "dax_tab" ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedKey === "dax_tab" ? "Copied" : "Copy DAX"}
                      </button>
                    </div>
                    <pre className="p-3 bg-slate-900 text-amber-300 font-mono text-xs rounded-xl overflow-x-auto max-h-64">
                      {dashboard.dax_script}
                    </pre>

                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block pt-2">
                      Power Query (M) Script
                    </span>
                    <pre className="p-3 bg-slate-900 text-sky-300 font-mono text-xs rounded-xl overflow-x-auto max-h-40">
                      {dashboard.powerquery_m}
                    </pre>
                  </div>

                  {/* Tableau Calculated Fields */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Code2 className="w-4 h-4 text-sky-600" />
                        Tableau Calculated Fields
                      </span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            dashboard.tableau_calculated_fields
                              .map((c) => `// ${c.caption}\n${c.formula}`)
                              .join("\n\n"),
                            "tableau_tab"
                          )
                        }
                        className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "tableau_tab" ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedKey === "tableau_tab" ? "Copied" : "Copy All"}
                      </button>
                    </div>

                    <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                      {dashboard.tableau_calculated_fields.map((calc, i) => (
                        <div key={i} className="p-2.5 bg-white border border-slate-200 rounded-xl">
                          <div className="text-xs font-bold text-slate-800 mb-1">
                            {calc.caption}
                          </div>
                          <pre className="text-xs font-mono text-sky-700 bg-slate-50 p-2 rounded border border-slate-100">
                            {calc.formula}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}