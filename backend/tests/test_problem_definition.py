# backend/tests/test_problem_definition.py
import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.modules.data_analyst import analyst as analyst_mod
from app.modules.data_analyst import problem_definer as pd_mod
from app.modules.data_analyst.problem_definer import (
    _LLMProblemDefinitionDraft,
    build_static_problem_definition,
    define_problem_and_align_metrics,
    verify_and_define_dataset,
    verify_dataset_readiness,
)
from app.modules.data_analyst.schemas import (
    AlignedMetricSpec,
    ChartVisualSpec,
    DashboardPlan,
    KPISpec,
    LLMDataScienceSynthesis,
    ReportCritique,
    StakeholderAlignment,
)

PERFECT_SAAS_CSV = """Region,Category,Revenue,Profit,Transactions,ChurnRate
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

UNUSABLE_TEXT_ONLY_CSV = """id,name,notes
1,Alpha,good
2,Beta,pending
3,Gamma,done
4,Delta,review
"""


def test_verify_perfect_dataset_passes_all_checks():
    verification, df, report, roles = verify_dataset_readiness(PERFECT_SAAS_CSV, "saas.csv")
    assert verification.status == "perfect"
    assert verification.is_good_dataset is True
    assert verification.readiness_score >= 95.0
    assert verification.blocking_issues == []
    assert "Revenue" in verification.numeric_metrics
    assert "Region" in verification.categorical_dimensions
    assert df is not None and report is not None and roles is not None


def test_verify_unusable_dataset_blocks_problem_definition():
    verification, _, _, _ = verify_dataset_readiness(UNUSABLE_TEXT_ONLY_CSV, "text_only.csv")
    assert verification.status == "unusable"
    assert verification.is_good_dataset is False
    assert len(verification.blocking_issues) >= 1


@pytest.mark.asyncio
async def test_verify_and_define_skips_problem_definition_when_dataset_bad():
    intake = await verify_and_define_dataset("Region,Revenue\nNorth,100\n", "too_small.csv")
    assert intake.verification.is_good_dataset is False
    assert intake.verification.status == "unusable"
    assert intake.problem_definition is None


@pytest.mark.asyncio
async def test_define_problem_blocks_directly_if_verification_failed():
    verification, df, _, roles = verify_dataset_readiness("Region,Revenue\nNorth,100\n", "tiny.csv")
    assert verification.is_good_dataset is False
    assert df is not None and roles is not None
    with pytest.raises(ValueError, match="failed verification"):
        await define_problem_and_align_metrics(df, roles, verification, "tiny.csv")


@pytest.mark.asyncio
async def test_verify_and_define_produces_aligned_metrics_and_stakeholders():
    intake = await verify_and_define_dataset(PERFECT_SAAS_CSV, "saas.csv")
    assert intake.verification.is_good_dataset is True
    assert intake.problem_definition is not None

    pd_res = intake.problem_definition
    assert "Revenue" in pd_res.core_question
    assert len(pd_res.stakeholders) >= 2
    assert len(pd_res.aligned_metrics) >= 3
    churn_spec = next((m for m in pd_res.aligned_metrics if m.metric_name == "ChurnRate"), None)
    assert churn_spec is not None
    assert churn_spec.role == "Guardrail"
    assert "never SUM" in churn_spec.aggregation
    assert pd_res.recommended_analysis_prompt


def test_verify_and_define_api_endpoint_e2e():
    client = TestClient(app)
    res_good = client.post(
        "/api/analyst/verify-and-define",
        data={"raw_csv": PERFECT_SAAS_CSV, "dataset_name": "saas.csv", "user_goal": "Reduce regional churn"},
    )
    assert res_good.status_code == 200
    body_good = res_good.json()
    assert body_good["verification"]["status"] == "perfect"
    assert body_good["verification"]["is_good_dataset"] is True
    assert body_good["problem_definition"] is not None
    assert "Reduce regional churn" in body_good["problem_definition"]["core_question"]

    res_bad = client.post(
        "/api/analyst/verify-and-define",
        data={"raw_csv": UNUSABLE_TEXT_ONLY_CSV, "dataset_name": "text_only.csv"},
    )
    assert res_bad.status_code == 200
    body_bad = res_bad.json()
    assert body_bad["verification"]["is_good_dataset"] is False
    assert body_bad["problem_definition"] is None


def test_static_problem_definition_extracts_empirical_signals_and_goal_focus():
    verification, df, _, roles = verify_dataset_readiness(PERFECT_SAAS_CSV, "saas.csv")
    assert verification.is_good_dataset and df is not None and roles is not None

    static_def = build_static_problem_definition(
        df=df,
        roles=roles,
        verification=verification,
        dataset_name="saas.csv",
        user_goal="Reduce ChurnRate across Category",
    )
    assert static_def.synthesis_mode == "static_only"
    assert "static-code" in static_def.ai_provider_used
    assert len(static_def.static_signals) >= 3
    assert any("North Star" in s for s in static_def.static_signals)
    assert any("Cohort Gap" in s or "Driver Correlation" in s for s in static_def.static_signals)
    assert "Category" in static_def.core_question


@pytest.mark.asyncio
async def test_hybrid_static_and_ai_problem_definition_fuses_signals_and_enforces_guardrails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pd_mod, "get_configured_providers", lambda: ["groq"])
    verification, df, _, roles = verify_dataset_readiness(PERFECT_SAAS_CSV, "saas.csv")
    assert verification.is_good_dataset and df is not None and roles is not None

    captured_prompts: list[str] = []

    async def fake_llm(*, response_model, user_prompt: str, **kwargs):
        captured_prompts.append(user_prompt)
        return _LLMProblemDefinitionDraft(
            core_question="Which SaaS regions and product tiers drive net Revenue expansion without elevating ChurnRate?",
            business_goal="Grow North America and Europe ARR while capping ChurnRate below P95.",
            decision_needed="Reallocate GTM budget toward Enterprise Cloud and remediate Latin America churn.",
            stakeholders=[
                StakeholderAlignment(
                    stakeholder_role="Chief Revenue Officer",
                    primary_concern="Protect Enterprise Cloud expansion while diversifying beyond top region.",
                    target_metrics=["Revenue", "Region", "NonExistentCol"],
                ),
                StakeholderAlignment(
                    stakeholder_role="VP Customer Success",
                    primary_concern="Contain ChurnRate in Developer Tools cohort.",
                    target_metrics=["ChurnRate", "Category"],
                ),
            ],
            aligned_metrics=[
                AlignedMetricSpec(
                    metric_name="Revenue",
                    role="North Star",
                    aggregation="SUM & Regional Share %",
                    stakeholder_alignment="Primary top-line growth KPI.",
                ),
                AlignedMetricSpec(
                    metric_name="ChurnRate",
                    role="Guardrail",
                    aggregation="SUM(ChurnRate)",  # Deliberately unsafe aggregation to test static code guardrail
                    stakeholder_alignment="Retention risk threshold.",
                ),
                AlignedMetricSpec(
                    metric_name="FakeColumn",
                    role="Driver",
                    aggregation="SUM",
                    stakeholder_alignment="Hallucinated metric.",
                ),
            ],
            clarifying_questions=["What is the maximum acceptable ChurnRate for Developer Tools?"],
            recommended_analysis_prompt="Analyze saas.csv Revenue growth vs ChurnRate across Region and Category.",
        )

    result = await define_problem_and_align_metrics(
        df=df,
        roles=roles,
        verification=verification,
        dataset_name="saas.csv",
        user_goal="Reduce regional churn",
        generate_fn=fake_llm,
    )

    assert len(captured_prompts) == 1
    # Verify AI received static code empirical signals and static baseline framing
    assert "Static Code Empirical Signals:" in captured_prompts[0]
    assert "Static Code Baseline Problem Framing:" in captured_prompts[0]
    assert result.synthesis_mode == "static_and_ai"
    assert result.ai_provider_used.startswith("static-code + ")
    assert len(result.static_signals) >= 3
    assert "Reduce regional churn" in result.core_question

    metric_names = [m.metric_name for m in result.aligned_metrics]
    assert "FakeColumn" not in metric_names
    assert "Region" in metric_names  # Preserved from static code understanding
    churn_spec = next(m for m in result.aligned_metrics if m.metric_name == "ChurnRate")
    assert "never SUM" in churn_spec.aggregation  # Unsafe AI SUM overridden by static guardrail
    cro = next(s for s in result.stakeholders if s.stakeholder_role == "Chief Revenue Officer")
    assert "NonExistentCol" not in cro.target_metrics


@pytest.mark.asyncio
async def test_generate_complete_dashboard_uses_hybrid_static_and_ai_problem_definition(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(analyst_mod.settings, "GROQ_API_KEY", "gsk_test_dummy_123456")
    monkeypatch.setattr(analyst_mod.settings, "GEMINI_API_KEY", "AIzaSyTestDummyKey123456")
    monkeypatch.setattr(pd_mod, "get_configured_providers", lambda: ["groq", "gemini"])

    planner_prompts: list[str] = []

    async def fake_generate_structured(*, response_model, user_prompt="", **kwargs):
        if response_model is _LLMProblemDefinitionDraft:
            return _LLMProblemDefinitionDraft(
                core_question="How can SaaS leadership expand Revenue across Regions while capping ChurnRate?",
                business_goal="Scale Enterprise Cloud Revenue without increasing ChurnRate tail risk.",
                decision_needed="Shift expansion budget to high-yield cohorts and target Developer Tools retention.",
                stakeholders=[
                    StakeholderAlignment(
                        stakeholder_role="CRO",
                        primary_concern="Revenue growth & cohort concentration.",
                        target_metrics=["Revenue", "Region"],
                    ),
                    StakeholderAlignment(
                        stakeholder_role="CS Lead",
                        primary_concern="ChurnRate mitigation.",
                        target_metrics=["ChurnRate"],
                    ),
                ],
                aligned_metrics=[
                    AlignedMetricSpec(
                        metric_name="Revenue",
                        role="North Star",
                        aggregation="SUM & Share %",
                        stakeholder_alignment="Primary revenue KPI.",
                    ),
                ],
                clarifying_questions=["What ChurnRate cap triggers retention playbooks?"],
                recommended_analysis_prompt="Analyze Revenue vs ChurnRate across Region and Category.",
            )
        if response_model is LLMDataScienceSynthesis:
            return LLMDataScienceSynthesis(
                cleansing_assessment="Clean 10-row SaaS dataset.",
                feature_engineering_recommendations=["Track Profit margin ratio."],
                cluster_interpretations=["Enterprise Cloud forms high-revenue cluster."],
                predictive_driver_takeaway="Transactions and Profit explain Revenue.",
            )
        if response_model is ReportCritique:
            return ReportCritique(
                overall_score=95.0,
                empirical_grounding=95.0,
                executive_depth=95.0,
                statistical_rigor=95.0,
                visual_storytelling=95.0,
                powerbi_dax_readiness=95.0,
                actionability_roi=95.0,
                passes_principal_bar=True,
            )
        planner_prompts.append(user_prompt)
        return DashboardPlan(
            title="Hybrid Problem-Driven SaaS Report",
            summary="Executive synthesis aligned to problem definition.",
            dataset_name="saas.csv",
            kpis=[
                KPISpec(
                    id="kpi_1",
                    title="Total Revenue",
                    value="$1.28M",
                    formula_dax="Total Revenue = SUM('Dataset'[Revenue])",
                    formula_tableau="SUM([Revenue])",
                    rationale="North Star KPI",
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
            csv_text=PERFECT_SAAS_CSV,
            user_prompt="Reduce regional churn while growing revenue",
            dataset_name="saas.csv",
            refinement_iterations=1,
        )

    assert plan.problem_definition is not None
    assert plan.problem_definition.synthesis_mode == "static_and_ai"
    assert plan.problem_definition.ai_provider_used.startswith("static-code + ")
    assert len(plan.problem_definition.static_signals) >= 3
    assert len(planner_prompts) == 1
    assert "ALIGNED PROBLEM DEFINITION & STAKEHOLDER MANDATE (STATIC CODE + AI):" in planner_prompts[0]
