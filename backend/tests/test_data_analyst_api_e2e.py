# backend/tests/test_data_analyst_api_e2e.py
import pytest
import io
import json
import zipfile
from starlette.testclient import TestClient
from app.main import app

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

client = TestClient(app)


def test_e2e_api_profile():
    """Verify POST /api/analyst/profile returns complete schema profiling."""
    files = {"file": ("dataset.csv", io.BytesIO(SAAS_CSV.encode("utf-8")), "text/csv")}
    response = client.post("/api/analyst/profile", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 10
    assert data["col_count"] == 6
    assert data["data_integrity_score"] > 90.0
    col_names = [c["name"] for c in data["columns"]]
    assert "Revenue" in col_names
    assert "ChurnRate" in col_names


def test_e2e_api_generate_dashboard_risk():
    """Verify POST /api/analyst/generate-dashboard adapts to churn & risk mandate."""
    response = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Evaluate churn rate across regions and diagnose high-risk customer segments",
            "dataset_name": "saas_metrics.csv",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["analytical_intent"] == "risk_and_churn"
    assert "ChurnRate" in data["focused_metrics"]
    assert "Region" in data["focused_dimensions"]
    assert len(data["kpis"]) >= 4
    assert len(data["visuals"]) >= 2
    # Ensure visual series data was calculated
    assert len(data["visuals"][0]["series_data"]) > 0


def test_e2e_api_generate_dashboard_unit_economics():
    """Verify POST /api/analyst/generate-dashboard adapts to unit economics mandate."""
    response = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Evaluate unit economics: identify which category delivers the highest margin efficiency",
            "dataset_name": "saas_metrics.csv",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["analytical_intent"] == "unit_economics"
    assert "Category" in data["focused_dimensions"]


def test_e2e_api_generate_dashboard_stream_sse():
    """Verify POST /api/analyst/generate-dashboard/stream emits progressive SSE telemetry."""
    response = client.post(
        "/api/analyst/generate-dashboard/stream",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Conduct concentration risk & HHI volatility audit on Region by Revenue",
            "dataset_name": "saas_metrics.csv",
        },
    )
    assert response.status_code == 200
    content = response.text
    assert "event: status" in content
    assert "event: complete" in content
    assert "Step 1/5" in content
    assert "Step 3/5" in content
    assert "Step 5/5" in content


def test_e2e_api_export_powerbi():
    """Verify POST /api/analyst/export/powerbi generates a valid .pbip zip archive."""
    # First generate a plan
    gen_res = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Unit economics and capital allocation review",
            "dataset_name": "saas.csv",
        },
    )
    plan_dict = gen_res.json()

    export_res = client.post(
        "/api/analyst/export/powerbi",
        data={
            "raw_csv": SAAS_CSV,
            "plan_json": json.dumps(plan_dict),
        },
    )
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/zip"

    # Inspect zip contents
    zip_bytes = io.BytesIO(export_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as z:
        filenames = z.namelist()
        assert any(f.endswith(".pbip") for f in filenames)
        assert any("model.bim" in f for f in filenames)
        assert any("report.json" in f for f in filenames)
        assert any("dataset.csv" in f for f in filenames)


def test_e2e_api_export_tableau():
    """Verify POST /api/analyst/export/tableau generates a valid .twbx zip archive."""
    gen_res = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Unit economics review",
            "dataset_name": "saas.csv",
        },
    )
    plan_dict = gen_res.json()

    export_res = client.post(
        "/api/analyst/export/tableau",
        data={
            "raw_csv": SAAS_CSV,
            "plan_json": json.dumps(plan_dict),
        },
    )
    assert export_res.status_code == 200
    assert "tableau" in export_res.headers["content-type"]

    zip_bytes = io.BytesIO(export_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as z:
        filenames = z.namelist()
        assert any(f.endswith(".twb") for f in filenames)
        assert any("dataset.csv" in f for f in filenames)


def test_e2e_api_export_dossier_markdown():
    """Verify POST /api/analyst/export/dossier produces authoritative Markdown."""
    gen_res = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Diagnose customer churn rate across regions",
            "dataset_name": "saas.csv",
        },
    )
    plan_dict = gen_res.json()

    export_res = client.post(
        "/api/analyst/export/dossier",
        data={
            "plan_json": json.dumps(plan_dict),
        },
    )
    assert export_res.status_code == 200
    md = export_res.text
    assert "EXECUTIVE INTELLIGENCE DOSSIER" in md
    assert "EXECUTIVE VERDICT" in md
    assert "SITUATION - COMPLICATION - RESOLUTION" in md
    assert "VISUAL ANALYTICS ARCHITECTURE" in md
    assert "ChurnRate" in md


def test_e2e_api_minimal_prompt_fallback_robustness():
    """Verify minimal prompt gracefully falls back to default columns without crashing."""
    response = client.post(
        "/api/analyst/generate-dashboard",
        data={
            "raw_csv": SAAS_CSV,
            "prompt": "Analyze",
            "dataset_name": "saas.csv",
        },
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["title"] != ""
    assert len(plan["kpis"]) >= 4
    assert len(plan["visuals"]) >= 1

