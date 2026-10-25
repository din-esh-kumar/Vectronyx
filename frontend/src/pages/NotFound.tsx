import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Compass, LayoutDashboard, Sparkles } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#0B0813] text-white flex flex-col items-center justify-center p-6 relative overflow-hidden text-center selection:bg-violet-600/30 selection:text-violet-200">
      {/* Background ambient lighting */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-gradient-to-br from-violet-600/20 via-amber-600/10 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-md mx-auto space-y-6">
        {/* Animated Radar Icon */}
        <div className="relative mx-auto w-24 h-24 rounded-3xl glass-card flex items-center justify-center border border-violet-500/30 shadow-2xl">
          <div className="absolute inset-0 rounded-3xl bg-violet-600/10 animate-ping" />
          <Compass className="w-10 h-10 text-amber-400 animate-spin-slow" />
        </div>

        <div>
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-amber-400 px-3 py-1 rounded-full bg-amber-950/50 border border-amber-500/30">
            Error 404 • Coordinate Drift
          </span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white mt-3 font-display">
            Vector Not Found
          </h1>
          <p className="text-xs sm:text-sm text-violet-200/70 mt-2 leading-relaxed font-sans">
            The requested workspace trajectory does not exist or has been relocated to another dimension.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link
            to="/"
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-gradient-to-r from-violet-600 to-amber-600 hover:from-violet-500 hover:to-amber-500 shadow-lg shadow-violet-900/40 transition-all flex items-center justify-center gap-2"
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Return to Dashboard</span>
          </Link>

          <Link
            to="/data-analyst"
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs sm:text-sm text-violet-200 bg-violet-950/40 hover:bg-violet-900/40 border border-violet-500/25 transition-all flex items-center justify-center gap-2"
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Explore Data Analyst</span>
          </Link>
        </div>
      </div>
    </div>
  );
}