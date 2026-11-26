# backend/app/modules/data_analyst/problem_definer.py
"""
Dataset Readiness Verification & Stakeholder Problem Definition Engine.

Stage 1: Verifies whether an ingested CSV/TSV dataset is structurally and statistically
         sound ("perfect" or "good_with_warnings" vs "unusable").
Stage 2: Only when the dataset passes verification, defines the core analytical question,
         business goal, decision needed, and aligns key metrics with stakeholders grounded
         strictly in the dataset's verified schema and semantic roles.
"""
from __future__ import annotations

import io
import logging
import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel

from app.modules.data_analyst.data_cleaner import clean_and_deduplicate_dataset
from app.modules.data_analyst.profiler import (
    build_expert_statistical_diagnostics,
    classify_dataframe_roles,
    compute_correlations_and_matrix,
    compute_segment_benchmarks,
    format_compact_value,
    safe_float,
)
from app.modules.data_analyst.schemas import (
    AlignedMetricSpec,
    ConcentrationAnalysis,
    CorrelationInsight,
    DataCleansingReport,
    DatasetIntakeResponse,
    DatasetVerificationCheck,
    DatasetVerificationResult,
    ProblemDefinitionResult,
    SegmentBenchmark,
    StakeholderAlignment,
    StatisticalDiagnostic,
)
from app.services.llm.instructor_client import (
    format_provider_model_label,
    generate_structured,
    get_configured_providers,
    get_last_provider_used,
)

logger = logging.getLogger("vectronyx.problem_definer")

_MIN_ROWS = 3
_RECOMMENDED_ROWS = 10
_MIN_COLS = 2
_RISK_METRIC_RE = re.compile(r"(?:churn|chargeback|fraud|risk|defect|bounce|error|latency|delay|cost|loss|cancel)", re.IGNORECASE)
_GROWTH_METRIC_RE = re.compile(r"(?:revenue|profit|margin|arr|mrr|volume|sales|gmv|yield|fee|income|bookings|ltv)", re.IGNORECASE)
_VOLUME_METRIC_RE = re.compile(r"(?:transaction|count|unit|order|user|customer|session|deal|volume|quantity)", re.IGNORECASE)


class _LLMProblemDefinitionDraft(BaseModel):
    core_question: str
    business_goal: str
    decision_needed: str
    stakeholders: List[StakeholderAlignment]
    aligned_metrics: List[AlignedMetricSpec]
    clarifying_questions: List[str]
    recommended_analysis_prompt: str


def _parse_delimited_csv(csv_text: str) -> pd.DataFrame:
    """Parse CSV or TSV safely, sniffing delimiter when tabs are present."""
    stripped = (csv_text or "").strip()
    if not stripped:
        raise ValueError("Dataset content is empty.")
    first_line = stripped.splitlines()[0]
    sep = "\t" if ("\t" in first_line and "," not in first_line) else ","
    return pd.read_csv(io.StringIO(csv_text), sep=sep)


def verify_dataset_readiness(
    csv_text: str,
    dataset_name: str = "dataset.csv",
) -> Tuple[
    DatasetVerificationResult,
    Optional[pd.DataFrame],
    Optional[DataCleansingReport],
    Optional[Dict[str, Dict[str, Any]]],
]:
    """
    Verify whether an uploaded dataset is 'perfect', 'good_with_warnings', or 'unusable'.
    Returns (verification_result, cleaned_df, cleansing_report, semantic_roles).
    """
    checks: List[DatasetVerificationCheck] = []
    warnings: List[str] = []
    blocking_issues: List[str] = []

    if not csv_text or not csv_text.strip():
        msg = "Dataset payload is empty. Upload a non-empty CSV or TSV file."
        return (
            DatasetVerificationResult(
                status="unusable",
                is_good_dataset=False,
                readiness_score=0.0,
                summary=msg,
                checks=[DatasetVerificationCheck(name="File Parseability", status="fail", detail=msg)],
                blocking_issues=[msg],
            ),
            None,
            None,
            None,
        )

    try:
        raw_df = _parse_delimited_csv(csv_text)
    except Exception as exc:
        msg = f"Failed to parse tabular CSV/TSV structure ({exc})."
        return (
            DatasetVerificationResult(
                status="unusable",
                is_good_dataset=False,
                readiness_score=0.0,
                summary=msg,
                checks=[DatasetVerificationCheck(name="File Parseability", status="fail", detail=msg)],
                blocking_issues=[msg],
            ),
            None,
            None,
            None,
        )

    raw_rows, raw_cols = raw_df.shape
    raw_total_cells = max(1, raw_rows * raw_cols)
    raw_null_cells = int(raw_df.isna().sum().sum()) if raw_rows > 0 and raw_cols > 0 else raw_total_cells
    raw_completeness = round(((raw_total_cells - raw_null_cells) / raw_total_cells) * 100.0, 1)
    raw_dups = int(raw_df.duplicated().sum()) if raw_rows > 0 else 0

    cleaned_df, cleansing_report = clean_and_deduplicate_dataset(raw_df)
    clean_rows, clean_cols = cleaned_df.shape
    roles = classify_dataframe_roles(cleaned_df)

    numeric_metrics = [
        col for col, info in roles.items()
        if info.get("is_numeric") or info.get("role") in ("additive_metric", "intensive_metric", "rate")
    ]
    categorical_dims = [
        col for col, info in roles.items()
        if info.get("role") in ("categorical_low", "categorical_medium", "categorical_high")
    ]
    temporal_dims = [
        col for col, info in roles.items()
        if info.get("role") == "datetime"
    ]
    excluded_ids = [
        col for col, info in roles.items()
        if info.get("role") == "identifier"
    ]

    score = 100.0

    # 1. Sample size check
    if raw_rows < _MIN_ROWS or clean_rows == 0:
        detail = f"Only {raw_rows} row(s) received ({clean_rows} usable); at least {_MIN_ROWS} rows are required for statistical profiling."
        checks.append(DatasetVerificationCheck(name="Sample Size Sufficiency", status="fail", detail=detail))
        blocking_issues.append(detail)
        score -= 45.0
    elif clean_rows < _MIN_ROWS:
        detail = f"{raw_rows:,} raw rows deduplicated to {clean_rows} unique row(s); variance and outlier modeling will be limited."
        checks.append(DatasetVerificationCheck(name="Sample Size Sufficiency", status="warn", detail=detail))
        warnings.append(detail)
        score -= 15.0
    elif clean_rows < _RECOMMENDED_ROWS:
        detail = f"{clean_rows} usable rows (below {_RECOMMENDED_ROWS}-row benchmark); trends and outliers are directional."
        checks.append(DatasetVerificationCheck(name="Sample Size Sufficiency", status="warn", detail=detail))
        warnings.append(detail)
        score -= 6.0
    else:
        checks.append(
            DatasetVerificationCheck(
                name="Sample Size Sufficiency",
                status="pass",
                detail=f"{clean_rows:,} usable rows ready for distribution, quantile, and anomaly modeling.",
            )
        )

    # 2. Schema & column breadth check
    if clean_cols < _MIN_COLS:
        detail = f"Only {clean_cols} usable column(s) remain after hygiene checks; need at least {_MIN_COLS} columns."
        checks.append(DatasetVerificationCheck(name="Schema & Column Breadth", status="fail", detail=detail))
        blocking_issues.append(detail)
        score -= 35.0
    elif cleansing_report.columns_dropped > 0:
        detail = (
            f"{clean_cols} active columns ({cleansing_report.columns_dropped} empty/constant/mirror column(s) dropped)."
        )
        checks.append(DatasetVerificationCheck(name="Schema & Column Breadth", status="warn", detail=detail))
        warnings.append(detail)
        score -= 4.0
    else:
        checks.append(
            DatasetVerificationCheck(
                name="Schema & Column Breadth",
                status="pass",
                detail=f"{clean_cols} clean columns with valid headers and zero redundant fields.",
            )
        )

    # 3. Completeness & missingness check
    if raw_completeness < 30.0:
        detail = f"Critical missingness: raw dataset is only {raw_completeness:.1f}% complete."
        checks.append(DatasetVerificationCheck(name="Completeness & Missingness", status="fail", detail=detail))
        blocking_issues.append(detail)
        score -= 40.0
    elif raw_completeness < 95.0:
        detail = (
            f"Raw completeness {raw_completeness:.1f}% ({cleansing_report.missing_values_imputed} missing cell(s) "
            f"auto-imputed; post-cleansing integrity {cleansing_report.integrity_after:.1f}%)."
        )
        checks.append(DatasetVerificationCheck(name="Completeness & Missingness", status="warn", detail=detail))
        warnings.append(detail)
        score -= min(18.0, max(3.0, (95.0 - raw_completeness) * 0.4))
    else:
        checks.append(
            DatasetVerificationCheck(
                name="Completeness & Missingness",
                status="pass",
                detail=f"{raw_completeness:.1f}% raw completeness with clean numeric/categorical coverage.",
            )
        )

    # 4. Duplicate hygiene check
    dup_pct = (raw_dups / max(1, raw_rows)) * 100.0
    if raw_dups > 0:
        detail = f"Detected {raw_dups} duplicate row(s) ({dup_pct:.1f}%), automatically deduplicated."
        checks.append(DatasetVerificationCheck(name="Duplicate Hygiene", status="warn", detail=detail))
        warnings.append(detail)
        score -= min(12.0, max(2.0, dup_pct * 0.3))
    else:
        checks.append(
            DatasetVerificationCheck(
                name="Duplicate Hygiene",
                status="pass",
                detail="Zero duplicate rows detected.",
            )
        )

    # 5. Analytical metric coverage check
    if len(numeric_metrics) == 0:
        detail = "No non-ID quantitative metrics detected; cannot compute KPIs, distributions, or anomaly models."
        checks.append(DatasetVerificationCheck(name="Analytical Metric Coverage", status="fail", detail=detail))
        blocking_issues.append(detail)
        score -= 40.0
    elif len(numeric_metrics) == 1:
        detail = f"Single quantitative metric detected ({numeric_metrics[0]}); bivariate correlation analysis will be limited."
        checks.append(DatasetVerificationCheck(name="Analytical Metric Coverage", status="warn", detail=detail))
        warnings.append(detail)
        score -= 5.0
    else:
        checks.append(
            DatasetVerificationCheck(
                name="Analytical Metric Coverage",
                status="pass",
                detail=f"{len(numeric_metrics)} non-ID quantitative metrics verified: {', '.join(numeric_metrics[:4])}.",
            )
        )

    # 6. Segmentation / Time dimension check
    dim_total = len(categorical_dims) + len(temporal_dims)
    if dim_total == 0:
        detail = "No categorical or temporal dimensions detected; cohort comparison and trend breakdowns will be limited."
        checks.append(DatasetVerificationCheck(name="Cohort & Time Dimensions", status="warn", detail=detail))
        warnings.append(detail)
        score -= 5.0
    else:
        dim_names = categorical_dims[:3] + temporal_dims[:2]
        checks.append(
            DatasetVerificationCheck(
                name="Cohort & Time Dimensions",
                status="pass",
                detail=f"{dim_total} segmentation/time dimension(s) ready: {', '.join(dim_names)}.",
            )
        )

    readiness_score = round(max(0.0, min(100.0, score)), 1)

    if blocking_issues:
        status = "unusable"
        is_good = False
        summary = (
            f"'{dataset_name}' failed dataset verification ({len(blocking_issues)} blocking issue(s)): "
            f"{blocking_issues[0]}"
        )
    elif readiness_score >= 90.0 and not warnings:
        status = "perfect"
        is_good = True
        summary = (
            f"'{dataset_name}' verified as a perfect dataset ({readiness_score:.1f}/100): "
            f"{clean_rows:,} rows × {clean_cols} cols, {raw_completeness:.1f}% complete, ready for problem definition."
        )
    else:
        status = "good_with_warnings"
        is_good = True
        summary = (
            f"'{dataset_name}' verified as a good dataset ({readiness_score:.1f}/100) with {len(warnings)} minor note(s); "
            f"cleansing raised integrity to {cleansing_report.integrity_after:.1f}%."
        )

    verification = DatasetVerificationResult(
        status=status,
        is_good_dataset=is_good,
        readiness_score=readiness_score,
        summary=summary,
        row_count=raw_rows,
        column_count=raw_cols,
        cleaned_row_count=clean_rows,
        cleaned_column_count=clean_cols,
        completeness_pct=raw_completeness,
        duplicate_rows=raw_dups,
        numeric_metrics=numeric_metrics,
        categorical_dimensions=categorical_dims,
        temporal_dimensions=temporal_dims,
        excluded_id_columns=excluded_ids,
        checks=checks,
        warnings=warnings,
        blocking_issues=blocking_issues,
    )
    return verification, cleaned_df, cleansing_report, roles


def _infer_metric_role_and_agg(col_name: str, role_info: Dict[str, Any]) -> Tuple[str, str]:
    """Assign stakeholder metric role and safe aggregation rule from semantic column role."""
    semantic_role = role_info.get("role", "")
    is_rate = bool(role_info.get("is_rate")) or semantic_role == "rate"
    is_intensive = bool(role_info.get("is_intensive")) or semantic_role == "intensive_metric"
    if semantic_role in ("categorical_low", "categorical_medium", "categorical_high", "datetime"):
        return "Segment Dimension", "GROUP BY"
    if is_rate or _RISK_METRIC_RE.search(col_name):
        agg = "AVERAGE / P50 / P95 (never SUM)" if is_rate else "AVERAGE / P95"
        return "Guardrail", agg
    if is_intensive:
        return "Driver", "AVERAGE / Median / P95"
    if _GROWTH_METRIC_RE.search(col_name):
        return "North Star", "SUM & Cohort Share %"
    if _VOLUME_METRIC_RE.search(col_name):
        return "Driver", "SUM & Per-Cohort Mean"
    return "Driver", "SUM & Median/IQR"


def _compute_static_concentration(
    df: pd.DataFrame,
    cat_cols: List[str],
    num_cols: List[str],
) -> Optional[ConcentrationAnalysis]:
    """Compute Pareto Top-20% share & HHI concentration deterministically for problem framing."""
    if not cat_cols or not num_cols:
        return None
    cat_col = cat_cols[0]
    num_col = num_cols[0]
    if cat_col not in df.columns or num_col not in df.columns:
        return None
    grouped = df.groupby(cat_col, observed=True)[num_col].sum().sort_values(ascending=False)
    total_vol = float(grouped.sum())
    if total_vol <= 0 or len(grouped) == 0:
        return None
    shares = (grouped / total_vol) * 100.0
    hhi = float(round((shares ** 2).sum(), 1))
    top_n = max(1, int(math.ceil(len(grouped) * 0.2)))
    top_share = float(round((grouped.iloc[:top_n].sum() / total_vol) * 100.0, 1))
    classification = "Competitive & Diversified"
    if hhi >= 2500:
        classification = "Highly Concentrated (Elevated Single-Point Vulnerability)"
    elif hhi >= 1500:
        classification = "Moderately Concentrated"
    return ConcentrationAnalysis(
        dimension=cat_col,
        metric=num_col,
        top_20_percent_share=top_share,
        hhi_index=hhi,
        market_classification=classification,
        strategic_takeaway=(
            f"Top {top_n} {cat_col} cohort(s) control {top_share}% of {num_col} (HHI={hhi})."
        ),
    )


def _match_goal_columns(
    candidates: List[str],
    user_goal: str,
) -> List[str]:
    """Rank columns that explicitly match terms in user_goal ahead of defaults."""
    goal_l = (user_goal or "").lower().strip()
    if not goal_l:
        return []
    hits: List[str] = []
    for col in candidates:
        c_clean = col.lower().replace("_", " ").replace("-", " ")
        if col.lower() in goal_l or c_clean in goal_l:
            hits.append(col)
    return hits


def analyze_static_problem_context(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    verification: DatasetVerificationResult,
    user_goal: str = "",
    diagnostics: Optional[List[StatisticalDiagnostic]] = None,
    correlations: Optional[List[CorrelationInsight]] = None,
    segment_benchmarks: Optional[List[SegmentBenchmark]] = None,
    concentration: Optional[ConcentrationAnalysis] = None,
) -> Dict[str, Any]:
    """
    Static code-based problem understanding:
    Analyzes distributions, quantiles, skewness, Tukey outliers, ANOVA cohort variance,
    Pareto/HHI concentration, and bivariate correlations to surface concrete analytical problems.
    """
    numerics = list(verification.numeric_metrics)
    dims = list(verification.categorical_dimensions or verification.temporal_dimensions)

    goal_num_hits = _match_goal_columns(numerics, user_goal)
    goal_dim_hits = _match_goal_columns(dims, user_goal)

    growth_cols = [c for c in numerics if _GROWTH_METRIC_RE.search(c)]
    risk_cols = [
        c for c in numerics
        if _RISK_METRIC_RE.search(c) or roles.get(c, {}).get("is_rate") or roles.get(c, {}).get("role") == "rate"
    ]

    # If user explicitly named a non-risk metric in goal, prefer it as North Star; if they named a risk metric, elevate it as Guardrail
    goal_growth = [c for c in goal_num_hits if c not in risk_cols]
    goal_risk = [c for c in goal_num_hits if c in risk_cols]

    north_star = (
        goal_growth[0]
        if goal_growth
        else (growth_cols[0] if growth_cols else (goal_num_hits[0] if goal_num_hits else (numerics[0] if numerics else "Primary Metric")))
    )
    secondary_num = next((c for c in numerics if c != north_star and c not in risk_cols), None)
    guardrail = (
        goal_risk[0]
        if goal_risk
        else (risk_cols[0] if risk_cols else (secondary_num or (numerics[1] if len(numerics) > 1 else None)))
    )
    primary_dim = goal_dim_hits[0] if goal_dim_hits else (dims[0] if dims else None)
    secondary_dim = next((d for d in dims if d != primary_dim), None)

    ordered_numerics = [c for c in dict.fromkeys([north_star] + ([guardrail] if guardrail else []) + numerics) if c in df.columns]
    ordered_dims = [d for d in dict.fromkeys(([primary_dim] if primary_dim else []) + dims) if d in df.columns]

    resolved_diags = (
        diagnostics
        if diagnostics is not None
        else build_expert_statistical_diagnostics(df, ordered_numerics, roles)
    )
    resolved_corrs = (
        correlations
        if correlations is not None
        else compute_correlations_and_matrix(df, ordered_numerics, roles)[0]
    )
    resolved_benchmarks = (
        segment_benchmarks
        if segment_benchmarks is not None
        else compute_segment_benchmarks(df, ordered_dims, ordered_numerics, roles)
    )
    resolved_conc = (
        concentration
        if concentration is not None
        else _compute_static_concentration(df, ordered_dims, ordered_numerics)
    )

    diag_map = {d.metric_name: d for d in resolved_diags}
    metric_baselines: Dict[str, str] = {}
    static_signals: List[str] = []

    for col in ordered_numerics[:4]:
        info = roles.get(col, {})
        is_rate = bool(info.get("is_rate")) or info.get("role") == "rate"
        is_intensive = bool(info.get("is_intensive")) or info.get("role") == "intensive_metric" or is_rate
        unit_fmt = info.get("unit_format", "number")
        d = diag_map.get(col)
        series = df[col].dropna()
        if series.empty:
            continue
        max_scale = float(series.max()) if is_rate else None
        total_val = safe_float(series.sum())
        mean_val = d.mean if d else safe_float(series.mean(), decimals=2)
        med_val = d.median if d and d.median is not None else safe_float(series.median(), decimals=2)
        p95_val = d.p95 if d and d.p95 is not None else safe_float(series.quantile(0.95), decimals=2)
        skew_val = d.skewness if d else 0.0
        cv_val = d.cv if d else 0.0
        out_cnt = d.outlier_count if d and d.outlier_count is not None else 0

        if is_intensive:
            summary_str = (
                f"Mean={format_compact_value(mean_val, unit_fmt, max_scale)}, "
                f"Median={format_compact_value(med_val, unit_fmt, max_scale)}, "
                f"P95={format_compact_value(p95_val, unit_fmt, max_scale)}, Skew={skew_val:+.2f}"
            )
        else:
            summary_str = (
                f"Total={format_compact_value(total_val, unit_fmt)}, "
                f"Mean={format_compact_value(mean_val, unit_fmt)}, "
                f"Median={format_compact_value(med_val, unit_fmt)}, "
                f"P95={format_compact_value(p95_val, unit_fmt)}, Skew={skew_val:+.2f}"
            )
        if out_cnt > 0:
            summary_str += f", TukeyOutliers={out_cnt}"
        metric_baselines[col] = summary_str

        if col == north_star:
            static_signals.append(f"North Star '{col}' baseline: {summary_str}.")
        elif col == guardrail:
            static_signals.append(f"Guardrail '{col}' baseline: {summary_str}.")

        if abs(med_val) > 1e-9 and abs((mean_val - med_val) / abs(med_val)) >= 0.15:
            diff_pct = ((mean_val - med_val) / abs(med_val)) * 100.0
            static_signals.append(
                f"Skew Alert on '{col}': Mean diverges {diff_pct:+.0f}% from Median (CV={cv_val:.2f}), requiring median/IQR guardrails."
            )

    top_bench = resolved_benchmarks[0] if resolved_benchmarks else None
    if top_bench:
        spread_txt = f" ({top_bench.spread_ratio:.1f}x spread)" if top_bench.spread_ratio else ""
        static_signals.append(
            f"Cohort Gap (ANOVA η²={top_bench.eta_squared:.2f}): '{top_bench.top_segment}' leads vs '{top_bench.bottom_segment}' on {top_bench.metric} by {top_bench.dimension}{spread_txt}."
        )

    if resolved_conc and (resolved_conc.hhi_index >= 1500 or resolved_conc.top_20_percent_share >= 40.0):
        static_signals.append(
            f"Concentration Signal: Top 20% of {resolved_conc.dimension} drive {resolved_conc.top_20_percent_share}% of {resolved_conc.metric} (HHI={resolved_conc.hhi_index}, {resolved_conc.market_classification})."
        )

    top_corr = resolved_corrs[0] if resolved_corrs else None
    if top_corr and abs(top_corr.pearson_r) >= 0.40:
        static_signals.append(
            f"Driver Correlation: {top_corr.metric_a} vs {top_corr.metric_b} shows {top_corr.strength.lower()} {top_corr.direction.lower()} linkage (r={top_corr.pearson_r:+.2f})."
        )

    outlier_hits = [(d.metric_name, d.outlier_count, d.outlier_pct) for d in resolved_diags if (d.outlier_count or 0) > 0]
    if outlier_hits:
        top_out = outlier_hits[0]
        static_signals.append(
            f"Tail Anomaly Signal: {top_out[0]} has {top_out[1]} Tukey 1.5xIQR outlier(s) ({top_out[2]}% of rows)."
        )

    return {
        "north_star": north_star,
        "secondary_num": secondary_num,
        "guardrail": guardrail,
        "primary_dim": primary_dim,
        "secondary_dim": secondary_dim,
        "temporal_dim": verification.temporal_dimensions[0] if verification.temporal_dimensions else None,
        "ordered_numerics": ordered_numerics,
        "ordered_dims": ordered_dims,
        "metric_baselines": metric_baselines,
        "static_signals": static_signals[:6],
        "top_benchmark": top_bench,
        "concentration": resolved_conc,
        "top_corr": top_corr,
        "diag_map": diag_map,
    }


def _build_deterministic_problem_definition(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    verification: DatasetVerificationResult,
    dataset_name: str,
    user_goal: str = "",
    diagnostics: Optional[List[StatisticalDiagnostic]] = None,
    correlations: Optional[List[CorrelationInsight]] = None,
    segment_benchmarks: Optional[List[SegmentBenchmark]] = None,
    concentration: Optional[ConcentrationAnalysis] = None,
) -> ProblemDefinitionResult:
    """Build a quantified, code-understood problem definition and stakeholder alignment offline."""
    ctx = analyze_static_problem_context(
        df=df,
        roles=roles,
        verification=verification,
        user_goal=user_goal,
        diagnostics=diagnostics,
        correlations=correlations,
        segment_benchmarks=segment_benchmarks,
        concentration=concentration,
    )
    numerics = ctx["ordered_numerics"] or list(verification.numeric_metrics)
    dims = ctx["ordered_dims"] or list(verification.categorical_dimensions or verification.temporal_dimensions)

    north_star: str = ctx["north_star"]
    secondary_num: Optional[str] = ctx["secondary_num"]
    guardrail: Optional[str] = ctx["guardrail"]
    primary_dim: Optional[str] = ctx["primary_dim"]
    secondary_dim: Optional[str] = ctx["secondary_dim"]
    top_bench: Optional[SegmentBenchmark] = ctx["top_benchmark"]
    conc: Optional[ConcentrationAnalysis] = ctx["concentration"]
    top_corr: Optional[CorrelationInsight] = ctx["top_corr"]
    metric_baselines: Dict[str, str] = ctx["metric_baselines"]
    static_signals: List[str] = ctx["static_signals"]

    dim_phrase = (
        f"across {primary_dim}" + (f" and {secondary_dim}" if secondary_dim else "")
        if primary_dim
        else "across records"
    )
    guardrail_phrase = f" without elevating {guardrail}" if guardrail and guardrail != north_star else ""
    bench_evidence = (
        f" (closing the {top_bench.spread_ratio:.1f}x gap between '{top_bench.top_segment}' and '{top_bench.bottom_segment}')"
        if top_bench and top_bench.spread_ratio
        else ""
    )

    if user_goal.strip():
        core_question = (
            f"Given the goal '{user_goal.strip()}', which cohorts {dim_phrase} drive {north_star} performance"
            f"{guardrail_phrase}{bench_evidence}, and where do outliers signal structural risk?"
        )
    else:
        core_question = (
            f"Which cohorts {dim_phrase} drive sustainable {north_star} growth{guardrail_phrase}{bench_evidence}, "
            f"and which outliers or underperforming segments require immediate intervention?"
        )

    conc_clause = (
        f" while mitigating {conc.dimension} concentration (Top 20% = {conc.top_20_percent_share}%, HHI={conc.hhi_index})"
        if conc and conc.hhi_index >= 1500
        else ""
    )
    business_goal = (
        f"Maximize {north_star}"
        + (f" ({metric_baselines[north_star].split(',')[0]})" if north_star in metric_baselines else "")
        + (f" and {secondary_num}" if secondary_num and secondary_num != guardrail else "")
        + (f" while keeping {guardrail} within safe quantile guardrails" if guardrail and guardrail != north_star else "")
        + f" by reallocating focus across {primary_dim or 'high-performing cohorts'}{conc_clause}."
    )

    corr_clause = (
        f" and levering the {top_corr.metric_a}–{top_corr.metric_b} relationship (r={top_corr.pearson_r:+.2f})"
        if top_corr and abs(top_corr.pearson_r) >= 0.40
        else ""
    )
    decision_needed = (
        f"Prioritize budget, operational capacity, and remediation playbooks {dim_phrase} based on "
        f"{north_star} contribution, Pareto concentration, and IsolationForest tail anomalies{corr_clause}."
    )

    # Stakeholders grounded in dataset domain
    is_fintech = any(k in " ".join(numerics + dims).lower() for k in ("corridor", "chargeback", "settlement", "grossvolume", "netfee", "payment"))
    is_saas = any(k in " ".join(numerics + dims).lower() for k in ("churn", "arr", "mrr", "saas", "subscription"))

    if is_fintech:
        stakeholders = [
            StakeholderAlignment(
                stakeholder_role="Treasury & Payments Leadership",
                primary_concern=f"Scaling {north_star} and fee capture across top payment corridors.",
                target_metrics=[m for m in [north_star, secondary_num] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="Risk & Fraud Operations",
                primary_concern=f"Containing tail exposure on {guardrail or north_star} and settlement latency.",
                target_metrics=[m for m in [guardrail, primary_dim] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="Finance & BI Analytics",
                primary_concern="Reconciling corridor take-rates, Pareto concentration (HHI), and SLA compliance.",
                target_metrics=[m for m in numerics[:3] if m],
            ),
        ]
    elif is_saas:
        stakeholders = [
            StakeholderAlignment(
                stakeholder_role="Revenue & GTM Leadership (CRO)",
                primary_concern=f"Expanding {north_star} across high-yield {primary_dim or 'segments'} without regional over-concentration.",
                target_metrics=[m for m in [north_star, primary_dim] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="Customer Success & Retention",
                primary_concern=f"Reducing tail attrition on {guardrail or north_star} in lagging cohorts.",
                target_metrics=[m for m in [guardrail, secondary_dim] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="FP&A / Executive BI",
                primary_concern="Standardizing additive vs rate DAX definitions and margin drivers.",
                target_metrics=[m for m in numerics[:3] if m],
            ),
        ]
    else:
        stakeholders = [
            StakeholderAlignment(
                stakeholder_role="Executive Sponsor / Business Owner",
                primary_concern=f"Growing {north_star} and uncovering top cohort drivers {dim_phrase}.",
                target_metrics=[m for m in [north_star, primary_dim] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="Operations & Risk Lead",
                primary_concern=f"Monitoring {guardrail or north_star} variance and resolving outlier anomalies.",
                target_metrics=[m for m in [guardrail, secondary_num] if m],
            ),
            StakeholderAlignment(
                stakeholder_role="Analytics & BI Engineering",
                primary_concern="Ensuring statistically valid aggregations and decision-ready Power BI / Tableau KPIs.",
                target_metrics=numerics[:3],
            ),
        ]

    aligned_metrics: List[AlignedMetricSpec] = []
    for col in numerics[:4]:
        role_info = roles.get(col, {})
        m_role, agg = _infer_metric_role_and_agg(col, role_info)
        if col == north_star:
            m_role = "North Star"
        elif col == guardrail and col != north_star:
            m_role = "Guardrail"
        baseline_note = f" ({metric_baselines[col]})" if col in metric_baselines else ""
        aligned_metrics.append(
            AlignedMetricSpec(
                metric_name=col,
                role=m_role,  # type: ignore[arg-type]
                aggregation=agg,
                stakeholder_alignment=(
                    f"Primary {m_role.lower()} KPI tracked via {agg} across {primary_dim or 'all records'}{baseline_note}."
                ),
            )
        )
    for dim in dims[:2]:
        aligned_metrics.append(
            AlignedMetricSpec(
                metric_name=dim,
                role="Segment Dimension",
                aggregation="GROUP BY / ANOVA η²",
                stakeholder_alignment=f"Primary cohort slicing axis ({int(df[dim].nunique())} unique values) for variance & Pareto benchmarking.",
            )
        )

    guardrail_diag = ctx["diag_map"].get(guardrail) if guardrail else None
    guardrail_p95_txt = (
        f" (current P95={format_compact_value(guardrail_diag.p95, roles.get(guardrail, {}).get('unit_format', 'number'), float(df[guardrail].max()) if roles.get(guardrail, {}).get('is_rate') else None)})"
        if guardrail and guardrail_diag and guardrail_diag.p95 is not None and guardrail in df.columns
        else ""
    )

    clarifying_questions = [
        f"Should {north_star} optimization prioritize total volume expansion or margin efficiency per {primary_dim or 'record'}?",
        (
            f"What acceptable upper threshold should stakeholders enforce for {guardrail}{guardrail_p95_txt} before flagging a {primary_dim or 'cohort'} as high-risk?"
            if guardrail and guardrail != north_star
            else f"Which target threshold on {north_star} defines success for the top {primary_dim or 'cohorts'}?"
        ),
        (
            f"Are decisions evaluated at the {primary_dim} × {secondary_dim} intersection or rolled up by {primary_dim} alone?"
            if primary_dim and secondary_dim
            else f"Are outliers in {north_star} expected operational extremes or data anomalies requiring remediation?"
        ),
    ]

    recommended_prompt = (
        f"Define and execute a Principal analysis on '{dataset_name}' answering: {core_question} "
        f"Align KPIs around {', '.join(numerics[:3])}"
        + (f" segmented by {', '.join(dims[:2])}" if dims else "")
        + ", quantify Pareto/HHI concentration, isolate anomalies, and recommend prioritized ROI actions."
    )

    return ProblemDefinitionResult(
        core_question=core_question,
        business_goal=business_goal,
        decision_needed=decision_needed,
        stakeholders=stakeholders,
        aligned_metrics=aligned_metrics,
        clarifying_questions=clarifying_questions,
        recommended_analysis_prompt=recommended_prompt,
        static_signals=static_signals,
        synthesis_mode="static_only",
        ai_provider_used="static-code (deterministic)",
    )


build_static_problem_definition = _build_deterministic_problem_definition


def _merge_static_and_ai_problem_definition(
    static_def: ProblemDefinitionResult,
    ai_draft: _LLMProblemDefinitionDraft,
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    provider_label: str,
    user_goal: str = "",
) -> ProblemDefinitionResult:
    """
    Fuse deterministic static code understanding with AI synthesis:
    - Enforces valid column names and safe aggregation rules (never SUM rates/ratios).
    - Preserves critical static North Star / Guardrail / Segment dimensions if AI omitted them.
    - Retains empirical static_signals alongside AI-refined business framing.
    """
    valid_cols = set(df.columns)
    static_metric_map = {m.metric_name: m for m in static_def.aligned_metrics}

    merged_metrics: List[AlignedMetricSpec] = []
    seen_metrics: set[str] = set()

    for m in ai_draft.aligned_metrics:
        if m.metric_name not in valid_cols or m.metric_name in seen_metrics:
            continue
        seen_metrics.add(m.metric_name)
        role_info = roles.get(m.metric_name, {})
        static_role, safe_agg = _infer_metric_role_and_agg(m.metric_name, role_info)
        static_spec = static_metric_map.get(m.metric_name)

        is_rate_or_intensive = (
            bool(role_info.get("is_rate"))
            or bool(role_info.get("is_intensive"))
            or role_info.get("role") in ("rate", "intensive_metric")
        )
        # Never allow SUM on rate/ratio/intensive metrics; otherwise allow AI's refined agg unless empty
        if is_rate_or_intensive and ("sum" in (m.aggregation or "").lower() or not m.aggregation.strip()):
            enforced_agg = safe_agg
        else:
            enforced_agg = (m.aggregation or "").strip() or (static_spec.aggregation if static_spec else safe_agg)

        # Preserve critical North Star / Guardrail / Segment Dimension roles identified by static code
        enforced_role = static_spec.role if static_spec and static_spec.role in ("North Star", "Guardrail", "Segment Dimension") else (m.role or static_role)
        alignment_note = (m.stakeholder_alignment or "").strip() or (
            static_spec.stakeholder_alignment if static_spec else f"Aligned {enforced_role.lower()} metric."
        )
        merged_metrics.append(
            AlignedMetricSpec(
                metric_name=m.metric_name,
                role=enforced_role,  # type: ignore[arg-type]
                aggregation=enforced_agg,
                stakeholder_alignment=alignment_note,
            )
        )

    # Guarantee all essential static metrics (North Star, Guardrail, primary Segment Dimension) are represented
    for static_spec in static_def.aligned_metrics:
        if static_spec.metric_name not in seen_metrics and len(merged_metrics) < 6:
            merged_metrics.append(static_spec)
            seen_metrics.add(static_spec.metric_name)

    if not merged_metrics:
        merged_metrics = static_def.aligned_metrics

    merged_stakeholders: List[StakeholderAlignment] = []
    for st in ai_draft.stakeholders:
        if not (st.stakeholder_role or "").strip():
            continue
        clean_targets = [t for t in st.target_metrics if t in valid_cols]
        merged_stakeholders.append(
            StakeholderAlignment(
                stakeholder_role=st.stakeholder_role.strip(),
                primary_concern=(st.primary_concern or "").strip() or "Track aligned KPIs and risk thresholds.",
                target_metrics=clean_targets,
            )
        )
    if len(merged_stakeholders) < 2:
        merged_stakeholders = static_def.stakeholders

    core_question = ai_draft.core_question.strip() or static_def.core_question
    if user_goal.strip() and user_goal.strip().lower() not in core_question.lower():
        core_question = f"{core_question} (Mandate: {user_goal.strip()})"

    clarifying_qs = [q.strip() for q in ai_draft.clarifying_questions if q and q.strip()]
    for sq in static_def.clarifying_questions:
        if len(clarifying_qs) >= 4:
            break
        if sq not in clarifying_qs:
            clarifying_qs.append(sq)

    return ProblemDefinitionResult(
        core_question=core_question,
        business_goal=ai_draft.business_goal.strip() or static_def.business_goal,
        decision_needed=ai_draft.decision_needed.strip() or static_def.decision_needed,
        stakeholders=merged_stakeholders,
        aligned_metrics=merged_metrics,
        clarifying_questions=clarifying_qs[:4],
        recommended_analysis_prompt=ai_draft.recommended_analysis_prompt.strip() or static_def.recommended_analysis_prompt,
        static_signals=static_def.static_signals,
        synthesis_mode="static_and_ai",
        ai_provider_used=f"static-code + {provider_label}",
    )


async def define_problem_and_align_metrics(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    verification: DatasetVerificationResult,
    dataset_name: str = "dataset.csv",
    user_goal: str = "",
    diagnostics: Optional[List[StatisticalDiagnostic]] = None,
    correlations: Optional[List[CorrelationInsight]] = None,
    segment_benchmarks: Optional[List[SegmentBenchmark]] = None,
    concentration: Optional[ConcentrationAnalysis] = None,
    static_problem: Optional[ProblemDefinitionResult] = None,
    generate_fn: Optional[Callable[..., Any]] = None,
) -> ProblemDefinitionResult:
    """
    Stage 2 (Hybrid Static Code + AI):
    1. Computes static code problem understanding (quantiles, skew, ANOVA cohort spreads,
       Pareto/HHI concentration, correlations, North Star & Guardrail inference).
    2. Feeds BOTH the schema and static code findings into the AI to sharpen business
       context, stakeholder alignment, and strategic decisions.
    3. Reconciles AI output against static code guardrails (never SUM rate/ratio metrics).
    """
    if not verification.is_good_dataset:
        raise ValueError(
            "Dataset failed verification; fix blocking issues before defining the analytical problem."
        )

    static_def = static_problem or _build_deterministic_problem_definition(
        df=df,
        roles=roles,
        verification=verification,
        dataset_name=dataset_name,
        user_goal=user_goal,
        diagnostics=diagnostics,
        correlations=correlations,
        segment_benchmarks=segment_benchmarks,
        concentration=concentration,
    )

    configured = get_configured_providers()
    if not configured:
        return static_def

    schema_brief_lines = []
    for col in df.columns[:16]:
        role_info = roles.get(col, {})
        role_name = role_info.get("role", "unknown")
        unique_cnt = int(df[col].nunique())
        samples = df[col].dropna().unique()[:3].tolist()
        schema_brief_lines.append(f"- {col} (role={role_name}, unique={unique_cnt}, sample={samples})")

    static_signals_block = "\n".join(f"- {s}" for s in static_def.static_signals) or "- No strong statistical anomalies flagged."
    static_metrics_block = "\n".join(
        f"- {m.metric_name} [{m.role} | {m.aggregation}]: {m.stakeholder_alignment}"
        for m in static_def.aligned_metrics
    )

    sys_prompt = (
        "You are a Principal Data Strategist & Analytics Translator. "
        "The uploaded dataset passed structural verification and deterministic code analysis has already extracted "
        "empirical baselines, cohort spreads, concentration (HHI), and correlations. "
        "Use BOTH the dataset schema AND the static code findings to refine the core question, business goal, "
        "decision needed, realistic stakeholders, and aligned metrics. "
        "Use ONLY exact column names from the schema and NEVER recommend SUM() on rate/ratio/intensive columns."
    )
    user_prompt = (
        f"Dataset: {dataset_name} ({verification.cleaned_row_count} rows × {verification.cleaned_column_count} cols, "
        f"readiness={verification.readiness_score}/100, status={verification.status})\n"
        f"Optional User Context: {user_goal.strip() or 'None provided — synthesize from schema and empirical signals'}\n\n"
        f"Verified Columns & Semantic Roles:\n" + "\n".join(schema_brief_lines) + "\n\n"
        f"Static Code Empirical Signals:\n{static_signals_block}\n\n"
        f"Static Code Baseline Problem Framing:\n"
        f"- Core Question: {static_def.core_question}\n"
        f"- Business Goal: {static_def.business_goal}\n"
        f"- Decision Needed: {static_def.decision_needed}\n"
        f"- Baseline Aligned Metrics:\n{static_metrics_block}"
    )

    llm_caller = generate_fn or generate_structured
    try:
        draft = await llm_caller(
            response_model=_LLMProblemDefinitionDraft,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            provider=configured[0],
            max_retries=2,
            temperature=0.2,
            max_tokens=2048,
        )
        if not isinstance(draft, _LLMProblemDefinitionDraft):
            raise TypeError(f"Unexpected LLM problem definition payload type: {type(draft).__name__}")
        provider_label = format_provider_model_label(get_last_provider_used() or configured[0])
        return _merge_static_and_ai_problem_definition(
            static_def=static_def,
            ai_draft=draft,
            df=df,
            roles=roles,
            provider_label=provider_label,
            user_goal=user_goal,
        )
    except Exception as exc:
        logger.warning(f"LLM problem definition failed; using static code framing ({exc})")
        return static_def


async def verify_and_define_dataset(
    csv_text: str,
    dataset_name: str = "dataset.csv",
    user_goal: str = "",
) -> DatasetIntakeResponse:
    """
    Full 2-step intake gate:
      1. Verify dataset readiness.
      2. If good/perfect, define the problem & align key metrics with stakeholders.
    """
    verification, cleaned_df, _, roles = verify_dataset_readiness(csv_text, dataset_name=dataset_name)
    problem_def: Optional[ProblemDefinitionResult] = None
    if verification.is_good_dataset and cleaned_df is not None and roles is not None:
        problem_def = await define_problem_and_align_metrics(
            df=cleaned_df,
            roles=roles,
            verification=verification,
            dataset_name=dataset_name,
            user_goal=user_goal,
        )
    return DatasetIntakeResponse(
        dataset_name=dataset_name,
        verification=verification,
        problem_definition=problem_def,
    )
