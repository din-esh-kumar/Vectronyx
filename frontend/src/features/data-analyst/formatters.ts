// frontend/src/features/data-analyst/formatters.ts
import type { DashboardPlan } from "./types";

const ID_HEADER_RE =
  /^(?:unnamed:\s*0|index|id|uuid|guid|isbn(?:10|13)?|book_?id|user_?id|customer_?id|client_?id|order_?id|product_?id|account_?id|transaction_?id|txn_?id|record_?id|row_?id)$|_(?:id|uuid|guid|isbn|sku|ssn)$/i;

export function formatMetricValue(
  value: number | null | undefined,
  unitFormat?: string | null,
  isFractionHint = false
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (unitFormat === "percent") {
    const pct = isFractionHint || (Math.abs(value) <= 1.0 && value !== 0) ? value * 100 : value;
    return `${pct.toFixed(2)}%`;
  }
  const prefix = unitFormat === "currency" ? "$" : "";
  const av = Math.abs(value);
  if (av >= 1_000_000_000) return `${prefix}${(value / 1_000_000_000).toFixed(2)}B`;
  if (av >= 1_000_000) return `${prefix}${(value / 1_000_000).toFixed(2)}M`;
  if (av >= 10_000) return `${prefix}${(value / 1_000).toFixed(1)}K`;
  if (av >= 100) return `${prefix}${Math.round(value).toLocaleString()}`;
  if (Math.abs(value - Math.round(value)) < 1e-6) return `${prefix}${Math.round(value).toLocaleString()}`;
  return `${prefix}${value.toFixed(2)}`;
}

export function formatAxisTick(value: number | string, unitFormat?: string | null): string {
  if (typeof value === "string") return value;
  if (!Number.isFinite(value)) return "";
  if (unitFormat === "percent") {
    const pct = Math.abs(value) <= 1.0 && value !== 0 ? value * 100 : value;
    return `${pct.toFixed(1)}%`;
  }
  const prefix = unitFormat === "currency" ? "$" : "";
  const av = Math.abs(value);
  if (av >= 1_000_000_000) return `${prefix}${(value / 1_000_000_000).toFixed(1)}B`;
  if (av >= 1_000_000) return `${prefix}${(value / 1_000_000).toFixed(1)}M`;
  if (av >= 1_000) return `${prefix}${(value / 1_000).toFixed(1)}K`;
  if (Math.abs(value - Math.round(value)) < 1e-6) return `${prefix}${Math.round(value)}`;
  return `${prefix}${value.toFixed(1)}`;
}

export function truncateLabel(label: string, maxLen = 18): string {
  const s = String(label || "").trim();
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen - 1)}…`;
}

export function parseCsvLine(line: string, delimiter: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === delimiter && !inQuotes) {
      cells.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  cells.push(current.trim());
  return cells;
}

export interface DetectedCsvMeta {
  headers: string[];
  nonIdHeaders: string[];
  excludedIds: string[];
  numericCandidates: string[];
  categoricalCandidates: string[];
  approxRows: number;
}

export function inspectCsvMetadata(csvContent: string): DetectedCsvMeta {
  const cleaned = (csvContent || "").replace(/^\uFEFF/, "").trim();
  if (!cleaned) {
    return {
      headers: [],
      nonIdHeaders: [],
      excludedIds: [],
      numericCandidates: [],
      categoricalCandidates: [],
      approxRows: 0,
    };
  }
  const lines = cleaned.split(/\r?\n/).filter((l) => l.trim() !== "");
  const headerLine = lines[0] || "";
  const delimiter = headerLine.includes("\t") && !headerLine.includes(",") ? "\t" : ",";
  const headers = parseCsvLine(headerLine, delimiter).filter(Boolean);
  const sampleRows = lines.slice(1, 25).map((l) => parseCsvLine(l, delimiter));

  const excludedIds: string[] = [];
  const nonIdHeaders: string[] = [];
  const numericCandidates: string[] = [];
  const categoricalCandidates: string[] = [];

  headers.forEach((h, idx) => {
    if (ID_HEADER_RE.test(h.trim())) {
      excludedIds.push(h);
      return;
    }
    nonIdHeaders.push(h);

    const vals = sampleRows.map((r) => (idx < r.length ? r[idx].trim() : "")).filter((v) => v !== "");
    const looksNumeric =
      vals.length > 0 &&
      vals.every((v) => /^-?\d+(?:\.\d+)?$/.test(v.replace(/,/g, "")));

    if (looksNumeric && !/year|yr/i.test(h)) {
      numericCandidates.push(h);
    } else if (!/url|uri|thumbnail|description|abstract/i.test(h)) {
      categoricalCandidates.push(h);
    }
  });

  return {
    headers,
    nonIdHeaders,
    excludedIds,
    numericCandidates,
    categoricalCandidates,
    approxRows: Math.max(0, lines.length - 1),
  };
}

export function buildClientDossierMarkdown(plan: DashboardPlan): string {
  const dossier = plan.dossier;
  const lines: string[] = [
    `# Executive Intelligence Dossier: ${plan.title}`,
    `**Dataset:** \`${plan.dataset_name}\` | **Data Integrity:** \`${dossier?.data_integrity_score ?? 100}%\``,
    "",
    "## Executive Summary",
    plan.summary,
    "",
  ];

  if (dossier) {
    lines.push("## 1. Boardroom Verdict", `> ${dossier.executive_verdict}`, "");
    lines.push(
      "## 2. Situation - Complication - Resolution",
      `- **Situation:** ${dossier.situation}`,
      `- **Complication:** ${dossier.complication}`,
      `- **Resolution:** ${dossier.resolution}`,
      ""
    );
  }

  if (plan.kpis.length > 0) {
    lines.push("## 3. Executive KPI Scorecard", "| Metric | Value | Variance | Benchmark | Takeaway |", "| :--- | :--- | :--- | :--- | :--- |");
    plan.kpis.forEach((k) => {
      lines.push(`| **${k.title}** | \`${k.value}\` | ${k.change || "—"} | ${k.benchmark || "—"} | ${k.executive_takeaway || k.rationale} |`);
    });
    lines.push("");
  }

  if (plan.visuals.length > 0) {
    lines.push("## 4. Adaptive Visual Intelligence", "| Title | Type | Axes | Selection Rationale | Key Finding |", "| :--- | :--- | :--- | :--- | :--- |");
    plan.visuals.forEach((v) => {
      lines.push(`| **${v.title}** | \`${v.chart_type}\` | \`${v.x_axis}\` → \`${v.y_axis}\` | ${v.selection_reason || v.description} | ${v.key_insight || "—"} |`);
    });
    lines.push("");
  }

  if (dossier?.correlation_insights?.length) {
    lines.push("## 5. Correlation & Driver Analysis", "| Pair | Pearson r | Spearman ρ | p-value | Interpretation |", "| :--- | :--- | :--- | :--- | :--- |");
    dossier.correlation_insights.forEach((c) => {
      lines.push(`| **${c.metric_a} × ${c.metric_b}** | ${c.pearson_r.toFixed(2)} | ${c.spearman_rho.toFixed(2)} | ${c.p_value} | ${c.interpretation} |`);
    });
    lines.push("");
  }

  if (dossier?.statistical_diagnostics?.length) {
    lines.push("## 6. Non-Parametric Quantiles & Distribution Forensics", "| Metric | Mean | Median | Q1–Q3 | P95 | Skew | CV | Outliers |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |");
    dossier.statistical_diagnostics.forEach((d) => {
      const iqr = d.p25 != null && d.p75 != null ? `${d.p25}–${d.p75}` : "—";
      lines.push(`| **${d.metric_name}** | ${d.mean} | ${d.median ?? "—"} | ${iqr} | ${d.p95 ?? "—"} | ${d.skewness} | ${d.cv} | ${d.outlier_count ?? "—"} |`);
    });
    lines.push("");
  }

  if (dossier?.risk_matrix?.length) {
    lines.push("## 7. Governance & Risk Matrix", "| Risk | Severity | Probability | Exposure | Mitigation |", "| :--- | :--- | :--- | :--- | :--- |");
    dossier.risk_matrix.forEach((r) => {
      lines.push(`| **${r.risk_title}** | ${r.severity} | ${r.probability} | ${r.business_exposure} | ${r.mitigation_protocol} |`);
    });
    lines.push("");
  }

  return lines.join("\n");
}
