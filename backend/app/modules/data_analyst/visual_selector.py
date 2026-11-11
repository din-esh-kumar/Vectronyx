# backend/app/modules/data_analyst/visual_selector.py
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from app.modules.data_analyst.profiler import (
    classify_dataframe_roles,
    format_compact_value,
    safe_float,
)
from app.modules.data_analyst.schemas import (
    ChartVisualSpec,
    ConcentrationAnalysis,
    CorrelationInsight,
)

logger = logging.getLogger("vectronyx.analyst.visuals")


def _resolve_col_name(df: pd.DataFrame, candidate: str) -> str:
    if candidate in df.columns:
        return candidate
    col_map = {str(c).lower(): c for c in df.columns}
    lowered = (candidate or "").lower().strip()
    if lowered in col_map:
        return str(col_map[lowered])
    for c in df.columns:
        cl = str(c).lower()
        if cl in lowered or lowered in cl:
            return str(c)
    return candidate


def _format_bin_edge(val: float, unit_format: str, is_fraction_rate: bool) -> str:
    v = safe_float(val, 0.0)
    if unit_format == "percent":
        pct = v * 100.0 if is_fraction_rate else v
        return f"{pct:.1f}%"
    prefix = "$" if unit_format == "currency" else ""
    av = abs(v)
    if av >= 1_000_000:
        return f"{prefix}{v / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{prefix}{v / 1_000:.1f}K"
    if abs(v - round(v)) < 0.05:
        return f"{prefix}{v:.0f}"
    return f"{prefix}{v:.2f}"


def compute_visual_series_data_expert(
    df: pd.DataFrame,
    visual: ChartVisualSpec,
    roles: Optional[Dict[str, Dict[str, Any]]] = None,
    anomaly_indices: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Computes rich series payloads matched to visual type:
    - histogram: numeric quantile-aware binning in ascending numerical order
    - pareto: sorted descending bars + cumulative % curve + count per bucket
    - scatter: outlier-preserving sampled coordinates + Pearson r / OLS stats
    - line / area on datetime: chronological period bucketing (Year/Month/Day)
    - bar / horizontal_bar / pie: grouped rollup with sample count & vs-mean delta
    """
    if roles is None:
        roles = classify_dataframe_roles(df)

    x_col = _resolve_col_name(df, visual.x_axis)
    y_col = _resolve_col_name(df, visual.y_axis)

    if x_col not in df.columns:
        return []
    if visual.chart_type.lower() != "histogram" and y_col not in df.columns:
        return []

    visual.x_axis = str(x_col)
    visual.y_axis = str(y_col if y_col in df.columns else x_col)

    ctype = (visual.chart_type or "bar").lower().strip()
    x_info = roles.get(visual.x_axis, {})
    y_info = roles.get(visual.y_axis, {})
    y_unit = visual.unit_format or y_info.get("unit_format", "number")
    visual.unit_format = y_unit

    is_rate = bool(y_info.get("is_rate", False))
    y_max_raw = safe_float(df[visual.y_axis].dropna().max(), 0.0) if pd.api.types.is_numeric_dtype(df[visual.y_axis]) else 0.0
    is_fraction_rate = is_rate and y_max_raw <= 1.0

    try:
        # 1. BINNED DISTRIBUTION HISTOGRAM (preserves numerical order)
        if ctype == "histogram":
            col = visual.x_axis if pd.api.types.is_numeric_dtype(df[visual.x_axis]) else visual.y_axis
            if not pd.api.types.is_numeric_dtype(df[col]):
                return []
            raw_series = df[col]
            series: pd.Series = (raw_series if isinstance(raw_series, pd.Series) else raw_series.iloc[:, 0]).dropna()
            if len(series) < 3 or safe_float(series.std(), 0.0) <= 1e-12:
                return []

            c_info = roles.get(col, {})
            unit_fmt = c_info.get("unit_format", "number")
            c_rate = bool(c_info.get("is_rate", False))
            c_max = safe_float(series.max())
            frac_rate = c_rate and c_max <= 1.0

            s_min = float(series.min())
            s_max = float(series.max())
            skew = safe_float(series.skew(), 0.0)
            q1 = float(series.quantile(0.25))
            median = float(series.median())
            q3 = float(series.quantile(0.75))
            p98 = float(series.quantile(0.98))

            # Handle extreme power-law tail compression so main distribution remains readable
            tail_overflow_count = 0
            plot_series: pd.Series = series
            tail_capped = False
            if abs(skew) >= 1.8 and s_max > 0 and p98 > s_min and p98 < s_max * 0.45:
                plot_series = pd.Series(series[series <= p98])
                tail_overflow_count = int((series > p98).sum())
                tail_capped = True

            n_bins = min(12, max(6, int(round(1 + 3.322 * np.log10(max(2, len(plot_series)))))))
            counts, edges = np.histogram(np.asarray(plot_series, dtype=float), bins=n_bins)
            total_n = max(1, len(series))

            result: List[Dict[str, Any]] = []
            peak_idx = int(np.argmax(counts)) if len(counts) > 0 else 0
            for idx, cnt in enumerate(counts):
                low = float(edges[idx])
                high = float(edges[idx + 1])
                label = f"{_format_bin_edge(low, unit_fmt, frac_rate)}–{_format_bin_edge(high, unit_fmt, frac_rate)}"
                result.append({
                    "name": label,
                    "value": int(cnt),
                    "pct": round((int(cnt) / total_n) * 100.0, 1),
                    "binMin": round(low, 4),
                    "binMax": round(high, 4),
                })
            if tail_capped and tail_overflow_count > 0:
                result.append({
                    "name": f">{_format_bin_edge(p98, unit_fmt, frac_rate)}",
                    "value": tail_overflow_count,
                    "pct": round((tail_overflow_count / total_n) * 100.0, 1),
                    "binMin": round(p98, 4),
                    "binMax": round(s_max, 4),
                })

            visual.unit_format = "count"
            modal_label = result[peak_idx]["name"] if peak_idx < len(result) else "N/A"
            med_txt = format_compact_value(median, unit_fmt, c_max if c_rate else None)
            iqr_txt = f"{format_compact_value(q1, unit_fmt, c_max if c_rate else None)}–{format_compact_value(q3, unit_fmt, c_max if c_rate else None)}"
            visual.stat_badge = visual.stat_badge or f"Median {med_txt} | Skew {skew:+.2f}"
            visual.key_insight = visual.key_insight or (
                f"Modal density peaks at [{modal_label}] ({result[peak_idx]['pct']}% of observations); "
                f"50% IQR spans {iqr_txt} with skew {skew:+.2f}."
            )
            return result

        # 2. SCATTER PLOT (Bivariate numerical relationship + outlier markers)
        if ctype == "scatter":
            pair_df: pd.DataFrame = pd.DataFrame(df[[visual.x_axis, visual.y_axis]]).dropna()
            if pair_df.empty:
                return []

            x_is_num = pd.api.types.is_numeric_dtype(pair_df[visual.x_axis])
            y_is_num = pd.api.types.is_numeric_dtype(pair_df[visual.y_axis])
            if not x_is_num or not y_is_num:
                return []

            anom_set = anomaly_indices or set()
            if len(pair_df) > 100:
                outlier_mask = pair_df.index.isin(anom_set)
                outlier_rows = pd.DataFrame(pair_df.loc[outlier_mask]).head(15)
                normal_rows = pd.DataFrame(pair_df.loc[~outlier_mask])
                sample_n = max(1, 100 - len(outlier_rows))
                sampled_normal = normal_rows.sample(n=min(sample_n, len(normal_rows)), random_state=42)
                sample_df = pd.concat([outlier_rows, sampled_normal]).sort_index()
            else:
                sample_df = pair_df

            label_candidates = [
                str(col) for col in df.columns
                if roles.get(str(col), {}).get("role") in ("categorical_low", "categorical_medium", "categorical_high")
            ]
            label_col = next(
                (c for c in label_candidates if any(k in c.lower() for k in ("name", "title", "region", "category", "segment", "corridor"))),
                label_candidates[0] if label_candidates else None,
            )

            result = []
            for idx, row in sample_df.iterrows():
                idx_display = f"#{int(idx) + 1}" if isinstance(idx, (int, np.integer)) else str(idx)
                pt_label = f"Row {idx_display}"
                if label_col and label_col in df.columns and pd.notna(df.loc[idx, label_col]):
                    raw_lbl = str(df.loc[idx, label_col])
                    pt_label = f"{raw_lbl[:28]} ({idx_display})"
                result.append({
                    "name": pt_label,
                    "x": safe_float(row[visual.x_axis], decimals=4),
                    "value": safe_float(row[visual.y_axis], decimals=4),
                    "isOutlier": bool(idx in anom_set),
                })

            if len(pair_df) >= 4 and pair_df[visual.x_axis].std() > 1e-12 and pair_df[visual.y_axis].std() > 1e-12:
                try:
                    res: Any = stats.pearsonr(pair_df[visual.x_axis], pair_df[visual.y_axis])
                    r_val = safe_float(res.statistic if hasattr(res, "statistic") else res[0], 0.0, decimals=2)
                    p_val = safe_float(res.pvalue if hasattr(res, "pvalue") else res[1], 1.0, decimals=4)
                    p_txt = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
                    visual.stat_badge = f"r = {r_val:+.2f} ({p_txt})"
                    if not visual.key_insight:
                        strength = "Strong" if abs(r_val) >= 0.7 else ("Moderate" if abs(r_val) >= 0.4 else "Weak")
                        direction = "positive" if r_val >= 0 else "inverse"
                        visual.key_insight = (
                            f"{strength} {direction} linear correlation between {visual.x_axis} and {visual.y_axis} "
                            f"(Pearson r = {r_val:+.2f}, R² = {r_val ** 2:.2f}, {p_txt})."
                        )
                except Exception:
                    pass
            return result

        # 3. CHRONOLOGICAL TIME-SERIES (line / area when X is datetime)
        if x_info.get("role") == "datetime" and x_info.get("parsed_dates") is not None:
            parsed_col: pd.Series = x_info["parsed_dates"]
            valid_mask = parsed_col.notna() & df[visual.y_axis].notna()
            ts_df = pd.DataFrame({
                "_dt": parsed_col[valid_mask],
                "_y": df.loc[valid_mask, visual.y_axis],
            })
            if ts_df.empty:
                return []

            span_days = max(1, int((ts_df["_dt"].max() - ts_df["_dt"].min()).days))
            n_unique_dates = ts_df["_dt"].nunique()
            if n_unique_dates <= 24:
                freq_label = "Date"
                ts_df["_bucket"] = ts_df["_dt"].dt.strftime("%Y-%m-%d")
                ts_df["_sort"] = ts_df["_dt"]
            elif span_days <= 365 * 4:
                freq_label = "Month"
                ts_df["_bucket"] = ts_df["_dt"].dt.to_period("M").astype(str)
                ts_df["_sort"] = ts_df["_dt"].dt.to_period("M")
            else:
                freq_label = "Year"
                # Focus recent active years if very sparse tail spans a century
                ts_df["_bucket"] = ts_df["_dt"].dt.year.astype(str)
                ts_df["_sort"] = ts_df["_dt"].dt.year

            agg = (visual.aggregation or y_info.get("default_agg", "sum")).lower()
            agg_fn = "mean" if agg in ("avg", "mean") else ("count" if agg == "count" else "sum")

            grouped = (
                ts_df.groupby(["_sort", "_bucket"], observed=True)["_y"]
                .agg(value=agg_fn, count="count")
                .reset_index()
                .sort_values("_sort", ascending=True)
            )
            if len(grouped) > 36:
                grouped = grouped.tail(36)

            overall_mean = safe_float(grouped["value"].mean())
            if visual.reference_value is None:
                visual.reference_value = round(overall_mean, 4)
                visual.reference_label = f"Period Mean ({format_compact_value(overall_mean, y_unit, y_max_raw if is_rate else None)})"

            result = [
                {
                    "name": str(r["_bucket"]),
                    "value": safe_float(r["value"], decimals=4 if is_fraction_rate else 2),
                    "count": int(r["count"]),
                }
                for _, r in grouped.iterrows()
            ]
            if len(result) >= 2 and not visual.key_insight:
                first_v = result[0]["value"]
                last_v = result[-1]["value"]
                peak_row = grouped.loc[grouped["value"].idxmax()]
                visual.stat_badge = visual.stat_badge or f"{len(result)} {freq_label}s"
                visual.key_insight = (
                    f"Chronological {freq_label.lower()} trajectory peaked in {peak_row['_bucket']} at "
                    f"{format_compact_value(safe_float(peak_row['value']), y_unit, y_max_raw if is_rate else None)} "
                    f"(earliest: {format_compact_value(first_v, y_unit, y_max_raw if is_rate else None)} → latest: "
                    f"{format_compact_value(last_v, y_unit, y_max_raw if is_rate else None)})."
                )
            return result

        # 4. CATEGORICAL / PARETO / RANKED BAR / DONUT AGGREGATIONS
        agg = (visual.aggregation or y_info.get("default_agg", "sum")).lower()
        sub: pd.DataFrame = pd.DataFrame(df[[visual.x_axis, visual.y_axis]]).dropna()
        if sub.empty:
            return []

        grouped: pd.DataFrame
        if agg in ("avg", "mean"):
            grouped = pd.DataFrame(
                sub.groupby(visual.x_axis, observed=True)[visual.y_axis].agg(value="mean", count="count").reset_index()
            )
            if len(df) >= 100 and len(grouped) > 15:
                eligible = pd.DataFrame(grouped[grouped["count"] >= 3])
                if len(eligible) >= 5:
                    grouped = eligible
        elif agg == "count":
            grouped = pd.DataFrame(
                sub.groupby(visual.x_axis, observed=True)[visual.y_axis].agg(value="count", count="count").reset_index()
            )
        else:
            grouped = pd.DataFrame(
                sub.groupby(visual.x_axis, observed=True)[visual.y_axis].agg(value="sum", count="count").reset_index()
            )

        grouped = grouped.sort_values(by="value", ascending=False)

        total_sum_all = safe_float(grouped["value"].sum(), 0.0)
        cohort_mean_all = safe_float(grouped["value"].mean(), 0.0)
        if visual.reference_value is None and ctype in ("bar", "horizontal_bar"):
            visual.reference_value = round(cohort_mean_all, 4 if is_fraction_rate else 2)
            visual.reference_label = f"Cohort Mean ({format_compact_value(cohort_mean_all, y_unit, y_max_raw if is_rate else None)})"

        max_cats = 10 if ctype in ("horizontal_bar", "pareto") else 8
        if len(grouped) > max_cats:
            top_records = grouped.head(max_cats - 1)
            other_rows = grouped.iloc[max_cats - 1:]
            other_val = safe_float(
                other_rows["value"].mean() if agg in ("avg", "mean") else other_rows["value"].sum()
            )
            other_cnt = int(other_rows["count"].sum())
            display_rows = [
                {
                    "name": str(r[visual.x_axis]),
                    "value": safe_float(r["value"], decimals=4 if is_fraction_rate else 2),
                    "count": int(r["count"]),
                }
                for _, r in top_records.iterrows()
            ]
            # For rankings by average, keep clean Top N without blurring mean into "Other"; for sums/Pareto include Other
            if agg not in ("avg", "mean"):
                display_rows.append({
                    "name": "Other Cohorts",
                    "value": safe_float(other_val, decimals=2),
                    "count": other_cnt,
                })
        else:
            display_rows = [
                {
                    "name": str(r[visual.x_axis]),
                    "value": safe_float(r["value"], decimals=4 if is_fraction_rate else 2),
                    "count": int(r["count"]),
                }
                for _, r in grouped.iterrows()
            ]

        if ctype == "pareto":
            denom = total_sum_all if abs(total_sum_all) > 1e-9 else 1.0
            running = 0.0
            for item in display_rows:
                running += max(0.0, float(item["value"]))
                item["cumulativePct"] = round(min(100.0, (running / denom) * 100.0), 1)
                item["sharePct"] = round((max(0.0, float(item["value"])) / denom) * 100.0, 1)
            visual.reference_value = 80.0
            visual.reference_label = "80% Pareto Threshold"
            top_two_cum = display_rows[min(1, len(display_rows) - 1)]["cumulativePct"] if display_rows else 0.0
            visual.stat_badge = f"Top 2 = {top_two_cum:.1f}% Cum."
            if not visual.key_insight and display_rows:
                visual.key_insight = (
                    f"Leading segment '{display_rows[0]['name']}' holds {display_rows[0]['sharePct']:.1f}% share; "
                    f"top {min(2, len(display_rows))} segments drive {top_two_cum:.1f}% of cumulative {visual.y_axis}."
                )
        else:
            if display_rows:
                top_r = display_rows[0]
                bot_r = display_rows[-1]
                for item in display_rows:
                    if abs(cohort_mean_all) > 1e-9:
                        item["vsMeanPct"] = round(((item["value"] - cohort_mean_all) / abs(cohort_mean_all)) * 100.0, 1)
                    if abs(total_sum_all) > 1e-9 and agg not in ("avg", "mean"):
                        item["sharePct"] = round((max(0.0, float(item["value"])) / total_sum_all) * 100.0, 1)

                if not visual.stat_badge:
                    visual.stat_badge = f"{len(grouped)} Cohorts" if len(grouped) > max_cats else f"Mean {format_compact_value(cohort_mean_all, y_unit, y_max_raw if is_rate else None)}"
                if not visual.key_insight:
                    t_disp = format_compact_value(top_r["value"], y_unit, y_max_raw if is_rate else None)
                    b_disp = format_compact_value(bot_r["value"], y_unit, y_max_raw if is_rate else None)
                    vs_mean = top_r.get("vsMeanPct")
                    vs_txt = f" ({vs_mean:+.1f}% vs cohort mean)" if vs_mean is not None else ""
                    visual.key_insight = (
                        f"Highest segment '{top_r['name']}' averages/totals {t_disp}{vs_txt}; "
                        f"lowest displayed segment '{bot_r['name']}' sits at {b_disp}."
                    )

        return display_rows
    except Exception as exc:
        logger.warning(f"Failed to compute expert visual series for {visual.title}: {exc}")
        return []


def _choose_categorical_chart_type(
    dim_info: Dict[str, Any],
    agg: str,
    is_concentrated: bool,
) -> str:
    nunique = int(dim_info.get("nunique", 0))
    avg_len = float(dim_info.get("avg_label_len", 8.0))
    if agg == "sum" and is_concentrated and nunique >= 4:
        return "pareto"
    if nunique >= 6 or avg_len > 12.0:
        return "horizontal_bar"
    return "bar"


def build_expert_visual_plan(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
    intent: str,
    concentration: Optional[ConcentrationAnalysis] = None,
    correlations: Optional[List[CorrelationInsight]] = None,
) -> List[ChartVisualSpec]:
    """
    Constructs a complementary 4-to-5 chart analytical portfolio selected strictly
    by data shape, cardinality, temporal order, distribution skew, and covariance.
    """
    visuals: List[ChartVisualSpec] = []
    used_signatures: Set[Tuple[str, str, str]] = set()
    used_pairs: Set[Tuple[str, str]] = set()

    usable_numerics = [
        c
        for c in target_numerics
        if c in df.columns
        and pd.api.types.is_numeric_dtype(df[c])
        and roles.get(c, {}).get("role") not in ("identifier", "constant")
    ]
    if not usable_numerics:
        usable_numerics = [c for c in target_numerics if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    usable_cats = [
        c
        for c in target_cats
        if c in df.columns
        and roles.get(c, {}).get("role") in ("categorical_low", "categorical_medium", "categorical_high")
        and roles.get(c, {}).get("unique_ratio", 0.0) < 0.92
    ]
    if not usable_cats:
        usable_cats = [c for c in target_cats if c in df.columns and roles.get(c, {}).get("role") != "identifier"]

    temporal_cols = [str(c) for c in df.columns if roles.get(str(c), {}).get("role") == "datetime"]

    primary_num = usable_numerics[0] if usable_numerics else None
    sec_num = usable_numerics[1] if len(usable_numerics) > 1 else None
    primary_cat = usable_cats[0] if usable_cats else None
    sec_cat = usable_cats[1] if len(usable_cats) > 1 else primary_cat

    if not primary_num:
        return visuals

    p_num_info = roles.get(primary_num, {})
    p_agg = p_num_info.get("default_agg", "sum")
    p_unit = p_num_info.get("unit_format", "number")
    is_conc = bool(
        (concentration and (concentration.hhi_index >= 1400 or concentration.top_20_percent_share >= 35.0))
        or intent == "concentration_risk"
    )

    # 1. Primary Categorical Performance / Concentration Chart
    if primary_cat:
        cat_info = roles.get(primary_cat, {})
        nunique = int(cat_info.get("nunique", 0))
        avg_len = float(cat_info.get("avg_label_len", 8.0))
        if intent == "concentration_risk" and p_agg == "sum" and nunique >= 4:
            ctype = "pareto"
            reason = f"Pareto 80/20 selected: concentration mandate across '{primary_cat}' ({nunique} cohorts) pairing volume bars with cumulative % share."
        elif nunique >= 6 or avg_len > 12.0:
            ctype = "horizontal_bar"
            reason = f"Horizontal ranking selected: '{primary_cat}' has {nunique} cohorts (avg label {avg_len:.0f} chars), preventing X-axis crowding."
        else:
            ctype = "bar"
            reason = f"Vertical bar comparison selected: '{primary_cat}' has {nunique} discrete cohorts benchmarked against portfolio mean ({p_agg.upper()})."
        visuals.append(
            ChartVisualSpec(
                id="vis_cohort_primary",
                title=f"{'Pareto 80/20: ' if ctype == 'pareto' else ('Mean ' if p_agg == 'avg' else '')}{primary_num} by {primary_cat}",
                chart_type=ctype,
                x_axis=primary_cat,
                y_axis=primary_num,
                aggregation=p_agg,
                unit_format=p_unit,
                description=f"Segment performance comparison evaluating {primary_num} spread across {primary_cat}.",
                selection_reason=reason,
            )
        )
        used_signatures.add((ctype, primary_cat, primary_num))
        used_pairs.add((primary_cat, primary_num))

    # 2. Chronological Time-Series Area/Line (ONLY if verified temporal column exists)
    if temporal_cols:
        t_col = temporal_cols[0]
        visuals.append(
            ChartVisualSpec(
                id="vis_temporal_trend",
                title=f"Longitudinal Trend: {primary_num} over {t_col}",
                chart_type="area",
                x_axis=t_col,
                y_axis=primary_num,
                aggregation=p_agg,
                unit_format=p_unit,
                description=f"Chronological trajectory of {primary_num} tracking momentum and cyclical shifts over time.",
                selection_reason=f"Time-series area selected: '{t_col}' parsed as ordered datetime series sorted chronologically.",
            )
        )
        used_signatures.add(("area", t_col, primary_num))
        used_pairs.add((t_col, primary_num))

    # 3. Binned Distribution Histogram for skewed / multi-value continuous metrics
    if len(df) >= 12 and p_num_info.get("nunique", 0) >= 8 and safe_float(df[primary_num].dropna().std(), 0.0) > 1e-12:
        skew = safe_float(df[primary_num].dropna().skew(), 0.0)
        visuals.append(
            ChartVisualSpec(
                id="vis_distribution_hist",
                title=f"Distribution Profile: {primary_num}",
                chart_type="histogram",
                x_axis=primary_num,
                y_axis=primary_num,
                aggregation="distribution",
                unit_format="count",
                description=f"Empirical frequency density across numeric bins isolating modality, central tendency, and tail skew.",
                selection_reason=f"Histogram selected: continuous metric '{primary_num}' spans {p_num_info.get('nunique', 0):,} distinct values (skewness {skew:+.2f}); binning reveals true density shape.",
            )
        )
        used_signatures.add(("histogram", primary_num, primary_num))
        used_pairs.add((primary_num, primary_num))

    # 4. Bivariate Scatter Plot on strongest numeric pair
    if len(usable_numerics) >= 2 and sec_num is not None:
        pair_x: str = primary_num
        pair_y: str = sec_num
        pair_r: Optional[float] = None
        if correlations:
            best = correlations[0]
            pair_x, pair_y, pair_r = best.metric_a, best.metric_b, best.pearson_r
        r_clause = f"strongest empirical covariance (Pearson r = {pair_r:+.2f})" if pair_r is not None else "two continuous variables"
        visuals.append(
            ChartVisualSpec(
                id="vis_bivariate_scatter",
                title=f"Correlation Forensics: {pair_x} vs {pair_y}",
                chart_type="scatter",
                x_axis=pair_x,
                y_axis=pair_y,
                aggregation="raw",
                unit_format=roles.get(pair_y, {}).get("unit_format", "number"),
                description=f"Bivariate scatter diagnosing linearity, structural slope, and IsolationForest outliers between {pair_x} and {pair_y}.",
                selection_reason=f"Scatter plot selected: isolates {r_clause} with multivariate anomaly markers highlighted.",
            )
        )
        used_signatures.add(("scatter", pair_x, pair_y))
        used_pairs.add((pair_x, pair_y))

    # 5. Complementary Secondary Dimension / Pareto 80/20 / Mix Breakdown (avoid duplicate x,y)
    pareto_dim = next(
        (d for d in usable_cats if any((d, m) not in used_pairs and roles.get(m, {}).get("default_agg") == "sum" for m in usable_numerics)),
        None,
    )
    pareto_metric = next(
        (m for m in usable_numerics if roles.get(m, {}).get("default_agg") == "sum" and pareto_dim and (pareto_dim, m) not in used_pairs),
        None,
    )

    if pareto_dim and pareto_metric and (is_conc or roles.get(pareto_dim, {}).get("nunique", 0) >= 4):
        p_info = roles.get(pareto_dim, {})
        if p_info.get("nunique", 0) <= 5 and pareto_dim != primary_cat:
            visuals.append(
                ChartVisualSpec(
                    id="vis_mix_donut",
                    title=f"Portfolio Mix: {pareto_metric} Share by {pareto_dim}",
                    chart_type="pie",
                    x_axis=pareto_dim,
                    y_axis=pareto_metric,
                    aggregation="sum",
                    unit_format=roles.get(pareto_metric, {}).get("unit_format", "number"),
                    description=f"Proportional portfolio composition across {pareto_dim}.",
                    selection_reason=f"Donut composition selected: '{pareto_dim}' has only {p_info.get('nunique')} mutually exclusive additive slices.",
                )
            )
            used_pairs.add((pareto_dim, pareto_metric))
        else:
            visuals.append(
                ChartVisualSpec(
                    id="vis_pareto_conc",
                    title=f"Pareto 80/20 Concentration: {pareto_metric} by {pareto_dim}",
                    chart_type="pareto",
                    x_axis=pareto_dim,
                    y_axis=pareto_metric,
                    aggregation="sum",
                    unit_format=roles.get(pareto_metric, {}).get("unit_format", "number"),
                    description=f"Ranked cumulative share curve quantifying dependency risk and top-tier concentration across {pareto_dim}.",
                    selection_reason=f"Pareto combo chart selected: additive metric '{pareto_metric}' across '{pareto_dim}' exposes top-tier cumulative concentration vs 80% threshold.",
                )
            )
            used_pairs.add((pareto_dim, pareto_metric))

    # 6. Add secondary rate/risk driver across cohort if not yet covered (ensures >= 4 diverse charts)
    rate_or_sec = next(
        (m for m in usable_numerics if any((d, m) not in used_pairs for d in usable_cats)),
        None,
    )
    if rate_or_sec and len(visuals) < 5:
        dim_choice = next((d for d in usable_cats if (d, rate_or_sec) not in used_pairs), primary_cat)
        if dim_choice:
            sec_num_info = roles.get(rate_or_sec, {})
            sec_agg = sec_num_info.get("default_agg", "sum")
            ctype_sec = _choose_categorical_chart_type(roles.get(dim_choice, {}), sec_agg, False)
            visuals.append(
                ChartVisualSpec(
                    id="vis_secondary_cohort",
                    title=f"{'Mean ' if sec_agg == 'avg' else ''}{rate_or_sec} across {dim_choice}",
                    chart_type=ctype_sec,
                    x_axis=dim_choice,
                    y_axis=rate_or_sec,
                    aggregation=sec_agg,
                    unit_format=sec_num_info.get("unit_format", "number"),
                    description=f"Secondary diagnostic contrasting {rate_or_sec} spread across {dim_choice} cohorts.",
                    selection_reason=f"Comparative {'horizontal ' if ctype_sec == 'horizontal_bar' else ''}bar selected for discrete '{dim_choice}' cohorts benchmarked against mean.",
                )
            )

    return visuals[:5]


def validate_and_upgrade_visuals(
    df: pd.DataFrame,
    proposed_visuals: List[ChartVisualSpec],
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
    intent: str,
    concentration: Optional[ConcentrationAnalysis] = None,
    correlations: Optional[List[CorrelationInsight]] = None,
) -> List[ChartVisualSpec]:
    """
    Acts as a Principal Data Analyst peer-reviewing LLM-proposed visuals:
    - Removes ID columns
    - Converts line/area on unordered categories to bar/horizontal_bar
    - Converts pie charts on rates/averages or >5 slices to bar/pareto
    - Supplements missing diagnostic charts (histogram / scatter / pareto / temporal)
    """
    fallback_pool = build_expert_visual_plan(
        df=df,
        roles=roles,
        target_numerics=target_numerics,
        target_cats=target_cats,
        intent=intent,
        concentration=concentration,
        correlations=correlations,
    )

    upgraded: List[ChartVisualSpec] = []
    seen_types: Set[str] = set()
    seen_axes: Set[Tuple[str, str, str]] = set()

    for vis in proposed_visuals:
        x_col = _resolve_col_name(df, vis.x_axis)
        y_col = _resolve_col_name(df, vis.y_axis)
        if x_col not in df.columns:
            continue
        if vis.chart_type.lower() != "histogram" and y_col not in df.columns:
            continue

        x_info = roles.get(x_col, {})
        y_info = roles.get(y_col, {})
        if x_info.get("role") == "identifier" or y_info.get("role") == "identifier":
            continue

        ctype = (vis.chart_type or "bar").lower().strip()
        agg = (vis.aggregation or y_info.get("default_agg", "sum")).lower()

        # Prevent degenerate or non-numeric scatter plots
        if ctype == "scatter":
            if not (pd.api.types.is_numeric_dtype(df[x_col]) and pd.api.types.is_numeric_dtype(df[y_col])):
                ctype = "horizontal_bar" if x_info.get("nunique", 0) >= 6 else "bar"
                vis.selection_reason = f"Converted scatter on categorical '{x_col}' into cohort '{ctype.replace('_', ' ')}' comparison."
            elif x_col == y_col:
                ctype = "histogram"
                vis.selection_reason = f"Converted single-variable scatter on '{x_col}' into density histogram."

        # Prevent summing non-additive rates/averages
        if y_info.get("is_intensive") and agg == "sum":
            agg = "avg"

        # Rule 1: Line/Area ONLY for datetime/ordered continuous sequences
        if ctype in ("line", "area") and x_info.get("role") != "datetime":
            if x_info.get("nunique", 0) >= 6 or x_info.get("avg_label_len", 8.0) > 12.0:
                ctype = "horizontal_bar"
                vis.selection_reason = (
                    vis.selection_reason
                    or f"Upgraded to horizontal bar: '{x_col}' is unordered categorical (not continuous time), preventing false trend lines."
                )
            else:
                ctype = "bar"
                vis.selection_reason = (
                    vis.selection_reason
                    or f"Upgraded to vertical bar: '{x_col}' has discrete unordered cohorts, so bar comparison is more accurate than line interpolation."
                )

        # Rule 2: Pie/Donut ONLY for 2-5 mutually exclusive additive slices
        if ctype == "pie":
            y_has_neg = pd.api.types.is_numeric_dtype(df[y_col]) and safe_float(df[y_col].min(), 0.0) < 0
            x_nunique = x_info.get("nunique", 0)
            if agg in ("avg", "mean") or x_nunique > 5 or x_nunique < 2 or y_has_neg:
                ctype = "pareto" if agg == "sum" and x_nunique >= 4 else "horizontal_bar"
                reason_detail = "rates/averages" if agg in ("avg", "mean") else f"{x_nunique} categories"
                vis.selection_reason = (
                    f"Upgraded to {ctype.replace('_', ' ')}: pie/donut is invalid for {reason_detail}."
                )
            else:
                vis.selection_reason = (
                    vis.selection_reason
                    or f"Donut chart validated: '{x_col}' has {x_nunique} clean mutually exclusive slices over additive {y_col}."
                )

        # Rule 3: Bar with many categories or long labels -> horizontal_bar
        if ctype == "bar" and (x_info.get("nunique", 0) >= 7 or x_info.get("avg_label_len", 8.0) > 12.0):
            ctype = "horizontal_bar"
            vis.selection_reason = (
                vis.selection_reason
                or f"Horizontal bar selected: '{x_col}' ({x_info.get('nunique')} categories) reads more cleanly horizontally."
            )

        if not vis.selection_reason:
            vis.selection_reason = f"Selected '{ctype}' visual tailored to {x_col} ({x_info.get('role', 'dimension')}) vs {y_col} ({agg.upper()})."

        vis.x_axis = str(x_col)
        vis.y_axis = str(y_col)
        vis.chart_type = ctype
        vis.aggregation = agg
        vis.unit_format = vis.unit_format or y_info.get("unit_format", "number")

        sig = (ctype, vis.x_axis, vis.y_axis)
        if sig not in seen_axes:
            upgraded.append(vis)
            seen_axes.add(sig)
            seen_types.add(ctype)

    # Supplement from expert fallback pool so report covers distribution + correlation + concentration
    priority_types = {"histogram", "scatter", "pareto", "area"}
    for fb in fallback_pool:
        if len(upgraded) >= 5:
            break
        sig = (fb.chart_type, fb.x_axis, fb.y_axis)
        if sig in seen_axes:
            continue
        if fb.chart_type in priority_types and fb.chart_type not in seen_types:
            upgraded.append(fb)
            seen_axes.add(sig)
            seen_types.add(fb.chart_type)

    for fb in fallback_pool:
        if len(upgraded) >= 4:
            break
        sig = (fb.chart_type, fb.x_axis, fb.y_axis)
        if sig not in seen_axes:
            upgraded.append(fb)
            seen_axes.add(sig)
            seen_types.add(fb.chart_type)

    return upgraded[:6]
