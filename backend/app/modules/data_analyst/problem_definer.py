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
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel

from app.modules.data_analyst.data_cleaner import clean_and_deduplicate_dataset
from app.modules.data_analyst.profiler import classify_dataframe_roles
from app.modules.data_analyst.schemas import (
    AlignedMetricSpec,
    DataCleansingReport,
    DatasetIntakeResponse,
    DatasetVerificationCheck,
    DatasetVerificationResult,
    ProblemDefinitionResult,
    StakeholderAlignment,
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


def _build_deterministic_problem_definition(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    verification: DatasetVerificationResult,
    dataset_name: str,
    user_goal: str = "",
) -> ProblemDefinitionResult:
    """Build a crisp, dataset-grounded problem definition and stakeholder alignment offline."""
    numerics = verification.numeric_metrics
    dims = verification.categorical_dimensions or verification.temporal_dimensions

    # Prioritize growth metric as North Star, risk/rate metric as Guardrail
    growth_cols = [c for c in numerics if _GROWTH_METRIC_RE.search(c)]
    risk_cols = [
        c for c in numerics
        if _RISK_METRIC_RE.search(c) or roles.get(c, {}).get("is_rate") or roles.get(c, {}).get("role") == "rate"
    ]
    north_star = growth_cols[0] if growth_cols else (numerics[0] if numerics else "Primary Metric")
    secondary_num = next((c for c in numerics if c != north_star and c not in risk_cols), None)
    guardrail = risk_cols[0] if risk_cols else (secondary_num or (numerics[1] if len(numerics) > 1 else None))
    primary_dim = dims[0] if dims else None
    secondary_dim = dims[1] if len(dims) > 1 else None

    dim_phrase = (
        f"across {primary_dim}" + (f" and {secondary_dim}" if secondary_dim else "")
        if primary_dim
        else "across records"
    )
    guardrail_phrase = f" without elevating {guardrail}" if guardrail and guardrail != north_star else ""

    if user_goal.strip():
        core_question = (
            f"Given the goal '{user_goal.strip()}', which cohorts {dim_phrase} drive {north_star} performance"
            f"{guardrail_phrase}, and where do outliers signal structural risk?"
        )
    else:
        core_question = (
            f"Which cohorts {dim_phrase} drive sustainable {north_star} growth{guardrail_phrase}, "
            f"and which outliers or underperforming segments require immediate intervention?"
        )

    business_goal = (
        f"Maximize {north_star}"
        + (f" and {secondary_num}" if secondary_num and secondary_num != guardrail else "")
        + (f" while keeping {guardrail} within safe quantile guardrails" if guardrail and guardrail != north_star else "")
        + f" by reallocating focus across {primary_dim or 'high-performing cohorts'}."
    )

    decision_needed = (
        f"Prioritize budget, operational capacity, and remediation playbooks {dim_phrase} based on "
        f"{north_star} contribution, Pareto concentration, and IsolationForest tail anomalies."
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
        aligned_metrics.append(
            AlignedMetricSpec(
                metric_name=col,
                role=m_role,  # type: ignore[arg-type]
                aggregation=agg,
                stakeholder_alignment=(
                    f"Primary {m_role.lower()} KPI tracked via {agg} across {primary_dim or 'all records'}."
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

    clarifying_questions = [
        f"Should {north_star} optimization prioritize total volume expansion or margin efficiency per {primary_dim or 'record'}?",
        (
            f"What acceptable upper threshold should stakeholders enforce for {guardrail} before flagging a {primary_dim or 'cohort'} as high-risk?"
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
        ai_provider_used="deterministic",
    )


async def define_problem_and_align_metrics(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    verification: DatasetVerificationResult,
    dataset_name: str = "dataset.csv",
    user_goal: str = "",
) -> ProblemDefinitionResult:
    """
    Stage 2: Given a verified good/perfect dataset, clarify the core question, business goal,
    decision needed, and align key metrics with stakeholders.
    """
    if not verification.is_good_dataset:
        raise ValueError(
            "Dataset failed verification; fix blocking issues before defining the analytical problem."
        )

    fallback = _build_deterministic_problem_definition(
        df=df,
        roles=roles,
        verification=verification,
        dataset_name=dataset_name,
        user_goal=user_goal,
    )

    configured = get_configured_providers()
    if not configured:
        return fallback

    schema_brief_lines = []
    for col in df.columns[:16]:
        role_info = roles.get(col, {})
        role_name = role_info.get("role", "unknown")
        unique_cnt = int(df[col].nunique())
        samples = df[col].dropna().unique()[:3].tolist()
        schema_brief_lines.append(f"- {col} (role={role_name}, unique={unique_cnt}, sample={samples})")

    sys_prompt = (
        "You are a Principal Data Strategist & Analytics Translator. "
        "The uploaded dataset has passed structural verification. "
        "Define the problem clearly: clarify the core question, business goal, concrete decision needed, "
        "and align key metrics with realistic stakeholders strictly using ONLY the dataset's actual column names. "
        "Never recommend SUM() on rate/ratio columns."
    )
    user_prompt = (
        f"Dataset: {dataset_name} ({verification.cleaned_row_count} rows × {verification.cleaned_column_count} cols, "
        f"readiness={verification.readiness_score}/100, status={verification.status})\n"
        f"Optional User Context: {user_goal.strip() or 'None provided — infer from dataset schema'}\n\n"
        f"Verified Columns & Semantic Roles:\n" + "\n".join(schema_brief_lines)
    )

    try:
        draft = await generate_structured(
            response_model=_LLMProblemDefinitionDraft,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            provider=configured[0],
            max_retries=2,
            temperature=0.2,
            max_tokens=2048,
        )
        valid_cols = set(df.columns)
        grounded_metrics = [
            m for m in draft.aligned_metrics if m.metric_name in valid_cols
        ] or fallback.aligned_metrics
        provider_label = format_provider_model_label(get_last_provider_used() or configured[0])

        return ProblemDefinitionResult(
            core_question=draft.core_question.strip() or fallback.core_question,
            business_goal=draft.business_goal.strip() or fallback.business_goal,
            decision_needed=draft.decision_needed.strip() or fallback.decision_needed,
            stakeholders=draft.stakeholders or fallback.stakeholders,
            aligned_metrics=grounded_metrics,
            clarifying_questions=(draft.clarifying_questions or fallback.clarifying_questions)[:4],
            recommended_analysis_prompt=draft.recommended_analysis_prompt.strip() or fallback.recommended_analysis_prompt,
            ai_provider_used=provider_label,
        )
    except Exception as exc:
        logger.warning(f"LLM problem definition failed; using deterministic framing ({exc})")
        return fallback


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
