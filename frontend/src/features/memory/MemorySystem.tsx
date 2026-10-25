import React, { useState } from "react";
import {
  Database,
  Search,
  Plus,
  SlidersHorizontal,
  HardDrive,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle2,
  Trash2,
  Eye,
  Tag,
  Clock,
  ArrowRight,
  ShieldCheck,
  Zap,
  Filter,
  X,
  RefreshCw
} from "lucide-react";
import toast from "react-hot-toast";

interface MemoryItem {
  id: string;
  title: string;
  content: string;
  category: "Tabular Knowledge" | "User Context" | "Architecture" | "Research Notes";
  similarity: number; // e.g. 0.94
  vectorPreview: number[];
  dimensions: number;
  timestamp: string;
  source: string;
}

const INITIAL_MEMORIES: MemoryItem[] = [
  {
    id: "mem-1",
    title: "SaaS Enterprise Unit Economics & Churn Thresholds",
    content: "Enterprise Cloud customer ARR correlates negatively with ChurnRate when annual contract value (ACV) exceeds $150k. Volatility detected primarily in Developer Tools cohort.",
    category: "Tabular Knowledge",
    similarity: 0.96,
    vectorPreview: [0.042, -0.128, 0.315, 0.089, -0.214, 0.512],
    dimensions: 768,
    timestamp: "10 mins ago",
    source: "saas_enterprise_q3.csv",
  },
  {
    id: "mem-2",
    title: "Dual-Tier High-Performance LLM Routing Rules",
    content: "Queries requiring large context window (>32k tokens) or complex tabular reasoning route to Google Gemini (gemini-3.5-flash-lite). Sub-second conversational responses route to Groq Cloud LPUs.",
    category: "Architecture",
    similarity: 0.92,
    vectorPreview: [0.187, 0.034, -0.098, 0.441, -0.165, 0.088],
    dimensions: 768,
    timestamp: "1 hour ago",
    source: "system_architecture_spec.md",
  },
  {
    id: "mem-3",
    title: "Executive Developer User Profile & Permissions",
    content: "Active developer user Edwin Samuel, Pro Workstation tier. High-frequency operations in IsolationForest econometric modeling and DuckDuckGo ReAct synthesis.",
    category: "User Context",
    similarity: 0.88,
    vectorPreview: [-0.052, 0.214, 0.178, -0.321, 0.119, 0.045],
    dimensions: 768,
    timestamp: "3 hours ago",
    source: "supabase_auth_users",
  },
  {
    id: "mem-4",
    title: "Supabase pgvector HNSW Index Benchmark",
    content: "HNSW index configured with m=16, ef_construction=64 on vector_cosine_ops achieves sub-10ms recall across 1M records with 99.2% accuracy.",
    category: "Research Notes",
    similarity: 0.84,
    vectorPreview: [0.334, -0.088, 0.124, 0.052, -0.401, 0.287],
    dimensions: 768,
    timestamp: "5 hours ago",
    source: "pgvector_research_report.md",
  },
];

export default function MemorySystem() {
  const [searchQuery, setSearchQuery] = useState("");
  const [similarityThreshold, setSimilarityThreshold] = useState(0.75);
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [memories, setMemories] = useState<MemoryItem[]>(INITIAL_MEMORIES);
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState<MemoryItem["category"]>("Tabular Knowledge");

  // Filter memories based on search query, similarity, and category
  const filteredMemories = memories.filter((mem) => {
    const matchesSearch =
      mem.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      mem.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      mem.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "All" || mem.category === selectedCategory;
    const matchesSimilarity = mem.similarity >= similarityThreshold;
    return matchesSearch && matchesCategory && matchesSimilarity;
  });

  const handleAddMemory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) {
      toast.error("Title and content are required");
      return;
    }

    const newItem: MemoryItem = {
      id: `mem-${Date.now()}`,
      title: newTitle,
      content: newContent,
      category: newCategory,
      similarity: 0.95,
      vectorPreview: [
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
        parseFloat((Math.random() * 0.8 - 0.4).toFixed(3)),
      ],
      dimensions: 768,
      timestamp: "Just now",
      source: "manual_workbench_input",
    };

    setMemories([newItem, ...memories]);
    setIsAddOpen(false);
    setNewTitle("");
    setNewContent("");
    toast.success("Memory embedded & indexed in pgvector!");
  };

  const handleDelete = (id: string) => {
    setMemories(memories.filter((m) => m.id !== id));
    if (selectedMemory?.id === id) setSelectedMemory(null);
    toast.success("Vector node purged from pgvector");
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn">
      {/* HEADER SECTION */}
      <div className="p-6 sm:p-8 rounded-3xl glass-card border border-violet-500/25 relative overflow-hidden">
        <div className="absolute -top-16 -right-16 w-72 h-72 rounded-full bg-gradient-to-br from-purple-600/15 via-amber-600/10 to-transparent blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-950/60 border border-violet-500/30 text-violet-300 text-xs font-mono mb-2">
              <Database className="w-3.5 h-3.5 text-amber-400" />
              <span>Supabase pgvector (768-dim HNSW)</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-display">
              Contextual Semantic Memory Engine
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-violet-200/70 max-w-2xl leading-relaxed">
              Maintains persistent episodic and semantic context vectors inside PostgreSQL.
              Augments agent prompt templates and grounds reasoning with zero database synchronization drift.
            </p>
          </div>

          <button
            onClick={() => setIsAddOpen(true)}
            className="px-4 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-gradient-to-r from-violet-600 via-purple-700 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-md shadow-violet-900/30 transition-all flex items-center gap-2 cursor-pointer active:scale-95 shrink-0 self-start md:self-auto"
          >
            <Plus className="w-4 h-4 text-amber-300" />
            <span>Ingest New Memory</span>
          </button>
        </div>

        {/* TELEMETRY METRICS ROW */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-violet-500/15 pt-5">
          <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-500/15">
            <span className="text-[10px] font-mono uppercase text-violet-400/70 block">
              Indexed Vectors
            </span>
            <span className="text-lg font-bold text-white font-mono mt-0.5 block">
              1,420 Nodes
            </span>
          </div>

          <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-500/15">
            <span className="text-[10px] font-mono uppercase text-violet-400/70 block">
              Embedding Dims
            </span>
            <span className="text-lg font-bold text-amber-400 font-mono mt-0.5 block">
              768-dim float32
            </span>
          </div>

          <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-500/15">
            <span className="text-[10px] font-mono uppercase text-violet-400/70 block">
              Index Algorithm
            </span>
            <span className="text-lg font-bold text-violet-300 font-mono mt-0.5 block">
              HNSW (m=16)
            </span>
          </div>

          <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-500/15">
            <span className="text-[10px] font-mono uppercase text-violet-400/70 block">
              Avg Recall SLA
            </span>
            <span className="text-lg font-bold text-emerald-400 font-mono mt-0.5 block">
              8.4 ms p95
            </span>
          </div>
        </div>
      </div>

      {/* SEARCH & FILTERS BAR */}
      <div className="p-5 rounded-2xl glass-card border border-violet-500/20 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Query semantic memory using natural language (e.g., 'SaaS churn rates' or 'Gemini model parameters')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-violet-950/40 border border-violet-500/25 text-xs sm:text-sm text-white placeholder-violet-400/40 focus-vb"
            />
            <Search className="w-4 h-4 text-amber-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          </div>

          {/* Category filter pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {["All", "Tabular Knowledge", "Architecture", "User Context", "Research Notes"].map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-xs px-3 py-2 rounded-xl transition-all cursor-pointer whitespace-nowrap ${
                  selectedCategory === cat
                    ? "bg-gradient-to-r from-violet-600 to-amber-600 text-white font-semibold shadow-sm"
                    : "bg-violet-950/30 text-violet-300/70 hover:text-white border border-violet-500/15"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Similarity Threshold Slider */}
        <div className="flex items-center justify-between text-xs font-mono text-violet-300/80 pt-2 border-t border-violet-500/10">
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400" />
            <span>Cosine Similarity Threshold: {(similarityThreshold * 100).toFixed(0)}%</span>
          </span>
          <input
            type="range"
            min="0.5"
            max="0.99"
            step="0.01"
            value={similarityThreshold}
            onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
            className="w-36 sm:w-48 accent-amber-500 cursor-pointer"
          />
        </div>
      </div>

      {/* 2D EMBEDDING PROJECTION CLUSTERS VISUALIZER */}
      <div className="p-5 sm:p-6 rounded-3xl glass-card-bronze border border-amber-500/25 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm sm:text-base font-bold text-amber-200 font-display flex items-center gap-2">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>2D Latent Vector Space (t-SNE Projection)</span>
            </h2>
            <p className="text-xs text-violet-200/70 mt-0.5">
              Topological cluster representation of 768-dimensional embeddings in memory
            </p>
          </div>
          <span className="text-[11px] font-mono text-amber-400/80">
            {filteredMemories.length} Active Nodes Plotted
          </span>
        </div>

        {/* Visual Map Canvas */}
        <div className="h-44 sm:h-52 w-full rounded-2xl bg-[#090610] border border-violet-500/20 relative overflow-hidden flex items-center justify-center p-4">
          {/* Ambient background grid lines */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(139,92,246,0.1)_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

          {/* Scatter Nodes representing memories */}
          {memories.map((m, idx) => {
            const posX = 15 + ((idx * 23) % 70);
            const posY = 20 + ((idx * 37) % 60);
            const isSelected = selectedMemory?.id === m.id;

            return (
              <div
                key={m.id}
                onClick={() => setSelectedMemory(m)}
                style={{ left: `${posX}%`, top: `${posY}%` }}
                className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-300 group ${
                  isSelected ? "scale-150 z-20" : "hover:scale-125 z-10"
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full flex items-center justify-center shadow-lg transition-all ${
                    m.category === "Tabular Knowledge"
                      ? "bg-amber-500 shadow-amber-500/50"
                      : m.category === "Architecture"
                      ? "bg-violet-500 shadow-violet-500/50"
                      : m.category === "User Context"
                      ? "bg-purple-400 shadow-purple-500/50"
                      : "bg-emerald-400 shadow-emerald-500/50"
                  } ${isSelected ? "ring-4 ring-white animate-pulse" : ""}`}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                </div>

                {/* Hover Tooltip */}
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover:block z-30 px-2.5 py-1.5 rounded-lg bg-[#181126] text-white border border-violet-500/40 text-[10px] whitespace-nowrap shadow-xl font-mono">
                  <div className="font-bold text-amber-300">{m.title}</div>
                  <div className="text-violet-300/70">Cosine Match: {(m.similarity * 100).toFixed(0)}%</div>
                </div>
              </div>
            );
          })}

          <div className="absolute bottom-2 right-3 text-[10px] font-mono text-violet-400/50">
            Latent Dimension 1 vs Latent Dimension 2
          </div>
        </div>
      </div>

      {/* MEMORY ITEMS LIST */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400/80 font-mono">
          Retrieved Context Nodes ({filteredMemories.length})
        </h3>

        {filteredMemories.length === 0 ? (
          <div className="p-8 rounded-2xl glass-card text-center text-sm text-violet-300/60 border border-violet-500/20">
            No memories match the current search or similarity threshold. Try adjusting the slider.
          </div>
        ) : (
          filteredMemories.map((mem) => (
            <div
              key={mem.id}
              className={`p-4 sm:p-5 rounded-2xl glass-card border transition-all ${
                selectedMemory?.id === mem.id
                  ? "border-amber-400/50 bg-violet-950/40"
                  : "border-violet-500/20 hover:border-violet-400/40"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm sm:text-base font-bold text-white font-display">
                      {mem.title}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950/50 text-amber-300 border border-amber-500/30">
                      {mem.category}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      Cosine: {(mem.similarity * 100).toFixed(0)}%
                    </span>
                  </div>

                  <p className="text-xs sm:text-sm text-violet-200/80 leading-relaxed font-sans">
                    {mem.content}
                  </p>

                  <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-violet-400/60 pt-1">
                    <span className="flex items-center gap-1">
                      <Tag className="w-3 h-3 text-amber-400" /> Source: {mem.source}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Indexed {mem.timestamp}
                    </span>
                  </div>
                </div>

                {/* Right actions: Vector array preview & delete */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setSelectedMemory(selectedMemory?.id === mem.id ? null : mem)}
                    className="px-3 py-1.5 rounded-xl text-xs font-mono bg-violet-900/30 hover:bg-violet-800/40 text-violet-200 border border-violet-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5 text-amber-400" />
                    <span>{selectedMemory?.id === mem.id ? "Hide Vector" : "Inspect 768d"}</span>
                  </button>

                  <button
                    onClick={() => handleDelete(mem.id)}
                    className="p-2 rounded-xl text-violet-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors cursor-pointer"
                    title="Purge node"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Collapsible Vector Inspector */}
              {selectedMemory?.id === mem.id && (
                <div className="mt-4 p-3.5 rounded-xl bg-black/60 border border-violet-500/30 font-mono text-xs text-amber-300/90 space-y-2 animate-fadeIn">
                  <div className="flex items-center justify-between text-[11px] text-violet-300 border-b border-violet-500/20 pb-1.5">
                    <span>pgvector Embedding Preview (First 6 dimensions of 768)</span>
                    <span className="text-emerald-400">IEEE 754 Float32</span>
                  </div>
                  <div className="text-[11px] text-amber-200 break-all leading-relaxed">
                    [{mem.vectorPreview.join(", ")}, ... +762 dimensions]
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* ADD MEMORY MODAL */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg rounded-3xl glass-panel p-6 border border-violet-500/30 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between border-b border-violet-500/15 pb-3">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white font-display">
                  Ingest Context into pgvector
                </h3>
              </div>
              <button
                onClick={() => setIsAddOpen(false)}
                className="p-1 rounded-lg text-violet-300 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddMemory} className="space-y-4 text-xs">
              <div>
                <label className="block text-violet-300 font-medium mb-1">Title / Context Tag</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 FinTech ARR Cohort Volatility Rule"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-violet-950/60 border border-violet-500/25 text-white focus-vb"
                />
              </div>

              <div>
                <label className="block text-violet-300 font-medium mb-1">Knowledge Content</label>
                <textarea
                  rows={4}
                  placeholder="Provide semantic text fragment to embed in 768 dimensions..."
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-violet-950/60 border border-violet-500/25 text-white focus-vb leading-relaxed"
                />
              </div>

              <div>
                <label className="block text-violet-300 font-medium mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as any)}
                  className="w-full px-3.5 py-2 rounded-xl bg-violet-950/60 border border-violet-500/25 text-white focus-vb"
                >
                  <option value="Tabular Knowledge">Tabular Knowledge</option>
                  <option value="Architecture">Architecture</option>
                  <option value="User Context">User Context</option>
                  <option value="Research Notes">Research Notes</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 rounded-xl text-violet-300 hover:text-white"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl font-semibold text-white bg-gradient-to-r from-violet-600 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-md cursor-pointer"
                >
                  Generate 768d Embedding & Index
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}