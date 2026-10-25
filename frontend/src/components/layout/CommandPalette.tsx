import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../store/useAppStore";
import {
  Search,
  LayoutDashboard,
  BarChart3,
  Sparkles,
  Database,
  Settings,
  ArrowRight,
  X,
  Zap,
  Sun,
  Moon,
} from "lucide-react";

export default function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen, theme, toggleTheme } = useAppStore();
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (e.key === "Escape" && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  const actions = [
    {
      id: "dash",
      title: "Executive Dashboard",
      subtitle: "System overview, inference velocity, active cluster telemetry",
      icon: LayoutDashboard,
      path: "/",
      tag: "Command",
      keywords: ["dashboard", "home", "metrics", "telemetry", "velocity", "tokens", "cluster", "groq", "gemini", "status"],
    },
    {
      id: "analyst",
      title: "Data Analyst & Econometric Engine",
      subtitle: "Ingest CSV, IsolationForest anomaly detection, PowerBI & Tableau export",
      icon: BarChart3,
      path: "/data-analyst",
      tag: "Tabular AI",
      keywords: ["analyst", "data", "churn", "fintech", "saas", "anomaly", "anomalies", "outliers", "csv", "tsv", "tabular", "dax", "powerbi", "tableau", "scr", "mckinsey"],
    },
    {
      id: "research",
      title: "Autonomous Web Research Agent",
      subtitle: "Multi-hop ReAct exploration with DuckDuckGo & Trafilatura scraper",
      icon: Sparkles,
      path: "/research",
      tag: "ReAct Loop",
      keywords: ["research", "agent", "react", "duckduckgo", "trafilatura", "search", "web", "deep", "crawl", "probe", "investigation"],
    },
    {
      id: "memory",
      title: "Contextual Semantic Memory Engine",
      subtitle: "Supabase pgvector 768-dim semantic search, 2D latent space, recall",
      icon: Database,
      path: "/memory",
      tag: "Vector DB",
      keywords: ["memory", "vector", "vectors", "pgvector", "supabase", "hnsw", "embedding", "embeddings", "semantic", "cosine", "latent", "tsne", "clusters", "768d"],
    },
    {
      id: "settings",
      title: "Workbench Settings & API Keys",
      subtitle: "Groq LPUs, Gemini 1M Context, Supabase credentials, model routing",
      icon: Settings,
      path: "/settings",
      tag: "Config",
      keywords: ["settings", "keys", "api", "gemini", "groq", "supabase", "config", "token", "credentials", "latency", "temperature"],
    },
    {
      id: "theme-toggle",
      title: theme === "dark" ? "Switch to Warm Ivory Light Mode" : "Switch to Obsidian Velvet Dark Mode",
      subtitle: "Toggle visual workbench theme",
      icon: theme === "dark" ? Sun : Moon,
      path: "",
      action: () => toggleTheme(),
      tag: "Theme",
      keywords: ["theme", "dark", "light", "mode", "color", "sun", "moon", "appearance"],
    },
  ];

  const q = query.toLowerCase().trim();
  const filtered = actions.filter((a) => {
    if (!q) return true;
    return (
      a.title.toLowerCase().includes(q) ||
      a.subtitle.toLowerCase().includes(q) ||
      a.tag.toLowerCase().includes(q) ||
      a.keywords.some((k) => k.includes(q))
    );
  });

  const handleSelect = (item: (typeof actions)[0]) => {
    if (item.action) {
      item.action();
    } else if (item.path) {
      navigate(item.path);
    }
    setCommandPaletteOpen(false);
    setQuery("");
  };

  return (
    <div
      onClick={() => setCommandPaletteOpen(false)}
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/65 backdrop-blur-sm animate-fadeIn"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl rounded-2xl glass-panel shadow-2xl border border-violet-500/25 overflow-hidden transition-all duration-200"
        style={{
          boxShadow: "0 20px 60px -10px rgba(126, 34, 206, 0.4), 0 0 20px rgba(180, 83, 9, 0.2)",
        }}
      >
        {/* Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-violet-500/15 gap-3 bg-violet-950/30">
          <Search className="w-5 h-5 text-amber-400 shrink-0" />
          <input
            type="text"
            placeholder="Type a command or search workbench... (e.g., churn, memory, keys)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="w-full bg-transparent text-sm md:text-base text-violet-100 placeholder-violet-400/50 focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[11px] font-mono rounded bg-violet-900/40 text-violet-300 border border-violet-500/20 shrink-0">
            ESC
          </kbd>
          <button
            onClick={() => setCommandPaletteOpen(false)}
            className="p-1 rounded-lg text-violet-300 hover:text-white hover:bg-violet-800/40 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-violet-300/60 font-mono">
              No matching actions found for "{query}"
            </div>
          ) : (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => handleSelect(item)}
                  className="w-full flex items-center justify-between p-3 rounded-xl text-left hover:bg-violet-900/30 group transition-colors border border-transparent hover:border-violet-500/20 cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-violet-900/40 text-violet-300 group-hover:text-amber-400 group-hover:bg-amber-900/20 transition-colors shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-violet-100 group-hover:text-white flex items-center gap-2">
                        <span>{item.title}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-500/20">
                          {item.tag}
                        </span>
                      </div>
                      <div className="text-xs text-violet-300/60 mt-0.5">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-violet-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all shrink-0" />
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-violet-500/15 bg-black/30 flex items-center justify-between text-[11px] text-violet-300/60 font-mono">
          <span className="flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-amber-400" /> Fast Navigation
          </span>
          <span>Press ↑↓ to navigate • ↵ to select</span>
        </div>
      </div>
    </div>
  );
}
