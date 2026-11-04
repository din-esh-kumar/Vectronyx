# backend/tests/test_data_analyst_prompt_driven.py
import pytest
import pandas as pd
import io

from app.modules.data_analyst.analyst import (
    resolve_prompt_intent_and_columns,
    compute_ground_truth_context,
    reconcile_kpi_ground_truth,
    calculate_concentration_analysis,
    calculate_statistical_diagnostics,
    compute_visual_series_data,
    _heuristic_fallback_dashboard,
    generate_complete_dashboard,
)
from app.modules.data_analyst.schemas import (
    DashboardPlan,
    KPISpec,
    ChartVisualSpec,
)

SAAS_CSV = """Region,Category,Revenue,Profit,Transactions,ChurnRate
North America,Enterprise Cloud,245000,78000,124,0.04
Europe,Enterprise Cloud,189000,56000,98,0.05
Asia Pacific,AI Workspaces,142000,41000,82,0.08
Latin America,Developer Tools,48000,12500,45,0.12
North America,Developer Tools,85000,24000,110,0.06
Europe,AI Workspaces,112000,34000,74,0.07
Middle East,Enterprise Cloud,96000,29000,38,0.09
North America,AI Workspaces,165000,52000,95,0.05
Europe,Developer Tools,62000,18000,68,0.08
Asia Pacific,Enterprise Cloud,135000,39000,71,0.07
"""

FINTECH_CSV = """Corridor,PaymentType,GrossVolume,NetFee,SettlementDays,ChargebackRate
US-EU,Cross-Border Treasury,4200000,126000,1,0.0008
APAC-US,E-Commerce Settlement,2850000,99750,2,0.0024
LATAM-US,Remittance Flow,980000,34300,3,0.0115
EMEA-APAC,Corporate Liquidity,1650000,49500,1,0.0012
US-APAC,SaaS Subscription,2100000,73500,2,0.0032
"""


def test_resolve_prompt_intent_and_columns_risk_churn():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    prompt = "Diagnose customer churn rate across regions and identify high-risk cohort leakage"
    target_numerics, target_cats, intent = resolve_prompt_intent_and_columns(df, prompt)

    assert "ChurnRate" in target_numerics
    # ChurnRate should be prioritized at the front
    assert target_numerics[0] == "ChurnRate"
    assert "Region" in target_cats
    assert target_cats[0] == "Region"
    assert intent == "risk_and_churn"


def test_resolve_prompt_intent_and_columns_unit_economics():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    prompt = "Evaluate unit economics: analyze category profit margin and transaction efficiency"
    target_numerics, target_cats, intent = resolve_prompt_intent_and_columns(df, prompt)

    assert target_cats[0] == "Category"
    assert intent == "unit_economics"
    assert "Profit" in target_numerics or "Transactions" in target_numerics


def test_resolve_prompt_intent_and_columns_fintech():
    df = pd.read_csv(io.StringIO(FINTECH_CSV))
    prompt = "Analyze corridor chargeback rate and payment type net fee take-rate efficiency"
    target_numerics, target_cats, intent = resolve_prompt_intent_and_columns(df, prompt)

    assert "ChargebackRate" in target_numerics
    assert "NetFee" in target_numerics
    assert "Corridor" in target_cats or "PaymentType" in target_cats


def test_compute_ground_truth_context():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    metrics, summary_text = compute_ground_truth_context(df, ["Revenue", "ChurnRate"], ["Region"])

    assert "Revenue" in metrics
    assert "ChurnRate" in metrics
    assert metrics["Revenue"]["total"] == float(df["Revenue"].sum())
    assert metrics["ChurnRate"]["mean"] == round(float(df["ChurnRate"].mean()), 4) or round(float(df["ChurnRate"].mean()), 2)
    assert "Top Region cohorts for Revenue" in summary_text


def test_dynamic_concentration_analysis_on_prompt_dimensions():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    # When user asks about ChurnRate by Category
    conc = calculate_concentration_analysis(df, ["Category"], ["ChurnRate"])
    assert conc is not None
    assert conc.dimension == "Category"
    assert conc.metric == "ChurnRate"
    assert conc.hhi_index > 0


def test_reconcile_kpi_ground_truth():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    metrics, _ = compute_ground_truth_context(df, ["Revenue", "ChurnRate"], ["Region"])

    mock_kpis = [
        KPISpec(
            id="kpi_1",
            title="Total Revenue",
            value="$1,245,000",  # Placeholder hallucinated value
            formula_dax="Total Revenue = SUM('Dataset'[Revenue])",
            formula_tableau="SUM([Revenue])",
            rationale="Baseline revenue",
        ),
        KPISpec(
            id="kpi_2",
            title="Average Churn Rate",
            value="+14.2% YoY",  # Generic placeholder
            formula_dax="Avg Churn = AVERAGE('Dataset'[ChurnRate])",
            formula_tableau="AVG([ChurnRate])",
            rationale="Attrition hurdle",
        ),
    ]

    reconciled = reconcile_kpi_ground_truth(df, mock_kpis, metrics)
    total_rev = df["Revenue"].sum()
    mean_churn = df["ChurnRate"].mean()

    # Should be replaced by real ground truth
    assert f"${total_rev / 1e6:.2f}M" in reconciled[0].value or f"${total_rev:,.2f}" in reconciled[0].value
    assert f"{mean_churn * 100:.2f}%" in reconciled[1].value


def test_compute_visual_series_data_fuzzy_matching():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    # Casing mismatch test: "region" and "churnrate"
    vis = ChartVisualSpec(
        id="vis_test",
        title="Regional Churn",
        chart_type="bar",
        x_axis="region",  # Lowercase
        y_axis="churnrate",  # Lowercase
        aggregation="avg",
        description="Fuzzy match test",
    )

    data = compute_visual_series_data(df, vis)
    assert len(data) > 0
    assert vis.x_axis == "Region"
    assert vis.y_axis == "ChurnRate"


def test_heuristic_fallback_dashboard_prompt_conditioned():
    df = pd.read_csv(io.StringIO(SAAS_CSV))
    prompt = "Diagnose churn rate leakage and customer tier risk across regions"
    plan = _heuristic_fallback_dashboard(df, prompt, "saas_enterprise_q3.csv")

    assert plan.analytical_intent == "risk_and_churn"
    assert plan.focused_metrics[0] == "ChurnRate"
    assert plan.focused_dimensions[0] == "Region"
    assert len(plan.kpis) >= 4
    # The first KPI should focus on ChurnRate exposure
    assert "ChurnRate" in plan.kpis[0].title
    assert "%" in plan.kpis[0].value
    assert plan.dossier is not None
    assert "ChurnRate" in plan.dossier.situation


@pytest.mark.asyncio
async def test_generate_complete_dashboard_end_to_end():
    prompt = "Evaluate unit economics: identify which category delivers highest profit margin"
    plan = await generate_complete_dashboard(SAAS_CSV, prompt, "saas.csv")

    assert isinstance(plan, DashboardPlan)
    assert plan.analytical_intent == "unit_economics"
    assert len(plan.visuals) > 0
    assert len(plan.kpis) >= 4
    # Visuals should have populated series data
    assert len(plan.visuals[0].series_data) > 0

