# backend/tests/test_instructor_structured.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel, Field, ValidationError, field_validator
import instructor
from instructor import Mode

from app.services.llm.instructor_client import (
    generate_structured,
    get_groq_instructor,
    get_genai_instructor,
    _execute_with_groq,
    _execute_with_gemini,
    InstructorStructuredOutputError,
)
from app.modules.research_agent.schemas import (
    WebSearchArgs,
    WebScrapeArgs,
    DataAnalystArgs,
    ResearchPlanningDecision,
    ResearchFindingsExtraction,
    KeyFinding,
    ResearchStreamRequest,
)
from app.modules.research_agent.tools import (
    execute_web_search,
    execute_web_scrape,
    execute_data_analyst,
    dispatch_tool_call,
    TOOL_SCHEMA_REGISTRY,
    TOOL_EXECUTOR_REGISTRY,
)
from app.modules.data_analyst.schemas import (
    DashboardPlan,
    KPISpec,
    ChartVisualSpec,
    AnomalyFinding,
)
from app.modules.data_analyst.analyst import call_llm_dashboard_planner, generate_complete_dashboard
from app.modules.research_agent.agent import stream_research_agent


# ------------------------------------------------------------
# 1. Type-Safe Tool Argument Validation Tests
# ------------------------------------------------------------

def test_web_search_args_validation():
    """Verify WebSearchArgs enforces strict Pydantic constraints."""
    # Valid arguments
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
    # Valid arguments
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
    # Valid arguments
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
# 2. Central Type-Safe Tool Router & Dispatcher Tests
# ------------------------------------------------------------

def test_tool_registry_integrity():
    """Verify TOOL_SCHEMA_REGISTRY and TOOL_EXECUTOR_REGISTRY contain required tools."""
    assert "web_search" in TOOL_SCHEMA_REGISTRY
    assert "web_scrape" in TOOL_SCHEMA_REGISTRY
    assert "data_analyst" in TOOL_SCHEMA_REGISTRY
    assert TOOL_SCHEMA_REGISTRY["web_search"] == WebSearchArgs
    assert TOOL_SCHEMA_REGISTRY["web_scrape"] == WebScrapeArgs
    assert TOOL_SCHEMA_REGISTRY["data_analyst"] == DataAnalystArgs


@pytest.mark.asyncio
async def test_dispatch_tool_call_web_search():
    """Verify dispatch_tool_call validates and executes web_search."""
    with patch("app.modules.research_agent.tools.search_web") as mock_search:
        mock_search.return_value = []
        result = await dispatch_tool_call("web_search", {"query": "vector indexing", "max_results": 3})
        assert isinstance(result, list)
        mock_search.assert_called_once_with(query="vector indexing", max_results=3)


@pytest.mark.asyncio
async def test_dispatch_tool_call_web_scrape():
    """Verify dispatch_tool_call validates and executes web_scrape."""
    with patch("app.modules.research_agent.tools.scrape_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "clean markdown text"
        result = await dispatch_tool_call("web_scrape", {"url": "https://docs.vectronyx.ai", "max_chars": 800})
        assert result == "clean markdown text"
        mock_scrape.assert_awaited_once_with(url="https://docs.vectronyx.ai", max_chars=800)


@pytest.mark.asyncio
async def test_dispatch_tool_call_data_analyst():
    """Verify dispatch_tool_call validates and executes data_analyst with JSON string."""
    payload_json = json.dumps({
        "prompt": "Evaluate ARR growth",
        "csv_data": "quarter,arr\nQ1,1000\nQ2,1400",
        "dataset_name": "arr_growth.csv"
    })
    
    mock_plan = DashboardPlan(
        title="ARR Growth",
        summary="Summary",
        kpis=[KPISpec(id="1", title="ARR", value="$1400", formula_dax="", formula_tableau="", rationale="")],
        visuals=[]
    )
    with patch("app.modules.data_analyst.analyst.generate_complete_dashboard", new_callable=AsyncMock) as mock_analyst:
        mock_analyst.return_value = mock_plan
        result = await dispatch_tool_call("data_analyst", payload_json)
        assert isinstance(result, DashboardPlan)
        assert result.title == "ARR Growth"
        mock_analyst.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_tool_call_unknown_tool():
    """Verify dispatch_tool_call raises ValueError for unknown tools."""
    with pytest.raises(ValueError) as exc:
        await dispatch_tool_call("unknown_tool", {})
    assert "Unknown tool 'unknown_tool'" in str(exc.value)


@pytest.mark.asyncio
async def test_dispatch_tool_call_validation_failure():
    """Verify dispatch_tool_call raises ValidationError for invalid schema inputs."""
    with pytest.raises(ValidationError):
        # max_results is invalid (negative)
        await dispatch_tool_call("web_search", {"query": "fail", "max_results": -5})


# ------------------------------------------------------------
# 3. Instructor Client Initialization & Mode Handling Tests
# ------------------------------------------------------------

def test_instructor_client_factories():
    """Verify Instructor wraps Groq and Gemini clients without error."""
    groq_ic = get_groq_instructor(api_key="mock_groq_key")
    assert groq_ic is not None
    assert hasattr(groq_ic, "create")

    genai_ic = get_genai_instructor(api_key="mock_gemini_key")
    assert genai_ic is not None
    assert hasattr(genai_ic, "create")


def test_get_groq_instructor_missing_key():
    """Verify get_groq_instructor raises ValueError if API key is not configured."""
    with patch("app.core.config.settings.GROQ_API_KEY", ""):
        with pytest.raises(ValueError) as exc:
            get_groq_instructor()
        assert "GROQ_API_KEY is not configured" in str(exc.value)


def test_get_genai_instructor_missing_key():
    """Verify get_genai_instructor raises ValueError if API key is not configured."""
    with patch("app.core.config.settings.GEMINI_API_KEY", ""):
        with pytest.raises(ValueError) as exc:
            get_genai_instructor()
        assert "GEMINI_API_KEY is not configured" in str(exc.value)


@pytest.mark.asyncio
async def test_groq_auto_mode_selection_and_fallback():
    """Verify Groq auto-selects Mode.JSON for openai/ models and handles tool_use_failed retry."""
    class SimpleOut(BaseModel):
        msg: str

    mock_client = AsyncMock()
    mock_client.create.return_value = SimpleOut(msg="Mode JSON Success")

    with patch("app.services.llm.instructor_client.get_groq_instructor", return_value=mock_client) as mock_factory:
        # 1. Model starting with openai/ -> should use Mode.JSON
        res = await _execute_with_groq(
            response_model=SimpleOut,
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-oss-120b"
        )
        assert res.msg == "Mode JSON Success"
        mock_factory.assert_called_with(mode=Mode.JSON)

    # 2. Tool calling rejected (tool choice is required) -> auto fallback to Mode.JSON
    call_count = 0
    def mock_create_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Error code: 400 - Tool choice is required, but model did not call a tool")
        return SimpleOut(msg="Recovered in JSON mode")

    mock_client2 = AsyncMock()
    mock_client2.create.side_effect = mock_create_side_effect
    with patch("app.services.llm.instructor_client.get_groq_instructor", return_value=mock_client2):
        res2 = await _execute_with_groq(
            response_model=SimpleOut,
            messages=[{"role": "user", "content": "hi"}],
            model="llama-3.1-8b-instant"
        )
        assert res2.msg == "Recovered in JSON mode"
        assert call_count == 2


@pytest.mark.asyncio
async def test_gemini_fallback_model():
    """Verify Gemini retries with gemini-3.5-flash-lite if preview model fails."""
    class SimpleOut(BaseModel):
        msg: str

    call_count = 0
    def mock_gemini_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("404 Model Not Found / Deprecated")
        return SimpleOut(msg="Gemini flash lite recovery")

    mock_client = AsyncMock()
    mock_client.create.side_effect = mock_gemini_side_effect
    with patch("app.services.llm.instructor_client.get_genai_instructor", return_value=mock_client):
        res = await _execute_with_gemini(
            response_model=SimpleOut,
            messages=[{"role": "user", "content": "hi"}],
            model="gemini-3.8-flash"
        )
        assert res.msg == "Gemini flash lite recovery"
        assert call_count == 2


# ------------------------------------------------------------
# 4. Instructor Structured Outputs & Self-Correction Feedback Tests
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
async def test_instructor_generate_structured_with_messages_list():
    """Verify generate_structured accepts direct messages list."""
    expected = DummySchema(metric="DirectMessages", score=90.0)

    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = expected
        
        result = await generate_structured(
            response_model=DummySchema,
            messages=[
                {"role": "system", "content": "System mandate"},
                {"role": "user", "content": "User input"}
            ],
            provider="groq"
        )
        assert result.metric == "DirectMessages"


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
# 5. Data Analyst Dashboard Planning with Instructor
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


# ------------------------------------------------------------
# 6. ReAct Agent Tool Calls & Findings Extraction Tests
# ------------------------------------------------------------

def test_research_findings_extraction_validation():
    """Verify ResearchFindingsExtraction enforces confidence score and key findings count."""
    valid = ResearchFindingsExtraction(
        executive_summary="Summary statement of findings.",
        confidence_score=95,
        key_findings=[
            KeyFinding(
                title="Finding 1",
                description="Desc 1",
                impact="Critical",
                category="Infrastructure"
            )
        ]
    )
    assert valid.confidence_score == 95
    assert len(valid.key_findings) == 1

    # Confidence score < 50 raises ValidationError
    with pytest.raises(ValidationError):
        ResearchFindingsExtraction(
            executive_summary="Summary",
            confidence_score=30,
            key_findings=[KeyFinding(title="T", description="D", category="C")]
        )

    # Empty key findings raises ValidationError (min_length=1)
    with pytest.raises(ValidationError):
        ResearchFindingsExtraction(
            executive_summary="Summary",
            confidence_score=90,
            key_findings=[]
        )


@pytest.mark.asyncio
async def test_stream_research_agent_with_data_analyst_tool():
    """Verify stream_research_agent invokes Data Analyst when tabular CSV data is provided."""
    csv_payload = "category,margin\nSoftware,0.45\nServices,0.18"
    events = []

    async for event_str in stream_research_agent(
        query="Analyze enterprise software margins",
        depth="quick",
        csv_data=csv_payload
    ):
        if event_str.startswith("event:"):
            events.append(event_str.replace("event:", "").split("\n")[0].strip())

    assert "thought" in events
    assert "tool_start" in events
    assert "tool_end" in events
    assert "complete" in events
