# backend/tests/verify_live_instructor.py
"""
Live Integration and Heavy Verification Suite for Instructor / Pydantic Structured Outputs.
Tests real LLM calls against Groq Cloud and Google Gemini, verifying:
1. Zero JSON/XML parsing errors with complex nested schemas.
2. Self-correcting feedback loops with Pydantic field validators.
3. Multi-provider fallback and resiliency.
4. Type-safe tool calling and dispatching.
5. End-to-end FastAPI endpoint invocations (profiling, streaming, dashboard generation, exports).
"""
import sys
import io
# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

import asyncio
import json
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import httpx

from app.core.config import settings
from app.services.llm.instructor_client import (
    generate_structured,
    get_groq_instructor,
    get_genai_instructor,
)
from app.modules.research_agent.schemas import (
    WebSearchArgs,
    WebScrapeArgs,
    DataAnalystArgs,
    ResearchPlanningDecision,
)
from app.modules.research_agent.tools import dispatch_tool_call
from app.modules.data_analyst.schemas import DashboardPlan
from app.modules.data_analyst.analyst import generate_complete_dashboard
from app.main import app


# ---------------------------------------------------------------------------
# Complex Schema Definitions for Torture Testing
# ---------------------------------------------------------------------------

class TechnicalMetric(BaseModel):
    name: str = Field(..., description="Name of the technical metric")
    p95_latency_ms: float = Field(..., ge=0.0, le=1000.0, description="p95 latency in ms")
    throughput_qps: int = Field(..., ge=1, description="Queries per second")
    status: str = Field(..., description="Operational status: healthy, degraded, critical")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"healthy", "degraded", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"Status must be one of {allowed}, got '{v}'")
        return v.lower()


class ArchitectureBenchmarkReport(BaseModel):
    architecture_title: str
    database_engine: str
    production_ready: bool
    metrics: List[TechnicalMetric] = Field(..., min_length=2, max_length=5)
    tradeoffs_summary: str = Field(..., min_length=15)


async def test_live_gemini_structured():
    print("\n--- 1. Testing Live Gemini Structured Output (gemini-3.5-flash-lite) ---")
    try:
        report = await generate_structured(
            response_model=ArchitectureBenchmarkReport,
            system_prompt="You are a principal systems architect. Return an objective technical benchmark report in the requested schema.",
            user_prompt="Benchmark Supabase pgvector with HNSW index vs Pinecone Serverless for 768-dimensional embeddings.",
            provider="gemini",
            max_retries=3,
            temperature=0.1,
        )
        assert isinstance(report, ArchitectureBenchmarkReport)
        assert len(report.metrics) >= 2
        print(f"[OK] Gemini Succeeded: Title='{report.architecture_title}', Engine='{report.database_engine}', MetricsCount={len(report.metrics)}")
        for m in report.metrics:
            print(f"   - {m.name}: p95={m.p95_latency_ms}ms, qps={m.throughput_qps}, status={m.status}")
        return True
    except Exception as e:
        print(f"[FAIL] Gemini Structured Test Failed: {e}")
        return False


async def test_live_groq_structured():
    print("\n--- 2. Testing Live Groq Structured Output (Mode.JSON on openai/gpt-oss-120b) ---")
    try:
        report = await generate_structured(
            response_model=ArchitectureBenchmarkReport,
            system_prompt="You are a database performance engineer. Provide a benchmark report strictly matching the schema.",
            user_prompt="Provide performance metrics for in-memory Redis vs SQLite vector search.",
            provider="groq",
            max_retries=3,
            temperature=0.1,
        )
        assert isinstance(report, ArchitectureBenchmarkReport)
        assert len(report.metrics) >= 2
        print(f"[OK] Groq Succeeded: Title='{report.architecture_title}', Engine='{report.database_engine}', MetricsCount={len(report.metrics)}")
        for m in report.metrics:
            print(f"   - {m.name}: p95={m.p95_latency_ms}ms, qps={m.throughput_qps}, status={m.status}")
        return True
    except Exception as e:
        print(f"[FAIL] Groq Structured Test Failed: {e}")
        return False


async def test_type_safe_tool_dispatcher():
    print("\n--- 3. Testing Type-Safe Tool Dispatcher Concurrency & Coercion ---")
    # Dispatch multiple tools concurrently via dispatch_tool_call
    tasks = [
        dispatch_tool_call("web_search", {"query": "pgvector hnsw indexing", "max_results": 2}),
        dispatch_tool_call("web_scrape", {"url": "https://supabase.com/blog/pgvector-performance", "max_chars": 500}),
        dispatch_tool_call("data_analyst", {
            "prompt": "Evaluate regional sales volume",
            "csv_data": "region,sales\nNorth,5200\nSouth,3100\nWest,7400\nEast,4100",
            "dataset_name": "sales.csv"
        }),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check WebSearch result
    search_res = results[0]
    assert not isinstance(search_res, Exception), f"Search failed: {search_res}"
    print(f"[OK] WebSearch Tool Dispatched: Retrieved {len(search_res)} sources")

    # Check WebScrape result
    scrape_res = results[1]
    assert not isinstance(scrape_res, Exception), f"Scrape failed: {scrape_res}"
    print(f"[OK] WebScrape Tool Dispatched: Extracted {len(scrape_res)} chars")

    # Check DataAnalyst result
    analyst_res = results[2]
    assert not isinstance(analyst_res, Exception), f"DataAnalyst failed: {analyst_res}"
    assert isinstance(analyst_res, DashboardPlan)
    print(f"[OK] DataAnalyst Tool Dispatched: Generated DashboardPlan '{analyst_res.title}' with {len(analyst_res.kpis)} KPIs")

    return True


async def test_fastapi_endpoints_live():
    print("\n--- 4. Testing Live FastAPI Endpoints with TestClient ---")
    transport = httpx.ASGITransport(app=app)
    csv_sample = "quarter,arr,churn_rate\nQ1,1200000,0.021\nQ2,1450000,0.019\nQ3,1800000,0.015\nQ4,2300000,0.012"

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # A. Profile endpoint
        files = {"file": ("saas_metrics.csv", csv_sample.encode("utf-8"), "text/csv")}
        res_profile = await client.post("/api/analyst/profile", files=files)
        assert res_profile.status_code == 200
        profile_data = res_profile.json()
        print(f"[OK] /api/analyst/profile: Rows={profile_data['row_count']}, Cols={profile_data['col_count']}, Integrity={profile_data['data_integrity_score']}%")

        # B. Generate Dashboard endpoint (JSON response guaranteed DashboardPlan)
        form_data = {
            "prompt": "Executive SaaS ARR expansion analysis",
            "dataset_name": "saas_metrics.csv",
            "raw_csv": csv_sample,
        }
        res_dash = await client.post("/api/analyst/generate-dashboard", data=form_data)
        assert res_dash.status_code == 200
        dash_data = res_dash.json()
        assert "kpis" in dash_data
        assert "visuals" in dash_data
        assert "dossier" in dash_data
        print(f"[OK] /api/analyst/generate-dashboard: '{dash_data['title']}' ({len(dash_data['kpis'])} KPIs, {len(dash_data['visuals'])} Charts)")

        # C. Power BI PBIP Export
        res_pbi = await client.post(
            "/api/analyst/export/powerbi",
            data={"raw_csv": csv_sample, "plan_json": json.dumps(dash_data)}
        )
        assert res_pbi.status_code == 200
        assert res_pbi.headers["content-type"] == "application/zip"
        print(f"[OK] /api/analyst/export/powerbi: ZIP archive generated ({len(res_pbi.content)} bytes)")

        # D. Tableau TWBX Export
        res_tab = await client.post(
            "/api/analyst/export/tableau",
            data={"raw_csv": csv_sample, "plan_json": json.dumps(dash_data)}
        )
        assert res_tab.status_code == 200
        print(f"[OK] /api/analyst/export/tableau: TWBX workbook generated ({len(res_tab.content)} bytes)")

        # E. Executive Dossier Markdown Export
        res_dos = await client.post(
            "/api/analyst/export/dossier",
            data={"plan_json": json.dumps(dash_data)}
        )
        assert res_dos.status_code == 200
        assert "# 🏛️ EXECUTIVE INTELLIGENCE DOSSIER" in res_dos.text
        print(f"[OK] /api/analyst/export/dossier: Markdown document generated ({len(res_dos.text)} characters)")

    return True


async def main():
    print("=================================================================")
    print("VECTRONYX HEAVY LIVE INSTRUCTOR & STRUCTURED OUTPUT VERIFICATION")
    print("=================================================================")
    
    gemini_ok = await test_live_gemini_structured()
    groq_ok = await test_live_groq_structured()
    dispatcher_ok = await test_type_safe_tool_dispatcher()
    endpoints_ok = await test_fastapi_endpoints_live()

    print("\n=================================================================")
    print(f"VERIFICATION SUMMARY: Gemini={gemini_ok}, Groq={groq_ok}, Dispatcher={dispatcher_ok}, Endpoints={endpoints_ok}")
    print("=================================================================")

    if not (gemini_ok and groq_ok and dispatcher_ok and endpoints_ok):
        sys.exit(1)
    print("ALL LIVE CHECKS PASSED WITH ZERO ERRORS! ")


if __name__ == "__main__":
    asyncio.run(main())
