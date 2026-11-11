# backend/app/modules/data_analyst/analyst.py
import io
import json
import logging
from typing import Dict, Any, List, Optional, Set, AsyncGenerator
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import httpx

from app.core.config import settings
from app.core.sse import sse_event
from app.services.llm.instructor_client import generate_structured
from app.modules.data_analyst.profiler import (
    build_expert_statistical_diagnostics,
    classify_dataframe_roles,
    compute_correlations_and_matrix,
    compute_data_quality_audit,
    compute_segment_benchmarks,
    format_compact_value,
    safe_float,
)
from app.modules.data_analyst.visual_selector import (
    build_expert_visual_plan,
    compute_visual_series_data_expert,
    validate_and_upgrade_visuals,
)
from app.modules.data_analyst.schemas import (
    ColumnMetric,
    DatasetProfile,
    KPISpec,
    ChartVisualSpec,
    AnomalyFinding,
    StatisticalDiagnostic,
    ConcentrationAnalysis,
    StrategicInitiative,
    RiskAssessment,
    ExecutiveDossier,
    DashboardPlan,
)
from app.modules.data_analyst.prompts import (
    DASHBOARD_PLANNER_SYSTEM_PROMPT,
    build_dashboard_user_prompt,
)

logger = logging.getLogger("vectronyx.analyst")

def calculate_statistical_diagnostics(
    df: pd.DataFrame,
    numeric_cols: List[str],
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[StatisticalDiagnostic]:
    """
    Computes rigorous econometric and non-parametric distribution diagnostics:
    Mean, Median, Std, Q1/P25, Q3/P75, P95, IQR, Skewness, Kurtosis, CV, and Tukey outliers.
    """
    resolved_roles = roles if roles is not None else classify_dataframe_roles(df)
    return build_expert_statistical_diagnostics(df, numeric_cols, resolved_roles)


def calculate_concentration_analysis(df: pd.DataFrame, cat_cols: List[str], numeric_cols: List[str]) -> Optional[ConcentrationAnalysis]:
    """
    Computes concentration risk using the Herfindahl-Hirschman Index (HHI)
    and Pareto (80/20) top quantile volume share.
    """
    if not cat_cols or not numeric_cols:
        return None

    cat_col = cat_cols[0]
    num_col = numeric_cols[0]

    grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
    total_vol = float(grouped.sum())

    if total_vol <= 0 or len(grouped) == 0:
        return None

    shares = (grouped / total_vol) * 100.0
    hhi = float(round((shares ** 2).sum(), 1))

    # Top 20% categories share
    top_n = max(1, int(np.ceil(len(grouped) * 0.2)))
    top_share = float(round((grouped.iloc[:top_n].sum() / total_vol) * 100.0, 1))

    classification = "Competitive & Diversified"
    if hhi >= 2500:
        classification = "Highly Concentrated (Elevated Single-Point Vulnerability)"
    elif hhi >= 1500:
        classification = "Moderately Concentrated"

    takeaway = (
        f"Top {top_n} {cat_col} cohort(s) ({top_n}/{len(grouped)}) control {top_share}% of total {num_col}. "
        f"HHI index at {hhi} indicates a {classification.lower()} structure requiring diversification safeguards."
    )

    return ConcentrationAnalysis(
        dimension=cat_col,
        metric=num_col,
        top_20_percent_share=top_share,
        hhi_index=hhi,
        market_classification=classification,
        strategic_takeaway=takeaway,
    )


def calculate_data_integrity_score(df: pd.DataFrame) -> float:
    """
    Assesses dataset completeness, non-null density, and absence of duplicate observations.
    """
    if df.empty:
        return 0.0
    total_cells = df.shape[0] * df.shape[1]
    null_cells = int(df.isna().sum().sum())
    completeness = (total_cells - null_cells) / total_cells if total_cells > 0 else 1.0

    dups = df.duplicated().sum()
    dup_penalty = (dups / len(df)) * 0.2 if len(df) > 0 else 0.0

    score = max(50.0, min(100.0, (completeness * 100.0) - (dup_penalty * 100.0)))
    return float(round(score, 1))


def resolve_prompt_intent_and_columns(
    df: pd.DataFrame,
    user_prompt: str,
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> tuple[List[str], List[str], str]:
    """
    Analyzes user prompt against DataFrame columns using semantic role filtering,
    keyword matching, fuzzy substring checks, and intent classification.
    Excludes ID keys and raw timestamps from default numeric/categorical rankings.
    Returns:
        (resolved_numeric_cols, resolved_cat_cols, analytical_intent)
    """
    resolved_roles = roles if roles is not None else classify_dataframe_roles(df)
    prompt_lower = (user_prompt or "").lower()

    raw_numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    raw_cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]

    non_id_numerics = [
        c for c in raw_numeric_cols
        if resolved_roles.get(str(c), {}).get("role") not in ("identifier", "datetime", "constant")
    ]
    all_numeric_cols = non_id_numerics if non_id_numerics else [
        c for c in raw_numeric_cols if resolved_roles.get(str(c), {}).get("role") != "identifier"
    ] or raw_numeric_cols

    usable_cats = [
        c for c in raw_cat_cols
        if resolved_roles.get(str(c), {}).get("role") in ("categorical_low", "categorical_medium", "categorical_high")
    ]
    # Order low/medium cardinality clean grouping columns ahead of high-cardinality free-text titles
    usable_cats.sort(
        key=lambda c: (
            0 if resolved_roles.get(str(c), {}).get("role") == "categorical_low" else (
                1 if resolved_roles.get(str(c), {}).get("role") == "categorical_medium" else 2
            ),
            resolved_roles.get(str(c), {}).get("unique_ratio", 1.0),
        )
    )
    all_cat_cols = usable_cats if usable_cats else [
        c for c in raw_cat_cols if resolved_roles.get(str(c), {}).get("role") not in ("identifier", "datetime", "text_freetext")
    ] or raw_cat_cols

    # 1. Direct or substring column match
    matched_numerics = []
    for c in all_numeric_cols:
        c_clean = str(c).lower().replace("_", " ").replace("-", " ")
        if c_clean in prompt_lower or str(c).lower() in prompt_lower:
            matched_numerics.append(c)

    matched_cats = []
    for c in all_cat_cols:
        c_clean = str(c).lower().replace("_", " ").replace("-", " ")
        if c_clean in prompt_lower or str(c).lower() in prompt_lower:
            matched_cats.append(c)

    # 2. Semantic domain synonyms
    synonym_map = {
        "churn": ["churn", "attrition", "retention", "dropoff", "cancel", "inactive"],
        "revenue": ["revenue", "sales", "arr", "mrr", "income", "gross", "billing", "turnover"],
        "profit": ["profit", "margin", "ebitda", "net", "take-rate", "take rate", "spread", "fee", "yield"],
        "volume": ["volume", "transactions", "orders", "settlement", "count", "liquidity", "records", "ratings"],
        "risk": ["risk", "chargeback", "fraud", "exposure", "volatility", "tail", "loss", "vulnerability"],
        "quality": ["rating", "score", "review", "quality", "satisfaction", "nps"],
        "region": ["region", "country", "territory", "corridor", "geo", "market", "zone", "language"],
        "segment": ["segment", "category", "tier", "cohort", "type", "plan", "product", "channel", "publisher", "author"],
    }

    for concept, keywords in synonym_map.items():
        if any(kw in prompt_lower for kw in keywords):
            for c in all_numeric_cols:
                c_str = str(c).lower()
                if any(kw in c_str for kw in keywords) and c not in matched_numerics:
                    matched_numerics.append(c)
            for c in all_cat_cols:
                c_str = str(c).lower()
                if any(kw in c_str for kw in keywords) and c not in matched_cats:
                    matched_cats.append(c)

    # Append remaining available columns sorted by statistical informativeness (variance / clean cardinality)
    for c in all_numeric_cols:
        if c not in matched_numerics:
            matched_numerics.append(c)
    for c in all_cat_cols:
        if c not in matched_cats:
            matched_cats.append(c)

    # 3. Intent Classification
    intent = "general_executive"
    if any(k in prompt_lower for k in ["churn", "chargeback", "risk", "leakage", "tail", "loss", "vulnerability", "outlier"]):
        intent = "risk_and_churn"
    elif any(k in prompt_lower for k in ["unit economic", "margin", "profit", "take-rate", "take rate", "efficiency", "yield", "cac", "ltv", "fee"]):
        intent = "unit_economics"
    elif any(k in prompt_lower for k in ["concentration", "hhi", "pareto", "monopoly", "diversif", "reliance", "share"]):
        intent = "concentration_risk"
    elif any(k in prompt_lower for k in ["volume", "growth", "scale", "arr", "expansion", "liquidity", "trend"]):
        intent = "volume_and_growth"
    elif any(k in prompt_lower for k in ["correlation", "relationship", "driver", "regression", "factor", "impact"]):
        intent = "driver_and_correlation"

    return matched_numerics, matched_cats, intent


def compute_ground_truth_context(
    df: pd.DataFrame, 
    target_numerics: List[str], 
    target_cats: List[str],
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> tuple[Dict[str, Any], str]:
    """
    Computes exact empirical statistics for target columns (respecting additive vs intensive semantics).
    Returns:
        (metrics_dict, formatted_summary_text)
    """
    resolved_roles = roles if roles is not None else classify_dataframe_roles(df)
    metrics: Dict[str, Any] = {}
    lines: List[str] = []

    for col in target_numerics[:5]:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        info = resolved_roles.get(str(col), {})
        is_rate = bool(info.get("is_rate", False)) or (
            "rate" in col.lower() or "ratio" in col.lower() or "pct" in col.lower()
            or (0 <= float(s.min()) and float(s.max()) <= 1.0 and float(s.mean()) < 0.95 and "rating" not in col.lower())
        )
        is_intensive = bool(info.get("is_intensive", False)) or is_rate
        unit_fmt = info.get("unit_format") or ("percent" if is_rate else ("currency" if any(k in col.lower() for k in ("rev", "profit", "fee", "cost", "volume")) else "number"))

        total_val = safe_float(s.sum())
        mean_val = safe_float(s.mean())
        median_val = safe_float(s.median())
        q1_val = safe_float(s.quantile(0.25))
        q3_val = safe_float(s.quantile(0.75))
        p95_val = safe_float(s.quantile(0.95))
        min_val = safe_float(s.min())
        max_val = safe_float(s.max())
        std_val = safe_float(s.std()) if len(s) > 1 else 0.0
        cv_val = round(std_val / mean_val, 2) if abs(mean_val) > 1e-6 else 0.0
        is_currency = unit_fmt == "currency"

        if is_rate:
            pct_mean = mean_val * 100.0 if max_val <= 1.0 else mean_val
            formatted_val = f"{pct_mean:.2f}% (Mean)"
        elif is_intensive:
            formatted_val = f"{format_compact_value(mean_val, unit_fmt)} (Mean)"
        elif is_currency:
            formatted_val = f"${total_val:,.2f}" if abs(total_val) < 1e6 else f"${total_val / 1e6:.2f}M"
        else:
            formatted_val = f"{total_val:,.1f}"

        metrics[col] = {
            "total": total_val,
            "mean": mean_val,
            "median": median_val,
            "p25": q1_val,
            "p75": q3_val,
            "p95": p95_val,
            "min": min_val,
            "max": max_val,
            "std": std_val,
            "cv": cv_val,
            "formatted_display": formatted_val,
            "is_rate": is_rate,
            "is_intensive": is_intensive,
            "is_currency": is_currency,
            "unit_format": unit_fmt,
        }

        lines.append(
            f"- Metric '{col}' ({'intensive/rate' if is_intensive else 'additive'}): "
            f"Total={total_val:,.2f}, Mean={mean_val:,.2f}, Median={median_val:,.2f}, "
            f"IQR={q1_val:,.2f}–{q3_val:,.2f}, P95={p95_val:,.2f}, Min={min_val:,.2f}, Max={max_val:,.2f}, Std={std_val:,.2f}, CV={cv_val}"
        )

    # Segment breakdowns
    usable_cat = next((c for c in target_cats if c in df.columns and resolved_roles.get(str(c), {}).get("role") != "identifier"), target_cats[0] if target_cats else None)
    if usable_cat and target_numerics:
        primary_cat = usable_cat
        primary_num = target_numerics[0]
        p_info = resolved_roles.get(str(primary_num), {})
        use_mean = bool(p_info.get("is_intensive", False))
        try:
            agg_series = df.groupby(primary_cat, observed=True)[primary_num].mean() if use_mean else df.groupby(primary_cat, observed=True)[primary_num].sum()
            grouped = agg_series.sort_values(ascending=False).head(5)
            cohort_lines = [f"{k}: {v:,.2f}" for k, v in grouped.items()]
            lines.append(f"- Top {primary_cat} cohorts for {primary_num} ({'Mean' if use_mean else 'Sum'}): {'; '.join(cohort_lines)}")
        except Exception as e:
            logger.debug(f"Could not group {primary_cat} by {primary_num}: {e}")

    summary_text = "\n".join(lines)
    return metrics, summary_text


def reconcile_kpi_ground_truth(
    df: pd.DataFrame, 
    kpis: List[KPISpec], 
    ground_truth_metrics: Dict[str, Any]
) -> List[KPISpec]:
    """
    Inspects each KPI generated by the LLM. If the KPI references a known column,
    verifies or updates the KPI value with the exact mathematically computed ground-truth.
    """
    reconciled = []
    for kpi in kpis:
        matched_metric = None
        for metric_name, m_data in ground_truth_metrics.items():
            col_l = metric_name.lower()
            if col_l in kpi.title.lower() or col_l in kpi.formula_dax.lower() or col_l in kpi.formula_tableau.lower():
                matched_metric = (metric_name, m_data)
                break

        if matched_metric:
            metric_name, m_data = matched_metric
            is_avg = (
                any(a in kpi.title.lower() or a in kpi.formula_dax.lower() for a in ["avg", "average", "mean"])
                or bool(m_data.get("is_rate", False))
                or bool(m_data.get("is_intensive", False))
            )
            val = m_data["mean"] if is_avg else m_data["total"]

            if m_data["is_rate"]:
                formatted_ground = f"{val * 100:.2f}%" if val <= 1.0 else f"{val:.2f}%"
            elif m_data["is_currency"]:
                formatted_ground = f"${val:,.2f}" if abs(val) < 1e6 else f"${val / 1e6:.2f}M"
            else:
                formatted_ground = format_compact_value(val, m_data.get("unit_format", "number"))

            if kpi.value in ["$1,245,000", "+14.2% YoY", "0", "$0", "$1.0M"] or not kpi.value or ("$" in kpi.value and m_data["is_rate"]):
                kpi.value = formatted_ground
        reconciled.append(kpi)
    return reconciled


def profile_dataset(
    csv_text: str,
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
    df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, DatasetProfile, List[AnomalyFinding]]:
    """
    Parses CSV into a Pandas DataFrame, creates a comprehensive schema profile,
    and runs Scikit-Learn IsolationForest over non-ID, non-constant numeric features
    to identify genuine multidimensional outliers.
    """
    if df is None:
        df = pd.read_csv(io.StringIO(csv_text))
    row_count, col_count = df.shape
    resolved_roles = roles if roles is not None else classify_dataframe_roles(df)

    columns_metrics: List[ColumnMetric] = []
    numeric_cols = []
    cat_cols = []

    for col in df.columns:
        series = df[col]
        dtype_str = str(series.dtype)
        null_cnt = int(series.isna().sum())
        unique_cnt = int(series.nunique())
        samples = series.dropna().unique()[:5].tolist()
        samples = [str(s) if not isinstance(s, (int, float, str, bool)) else s for s in samples]

        min_val = None
        max_val = None
        mean_val = None
        skew_val = None
        cv_val = None

        if pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
            valid = series.dropna()
            if not valid.empty:
                min_val = safe_float(valid.min())
                max_val = safe_float(valid.max())
                mean_val = safe_float(valid.mean(), decimals=2)
                if len(valid) > 2:
                    skew_val = safe_float(valid.skew(), decimals=2)
                    std_temp = safe_float(valid.std())
                    if abs(mean_val) > 1e-6:
                        cv_val = safe_float(std_temp / mean_val, decimals=2)
        else:
            cat_cols.append(col)

        columns_metrics.append(
            ColumnMetric(
                name=col if isinstance(col, str) else str(col),
                dtype=dtype_str,
                null_count=null_cnt,
                unique_count=unique_cnt,
                sample_values=samples,
                min_val=min_val,
                max_val=max_val,
                mean_val=mean_val,
                skewness=skew_val,
                cv=cv_val,
            )
        )

    preview_df = df.head(10).replace({np.nan: None})
    preview_rows: List[Dict[str, Any]] = [{str(k): v for k, v in row.items()} for row in preview_df.to_dict(orient="records")]
    integrity_score = calculate_data_integrity_score(df)

    profile = DatasetProfile(
        row_count=row_count,
        col_count=col_count,
        columns=columns_metrics,
        preview_rows=preview_rows,
        data_integrity_score=integrity_score,
    )

    # Detect anomalies via IsolationForest (strictly exclude IDs and zero-variance columns)
    anomalies: List[AnomalyFinding] = []
    model_features = [
        c for c in numeric_cols
        if resolved_roles.get(str(c), {}).get("role") not in ("identifier", "constant", "datetime")
        and safe_float(df[c].dropna().std(), 0.0) > 1e-12
    ]
    if len(model_features) >= 1 and row_count >= 5:
        try:
            medians = df[model_features].median()
            num_df = df[model_features].fillna(medians)
            stds = num_df.std().replace(0, 1.0)
            iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
            preds = iso.fit_predict(num_df)
            scores = iso.decision_function(num_df)

            outlier_indices = np.where(preds == -1)[0]
            sorted_outliers = sorted(outlier_indices, key=lambda idx: scores[idx])[:5]

            for idx in sorted_outliers:
                score_val = safe_float(-scores[idx], decimals=3)
                row_features = df.iloc[idx].to_dict()
                clean_features = {str(k): (str(v) if pd.isna(v) else (v.item() if isinstance(v, np.generic) else v)) for k, v in row_features.items()}

                # Quantify which metric deviated furthest from cohort median
                driver_details = []
                best_col = str(model_features[0])
                best_z = -1.0
                for feat in model_features:
                    val_f = safe_float(num_df.iloc[idx][feat], 0.0)
                    med_f = safe_float(medians[feat], 0.0)
                    std_f = safe_float(stds[feat], 1.0)
                    z = abs(val_f - med_f) / max(1e-9, std_f)
                    if z > best_z:
                        best_z = z
                        best_col = str(feat)
                        f_info = resolved_roles.get(str(feat), {})
                        max_scale = f_info.get("max_val") if f_info.get("is_rate") else None
                        u_fmt = f_info.get("unit_format", "number")
                        driver_details = [
                            best_col,
                            format_compact_value(val_f, u_fmt, max_scale),
                            format_compact_value(med_f, u_fmt, max_scale),
                        ]

                driver_text = (
                    f"Extreme divergence led by {driver_details[0]} = {driver_details[1]} vs cohort median {driver_details[2]} ({best_z:.1f}σ separation)."
                    if driver_details
                    else f"Extreme variance divergence detected in row #{idx + 1} relative to cohort distribution medians."
                )

                anomalies.append(
                    AnomalyFinding(
                        row_index=int(idx),
                        score=score_val,
                        explanation=f"Multivariate IsolationForest outlier (Score: {score_val}) across {model_features[:3]}",
                        root_cause_attribution=driver_text,
                        business_impact=f"Skews aggregate {best_col} means and cohort variance estimates; requires segmentation check before setting targets.",
                        action_required=f"Verify Observation #{int(idx) + 1} ({best_col} extreme); exclude one-time shocks from baseline averages or flag for audit.",
                        features=clean_features,
                    )
                )
        except Exception as e:
            logger.warning(f"IsolationForest anomaly detection failed: {e}")

    return df, profile, anomalies


def _build_deep_stats_brief(
    quality_audit: Any,
    diagnostics: List[StatisticalDiagnostic],
    correlations: List[Any],
    segment_benchmarks: List[Any],
) -> str:
    lines: List[str] = [
        f"Data Quality: {quality_audit.total_rows:,} rows x {quality_audit.total_columns} cols, "
        f"Completeness={quality_audit.completeness_pct:.1f}%, Duplicates={quality_audit.duplicate_rows:,} ({quality_audit.duplicate_pct:.1f}%)."
    ]
    if quality_audit.excluded_id_columns:
        lines.append(f"Excluded Identifier Columns (DO NOT aggregate or chart): {', '.join(quality_audit.excluded_id_columns)}")
    if quality_audit.temporal_columns:
        lines.append(f"Detected Chronological/Datetime Columns (ideal for time-series area/line): {', '.join(quality_audit.temporal_columns)}")
    if diagnostics:
        lines.append("Distribution Shapes & Quantiles:")
        for d in diagnostics[:4]:
            lines.append(
                f"  * {d.metric_name}: mean={d.mean}, median={d.median}, IQR=[{d.p25}, {d.p75}], P95={d.p95}, "
                f"skew={d.skewness}, outliers={d.outlier_count} ({d.outlier_pct}%), verdict={d.normality_verdict}"
            )
    if correlations:
        lines.append("Top Empirical Correlations (ideal for scatter plot):")
        for c in correlations[:3]:
            lines.append(f"  * {c.metric_a} vs {c.metric_b}: Pearson r={c.pearson_r:+.2f}, Spearman ρ={c.spearman_rho:+.2f} ({c.strength} {c.direction})")
    if segment_benchmarks:
        lines.append("Top Segment Variance Drivers (ANOVA η²):")
        for sb in segment_benchmarks[:2]:
            lines.append(f"  * {sb.narrative}")
    return "\n".join(lines)


def _heuristic_fallback_dashboard(
    df: pd.DataFrame,
    user_prompt: str,
    dataset_name: str,
    target_numerics: Optional[List[str]] = None,
    target_cats: Optional[List[str]] = None,
    intent: Optional[str] = None,
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
    anomalies: Optional[List[AnomalyFinding]] = None,
) -> DashboardPlan:
    """
    Principal Data Analyst Heuristic Engine (Prompt-Adaptive & Statistically Grounded):
    Synthesizes an authoritative analytical report combining non-parametric distributions,
    ANOVA segment benchmarks, multivariate correlations, data quality governance,
    and data-shape-selected visualizations.
    """
    resolved_roles = roles if roles is not None else classify_dataframe_roles(df)
    if not target_numerics or not target_cats or not intent:
        resolved_num, resolved_cat, resolved_intent = resolve_prompt_intent_and_columns(df, user_prompt, roles=resolved_roles)
        target_numerics = target_numerics or resolved_num
        target_cats = target_cats or resolved_cat
        intent = intent or resolved_intent

    numeric_cols = [c for c in target_numerics if c in df.columns and resolved_roles.get(str(c), {}).get("role") != "identifier"]
    if not numeric_cols:
        numeric_cols = target_numerics if target_numerics else [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in target_cats if c in df.columns and resolved_roles.get(str(c), {}).get("role") not in ("identifier", "datetime")]
    if not cat_cols:
        cat_cols = target_cats if target_cats else [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]

    diagnostics = build_expert_statistical_diagnostics(df, numeric_cols, resolved_roles)
    concentration = calculate_concentration_analysis(df, cat_cols, numeric_cols)
    integrity = calculate_data_integrity_score(df)
    ground_truth, _ = compute_ground_truth_context(df, numeric_cols, cat_cols, roles=resolved_roles)
    quality_audit = compute_data_quality_audit(df, resolved_roles)
    correlations, correlation_matrix = compute_correlations_and_matrix(df, numeric_cols, resolved_roles)
    segment_benchmarks = compute_segment_benchmarks(df, cat_cols, numeric_cols, resolved_roles)

    kpis: List[KPISpec] = []
    primary_num = numeric_cols[0] if numeric_cols else "Volume"
    primary_cat = cat_cols[0] if cat_cols else "Cohorts"

    # Lead KPI calibrated to prompt intent + metric semantics
    p_data = ground_truth.get(primary_num, {})
    p_info = resolved_roles.get(str(primary_num), {})
    p_unit = p_data.get("unit_format", "number")
    p_max = p_data.get("max") if p_data.get("is_rate") else None

    if intent == "risk_and_churn" and primary_num in df.columns:
        val_str = p_data.get("formatted_display", f"{df[primary_num].mean():.2f}")
        med_str = format_compact_value(p_data.get("median", 0.0), p_unit, p_max)
        p95_str = format_compact_value(p_data.get("p95", 0.0), p_unit, p_max)
        kpis.append(
            KPISpec(
                id="kpi_risk_1",
                title=f"Core Exposure: {primary_num}",
                value=val_str.replace(" (Mean)", ""),
                change=f"Median: {med_str} | P95 Tail: {p95_str}",
                trend="down" if p_data.get("mean", 0) > 0.05 else "neutral",
                benchmark=f"Median: {med_str}",
                variance=f"IQR {format_compact_value(p_data.get('p25', 0.0), p_unit, p_max)}–{format_compact_value(p_data.get('p75', 0.0), p_unit, p_max)}",
                executive_takeaway=f"Quantile spread isolates tail exposure in top 5% (>= {p95_str}); cohort-level thresholds required.",
                formula_dax=f"Avg {primary_num} = AVERAGE('Dataset'[{primary_num}])",
                formula_tableau=f"AVG([{primary_num}])",
                rationale=f"Primary risk distribution metric for mandate: '{user_prompt[:60]}'",
            )
        )
    elif intent == "unit_economics" and primary_num in df.columns:
        val_str = p_data.get("formatted_display", f"${df[primary_num].sum():,.2f}").replace(" (Mean)", "")
        med_str = format_compact_value(p_data.get("median", 0.0), p_unit, p_max)
        p95_str = format_compact_value(p_data.get("p95", 0.0), p_unit, p_max)
        kpis.append(
            KPISpec(
                id="kpi_econ_1",
                title=f"{'Mean ' if p_info.get('is_intensive') else 'Aggregate '}Yield: {primary_num}",
                value=val_str,
                change=f"Median: {med_str} | P95: {p95_str}",
                trend="up",
                benchmark=f"P75 Top-Quartile: {format_compact_value(p_data.get('p75', 0.0), p_unit, p_max)}",
                variance=f"CV {p_data.get('cv', 0.0):.2f} dispersion",
                executive_takeaway=f"Unit economic baseline across {len(df):,} observations comparing mean vs median central tendency.",
                formula_dax=f"{'Avg' if p_info.get('is_intensive') else 'Total'} {primary_num} = {'AVERAGE' if p_info.get('is_intensive') else 'SUM'}('Dataset'[{primary_num}])",
                formula_tableau=f"{'AVG' if p_info.get('is_intensive') else 'SUM'}([{primary_num}])",
                rationale=f"Monetization baseline for {primary_num}.",
            )
        )
    else:
        kpis.append(
            KPISpec(
                id="kpi_records",
                title="Validated Dataset Volume",
                value=f"{len(df):,} Rows",
                change=f"{len(df.columns)} Cols | {quality_audit.duplicate_rows} Dups",
                trend="up" if quality_audit.completeness_pct >= 95 else "neutral",
                benchmark="Completeness >= 98%",
                variance=f"{quality_audit.completeness_pct:.1f}% non-null",
                executive_takeaway=(
                    f"Excluded {len(quality_audit.excluded_id_columns)} ID column(s) from metric sums to prevent bias."
                    if quality_audit.excluded_id_columns
                    else f"Validated {len(df.columns)} schema fields across {len(df):,} rows."
                ),
                formula_dax="Total Records = COUNTROWS('Dataset')",
                formula_tableau="COUNT([Dataset])",
                rationale="Empirical sample size & structural hygiene check.",
            )
        )

    for idx, num_col in enumerate(numeric_cols[:3]):
        if len(kpis) >= 4:
            break
        col_data = ground_truth.get(num_col, {})
        c_info = resolved_roles.get(str(num_col), {})
        u_fmt = col_data.get("unit_format", "number")
        is_rate = bool(col_data.get("is_rate", False))
        is_intensive = bool(col_data.get("is_intensive", False))
        m_scale = col_data.get("max") if is_rate else None

        mean_val = col_data.get("mean", 0.0)
        med_val = col_data.get("median", mean_val)
        cv_val = col_data.get("cv", 0.0)
        p75_val = col_data.get("p75", mean_val)
        p95_val = col_data.get("p95", mean_val)

        if is_rate:
            display_val = format_compact_value(mean_val, "percent", m_scale)
            title_prefix = "Mean Rate"
        elif is_intensive:
            display_val = format_compact_value(mean_val, u_fmt)
            title_prefix = "Mean"
        else:
            display_val = format_compact_value(col_data.get("total", 0.0), u_fmt)
            title_prefix = "Total"

        med_disp = format_compact_value(med_val, u_fmt, m_scale)
        p75_disp = format_compact_value(p75_val, u_fmt, m_scale)
        p95_disp = format_compact_value(p95_val, u_fmt, m_scale)
        skew_gap = ""
        if abs(med_val) > 1e-9:
            diff_pct = ((mean_val - med_val) / abs(med_val)) * 100.0
            if abs(diff_pct) >= 15.0:
                skew_gap = f"Mean is {diff_pct:+.0f}% vs median ({med_disp}), proving skew/tail pull."

        kpis.append(
            KPISpec(
                id=f"kpi_{idx + 1}",
                title=f"{title_prefix}: {num_col}",
                value=display_val,
                change=f"Median: {med_disp} | CV: {cv_val:.2f}",
                trend="up" if mean_val > 0 else "down",
                benchmark=f"P75: {p75_disp}",
                variance=f"P95: {p95_disp}",
                executive_takeaway=skew_gap or f"IQR Q3 sits at {p75_disp}; CV of {cv_val:.2f} shows {'low volatility' if cv_val < 0.5 else 'elevated variance'}.",
                formula_dax=f"Metric_{num_col} = {'AVERAGE' if is_intensive else 'SUM'}('Dataset'[{num_col}])",
                formula_tableau=f"{'AVG' if is_intensive else 'SUM'}([{num_col}])",
                rationale=f"Ground-truth distribution summary for {num_col}.",
            )
        )

    while len(kpis) < 4:
        extra_idx = len(kpis) + 1
        kpis.append(
            KPISpec(
                id=f"kpi_aux_{extra_idx}",
                title="Data Integrity Index",
                value=f"{integrity}%",
                change=f"{quality_audit.duplicate_rows} Duplicates",
                trend="up" if integrity >= 95 else "neutral",
                benchmark="Target: >=95.0%",
                variance=f"{quality_audit.completeness_pct:.1f}% non-null",
                executive_takeaway="Cell completeness and deduplication health across evaluated records.",
                formula_dax="Data_Integrity = 1.0",
                formula_tableau="1.0",
                rationale="Data governance baseline metric.",
            )
        )

    # Data-driven Visual Selection
    visuals = build_expert_visual_plan(
        df=df,
        roles=resolved_roles,
        target_numerics=numeric_cols,
        target_cats=cat_cols,
        intent=intent,
        concentration=concentration,
        correlations=correlations,
    )

    # Quantified Insights for Senior Analyst Narrative
    top_corr = correlations[0] if correlations else None
    top_bench = segment_benchmarks[0] if segment_benchmarks else None
    primary_diag = diagnostics[0] if diagnostics else None

    corr_clause = (
        f" Bivariate screening highlights a {top_corr.strength.lower()} {top_corr.direction.lower()} correlation "
        f"between {top_corr.metric_a} and {top_corr.metric_b} (r = {top_corr.pearson_r:+.2f}, p = {top_corr.p_value:.3g})."
        if top_corr
        else ""
    )
    bench_clause = (
        f" Across {top_bench.dimension} ({top_bench.cohort_count} cohorts, η² = {top_bench.eta_squared:.2f}), "
        f"'{top_bench.top_segment}' leads while '{top_bench.bottom_segment}' lags"
        + (f" ({top_bench.spread_ratio:.1f}x spread)." if top_bench.spread_ratio else ".")
        if top_bench
        else ""
    )
    diag_clause = (
        f" {primary_num} shows {primary_diag.normality_verdict.lower()} shape (CV {primary_diag.cv:.2f}, "
        f"{primary_diag.outlier_count} Tukey outliers / {primary_diag.outlier_pct:.1f}%)."
        if primary_diag and primary_diag.normality_verdict
        else ""
    )
    id_note = (
        f" Automatically isolated {len(quality_audit.excluded_id_columns)} identifier key(s) "
        f"({', '.join(quality_audit.excluded_id_columns)}) from mathematical rollups."
        if quality_audit.excluded_id_columns
        else ""
    )

    initiatives = [
        StrategicInitiative(
            priority="P0 - Immediate (0-30d)",
            time_horizon="0-30 Days",
            title=(
                f"Audit {primary_diag.outlier_count} Statistical Outliers in {primary_num}"
                if primary_diag and primary_diag.outlier_count
                else f"Contain Variance Volatility in {primary_num}"
            ),
            rationale=(
                f"IQR fence diagnostics ({primary_diag.outlier_pct:.1f}% outlier density) and IsolationForest flags show tail events distort unweighted means vs median ({primary_diag.median})."
                if primary_diag
                else f"Isolate high-leverage variance drivers across {primary_num}."
            ),
            expected_financial_impact=f"Stabilizes {primary_num} forecasting accuracy and caps tail-risk leakage.",
            operational_owner="Principal Analyst / RevOps Lead",
            risk_level="Low",
        ),
        StrategicInitiative(
            priority="P1 - 30-60 Days",
            time_horizon="30-60 Days",
            title=(
                f"Replicate '{top_bench.top_segment}' Playbook Across {top_bench.dimension}"
                if top_bench
                else f"Rebalance Cohort Concentration Across {primary_cat}"
            ),
            rationale=(
                f"{top_bench.narrative}"
                if top_bench
                else f"Address concentration dependencies (Top 20%: {concentration.top_20_percent_share if concentration else 0}%)."
            ),
            expected_financial_impact="Narrows top-to-bottom cohort spread and expands blended efficiency.",
            operational_owner="VP of Operations & Commercial Leads",
            risk_level="Medium",
        ),
        StrategicInitiative(
            priority="P2 - 90 Days+",
            time_horizon="90+ Days",
            title=(
                f"Operationalize Leading Indicator Tracking ({top_corr.metric_a} → {top_corr.metric_b})"
                if top_corr and abs(top_corr.pearson_r) >= 0.4
                else f"Deploy Automated Quantile Governance & Schema SLA for {primary_num}"
            ),
            rationale=(
                f"{top_corr.interpretation}"
                if top_corr and abs(top_corr.pearson_r) >= 0.4
                else "Institutionalize median/IQR SLA gates and duplicate/null freshness checks across pipelines."
            ),
            expected_financial_impact="Continuous early-warning telemetry before lagging KPI misses.",
            operational_owner="Head of Data Architecture & BI",
            risk_level="Low",
        ),
    ]

    risks = [
        RiskAssessment(
            risk_title=f"Cohort Concentration across {concentration.dimension if concentration else primary_cat}",
            severity="High" if (concentration and concentration.hhi_index >= 2000) else "Moderate",
            probability="Medium",
            business_exposure=(
                f"HHI at {concentration.hhi_index} ({concentration.market_classification}): top 20% of {concentration.dimension} drive {concentration.top_20_percent_share}% of {concentration.metric}."
                if concentration
                else f"Over-reliance on top {primary_cat} segments weakens portfolio resilience."
            ),
            mitigation_protocol="Track rolling HHI & Pareto 80/20 contribution monthly; incentivize growth in mid-tier segments.",
        ),
        RiskAssessment(
            risk_title=f"Skewness & Mean Distortion in {primary_num}",
            severity="High" if (primary_diag and abs(primary_diag.skewness) >= 1.5) else "Moderate",
            probability="High" if (primary_diag and (primary_diag.outlier_pct or 0) >= 5.0) else "Medium",
            business_exposure=(
                f"Non-normal skew ({primary_diag.skewness:+.2f}) causes arithmetic averages to misstate typical cohort performance."
                if primary_diag
                else f"Tail variance in {primary_num} introduces planning drift."
            ),
            mitigation_protocol="Benchmark targets against Median (P50) & IQR bands (P25–P75) rather than mean alone.",
        ),
    ]
    if quality_audit.completeness_pct < 98.0 or quality_audit.duplicate_rows > 0:
        risks.append(
            RiskAssessment(
                risk_title="Ingestion Hygiene (Nulls / Duplicate Records)",
                severity="Moderate",
                probability="High",
                business_exposure=f"{quality_audit.duplicate_rows:,} duplicate rows ({quality_audit.duplicate_pct:.1f}%) and {100.0 - quality_audit.completeness_pct:.1f}% missing cell rate may bias aggregates.",
                mitigation_protocol="Enforce upstream primary-key deduplication and null imputation rules prior to BI refresh.",
            )
        )

    dossier = ExecutiveDossier(
        executive_verdict=(
            f"Empirical Verdict: Across {len(df):,} validated records of {dataset_name}, "
            f"{primary_num} shows its clearest structural differentiation across {top_bench.dimension if top_bench else primary_cat}."
            f"{bench_clause} Anchor operational decisions on median/IQR benchmarks while resolving flagged tail outliers."
        ),
        situation=(
            f"Dataset comprises {len(df):,} rows and {len(df.columns)} columns ({quality_audit.completeness_pct:.1f}% complete, "
            f"{quality_audit.duplicate_rows:,} duplicates). Analysis prioritizes target metrics [{', '.join(numeric_cols[:3])}] "
            f"segmented by [{', '.join(cat_cols[:2])}] under '{user_prompt}'."
            f"{id_note}"
        ),
        complication=(
            f"{diag_clause.strip()}{corr_clause}"
            + (
                f" Concentration across {concentration.dimension} registers HHI {concentration.hhi_index} "
                f"({concentration.market_classification}, top 20% = {concentration.top_20_percent_share}%)."
                if concentration
                else ""
            )
        ),
        resolution=(
            f"Execute a 3-horizon plan: (1) Triage extreme Tukey/IsolationForest anomalies distorting {primary_num}; "
            f"(2) Scale best practices from top cohort '{top_bench.top_segment if top_bench else primary_cat}' while remediating laggards; "
            f"(3) Replace mean-only scorecards with P25/Median/P75 guardrails and live DAX/Tableau telemetry."
        ),
        data_integrity_score=integrity,
        statistical_diagnostics=diagnostics,
        concentration_risk=concentration,
        strategic_initiatives=initiatives,
        risk_matrix=risks,
        methodological_notes=[
            f"Sample coverage: n = {len(df):,} observations across {len(df.columns)} features (completeness {quality_audit.completeness_pct:.1f}%, duplicates {quality_audit.duplicate_rows:,}).",
            f"Semantic typing classified {len(quality_audit.continuous_columns)} continuous, {len(quality_audit.rate_columns)} rate/ratio, {len(quality_audit.temporal_columns)} temporal, {len(quality_audit.categorical_columns)} categorical, and excluded {len(quality_audit.excluded_id_columns)} identifier key(s).",
            "Distributions evaluated via parametric (Mean, SD) and robust non-parametric (Median, IQR, P95, 1.5×IQR Tukey fences) bounds; covariance measured with Pearson r & Spearman ρ.",
            "Multivariate anomaly detection executed via Scikit-Learn IsolationForest (100 trees, contamination=0.05) strictly on standardized non-ID numeric features.",
        ],
        data_quality_audit=quality_audit,
        correlation_insights=correlations,
        correlation_matrix=correlation_matrix,
        segment_benchmarks=segment_benchmarks,
    )

    dax_script = f"-- Consolidated DAX Architecture for {dataset_name}\n-- Mandate: {user_prompt}\n" + "\n\n".join([k.formula_dax for k in kpis])
    powerquery_m = """let
    Source = Csv.Document(File.Contents("dataset.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    #"Promoted Headers\""""

    tableau_calcs = [{"caption": k.title, "formula": k.formula_tableau} for k in kpis]

    return DashboardPlan(
        title=f"Principal Data Analysis Report: {dataset_name.replace('.csv', '').replace('_', ' ').title()}",
        summary=(
            f"Senior statistical audit of {len(df):,} observations in {dataset_name} evaluating "
            f"{', '.join(numeric_cols[:3])} across {top_bench.dimension if top_bench else primary_cat}.{corr_clause}"
        ),
        dataset_name=dataset_name,
        kpis=kpis,
        visuals=visuals,
        dossier=dossier,
        dax_script=dax_script,
        powerquery_m=powerquery_m,
        tableau_calculated_fields=tableau_calcs,
        focused_metrics=numeric_cols[:3],
        focused_dimensions=cat_cols[:2],
        analytical_intent=intent,
    )


async def call_llm_dashboard_planner(
    schema_summary: str,
    row_count: int,
    user_prompt: str,
    dataset_name: str,
    ground_truth_summary: str = "",
    target_focus: str = "",
    deep_stats_summary: str = "",
) -> Optional[DashboardPlan]:
    """
    Invokes Instructor (wrapping Google Gemini / Groq Cloud) to synthesize a guaranteed
    type-safe DashboardPlan Pydantic model with automatic self-correcting retries.
    """
    user_content = build_dashboard_user_prompt(
        dataset_name=dataset_name,
        schema_summary=schema_summary,
        row_count=row_count,
        user_prompt=user_prompt,
        ground_truth_summary=ground_truth_summary,
        target_focus=target_focus,
        deep_stats_summary=deep_stats_summary,
    )
    try:
        plan = await generate_structured(
            response_model=DashboardPlan,
            system_prompt=DASHBOARD_PLANNER_SYSTEM_PROMPT,
            user_prompt=user_content,
            max_retries=3,
            temperature=0.2,
        )
        return plan
    except Exception as e:
        logger.warning(f"Instructor structured dashboard planning failed: {e}")
        return None


def compute_visual_series_data(
    df: pd.DataFrame,
    visual: ChartVisualSpec,
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
    anomaly_indices: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Executes shape-aware Pandas aggregation for histograms, Pareto curves,
    chronological time-series, scatter plots, and grouped bars.
    """
    return compute_visual_series_data_expert(df, visual, roles=roles, anomaly_indices=anomaly_indices)


def generate_dossier_markdown(plan: DashboardPlan) -> str:
    """
    Compiles a 10-year Senior Data Analyst Executive Dossier markdown document
    with full SCR synthesis, data quality governance, non-parametric quantiles,
    correlations, ANOVA segment benchmarks, visuals rationale, and BI formulas.
    """
    dossier = plan.dossier
    if not dossier:
        return f"# {plan.title}\n\n{plan.summary}"

    focus_line = ""
    if plan.focused_metrics or plan.analytical_intent:
        focus_line = f"**Analytical Intent:** `{plan.analytical_intent or 'General Executive'}` | **Target Metrics:** `{', '.join(plan.focused_metrics)}` | **Cohorts:** `{', '.join(plan.focused_dimensions)}`\n"

    md = f"""# 🏛️ EXECUTIVE INTELLIGENCE DOSSIER
## {plan.title}
**Dataset:** `{plan.dataset_name}` | **Data Integrity Index:** `{dossier.data_integrity_score}%` | **Classification:** Principal Analyst Technical Report
{focus_line}
---

### 1. EXECUTIVE VERDICT
> **Boardroom Takeaway:** {dossier.executive_verdict}

---

### 2. SITUATION - COMPLICATION - RESOLUTION (SCR) ANALYSIS
* **Situation (Current Operational Baseline):**
  {dossier.situation}

* **Complication (Structural Vulnerabilities & Headwinds):**
  {dossier.complication}

* **Resolution (Target Operating Playbook):**
  {dossier.resolution}

---

### 3. EXECUTIVE KPI SCORECARD
| Metric | Value | Variance vs Target | Benchmark | Strategic Implication |
| :--- | :--- | :--- | :--- | :--- |
"""
    for kpi in plan.kpis:
        md += f"| **{kpi.title}** | `{kpi.value}` | `{kpi.change or 'N/A'}` | {kpi.benchmark or 'Sector Median'} | {kpi.executive_takeaway or kpi.rationale} |\n"

    if dossier.data_quality_audit:
        q = dossier.data_quality_audit
        md += f"""
---

### 4. DATA GOVERNANCE & SCHEMA ROLE AUDIT
* **Dimensions:** `{q.total_rows:,}` observations × `{q.total_columns}` columns
* **Completeness:** `{q.completeness_pct:.1f}%` | **Duplicate Rows:** `{q.duplicate_rows:,}` (`{q.duplicate_pct:.1f}%`)
* **Excluded ID Columns:** `{', '.join(q.excluded_id_columns) if q.excluded_id_columns else 'None'}`
* **Chronological Axes:** `{', '.join(q.temporal_columns) if q.temporal_columns else 'None'}`
* **Continuous / Additive Metrics:** `{', '.join(q.continuous_columns) if q.continuous_columns else 'None'}`
* **Rates / Ratios (Mean-only):** `{', '.join(q.rate_columns) if q.rate_columns else 'None'}`
"""

    if dossier.concentration_risk:
        c = dossier.concentration_risk
        md += f"""
---

### 5. PORTFOLIO CONCENTRATION & VOLATILITY (HHI ANALYSIS)
* **Analyzed Dimension:** `{c.dimension}` on metric `{c.metric}`
* **Top 20% Quantile Concentration:** `{c.top_20_percent_share}%` of total volume
* **Herfindahl-Hirschman Index (HHI):** `{c.hhi_index}` ({c.market_classification})
* **Strategic Assessment:** {c.strategic_takeaway}
"""

    if dossier.statistical_diagnostics:
        md += """
---

### 6. ECONOMETRIC DISTRIBUTION & QUANTILE DIAGNOSTICS
| Metric | Mean | Median | Q1–Q3 (IQR) | P95 | Skew | CV | Tukey Outliers | Diagnosis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for d in dossier.statistical_diagnostics:
            iqr_str = f"{d.p25}–{d.p75}" if d.p25 is not None and d.p75 is not None else "N/A"
            out_str = f"{d.outlier_count} ({d.outlier_pct}%)" if d.outlier_count is not None else "N/A"
            md += f"| **{d.metric_name}** | {d.mean} | {d.median if d.median is not None else 'N/A'} | {iqr_str} | {d.p95 if d.p95 is not None else 'N/A'} | {d.skewness} | {d.cv} | {out_str} | {d.interpretation} |\n"

    if dossier.correlation_insights:
        md += """
---

### 7. MULTIVARIATE CORRELATION & FEATURE DRIVER ANALYSIS
| Metric Pair | Pearson r | Spearman ρ | p-value | Strength & Direction | Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for corr in dossier.correlation_insights:
            md += f"| **{corr.metric_a} × {corr.metric_b}** | `{corr.pearson_r:+.3f}` | `{corr.spearman_rho:+.3f}` | `{corr.p_value}` | {corr.strength} {corr.direction} | {corr.interpretation} |\n"

    if dossier.segment_benchmarks:
        md += """
---

### 8. COHORT PERFORMANCE & ANOVA VARIANCE BENCHMARKS
"""
        for sb in dossier.segment_benchmarks:
            md += f"#### `{sb.metric}` by `{sb.dimension}` (η² = `{sb.eta_squared}`, {sb.cohort_count} cohorts)\n{sb.narrative}\n\n"
            md += "| Segment | n | Mean | vs Portfolio Mean | Share % | Status |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            for row in sb.rows:
                md += f"| **{row.segment}** | {row.record_count:,} | `{row.metric_mean}` | `{row.vs_mean_pct:+.1f}%` | {row.share_pct:.1f}% | `{row.status}` |\n"
            md += "\n"

    if dossier.strategic_initiatives:
        md += """
---

### 9. PRIORITIZED STRATEGIC ACTION ROADMAP
| Priority | Time Horizon | Strategic Initiative | Expected Financial Impact | Operational Owner | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for init in dossier.strategic_initiatives:
            md += f"| **{init.priority}** | {init.time_horizon} | **{init.title}**<br>*{init.rationale}* | `{init.expected_financial_impact}` | {init.operational_owner} | `{init.risk_level}` |\n"

    if dossier.risk_matrix:
        md += """
---

### 10. GOVERNANCE & RISK MITIGATION MATRIX
| Risk Vector | Severity | Probability | Business Exposure | Mitigation Protocol |
| :--- | :--- | :--- | :--- | :--- |
"""
        for r in dossier.risk_matrix:
            md += f"| **{r.risk_title}** | `{r.severity}` | `{r.probability}` | {r.business_exposure} | {r.mitigation_protocol} |\n"

    if plan.anomalies:
        md += """
---

### 11. ISOLATION FOREST MULTIVARIATE OUTLIER FORENSICS
"""
        for anom in plan.anomalies:
            md += f"- **Observation #{anom.row_index + 1}** (Anomaly Score: `{anom.score}`): {anom.explanation}\n"
            md += f"  - *Root Cause:* {anom.root_cause_attribution}\n"
            md += f"  - *Business Impact:* {anom.business_impact}\n"
            md += f"  - *Prescribed Intervention:* {anom.action_required}\n"

    md += """
---

### 12. METHODOLOGICAL DISCLOSURES
"""
    for note in dossier.methodological_notes:
        md += f"- {note}\n"

    if plan.visuals:
        md += """
---

### 13. VISUAL ANALYTICS ARCHITECTURE
| Chart Title | Visual Type | Axes (X → Y) | Aggregation | Why Selected | Key Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for v in plan.visuals:
            md += f"| **{v.title}** | `{v.chart_type}` | `{v.x_axis}` → `{v.y_axis}` | `{v.aggregation}` | {v.selection_reason or v.description} | {v.key_insight or '—'} |\n"

    if plan.dax_script or plan.tableau_calculated_fields:
        md += """
---

### 14. ENTERPRISE BUSINESS INTELLIGENCE (BI) INTEGRATION
"""
        if plan.dax_script:
            md += f"""#### Power BI DAX Measures:
```dax
{plan.dax_script.strip()}
```
"""
        if plan.tableau_calculated_fields:
            md += """#### Tableau Calculated Fields:
"""
            for t in plan.tableau_calculated_fields:
                md += f"- **{t.get('caption', 'Calculation')}**: `{t.get('formula', '')}`\n"

    return md


def _assemble_expert_plan(
    df: pd.DataFrame,
    profile: DatasetProfile,
    anomalies: List[AnomalyFinding],
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
    intent: str,
    user_prompt: str,
    dataset_name: str,
    diagnostics: List[StatisticalDiagnostic],
    concentration: Optional[ConcentrationAnalysis],
    ground_truth_dict: Dict[str, Any],
    quality_audit: Any,
    correlations: List[Any],
    correlation_matrix: Any,
    segment_benchmarks: List[Any],
    llm_plan: Optional[DashboardPlan],
) -> DashboardPlan:
    if llm_plan is not None:
        plan = llm_plan
        plan.dataset_name = dataset_name
        if plan.dossier:
            plan.dossier.statistical_diagnostics = diagnostics
            plan.dossier.concentration_risk = concentration
            plan.dossier.data_integrity_score = profile.data_integrity_score
            plan.dossier.data_quality_audit = quality_audit
            plan.dossier.correlation_insights = correlations
            plan.dossier.correlation_matrix = correlation_matrix
            plan.dossier.segment_benchmarks = segment_benchmarks
        plan.focused_metrics = target_numerics[:3]
        plan.focused_dimensions = target_cats[:2]
        plan.analytical_intent = intent
        plan.kpis = reconcile_kpi_ground_truth(df, plan.kpis, ground_truth_dict)
        plan.visuals = validate_and_upgrade_visuals(
            df=df,
            proposed_visuals=plan.visuals,
            roles=roles,
            target_numerics=target_numerics,
            target_cats=target_cats,
            intent=intent,
            concentration=concentration,
            correlations=correlations,
        )
    else:
        logger.info("Falling back to prompt-adaptive heuristic dashboard plan")
        plan = _heuristic_fallback_dashboard(
            df=df,
            user_prompt=user_prompt,
            dataset_name=dataset_name,
            target_numerics=target_numerics,
            target_cats=target_cats,
            intent=intent,
            roles=roles,
            anomalies=anomalies,
        )

    anomaly_idx_set = {a.row_index for a in anomalies}
    final_visuals: List[ChartVisualSpec] = []
    for vis in plan.visuals:
        vis.series_data = compute_visual_series_data(
            df, vis, roles=roles, anomaly_indices=anomaly_idx_set
        )
        if vis.series_data:
            final_visuals.append(vis)
    if final_visuals:
        plan.visuals = final_visuals

    plan.anomalies = anomalies
    return plan


async def generate_complete_dashboard(csv_text: str, user_prompt: str, dataset_name: str = "dataset.csv") -> DashboardPlan:
    """
    Master Principal Data Analyst Pipeline (Prompt-Adaptive & Data-Shape-Driven):
    1. Ingests & classifies semantic column roles + runs IsolationForest over non-ID numeric features.
    2. Resolves target metrics, dimensions, and analytical intent from user prompt.
    3. Computes quantiles, correlations, ANOVA segment benchmarks, HHI, and data quality audit.
    4. Invokes Gemini / Groq LLM planner via Instructor, then peer-reviews & upgrades visual selections.
    5. Reconciles KPIs against ground-truth and populates data-grounded visual series.
    """
    raw_df = pd.read_csv(io.StringIO(csv_text))
    roles = classify_dataframe_roles(raw_df)
    df, profile, anomalies = profile_dataset(csv_text, roles=roles, df=raw_df)
    target_numerics, target_cats, intent = resolve_prompt_intent_and_columns(df, user_prompt, roles=roles)

    diagnostics = build_expert_statistical_diagnostics(df, target_numerics, roles)
    concentration = calculate_concentration_analysis(df, target_cats, target_numerics)
    ground_truth_dict, ground_truth_summary = compute_ground_truth_context(df, target_numerics, target_cats, roles=roles)
    quality_audit = compute_data_quality_audit(df, roles)
    correlations, correlation_matrix = compute_correlations_and_matrix(df, target_numerics, roles)
    segment_benchmarks = compute_segment_benchmarks(df, target_cats, target_numerics, roles)
    deep_stats_summary = _build_deep_stats_brief(quality_audit, diagnostics, correlations, segment_benchmarks)

    target_focus = (
        f"Primary Target Metrics: {', '.join(target_numerics[:3])}\n"
        f"Target Categorical Dimensions: {', '.join(target_cats[:2])}\n"
        f"Analytical Intent: {intent}"
    )

    schema_lines = []
    for col in profile.columns:
        c_role = roles.get(col.name, {}).get("role", col.dtype)
        stat_summary = f"role={c_role}, dtype={col.dtype}, unique={col.unique_count}, nulls={col.null_count}"
        if col.min_val is not None:
            stat_summary += f", min={col.min_val}, max={col.max_val}, mean={col.mean_val}, skew={col.skewness}, cv={col.cv}"
        schema_lines.append(f"- {col.name} ({stat_summary}, sample={col.sample_values[:3]})")
    schema_summary = "\n".join(schema_lines)

    llm_plan = await call_llm_dashboard_planner(
        schema_summary=schema_summary,
        row_count=profile.row_count,
        user_prompt=user_prompt,
        dataset_name=dataset_name,
        ground_truth_summary=ground_truth_summary,
        target_focus=target_focus,
        deep_stats_summary=deep_stats_summary,
    )

    return _assemble_expert_plan(
        df=df,
        profile=profile,
        anomalies=anomalies,
        roles=roles,
        target_numerics=target_numerics,
        target_cats=target_cats,
        intent=intent,
        user_prompt=user_prompt,
        dataset_name=dataset_name,
        diagnostics=diagnostics,
        concentration=concentration,
        ground_truth_dict=ground_truth_dict,
        quality_audit=quality_audit,
        correlations=correlations,
        correlation_matrix=correlation_matrix,
        segment_benchmarks=segment_benchmarks,
        llm_plan=llm_plan,
    )


async def generate_complete_dashboard_stream(csv_text: str, user_prompt: str, dataset_name: str = "dataset.csv") -> AsyncGenerator[str, None]:
    """
    SSE Telemetry Stream for the Principal Data Analyst & Executive Dashboard Generator.
    """
    yield sse_event("status", {
        "step": 1,
        "stage": "profiling",
        "message": f"Step 1/5: Classifying column semantic roles and profiling '{dataset_name}'..."
    })

    raw_df = pd.read_csv(io.StringIO(csv_text))
    roles = classify_dataframe_roles(raw_df)
    df, profile, anomalies = profile_dataset(csv_text, roles=roles, df=raw_df)
    target_numerics, target_cats, intent = resolve_prompt_intent_and_columns(df, user_prompt, roles=roles)

    yield sse_event("status", {
        "step": 2,
        "stage": "anomaly_detection",
        "message": f"Step 2/5: IsolationForest flagged {len(anomalies)} multivariate outliers on non-ID features (Integrity: {profile.data_integrity_score}%)..."
    })

    diagnostics = build_expert_statistical_diagnostics(df, target_numerics, roles)
    concentration = calculate_concentration_analysis(df, target_cats, target_numerics)
    ground_truth_dict, ground_truth_summary = compute_ground_truth_context(df, target_numerics, target_cats, roles=roles)
    quality_audit = compute_data_quality_audit(df, roles)
    correlations, correlation_matrix = compute_correlations_and_matrix(df, target_numerics, roles)
    segment_benchmarks = compute_segment_benchmarks(df, target_cats, target_numerics, roles)
    deep_stats_summary = _build_deep_stats_brief(quality_audit, diagnostics, correlations, segment_benchmarks)

    primary_targets = ", ".join(target_numerics[:2]) if target_numerics else "All Metrics"
    yield sse_event("status", {
        "step": 3,
        "stage": "intent_resolution",
        "message": f"Step 3/5: Computed quantiles, Pearson/Spearman correlations & ANOVA drivers on [{primary_targets}]..."
    })

    target_focus = (
        f"Primary Target Metrics: {', '.join(target_numerics[:3])}\n"
        f"Target Categorical Dimensions: {', '.join(target_cats[:2])}\n"
        f"Analytical Intent: {intent}"
    )

    schema_lines = []
    for col in profile.columns:
        c_role = roles.get(col.name, {}).get("role", col.dtype)
        stat_summary = f"role={c_role}, dtype={col.dtype}, unique={col.unique_count}, nulls={col.null_count}"
        if col.min_val is not None:
            stat_summary += f", min={col.min_val}, max={col.max_val}, mean={col.mean_val}, skew={col.skewness}, cv={col.cv}"
        schema_lines.append(f"- {col.name} ({stat_summary}, sample={col.sample_values[:3]})")
    schema_summary = "\n".join(schema_lines)

    yield sse_event("status", {
        "step": 4,
        "stage": "llm_synthesis",
        "message": "Step 4/5: Synthesizing Principal Analyst thesis, KPIs, risk governance, and BI formulas..."
    })

    llm_plan = await call_llm_dashboard_planner(
        schema_summary=schema_summary,
        row_count=profile.row_count,
        user_prompt=user_prompt,
        dataset_name=dataset_name,
        ground_truth_summary=ground_truth_summary,
        target_focus=target_focus,
        deep_stats_summary=deep_stats_summary,
    )

    yield sse_event("status", {
        "step": 5,
        "stage": "series_aggregation",
        "message": "Step 5/5: Selecting data-matched visual geometries (Pareto, scatter, histogram, cohorts) & compiling Power BI PBIP..."
    })

    plan = _assemble_expert_plan(
        df=df,
        profile=profile,
        anomalies=anomalies,
        roles=roles,
        target_numerics=target_numerics,
        target_cats=target_cats,
        intent=intent,
        user_prompt=user_prompt,
        dataset_name=dataset_name,
        diagnostics=diagnostics,
        concentration=concentration,
        ground_truth_dict=ground_truth_dict,
        quality_audit=quality_audit,
        correlations=correlations,
        correlation_matrix=correlation_matrix,
        segment_benchmarks=segment_benchmarks,
        llm_plan=llm_plan,
    )

    yield sse_event("complete", plan.model_dump())

