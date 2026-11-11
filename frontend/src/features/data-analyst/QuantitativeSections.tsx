// frontend/src/features/data-analyst/QuantitativeSections.tsx
import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  Layers,
  ShieldAlert,
} from "lucide-react";
import type {
  AnomalyFinding,
  DataQualityAudit,
  RiskAssessment,
  SegmentBenchmark,
  StatisticalDiagnostic,
} from "./types";
import { formatMetricValue, truncateLabel } from "./formatters";

/* =========================================================================
   Inline Quantile IQR Box-and-Whisker Micro-Bar
   ========================================================================= */
const IqrSpreadBar: React.FC<{ diag: StatisticalDiagnostic }> = ({ diag }) => {
  if (
    diag.min_val == null ||
    diag.max_val == null ||
    diag.p25 == null ||
    diag.median == null ||
    diag.p75 == null
  ) {
    return <span className="text-violet-400/50 text-[10px] font-mono">—</span>;
  }

  const span = diag.max_val - diag.min_val;
  if (span <= 0) {
    return <span className="text-violet-400/60 text-[10px] font-mono">Zero span</span>;
  }

  const q1Pct = Math.max(0, Math.min(100, ((diag.p25 - diag.min_val) / span) * 100));
  const medPct = Math.max(0, Math.min(100, ((diag.median - diag.min_val) / span) * 100));
  const q3Pct = Math.max(q1Pct, Math.min(100, ((diag.p75 - diag.min_val) / span) * 100));

  return (
    <div className="w-28 space-y-0.5" title={`Min ${diag.min_val} | Q1 ${diag.p25} | Med ${diag.median} | Q3 ${diag.p75} | Max ${diag.max_val}`}>
      <div className="relative h-2.5 rounded-full bg-violet-950/60 border border-violet-500/20 overflow-hidden">
        {/* IQR Box */}
        <div
          className="absolute top-0 bottom-0 bg-violet-500/60 border-x border-violet-300"
          style={{ left: `${q1Pct}%`, width: `${Math.max(4, q3Pct - q1Pct)}%` }}
        />
        {/* Median Marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-amber-400"
          style={{ left: `${medPct}%` }}
        />
      </div>
      <div className="flex justify-between text-[9px] font-mono text-violet-300/60">
        <span>{formatMetricValue(diag.min_val, diag.unit_format)}</span>
        <span>{formatMetricValue(diag.max_val, diag.unit_format)}</span>
      </div>
    </div>
  );
};

/* =========================================================================
   1. Econometric Distribution & Non-Parametric Quantiles Table
   ========================================================================= */
export const QuantileDiagnosticsSection: React.FC<{
  diagnostics: StatisticalDiagnostic[];
}> = ({ diagnostics }) => {
  if (!diagnostics || diagnostics.length === 0) return null;

  return (
    <div className="p-6 rounded-2xl glass-card border border-violet-500/20 overflow-hidden space-y-4 print-break-avoid">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
            <Activity className="w-5 h-5 text-amber-400" />
            <span>Econometric Distribution & Non-Parametric Quantile Forensics</span>
          </h3>
          <p className="text-xs text-violet-300/70 mt-0.5">
            Compares arithmetic Mean vs Median (P50), Q1–Q3 Interquartile Range, P95 tail bounds, CV (σ/μ), and Tukey 1.5×IQR fence outliers.
          </p>
        </div>
        <span className="text-[10px] font-mono text-amber-300/80 self-start sm:self-auto">
          Amber tick = Median • Bar = IQR
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-violet-500/20 text-violet-400 font-mono uppercase tracking-wider text-[10px]">
              <th className="py-2.5 px-3">Metric</th>
              <th className="py-2.5 px-3 text-right">Mean</th>
              <th className="py-2.5 px-3 text-right">Median (P50)</th>
              <th className="py-2.5 px-3 text-right">Q1–Q3 (IQR)</th>
              <th className="py-2.5 px-3 text-right">P95 Tail</th>
              <th className="py-2.5 px-3">Spread</th>
              <th className="py-2.5 px-3 text-right">Skew / CV</th>
              <th className="py-2.5 px-3 text-right">Outliers</th>
              <th className="py-2.5 px-3">Shape Verdict</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-violet-500/10 text-violet-200">
            {diagnostics.map((d, i) => {
              const isFrac = d.unit_format === "percent" && (d.max_val ?? 1) <= 1.0;
              const iqrLabel =
                d.p25 != null && d.p75 != null
                  ? `${formatMetricValue(d.p25, d.unit_format, isFrac)}–${formatMetricValue(d.p75, d.unit_format, isFrac)}`
                  : "—";
              const outPct = d.outlier_pct ?? 0;

              return (
                <tr key={i} className="hover:bg-violet-900/20 transition align-top">
                  <td className="py-3 px-3 font-bold text-white whitespace-nowrap">
                    <div>{d.metric_name}</div>
                    {d.sample_count && (
                      <div className="text-[10px] font-mono text-violet-300/60 font-normal">
                        n = {d.sample_count.toLocaleString()}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-3 font-mono text-right whitespace-nowrap">
                    {formatMetricValue(d.mean, d.unit_format, isFrac)}
                  </td>
                  <td className="py-3 px-3 font-mono text-right font-semibold text-amber-300 whitespace-nowrap">
                    {formatMetricValue(d.median, d.unit_format, isFrac)}
                  </td>
                  <td className="py-3 px-3 font-mono text-right whitespace-nowrap">{iqrLabel}</td>
                  <td className="py-3 px-3 font-mono text-right whitespace-nowrap">
                    {formatMetricValue(d.p95, d.unit_format, isFrac)}
                  </td>
                  <td className="py-3 px-3">
                    <IqrSpreadBar diag={d} />
                  </td>
                  <td className="py-3 px-3 font-mono text-right whitespace-nowrap">
                    <span className="text-amber-300 font-semibold">{d.skewness}</span>
                    <span className="text-violet-400/60"> / </span>
                    <span className="text-violet-200">{d.cv}</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-right whitespace-nowrap">
                    {d.outlier_count != null ? (
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          outPct >= 5
                            ? "bg-amber-950/60 text-amber-300 border border-amber-500/30"
                            : "bg-violet-950/50 text-violet-200 border border-violet-500/20"
                        }`}
                      >
                        {d.outlier_count.toLocaleString()} ({outPct.toFixed(1)}%)
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="py-3 px-3 max-w-xs space-y-1">
                    {d.normality_verdict && (
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-violet-900/50 text-violet-200 border border-violet-500/25">
                        {d.normality_verdict}
                      </span>
                    )}
                    <div className="text-[11px] text-violet-300/75 leading-relaxed">
                      {d.interpretation}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* =========================================================================
   2. Segment Variance Benchmarks (ANOVA eta^2 Cohort Tables)
   ========================================================================= */
export const SegmentBenchmarksSection: React.FC<{
  benchmarks?: SegmentBenchmark[];
}> = ({ benchmarks = [] }) => {
  if (!benchmarks || benchmarks.length === 0) return null;

  return (
    <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-5 print-break-avoid">
      <div>
        <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-amber-400" />
          <span>Cohort Variance Benchmarks (One-Way ANOVA η²)</span>
        </h3>
        <p className="text-xs text-violet-300/70 mt-0.5">
          Quantifies how strongly categorical cohorts explain metric dispersion (η²) and benchmarks leading vs lagging segments against portfolio mean.
        </p>
      </div>

      <div className="space-y-6">
        {benchmarks.map((sb, idx) => {
          const etaPct = Math.min(100, Math.round(sb.eta_squared * 100));
          return (
            <div
              key={`${sb.dimension}-${sb.metric}-${idx}`}
              className="p-4 rounded-xl bg-violet-950/30 border border-violet-500/20 space-y-3"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-white font-display">
                      {sb.metric} by {sb.dimension}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/60 text-amber-300 border border-amber-500/30">
                      ANOVA η² = {sb.eta_squared.toFixed(2)} ({etaPct}% variance explained)
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-violet-900/50 text-violet-200 border border-violet-500/25">
                      {sb.cohort_count.toLocaleString()} Cohorts
                    </span>
                  </div>
                  <p className="text-xs text-violet-200/80 mt-1">{sb.narrative}</p>
                </div>

                <div className="w-full md:w-44 shrink-0 space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-violet-300/70">
                    <span>Cohort Effect Size</span>
                    <span>{etaPct}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-violet-950/80 border border-violet-500/25 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-violet-500 to-amber-500"
                      style={{ width: `${Math.max(4, etaPct)}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-violet-500/20 text-violet-400 font-mono uppercase tracking-wider text-[10px]">
                      <th className="py-2 px-2.5">Segment</th>
                      <th className="py-2 px-2.5 text-right">n</th>
                      <th className="py-2 px-2.5 text-right">Mean</th>
                      <th className="py-2 px-2.5 text-right">vs Mean</th>
                      <th className="py-2 px-2.5 text-right">Vol Share</th>
                      <th className="py-2 px-2.5 text-right">Tier Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-violet-500/10 text-violet-200">
                    {sb.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-violet-900/20 transition">
                        <td className="py-2 px-2.5 font-semibold text-white" title={row.segment}>
                          {truncateLabel(row.segment, 28)}
                        </td>
                        <td className="py-2 px-2.5 font-mono text-right">
                          {row.record_count.toLocaleString()}
                        </td>
                        <td className="py-2 px-2.5 font-mono text-right font-semibold">
                          {row.metric_mean.toLocaleString()}
                        </td>
                        <td
                          className={`py-2 px-2.5 font-mono text-right font-semibold ${
                            row.vs_mean_pct >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {row.vs_mean_pct >= 0 ? "+" : ""}
                          {row.vs_mean_pct.toFixed(1)}%
                        </td>
                        <td className="py-2 px-2.5 font-mono text-right">
                          {row.share_pct.toFixed(1)}%
                        </td>
                        <td className="py-2 px-2.5 text-right">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                              row.status === "Outperformer"
                                ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/30"
                                : row.status === "Underperformer"
                                ? "bg-rose-950/60 text-rose-300 border-rose-500/30"
                                : "bg-violet-900/50 text-violet-200 border-violet-500/25"
                            }`}
                          >
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* =========================================================================
   3. IsolationForest Multivariate Outlier Forensics
   ========================================================================= */
export const OutlierForensicsSection: React.FC<{
  anomalies?: AnomalyFinding[];
}> = ({ anomalies = [] }) => {
  if (!anomalies || anomalies.length === 0) return null;

  return (
    <div className="p-5 sm:p-6 rounded-2xl glass-card-bronze border border-amber-500/25 space-y-4 print-break-avoid">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <h3 className="text-base font-bold text-amber-300 font-display">
            Scikit-Learn IsolationForest: Multivariate Outlier Forensics
          </h3>
        </div>
        <span className="text-[11px] font-mono text-amber-200/80">
          {anomalies.length} Extreme Observation(s) Flagged (Non-ID Feature Space)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {anomalies.map((anom, i) => {
          const featurePairs = Object.entries(anom.features || {})
            .filter(([, v]) => v !== null && v !== undefined && String(v).trim() !== "")
            .slice(0, 4);

          return (
            <div
              key={i}
              className="p-4 bg-violet-950/50 border border-amber-500/25 rounded-xl text-xs space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between font-bold text-white font-mono">
                  <span>Observation #{anom.row_index + 1}</span>
                  <span className="px-2 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-500/30 text-[10px]">
                    Anomaly Score: {anom.score}
                  </span>
                </div>

                {featurePairs.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {featurePairs.map(([k, v]) => (
                      <span
                        key={k}
                        className="px-1.5 py-0.5 rounded bg-violet-900/50 text-violet-200 border border-violet-500/20 font-mono text-[10px]"
                      >
                        {k}: {truncateLabel(String(v), 20)}
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-violet-200/85 text-[11px] font-sans leading-relaxed">
                  {anom.explanation}
                </p>

                {anom.root_cause_attribution && (
                  <p className="text-[11px] text-amber-300/95 font-sans leading-relaxed">
                    <strong>Root Cause:</strong> {anom.root_cause_attribution}
                  </p>
                )}

                {anom.business_impact && (
                  <p className="text-[11px] text-violet-200/75 font-sans leading-relaxed">
                    <strong>Impact:</strong> {anom.business_impact}
                  </p>
                )}
              </div>

              {anom.action_required && (
                <div className="p-2.5 bg-amber-950/60 rounded-lg border border-amber-500/30 text-[10.5px] text-amber-200 font-medium font-sans leading-snug">
                  <strong>Action:</strong> {anom.action_required}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* =========================================================================
   4. Risk Governance Matrix, Data Quality Audit & Methodological Disclosures
   ========================================================================= */
export const DataGovernanceSection: React.FC<{
  risks?: RiskAssessment[];
  audit?: DataQualityAudit | null;
  notes?: string[];
}> = ({ risks = [], audit, notes = [] }) => {
  const [showSchemaTable, setShowSchemaTable] = useState(false);

  if (risks.length === 0 && !audit && notes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Risk Governance Matrix */}
      {risks.length > 0 && (
        <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4 print-break-avoid">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              <span>Enterprise Risk Governance & Mitigation Register</span>
            </h3>
            <span className="text-xs font-mono text-violet-400/70">
              {risks.length} Active Risk Vector(s)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {risks.map((r, i) => (
              <div
                key={i}
                className="p-4 rounded-xl bg-violet-950/35 border border-violet-500/20 space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-sm font-bold text-white font-display">{r.risk_title}</h4>
                  <div className="flex items-center gap-1.5 text-[10px] font-mono">
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold border ${
                        /critical|high/i.test(r.severity)
                          ? "bg-rose-950/60 text-rose-300 border-rose-500/30"
                          : "bg-amber-950/60 text-amber-300 border-amber-500/30"
                      }`}
                    >
                      Severity: {r.severity}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-violet-900/50 text-violet-200 border border-violet-500/25">
                      Prob: {r.probability}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-violet-200/80 leading-relaxed">
                  <strong>Exposure:</strong> {r.business_exposure}
                </p>
                <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/20 text-[11px] text-emerald-300 leading-relaxed">
                  <strong>Mitigation Protocol:</strong> {r.mitigation_protocol}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Quality Governance & Schema Semantic Audit */}
      {audit && (
        <div className="p-6 rounded-2xl glass-card border border-violet-500/20 space-y-4 print-break-avoid">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
                <Database className="w-5 h-5 text-amber-400" />
                <span>Data Governance, Hygiene & Schema Semantic Typing</span>
              </h3>
              <p className="text-xs text-violet-300/70 mt-0.5">
                Automated column-role audit separating ID keys, intensive rates, additive measures, and chronological axes before modeling.
              </p>
            </div>

            {audit.column_audit.length > 0 && (
              <button
                onClick={() => setShowSchemaTable((prev) => !prev)}
                className="no-print inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-violet-950/60 hover:bg-violet-900/70 text-violet-200 text-xs font-mono border border-violet-500/30 cursor-pointer self-start sm:self-auto"
              >
                {showSchemaTable ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" />
                    <span>Hide Column Matrix ({audit.column_audit.length})</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    <span>Inspect Column Matrix ({audit.column_audit.length})</span>
                  </>
                )}
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/15">
              <span className="text-[11px] text-violet-300/70">Observations × Fields</span>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {audit.total_rows.toLocaleString()} × {audit.total_columns}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/15">
              <span className="text-[11px] text-violet-300/70">Cell Completeness</span>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                {audit.completeness_pct.toFixed(1)}%
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/15">
              <span className="text-[11px] text-violet-300/70">Duplicate Rows</span>
              <div className="text-lg font-bold text-amber-300 font-mono mt-0.5">
                {audit.duplicate_rows.toLocaleString()} ({audit.duplicate_pct.toFixed(1)}%)
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-violet-950/40 border border-violet-500/15">
              <span className="text-[11px] text-violet-300/70">Excluded ID Keys</span>
              <div className="text-lg font-bold text-violet-200 font-mono mt-0.5">
                {audit.excluded_id_columns.length}
              </div>
            </div>
          </div>

          {audit.excluded_id_columns.length > 0 && (
            <div className="text-xs bg-amber-950/35 border border-amber-500/25 rounded-xl px-3.5 py-2.5 text-amber-200 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                <strong>Identifier Guardrail Active:</strong> Excluded{" "}
                <code className="font-mono">{audit.excluded_id_columns.join(", ")}</code> from KPI sums, correlations, and IsolationForest features to prevent bogus numeric distortion.
              </span>
            </div>
          )}

          {showSchemaTable && audit.column_audit.length > 0 && (
            <div className="overflow-x-auto pt-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-violet-500/20 text-violet-400 font-mono uppercase tracking-wider text-[10px]">
                    <th className="py-2 px-2.5">Column</th>
                    <th className="py-2 px-2.5">Semantic Role</th>
                    <th className="py-2 px-2.5">Dtype</th>
                    <th className="py-2 px-2.5 text-right">Nulls</th>
                    <th className="py-2 px-2.5 text-right">Unique</th>
                    <th className="py-2 px-2.5">Analyst Handling</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-violet-500/10 text-violet-200">
                  {audit.column_audit.map((col, idx) => (
                    <tr key={idx} className="hover:bg-violet-900/20 transition">
                      <td className="py-2 px-2.5 font-mono font-bold text-white">{col.name}</td>
                      <td className="py-2 px-2.5">
                        <span className="px-2 py-0.5 rounded bg-violet-900/50 text-violet-200 border border-violet-500/25 font-mono text-[10px]">
                          {col.semantic_role}
                        </span>
                      </td>
                      <td className="py-2 px-2.5 font-mono text-[11px]">{col.dtype}</td>
                      <td className="py-2 px-2.5 font-mono text-right">
                        {col.null_count.toLocaleString()} ({col.null_pct.toFixed(1)}%)
                      </td>
                      <td className="py-2 px-2.5 font-mono text-right">
                        {col.unique_count.toLocaleString()}
                      </td>
                      <td className="py-2 px-2.5 text-[11px] text-violet-300/80">
                        {col.recommendation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Methodological Disclosures */}
      {notes.length > 0 && (
        <div className="p-5 rounded-2xl glass-card border border-violet-500/20 space-y-2.5 print-break-avoid">
          <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-violet-300">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>Methodological Disclosures & Statistical Guardrails</span>
          </div>
          <ul className="space-y-1.5 text-xs text-violet-200/80 list-disc pl-5 leading-relaxed">
            {notes.map((n, idx) => (
              <li key={idx}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
