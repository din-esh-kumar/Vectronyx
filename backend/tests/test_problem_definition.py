# backend/tests/test_problem_definition.py
import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.modules.data_analyst.problem_definer import (
    define_problem_and_align_metrics,
    verify_and_define_dataset,
    verify_dataset_readiness,
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
