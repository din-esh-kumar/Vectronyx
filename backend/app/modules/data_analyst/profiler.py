# backend/app/modules/data_analyst/profiler.py
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from app.modules.data_analyst.schemas import (
    ColumnAuditItem,
    CorrelationInsight,
    CorrelationMatrixData,
    DataQualityAudit,
    SegmentBenchmark,
    SegmentPerformanceRow,
    StatisticalDiagnostic,
)

ID_NAME_RE = re.compile(
    r"^(?:unnamed:\s*0|index|id|uuid|guid|isbn(?:10|13)?|book_?id|user_?id|customer_?id|"
    r"client_?id|order_?id|product_?id|account_?id|transaction_?id|txn_?id|record_?id|row_?id)$|"
    r"_(?:id|uuid|guid|isbn|sku|ssn)$",
    re.IGNORECASE,
)

NON_ID_METRIC_HINT_RE = re.compile(
    r"(?:rev|profit|sales|price|cost|salary|income|amount|volume|score|rating|count|"
    r"pages|duration|days|hours|rate|ratio|margin|fee|churn|qty|units|transactions|orders)",
    re.IGNORECASE,
)

DATE_HINT_RE = re.compile(
    r"(?:date|time|timestamp|created|updated|published|publication|month|quarter|period|week|day|year)",
    re.IGNORECASE,
)

DATE_VALUE_PATTERN_RE = re.compile(
    r"(?:\d{4}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|:\d{2}|"
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)",
    re.IGNORECASE,
)

RATE_HINT_RE = re.compile(
    r"(?:rate|ratio|pct|percent|percentage|margin|churn|chargeback|yield|roi|roe|roa|ctr|cvr|conversion)",
    re.IGNORECASE,
)

INTENSIVE_HINT_RE = re.compile(
    r"(?:average|avg|mean|rating|score|price|unit_price|cost_per|age|duration|days|hours|"
    r"minutes|seconds|pages|num_pages|weight|height|temp|temperature|rank|index)",
    re.IGNORECASE,
)

CURRENCY_HINT_RE = re.compile(
    r"(?:rev|revenue|profit|sales|fee|cost|price|arr|mrr|gmv|gpv|ebitda|income|budget|"
    r"spend|grossvolume|netfee|billing|salary|amount|ltv|cac)",
    re.IGNORECASE,
)

COUNT_HINT_RE = re.compile(
    r"(?:count|transactions|txns|orders|qty|quantity|units|users|customers|pages|days|reviews)",
    re.IGNORECASE,
)

ADDITIVE_OVERRIDE_RE = re.compile(
    r"(?:count|cnt|total|sum|qty|quantity|units|transactions|orders|volume)$|(?:^|_)(?:count|total|sum|qty)(?:$|_)",
    re.IGNORECASE,
)


def safe_float(val: Any, default: float = 0.0, decimals: Optional[int] = None) -> float:
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, decimals) if decimals is not None else f
    except (TypeError, ValueError):
        return default


def safe_opt_float(val: Any, decimals: Optional[int] = 2) -> Optional[float]:
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals) if decimals is not None else f
    except (TypeError, ValueError):
        return None


def infer_unit_format(col_name: str, is_rate: bool = False) -> str:
    if is_rate:
        return "percent"
    name = col_name or ""
    if COUNT_HINT_RE.search(name) and not CURRENCY_HINT_RE.search(name):
        return "count"
    if CURRENCY_HINT_RE.search(name) and not INTENSIVE_HINT_RE.search(name):
        return "currency"
    if any(k in name.lower() for k in ("price", "fee", "revenue", "profit", "cost", "amount", "volume", "arr", "mrr")):
        return "currency"
    if COUNT_HINT_RE.search(name):
        return "count"
    return "number"


def format_compact_value(val: float, unit_format: str = "number", max_scale: Optional[float] = None) -> str:
    v = safe_float(val, 0.0)
    if unit_format == "percent":
        pct = v * 100.0 if (max_scale is not None and max_scale <= 1.0 and abs(v) <= 1.0) else v
        return f"{pct:.2f}%"
    prefix = "$" if unit_format == "currency" else ""
    av = abs(v)
    if av >= 1_000_000_000:
        return f"{prefix}{v / 1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"{prefix}{v / 1_000_000:.2f}M"
    if av >= 10_000:
        return f"{prefix}{v / 1_000:.1f}K"
    if abs(v - round(v)) < 1e-6:
        return f"{prefix}{v:,.0f}"
    return f"{prefix}{v:,.2f}"


def _try_parse_datetime(series: pd.Series, col_name: str) -> Optional[pd.Series]:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    non_null = series.dropna()
    if len(non_null) < 3:
        return None

    # Integer or whole-number float year column (e.g. Year = 2019..2025, published_year with NaNs)
    if pd.api.types.is_integer_dtype(series) or pd.api.types.is_float_dtype(series):
        if re.search(r"(?:^|_)(year|yr|fiscal_year|published_year|release_year|model_year|birth_year|cohort_year)$", col_name, re.IGNORECASE):
            is_whole = ((non_null % 1).abs() < 1e-6).mean() >= 0.98
            if is_whole and float(non_null.min()) >= 1800 and float(non_null.max()) <= 2100 and non_null.nunique() >= 3:
                year_str = series.dropna().round().astype(int).astype(str)
                parsed_years = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
                parsed_years.loc[year_str.index] = pd.to_datetime(year_str, format="%Y", errors="coerce")
                return parsed_years
        return None

    if pd.api.types.is_numeric_dtype(series):
        return None

    sample_str = non_null.astype(str).head(150).str.strip()
    looks_like_date = sample_str.apply(lambda s: bool(DATE_VALUE_PATTERN_RE.search(s)))
    min_ratio = 0.65 if DATE_HINT_RE.search(col_name) else 0.85
    if looks_like_date.mean() < min_ratio:
        return None

    parsed = pd.to_datetime(series.astype(str).str.strip(), errors="coerce", format="mixed")
    valid_ratio = parsed.notna().sum() / max(1, len(non_null))
    if valid_ratio >= 0.75 and parsed.dropna().nunique() >= 3:
        return parsed
    return None


def classify_dataframe_roles(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Classifies each column into a semantic analytical role so downstream metrics,
    correlations, and visualizers behave like a 10-year experienced data analyst.
    """
    roles: Dict[str, Dict[str, Any]] = {}
    n_rows = len(df)

    for col in df.columns:
        col_name = str(col)
        series = df[col]
        non_null = series.dropna()
        n_valid = len(non_null)
        nunique = int(series.nunique(dropna=True))
        null_count = int(series.isna().sum())
        unique_ratio = (nunique / n_valid) if n_valid > 0 else 0.0

        # 0. Explicit ID column names take precedence even on synthetic constant fixtures
        is_num = pd.api.types.is_numeric_dtype(series)
        is_id_name = bool(ID_NAME_RE.search(col_name.strip()))
        if is_id_name:
            roles[col_name] = {
                "name": col_name,
                "role": "identifier",
                "is_numeric": False,
                "unit_format": "number",
                "default_agg": "count",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": int((non_null == 0).sum()) if is_num else 0,
                "avg_label_len": 0.0,
                "is_rate": False,
                "is_intensive": False,
                "parsed_dates": None,
            }
            continue

        # Constant or near-empty column
        if n_valid == 0 or (n_rows > 1 and nunique <= 1):
            roles[col_name] = {
                "name": col_name,
                "role": "constant",
                "is_numeric": is_num,
                "unit_format": infer_unit_format(col_name, False),
                "default_agg": "avg" if is_num else "count",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": int((non_null == 0).sum()) if is_num else 0,
                "avg_label_len": 0.0,
                "is_rate": False,
                "is_intensive": False,
                "parsed_dates": None,
            }
            continue

        # 1. Heuristic identifier check (monotonic / high-cardinality surrogate keys)
        is_monotonic_int_id = False
        is_long_int_id = False
        if is_num and pd.api.types.is_integer_dtype(series) and n_valid >= 25 and unique_ratio >= 0.95:
            if not NON_ID_METRIC_HINT_RE.search(col_name):
                if non_null.is_monotonic_increasing:
                    diffs = non_null.diff().dropna()
                    if not diffs.empty and (diffs == 1).mean() >= 0.8:
                        is_monotonic_int_id = True
                median_abs = float(non_null.abs().median())
                if median_abs >= 1_000_000 and re.search(r"(?:id|code|isbn|num|no|key)", col_name, re.IGNORECASE):
                    is_long_int_id = True

        is_string_code_id = (
            not is_num
            and n_valid >= 25
            and unique_ratio >= 0.95
            and re.search(r"(?:id|code|isbn|uuid|sku|key|hash)", col_name, re.IGNORECASE) is not None
        )

        if is_id_name or is_monotonic_int_id or is_long_int_id or is_string_code_id:
            roles[col_name] = {
                "name": col_name,
                "role": "identifier",
                "is_numeric": False,
                "unit_format": "number",
                "default_agg": "count",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": int((non_null == 0).sum()) if is_num else 0,
                "avg_label_len": 0.0,
                "is_rate": False,
                "is_intensive": False,
                "parsed_dates": None,
            }
            continue

        # 2. Datetime / sequential period detection
        parsed_dates = _try_parse_datetime(series, col_name)
        if parsed_dates is not None:
            roles[col_name] = {
                "name": col_name,
                "role": "datetime",
                "is_numeric": False,
                "unit_format": "number",
                "default_agg": "count",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": 0,
                "avg_label_len": 10.0,
                "is_rate": False,
                "is_intensive": False,
                "parsed_dates": parsed_dates,
            }
            continue

        # 3. Boolean check
        if pd.api.types.is_bool_dtype(series):
            roles[col_name] = {
                "name": col_name,
                "role": "categorical_low",
                "is_numeric": False,
                "unit_format": "count",
                "default_agg": "count",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": 0,
                "avg_label_len": 5.0,
                "is_rate": False,
                "is_intensive": False,
                "parsed_dates": None,
            }
            continue

        # 4. Numeric metric classification (rate vs intensive vs additive)
        if is_num:
            s_min = float(non_null.min())
            s_max = float(non_null.max())
            s_mean = float(non_null.mean())
            zero_count = int((non_null == 0).sum())

            is_rate = bool(RATE_HINT_RE.search(col_name))
            if not is_rate and pd.api.types.is_float_dtype(series):
                if 0.0 <= s_min and s_max <= 1.0 and s_mean < 0.95 and not re.search(r"rating|score", col_name, re.IGNORECASE):
                    is_rate = True

            is_intensive = is_rate or (
                bool(INTENSIVE_HINT_RE.search(col_name))
                and not bool(ADDITIVE_OVERRIDE_RE.search(col_name))
            )
            unit_fmt = infer_unit_format(col_name, is_rate=is_rate)
            role = "rate" if is_rate else ("intensive_metric" if is_intensive else "additive_metric")

            roles[col_name] = {
                "name": col_name,
                "role": role,
                "is_numeric": True,
                "unit_format": unit_fmt,
                "default_agg": "avg" if is_intensive else "sum",
                "nunique": nunique,
                "unique_ratio": round(unique_ratio, 3),
                "null_count": null_count,
                "zero_count": zero_count,
                "avg_label_len": 0.0,
                "is_rate": is_rate,
                "is_intensive": is_intensive,
                "max_val": safe_float(s_max),
                "parsed_dates": None,
            }
            continue

        # 5. Categorical / Text / URL dimension
        sample_str = non_null.astype(str).head(100)
        avg_len = float(sample_str.str.len().mean())
        is_url_col = (
            bool(re.search(r"(?:^|_)(url|uri|href|link|thumbnail|image|img|avatar|photo|website)(?:$|_)", col_name, re.IGNORECASE))
            or sample_str.str.match(r"^https?://", case=False).mean() >= 0.5
        )
        is_long_prose = avg_len >= 65.0 or (
            bool(re.search(r"(?:^|_)(description|abstract|body|notes|comment|comments|review_text|bio|narrative|summary)(?:$|_)", col_name, re.IGNORECASE))
            and nunique > 15
        )
        if is_url_col or is_long_prose:
            cat_role = "text_freetext"
        elif nunique <= 7:
            cat_role = "categorical_low"
        elif nunique <= 30:
            cat_role = "categorical_medium"
        else:
            cat_role = "categorical_high"

        roles[col_name] = {
            "name": col_name,
            "role": cat_role,
            "is_numeric": False,
            "unit_format": "number",
            "default_agg": "count",
            "nunique": nunique,
            "unique_ratio": round(unique_ratio, 3),
            "null_count": null_count,
            "zero_count": 0,
            "avg_label_len": round(avg_len, 1),
            "is_rate": False,
            "is_intensive": False,
            "parsed_dates": None,
        }

    return roles


def compute_data_quality_audit(df: pd.DataFrame, roles: Dict[str, Dict[str, Any]]) -> DataQualityAudit:
    total_rows, total_cols = df.shape
    duplicate_rows = int(df.duplicated().sum()) if total_rows > 0 else 0
    duplicate_pct = safe_float((duplicate_rows / max(1, total_rows)) * 100.0, decimals=2)

    total_cells = max(1, total_rows * max(1, total_cols))
    total_nulls = int(df.isna().sum().sum()) if total_rows > 0 else 0
    completeness_pct = safe_float(((total_cells - total_nulls) / total_cells) * 100.0, decimals=2)

    excluded_ids: List[str] = []
    temporal_cols: List[str] = []
    continuous_cols: List[str] = []
    rate_cols: List[str] = []
    categorical_cols: List[str] = []
    audit_items: List[ColumnAuditItem] = []

    for col in df.columns:
        cname = str(col)
        info = roles.get(cname, {})
        role = info.get("role", "categorical_high")
        null_cnt = int(info.get("null_count", int(df[col].isna().sum())))
        null_pct = safe_float((null_cnt / max(1, total_rows)) * 100.0, decimals=2)
        zero_cnt = int(info.get("zero_count", 0))
        unique_cnt = int(info.get("nunique", int(df[col].nunique(dropna=True))))

        rec = "Active analytical feature"
        if role == "identifier":
            excluded_ids.append(cname)
            rec = "Excluded from KPI sums/correlations (identifier key)"
        elif role == "datetime":
            temporal_cols.append(cname)
            rec = "Ordered chronological axis for time-series modeling"
        elif role == "rate":
            rate_cols.append(cname)
            rec = "Ratio/rate metric — aggregated via mean/median (never summed)"
        elif role in ("intensive_metric", "additive_metric"):
            continuous_cols.append(cname)
            rec = (
                "Intensive scale metric — evaluated with mean/median/IQR"
                if role == "intensive_metric"
                else "Additive continuous metric — Pareto, distribution & cohort rollups"
            )
        elif role == "constant":
            rec = "Zero variance (constant) — excluded from bivariate modeling"
        elif role == "text_freetext":
            rec = "URL / long free-text field — excluded from cohort aggregation charts"
        else:
            categorical_cols.append(cname)
            if role == "categorical_high":
                rec = f"High cardinality ({unique_cnt:,} values) — Top-N ranked cohorts"
            elif role == "categorical_low":
                rec = f"Clean low-cardinality dimension ({unique_cnt} cohorts)"
            else:
                rec = f"Medium cardinality dimension ({unique_cnt} cohorts) — horizontal ranking"

        if null_pct > 5.0:
            rec += f" | Warning: {null_pct:.1f}% missing"

        audit_items.append(
            ColumnAuditItem(
                name=cname,
                semantic_role=role,
                dtype=str(df[col].dtype),
                null_count=null_cnt,
                null_pct=null_pct,
                unique_count=unique_cnt,
                zero_count=zero_cnt,
                recommendation=rec,
            )
        )

    return DataQualityAudit(
        total_rows=int(total_rows),
        total_columns=int(total_cols),
        duplicate_rows=duplicate_rows,
        duplicate_pct=duplicate_pct,
        completeness_pct=completeness_pct,
        excluded_id_columns=excluded_ids,
        temporal_columns=temporal_cols,
        continuous_columns=continuous_cols,
        rate_columns=rate_cols,
        categorical_columns=categorical_cols,
        column_audit=audit_items,
    )


def build_expert_statistical_diagnostics(
    df: pd.DataFrame,
    numeric_cols: List[str],
    roles: Dict[str, Dict[str, Any]],
) -> List[StatisticalDiagnostic]:
    diagnostics: List[StatisticalDiagnostic] = []
    # Prioritize non-ID numeric columns
    eligible = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    non_ids = [c for c in eligible if roles.get(c, {}).get("role") != "identifier"]
    target_cols = non_ids if non_ids else eligible

    for col in target_cols[:6]:
        series = df[col].dropna()
        n = len(series)
        if n < 3:
            continue

        info = roles.get(col, {})
        unit_fmt = info.get("unit_format", "number")
        is_rate = bool(info.get("is_rate", False))

        mean_v = safe_float(series.mean())
        median_v = safe_float(series.median())
        std_v = safe_float(series.std()) if n > 1 else 0.0
        q1 = safe_float(series.quantile(0.25))
        q3 = safe_float(series.quantile(0.75))
        p95 = safe_float(series.quantile(0.95))
        min_v = safe_float(series.min())
        max_v = safe_float(series.max())
        iqr_v = safe_float(q3 - q1)

        skew_v = safe_float(series.skew(), default=0.0, decimals=2) if n > 2 else 0.0
        kurt_v = safe_float(series.kurtosis(), default=0.0, decimals=2) if n > 3 else 0.0
        cv_v = safe_float((std_v / mean_v), default=0.0, decimals=2) if abs(mean_v) > 1e-9 else 0.0

        # Tukey 1.5 * IQR fence outliers
        lower_fence = q1 - 1.5 * iqr_v
        upper_fence = q3 + 1.5 * iqr_v
        outlier_cnt = int(((series < lower_fence) | (series > upper_fence)).sum()) if iqr_v > 0 else 0
        outlier_pct = safe_float((outlier_cnt / n) * 100.0, decimals=1)

        # Normality / shape diagnosis
        if std_v < 1e-12:
            norm_verdict = "Zero Variance (Constant)"
        elif abs(skew_v) >= 1.5:
            norm_verdict = "Heavy Right-Skew (Power-Law)" if skew_v > 0 else "Heavy Left-Skew"
        elif abs(skew_v) >= 0.6:
            norm_verdict = "Moderately Skewed"
        elif abs(kurt_v) >= 1.5:
            norm_verdict = "Leptokurtic Fat-Tailed"
        else:
            norm_verdict = "Approx. Symmetric"

        mean_disp = format_compact_value(mean_v, unit_fmt, max_scale=max_v if is_rate else None)
        med_disp = format_compact_value(median_v, unit_fmt, max_scale=max_v if is_rate else None)
        mean_med_gap = ""
        if abs(median_v) > 1e-9:
            ratio_pct = ((mean_v - median_v) / abs(median_v)) * 100.0
            if abs(ratio_pct) >= 18.0:
                mean_med_gap = f"Mean ({mean_disp}) diverges {ratio_pct:+.0f}% vs median ({med_disp}), confirming outlier pull. "

        outlier_note = (
            f"{outlier_cnt:,} Tukey IQR outliers ({outlier_pct:.1f}%)."
            if outlier_cnt > 0
            else "No IQR fence outliers."
        )
        interp = (
            f"{norm_verdict} (skew {skew_v:+.2f}, CV {cv_v:.2f}). "
            f"{mean_med_gap}"
            f"IQR spans {format_compact_value(q1, unit_fmt, max_v if is_rate else None)}–"
            f"{format_compact_value(q3, unit_fmt, max_v if is_rate else None)}; {outlier_note}"
        )

        decimals = 4 if (is_rate and max_v <= 1.0) else 2
        diagnostics.append(
            StatisticalDiagnostic(
                metric_name=col,
                mean=round(mean_v, decimals),
                median=round(median_v, decimals),
                std=round(std_v, decimals),
                p25=round(q1, decimals),
                p75=round(q3, decimals),
                p95=round(p95, decimals),
                min_val=round(min_v, decimals),
                max_val=round(max_v, decimals),
                iqr=round(iqr_v, decimals),
                skewness=skew_v,
                kurtosis=kurt_v,
                cv=cv_v,
                outlier_count=outlier_cnt,
                outlier_pct=outlier_pct,
                normality_verdict=norm_verdict,
                sample_count=n,
                unit_format=unit_fmt,
                interpretation=interp,
            )
        )

    return diagnostics


def compute_correlations_and_matrix(
    df: pd.DataFrame,
    target_numerics: List[str],
    roles: Dict[str, Dict[str, Any]],
) -> Tuple[List[CorrelationInsight], Optional[CorrelationMatrixData]]:
    candidates = [
        c
        for c in target_numerics
        if c in df.columns
        and pd.api.types.is_numeric_dtype(df[c])
        and roles.get(c, {}).get("role") not in ("identifier", "constant")
        and safe_float(df[c].dropna().std(), 0.0) > 1e-12
    ]
    if len(candidates) < 2 or len(df) < 4:
        return [], None

    selected = candidates[:7]
    corr_df = df[selected].corr(method="pearson").fillna(0.0)
    matrix_rows: List[List[float]] = []
    for row_col in selected:
        matrix_rows.append([safe_float(corr_df.loc[row_col, col], 0.0, decimals=2) for col in selected])

    matrix_data = CorrelationMatrixData(metrics=selected, matrix=matrix_rows)

    pair_insights: List[Tuple[float, CorrelationInsight]] = []
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            m_a = selected[i]
            m_b = selected[j]
            paired = df[[m_a, m_b]].dropna()
            if len(paired) < 4:
                continue
            if paired[m_a].std() <= 1e-12 or paired[m_b].std() <= 1e-12:
                continue
            try:
                r_res = stats.pearsonr(paired[m_a], paired[m_b])
                r_val = safe_float(r_res.statistic if hasattr(r_res, "statistic") else r_res[0], 0.0, decimals=3)
                p_val = safe_float(r_res.pvalue if hasattr(r_res, "pvalue") else r_res[1], 1.0, decimals=4)
                s_res = stats.spearmanr(paired[m_a], paired[m_b])
                rho_val = safe_float(s_res.statistic if hasattr(s_res, "statistic") else s_res[0], r_val, decimals=3)
            except Exception:
                continue

            abs_r = abs(r_val)
            if abs_r >= 0.7:
                strength = "Strong"
            elif abs_r >= 0.4:
                strength = "Moderate"
            elif abs_r >= 0.2:
                strength = "Weak"
            else:
                strength = "Negligible"

            direction = "Positive" if r_val > 0.08 else ("Inverse" if r_val < -0.08 else "Neutral")
            sig_note = "statistically significant (p < 0.05)" if p_val < 0.05 else "not statistically significant at 95% confidence"

            if direction == "Positive":
                interp = (
                    f"{strength} positive linear association (r = {r_val:+.2f}, Spearman ρ = {rho_val:+.2f}, {sig_note}): "
                    f"increases in {m_a} co-move closely with higher {m_b}."
                )
            elif direction == "Inverse":
                interp = (
                    f"{strength} inverse trade-off (r = {r_val:+.2f}, Spearman ρ = {rho_val:+.2f}, {sig_note}): "
                    f"higher {m_a} corresponds to lower {m_b}."
                )
            else:
                interp = (
                    f"Near-zero linear covariance (r = {r_val:+.2f}, ρ = {rho_val:+.2f}); "
                    f"{m_a} and {m_b} move largely independently."
                )

            if abs(abs(rho_val) - abs_r) >= 0.18 and len(paired) >= 15:
                interp += " Spearman/Pearson gap signals non-linear or outlier-driven relationship."

            pair_insights.append(
                (
                    abs_r,
                    CorrelationInsight(
                        metric_a=m_a,
                        metric_b=m_b,
                        pearson_r=r_val,
                        spearman_rho=rho_val,
                        p_value=p_val,
                        strength=strength,
                        direction=direction,
                        interpretation=interp,
                    ),
                )
            )

    pair_insights.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in pair_insights[:5]], matrix_data


def compute_segment_benchmarks(
    df: pd.DataFrame,
    target_cats: List[str],
    target_numerics: List[str],
    roles: Dict[str, Dict[str, Any]],
) -> List[SegmentBenchmark]:
    usable_numerics = [
        c
        for c in target_numerics
        if c in df.columns
        and pd.api.types.is_numeric_dtype(df[c])
        and roles.get(c, {}).get("role") not in ("identifier", "constant")
    ]
    if not usable_numerics or len(df) < 4:
        return []

    metric = usable_numerics[0]
    metric_info = roles.get(metric, {})
    is_rate = bool(metric_info.get("is_rate", False))
    is_intensive = bool(metric_info.get("is_intensive", False))
    unit_fmt = metric_info.get("unit_format", "number")

    usable_cats = [
        c
        for c in target_cats
        if c in df.columns
        and roles.get(c, {}).get("role") in ("categorical_low", "categorical_medium", "categorical_high")
        and 2 <= df[c].nunique(dropna=True) <= 2000
        and roles.get(c, {}).get("unique_ratio", 0.0) < 0.92
    ]
    if not usable_cats:
        return []

    # Score candidate dimensions by ANOVA eta^2 variance explained + clean cardinality
    scored_dims: List[Tuple[float, str, float]] = []
    global_series = df[metric].dropna()
    global_mean = safe_float(global_series.mean(), 0.0)
    global_sum = safe_float(global_series.sum(), 0.0)
    ss_total = safe_float(((global_series - global_mean) ** 2).sum(), 0.0)

    for idx, dim in enumerate(usable_cats[:5]):
        sub = df[[dim, metric]].dropna()
        if len(sub) < 4 or sub[dim].nunique() < 2:
            continue
        grouped = sub.groupby(dim, observed=True)[metric]
        counts = grouped.count()
        # Keep top 20 groups by count for ANOVA when high cardinality
        top_keys = counts.sort_values(ascending=False).head(20).index
        anova_sub = sub[sub[dim].isin(top_keys)]
        group_arrays = [grp[metric].values for _, grp in anova_sub.groupby(dim, observed=True) if len(grp) >= 1]
        eta_sq = 0.0
        if len(group_arrays) >= 2 and ss_total > 1e-12:
            group_means = anova_sub.groupby(dim, observed=True)[metric].agg(["count", "mean"])
            ss_between = float((group_means["count"] * (group_means["mean"] - global_mean) ** 2).sum())
            ss_sub_total = float(((anova_sub[metric] - anova_sub[metric].mean()) ** 2).sum())
            if ss_sub_total > 1e-12:
                eta_sq = safe_float(min(1.0, max(0.0, ss_between / ss_sub_total)), 0.0, decimals=3)

        cardinality_bonus = 0.12 if 2 <= df[dim].nunique() <= 12 else (0.05 if df[dim].nunique() <= 30 else 0.0)
        prompt_bonus = 0.08 if idx == 0 else 0.0
        scored_dims.append((eta_sq + cardinality_bonus + prompt_bonus, dim, eta_sq))

    scored_dims.sort(key=lambda t: t[0], reverse=True)
    benchmarks: List[SegmentBenchmark] = []

    for _, dim, eta_sq in scored_dims[:2]:
        sub = df[[dim, metric]].dropna()
        agg_df = sub.groupby(dim, observed=True)[metric].agg(["count", "sum", "mean"]).reset_index()

        # Filter tiny sample artifacts only when comparing averages in large high-cardinality datasets
        if is_intensive and len(df) >= 100 and len(agg_df) > 15:
            filtered = agg_df[agg_df["count"] >= 3]
            if len(filtered) >= 5:
                agg_df = filtered

        sort_col = "mean" if is_intensive else "sum"
        agg_df = agg_df.sort_values(by=sort_col, ascending=False)
        cohort_count = int(df[dim].nunique(dropna=True))

        top_seg_row = agg_df.iloc[0]
        bottom_seg_row = agg_df.iloc[-1]
        top_seg = str(top_seg_row[dim])
        bottom_seg = str(bottom_seg_row[dim])

        # Select representative top + bottom cohorts (up to 8 rows total)
        if len(agg_df) <= 8:
            display_df = agg_df
        else:
            display_df = pd.concat([agg_df.head(5), agg_df.tail(3)]).drop_duplicates(subset=[dim])

        perf_rows: List[SegmentPerformanceRow] = []
        for _, r in display_df.iterrows():
            cnt = int(r["count"])
            tot = safe_float(r["sum"], decimals=2)
            m_val = safe_float(r["mean"], decimals=4 if is_rate else 2)
            share = safe_float((tot / global_sum) * 100.0, decimals=1) if abs(global_sum) > 1e-9 else 0.0
            vs_mean = safe_float(((m_val - global_mean) / abs(global_mean)) * 100.0, decimals=1) if abs(global_mean) > 1e-9 else 0.0
            status = "Outperformer" if vs_mean >= 10.0 else ("Underperformer" if vs_mean <= -10.0 else "Baseline")
            perf_rows.append(
                SegmentPerformanceRow(
                    dimension=dim,
                    segment=str(r[dim]),
                    record_count=cnt,
                    metric_total=None if is_intensive else tot,
                    metric_mean=m_val,
                    share_pct=share,
                    vs_mean_pct=vs_mean,
                    status=status,
                )
            )

        top_val = safe_float(top_seg_row[sort_col])
        bot_val = safe_float(bottom_seg_row[sort_col])
        spread_ratio = safe_opt_float(top_val / bot_val, decimals=2) if abs(bot_val) > 1e-9 and top_val * bot_val >= 0 else None

        max_scale = safe_float(global_series.max()) if is_rate else None
        narrative = (
            f"Segmenting {metric} across {dim} ({cohort_count} cohorts) explains {eta_sq * 100:.1f}% of observed variance (η² = {eta_sq:.2f}). "
            f"Leading cohort '{top_seg}' ({format_compact_value(safe_float(top_seg_row[sort_col]), unit_fmt, max_scale)}) "
            f"outperforms '{bottom_seg}' ({format_compact_value(safe_float(bottom_seg_row[sort_col]), unit_fmt, max_scale)})"
            + (f" by {spread_ratio:.1f}x." if spread_ratio and spread_ratio > 1.05 else ".")
        )

        benchmarks.append(
            SegmentBenchmark(
                dimension=dim,
                metric=metric,
                eta_squared=eta_sq,
                cohort_count=cohort_count,
                top_segment=top_seg,
                bottom_segment=bottom_seg,
                spread_ratio=spread_ratio,
                narrative=narrative,
                rows=perf_rows,
            )
        )

    return benchmarks
