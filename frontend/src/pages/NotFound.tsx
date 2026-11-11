import { Link } from "react-router-dom";
import { LayoutDashboard, BarChart3 } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md mx-auto space-y-5">
        <div>
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-amber-400">
            404
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-2 font-display">
            Page Not Found
          </h1>
          <p className="text-sm text-violet-200/70 mt-2 leading-relaxed">
            The requested route does not exist in this workspace.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link
            to="/"
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-gradient-to-r from-violet-600 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-lg shadow-violet-900/40 transition-all flex items-center justify-center gap-2"
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Back to Home</span>
          </Link>

          <Link
            to="/data-analyst"
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs sm:text-sm text-violet-200 bg-violet-950/40 hover:bg-violet-900/40 border border-violet-500/25 transition-all flex items-center justify-center gap-2"
          >
            <BarChart3 className="w-4 h-4 text-amber-400" />
            <span>Open Data Analyst</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
