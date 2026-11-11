// frontend/src/features/data-analyst/CorrelationHeatmap.tsx
import React, { useState } from "react";
import { GitCompareArrows, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import type { CorrelationInsight, CorrelationMatrixData } from "./types";
import { truncateLabel } from "./formatters";

interface CorrelationHeatmapProps {
  matrix?: CorrelationMatrixData | null;
  insights?: CorrelationInsight[];
}

function cellBackground(r: number, isDiagonal: boolean): string {
  if (isDiagonal) return "rgba(139, 92, 246, 0.28)";
  const mag = Math.min(1, Math.abs(r));
  if (r >= 0) {
    const alpha = (0.1 + mag * 0.65).toFixed(2);
    return `rgba(147, 51, 234, ${alpha})`;
  }
  const alpha = (0.1 + mag * 0.68).toFixed(2);
  return `rgba(194, 103, 26, ${alpha})`;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({
  matrix,
  insights = [],
}) => {
  const [hoveredCell, setHoveredCell] = useState<{ a: string; b: string; r: number } | null>(null);

  if ((!matrix || !matrix.metrics.length) && insights.length === 0) {
    return null;
  }

  return (
    <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-5 print-break-avoid">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
            <GitCompareArrows className="w-5 h-5 text-amber-400" />
            <span>Multivariate Correlation Matrix & Feature Driver Forensics</span>
          </h3>
          <p className="text-xs text-violet-300/70 mt-0.5">
            Measures linear co-movement (Pearson r) and rank-order monotonicity (Spearman ρ) across continuous non-ID features.
          </p>
        </div>

        <div className="flex items-center gap-3 text-[10px] font-mono shrink-0">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-purple-600/80 inline-block border border-violet-400/40" />
            <span className="text-violet-200">+1.0 Positive</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-amber-700/80 inline-block border border-amber-400/40" />
            <span className="text-amber-300">-1.0 Inverse</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Matrix Heatmap Grid */}
        {matrix && matrix.metrics.length >= 2 && (
          <div className="xl:col-span-6 overflow-x-auto space-y-2.5">
            <table className="w-full border-separate border-spacing-1 text-xs">
              <thead>
                <tr>
                  <th className="p-1.5 text-left text-[10px] font-mono text-violet-300/70 uppercase">
                    Variable
                  </th>
                  {matrix.metrics.map((m) => (
                    <th
                      key={m}
                      title={m}
                      className="p-1.5 text-center font-mono text-[10px] text-violet-200 font-semibold whitespace-nowrap"
                    >
                      {truncateLabel(m, 11)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.metrics.map((rowMetric, rIdx) => (
                  <tr key={rowMetric}>
                    <td
                      title={rowMetric}
                      className="p-1.5 font-mono text-[11px] font-semibold text-white whitespace-nowrap pr-2"
                    >
                      {truncateLabel(rowMetric, 14)}
                    </td>
                    {matrix.metrics.map((colMetric, cIdx) => {
                      const val = matrix.matrix[rIdx]?.[cIdx] ?? 0;
                      const isDiag = rIdx === cIdx;
                      const highContrast = !isDiag && Math.abs(val) >= 0.55;
                      return (
                        <td
                          key={colMetric}
                          onMouseEnter={() => setHoveredCell({ a: rowMetric, b: colMetric, r: val })}
                          onMouseLeave={() => setHoveredCell(null)}
                          style={{
                            backgroundColor: cellBackground(val, isDiag),
                            color: highContrast ? "#FFFFFF" : "var(--text-primary)",
                          }}
                          className="p-2 text-center font-mono text-[11px] font-bold rounded-lg border border-violet-500/15 transition cursor-default select-none"
                          title={`${rowMetric} vs ${colMetric}: Pearson r = ${val.toFixed(2)}`}
                        >
                          {val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="text-[11px] font-mono text-violet-300/80 min-h-[18px]">
              {hoveredCell
                ? `${hoveredCell.a} × ${hoveredCell.b}: Pearson r = ${hoveredCell.r >= 0 ? "+" : ""}${hoveredCell.r.toFixed(2)}`
                : "Hover any matrix cell to inspect exact pairwise correlation."}
            </div>
          </div>
        )}

        {/* Top Ranked Pairwise Findings */}
        <div className={`${matrix && matrix.metrics.length >= 2 ? "xl:col-span-6" : "xl:col-span-12"} space-y-2.5`}>
          {insights.length > 0 ? (
            insights.map((corr, idx) => {
              const isPos = corr.direction === "Positive";
              const isInv = corr.direction === "Inverse";
              return (
                <div
                  key={`${corr.metric_a}-${corr.metric_b}-${idx}`}
                  className="p-3.5 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-1.5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-bold text-xs sm:text-sm text-white">
                      {isPos ? (
                        <ArrowUpRight className="w-4 h-4 text-violet-400 shrink-0" />
                      ) : isInv ? (
                        <ArrowDownRight className="w-4 h-4 text-amber-400 shrink-0" />
                      ) : (
                        <Minus className="w-4 h-4 text-violet-300 shrink-0" />
                      )}
                      <span>
                        {corr.metric_a} × {corr.metric_b}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                      <span
                        className={`px-2 py-0.5 rounded-full font-bold border ${
                          corr.strength === "Strong"
                            ? "bg-amber-950/60 text-amber-300 border-amber-500/35"
                            : "bg-violet-900/50 text-violet-200 border-violet-500/30"
                        }`}
                      >
                        r = {corr.pearson_r >= 0 ? "+" : ""}
                        {corr.pearson_r.toFixed(2)}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-violet-950/60 text-violet-200 border border-violet-500/25">
                        ρ = {corr.spearman_rho >= 0 ? "+" : ""}
                        {corr.spearman_rho.toFixed(2)}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-violet-950/60 text-violet-300 border border-violet-500/20">
                        {corr.p_value < 0.001 ? "p < 0.001" : `p = ${corr.p_value.toFixed(3)}`}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-violet-200/80 leading-relaxed font-sans">
                    {corr.interpretation}
                  </p>
                </div>
              );
            })
          ) : (
            <p className="text-xs text-violet-300/70">
              No statistically varying pairs available for bivariate covariance ranking.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
