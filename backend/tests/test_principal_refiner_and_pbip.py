# backend/tests/test_principal_refiner_and_pbip.py
"""
Deterministic tests for the N-Iteration Principal Data Analyst Refinement Engine
and the 3-Page Executive Power BI (.pbip) Exporter.
"""
import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.modules.data_analyst.analyst import _heuristic_fallback_dashboard, generate_complete_dashboard
from app.modules.data_analyst.export_powerbi import (
    THEME_FILENAME,
    _infer_csv_columns_and_types,
    generate_powerbi_pbip_archive,
)
from app.modules.data_analyst.profiler import classify_dataframe_roles
from app.modules.data_analyst.refiner import (
    build_enterprise_dax_library,
    build_enterprise_powerquery_m,
    evaluate_plan_deterministic,
    run_iterative_refinement_stream,
)
from app.modules.data_analyst.schemas import (
    ChartVisualSpec,
    DashboardPlan,
    ExecutiveDossier,
    KPISpec,
    ReportCritique,
)


SAMPLE_CSV = (
    "date,region,segment,revenue,cost,customers,churn_rate\n"
    "2026-01-01,North,Enterprise,42000,14000,45,0.018\n"
    "2026-02-01,North,Pro,18500,6200,130,0.032\n"
    "2026-03-01,South,Starter,7800,3900,98,0.078\n"
    "2026-04-01,West,Enterprise,51000,15200,52,0.014\n"
    "2026-05-01,East,Pro,21200,7100,148,0.029\n"
    "2026-06-01,West,Enterprise,54800,16000,56,0.011\n"
    "2026-07-01,South,Starter,7200,4100,90,0.084\n"
    "2026-08-01,North,Enterprise,46500,14600,49,0.016\n"
    "2026-09-01,East,Pro,22900,7400,155,0.027\n"
    "2026-10-01,West,Enterprise,61500,17500,62,0.010\n"
)


def test_deterministic_evaluator_penalizes_shallow_draft_and_rewards_enriched_plan():
    df = pd.read_csv(io.StringIO(SAMPLE_CSV))
    roles = classify_dataframe_roles(df)

    shallow = DashboardPlan(
        title="Basic Report",
        summary="This shows sales.",
        dataset_name="sales.csv",
        kpis=[
            KPISpec(
                id="k1",
                title="Total Revenue",
                value="$100",
                formula_dax="Total Revenue = SUM('Dataset'[nonexistent_col])",
                formula_tableau="SUM([revenue])",
                rationale="basic",
            )
        ],
        visuals=[
            ChartVisualSpec(
                id="v1",
                title="Chart",
                chart_type="bar",
                x_axis="region",
                y_axis="revenue",
                aggregation="sum",
                description="bar",
            )
        ],
        dossier=ExecutiveDossier(
            executive_verdict="Things look okay.",
            situation="We have data.",
            complication="Some risk.",
            resolution="Do better.",
            data_integrity_score=95.0,
        ),
    )

    shallow_score, _, shallow_defects = evaluate_plan_deterministic(shallow, df, roles)
    assert shallow_score < 65.0
    assert any("unknown column" in d.lower() for d in shallow_defects)
    assert any("kpi" in d.lower() for d in shallow_defects)

    rich = _heuristic_fallback_dashboard(
        df=df,
        user_prompt="Analyze regional revenue, churn risk, and enterprise margins",
        dataset_name="sales.csv",
        target_numerics=["revenue", "cost", "churn_rate"],
        target_cats=["region", "segment"],
        intent="general_executive",
        roles=roles,
        anomalies=[],
    )
    rich.dax_script = build_enterprise_dax_library(df, rich, roles, ["revenue", "cost"], ["region", "segment"])
    rich.powerquery_m = build_enterprise_powerquery_m(df, roles, "sales.csv")

    rich_score, rich_rubric, _ = evaluate_plan_deterministic(rich, df, roles)
    assert rich_score > shallow_score + 20.0
    assert rich_rubric["powerbi_dax_readiness"] >= 90.0


@pytest.mark.asyncio
async def test_iterative_refinement_loop_runs_multiple_passes_until_expert_certified():
    df = pd.read_csv(io.StringIO(SAMPLE_CSV))
    roles = classify_dataframe_roles(df)
    base_plan = _heuristic_fallback_dashboard(
        df=df,
        user_prompt="Executive revenue & churn analysis",
        dataset_name="sales.csv",
        target_numerics=["revenue", "cost", "churn_rate"],
        target_cats=["region", "segment"],
        intent="general_executive",
        roles=roles,
        anomalies=[],
    )

    critiques = [
        ReportCritique(
            overall_score=74.0,
            empirical_grounding=76.0,
            executive_depth=70.0,
            statistical_rigor=75.0,
            visual_storytelling=72.0,
            powerbi_dax_readiness=78.0,
            actionability_roi=73.0,
            critical_defects=["Add 5th KPI and quantify regional EBITDA spread."],
            concrete_upgrade_directives=["Quantify West vs South cohort spread in SCR."],
            dax_and_powerbi_upgrades=["Add Pareto cumulative % and RANKX cohort rank."],
            passes_principal_bar=False,
        ),
        ReportCritique(
            overall_score=96.0,
            empirical_grounding=96.0,
            executive_depth=95.0,
            statistical_rigor=97.0,
            visual_storytelling=95.0,
            powerbi_dax_readiness=98.0,
            actionability_roi=95.0,
            critical_defects=[],
            concrete_upgrade_directives=[],
            dax_and_powerbi_upgrades=[],
            passes_principal_bar=True,
        ),
    ]

    upgraded_plan = base_plan.model_copy(deep=True)
    upgraded_plan.title = "Principal Executive Revenue & Churn Forensics (Refined)"
    upgraded_plan.kpis.append(
        KPISpec(
            id="kpi_5",
            title="Median Regional Revenue",
            value="$32,450",
            change="+14.2% vs Q1",
            trend="up",
            benchmark="Portfolio P50: $32.5K",
            variance="+14.2%",
            executive_takeaway="Median revenue outperforms Starter tier by 4.2x, confirming Enterprise expansion priority.",
            formula_dax="Median Regional Revenue = MEDIANX('Dataset', 'Dataset'[revenue])",
            formula_tableau="MEDIAN([revenue])",
            rationale="Non-parametric central tendency immune to fat-tail distortion.",
        )
    )
    if upgraded_plan.dossier:
        upgraded_plan.dossier.executive_verdict = (
            "Across 10 validated observations ($333,500 total revenue, median $32,450, IQR $19,175–$49,875), "
            "West Enterprise cohorts generate 50.2% of revenue at 1.2% churn while South Starter suffers 8.1% churn; "
            "reallocate Q4 expansion budget to Enterprise while executing immediate 30-day Starter retention triage."
        )
        upgraded_plan.dossier.situation = (
            "Dataset spans 10 monthly regional cohort records with 100.0% completeness and zero duplicate rows. "
            "Total revenue stands at $333,500 (mean $33,350 vs median $32,450, skew +0.18) with total operating cost of $106,000, "
            "yielding a 68.2% gross margin across North, West, East, and South territories."
        )
        upgraded_plan.dossier.complication = (
            "Severe cohort bifurcation drives portfolio variance (ANOVA eta-squared = 0.89): West Enterprise averages $55,767 "
            "at 1.17% churn whereas South Starter averages $7,500 with 8.10% churn (6.9x higher attrition). "
            "Concentration analysis indicates elevated Pareto share across top Enterprise accounts and 1.5xIQR tail dispersion."
        )
        upgraded_plan.dossier.resolution = (
            "Execute a 3-horizon operating plan: (1) Launch 0-30d Starter churn intervention targeting South accounts to recover +$42K ARR; "
            "(2) Scale Enterprise outbound playbook across West and North cohorts for +$120K incremental margin; "
            "(3) Deploy 3-page Power BI semantic model with live RANKX, median/P95 guardrails, and Tukey outlier alerts."
        )
        # Ensure >= 4 initiatives and >= 3 risks for high deterministic score
        while len(upgraded_plan.dossier.strategic_initiatives) < 4:
            upgraded_plan.dossier.strategic_initiatives.append(upgraded_plan.dossier.strategic_initiatives[0].model_copy())
        while len(upgraded_plan.dossier.risk_matrix) < 3:
            upgraded_plan.dossier.risk_matrix.append(upgraded_plan.dossier.risk_matrix[0].model_copy())

    statuses = []
    final_plan = None
    with patch("app.modules.data_analyst.refiner.critique_plan_with_llm", new=AsyncMock(side_effect=critiques)) as mock_crit, \
         patch("app.modules.data_analyst.refiner.rewrite_plan_with_llm", new=AsyncMock(return_value=upgraded_plan)) as mock_rew:
        async for evt, payload in run_iterative_refinement_stream(
            base_plan,
            df=df,
            roles=roles,
            target_numerics=["revenue", "cost", "churn_rate"],
            target_cats=["region", "segment"],
            dataset_name="sales.csv",
            user_prompt="Executive revenue & churn analysis",
            schema_summary="- revenue\n- region",
            ground_truth_summary="Total revenue = $333,500",
            deep_stats_summary="ANOVA eta2=0.89",
            assemble_fn=lambda p: p or base_plan,
            max_iterations=5,
            target_quality_score=90.0,
            enable_llm_refinement=True,
        ):
            if evt == "status":
                statuses.append(payload)
            elif evt == "done":
                final_plan = payload

    assert final_plan is not None
    assert mock_crit.await_count == 2  # Stopped early on Pass 2 once certified!
    assert mock_rew.await_count == 1
    assert final_plan.refinement_iterations_run == 2
    assert len(final_plan.refinement_history) == 2
    assert final_plan.refinement_history[0].verdict == "needs_refinement"
    assert final_plan.refinement_history[1].verdict == "expert_certified"
    assert (final_plan.quality_score or 0) >= 90.0
    assert len(final_plan.powerbi_pages) == 3
    assert any(s.get("stage") == "refinement_complete" for s in statuses)


@pytest.mark.asyncio
async def test_three_page_executive_powerbi_pbip_archive_structure():
    with patch("app.modules.data_analyst.analyst.call_llm_dashboard_planner", new=AsyncMock(return_value=None)):
        plan = await generate_complete_dashboard(
            csv_text=SAMPLE_CSV,
            user_prompt="Principal executive audit of revenue, cost, and churn by region and segment",
            dataset_name="enterprise_sales.csv",
            refinement_iterations=2,
        )

    assert len(plan.powerbi_pages) == 3
    assert plan.quality_score is not None

    cols = _infer_csv_columns_and_types(SAMPLE_CSV)
    col_types = {c["name"]: c["dataType"] for c in cols}
    assert col_types["date"] == "dateTime"
    assert col_types["revenue"] == "int64"
    assert col_types["churn_rate"] == "double"
    assert col_types["region"] == "string"

    archive = generate_powerbi_pbip_archive(plan, SAMPLE_CSV, filename_base="Enterprise_Sales")
    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
        expected = {
            "Enterprise_Sales.pbip",
            "Enterprise_Sales.Report/definition.pbir",
            "Enterprise_Sales.Report/report.json",
            f"Enterprise_Sales.Report/StaticResources/RegisteredResources/{THEME_FILENAME}",
            "Enterprise_Sales.Dataset/definition.pbidataset",
            "Enterprise_Sales.Dataset/model.bim",
            "Enterprise_Sales.Dataset/dataset.csv",
            "Executive_Analyst_Dossier.md",
            "DAX_Measures_Library.dax",
            "PowerBI_Setup_Guide.txt",
        }
        assert expected.issubset(names), f"Missing archive entries: {expected - names}"

        # Validate 3-page executive report.json + custom theme registration
        report = json.loads(zf.read("Enterprise_Sales.Report/report.json"))
        sections = report["sections"]
        assert len(sections) == 3
        assert [s["displayName"] for s in sections] == [
            "Executive Overview",
            "Statistical & Cohort Diagnostics",
            "Risk, Anomalies & Action Playbook",
        ]
        cfg = json.loads(report["config"])
        assert cfg["themeCollection"]["customTheme"]["name"] == THEME_FILENAME

        # Verify slicers, KPI cards, cohort tableEx, and executive narrative textboxes exist
        all_visual_types = set()
        for sec in sections:
            for vc in sec["visualContainers"]:
                vcfg = json.loads(vc["config"])
                all_visual_types.add(vcfg["singleVisual"]["visualType"])
        assert {"textbox", "slicer", "card", "tableEx"}.issubset(all_visual_types)

        # Validate enterprise model.bim semantic model
        model = json.loads(zf.read("Enterprise_Sales.Dataset/model.bim"))
        assert model["compatibilityLevel"] == 1567
        ds_table = model["model"]["tables"][0]
        measures = ds_table["measures"]
        assert len(measures) >= 10
        folders = {m.get("displayFolder") for m in measures}
        assert "01 · Executive KPIs" in folders
        assert "02 · Statistical & Distribution" in folders
        assert "03 · Cohort & Concentration" in folders
        assert "04 · Time Intelligence" in folders
        assert all(m.get("formatString") for m in measures)

        # Validate handover docs
        dossier_md = zf.read("Executive_Analyst_Dossier.md").decode("utf-8")
        assert "EXECUTIVE INTELLIGENCE DOSSIER" in dossier_md
        dax_lib = zf.read("DAX_Measures_Library.dax").decode("utf-8")
        assert "01 · Executive KPIs" in dax_lib
        assert "PERCENTILEX.INC" in dax_lib
