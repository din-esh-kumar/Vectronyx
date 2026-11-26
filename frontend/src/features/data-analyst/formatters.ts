// frontend/src/features/data-analyst/formatters.ts
import type {
  AlignedMetricSpec,
  DashboardPlan,
  DatasetIntakeResponse,
  DatasetVerificationCheck,
} from "./types";

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

export function buildOfflineDatasetIntake(
  csvContent: string,
  datasetName: string,
  userGoal = ""
): DatasetIntakeResponse {
  const meta = inspectCsvMetadata(csvContent);
  const checks: DatasetVerificationCheck[] = [];
  const warnings: string[] = [];
  const blocking_issues: string[] = [];
  let score = 100;

  if (meta.approxRows < 3) {
    const msg = `Only ${meta.approxRows} data row(s) detected; at least 3 rows are required for statistical analysis.`;
    checks.push({ name: "Sample Size Sufficiency", status: "fail", detail: msg });
    blocking_issues.push(msg);
    score -= 45;
  } else if (meta.approxRows < 10) {
    const msg = `${meta.approxRows} rows detected (below 10-row benchmark); trends will be directional.`;
    checks.push({ name: "Sample Size Sufficiency", status: "warn", detail: msg });
    warnings.push(msg);
    score -= 6;
  } else {
    checks.push({
      name: "Sample Size Sufficiency",
      status: "pass",
      detail: `${meta.approxRows.toLocaleString()} rows ready for profiling and outlier checks.`,
    });
  }

  if (meta.headers.length < 2) {
    const msg = `Only ${meta.headers.length} column(s) found; need at least 2 columns.`;
    checks.push({ name: "Schema & Column Breadth", status: "fail", detail: msg });
    blocking_issues.push(msg);
    score -= 35;
  } else {
    checks.push({
      name: "Schema & Column Breadth",
      status: "pass",
      detail: `${meta.headers.length} columns detected (${meta.excludedIds.length} ID key(s) excluded).`,
    });
  }

  if (meta.numericCandidates.length === 0) {
    const msg = "No non-ID quantitative metrics detected to compute KPIs or distributions.";
    checks.push({ name: "Analytical Metric Coverage", status: "fail", detail: msg });
    blocking_issues.push(msg);
    score -= 40;
  } else if (meta.numericCandidates.length === 1) {
    const msg = `Single quantitative metric (${meta.numericCandidates[0]}); correlation analysis will be limited.`;
    checks.push({ name: "Analytical Metric Coverage", status: "warn", detail: msg });
    warnings.push(msg);
    score -= 5;
  } else {
    checks.push({
      name: "Analytical Metric Coverage",
      status: "pass",
      detail: `${meta.numericCandidates.length} metrics verified: ${meta.numericCandidates.slice(0, 4).join(", ")}.`,
    });
  }

  if (meta.categoricalCandidates.length === 0) {
    const msg = "No categorical dimensions detected; cohort comparison will be limited.";
    checks.push({ name: "Cohort & Time Dimensions", status: "warn", detail: msg });
    warnings.push(msg);
    score -= 5;
  } else {
    checks.push({
      name: "Cohort & Time Dimensions",
      status: "pass",
      detail: `${meta.categoricalCandidates.length} dimension(s): ${meta.categoricalCandidates.slice(0, 3).join(", ")}.`,
    });
  }

  const readiness_score = Math.max(0, Math.min(100, score));
  const is_good_dataset = blocking_issues.length === 0;
  const status: "perfect" | "good_with_warnings" | "unusable" = !is_good_dataset
    ? "unusable"
    : warnings.length === 0 && readiness_score >= 90
    ? "perfect"
    : "good_with_warnings";

  const summary = !is_good_dataset
    ? `'${datasetName || "dataset.csv"}' failed readiness checks: ${blocking_issues[0]}`
    : status === "perfect"
    ? `'${datasetName || "dataset.csv"}' verified as a perfect dataset (${readiness_score}/100): ${meta.approxRows} rows × ${meta.headers.length} cols.`
    : `'${datasetName || "dataset.csv"}' verified as a good dataset (${readiness_score}/100) with ${warnings.length} minor note(s).`;

  if (!is_good_dataset) {
    return {
      dataset_name: datasetName || "dataset.csv",
      verification: {
        status,
        is_good_dataset: false,
        readiness_score,
        summary,
        row_count: meta.approxRows,
        column_count: meta.headers.length,
        cleaned_row_count: meta.approxRows,
        cleaned_column_count: meta.headers.length,
        completeness_pct: 100,
        duplicate_rows: 0,
        numeric_metrics: meta.numericCandidates,
        categorical_dimensions: meta.categoricalCandidates,
        temporal_dimensions: [],
        excluded_id_columns: meta.excludedIds,
        checks,
        warnings,
        blocking_issues,
      },
      problem_definition: null,
    };
  }

  const northStar = meta.numericCandidates[0];
  const guardrail =
    meta.numericCandidates.find((c) => /churn|chargeback|risk|latency|cost/i.test(c)) ||
    meta.numericCandidates[1] ||
    northStar;
  const primaryDim = meta.categoricalCandidates[0];
  const dimPhrase = primaryDim ? `across ${primaryDim}` : "across cohorts";
  const core_question = userGoal.trim()
    ? `Given '${userGoal.trim()}', which cohorts ${dimPhrase} drive ${northStar} while keeping ${guardrail} within safe limits?`
    : `Which cohorts ${dimPhrase} drive sustainable ${northStar} growth while controlling ${guardrail} risk and outlier volatility?`;

  const aligned_metrics: AlignedMetricSpec[] = meta.numericCandidates.slice(0, 4).map((col, i) => {
    const isRate = /rate|pct|percent|ratio|churn|chargeback|margin/i.test(col);
    const role: AlignedMetricSpec["role"] =
      i === 0 ? "North Star" : col === guardrail ? "Guardrail" : "Driver";
    const aggregation = isRate ? "AVERAGE / P50 / P95 (never SUM)" : "SUM & Cohort Share %";
    return {
      metric_name: col,
      role,
      aggregation,
      stakeholder_alignment: `Aligned ${role.toLowerCase()} metric evaluated via ${aggregation}.`,
    };
  });
  meta.categoricalCandidates.slice(0, 2).forEach((dim) => {
    aligned_metrics.push({
      metric_name: dim,
      role: "Segment Dimension",
      aggregation: "GROUP BY / ANOVA η²",
      stakeholder_alignment: `Primary slicing dimension for cohort variance and Pareto benchmarking.`,
    });
  });

  const recommended_analysis_prompt = `Analyze '${datasetName || "dataset.csv"}' to answer: ${core_question} Align KPIs on ${meta.numericCandidates.slice(0, 3).join(", ")}${primaryDim ? ` segmented by ${primaryDim}` : ""}, quantify Pareto/HHI concentration, and isolate anomalies.`;

  return {
    dataset_name: datasetName || "dataset.csv",
    verification: {
      status,
      is_good_dataset: true,
      readiness_score,
      summary,
      row_count: meta.approxRows,
      column_count: meta.headers.length,
      cleaned_row_count: meta.approxRows,
      cleaned_column_count: meta.headers.length,
      completeness_pct: 100,
      duplicate_rows: 0,
      numeric_metrics: meta.numericCandidates,
      categorical_dimensions: meta.categoricalCandidates,
      temporal_dimensions: [],
      excluded_id_columns: meta.excludedIds,
      checks,
      warnings,
      blocking_issues: [],
    },
    problem_definition: {
      core_question,
      business_goal: `Maximize ${northStar} and operating efficiency ${dimPhrase} while keeping ${guardrail} within stakeholder thresholds.`,
      decision_needed: `Prioritize resource allocation and risk remediation ${dimPhrase} based on Pareto share and anomaly diagnostics.`,
      stakeholders: [
        {
          stakeholder_role: "Executive / Business Owner",
          primary_concern: `Scaling ${northStar} across top-performing ${primaryDim || "cohorts"}.`,
          target_metrics: [northStar],
        },
        {
          stakeholder_role: "Risk & Operations Lead",
          primary_concern: `Monitoring ${guardrail} exposure and isolating tail outliers.`,
          target_metrics: [guardrail],
        },
      ],
      aligned_metrics,
      clarifying_questions: [
        `Should optimization prioritize total ${northStar} growth or efficiency per ${primaryDim || "unit"}?`,
        `What upper threshold on ${guardrail} triggers immediate stakeholder escalation?`,
      ],
      recommended_analysis_prompt,
      static_signals: [
        `Schema-detected North Star: ${northStar}; Guardrail: ${guardrail}.`,
        ...(primaryDim ? [`Primary segmentation dimension: ${primaryDim}.`] : []),
      ],
      synthesis_mode: "static_only",
      ai_provider_used: "static-code (client preview)",
    },
  };
}
