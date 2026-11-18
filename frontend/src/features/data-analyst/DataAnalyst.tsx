// frontend/src/features/data-analyst/DataAnalyst.tsx
import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Award,
  Briefcase,
  Check,
  Code2,
  Copy,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  Layers,
  Printer,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Upload,
  X,
  Zap,
} from "lucide-react";
import toast from "react-hot-toast";
import { fetchEventStream } from "../../lib/sse";
import { API_URL } from "../../lib/apiConfig";
import {
  generatePowerBiPbipZipBlob,
  sanitizePowerBiFilenameBase,
  stripDatasetExtension,
} from "../../lib/powerbiExport";
import { CorrelationHeatmap } from "./CorrelationHeatmap";
import {
  DataGovernanceSection,
  OutlierForensicsSection,
  QuantileDiagnosticsSection,
  SegmentBenchmarksSection,
} from "./QuantitativeSections";
import { ReportCharts } from "./ReportCharts";
import {
  SAMPLE_FINTECH_CSV,
  SAMPLE_SAAS_CSV,
  getFallbackPlan,
  getFintechPlan,
} from "./fallbackPlans";
import { buildClientDossierMarkdown, inspectCsvMetadata } from "./formatters";
import type { DashboardPlan, KPISpec } from "./types";

const API_BASE = `${API_URL}/api/analyst`;

const SectionHeader: React.FC<{
  number: string;
  title: string;
  subtitle?: string;
}> = ({ number, title, subtitle }) => (
  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 pb-2 border-b border-violet-500/15">
    <div className="flex items-baseline gap-2.5">
      <span className="font-mono text-xs font-bold text-amber-400 tracking-widest">
        {number}
      </span>
      <h3 className="text-base sm:text-lg font-extrabold text-white font-display tracking-tight">
        {title}
      </h3>
    </div>
    {subtitle && (
      <span className="text-xs font-mono text-violet-300/65">{subtitle}</span>
    )}
  </div>
);

const KpiScorecardGrid: React.FC<{ kpis: KPISpec[] }> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 print-break-avoid">
      {kpis.map((kpi, idx) => (
        <div
          key={kpi.id || idx}
          className="p-5 rounded-2xl glass-card border border-violet-500/20 hover:border-violet-400/40 transition flex flex-col justify-between gap-2"
        >
          <div>
            <div className="flex items-center justify-between text-xs text-violet-300/75 mb-1 gap-2">
              <span className="font-semibold truncate" title={kpi.title}>
                {kpi.title}
              </span>
              {kpi.trend === "up" ? (
                <TrendingUp className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : kpi.trend === "down" ? (
                <TrendingDown className="w-4 h-4 text-rose-400 shrink-0" />
              ) : (
                <Layers className="w-4 h-4 text-amber-400 shrink-0" />
              )}
            </div>
            <div className="text-2xl font-extrabold text-white mt-1 font-mono tracking-tight">
              {kpi.value}
            </div>
            {(kpi.change || kpi.variance || kpi.benchmark) && (
              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] font-mono">
                {kpi.change && (
                  <span className="text-amber-300 font-semibold">{kpi.change}</span>
                )}
                {kpi.benchmark && (
                  <span className="text-violet-300/75">• {kpi.benchmark}</span>
                )}
                {kpi.variance && (
                  <span className="text-emerald-400">• {kpi.variance}</span>
                )}
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-violet-500/15 text-[11px] text-violet-200/75 leading-relaxed line-clamp-3">
            {kpi.executive_takeaway || kpi.rationale}
          </div>
        </div>
      ))}
    </div>
  );
};

const DEFAULT_PROMPT =
  "Comprehensive Principal Data Analyst audit: evaluate metric distributions, feature correlations, cohort variance drivers, anomaly forensics, and strategic ROI actions.";

export default function DataAnalyst() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSample = searchParams.get("sample");

  const [csvContent, setCsvContent] = useState<string>(() =>
    initialSample === "saas"
      ? SAMPLE_SAAS_CSV
      : initialSample === "fintech"
      ? SAMPLE_FINTECH_CSV
      : ""
  );
  const [fileName, setFileName] = useState<string>(() =>
    initialSample === "saas"
      ? "saas_enterprise_q3.csv"
      : initialSample === "fintech"
      ? "fintech_global_volume.csv"
      : ""
  );
  const [userPrompt, setUserPrompt] = useState<string>(() =>
    initialSample === "fintech"
      ? "Cross-border FinTech liquidity audit: analyze corridor take-rates, settlement latency vs chargebacks, and anomaly tail risks."
      : DEFAULT_PROMPT
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [streamingStatus, setStreamingStatus] = useState<string>("");
  const [iterationLog, setIterationLog] = useState<string[]>([]);
  const [refinementIterations, setRefinementIterations] = useState<number>(3);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [dashboard, setDashboard] = useState<DashboardPlan | null>(() =>
    initialSample === "saas"
      ? getFallbackPlan("saas_enterprise_q3.csv")
      : initialSample === "fintech"
      ? getFintechPlan()
      : null
  );
  const [activeTab, setActiveTab] = useState<"dossier" | "visuals" | "bi">("dossier");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  useEffect(() => {
    const sample = searchParams.get("sample");
    if (sample === "saas") {
      setCsvContent(SAMPLE_SAAS_CSV);
      setFileName("saas_enterprise_q3.csv");
      setDashboard(getFallbackPlan("saas_enterprise_q3.csv"));
      setUserPrompt(DEFAULT_PROMPT);
      setErrorMsg("");
    } else if (sample === "fintech") {
      setCsvContent(SAMPLE_FINTECH_CSV);
      setFileName("fintech_global_volume.csv");
      setDashboard(getFintechPlan());
      setUserPrompt(
        "Cross-border FinTech liquidity audit: analyze corridor take-rates, settlement latency vs chargebacks, and anomaly tail risks."
      );
      setErrorMsg("");
    }
  }, [searchParams]);

  // Semantic CSV header & column role inspection (quoted-CSV safe, excludes ID columns)
  const csvMeta = useMemo(() => inspectCsvMetadata(csvContent), [csvContent]);

  // Dynamic dataset-aware prompt suggestions (never suggests IDs like isbn10 / bookID)
  const dynamicPromptChips = useMemo(() => {
    if (csvMeta.nonIdHeaders.length === 0) {
      return [
        "Principal Analyst Audit: Distributions, Correlations & Cohort Drivers",
        "Portfolio Concentration (HHI), Pareto 80/20 & Volatility Forensics",
        "IsolationForest Outlier Forensics & Non-Parametric Quantile Review",
      ];
    }

    const numerics = csvMeta.numericCandidates;
    const cats = csvMeta.categoricalCandidates;
    const primaryNum =
      numerics[0] || csvMeta.nonIdHeaders[1] || csvMeta.nonIdHeaders[0] || "Metrics";
    const secNum = numerics[1] || numerics[0] || "Efficiency";
    const primaryCat = cats[0] || csvMeta.nonIdHeaders[0] || "Cohorts";

    return [
      `Analyze ${primaryNum} distribution, quantiles, and cohort drivers across ${primaryCat}`,
      `Evaluate feature correlations between ${primaryNum} and ${secNum} with outlier forensics`,
      `Conduct Pareto 80/20 concentration and ANOVA variance audit on ${primaryNum} by ${primaryCat}`,
    ];
  }, [csvMeta]);

  const handleLoadSample = () => {
    setCsvContent(SAMPLE_SAAS_CSV);
    setFileName("saas_enterprise_q3.csv");
    setDashboard(getFallbackPlan("saas_enterprise_q3.csv"));
    setUserPrompt(DEFAULT_PROMPT);
    setErrorMsg("");
    if (searchParams.has("sample")) setSearchParams({});
    toast.success("Loaded Enterprise SaaS sample");
  };

  const handleLoadFintechSample = () => {
    setCsvContent(SAMPLE_FINTECH_CSV);
    setFileName("fintech_global_volume.csv");
    setDashboard(getFintechPlan());
    setUserPrompt(
      "Cross-border FinTech liquidity audit: analyze corridor take-rates, settlement latency vs chargebacks, and anomaly tail risks."
    );
    setErrorMsg("");
    if (searchParams.has("sample")) setSearchParams({});
    toast.success("Loaded FinTech liquidity sample");
  };

  const handleClearWorkspace = () => {
    setCsvContent("");
    setFileName("");
    setDashboard(null);
    setUserPrompt(DEFAULT_PROMPT);
    setErrorMsg("");
    setStreamingStatus("");
    if (searchParams.has("sample")) setSearchParams({});
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCsvContent(text);
      setDashboard(null);
      setErrorMsg("");
      if (searchParams.has("sample")) setSearchParams({});
      toast.success(`Loaded ${file.name}`);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleGenerateDashboard = async () => {
    if (!csvContent.trim()) {
      setErrorMsg("Please upload a CSV or load a sample dataset first.");
      toast.error("Please load or upload a CSV dataset");
      return;
    }
    setLoading(true);
    setStreamingStatus(`Initiating ${refinementIterations}-pass Principal Analyst pipeline (16K max tokens)...`);
    setIterationLog([]);
    setErrorMsg("");

    try {
      const datasetFilename = fileName || "dataset.csv";
      const createAnalysisFormData = () => {
        const fd = new FormData();
        fd.append("file", new Blob([csvContent], { type: "text/csv" }), datasetFilename);
        fd.append("prompt", userPrompt);
        fd.append("dataset_name", datasetFilename);
        fd.append("refinement_iterations", String(refinementIterations));
        fd.append("target_quality_score", "92");
        return fd;
      };

      let receivedPlan: DashboardPlan | null = null;
      let lastError = "";

      try {
        await fetchEventStream(
          `${API_BASE}/generate-dashboard/stream`,
          {
            method: "POST",
            body: createAnalysisFormData(),
          },
          {
            onStatus: (data) => {
              setStreamingStatus(data.message);
              setIterationLog((prev) => [...prev.slice(-7), data.message]);
              toast.loading(data.message, { id: "analyst-toast" });
            },
            onComplete: (completedPlan) => {
              receivedPlan = completedPlan;
            },
            onError: (err) => {
              lastError = err.message || "Streaming analysis interrupted";
            },
          }
        );
      } catch (streamErr: any) {
        lastError = streamErr?.message || "Streaming request failed";
      }

      if (!receivedPlan) {
        try {
          const restRes = await fetch(`${API_BASE}/generate-dashboard`, {
            method: "POST",
            body: createAnalysisFormData(),
          });
          const restContentType = restRes.headers.get("content-type") || "";
          if (restRes.ok && restContentType.includes("application/json")) {
            receivedPlan = await restRes.json();
          } else {
            lastError = `Backend returned HTTP ${restRes.status}`;
          }
        } catch (restErr: any) {
          lastError = restErr?.message || lastError || "Backend request failed";
        }
      }

      if (!receivedPlan) {
        if (csvContent === SAMPLE_SAAS_CSV) {
          receivedPlan = getFallbackPlan("saas_enterprise_q3.csv");
          toast("Loaded offline SaaS sample report", { id: "analyst-toast" });
        } else if (csvContent === SAMPLE_FINTECH_CSV) {
          receivedPlan = getFintechPlan();
          toast("Loaded offline FinTech sample report", { id: "analyst-toast" });
        } else {
          const msg =
            lastError && lastError !== "Streaming analysis interrupted"
              ? `Analysis failed (${lastError}). Verify the backend service is running and try again.`
              : "Unable to generate report from backend API. Verify backend connectivity and try again.";
          setErrorMsg(msg);
          toast.error("Failed to generate report", { id: "analyst-toast" });
          return;
        }
      } else {
        toast.success("Analysis report ready", { id: "analyst-toast" });
      }

      setDashboard(receivedPlan);
      setActiveTab("dossier");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to generate analysis report");
      toast.error("Failed to generate report", { id: "analyst-toast" });
    } finally {
      setLoading(false);
      setStreamingStatus("");
    }
  };

  const handleExportDossier = async () => {
    if (!dashboard) return;
    setDownloadingFormat("dossier");
    const baseName = stripDatasetExtension(dashboard.dataset_name) || "Vectronyx";

    try {
      const formData = new FormData();
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/dossier`, {
        method: "POST",
        body: formData,
      });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok || contentType.includes("text/html")) {
        throw new Error("Fallback to client export");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${baseName}_Executive_Dossier.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      const mdContent = buildClientDossierMarkdown(dashboard);
      const blob = new Blob([mdContent], { type: "text/markdown" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${baseName}_Executive_Dossier.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloadingFormat(null);
      toast.success("Dossier exported as Markdown");
    }
  };

  const handleExportPowerBI = async () => {
    if (!dashboard || !csvContent.trim()) {
      toast.error("Dataset CSV required for Power BI export");
      return;
    }
    setDownloadingFormat("powerbi");

    const datasetFilename = dashboard.dataset_name || fileName || "dataset.csv";
    const filenameBase = sanitizePowerBiFilenameBase(datasetFilename);
    const effectiveCsv = csvContent;

    const triggerDownload = (blob: Blob, downloadName: string) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    };

    try {
      const formData = new FormData();
      formData.append(
        "file",
        new Blob([effectiveCsv], { type: "text/csv" }),
        datasetFilename
      );
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/powerbi`, {
        method: "POST",
        body: formData,
      });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok || contentType.includes("text/html")) {
        throw new Error("Fallback to client Power BI bundle");
      }

      const blob = await res.blob();
      triggerDownload(blob, `${filenameBase}_PowerBI_Dashboard.zip`);
      toast.success("Power BI (.pbip) package exported");
    } catch {
      const blob = generatePowerBiPbipZipBlob(
        {
          title: dashboard.title,
          dataset_name: datasetFilename,
          kpis: dashboard.kpis,
          visuals: dashboard.visuals,
          dax_script: dashboard.dax_script,
          powerquery_m: dashboard.powerquery_m,
        },
        effectiveCsv
      );
      triggerDownload(blob, `${filenameBase}_PowerBI_Dashboard.zip`);
      toast.success("Power BI (.pbip) package exported (client bundle)");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleExportTableau = async () => {
    if (!dashboard || !csvContent.trim()) {
      toast.error("Dataset CSV required for Tableau export");
      return;
    }
    setDownloadingFormat("tableau");
    const datasetFilename = dashboard.dataset_name || fileName || "dataset.csv";
    const baseName = stripDatasetExtension(datasetFilename) || "Vectronyx_Dashboard";
    const effectiveCsv = csvContent;

    try {
      const formData = new FormData();
      formData.append(
        "file",
        new Blob([effectiveCsv], { type: "text/csv" }),
        datasetFilename
      );
      formData.append("plan_json", JSON.stringify(dashboard));

      const res = await fetch(`${API_BASE}/export/tableau`, {
        method: "POST",
        body: formData,
      });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok || contentType.includes("text/html")) {
        throw new Error("Fallback to client bundle");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${baseName}_Tableau_Dashboard.twbx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Tableau workbook exported");
    } catch {
      const content = dashboard.tableau_calculated_fields
        .map((c) => `// ${c.caption}\n${c.formula}`)
        .join("\n\n");
      const blob = new Blob([content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${baseName}_Tableau_Fields.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Tableau fields exported");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handlePrintPdf = () => {
    if (activeTab !== "dossier") {
      setActiveTab("dossier");
      setTimeout(() => window.print(), 150);
    } else {
      window.print();
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const dossier = dashboard?.dossier;
  const audit = dossier?.data_quality_audit;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-20 animate-fadeIn">
      {/* Compact Header & Sample Presets */}
      <div className="no-print flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-display">
            Data Analyst
          </h1>
          <p className="text-violet-200/70 text-xs sm:text-sm mt-1">
            Statistical profiling, adaptive visualizations, anomaly detection, and Power BI / Tableau export.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
          <button
            type="button"
            onClick={handleLoadSample}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer active:scale-95 border ${
              fileName === "saas_enterprise_q3.csv"
                ? "bg-gradient-to-r from-violet-700 to-purple-800 text-white border-violet-400/60"
                : "bg-violet-950/60 hover:bg-violet-900/60 text-violet-200 border-violet-500/30"
            }`}
          >
            <Database className="w-3.5 h-3.5 text-amber-400" />
            <span>SaaS Sample</span>
          </button>

          <button
            type="button"
            onClick={handleLoadFintechSample}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer active:scale-95 border ${
              fileName === "fintech_global_volume.csv"
                ? "bg-gradient-to-r from-[#884F2E] to-[#542A13] text-white border-[#BD8E70]"
                : "bg-[#3D1C0B]/60 hover:bg-[#542A13]/60 text-amber-200 border-[#884F2E]/30"
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>FinTech Sample</span>
          </button>

          {(csvContent || dashboard) && (
            <button
              type="button"
              onClick={handleClearWorkspace}
              className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-medium text-violet-300/80 hover:text-white bg-violet-950/40 hover:bg-violet-900/50 border border-violet-500/20 transition cursor-pointer"
              title="Reset dataset and report"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Dataset Ingestion & Analysis Prompt */}
      <div className="no-print grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 p-5 rounded-2xl glass-card border border-violet-500/20 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <FileSpreadsheet className="w-4 h-4 text-amber-400" />
              <span>1. Dataset Upload</span>
            </h2>

            <label className="border-2 border-dashed border-violet-500/30 hover:border-amber-400/50 transition rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer bg-violet-950/20 hover:bg-violet-950/40">
              <Upload className="w-7 h-7 text-amber-400 mb-2" />
              <span className="text-sm font-medium text-violet-100 text-center">
                {fileName ? fileName : "Upload CSV / TSV Dataset"}
              </span>
              <span className="text-xs text-violet-400/60 mt-1 font-mono">
                Click to select a file
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
            <div className="space-y-1.5">
              <div className="p-3 bg-violet-900/30 border border-violet-500/30 rounded-xl flex items-center justify-between text-xs text-amber-300 font-mono">
                <span className="flex items-center gap-2 truncate">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="truncate">{fileName || "dataset.csv"}</span>
                </span>
                <span className="shrink-0">
                  {csvMeta.approxRows.toLocaleString()} rows × {csvMeta.headers.length} cols
                </span>
              </div>
              {csvMeta.excludedIds.length > 0 && (
                <div className="px-3 py-1.5 rounded-lg bg-amber-950/35 border border-amber-500/20 text-[11px] font-mono text-amber-300">
                  Excluded ID keys: {csvMeta.excludedIds.join(", ")}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="lg:col-span-7 p-5 rounded-2xl glass-card-bronze border border-amber-500/25 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-amber-200 flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-amber-400" />
              <span>2. Analysis Prompt</span>
            </h2>

            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={3}
              placeholder="State the analytical objective, variance question, or decision hypothesis..."
              className="w-full text-xs sm:text-sm border border-violet-500/25 bg-violet-950/40 rounded-xl p-3 focus-vb text-white resize-none font-sans placeholder-violet-400/40"
            />

            <div className="flex flex-wrap gap-1.5 mt-2">
              {dynamicPromptChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => setUserPrompt(chip)}
                  className="text-xs px-2.5 py-1 rounded-lg bg-violet-900/30 hover:bg-violet-800/40 text-violet-200 border border-violet-500/20 transition cursor-pointer text-left"
                >
                  + {chip}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3 pt-3 border-t border-amber-500/15">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
                <span className="text-amber-300/90 font-semibold">Refinement Passes (16K Max Tokens):</span>
                {[
                  { n: 1, label: "1× Draft" },
                  { n: 3, label: "3× Senior" },
                  { n: 5, label: "5× Principal" },
                  { n: 8, label: "8× Boardroom" },
                ].map((opt) => (
                  <button
                    key={opt.n}
                    type="button"
                    disabled={loading}
                    onClick={() => setRefinementIterations(opt.n)}
                    className={`px-2.5 py-1 rounded-lg border transition cursor-pointer ${
                      refinementIterations === opt.n
                        ? "bg-amber-500/25 text-amber-200 border-amber-400/60 font-bold"
                        : "bg-violet-950/50 text-violet-300/75 border-violet-500/20 hover:border-amber-400/35"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <span className="text-[10px] font-mono text-emerald-300/80">
                Target ≥ 92/100 · 3-Page Power BI (.pbip)
              </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                {loading && streamingStatus && (
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-mono text-amber-300 animate-fadeIn">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0 text-amber-400" />
                      <span className="truncate">{streamingStatus}</span>
                    </div>
                    {iterationLog.length > 1 && (
                      <div className="max-h-20 overflow-y-auto space-y-0.5 pl-5 text-[10px] font-mono text-violet-300/70">
                        {iterationLog.slice(0, -1).map((line, i) => (
                          <div key={i} className="truncate">
                            ✓ {line}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={handleGenerateDashboard}
                disabled={loading}
                className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-700 via-purple-800 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] disabled:opacity-50 text-white font-bold text-xs sm:text-sm transition shadow-lg shadow-violet-950/40 cursor-pointer active:scale-95 border border-[#E8A276]/30 shrink-0"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-[#E8A276]" />
                    <span>Refining ({refinementIterations}×)...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-[#E8A276]" />
                    <span>Generate Principal Report ({refinementIterations}×)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Compiled Principal Analysis Report */}
      {dashboard && (
        <div className="space-y-6 sm:space-y-8 animate-fadeIn">
          {/* Report Masthead & Export Actions */}
          <div className="p-6 rounded-3xl glass-card border border-violet-500/20 flex flex-col lg:flex-row lg:items-center justify-between gap-4 print-break-avoid">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-violet-900/50 text-violet-300 border border-violet-500/30">
                  Data Integrity: {dossier?.data_integrity_score ?? 100}%
                </span>
                {typeof dashboard.quality_score === "number" && (
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${
                      dashboard.quality_score >= 92
                        ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/40"
                        : "bg-amber-950/60 text-amber-300 border-amber-500/40"
                    }`}
                  >
                    Principal Quality: {dashboard.quality_score.toFixed(1)}/100
                    {dashboard.refinement_iterations_run ? ` (${dashboard.refinement_iterations_run}× Pass)` : ""}
                  </span>
                )}
                {audit && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-emerald-950/50 text-emerald-300 border border-emerald-500/30">
                    {audit.total_rows.toLocaleString()} Rows × {audit.total_columns} Cols ({audit.completeness_pct.toFixed(1)}% Complete)
                  </span>
                )}
                <span className="text-xs font-mono text-amber-400/90">
                  Source: {dashboard.dataset_name}
                </span>
              </div>

              <h2 className="text-xl sm:text-2xl font-extrabold text-white font-display">
                {dashboard.title}
              </h2>
              <p className="text-xs sm:text-sm text-violet-200/75 max-w-3xl leading-relaxed">
                {dashboard.summary}
              </p>
            </div>

            <div className="no-print flex flex-wrap items-center gap-2 shrink-0">
              <button
                onClick={handleExportDossier}
                disabled={downloadingFormat === "dossier"}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-violet-900/40 hover:bg-violet-800/50 text-white font-medium text-xs border border-violet-500/25 transition cursor-pointer"
                title="Download full Markdown technical report"
              >
                <FileText className="w-3.5 h-3.5 text-amber-400" />
                <span>{downloadingFormat === "dossier" ? "Exporting..." : "Report (.md)"}</span>
              </button>

              <button
                onClick={handlePrintPdf}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-100 font-medium text-xs border border-violet-500/25 transition cursor-pointer"
                title="Print or save report as Executive PDF"
              >
                <Printer className="w-3.5 h-3.5 text-amber-400" />
                <span>Print / PDF</span>
              </button>

              <button
                onClick={handleExportPowerBI}
                disabled={downloadingFormat === "powerbi"}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 font-medium text-xs border border-amber-500/30 transition cursor-pointer"
                title="Download Power BI Project (.pbip ZIP)"
              >
                <Download className="w-3.5 h-3.5 text-amber-400" />
                <span>{downloadingFormat === "powerbi" ? "Exporting..." : "Power BI (.pbip)"}</span>
              </button>

              <button
                onClick={handleExportTableau}
                disabled={downloadingFormat === "tableau"}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-200 font-medium text-xs border border-violet-500/30 transition cursor-pointer"
                title="Download Tableau Workbook (.twbx)"
              >
                <Download className="w-3.5 h-3.5 text-violet-400" />
                <span>{downloadingFormat === "tableau" ? "Exporting..." : "Tableau (.twbx)"}</span>
              </button>
            </div>
          </div>

          {/* Navigation View Tabs */}
          <div className="no-print flex flex-wrap border-b border-violet-500/15 gap-4 sm:gap-6 text-xs sm:text-sm font-semibold">
            <button
              onClick={() => setActiveTab("dossier")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "dossier"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Briefcase className="w-4 h-4" />
              <span>1. Executive Analysis Report</span>
            </button>
            <button
              onClick={() => setActiveTab("visuals")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "visuals"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>2. Visual Command Center</span>
            </button>
            <button
              onClick={() => setActiveTab("bi")}
              className={`pb-3 border-b-2 flex items-center gap-2 transition cursor-pointer ${
                activeTab === "bi"
                  ? "border-amber-400 text-amber-300"
                  : "border-transparent text-violet-300/60 hover:text-violet-100"
              }`}
            >
              <Code2 className="w-4 h-4" />
              <span>3. BI Architecture & DAX</span>
            </button>
          </div>

          {/* =================================================================
              TAB 1: COHESIVE PRINCIPAL DATA ANALYST REPORT (01 -> 08)
             ================================================================= */}
          {activeTab === "dossier" && (
            <div className="space-y-8">
              {/* Analytical Scope Strip */}
              {(dashboard.focused_metrics?.length || dashboard.analytical_intent) && (
                <div className="flex flex-wrap items-center gap-2 p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/25 text-xs">
                  <div className="flex items-center gap-1.5 text-amber-300 font-mono font-medium">
                    <Target className="w-3.5 h-3.5 text-amber-400" />
                    <span>Analytical Focus:</span>
                  </div>
                  {dashboard.analytical_intent && (
                    <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase font-mono text-[10px]">
                      {dashboard.analytical_intent.replace(/_/g, " ")}
                    </span>
                  )}
                  {dashboard.focused_metrics && dashboard.focused_metrics.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-violet-300">
                      <span className="text-violet-400/70">Target Metrics:</span>
                      {dashboard.focused_metrics.map((m) => (
                        <span
                          key={m}
                          className="px-2 py-0.5 rounded bg-violet-800/40 text-violet-200 border border-violet-500/25 font-mono text-[11px]"
                        >
                          {m}
                        </span>
                      ))}
                    </div>
                  )}
                  {dashboard.focused_dimensions && dashboard.focused_dimensions.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-violet-300">
                      <span className="text-violet-400/70">Cohorts:</span>
                      {dashboard.focused_dimensions.map((d) => (
                        <span
                          key={d}
                          className="px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-500/25 font-mono text-[11px]"
                        >
                          {d}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Iterative Peer-Review Quality Audit Trail */}
              {dashboard.refinement_history && dashboard.refinement_history.length > 0 && (
                <div className="p-5 rounded-2xl glass-card border border-emerald-500/25 space-y-4 print-break-avoid">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Award className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-sm font-bold text-white font-display">
                        Principal Peer-Review &amp; Iterative Refinement Audit
                      </h4>
                    </div>
                    <span className="text-xs font-mono text-emerald-300">
                      Score Progression:{" "}
                      {dashboard.refinement_history.map((r) => `${r.score.toFixed(0)}`).join(" → ")} / 100
                    </span>
                  </div>

                  {(() => {
                    const latest = dashboard.refinement_history[dashboard.refinement_history.length - 1];
                    const rubricEntries = Object.entries(latest.rubric_scores || {});
                    return (
                      <>
                        {rubricEntries.length > 0 && (
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                            {rubricEntries.map(([axis, val]) => (
                              <div
                                key={axis}
                                className="p-2.5 rounded-xl bg-violet-950/45 border border-violet-500/20 space-y-1"
                              >
                                <div className="text-[10px] font-mono text-violet-300/75 capitalize truncate">
                                  {axis.replace(/_/g, " ")}
                                </div>
                                <div className="text-sm font-extrabold font-mono text-white">
                                  {Number(val).toFixed(0)}/100
                                </div>
                                <div className="h-1.5 rounded-full bg-violet-950 overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-gradient-to-r from-amber-400 to-emerald-400"
                                    style={{ width: `${Math.min(100, Math.max(0, Number(val)))}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
                          {dashboard.refinement_history.map((rec) => (
                            <div
                              key={rec.iteration}
                              className="p-3 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-1.5"
                            >
                              <div className="flex items-center justify-between font-mono text-[11px]">
                                <span className="font-bold text-amber-300">Pass #{rec.iteration}</span>
                                <span className="text-emerald-300 font-bold">
                                  {rec.score.toFixed(1)}/100 ·{" "}
                                  {rec.verdict === "expert_certified" ? "Certified" : "Refined"}
                                </span>
                              </div>
                              {rec.improvements_applied && rec.improvements_applied.length > 0 && (
                                <ul className="space-y-0.5 text-[11px] text-violet-200/80 list-disc pl-4">
                                  {rec.improvements_applied.slice(0, 3).map((imp, idx) => (
                                    <li key={idx}>{imp}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* 01. EXECUTIVE KPI SCORECARD */}
              <div className="space-y-3">
                <SectionHeader
                  number="01"
                  title="Executive KPI Scorecard"
                  subtitle="Mean vs Median, P75 & P95 Benchmarks"
                />
                <KpiScorecardGrid kpis={dashboard.kpis} />
              </div>

              {/* 02. BOARDROOM VERDICT & SCR THESIS */}
              {dossier && (
                <div className="space-y-4 print-break-avoid">
                  <SectionHeader
                    number="02"
                    title="Executive Verdict & SCR Synthesis"
                    subtitle="Situation → Complication → Resolution"
                  />

                  <div className="rounded-2xl p-6 glass-card-bronze border border-amber-500/30">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-widest mb-1.5 font-mono">
                      <Award className="w-4 h-4 text-amber-400" />
                      <span>Principal Analyst Verdict</span>
                    </div>
                    <p className="text-base sm:text-lg font-medium text-amber-100 leading-relaxed font-sans">
                      {dossier.executive_verdict}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="p-5 rounded-2xl glass-card border border-violet-500/20 space-y-2">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-violet-900/50 text-violet-300 border border-violet-500/30">
                        Situation (Baseline)
                      </div>
                      <h4 className="text-sm font-bold text-white font-display">
                        Empirical State
                      </h4>
                      <p className="text-xs text-violet-200/75 leading-relaxed font-sans">
                        {dossier.situation}
                      </p>
                    </div>

                    <div className="p-5 rounded-2xl glass-card border border-amber-500/20 space-y-2">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/50 text-amber-300 border border-amber-500/30">
                        Complication (Drivers & Risk)
                      </div>
                      <h4 className="text-sm font-bold text-white font-display">
                        Structural Vulnerabilities
                      </h4>
                      <p className="text-xs text-violet-200/75 leading-relaxed font-sans">
                        {dossier.complication}
                      </p>
                    </div>

                    <div className="p-5 rounded-2xl glass-card border border-emerald-500/20 space-y-2">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/50 text-emerald-300 border border-emerald-500/30">
                        Resolution (Decision)
                      </div>
                      <h4 className="text-sm font-bold text-white font-display">
                        Strategic Action Plan
                      </h4>
                      <p className="text-xs text-violet-200/75 leading-relaxed font-sans">
                        {dossier.resolution}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* 03. ADAPTIVE VISUAL INTELLIGENCE SUITE */}
              {dashboard.visuals && dashboard.visuals.length > 0 && (
                <div className="space-y-4">
                  <SectionHeader
                    number="03"
                    title="Adaptive Visual Intelligence Suite"
                    subtitle="Every Geometry Selected by Cardinality, Continuity & Skew"
                  />
                  <ReportCharts visuals={dashboard.visuals} />
                </div>
              )}

              {/* 04. CORRELATION MATRIX & DRIVER FORENSICS */}
              {dossier &&
                (dossier.correlation_matrix || dossier.correlation_insights?.length) && (
                  <div className="space-y-3">
                    <SectionHeader
                      number="04"
                      title="Multivariate Correlation & Driver Forensics"
                      subtitle="Pearson r + Spearman ρ Rank Screening"
                    />
                    <CorrelationHeatmap
                      matrix={dossier.correlation_matrix}
                      insights={dossier.correlation_insights}
                    />
                  </div>
                )}

              {/* 05. NON-PARAMETRIC QUANTILES & DISTRIBUTION FORENSICS */}
              {dossier && dossier.statistical_diagnostics?.length > 0 && (
                <div className="space-y-3">
                  <SectionHeader
                    number="05"
                    title="Distribution Moments & Non-Parametric Quantiles"
                    subtitle="Mean vs Median, IQR Spread & Tukey 1.5×IQR Fences"
                  />
                  <QuantileDiagnosticsSection diagnostics={dossier.statistical_diagnostics} />
                </div>
              )}

              {/* 06. COHORT VARIANCE (ANOVA ETA^2) & HHI CONCENTRATION */}
              {dossier &&
                (dossier.segment_benchmarks?.length || dossier.concentration_risk) && (
                  <div className="space-y-4">
                    <SectionHeader
                      number="06"
                      title="Cohort Performance & Portfolio Concentration"
                      subtitle="One-Way ANOVA η² & Herfindahl-Hirschman Index"
                    />

                    <SegmentBenchmarksSection benchmarks={dossier.segment_benchmarks} />

                    {dossier.concentration_risk && (
                      <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4 print-break-avoid">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <SlidersHorizontal className="w-5 h-5 text-amber-400" />
                            <h3 className="text-base font-bold text-white font-display">
                              Herfindahl-Hirschman (HHI) Concentration & Pareto Forensics
                            </h3>
                          </div>
                          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-950/60 text-amber-300 border border-amber-500/30 self-start sm:self-auto">
                            {dossier.concentration_risk.market_classification}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                            <span className="text-xs text-violet-300/70 font-medium">
                              Top 20% Quantile Share
                            </span>
                            <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
                              {dossier.concentration_risk.top_20_percent_share}%
                            </div>
                            <span className="text-[11px] text-violet-400/65">
                              Share of total {dossier.concentration_risk.metric}
                            </span>
                          </div>

                          <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                            <span className="text-xs text-violet-300/70 font-medium">
                              HHI Concentration Index
                            </span>
                            <div className="text-2xl font-bold text-white mt-1 font-mono">
                              {dossier.concentration_risk.hhi_index}
                            </div>
                            <span className="text-[11px] text-violet-400/65">
                              &ge;2,500 indicates acute concentration risk
                            </span>
                          </div>

                          <div className="p-4 rounded-xl bg-violet-950/40 border border-violet-500/15">
                            <span className="text-xs text-violet-300/70 font-medium">
                              Segment Axis
                            </span>
                            <div className="text-xl font-bold text-violet-200 mt-1 truncate">
                              {dossier.concentration_risk.dimension}
                            </div>
                            <span className="text-[11px] text-violet-400/65">
                              Primary concentration dimension
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-amber-200/90 bg-amber-950/30 p-3.5 rounded-xl border border-amber-500/25 leading-relaxed font-sans">
                          <strong>Principal Takeaway:</strong>{" "}
                          {dossier.concentration_risk.strategic_takeaway}
                        </p>
                      </div>
                    )}
                  </div>
                )}

              {/* 07. ISOLATIONFOREST OUTLIER FORENSICS */}
              {dashboard.anomalies && dashboard.anomalies.length > 0 && (
                <div className="space-y-3">
                  <SectionHeader
                    number="07"
                    title="Multivariate Anomaly & Outlier Forensics"
                    subtitle="Standardized Z-Divergence Root-Cause Attribution"
                  />
                  <OutlierForensicsSection anomalies={dashboard.anomalies} />
                </div>
              )}

              {/* 08. ACTION ROADMAP, RISK GOVERNANCE & SCHEMA AUDIT */}
              {dossier && (
                <div className="space-y-6">
                  <SectionHeader
                    number="08"
                    title="Prioritized Roadmap, Risk Governance & Data Audit"
                    subtitle="P0–P2 Execution + Schema Hygiene + Methodology"
                  />

                  {dossier.strategic_initiatives?.length > 0 && (
                    <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4 print-break-avoid">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Target className="w-5 h-5 text-amber-400" />
                          <h3 className="text-base font-bold text-white font-display">
                            Prioritized Strategic Action Roadmap
                          </h3>
                        </div>
                        <span className="text-xs font-mono text-violet-400/65">
                          Boardroom Execution Register
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {dossier.strategic_initiatives.map((init, i) => (
                          <div
                            key={i}
                            className="rounded-2xl p-4 flex flex-col justify-between bg-violet-950/30 border border-violet-500/20 hover:border-violet-400/40 transition"
                          >
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-xs">
                                <span
                                  className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold ${
                                    init.priority.includes("P0")
                                      ? "bg-rose-950/70 text-rose-300 border border-rose-500/30"
                                      : init.priority.includes("P1")
                                      ? "bg-amber-950/70 text-amber-300 border border-amber-500/30"
                                      : "bg-violet-900/50 text-violet-300 border border-violet-500/30"
                                  }`}
                                >
                                  {init.priority}
                                </span>
                                <span className="text-violet-400/70 text-[11px] font-mono">
                                  {init.time_horizon}
                                </span>
                              </div>

                              <h4 className="text-sm font-bold text-white font-display leading-snug">
                                {init.title}
                              </h4>
                              <p className="text-xs text-violet-200/75 leading-relaxed font-sans">
                                {init.rationale}
                              </p>
                            </div>

                            <div className="mt-4 pt-3 border-t border-violet-500/15 space-y-1 text-xs font-mono">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-violet-400/65">Impact:</span>
                                <span className="font-bold text-emerald-400 text-right">
                                  {init.expected_financial_impact}
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-[11px] text-violet-400/60">
                                <span>Owner: {init.operational_owner}</span>
                                <span>Risk: {init.risk_level}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <DataGovernanceSection
                    risks={dossier.risk_matrix}
                    audit={dossier.data_quality_audit}
                    notes={dossier.methodological_notes}
                  />
                </div>
              )}
            </div>
          )}

          {/* =================================================================
              TAB 2: VISUAL COMMAND CENTER (FOCUSED CHARTS + CORRELATION + OUTLIERS)
             ================================================================= */}
          {activeTab === "visuals" && (
            <div className="space-y-6">
              <KpiScorecardGrid kpis={dashboard.kpis} />

              <ReportCharts
                visuals={dashboard.visuals}
                sectionTitle="Shape-Selected Interactive Visualizations"
                sectionSubtitle="Includes Why-Selected rationale, Cohort Mean / Pareto 80% references, and Finding summaries."
              />

              {dossier && (
                <CorrelationHeatmap
                  matrix={dossier.correlation_matrix}
                  insights={dossier.correlation_insights}
                />
              )}

              <OutlierForensicsSection anomalies={dashboard.anomalies} />
            </div>
          )}

          {/* =================================================================
              TAB 3: BI DEPLOYMENT (POWER BI .PBIP & TABLEAU .TWBX)
             ================================================================= */}
          {activeTab === "bi" && (
            <div className="space-y-6">
              <div className="p-6 rounded-3xl glass-card border border-violet-500/20 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-bold text-white font-display">
                      Enterprise BI Deployment Architecture
                    </h3>
                    <p className="text-xs text-violet-300/70 mt-0.5">
                      Export compiled Power BI (.pbip) & Tableau (.twbx) project packages with shape-matched visual specs and typed TMSL columns.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleExportPowerBI}
                      disabled={downloadingFormat === "powerbi"}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 font-medium text-xs border border-amber-500/30 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5 text-amber-400" />
                      <span>
                        {downloadingFormat === "powerbi" ? "Exporting..." : "Download Power BI (.pbip)"}
                      </span>
                    </button>

                    <button
                      onClick={handleExportTableau}
                      disabled={downloadingFormat === "tableau"}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-200 font-medium text-xs border border-violet-500/30 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5 text-violet-400" />
                      <span>
                        {downloadingFormat === "tableau" ? "Exporting..." : "Download Tableau (.twbx)"}
                      </span>
                    </button>
                  </div>
                </div>

                {/* 3-Page Executive Power BI Architecture Blueprint */}
                {dashboard.powerbi_pages && dashboard.powerbi_pages.length > 0 && (
                  <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/25 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs font-mono font-bold text-amber-300 uppercase tracking-wider">
                        3-Page Executive Power BI (.pbip) Architecture + Custom Corporate Theme
                      </div>
                      <span className="text-[11px] font-mono text-emerald-300">
                        TMSL v1567 · 4 DAX Display Folders · Interactive Slicers
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      {dashboard.powerbi_pages.map((pg) => (
                        <div
                          key={pg.page_number}
                          className="p-3.5 rounded-xl bg-violet-950/50 border border-violet-500/25 space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-bold text-white font-display">
                              Page {pg.page_number}: {pg.name}
                            </span>
                            <span className="text-[10px] font-mono text-amber-300 shrink-0">
                              {pg.dimensions}
                            </span>
                          </div>
                          <p className="text-[11px] text-violet-200/75 leading-relaxed">{pg.purpose}</p>
                          {pg.slicers && pg.slicers.length > 0 && (
                            <div className="text-[10px] font-mono text-emerald-300">
                              Slicers: {pg.slicers.join(", ")}
                            </div>
                          )}
                          {pg.visuals && pg.visuals.length > 0 && (
                            <div className="text-[10px] font-mono text-violet-300/80">
                              Containers: {pg.visuals.join(" · ")}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Power BI Visual Architecture Blueprint */}
                {dashboard.visuals?.length > 0 && (
                  <div className="p-4 rounded-2xl bg-violet-950/35 border border-violet-500/20 space-y-2">
                    <div className="text-xs font-mono font-bold text-amber-300 uppercase tracking-wider">
                      Compiled Power BI Visual Blueprint ({dashboard.visuals.length} Canvas Containers)
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
                      {dashboard.visuals.map((v, i) => (
                        <div
                          key={v.id || i}
                          className="p-2.5 rounded-xl bg-violet-900/30 border border-violet-500/20 flex items-center justify-between gap-2"
                        >
                          <div className="min-w-0">
                            <div className="font-semibold text-white truncate">{v.title}</div>
                            <div className="font-mono text-[10px] text-violet-300/70 truncate">
                              {v.x_axis} → {v.y_axis} ({v.aggregation})
                            </div>
                          </div>
                          <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/30 font-mono text-[10px] shrink-0">
                            {v.chart_type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-1">
                  {/* Power BI DAX & M */}
                  <div className="border border-violet-500/20 rounded-2xl p-4 bg-violet-950/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <Code2 className="w-4 h-4 text-amber-400" />
                        Power BI DAX Measures
                      </span>
                      <button
                        onClick={() => copyToClipboard(dashboard.dax_script, "dax_tab")}
                        className="text-xs text-violet-300 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "dax_tab" ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span>{copiedKey === "dax_tab" ? "Copied" : "Copy DAX"}</span>
                      </button>
                    </div>
                    <pre className="p-3 bg-black/60 text-amber-300 font-mono text-xs rounded-xl overflow-x-auto max-h-64 border border-violet-500/20">
                      {dashboard.dax_script}
                    </pre>

                    <span className="text-xs font-bold text-violet-300 uppercase tracking-wider block pt-2 font-mono">
                      Power Query (M) ETL Script
                    </span>
                    <pre className="p-3 bg-black/60 text-violet-200 font-mono text-xs rounded-xl overflow-x-auto max-h-40 border border-violet-500/20">
                      {dashboard.powerquery_m}
                    </pre>
                  </div>

                  {/* Tableau Calculated Fields */}
                  <div className="border border-violet-500/20 rounded-2xl p-4 bg-violet-950/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <Code2 className="w-4 h-4 text-amber-400" />
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
                        className="text-xs text-violet-300 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "tableau_tab" ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span>{copiedKey === "tableau_tab" ? "Copied" : "Copy All"}</span>
                      </button>
                    </div>

                    <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                      {dashboard.tableau_calculated_fields.map((calc, i) => (
                        <div
                          key={i}
                          className="p-2.5 bg-black/40 border border-violet-500/20 rounded-xl"
                        >
                          <div className="text-xs font-bold text-amber-200 mb-1 font-mono">
                            {calc.caption}
                          </div>
                          <pre className="text-xs font-mono text-violet-200 bg-violet-950/50 p-2 rounded border border-violet-500/20">
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
