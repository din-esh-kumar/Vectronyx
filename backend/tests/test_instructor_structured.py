# backend/tests/test_instructor_structured.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel, Field, ValidationError

from app.services.llm.instructor_client import (
    generate_structured,
    get_groq_instructor,
    get_genai_instructor,
    InstructorStructuredOutputError,
)
from app.modules.research_agent.schemas import (
    WebSearchArgs,
    WebScrapeArgs,
    DataAnalystArgs,
    ResearchPlanningDecision,
    ResearchFindingsExtraction,
    KeyFinding,
)
from app.modules.research_agent.tools import (
    execute_web_search,
    execute_web_scrape,
    execute_data_analyst,
)
from app.modules.data_analyst.schemas import (
    DashboardPlan,
    KPISpec,
    ChartVisualSpec,
)
from app.modules.data_analyst.analyst import call_llm_dashboard_planner


# ------------------------------------------------------------
# 1. Type-Safe Tool Argument Validation Tests
# ------------------------------------------------------------

def test_web_search_args_validation():
    """Verify WebSearchArgs enforces strict Pydantic constraints."""
    # Valid
    args = WebSearchArgs(query="pgvector latency benchmark", max_results=5)
    assert args.query == "pgvector latency benchmark"
    assert args.max_results == 5

    # Coercion from dictionary
    sources = execute_web_search({"query": "in-memory vector db", "max_results": 2})
    assert isinstance(sources, list)

    # Invalid max_results (< 1)
    with pytest.raises(ValidationError):
        WebSearchArgs(query="test", max_results=0)

    # Invalid max_results (> 10)
    with pytest.raises(ValidationError):
        WebSearchArgs(query="test", max_results=50)

    # Missing required query
    with pytest.raises(ValidationError):
        WebSearchArgs.model_validate({"max_results": 5})


@pytest.mark.asyncio
async def test_web_scrape_args_validation():
    """Verify WebScrapeArgs strictly validates URL and max_chars boundaries."""
    # Valid
    args = WebScrapeArgs(url="https://supabase.com/blog/pgvector-performance", max_chars=1200)
    assert args.max_chars == 1200

    # Coercion from dictionary with SSRF blocked loopback
    res = await execute_web_scrape({"url": "http://127.0.0.1/admin", "max_chars": 500})
    assert "restricted or invalid URL" in res

    # Invalid max_chars (< 100)
    with pytest.raises(ValidationError):
        WebScrapeArgs(url="https://example.com", max_chars=50)

    # Invalid max_chars (> 10000)
    with pytest.raises(ValidationError):
        WebScrapeArgs(url="https://example.com", max_chars=20000)


@pytest.mark.asyncio
async def test_data_analyst_args_validation():
    """Verify DataAnalystArgs enforces prompt and CSV presence."""
    # Valid
    args = DataAnalystArgs(
        prompt="Analyze margin trends by region",
        csv_data="region,margin\nEMEA,0.24\nAPAC,0.18\nAMER,0.31",
        dataset_name="margins.csv",
    )
    assert args.dataset_name == "margins.csv"

    # Execution returns a validated DashboardPlan
    plan = await execute_data_analyst(args)
    assert isinstance(plan, DashboardPlan)
    assert len(plan.kpis) > 0

    # Missing required fields
    with pytest.raises(ValidationError):
        DataAnalystArgs.model_validate({"prompt": "Missing CSV"})


# ------------------------------------------------------------
# 2. Instructor Client Initialization Tests
# ------------------------------------------------------------

def test_instructor_client_factories():
    """Verify Instructor wraps Groq and Gemini clients without error."""
    groq_ic = get_groq_instructor(api_key="mock_groq_key")
    assert groq_ic is not None
    assert hasattr(groq_ic, "create")

    genai_ic = get_genai_instructor(api_key="mock_gemini_key")
    assert genai_ic is not None
    assert hasattr(genai_ic, "create")


# ------------------------------------------------------------
# 3. Instructor Structured Outputs & Self-Correcting Retry Tests
# ------------------------------------------------------------

class DummySchema(BaseModel):
    metric: str
    score: float = Field(ge=0.0, le=100.0)


@pytest.mark.asyncio
async def test_instructor_generate_structured_success():
    """Verify generate_structured returns valid Pydantic model directly."""
    expected = DummySchema(metric="Accuracy", score=98.5)

    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = expected
        
        result = await generate_structured(
            response_model=DummySchema,
            system_prompt="Test System",
            user_prompt="Test User",
            provider="groq"
        )
        assert isinstance(result, DummySchema)
        assert result.metric == "Accuracy"
        assert result.score == 98.5
        mock_groq.assert_awaited_once()


@pytest.mark.asyncio
async def test_instructor_multi_provider_failover():
    """Verify automatic failover when primary provider encounters an error."""
    expected = DummySchema(metric="FailoverSuccess", score=92.0)

    # Primary (gemini) fails, secondary (groq) succeeds
    with patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        
        mock_gemini.side_effect = RuntimeError("Gemini 503 Service Unavailable")
        mock_groq.return_value = expected

        result = await generate_structured(
            response_model=DummySchema,
            system_prompt="Sys",
            user_prompt="User",
            provider="gemini"
        )
        assert result.metric == "FailoverSuccess"
        assert result.score == 92.0
        mock_gemini.assert_awaited_once()
        mock_groq.assert_awaited_once()


@pytest.mark.asyncio
async def test_instructor_all_providers_failure():
    """Verify InstructorStructuredOutputError is raised when all providers fail."""
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq, \
         patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini:
        
        mock_groq.side_effect = RuntimeError("Groq rate limit exceeded")
        mock_gemini.side_effect = RuntimeError("Gemini connection timeout")

        with pytest.raises(InstructorStructuredOutputError) as exc_info:
            await generate_structured(
                response_model=DummySchema,
                system_prompt="Sys",
                user_prompt="User",
                provider="groq"
            )
        assert "All structured output providers failed" in str(exc_info.value)


# ------------------------------------------------------------
# 4. Data Analyst Dashboard Planning with Instructor
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_llm_dashboard_planner_guarantees_dashboard_plan():
    """Verify call_llm_dashboard_planner returns a validated DashboardPlan via Instructor."""
    mock_plan = DashboardPlan(
        title="Revenue Analysis",
        summary="SaaS unit economics overview",
        dataset_name="metrics.csv",
        kpis=[
            KPISpec(
                id="kpi_1",
                title="Gross ARR",
                value="$4.8M",
                change="+18%",
                trend="up",
                formula_dax="Total ARR = SUM(Subscriptions[Amount])",
                formula_tableau="SUM([Amount])",
                rationale="Core recurring baseline"
            )
        ],
        visuals=[
            ChartVisualSpec(
                id="vis_1",
                title="ARR by Region",
                chart_type="bar",
                x_axis="region",
                y_axis="arr",
                aggregation="sum",
                description="Distribution across geographic operating entities"
            )
        ]
    )

    with patch("app.modules.data_analyst.analyst.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_plan

        plan = await call_llm_dashboard_planner(
            schema_summary="- region (dtype=object)\n- arr (dtype=int64)",
            row_count=100,
            user_prompt="Analyze ARR by region",
            dataset_name="metrics.csv"
        )
        assert isinstance(plan, DashboardPlan)
        assert plan.title == "Revenue Analysis"
        assert len(plan.kpis) == 1
        assert plan.kpis[0].title == "Gross ARR"
        assert len(plan.visuals) == 1
        assert plan.visuals[0].chart_type == "bar"


@pytest.mark.asyncio
async def test_call_llm_dashboard_planner_fallback_on_error():
    """Verify call_llm_dashboard_planner returns None when generation fails, enabling heuristic fallback."""
    with patch("app.modules.data_analyst.analyst.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("Network timeout")

        plan = await call_llm_dashboard_planner(
            schema_summary="- col1 (dtype=int64)",
            row_count=10,
            user_prompt="Analyze",
            dataset_name="test.csv"
        )
        assert plan is None

