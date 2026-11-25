# backend/app/modules/data_analyst/data_cleaner.py
"""
Dynamic Data Cleansing, Redundancy Removal, and End-to-End Data Science Pipeline.
Adapts dynamically to arbitrary CSV datasets (schema, cardinality, skew, missingness,
collinearity, clustering structure, and predictive feature importances).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from app.modules.data_analyst.profiler import ID_NAME_RE, safe_float
from app.modules.data_analyst.schemas import (
    CleansingAction,
    ClusterProfile,
    DataCleansingReport,
    DataScienceSummary,
    FeatureImportanceItem,
)

logger = logging.getLogger("vectronyx.data_cleaner")

_MISSING_TOKENS = {
    "",
    "na",
    "n/a",
    "nan",
    "null",
    "none",
    "nil",
    "undefined",
    "-",
    "--",
    "?",
    "missing",
    "#n/a",
    "#na",
    "#value!",
}

_CURRENCY_NUMERIC_RE = re.compile(r"^[\s$€£¥₹+,-]*\(?[\d,]+(?:\.\d+)?\)?%?[\s]*$")


def _compute_integrity(df: pd.DataFrame) -> float:
    if df.empty or df.shape[0] == 0 or df.shape[1] == 0:
        return 0.0
    total_cells = df.shape[0] * df.shape[1]
    null_cells = int(df.isna().sum().sum())
    completeness = (total_cells - null_cells) / total_cells
    dups = int(df.duplicated().sum())
    dup_penalty = (dups / len(df)) * 0.25 if len(df) > 0 else 0.0
    return float(round(max(0.0, min(100.0, (completeness * 100.0) - (dup_penalty * 100.0))), 1))


def _dedupe_column_names(columns: List[Any]) -> List[str]:
    seen: Dict[str, int] = {}
    cleaned: List[str] = []
    for idx, raw in enumerate(columns):
        base = re.sub(r"\s+", " ", str(raw or "").strip()) or f"column_{idx}"
        if base in seen:
            seen[base] += 1
            cleaned.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            cleaned.append(base)
    return cleaned


def _try_coerce_numeric_string(series: pd.Series) -> Optional[pd.Series]:
    """Coerce currency/percent/comma-formatted string columns to float64 when >= 80% valid."""
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return None
    non_null = series.dropna()
    if len(non_null) < 3:
        return None
    sample_str = non_null.astype(str).str.strip()
    if sample_str.apply(lambda s: bool(_CURRENCY_NUMERIC_RE.match(s))).mean() < 0.80:
        return None

    def _parse_num(val: Any) -> float:
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        if not s:
            return np.nan
        neg = s.startswith("(") and s.endswith(")")
        s = s.strip("()").replace(",", "").replace("$", "").replace("€", "").replace("£", "").replace("¥", "").replace("₹", "").replace("%", "").strip()
        try:
            num = float(s)
            return -num if neg else num
        except ValueError:
            return np.nan

    parsed = pd.Series([_parse_num(v) for v in series.tolist()], index=series.index, dtype="float64")
    valid_ratio = float(parsed.notna().sum()) / max(1, len(non_null))
    if valid_ratio >= 0.80:
        return parsed
    return None


def _is_sequential_unnamed_index(series: pd.Series, col_name: str) -> bool:
    if not re.match(r"^(?:unnamed:\s*0|index|row_?id|row_?num)$", col_name.strip(), re.IGNORECASE):
        return False
    non_null = series.dropna()
    if len(non_null) < 3 or not pd.api.types.is_numeric_dtype(non_null):
        return False
    vals = [float(v) for v in non_null.tolist()]
    return all(abs((vals[i + 1] - vals[i]) - 1.0) < 1e-6 for i in range(len(vals) - 1))


def clean_and_deduplicate_dataset(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, DataCleansingReport]:
    """
    Executes dynamic, dataset-adaptive cleansing and redundancy elimination:
      1. Header normalization & unnamed sequential index removal
      2. String whitespace trimming, missing-token normalization, & case canonicalization
      3. Dynamic currency/percentage/comma numeric coercion & +/-inf cleanup
      4. Exact row deduplication & primary-key duplicate elimination
      5. Constant, >80%-sparse, and exact mirror-column removal
      6. Skew-aware missing value imputation (median if |skew| > 1.0 else mean; mode/Unknown for cats)
      7. Collinear feature redundancy audit (|r| >= 0.995 flagged for ML pruning)
    """
    raw_rows, raw_cols = raw_df.shape
    df = raw_df.copy()
    integrity_before = _compute_integrity(df)

    actions: List[CleansingAction] = []
    dropped_cols: List[str] = []
    redundant_cols: List[str] = []
    collinear_pruned: List[str] = []
    type_coercions: List[str] = []
    whitespace_norm_count = 0
    missing_imputed_count = 0
    duplicates_removed = 0

    # 1. Normalize column names
    df.columns = _dedupe_column_names(list(df.columns))

    # Drop 100%-empty columns
    cols_to_drop_initial: List[str] = []
    for col in list(df.columns):
        if df[col].isna().all():
            cols_to_drop_initial.append(col)
            actions.append(CleansingAction(
                stage="schema_hygiene",
                target=col,
                action="drop_empty_column",
                count=raw_rows,
                detail=f"Dropped 100%-empty column '{col}'.",
            ))

    if cols_to_drop_initial:
        df = df.drop(columns=cols_to_drop_initial)
        dropped_cols.extend(cols_to_drop_initial)

    # 2. Trim whitespace & normalize missing placeholders across object/string columns
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            orig = df[col].astype("object")
            non_null_mask = orig.notna()
            if non_null_mask.any():
                trimmed = orig.where(~non_null_mask, orig.astype(str).str.strip())
                changed_ws = int((trimmed[non_null_mask] != orig[non_null_mask].astype(str)).sum())
                whitespace_norm_count += changed_ws

                # Replace missing tokens with NaN
                lowered = trimmed.where(~trimmed.notna(), trimmed.astype(str).str.lower())
                missing_mask = lowered.isin(_MISSING_TOKENS)
                token_hits = int(missing_mask.sum())
                if token_hits > 0:
                    trimmed = trimmed.mask(missing_mask, np.nan)
                    whitespace_norm_count += token_hits
                df[col] = trimmed

    if whitespace_norm_count > 0:
        actions.append(CleansingAction(
            stage="string_normalization",
            target="text_columns",
            action="trim_and_nullify_placeholders",
            count=whitespace_norm_count,
            detail=f"Trimmed whitespace and normalized {whitespace_norm_count} placeholder tokens ('NA', 'null', '-', etc.) to NaN.",
        ))

    # 3. Dynamic currency / formatted numeric string coercion & +/-inf cleanup
    for col in list(df.columns):
        coerced = _try_coerce_numeric_string(df[col])
        if coerced is not None:
            df[col] = coerced
            type_coercions.append(f"{col}: string -> float64")
            actions.append(CleansingAction(
                stage="type_coercion",
                target=col,
                action="coerce_formatted_numeric",
                count=int(coerced.notna().sum()),
                detail=f"Parsed formatted numeric/currency/percent values in '{col}' into numeric float64.",
            ))
        elif pd.api.types.is_numeric_dtype(df[col]):
            inf_mask = np.isinf(df[col].to_numpy(dtype=float, na_value=np.nan))
            inf_cnt = int(np.sum(inf_mask))
            if inf_cnt > 0:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                actions.append(CleansingAction(
                    stage="numeric_hygiene",
                    target=col,
                    action="replace_infinity",
                    count=inf_cnt,
                    detail=f"Replaced {inf_cnt} infinite values in '{col}' with NaN for safe imputation.",
                ))

    # Canonicalize inconsistent casing in low/medium cardinality categoricals (e.g. "usa" vs "USA")
    case_canon_count = 0
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]) and not ID_NAME_RE.search(col):
            non_null = df[col].dropna().astype(str)
            if len(non_null) >= 4:
                raw_unique = non_null.nunique()
                lower_series = non_null.str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
                norm_unique = lower_series.nunique()
                if 1 <= norm_unique < raw_unique and norm_unique <= 50:
                    # Pick most frequent casing per normalized key
                    canonical_map: Dict[str, str] = {}
                    for norm_val, group in non_null.groupby(lower_series):
                        canonical_map[str(norm_val)] = str(group.mode().iloc[0])
                    mapped = df[col].where(df[col].isna(), df[col].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip().map(canonical_map))
                    diff_cnt = int((mapped.dropna() != non_null).sum())
                    if diff_cnt > 0:
                        df[col] = mapped
                        case_canon_count += diff_cnt
                        whitespace_norm_count += diff_cnt

    if case_canon_count > 0:
        actions.append(CleansingAction(
            stage="categorical_canonicalization",
            target="categorical_columns",
            action="merge_case_variants",
            count=case_canon_count,
            detail=f"Canonicalized {case_canon_count} inconsistent casing/spacing categorical labels.",
        ))

    # 4. Exact & Primary-Key Deduplication
    before_dup = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    exact_dups = before_dup - len(df)
    if exact_dups > 0:
        duplicates_removed += exact_dups
        actions.append(CleansingAction(
            stage="redundancy_removal",
            target="rows",
            action="drop_exact_duplicates",
            count=exact_dups,
            detail=f"Removed {exact_dups} exact duplicate observations.",
        ))

    # Primary-key deduplication only when an ID column is >= 90% unique (true PK, not FK)
    for col in df.columns:
        if ID_NAME_RE.search(col) and len(df) >= 5:
            non_null_ids = df[col].dropna()
            if len(non_null_ids) > 0 and (non_null_ids.nunique() / len(non_null_ids)) >= 0.90:
                dup_pk = int(non_null_ids.duplicated().sum())
                if dup_pk > 0:
                    # Keep the row with fewest missing values
                    df["_nn_tmp"] = df.notna().sum(axis=1)
                    df = (
                        df.sort_values("_nn_tmp", ascending=False)
                        .drop_duplicates(subset=[col], keep="first")
                        .drop(columns=["_nn_tmp"])
                        .reset_index(drop=True)
                    )
                    duplicates_removed += dup_pk
                    actions.append(CleansingAction(
                        stage="redundancy_removal",
                        target=col,
                        action="drop_primary_key_duplicates",
                        count=dup_pk,
                        detail=f"Deduplicated {dup_pk} conflicting primary-key rows on '{col}', keeping most complete record.",
                    ))
                break

    # 5. Column-level Redundancy Removal: Sequential Index, Constant, High-Sparsity (>80% null), Exact Mirror Columns
    cols_to_drop_redundancy: List[str] = []
    min_keep_cols = 2
    for col in list(df.columns):
        if df.shape[1] - len(cols_to_drop_redundancy) <= min_keep_cols:
            break
        if _is_sequential_unnamed_index(df[col], col):
            cols_to_drop_redundancy.append(col)
            redundant_cols.append(col)
            actions.append(CleansingAction(
                stage="redundancy_removal",
                target=col,
                action="drop_redundant_index",
                count=len(df),
                detail=f"Dropped redundant sequential index artifact '{col}'.",
            ))
            continue
        nunique = int(df[col].nunique(dropna=True))
        null_ratio = float(df[col].isna().mean()) if len(df) > 0 else 0.0
        if len(df) >= 3 and nunique <= 1:
            cols_to_drop_redundancy.append(col)
            redundant_cols.append(col)
            actions.append(CleansingAction(
                stage="redundancy_removal",
                target=col,
                action="drop_constant_column",
                count=len(df),
                detail=f"Removed zero-variance/constant column '{col}' (unique={nunique}).",
            ))
        elif len(df) >= 5 and null_ratio > 0.80:
            cols_to_drop_redundancy.append(col)
            actions.append(CleansingAction(
                stage="sparsity_pruning",
                target=col,
                action="drop_high_missingness_column",
                count=int(df[col].isna().sum()),
                detail=f"Dropped ultra-sparse column '{col}' ({null_ratio * 100:.1f}% missing).",
            ))

    if cols_to_drop_redundancy:
        df = df.drop(columns=cols_to_drop_redundancy)
        dropped_cols.extend(cols_to_drop_redundancy)

    # Exact duplicate / mirror columns (identical values across two differently named columns)
    mirror_drops: List[str] = []
    remaining_cols = list(df.columns)
    for i in range(len(remaining_cols)):
        c1 = remaining_cols[i]
        if c1 in mirror_drops:
            continue
        for j in range(i + 1, len(remaining_cols)):
            c2 = remaining_cols[j]
            if c2 in mirror_drops:
                continue
            if df.shape[1] - len(mirror_drops) <= min_keep_cols:
                break
            if df[c1].equals(df[c2]):
                mirror_drops.append(c2)
                redundant_cols.append(c2)
                actions.append(CleansingAction(
                    stage="redundancy_removal",
                    target=c2,
                    action="drop_mirror_column",
                    count=len(df),
                    detail=f"Removed exact duplicate column '{c2}' (100% identical to '{c1}').",
                ))

    if mirror_drops:
        df = df.drop(columns=mirror_drops)
        dropped_cols.extend(mirror_drops)

    # 6. Skew-Aware Missing Value Imputation
    for col in df.columns:
        null_cnt = int(df[col].isna().sum())
        if null_cnt == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            non_null = df[col].dropna()
            if non_null.empty:
                continue
            skew_val = safe_float(non_null.skew(), 0.0) if len(non_null) >= 3 else 0.0
            fill_val = float(non_null.median()) if abs(skew_val) > 1.0 else float(non_null.mean())
            method = "median" if abs(skew_val) > 1.0 else "mean"
            df[col] = df[col].fillna(fill_val)
            missing_imputed_count += null_cnt
            actions.append(CleansingAction(
                stage="imputation",
                target=col,
                action=f"impute_numeric_{method}",
                count=null_cnt,
                detail=f"Imputed {null_cnt} missing value(s) in '{col}' using {method} ({fill_val:.2f}).",
            ))
        else:
            non_null = df[col].dropna()
            if non_null.empty:
                fill_cat = "Unknown"
                method = "fallback_unknown"
            else:
                mode_series = non_null.mode()
                top_val = str(mode_series.iloc[0]) if not mode_series.empty else "Unknown"
                top_share = float((non_null == top_val).mean())
                fill_cat = top_val if top_share >= 0.15 else "Unknown"
                method = "mode" if top_share >= 0.15 else "unknown_bucket"
            df[col] = df[col].fillna(fill_cat)
            missing_imputed_count += null_cnt
            actions.append(CleansingAction(
                stage="imputation",
                target=col,
                action=f"impute_categorical_{method}",
                count=null_cnt,
                detail=f"Imputed {null_cnt} missing categorical value(s) in '{col}' with '{fill_cat}'.",
            ))

    # 7. Collinear Numeric Redundancy Audit (|r| >= 0.995) for ML Feature Pruning
    num_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and not ID_NAME_RE.search(c)
    ]
    if len(num_cols) >= 2 and len(df) >= 4:
        corr = df[num_cols].corr().abs()
        for i in range(len(num_cols)):
            c1 = num_cols[i]
            if c1 in collinear_pruned:
                continue
            for j in range(i + 1, len(num_cols)):
                c2 = num_cols[j]
                if c2 in collinear_pruned:
                    continue
                val = corr.loc[c1, c2]
                if pd.notna(val) and float(val) >= 0.995:
                    collinear_pruned.append(c2)
                    actions.append(CleansingAction(
                        stage="multicollinearity_audit",
                        target=c2,
                        action="prune_collinear_ml_feature",
                        count=len(df),
                        detail=f"Flagged '{c2}' (|r|={float(val):.4f} with '{c1}') as collinear redundancy; pruned from ML feature matrix.",
                    ))

    # Estimate extreme outlier winsorization count (3*IQR fence used in ML matrix)
    outliers_winsorized = 0
    for c in num_cols:
        s = df[c].dropna()
        if len(s) >= 6:
            q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
            iqr = q3 - q1
            if iqr > 0:
                outliers_winsorized += int(((s < q1 - 3.0 * iqr) | (s > q3 + 3.0 * iqr)).sum())

    integrity_after = _compute_integrity(df)
    report = DataCleansingReport(
        raw_rows=raw_rows,
        cleaned_rows=len(df),
        rows_removed=max(0, raw_rows - len(df)),
        duplicates_removed=duplicates_removed,
        raw_columns=raw_cols,
        cleaned_columns=df.shape[1],
        columns_dropped=len(dropped_cols),
        dropped_column_names=dropped_cols,
        redundant_columns_removed=list(dict.fromkeys(redundant_cols)),
        collinear_features_pruned=list(dict.fromkeys(collinear_pruned)),
        type_coercions=type_coercions,
        missing_values_imputed=missing_imputed_count,
        whitespace_and_case_normalized=whitespace_norm_count,
        outliers_winsorized=outliers_winsorized,
        integrity_before=integrity_before,
        integrity_after=integrity_after,
        actions=actions,
    )
    return df, report


def run_dynamic_data_science_pipeline(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    collinear_pruned: Optional[List[str]] = None,
) -> Tuple[DataScienceSummary, str]:
    """
    Executes a dataset-adaptive Data Science workflow on the cleansed DataFrame:
      1. Builds winsorized + standardized non-ID, non-collinear numeric matrix
      2. PCA variance explained (PC1 / PC2)
      3. Silhouette-optimized K-Means clustering (auto k in [2..6])
      4. RandomForestRegressor predictive driver & feature importance model on target_numerics[0]
    Returns (DataScienceSummary, concise_text_brief).
    """
    pruned_set = set(collinear_pruned or [])
    candidate_nums = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and roles.get(str(c), {}).get("role") not in ("identifier", "datetime", "constant")
        and str(c) not in pruned_set
    ]
    if not candidate_nums:
        candidate_nums = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
            and roles.get(str(c), {}).get("role") != "identifier"
        ]

    target_metric = target_numerics[0] if target_numerics and target_numerics[0] in df.columns else (candidate_nums[0] if candidate_nums else None)

    # Prepare clean, winsorized numeric matrix for unsupervised ML
    ml_cols = [c for c in candidate_nums if df[c].nunique(dropna=True) > 1]
    pca_variance: List[float] = []
    optimal_k = 0
    sil_score: Optional[float] = None
    clusters: List[ClusterProfile] = []

    if len(ml_cols) >= 2 and len(df) >= 6:
        X_ml = df[ml_cols].copy().astype(float)
        for c in ml_cols:
            X_ml[c] = X_ml[c].fillna(X_ml[c].median())
            q1, q3 = float(X_ml[c].quantile(0.25)), float(X_ml[c].quantile(0.75))
            iqr = q3 - q1
            if iqr > 0:
                X_ml[c] = X_ml[c].clip(lower=q1 - 3.0 * iqr, upper=q3 + 3.0 * iqr)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_ml)

        # PCA
        try:
            n_comp = min(3, len(ml_cols), len(df))
            pca = PCA(n_components=n_comp)
            pca.fit(X_scaled)
            pca_variance = [round(float(v) * 100.0, 1) for v in pca.explained_variance_ratio_]
        except Exception as exc:
            logger.debug(f"PCA skipped: {exc}")

        # Silhouette-optimized K-Means clustering
        try:
            max_k = min(6, len(df) - 1)
            best_k = 0
            best_sil = -1.0
            best_labels: Optional[np.ndarray] = None
            for k in range(2, max_k + 1):
                km = KMeans(n_clusters=k, n_init=10, random_state=42)
                labels = km.fit_predict(X_scaled)
                if len(set(labels)) < 2:
                    continue
                s = float(silhouette_score(X_scaled, labels))
                if s > best_sil:
                    best_sil = s
                    best_k = k
                    best_labels = labels

            if best_k >= 2 and best_labels is not None:
                optimal_k = best_k
                sil_score = round(best_sil, 3)
                temp = X_ml.copy()
                temp["_cluster"] = best_labels
                total_n = len(temp)
                for cid in sorted(temp["_cluster"].unique()):
                    sub = temp[temp["_cluster"] == cid]
                    centroid = {
                        col: round(float(sub[col].mean()), 2)
                        for col in ml_cols[:4]
                    }
                    # Label cluster dynamically vs global mean on target_metric
                    label = f"Cluster {int(cid) + 1}"
                    if target_metric and target_metric in sub.columns:
                        g_mean = float(temp[target_metric].mean())
                        c_mean = float(sub[target_metric].mean())
                        if g_mean != 0:
                            if c_mean >= g_mean * 1.15:
                                label = f"High-{target_metric} Cohort"
                            elif c_mean <= g_mean * 0.85:
                                label = f"Low-{target_metric} Cohort"
                            else:
                                label = f"Core {target_metric} Cohort"
                    clusters.append(
                        ClusterProfile(
                            cluster_id=int(cid),
                            label=label,
                            size=len(sub),
                            share_pct=round((len(sub) / total_n) * 100.0, 1),
                            centroid_summary=centroid,
                        )
                    )
        except Exception as exc:
            logger.debug(f"KMeans clustering skipped: {exc}")

    # Predictive Driver / Feature Importance Modeling
    feature_importances: List[FeatureImportanceItem] = []
    r2_val: Optional[float] = None
    rmse_val: Optional[float] = None
    model_type = "PCA + Silhouette K-Means"

    if target_metric and len(df) >= 8:
        feature_nums = [c for c in candidate_nums if c != target_metric and df[c].nunique(dropna=True) > 1]
        cat_features = [
            c for c in df.columns
            if roles.get(str(c), {}).get("role") == "categorical_low" and 2 <= df[c].nunique(dropna=True) <= 12
        ][:3]

        if feature_nums or cat_features:
            try:
                X_parts: List[pd.DataFrame] = []
                if feature_nums:
                    num_df = df[feature_nums].copy().astype(float)
                    for fc in feature_nums:
                        num_df[fc] = num_df[fc].fillna(num_df[fc].median())
                    X_parts.append(num_df)
                if cat_features:
                    cat_df = pd.get_dummies(df[cat_features].astype(str), drop_first=False, dtype=float)
                    X_parts.append(cat_df)

                X_pred = pd.concat(X_parts, axis=1)
                y_pred_series = df[target_metric].astype(float).fillna(df[target_metric].median())
                if X_pred.shape[1] >= 1 and y_pred_series.nunique() > 1:
                    rf = RandomForestRegressor(
                        n_estimators=100,
                        max_depth=6,
                        min_samples_leaf=max(1, len(df) // 20),
                        random_state=42,
                        oob_score=(len(df) >= 15),
                    )
                    rf.fit(X_pred, y_pred_series)
                    preds = rf.predict(X_pred)
                    raw_r2 = rf.oob_score_ if getattr(rf, "oob_score", False) and hasattr(rf, "oob_score_") else r2_score(y_pred_series, preds)
                    r2_val = round(float(raw_r2), 3)
                    rmse_val = round(float(np.sqrt(mean_squared_error(y_pred_series, preds))), 3)
                    model_type = "RandomForestRegressor + PCA + KMeans"

                    # Compute directional Pearson sign where available
                    importances = rf.feature_importances_
                    ranked = sorted(
                        zip(X_pred.columns, importances),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:8]
                    for feat_name, imp in ranked:
                        corr_val = 0.0
                        try:
                            corr_val = safe_float(X_pred[feat_name].corr(y_pred_series), 0.0)
                        except Exception:
                            corr_val = 0.0
                        feature_importances.append(
                            FeatureImportanceItem(
                                feature=str(feat_name),
                                importance_pct=round(float(imp) * 100.0, 1),
                                direction="positive" if corr_val >= 0 else "negative",
                            )
                        )
            except Exception as exc:
                logger.debug(f"RandomForest driver modeling skipped: {exc}")

    summary = DataScienceSummary(
        target_metric=target_metric,
        model_type=model_type,
        r2_score=r2_val,
        rmse=rmse_val,
        optimal_clusters=optimal_k,
        silhouette_score=sil_score,
        pca_variance_explained_pct=pca_variance,
        top_feature_importances=feature_importances,
        clusters=clusters,
    )

    lines = [f"ML Pipeline: {model_type} | Target: {target_metric or 'None'}"]
    if r2_val is not None:
        lines.append(f"  * Predictive Fit: R²={r2_val}, RMSE={rmse_val}")
    if pca_variance:
        lines.append(f"  * PCA Variance Explained: {', '.join(f'PC{i+1}={v}%' for i, v in enumerate(pca_variance))}")
    if optimal_k >= 2:
        lines.append(f"  * Silhouette-Optimal K-Means: k={optimal_k} (silhouette={sil_score})")
        for cl in clusters:
            lines.append(f"    - {cl.label}: {cl.size} rows ({cl.share_pct}%), centroid={cl.centroid_summary}")
    if feature_importances:
        top_f = ", ".join(f"{f.feature}={f.importance_pct}% ({f.direction})" for f in feature_importances[:5])
        lines.append(f"  * Top Predictive Drivers: {top_f}")

    return summary, "\n".join(lines)
