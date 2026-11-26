# backend/app/modules/data_analyst/refiner.py
"""
N-Iteration Principal Data Analyst Self-Refinement Engine
=========================================================
Continuously audits, peer-reviews, and rewrites a DashboardPlan using max-token
LLM passes (16K output tokens) until the report satisfies 10+ year Principal
Data Analyst & Enterprise Power BI Architect standards (>= 92/100 across 6 axes)
or completes the requested N iterations.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple, cast

import pandas as pd

from app.modules.data_analyst.prompts import (
    PEER_REVIEW_SYSTEM_PROMPT,
    REFINEMENT_SYSTEM_PROMPT,
    build_peer_review_user_prompt,
    build_refinement_user_prompt,
)
from app.modules.data_analyst.schemas import (
    DashboardPlan,
    LLMDashboardDraft,
    RefinementIterationRecord,
    ReportCritique,
)
from app.services.llm.instructor_client import (
    format_provider_model_label,
    generate_structured,
    get_configured_providers,
    get_last_provider_used,
    is_provider_on_cooldown,
)

logger = logging.getLogger("vectronyx.analyst_refiner")

DEFAULT_REFINEMENT_ITERATIONS = 3
MAX_REFINEMENT_ITERATIONS = 8
DEFAULT_TARGET_QUALITY_SCORE = 92.0
DEEP_PLANNER_MAX_TOKENS = 16384
PEER_REVIEW_MAX_TOKENS = 2048


def _count_numbers(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"(?<![A-Za-z0-9_])-?\d+(?:[.,]\d+)?%?(?![A-Za-z0-9_])", text))


def _extract_dataset_columns_in_dax(dax_text: str) -> List[str]:
    if not dax_text:
        return []
    return re.findall(r"(?:'Dataset'|Dataset)\[([^\]]+)\]", dax_text)


def _format_dax_col(col_name: str) -> str:
    safe = col_name.replace("]", "]]")
    return f"'Dataset'[{safe}]"


def _infer_m_type(series: pd.Series, role_info: Dict[str, Any]) -> str:
    role = role_info.get("role", "")
    if role == "temporal":
        return "type date"
    if pd.api.types.is_integer_dtype(series):
        return "Int64.Type"
    if pd.api.types.is_float_dtype(series) or pd.api.types.is_numeric_dtype(series):
        return "type number"
    return "type text"


def build_enterprise_powerquery_m(
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    dataset_name: str = "dataset.csv",
) -> str:
    """
    Generates a production Power Query M script with explicit schema typing,
    text hygiene (Table.Trim), and clean CSV ingestion.
    """
    type_pairs: List[str] = []
    text_cols: List[str] = []
    for col in list(df.columns)[:40]:
        safe_col = str(col).replace('"', '""')
        m_type = _infer_m_type(cast(pd.Series, df[col]), roles.get(str(col), {}))
        type_pairs.append(f'{{"{safe_col}", {m_type}}}')
        if m_type == "type text":
            text_cols.append(f'{{"{safe_col}", Text.Trim, type text}}')

    types_literal = ",\n        ".join(type_pairs)
    trim_step = ""
    final_step = '#"Changed Column Types"'
    if text_cols:
        trim_literal = ",\n        ".join(text_cols[:15])
        trim_step = (
            ',\n    #"Trimmed Text Dimensions" = Table.TransformColumns(\n'
            '        #"Changed Column Types",\n'
            "        {\n"
            f"            {trim_literal}\n"
            "        }\n"
            "    )"
        )
        final_step = '#"Trimmed Text Dimensions"'

    safe_file = (dataset_name or "dataset.csv").replace('"', '""')
    return (
        f"// Enterprise Power Query (M) ETL Pipeline — {safe_file}\n"
        "let\n"
        '    CsvFilePath = "dataset.csv",\n'
        '    Source = Csv.Document(File.Contents(CsvFilePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n'
        '    #"Changed Column Types" = Table.TransformColumnTypes(\n'
        '        #"Promoted Headers",\n'
        "        {\n"
        f"            {types_literal}\n"
        "        }\n"
        f"    ){trim_step}\n"
        "in\n"
        f"    {final_step}"
    )


def build_enterprise_dax_library(
    df: pd.DataFrame,
    plan: DashboardPlan,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
) -> str:
    """
    Builds a production-grade, display-folder documented DAX library using ONLY
    verified exact CSV column names so Power BI Desktop compiles cleanly.
    """
    valid_cols = set(df.columns)
    primary_num = next((c for c in target_numerics if c in valid_cols), None)
    secondary_num = next((c for c in target_numerics[1:] if c in valid_cols), None)
    primary_cat = next((c for c in target_cats if c in valid_cols), None)
    temporal_col = next(
        (c for c, info in roles.items() if info.get("role") == "temporal" and c in valid_cols),
        None,
    )

    sections: List[str] = [
        f"-- ============================================================================",
        f"-- VECTRONYX ENTERPRISE POWER BI DAX SEMANTIC LIBRARY — {plan.dataset_name}",
        f"-- Principal Data Analyst Architecture (Verified Against {len(df):,} Rows × {len(df.columns)} Columns)",
        f"-- ============================================================================",
        "",
        "-- [01 · Executive KPIs]",
    ]

    seen_names: set[str] = set()
    for kpi in plan.kpis:
        key = kpi.title.strip().lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        sections.append(f"-- {kpi.rationale}")
        sections.append(kpi.formula_dax.strip())
        sections.append("")

    if primary_num:
        p_ref = _format_dax_col(primary_num)
        p_label = primary_num.replace("_", " ").title()
        is_rate = roles.get(primary_num, {}).get("role") in ("rate", "score", "ratio")
        base_expr = f"AVERAGE({p_ref})" if is_rate else f"SUM({p_ref})"

        sections.extend([
            "-- [02 · Statistical & Distribution Diagnostics]",
            f"Record Count = COUNTROWS('Dataset')",
            "",
            f"{p_label} Median (P50) = MEDIANX('Dataset', {p_ref})",
            "",
            f"{p_label} Q1 (P25) = PERCENTILEX.INC('Dataset', {p_ref}, 0.25)",
            "",
            f"{p_label} Q3 (P75) = PERCENTILEX.INC('Dataset', {p_ref}, 0.75)",
            "",
            f"{p_label} Tail Threshold (P95) = PERCENTILEX.INC('Dataset', {p_ref}, 0.95)",
            "",
            f"{p_label} IQR Spread = PERCENTILEX.INC('Dataset', {p_ref}, 0.75) - PERCENTILEX.INC('Dataset', {p_ref}, 0.25)",
            "",
            f"{p_label} Std Dev = STDEVX.P('Dataset', {p_ref})",
            "",
            f"{p_label} Volatility CV % = DIVIDE(STDEVX.P('Dataset', {p_ref}), AVERAGEX('Dataset', {p_ref}), 0)",
            "",
            f"{p_label} Upper Tukey Outlier Count =\n"
            f"    VAR Q1 = PERCENTILEX.INC(ALLSELECTED('Dataset'), {p_ref}, 0.25)\n"
            f"    VAR Q3 = PERCENTILEX.INC(ALLSELECTED('Dataset'), {p_ref}, 0.75)\n"
            f"    VAR UpperFence = Q3 + 1.5 * (Q3 - Q1)\n"
            f"    RETURN COUNTROWS(FILTER('Dataset', {p_ref} > UpperFence))",
            "",
        ])

        if primary_cat:
            c_ref = _format_dax_col(primary_cat)
            c_label = primary_cat.replace("_", " ").title()
            sections.extend([
                "-- [03 · Cohort Benchmarks & Pareto Concentration]",
                f"{p_label} Share of Selected % =\n"
                f"    DIVIDE(\n"
                f"        {base_expr},\n"
                f"        CALCULATE({base_expr}, ALLSELECTED('Dataset')),\n"
                f"        0\n"
                f"    )",
                "",
                f"{c_label} Performance Rank =\n"
                f"    RANKX(\n"
                f"        ALLSELECTED({c_ref}),\n"
                f"        CALCULATE({base_expr}),\n"
                f"        ,\n"
                f"        DESC,\n"
                f"        DENSE\n"
                f"    )",
                "",
                f"{p_label} Variance vs Portfolio Mean % =\n"
                f"    VAR CurrentAvg = AVERAGE({p_ref})\n"
                f"    VAR PortfolioAvg = CALCULATE(AVERAGE({p_ref}), ALLSELECTED('Dataset'))\n"
                f"    RETURN DIVIDE(CurrentAvg - PortfolioAvg, PortfolioAvg, 0)",
                "",
                f"{p_label} Cumulative Pareto % =\n"
                f"    VAR CurrentMetric = {base_expr}\n"
                f"    VAR TotalMetric = CALCULATE({base_expr}, ALLSELECTED('Dataset'))\n"
                f"    VAR CumulativeMetric =\n"
                f"        SUMX(\n"
                f"            FILTER(\n"
                f"                SUMMARIZE(ALLSELECTED('Dataset'), {c_ref}, \"__Val\", {base_expr}),\n"
                f"                [__Val] >= CurrentMetric\n"
                f"            ),\n"
                f"            [__Val]\n"
                f"        )\n"
                f"    RETURN DIVIDE(CumulativeMetric, TotalMetric, 0)",
                "",
            ])

        if secondary_num:
            s_ref = _format_dax_col(secondary_num)
            s_label = secondary_num.replace("_", " ").title()
            sections.extend([
                f"{p_label} to {s_label} Efficiency Ratio = DIVIDE(SUM({p_ref}), SUM({s_ref}), 0)",
                "",
            ])

        if temporal_col:
            t_ref = _format_dax_col(temporal_col)
            sections.extend([
                "-- [04 · Time Intelligence & Running Trajectory]",
                f"{p_label} Running Cumulative =\n"
                f"    VAR MaxDate = MAX({t_ref})\n"
                f"    RETURN CALCULATE({base_expr}, FILTER(ALLSELECTED('Dataset'), {t_ref} <= MaxDate))",
                "",
            ])

    return "\n".join(sections).strip()


def build_powerbi_pages_blueprint(
    plan: DashboardPlan,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
) -> List[Dict[str, Any]]:
    """
    Returns a clean, UI-renderable blueprint of the 3-page Executive Power BI
    report exported inside the .pbip package.
    """
    temporal_cols = [c for c, info in roles.items() if info.get("role") == "temporal"]
    slicers = list(dict.fromkeys((target_cats[:2] + temporal_cols[:1])))[:2]

    page1_visuals = [v.title for v in plan.visuals[:4]]
    page2_visuals = [v.title for v in plan.visuals[4:]]
    if not page2_visuals and len(plan.visuals) >= 2:
        page2_visuals = [plan.visuals[-1].title]

    return [
        {
            "page_number": 1,
            "name": "Executive Overview",
            "dimensions": "1280×720 (16:9 Widescreen)",
            "purpose": "C-Suite summary: executive verdict banner, interactive slicers, formatted KPI scorecard row, and core 2×2 visual grid.",
            "slicers": slicers,
            "kpis": [k.title for k in plan.kpis[:5]],
            "visuals": page1_visuals,
        },
        {
            "page_number": 2,
            "name": "Statistical & Cohort Diagnostics",
            "dimensions": "1280×720 (16:9 Widescreen)",
            "purpose": "Senior analyst deep-dive: distribution & correlation visuals, interactive Cohort Performance matrix table, and quantile/ANOVA diagnostics.",
            "slicers": slicers[:1],
            "kpis": [f"{m} Median / P95 / CV %" for m in target_numerics[:2]],
            "visuals": page2_visuals + ["Cohort Performance Breakdown Table (tableEx)", "Statistical & Correlation Diagnostics Card"],
        },
        {
            "page_number": 3,
            "name": "Risk, Anomalies & Action Playbook",
            "dimensions": "1280×720 (16:9 Widescreen)",
            "purpose": "Boardroom decision ledger: SCR synthesis, P0/P1/P2 strategic ROI initiatives, Risk Governance Matrix, and IsolationForest outlier forensics.",
            "slicers": [],
            "kpis": ["Data Integrity Score", "Upper Tukey Outlier Count"],
            "visuals": ["SCR Executive Brief", "Prioritized Strategic Roadmap (P0–P2)", "Risk Governance & Outlier Forensics"],
        },
    ]


def evaluate_plan_deterministic(
    plan: DashboardPlan,
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
) -> Tuple[float, Dict[str, float], List[str]]:
    """
    Deterministic 6-axis Principal Data Analyst rubric evaluator (0–100).
    Flags concrete, measurable structural and quantitative defects.
    """
    valid_cols = set(df.columns)
    id_cols = {c for c, info in roles.items() if info.get("role") == "identifier"}
    defects: List[str] = []

    # 1. Empirical Grounding (numbers density + KPI benchmark/variance completeness)
    emp = 100.0
    if len(plan.kpis) < 4:
        emp -= 22.0
        defects.append(f"Only {len(plan.kpis)} KPI(s) provided; Principal reports require 5–6 executive KPIs.")
    elif len(plan.kpis) < 5:
        emp -= 8.0
        defects.append("Only 4 KPIs provided; add a 5th–6th KPI (e.g., median/spread or concentration benchmark).")

    missing_bench = sum(1 for k in plan.kpis if not (k.benchmark and k.variance and k.executive_takeaway))
    if missing_bench:
        emp -= min(20.0, missing_bench * 5.0)
        defects.append(f"{missing_bench} KPI(s) lack complete benchmark, variance, or executive takeaway.")

    summary_nums = _count_numbers(plan.summary)
    if summary_nums < 2:
        emp -= 15.0
        defects.append("Executive summary lacks concrete empirical figures (cite totals, medians, spreads, or r-values).")
    emp = max(0.0, min(100.0, emp))

    # 2. Executive Depth (SCR dossier length & numerical specificity)
    depth = 100.0
    dossier = plan.dossier
    if not dossier:
        depth = 20.0
        defects.append("Missing ExecutiveDossier SCR synthesis.")
    else:
        for field_name, min_len in (
            ("executive_verdict", 110),
            ("situation", 150),
            ("complication", 150),
            ("resolution", 150),
        ):
            val = getattr(dossier, field_name, "") or ""
            if len(val.strip()) < min_len:
                depth -= 12.0
                defects.append(f"Dossier `{field_name}` is too brief ({len(val.strip())} chars); expand to 3–5 numbers-dense boardroom sentences.")
            if _count_numbers(val) < 1:
                depth -= 6.0
                defects.append(f"Dossier `{field_name}` cites zero empirical numbers from the dataset.")
    depth = max(0.0, min(100.0, depth))

    # 3. Statistical Rigor (quantiles, skew/median, correlations, ANOVA, methodological notes)
    stat = 100.0
    combined_prose = " ".join([
        plan.summary or "",
        (dossier.executive_verdict if dossier else "") or "",
        (dossier.situation if dossier else "") or "",
        (dossier.complication if dossier else "") or "",
        (dossier.resolution if dossier else "") or "",
    ]).lower()
    stat_signals = sum(
        1 for kw in ("median", "iqr", "skew", "outlier", "p95", "correlation", "hhi", "pareto", "variance", "cohort")
        if kw in combined_prose
    )
    if stat_signals < 4:
        stat -= (4 - stat_signals) * 9.0
        defects.append("Executive narrative under-utilizes statistical diagnostics (explicitly cite median vs mean, IQR/P95, correlations, HHI/Pareto, and outliers).")
    if dossier and len(dossier.methodological_notes or []) < 3:
        stat -= 10.0
        defects.append("Include at least 3 methodological disclosures covering sampling, non-parametric bounds, and anomaly detection.")
    stat = max(0.0, min(100.0, stat))

    # 4. Visual Storytelling (5–6 complementary charts, valid non-ID axes, insights)
    vis_score = 100.0
    if len(plan.visuals) < 4:
        vis_score -= 25.0
        defects.append(f"Only {len(plan.visuals)} visual(s); Principal reports require 5–6 complementary charts.")
    elif len(plan.visuals) < 5:
        vis_score -= 8.0
        defects.append("Expand visual suite to 5–6 complementary charts (trend, cohort, Pareto, histogram, scatter).")
    distinct_types = len({(v.chart_type or "").lower() for v in plan.visuals})
    if distinct_types < 3 and len(plan.visuals) >= 3:
        vis_score -= 12.0
        defects.append("Visual types are repetitive; diversify across bar, horizontal_bar, line/area, pareto, histogram, and scatter.")
    missing_insights = sum(1 for v in plan.visuals if not (v.key_insight and len(v.key_insight.strip()) >= 40))
    if missing_insights:
        vis_score -= min(20.0, missing_insights * 6.0)
        defects.append(f"{missing_insights} visual(s) have weak or missing quantified key_insight annotations.")
    id_axis_hits = sum(1 for v in plan.visuals if v.x_axis in id_cols or v.y_axis in id_cols)
    if id_axis_hits:
        vis_score -= 25.0
        defects.append("One or more visuals reference identifier/ID columns on chart axes.")
    vis_score = max(0.0, min(100.0, vis_score))

    # 5. Power BI & DAX Readiness (valid column refs, advanced DAX patterns, typed M)
    bi_score = 100.0
    all_dax = "\n".join([plan.dax_script or ""] + [k.formula_dax or "" for k in plan.kpis])
    referenced_cols = _extract_dataset_columns_in_dax(all_dax)
    invalid_dax_cols = sorted({c for c in referenced_cols if c not in valid_cols})
    if invalid_dax_cols:
        bi_score -= min(30.0, len(invalid_dax_cols) * 10.0)
        defects.append(f"DAX references unknown column(s) not in CSV: {', '.join(invalid_dax_cols[:4])}.")
    advanced_dax_tokens = sum(
        1 for fn in ("DIVIDE", "CALCULATE", "ALLSELECTED", "MEDIAN", "PERCENTILE", "RANKX")
        if fn in all_dax.upper()
    )
    if advanced_dax_tokens < 3:
        bi_score -= 15.0
        defects.append("DAX script lacks enterprise patterns (include DIVIDE, CALCULATE/ALLSELECTED % share, RANKX, and MEDIANX/PERCENTILEX).")
    if not plan.powerquery_m or "Table.TransformColumnTypes" not in plan.powerquery_m:
        bi_score -= 12.0
        defects.append("Power Query M script lacks explicit Table.TransformColumnTypes schema enforcement.")
    bi_score = max(0.0, min(100.0, bi_score))

    # 6. Actionability & ROI (4+ initiatives with ROI/owners, 4+ risks)
    act = 100.0
    inits = dossier.strategic_initiatives if dossier else []
    risks = dossier.risk_matrix if dossier else []
    if len(inits) < 4:
        act -= (4 - len(inits)) * 10.0
        defects.append(f"Only {len(inits)} strategic initiative(s); deliver 4–5 sequenced P0/P1/P2 initiatives with quantified ROI.")
    if len(risks) < 3:
        act -= (3 - len(risks)) * 10.0
        defects.append(f"Only {len(risks)} risk vector(s); deliver 3–4+ concrete risks with quantified business exposure and mitigation protocols.")
    weak_inits = sum(1 for i in inits if not (i.expected_financial_impact and i.operational_owner and len(i.rationale or "") >= 50))
    if weak_inits:
        act -= min(20.0, weak_inits * 6.0)
        defects.append(f"{weak_inits} strategic initiative(s) lack detailed mathematical rationale, quantified impact, or named owner.")
    act = max(0.0, min(100.0, act))

    rubric = {
        "empirical_grounding": round(emp, 1),
        "executive_depth": round(depth, 1),
        "statistical_rigor": round(stat, 1),
        "visual_storytelling": round(vis_score, 1),
        "powerbi_dax_readiness": round(bi_score, 1),
        "actionability_roi": round(act, 1),
    }
    overall = round(sum(rubric.values()) / len(rubric), 1)
    return overall, rubric, defects


def _compact_plan_for_prompt(plan: DashboardPlan) -> str:
    """Serialize DashboardPlan concisely without verbose series/matrix blobs to maximize LLM reasoning budget."""
    dumped = plan.model_dump(
        exclude={
            "refinement_history",
            "powerbi_pages",
            "anomalies",
            "powerquery_m",
        }
    )
    for v in dumped.get("visuals", []):
        v["series_data"] = []
    if isinstance(dumped.get("dossier"), dict):
        dumped["dossier"]["correlation_matrix"] = None
        dumped["dossier"]["data_quality_audit"] = None
        dumped["dossier"]["statistical_diagnostics"] = []
        dumped["dossier"]["segment_benchmarks"] = []
        dumped["dossier"]["correlation_insights"] = []
    if dumped.get("dax_script"):
        dumped["dax_script"] = dumped["dax_script"][:1200]
    import json
    return json.dumps(dumped, separators=(",", ":"), default=str)[:9500]


def _choose_refinement_provider(iteration: int, role: str) -> str:
    """
    Round-robin rotate across configured, non-rate-limited providers (NVIDIA NIM, Groq, Gemini)
    to spread RPM/TPM load across providers during N-iteration refinement.
    """
    configured = get_configured_providers()
    if not configured:
        return "groq" if role == "critique" else "gemini"
    healthy = [p for p in configured if not is_provider_on_cooldown(p)]
    pool = healthy or configured
    offset = 0 if role == "critique" else 1
    return pool[(max(1, iteration) - 1 + offset) % len(pool)]


async def critique_plan_with_llm(
    plan: DashboardPlan,
    *,
    dataset_name: str,
    user_prompt: str,
    schema_summary: str,
    ground_truth_summary: str,
    deep_stats_summary: str,
    deterministic_score: float,
    deterministic_defects: List[str],
    iteration: int,
    max_iterations: int,
    provider: Optional[str] = None,
) -> Optional[ReportCritique]:
    resolved_provider = provider or _choose_refinement_provider(iteration, "critique")
    try:
        user_msg = build_peer_review_user_prompt(
            dataset_name=dataset_name,
            user_prompt=user_prompt,
            schema_summary=schema_summary,
            ground_truth_summary=ground_truth_summary,
            deep_stats_summary=deep_stats_summary,
            current_plan_json=_compact_plan_for_prompt(plan),
            deterministic_score=deterministic_score,
            deterministic_defects=deterministic_defects,
            iteration=iteration,
            max_iterations=max_iterations,
        )
        return await generate_structured(
            response_model=ReportCritique,
            system_prompt=PEER_REVIEW_SYSTEM_PROMPT,
            user_prompt=user_msg,
            provider=resolved_provider,
            max_retries=2,
            temperature=0.15,
            max_tokens=PEER_REVIEW_MAX_TOKENS,
        )
    except Exception as exc:
        logger.warning(f"Peer review critique LLM call failed on iteration {iteration}: {exc}")
        return None


async def rewrite_plan_with_llm(
    plan: DashboardPlan,
    *,
    dataset_name: str,
    user_prompt: str,
    schema_summary: str,
    ground_truth_summary: str,
    deep_stats_summary: str,
    critique_summary: str,
    iteration: int,
    max_iterations: int,
    provider: Optional[str] = None,
) -> Optional[DashboardPlan]:
    resolved_provider = provider or _choose_refinement_provider(iteration, "rewrite")
    try:
        user_msg = build_refinement_user_prompt(
            dataset_name=dataset_name,
            user_prompt=user_prompt,
            schema_summary=schema_summary,
            ground_truth_summary=ground_truth_summary,
            deep_stats_summary=deep_stats_summary,
            current_plan_json=_compact_plan_for_prompt(plan),
            critique_summary=critique_summary,
            iteration=iteration,
            max_iterations=max_iterations,
        )
        result = await generate_structured(
            response_model=LLMDashboardDraft,
            system_prompt=REFINEMENT_SYSTEM_PROMPT,
            user_prompt=user_msg,
            provider=resolved_provider,
            max_retries=2,
            temperature=0.2,
            max_tokens=DEEP_PLANNER_MAX_TOKENS,
        )
        if isinstance(result, DashboardPlan):
            return result
        return result.to_dashboard_plan()
    except Exception as exc:
        logger.warning(f"Refinement rewrite LLM call failed on iteration {iteration}: {exc}")
        return None


def enrich_plan_for_powerbi(
    plan: DashboardPlan,
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
) -> DashboardPlan:
    """
    Guarantees enterprise-grade Power BI DAX library, typed Power Query M,
    and 3-page Power BI layout blueprint on every DashboardPlan.
    """
    plan.dax_script = build_enterprise_dax_library(
        df=df,
        plan=plan,
        roles=roles,
        target_numerics=target_numerics,
        target_cats=target_cats,
    )
    if not plan.powerquery_m or "Table.TransformColumnTypes" not in plan.powerquery_m:
        plan.powerquery_m = build_enterprise_powerquery_m(
            df=df,
            roles=roles,
            dataset_name=plan.dataset_name,
        )
    plan.powerbi_pages = build_powerbi_pages_blueprint(
        plan=plan,
        roles=roles,
        target_numerics=target_numerics,
        target_cats=target_cats,
    )
    return plan


async def run_iterative_refinement_stream(
    initial_plan: DashboardPlan,
    *,
    df: pd.DataFrame,
    roles: Dict[str, Dict[str, Any]],
    target_numerics: List[str],
    target_cats: List[str],
    dataset_name: str,
    user_prompt: str,
    schema_summary: str,
    ground_truth_summary: str,
    deep_stats_summary: str,
    assemble_fn: Callable[[Optional[DashboardPlan]], DashboardPlan],
    max_iterations: int = DEFAULT_REFINEMENT_ITERATIONS,
    target_quality_score: float = DEFAULT_TARGET_QUALITY_SCORE,
    enable_llm_refinement: bool = True,
    participating_models: Optional[List[str]] = None,
) -> AsyncGenerator[Tuple[str, Any], None]:
    """
    Runs N iterations of Principal Peer Review + Max-Token Rewrite until the
    report achieves >= target_quality_score (Expert Certified) or completes N passes.

    Yields tuples of:
      ("status", {"stage": ..., "iteration": ..., "max_iterations": ..., "score": ..., "message": ...})
      ("done", final_DashboardPlan)
    """
    n_iters = max(1, min(MAX_REFINEMENT_ITERATIONS, int(max_iterations or 1)))
    current_plan = enrich_plan_for_powerbi(initial_plan, df, roles, target_numerics, target_cats)
    history: List[RefinementIterationRecord] = []
    final_score = 0.0

    for iteration in range(1, n_iters + 1):
        if enable_llm_refinement and iteration > 1 and len(get_configured_providers()) <= 1:
            # Gentle pacing when only a single provider is active to avoid per-second burst 429s
            await asyncio.sleep(0.5)

        det_score, det_rubric, det_defects = evaluate_plan_deterministic(current_plan, df, roles)

        llm_critique: Optional[ReportCritique] = None
        if enable_llm_refinement:
            critique_provider = _choose_refinement_provider(iteration, "critique")
            yield (
                "status",
                {
                    "stage": "peer_review",
                    "iteration": iteration,
                    "max_iterations": n_iters,
                    "score": det_score,
                    "message": f"Iteration {iteration}/{n_iters}: Principal Peer-Reviewer ({critique_provider}) auditing draft (baseline {det_score:.0f}/100)...",
                },
            )
            llm_critique = await critique_plan_with_llm(
                current_plan,
                dataset_name=dataset_name,
                user_prompt=user_prompt,
                schema_summary=schema_summary,
                ground_truth_summary=ground_truth_summary,
                deep_stats_summary=deep_stats_summary,
                deterministic_score=det_score,
                deterministic_defects=det_defects,
                iteration=iteration,
                max_iterations=n_iters,
                provider=critique_provider,
            )
            if llm_critique is not None and participating_models is not None:
                used_label = format_provider_model_label(get_last_provider_used() or critique_provider)
                if used_label not in participating_models:
                    participating_models.append(used_label)

        if llm_critique is not None:
            blended_rubric = {
                "empirical_grounding": round((det_rubric["empirical_grounding"] + llm_critique.empirical_grounding) / 2.0, 1),
                "executive_depth": round((det_rubric["executive_depth"] + llm_critique.executive_depth) / 2.0, 1),
                "statistical_rigor": round((det_rubric["statistical_rigor"] + llm_critique.statistical_rigor) / 2.0, 1),
                "visual_storytelling": round((det_rubric["visual_storytelling"] + llm_critique.visual_storytelling) / 2.0, 1),
                "powerbi_dax_readiness": round((det_rubric["powerbi_dax_readiness"] + llm_critique.powerbi_dax_readiness) / 2.0, 1),
                "actionability_roi": round((det_rubric["actionability_roi"] + llm_critique.actionability_roi) / 2.0, 1),
            }
            score = round((det_score * 0.4) + (llm_critique.overall_score * 0.6), 1)
            combined_critiques = list(dict.fromkeys(llm_critique.critical_defects + det_defects))[:8]
            upgrade_directives = list(
                dict.fromkeys(llm_critique.concrete_upgrade_directives + llm_critique.dax_and_powerbi_upgrades)
            )[:8]
        else:
            blended_rubric = det_rubric
            score = det_score
            combined_critiques = det_defects[:8]
            upgrade_directives = det_defects[:6]

        final_score = score
        certified = (score >= target_quality_score and det_score >= 88.0) or (not enable_llm_refinement and det_score >= target_quality_score)

        # If this is the final iteration OR report already passes the Principal bar, record & finish
        if certified or iteration >= n_iters or not enable_llm_refinement:
            history.append(
                RefinementIterationRecord(
                    iteration=iteration,
                    score=score,
                    rubric_scores=blended_rubric,
                    critiques_found=combined_critiques,
                    improvements_applied=(
                        ["Certified at Principal Analyst standard — enterprise Power BI DAX & 3-page layout finalized."]
                        if certified
                        else ["Completed configured refinement pass and finalized verified Power BI semantic model."]
                    ),
                    verdict="expert_certified" if certified else "needs_refinement",
                )
            )
            yield (
                "status",
                {
                    "stage": "refinement_complete",
                    "iteration": iteration,
                    "max_iterations": n_iters,
                    "score": score,
                    "message": (
                        f"Iteration {iteration}/{n_iters}: Report Expert Certified at {score:.1f}/100!"
                        if certified
                        else f"Iteration {iteration}/{n_iters}: Finalized Principal report (Score: {score:.1f}/100)."
                    ),
                },
            )
            break

        # Perform max-token rewrite addressing every critique
        yield (
            "status",
            {
                "stage": "refining_report",
                "iteration": iteration,
                "max_iterations": n_iters,
                "score": score,
                "message": (
                    f"Iteration {iteration}/{n_iters}: Score {score:.1f}/100 (< {target_quality_score:.0f}) — "
                    f"rewriting with 16K max tokens to fix {len(combined_critiques)} critique(s)..."
                ),
            },
        )

        critique_lines = [
            f"Current Score: {score:.1f}/100 (Target >= {target_quality_score:.0f}/100)",
            "Rubric Breakdown: " + ", ".join(f"{k}={v}" for k, v in blended_rubric.items()),
            "",
            "CRITICAL DEFECTS TO FIX:",
            *[f"- {c}" for c in combined_critiques],
            "",
            "CONCRETE UPGRADE DIRECTIVES:",
            *[f"- {u}" for u in upgrade_directives],
        ]
        rewrite_provider = _choose_refinement_provider(iteration, "rewrite")
        rewritten_raw = await rewrite_plan_with_llm(
            current_plan,
            dataset_name=dataset_name,
            user_prompt=user_prompt,
            schema_summary=schema_summary,
            ground_truth_summary=ground_truth_summary,
            deep_stats_summary=deep_stats_summary,
            critique_summary="\n".join(critique_lines),
            iteration=iteration + 1,
            max_iterations=n_iters,
            provider=rewrite_provider,
        )

        if rewritten_raw is not None:
            if participating_models is not None:
                used_label = format_provider_model_label(get_last_provider_used() or rewrite_provider)
                if used_label not in participating_models:
                    participating_models.append(used_label)
            current_plan = assemble_fn(rewritten_raw)
            current_plan = enrich_plan_for_powerbi(current_plan, df, roles, target_numerics, target_cats)
            applied = upgrade_directives[:5] or ["Deepened SCR narrative, KPI quantification, visual insights, and DAX measures."]
        else:
            applied = ["Retained verified ground-truth draft after LLM rewrite fallback; applied deterministic DAX & Power BI upgrades."]

        history.append(
            RefinementIterationRecord(
                iteration=iteration,
                score=score,
                rubric_scores=blended_rubric,
                critiques_found=combined_critiques,
                improvements_applied=applied,
                verdict="needs_refinement",
            )
        )

    current_plan.quality_score = final_score
    current_plan.refinement_iterations_run = len(history)
    current_plan.refinement_history = history
    yield ("done", current_plan)
