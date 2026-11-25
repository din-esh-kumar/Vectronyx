# backend/tests/test_data_cleansing_and_ds.py
import io
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.modules.data_analyst import analyst as analyst_mod
from app.modules.data_analyst.data_cleaner import (
    clean_and_deduplicate_dataset,
    run_dynamic_data_science_pipeline,
)
from app.modules.data_analyst.profiler import classify_dataframe_roles
from app.modules.data_analyst.schemas import (
    ChartVisualSpec,
    DashboardPlan,
    KPISpec,
    LLMDataScienceSynthesis,
    ReportCritique,
)

MESSY_CSV = """Unnamed: 0,Region,ConstantFlag,Revenue,Revenue_Mirror,Profit,Cost,ChurnRate
0,  north america ,ACTIVE,"$245,000","$245,000",78000,167000,4.0%
1,Europe,ACTIVE,"$189,000","$189,000",56000,133000,5.0%
1,Europe,ACTIVE,"$189,000","$189,000",56000,133000,5.0%
2,North America,ACTIVE,"$165,000","$165,000",52000,113000,5.0%
3,Asia Pacific,ACTIVE,"$142,000","$142,000",41000,101000,8.0%
4,Latin America,ACTIVE,N/A,N/A,12500,35500,12.0%
5,Middle East,ACTIVE,"$96,000","$96,000",29000,67000,-
6,Europe,ACTIVE,"$112,000","$112,000",34000,78000,7.0%
7,Asia Pacific,ACTIVE,"$135,000","$135,000",39000,96000,7.0%
8,North America,ACTIVE,"$85,000","$85,000",24000,61000,6.0%
9,Europe,ACTIVE,"$62,000","$62,000",18000,44000,8.0%
"""


def test_clean_and_deduplicate_messy_dataset():
    raw_df = pd.read_csv(io.StringIO(MESSY_CSV))
    cleaned_df, report = clean_and_deduplicate_dataset(raw_df)

    # Exact duplicate row removed
    assert report.raw_rows == 11
    assert report.cleaned_rows == 10
    assert report.duplicates_removed == 1

    # Unnamed: 0, ConstantFlag, and Revenue_Mirror dropped
    assert "Unnamed: 0" not in cleaned_df.columns
    assert "ConstantFlag" not in cleaned_df.columns
    assert "Revenue_Mirror" not in cleaned_df.columns
    assert report.columns_dropped >= 3

    # Currency & percentage coerced to numeric and missing tokens imputed
    assert pd.api.types.is_numeric_dtype(cleaned_df["Revenue"])
    assert pd.api.types.is_numeric_dtype(cleaned_df["ChurnRate"])
    assert cleaned_df.isna().sum().sum() == 0
    assert report.missing_values_imputed >= 2

    # Inconsistent casing merged ("  north america " -> "North America")
    assert cleaned_df["Region"].nunique() == 5
    assert "North America" in set(cleaned_df["Region"])
    assert report.integrity_after >= report.integrity_before


def test_dynamic_data_science_pipeline_outputs_ml_metrics():
    raw_df = pd.read_csv(io.StringIO(MESSY_CSV))
    cleaned_df, report = clean_and_deduplicate_dataset(raw_df)
    roles = classify_dataframe_roles(cleaned_df)
    ds_summary, ds_brief = run_dynamic_data_science_pipeline(
        cleaned_df,
        roles,
        target_numerics=["Revenue", "Profit"],
        collinear_pruned=report.collinear_features_pruned,
    )

    assert ds_summary.target_metric == "Revenue"
    assert ds_summary.optimal_clusters >= 2
    assert ds_summary.silhouette_score is not None
    assert len(ds_summary.pca_variance_explained_pct) >= 1
    assert len(ds_summary.top_feature_importances) >= 1
    assert ds_summary.r2_score is not None
    assert "RandomForestRegressor" in ds_brief


@pytest.mark.asyncio
async def test_dual_model_groq_and_gemini_orchestration(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(analyst_mod.settings, "GROQ_API_KEY", "gsk_test_dummy_123456")
    monkeypatch.setattr(analyst_mod.settings, "GEMINI_API_KEY", "AIzaSyTestDummyKey123456")

    seen_providers: list[str] = []

    async def fake_generate_structured(*, response_model, provider=None, **kwargs):
        seen_providers.append(provider or "default")
        if response_model is LLMDataScienceSynthesis:
            return LLMDataScienceSynthesis(
                cleansing_assessment="Removed 1 duplicate row and 3 redundant columns.",
                feature_engineering_recommendations=["Use Revenue/Cost spread ratio."],
                cluster_interpretations=["High-Revenue cohort leads portfolio margin."],
                predictive_driver_takeaway="Profit and Cost explain primary variance.",
            )
        if response_model is ReportCritique:
            return ReportCritique(
                overall_score=95.0,
                empirical_grounding=95.0,
                executive_depth=94.0,
                statistical_rigor=95.0,
                visual_storytelling=94.0,
                powerbi_dax_readiness=95.0,
                actionability_roi=94.0,
                passes_principal_bar=True,
            )
        return DashboardPlan(
            title="Cleansed Executive Report",
            summary="Full dual-model report.",
            dataset_name="messy.csv",
            kpis=[
                KPISpec(
                    id="kpi_1",
                    title="Total Revenue",
                    value="$1.2M",
                    formula_dax="Total Revenue = SUM('Dataset'[Revenue])",
                    formula_tableau="SUM([Revenue])",
                    rationale="Primary revenue metric",
                )
            ],
            visuals=[
                ChartVisualSpec(
                    id="vis_1",
                    title="Revenue by Region",
                    chart_type="bar",
                    x_axis="Region",
                    y_axis="Revenue",
                    aggregation="sum",
                    description="Regional breakdown",
                )
            ],
        )

    with (
        patch("app.modules.data_analyst.analyst.generate_structured", side_effect=fake_generate_structured),
        patch("app.modules.data_analyst.refiner.generate_structured", side_effect=fake_generate_structured),
    ):
        plan = await analyst_mod.generate_complete_dashboard(
            csv_text=MESSY_CSV,
            user_prompt="Analyze revenue drivers and churn cohorts",
            dataset_name="messy.csv",
            refinement_iterations=1,
        )

    assert "groq" in seen_providers
    assert "gemini" in seen_providers
    assert plan.cleansing_report is not None
    assert plan.cleansing_report.duplicates_removed == 1
    assert plan.data_science_summary is not None
    assert "Removed 1 duplicate row" in plan.data_science_summary.ai_data_science_verdict
    assert any(m.startswith("groq/") for m in plan.models_used)
    assert any(m.startswith("gemini/") for m in plan.models_used)
