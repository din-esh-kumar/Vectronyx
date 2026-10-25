import { create } from "zustand";

export interface SystemAlert {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  type: "info" | "success" | "warning";
  read: boolean;
}

interface AppState {
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
  toggleTheme: () => void;

  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  notifications: SystemAlert[];
  unreadCount: number;
  markAllNotificationsRead: () => void;

  systemStatus: {
    geminiStatus: "optimal" | "degraded" | "offline";
    groqSpeed: number; // tok/sec
    pgvectorCount: number;
    latencyMs: number;
  };
}

export const useAppStore = create<AppState>((set, get) => {
  const initialTheme = (localStorage.getItem("vectronyx-theme") as "dark" | "light") || "dark";
  if (typeof document !== "undefined") {
    if (initialTheme === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
    }
  }

  return {
    theme: initialTheme,
    setTheme: (theme) => {
      localStorage.setItem("vectronyx-theme", theme);
      if (typeof document !== "undefined") {
        if (theme === "dark") {
          document.documentElement.classList.add("dark");
          document.documentElement.classList.remove("light");
        } else {
          document.documentElement.classList.add("light");
          document.documentElement.classList.remove("dark");
        }
      }
      set({ theme });
    },
    toggleTheme: () => {
      const next = get().theme === "dark" ? "light" : "dark";
      get().setTheme(next);
    },

    commandPaletteOpen: false,
    setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
    toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

    notifications: [
      {
        id: "1",
        title: "IsolationForest Anomaly Flagged",
        description: "High variance detected on row #4 (Revenue: $48k, Churn: 12%).",
        timestamp: "2 mins ago",
        type: "warning",
        read: false,
      },
      {
        id: "2",
        title: "pgvector Semantic Index Rebuilt",
        description: "1,420 high-dimensional embeddings synced with HNSW index.",
        timestamp: "18 mins ago",
        type: "success",
        read: false,
      },
      {
        id: "3",
        title: "Dual Engine Active",
        description: "Gemini 1M Context + Groq 248 tok/s ready for ReAct exploration.",
        timestamp: "1 hour ago",
        type: "info",
        read: true,
      },
    ],
    unreadCount: 2,
    markAllNotificationsRead: () =>
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, read: true })),
        unreadCount: 0,
      })),

    systemStatus: {
      geminiStatus: "optimal",
      groqSpeed: 248,
      pgvectorCount: 1420,
      latencyMs: 14,
    },
  };
});
