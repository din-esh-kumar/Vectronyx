// frontend/src/features/data-analyst/DatasetVerificationCard.tsx
import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Compass,
  HelpCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
  XCircle,
} from "lucide-react";
import type { DatasetIntakeResponse } from "./types";

interface DatasetVerificationCardProps {
  intake: DatasetIntakeResponse | null;
  verifying: boolean;
  onApplyRecommendedPrompt: (prompt: string) => void;
  onReevaluateWithContext: () => void;
}

const ROLE_BADGE_CLASS: Record<string, string> = {
  "North Star": "bg-amber-500/20 text-amber-200 border-amber-400/50",
  Guardrail: "bg-rose-950/50 text-rose-300 border-rose-500/40",
  Driver: "bg-violet-900/45 text-violet-200 border-violet-500/35",
  "Segment Dimension": "bg-emerald-950/50 text-emerald-300 border-emerald-500/35",
};

export const DatasetVerificationCard: React.FC<DatasetVerificationCardProps> = ({
  intake,
  verifying,
  onApplyRecommendedPrompt,
  onReevaluateWithContext,
}) => {
  if (!intake && !verifying) return null;

  if (verifying && !intake) {
    return (
      <div className="no-print p-5 rounded-2xl glass-card border border-violet-500/25 flex items-center gap-3 text-xs font-mono text-amber-300 animate-fadeIn">
        <RefreshCw className="w-4 h-4 animate-spin text-amber-400 shrink-0" />
        <span>Verifying dataset readiness & aligning problem metrics with stakeholders...</span>
      </div>
    );
  }

  if (!intake) return null;

  const { verification, problem_definition: problem } = intake;
  const isPerfect = verification.status === "perfect";
  const isGood = verification.is_good_dataset;

  return (
    <div className="no-print space-y-4 animate-fadeIn">
      {/* Stage 1: Dataset Verification Gate */}
      <div
        className={`p-5 rounded-2xl glass-card border space-y-3 ${
          isPerfect
            ? "border-emerald-500/35"
            : isGood
            ? "border-amber-500/35"
            : "border-rose-500/45"
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            {isPerfect ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : isGood ? (
              <CheckCircle2 className="w-5 h-5 text-amber-400 shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
            )}
            <h2 className="text-sm font-bold text-white font-display">
              Dataset Readiness Verification
            </h2>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold border ${
                isPerfect
                  ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/40"
                  : isGood
                  ? "bg-amber-950/60 text-amber-300 border-amber-500/40"
                  : "bg-rose-950/60 text-rose-300 border-rose-500/40"
              }`}
            >
              {isPerfect
                ? `Perfect Dataset · ${verification.readiness_score.toFixed(0)}/100`
                : isGood
                ? `Good Dataset · ${verification.readiness_score.toFixed(0)}/100`
                : `Not Ready · ${verification.readiness_score.toFixed(0)}/100`}
            </span>
          </div>

          <button
            type="button"
            onClick={onReevaluateWithContext}
            disabled={verifying}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-semibold text-violet-200 hover:text-white bg-violet-950/50 hover:bg-violet-900/60 border border-violet-500/25 transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin text-amber-400" : ""}`} />
            <span>{verifying ? "Verifying..." : "Re-verify & Align"}</span>
          </button>
        </div>

        <p className="text-xs text-violet-200/85 leading-relaxed">{verification.summary}</p>

        {/* Verification Checks Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {verification.checks.map((chk) => (
            <div
              key={chk.name}
              className={`p-3 rounded-xl border text-xs ${
                chk.status === "pass"
                  ? "bg-emerald-950/20 border-emerald-500/25"
                  : chk.status === "warn"
                  ? "bg-amber-950/20 border-amber-500/25"
                  : "bg-rose-950/30 border-rose-500/35"
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-semibold text-white">{chk.name}</span>
                <span
                  className={`text-[10px] font-mono uppercase font-bold ${
                    chk.status === "pass"
                      ? "text-emerald-400"
                      : chk.status === "warn"
                      ? "text-amber-300"
                      : "text-rose-400"
                  }`}
                >
                  {chk.status}
                </span>
              </div>
              <p className="text-[11px] text-violet-200/75 leading-relaxed">{chk.detail}</p>
            </div>
          ))}
        </div>

        {verification.blocking_issues.length > 0 && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/35 text-xs text-rose-200 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-semibold">Blocking Issues (Problem Definition Skipped)</div>
              <ul className="list-disc pl-4 space-y-0.5">
                {verification.blocking_issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Stage 2: Problem Definition & Stakeholder Metric Alignment (Only for good/perfect datasets) */}
      {isGood && problem && (
        <div className="p-5 rounded-2xl glass-card-bronze border border-amber-500/30 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Compass className="w-5 h-5 text-amber-400 shrink-0" />
              <h2 className="text-sm font-bold text-amber-200 font-display">
                Problem Definition & Stakeholder Metric Alignment
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-950/50 border border-violet-500/30 text-violet-200">
                {problem.ai_provider_used}
              </span>
            </div>

            <button
              type="button"
              onClick={() => onApplyRecommendedPrompt(problem.recommended_analysis_prompt)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-violet-700 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] border border-amber-400/35 transition cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>Use Problem as Analysis Prompt</span>
            </button>
          </div>

          {/* Core Question / Business Goal / Decision Needed */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-violet-950/45 border border-violet-500/25 space-y-1">
              <div className="text-[10px] font-mono uppercase tracking-wider text-amber-300 font-bold flex items-center gap-1">
                <Target className="w-3 h-3" />
                <span>Core Question</span>
              </div>
              <p className="text-xs text-white leading-relaxed">{problem.core_question}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-violet-950/45 border border-violet-500/25 space-y-1">
              <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-300 font-bold">
                Business Goal
              </div>
              <p className="text-xs text-violet-100 leading-relaxed">{problem.business_goal}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-violet-950/45 border border-violet-500/25 space-y-1">
              <div className="text-[10px] font-mono uppercase tracking-wider text-violet-300 font-bold">
                Decision Needed
              </div>
              <p className="text-xs text-violet-100 leading-relaxed">{problem.decision_needed}</p>
            </div>
          </div>

          {/* Aligned Key Metrics */}
          {problem.aligned_metrics.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-amber-300/90 font-semibold">
                Aligned Key Metrics ({problem.aligned_metrics.length})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {problem.aligned_metrics.map((metric) => (
                  <div
                    key={metric.metric_name}
                    className="p-3 rounded-xl bg-black/25 border border-violet-500/20 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white font-mono truncate">
                        {metric.metric_name}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full border shrink-0 ${
                          ROLE_BADGE_CLASS[metric.role] || ROLE_BADGE_CLASS.Driver
                        }`}
                      >
                        {metric.role}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-amber-300/90">
                      Agg: {metric.aggregation}
                    </div>
                    <p className="text-[11px] text-violet-200/75 leading-relaxed">
                      {metric.stakeholder_alignment}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stakeholders & Clarifying Alignment Questions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 pt-1">
            {problem.stakeholders.length > 0 && (
              <div className="p-3.5 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-violet-300 font-semibold flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-amber-400" />
                  <span>Stakeholder Alignment</span>
                </div>
                <div className="space-y-2">
                  {problem.stakeholders.map((st, idx) => (
                    <div key={idx} className="text-xs space-y-0.5">
                      <div className="font-semibold text-white flex flex-wrap items-center gap-1.5">
                        <span>{st.stakeholder_role}</span>
                        {st.target_metrics.length > 0 && (
                          <span className="text-[10px] font-mono text-amber-300">
                            [{st.target_metrics.join(", ")}]
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-violet-200/75">{st.primary_concern}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {problem.clarifying_questions.length > 0 && (
              <div className="p-3.5 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-amber-300 font-semibold flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Stakeholder Alignment Questions</span>
                </div>
                <ul className="space-y-1.5 text-[11px] text-violet-200/80 list-disc pl-4">
                  {problem.clarifying_questions.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
