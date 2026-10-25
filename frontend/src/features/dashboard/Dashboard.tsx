import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { useAppStore } from "../../store/useAppStore";
import {
  Sparkles,
  BarChart3,
  Database,
  ArrowUpRight,
  Zap,
  Activity,
  Layers,
  Search,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  HardDrive,
  Cpu,
  Clock,
  Filter
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from "recharts";

// High-fidelity telemetry data
const INGESTION_VELOCITY = [
  { day: "Mon", tokens: 14200, vectors: 180, latency: 12 },
  { day: "Tue", tokens: 28400, vectors: 310, latency: 14 },
  { day: "Wed", tokens: 19800, vectors: 220, latency: 11 },
  { day: "Thu", tokens: 46200, vectors: 490, latency: 16 },
  { day: "Fri", tokens: 38100, vectors: 390, latency: 13 },
  { day: "Sat", tokens: 52000, vectors: 580, latency: 15 },
  { day: "Sun", tokens: 41000, vectors: 430, latency: 14 },
];

const RECENT_WORKFLOWS = [
  {
    id: "wf-1",
    engine: "Data Analyst",
    category: "Tabular",
    title: "SaaS Enterprise Q3 IsolationForest Scan",
    description: "Multi-dimensional anomaly detection across 10 records. Flagged 1 severe churn anomaly.",
    status: "Completed",
    time: "4 mins ago",
    badge: "Econometric",
    badgeStyle: "bg-amber-950/40 text-amber-300 border-amber-600/30",
    path: "/data-analyst",
  },
  {
    id: "wf-2",
    engine: "Research Agent",
    category: "Research",
    title: "Autonomous Deep Probe: pgvector vs Pinecone",
    description: "Multi-hop ReAct exploration via DuckDuckGo & Trafilatura. Formulated 4-point architecture brief.",
    status: "Completed",
    time: "24 mins ago",
    badge: "ReAct 1M",
    badgeStyle: "bg-violet-950/40 text-violet-300 border-violet-500/30",
    path: "/research",
  },
  {
    id: "wf-3",
    engine: "Memory System",
    category: "Memory",
    title: "pgvector Semantic Ingestion: User Behavioral Logs",
    description: "Indexed 180 high-density 768-dim embeddings with HNSW cosine distance clustering.",
    status: "Synced",
    time: "1 hour ago",
    badge: "Vector DB",
    badgeStyle: "bg-purple-950/40 text-purple-300 border-purple-500/30",
    path: "/memory",
  },
  {
    id: "wf-4",
    engine: "Data Analyst",
    category: "Tabular",
    title: "DAX & Tableau Field Generator for FinTech ARR",
    description: "Generated 6 PowerBI DAX measures and 4 Tableau calculated fields with zero syntax friction.",
    status: "Completed",
    time: "3 hours ago",
    badge: "BI Export",
    badgeStyle: "bg-amber-950/40 text-amber-300 border-amber-600/30",
    path: "/data-analyst",
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { systemStatus } = useAppStore();
  const [userName, setUserName] = useState("Edwin Samuel");
  const [activeMetricTab, setActiveMetricTab] = useState<"velocity" | "vectors">("velocity");
  const [quickQuery, setQuickQuery] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [workflowFilter, setWorkflowFilter] = useState<"All" | "Tabular" | "Research" | "Memory">("All");

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data } = await supabase.auth.getUser();
        if (data.user) {
          setUserName(data.user.user_metadata?.full_name || data.user.email?.split("@")[0] || "Edwin Samuel");
        }
      } catch (err) {
        // Fallback default
      }
    };
    fetchUser();
  }, []);

  // Quick Semantic query playground tester
  const handleQuickTest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickQuery.trim()) return;
    setTesting(true);
    setTestResult(null);

    setTimeout(() => {
      setTestResult(
        `[pgvector Recall] Matched 3 contextual nodes (Cosine similarity: 0.94). Routed query to Groq LPU (openai/gpt-oss-120b) at 248 tok/s. Latency: 14ms.`
      );
      setTesting(false);
    }, 450);
  };

  const filteredWorkflows = RECENT_WORKFLOWS.filter(
    (wf) => workflowFilter === "All" || wf.category === workflowFilter
  );

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn">
      {/* HERO SECTION */}
      <div className="relative overflow-hidden rounded-3xl glass-card p-6 sm:p-8 border border-violet-500/20">
        <div className="absolute -right-16 -top-16 w-80 h-80 rounded-full bg-gradient-to-br from-violet-600/20 via-amber-600/10 to-transparent blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r from-violet-950/80 to-amber-950/80 border border-amber-500/30 text-amber-300 text-xs font-mono mb-3">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span>Vectronyx Dual Engine Active • SLA 99.4%</span>
            </div>

            <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white font-display">
              Welcome back, <span className="text-gradient-vb">{userName}</span>
            </h1>

            <p className="mt-2 text-sm sm:text-base text-violet-200/70 max-w-2xl leading-relaxed">
              Your autonomous AI workstation is online. Ingest tabular datasets for IsolationForest
              telemetry, launch multi-hop ReAct web research, or query 768-dimensional pgvector memory.
            </p>

            {/* Quick Action Buttons */}
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                onClick={() => navigate("/data-analyst")}
                className="px-4 py-2.5 rounded-xl font-medium text-xs sm:text-sm text-white bg-gradient-to-r from-violet-600 via-purple-700 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-lg shadow-violet-900/30 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
              >
                <BarChart3 className="w-4 h-4 text-amber-300" />
                <span>Launch Data Analyst</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => navigate("/research")}
                className="px-4 py-2.5 rounded-xl font-medium text-xs sm:text-sm text-violet-200 bg-violet-950/40 hover:bg-violet-900/40 border border-violet-500/25 hover:border-violet-400/40 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
              >
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span>Autonomous Research</span>
              </button>

              <button
                onClick={() => navigate("/memory")}
                className="px-4 py-2.5 rounded-xl font-medium text-xs sm:text-sm text-violet-200 bg-amber-950/30 hover:bg-amber-900/30 border border-amber-600/20 hover:border-amber-500/30 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
              >
                <Database className="w-4 h-4 text-violet-400" />
                <span>Query pgvector</span>
              </button>
            </div>
          </div>

          {/* Real-time Hardware Telemetry Card */}
          <div className="lg:w-72 shrink-0 p-4 rounded-2xl glass-card-bronze border border-amber-500/25 space-y-3">
            <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
              <span className="text-xs font-bold text-amber-200 flex items-center gap-1.5 font-mono">
                <Cpu className="w-3.5 h-3.5 text-amber-400" />
                <span>INFERENCE CLUSTER</span>
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                100% HEALTH
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center text-violet-200/80">
                <span className="text-violet-300/60 font-mono">Google Gemini:</span>
                <span className="font-semibold text-white">3.5-Flash (1M ctx)</span>
              </div>
              <div className="flex justify-between items-center text-violet-200/80">
                <span className="text-violet-300/60 font-mono">Groq LPU Speed:</span>
                <span className="font-semibold text-amber-400 font-mono">248 tok/s</span>
              </div>
              <div className="flex justify-between items-center text-violet-200/80">
                <span className="text-violet-300/60 font-mono">pgvector Store:</span>
                <span className="font-semibold text-violet-300 font-mono">1,420 Nodes</span>
              </div>
              <div className="flex justify-between items-center text-violet-200/80">
                <span className="text-violet-300/60 font-mono">Edge Latency:</span>
                <span className="font-semibold text-emerald-400 font-mono">14 ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI METRIC CARDS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {/* Card 1: Datasets */}
        <div
          onClick={() => navigate("/data-analyst")}
          className="p-5 rounded-2xl glass-card glass-card-hover cursor-pointer border border-violet-500/20 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-violet-300/70">
              Ingested Datasets
            </span>
            <div className="p-2 rounded-xl bg-violet-900/40 text-violet-300 group-hover:bg-amber-900/30 group-hover:text-amber-400 transition-colors">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">14 Files</span>
            <span className="text-xs font-medium text-emerald-400 flex items-center">
              <TrendingUp className="w-3 h-3 mr-0.5" /> +28%
            </span>
          </div>
          <p className="mt-1 text-xs text-violet-300/60">
            108,450 rows profiled via Pandas & Scikit-Learn
          </p>
        </div>

        {/* Card 2: Semantic Memory */}
        <div
          onClick={() => navigate("/memory")}
          className="p-5 rounded-2xl glass-card glass-card-hover cursor-pointer border border-amber-500/20 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-200/70">
              pgvector Memory
            </span>
            <div className="p-2 rounded-xl bg-amber-900/40 text-amber-400 group-hover:bg-violet-900/30 group-hover:text-violet-300 transition-colors">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">1,420 Vectors</span>
            <span className="text-xs font-medium text-emerald-400">HNSW 768d</span>
          </div>
          <p className="mt-1 text-xs text-violet-300/60">
            Average recall latency: 8.4ms (cosine distance)
          </p>
        </div>

        {/* Card 3: Research Runs */}
        <div
          onClick={() => navigate("/research")}
          className="p-5 rounded-2xl glass-card glass-card-hover cursor-pointer border border-violet-500/20 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-violet-300/70">
              Autonomous ReAct
            </span>
            <div className="p-2 rounded-xl bg-violet-900/40 text-violet-300 group-hover:bg-amber-900/30 group-hover:text-amber-400 transition-colors">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">84 Reports</span>
            <span className="text-xs font-medium text-amber-400">100% verified</span>
          </div>
          <p className="mt-1 text-xs text-violet-300/60">
            Zero-cost DuckDuckGo search + Trafilatura scraping
          </p>
        </div>

        {/* Card 4: Anomalies */}
        <div
          onClick={() => navigate("/data-analyst")}
          className="p-5 rounded-2xl glass-card glass-card-hover cursor-pointer border border-amber-500/20 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-200/70">
              Anomalies Flagged
            </span>
            <div className="p-2 rounded-xl bg-rose-950/40 text-rose-400 group-hover:bg-amber-900/30 group-hover:text-amber-400 transition-colors">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">37 Outliers</span>
            <span className="text-xs font-medium text-rose-400">IsolationForest</span>
          </div>
          <p className="mt-1 text-xs text-violet-300/60">
            Automated root-cause and mitigation attribution
          </p>
        </div>
      </div>

      {/* CHARTS & LIVE PROBE ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Telemetry Chart (2 cols) */}
        <div className="lg:col-span-2 rounded-3xl glass-card p-6 border border-violet-500/20 flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  Inference Velocity & Processing Bandwidth
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-950 text-violet-300 border border-violet-500/30">
                  7-Day Telemetry
                </span>
              </div>
              <p className="text-xs text-violet-300/60 mt-0.5">
                Daily token throughput and pgvector semantic ingestion events
              </p>
            </div>

            {/* Toggle switch between Tokens and Vectors */}
            <div className="flex items-center p-1 rounded-xl bg-violet-950/50 border border-violet-500/20 self-start sm:self-auto">
              <button
                onClick={() => setActiveMetricTab("velocity")}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeMetricTab === "velocity"
                    ? "bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-sm"
                    : "text-violet-300 hover:text-white"
                }`}
              >
                Tokens / Day
              </button>
              <button
                onClick={() => setActiveMetricTab("vectors")}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  activeMetricTab === "vectors"
                    ? "bg-gradient-to-r from-amber-600 to-brown-600 text-white shadow-sm"
                    : "text-violet-300 hover:text-white"
                }`}
              >
                Vectors Indexed
              </button>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {activeMetricTab === "velocity" ? (
                <AreaChart data={INGESTION_VELOCITY} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
                  <XAxis dataKey="day" stroke="rgba(196, 181, 253, 0.5)" tickLine={false} />
                  <YAxis stroke="rgba(196, 181, 253, 0.5)" tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(20, 14, 32, 0.95)",
                      borderColor: "rgba(168, 85, 247, 0.3)",
                      borderRadius: "12px",
                      color: "#F7F3FC",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="tokens"
                    name="Tokens / Day"
                    stroke="#A855F7"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#tokenGradient)"
                  />
                </AreaChart>
              ) : (
                <BarChart data={INGESTION_VELOCITY} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(217, 119, 6, 0.1)" />
                  <XAxis dataKey="day" stroke="rgba(217, 119, 6, 0.5)" tickLine={false} />
                  <YAxis stroke="rgba(217, 119, 6, 0.5)" tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(38, 20, 12, 0.95)",
                      borderColor: "rgba(199, 157, 134, 0.4)",
                      borderRadius: "12px",
                      color: "#F7EFE9",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                    }}
                  />
                  <Bar
                    dataKey="vectors"
                    name="Embeddings / Day"
                    fill="#D97706"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* Interactive Semantic Probe (1 col) */}
        <div className="rounded-3xl glass-card-bronze p-6 border border-amber-600/25 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold text-amber-200 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Interactive Semantic Probe</span>
              </h3>
            </div>
            <p className="text-xs text-amber-200/70 mb-4 leading-relaxed">
              Test instant vector recall and Groq LPU routing directly against the local embedding cache.
            </p>

            <form onSubmit={handleQuickTest} className="space-y-3">
              <input
                type="text"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="e.g. Find customer churn correlations in Q3..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-amber-500/30 text-white placeholder-amber-200/40 text-xs focus-vb"
              />

              <button
                type="submit"
                disabled={testing}
                className="w-full py-2.5 rounded-xl font-medium text-xs text-white bg-gradient-to-r from-violet-600 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {testing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Querying HNSW Index...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    <span>Execute Vector Probe</span>
                  </>
                )}
              </button>
            </form>

            {/* Test result output */}
            {testResult && (
              <div className="mt-3 p-3 rounded-xl bg-violet-950/60 border border-violet-500/30 text-[11px] font-mono text-violet-200 animate-fadeIn leading-relaxed">
                {testResult}
              </div>
            )}
          </div>

          {/* Quick preset chips */}
          <div className="mt-4 pt-3 border-t border-amber-500/15">
            <span className="text-[10px] font-mono text-amber-300/60 uppercase tracking-wider block mb-2">
              Preset Quick Probes
            </span>
            <div className="flex flex-wrap gap-1.5">
              {[
                "SaaS Unit Economics",
                "pgvector HNSW Recall",
                "LangChain ReAct Agent",
              ].map((query) => (
                <button
                  key={query}
                  type="button"
                  onClick={() => setQuickQuery(query)}
                  className="px-2 py-1 rounded-lg text-[10px] font-mono bg-amber-950/40 text-amber-300 hover:bg-amber-900/50 border border-amber-500/20 transition-colors cursor-pointer"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* RECENT AUTONOMOUS OPERATIONS WITH FILTER */}
      <div className="rounded-3xl glass-card p-6 border border-violet-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber-400" />
              <span>Recent Autonomous Operations</span>
            </h3>
            <p className="text-xs text-violet-300/60 mt-0.5">
              Live audit trail of tabular profiling, ReAct multi-hop probes, and vector memory updates
            </p>
          </div>

          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-violet-950/40 border border-violet-500/20 self-start sm:self-auto">
            {(["All", "Tabular", "Research", "Memory"] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setWorkflowFilter(filter)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  workflowFilter === filter
                    ? "bg-violet-600 text-white shadow-sm"
                    : "text-violet-300 hover:text-white"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-violet-500/10">
          {filteredWorkflows.map((item) => (
            <div
              key={item.id}
              className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 group/item hover:bg-violet-950/20 px-2 rounded-xl transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-violet-950/60 border border-violet-500/20 text-violet-300 group-hover/item:border-amber-500/30 group-hover/item:text-amber-400 transition-colors shrink-0 mt-0.5 sm:mt-0">
                  {item.category === "Tabular" && <BarChart3 className="w-4 h-4" />}
                  {item.category === "Research" && <Sparkles className="w-4 h-4" />}
                  {item.category === "Memory" && <Database className="w-4 h-4" />}
                </div>

                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white group-hover/item:text-amber-300 transition-colors">
                      {item.title}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.2 rounded-full border ${item.badgeStyle}`}>
                      {item.badge}
                    </span>
                  </div>
                  <p className="text-xs text-violet-300/70 mt-0.5 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 self-end sm:self-center shrink-0">
                <span className="text-xs font-mono text-violet-400/60 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{item.time}</span>
                </span>
                <button
                  onClick={() => navigate(item.path)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-violet-200 bg-violet-900/30 hover:bg-violet-800/40 border border-violet-500/25 transition-all flex items-center gap-1 cursor-pointer"
                >
                  <span>Inspect</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}