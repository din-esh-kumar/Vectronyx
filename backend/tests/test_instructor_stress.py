# backend/tests/test_instructor_stress.py
"""
Exhaustive Stress & Edge-Case Test Suite for Instructor Structured Outputs
and Type-Safe Agent Tool Dispatcher in Vectronyx.

Covers:
1. Provider initialization & API key edge cases (empty, whitespace, missing, overrides)
2. Mode normalization (enum, string, casing)
3. Input validation & empty prompts guards
4. Multi-provider failover mechanics & model parameter safety
5. Automatic mode fallback on Groq tool choice failure
6. Dual Gemini model failover on rate limits / 404s
7. Comprehensive SSRF audit matrix (IPv4, IPv6, RFC 1918, link-local, cloud metadata, redirect SSRF)
8. Pydantic schema boundary & cross-field validator stress tests
9. Tool dispatcher parsing, coercions, malformed JSON, and unknown tools
10. High-concurrency async load stress tests (50+ simultaneous dispatches)
11. Self-correcting feedback loop simulation
"""

import asyncio
import json
from typing import Any
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel, Field, ValidationError

import instructor
from instructor import Mode

from app.core.config import settings
from app.services.llm.instructor_client import (
    generate_structured,
    get_groq_instructor,
    get_genai_instructor,
    _execute_with_groq,
    _execute_with_gemini,
    _normalize_mode,
    InstructorStructuredOutputError,
)
from app.modules.research_agent.schemas import (
    ResearchSource,
    WebSearchArgs,
    WebScrapeArgs,
    DataAnalystArgs,
    AgentToolCallDecision,
    ResearchPlanningDecision,
    ResearchFindingsExtraction,
    KeyFinding,
)
from app.modules.research_agent.tools import (
    is_safe_url,
    search_web,
    scrape_page,
    execute_web_search,
    execute_web_scrape,
    execute_data_analyst,
    dispatch_tool_call,
    TOOL_SCHEMA_REGISTRY,
    TOOL_EXECUTOR_REGISTRY,
)


class MockSimpleOutput(BaseModel):
    summary: str
    confidence: int = Field(ge=0, le=100)


# =====================================================================
# 1. PROVIDER INITIALIZATION & CONFIGURATION EDGE CASES
# =====================================================================

def test_groq_missing_api_key_raises_descriptive_error():
    """Verify get_groq_instructor raises ValueError when key is missing, empty, or whitespace."""
    with patch.object(settings, "GROQ_API_KEY", ""):
        with pytest.raises(ValueError, match="GROQ_API_KEY is not configured or is empty"):
            get_groq_instructor(api_key=None)

        with pytest.raises(ValueError, match="GROQ_API_KEY is not configured or is empty"):
            get_groq_instructor(api_key="")

        with pytest.raises(ValueError, match="GROQ_API_KEY is not configured or is empty"):
            get_groq_instructor(api_key="   \t\n  ")


def test_gemini_missing_api_key_raises_descriptive_error():
    """Verify get_genai_instructor raises ValueError when key is missing, empty, or whitespace."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured or is empty"):
            get_genai_instructor(api_key=None)

        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured or is empty"):
            get_genai_instructor(api_key="")

        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured or is empty"):
            get_genai_instructor(api_key="   ")


def test_groq_explicit_api_key_override():
    """Verify passing explicit api_key overrides settings and initializes client."""
    client = get_groq_instructor(api_key="gsk_override_test_12345", mode=Mode.JSON)
    assert client is not None


def test_gemini_explicit_api_key_override():
    """Verify passing explicit api_key overrides settings and initializes client."""
    client = get_genai_instructor(api_key="AIzaSyTestOverrideKey12345", mode=Mode.TOOLS)
    assert client is not None


def test_normalize_mode_variations():
    """Verify _normalize_mode handles enum instances, various string representations, and defaults."""
    assert _normalize_mode(Mode.JSON) == Mode.JSON
    assert _normalize_mode(Mode.TOOLS) == Mode.TOOLS
    assert _normalize_mode(Mode.MD_JSON) == Mode.MD_JSON
    assert _normalize_mode("json") == Mode.JSON
    assert _normalize_mode("JSON") == Mode.JSON
    assert _normalize_mode("Mode.JSON") == Mode.JSON
    assert _normalize_mode("tools") == Mode.TOOLS
    assert _normalize_mode("TOOLS") == Mode.TOOLS
    assert _normalize_mode("tool_call") == Mode.TOOLS
    assert _normalize_mode("function") == Mode.TOOLS
    assert _normalize_mode("md_json") == Mode.MD_JSON
    assert _normalize_mode("unexpected_mode_string") == Mode.TOOLS
    assert _normalize_mode(None) == Mode.TOOLS


# =====================================================================
# 2. GENERATE_STRUCTURED INPUT VALIDATION & ROUTING
# =====================================================================

@pytest.mark.asyncio
async def test_generate_structured_empty_prompts_raises_value_error():
    """Verify generate_structured rejects invocation when no system, user prompt, or messages are provided."""
    with pytest.raises(ValueError, match="At least one prompt or message must be provided"):
        await generate_structured(response_model=MockSimpleOutput)

    with pytest.raises(ValueError, match="At least one prompt or message must be provided"):
        await generate_structured(response_model=MockSimpleOutput, messages=[])


@pytest.mark.asyncio
async def test_generate_structured_with_explicit_messages_list():
    """Verify generate_structured preserves custom conversation history passed in messages."""
    custom_messages = [
        {"role": "system", "content": "You are a test evaluator."},
        {"role": "user", "content": "Return output."},
    ]
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = MockSimpleOutput(summary="Test OK", confidence=99)
        result = await generate_structured(
            response_model=MockSimpleOutput,
            messages=custom_messages,
            provider="groq",
        )
        assert result.summary == "Test OK"
        mock_groq.assert_awaited_once()
        call_kwargs = mock_groq.call_args.kwargs
        assert call_kwargs["messages"] == custom_messages


# =====================================================================
# 3. MULTI-PROVIDER FAILOVER & MODEL RESILIENCE
# =====================================================================

@pytest.mark.asyncio
async def test_generate_structured_primary_success_no_secondary_invocation():
    """Verify that when primary provider succeeds, secondary fallback is never invoked."""
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq, \
         patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini:
        mock_groq.return_value = MockSimpleOutput(summary="Groq Success", confidence=95)
        
        result = await generate_structured(
            response_model=MockSimpleOutput,
            user_prompt="Evaluate",
            provider="groq",
        )
        assert result.summary == "Groq Success"
        mock_groq.assert_awaited_once()
        mock_gemini.assert_not_called()


@pytest.mark.asyncio
async def test_generate_structured_groq_fails_fails_over_to_gemini():
    """
    Verify that when Groq fails, generation falls over to Gemini, and Gemini
    receives model=None to prevent Groq model names leaking into Gemini API.
    """
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq, \
         patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini:
        mock_groq.side_effect = RuntimeError("Groq 503 Service Unavailable / Rate Limit")
        mock_gemini.return_value = MockSimpleOutput(summary="Gemini Fallback Success", confidence=90)

        result = await generate_structured(
            response_model=MockSimpleOutput,
            user_prompt="Evaluate",
            provider="groq",
            model="llama-3.3-70b-versatile",
        )
        assert result.summary == "Gemini Fallback Success"
        mock_groq.assert_awaited_once()
        mock_gemini.assert_awaited_once()
        # Verify secondary provider received model=None so it uses native config
        assert mock_gemini.call_args.kwargs["model"] is None


@pytest.mark.asyncio
async def test_generate_structured_gemini_fails_fails_over_to_groq():
    """Verify that when Gemini is primary and fails, it falls over to Groq with model=None."""
    with patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        mock_gemini.side_effect = RuntimeError("Gemini Quota Exceeded 429")
        mock_groq.return_value = MockSimpleOutput(summary="Groq Recovery", confidence=92)

        result = await generate_structured(
            response_model=MockSimpleOutput,
            user_prompt="Evaluate",
            provider="gemini",
            model="gemini-2.5-flash",
        )
        assert result.summary == "Groq Recovery"
        mock_gemini.assert_awaited_once()
        mock_groq.assert_awaited_once()
        assert mock_groq.call_args.kwargs["model"] is None


@pytest.mark.asyncio
async def test_generate_structured_all_providers_fail_raises_custom_error():
    """Verify that when both providers fail, InstructorStructuredOutputError is raised with details."""
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq, \
         patch("app.services.llm.instructor_client._execute_with_gemini", new_callable=AsyncMock) as mock_gemini:
        mock_groq.side_effect = RuntimeError("Groq Connection Timeout")
        mock_gemini.side_effect = RuntimeError("Gemini Bad Request 400")

        with pytest.raises(InstructorStructuredOutputError) as exc_info:
            await generate_structured(
                response_model=MockSimpleOutput,
                user_prompt="Evaluate",
            )
        err_msg = str(exc_info.value)
        assert "All structured output providers failed" in err_msg
        assert "Groq Connection Timeout" in err_msg
        assert "Gemini Bad Request 400" in err_msg


@pytest.mark.asyncio
async def test_execute_with_groq_tool_calling_rejected_falls_back_to_mode_json():
    """Verify _execute_with_groq retries with Mode.JSON when Groq rejects tool choice."""
    mock_client_tools = MagicMock()
    mock_client_tools.create = AsyncMock(side_effect=Exception("tool choice is required for model"))

    mock_client_json = MagicMock()
    mock_client_json.create = AsyncMock(return_value=MockSimpleOutput(summary="JSON Mode Rescued", confidence=98))

    def fake_get_groq(mode=None):
        if mode == Mode.JSON:
            return mock_client_json
        return mock_client_tools

    with patch("app.services.llm.instructor_client.get_groq_instructor", side_effect=fake_get_groq):
        result = await _execute_with_groq(
            response_model=MockSimpleOutput,
            messages=[{"role": "user", "content": "hi"}],
            model="llama-3.1-8b-instant",
            mode=Mode.TOOLS,
        )
        assert result.summary == "JSON Mode Rescued"
        mock_client_tools.create.assert_awaited_once()
        mock_client_json.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_gemini_model_fallback_on_error():
    """Verify _execute_with_gemini automatically falls back to alternative model on failure."""
    mock_client = MagicMock()
    # First call with primary model fails; second call with fallback succeeds
    mock_client.create = AsyncMock(side_effect=[
        Exception("Model gemini-3.5-flash-lite not found or overloaded"),
        MockSimpleOutput(summary="Gemini Secondary Model Success", confidence=91)
    ])

    with patch("app.services.llm.instructor_client.get_genai_instructor", return_value=mock_client):
        result = await _execute_with_gemini(
            response_model=MockSimpleOutput,
            messages=[{"role": "user", "content": "Test"}],
            model="gemini-3.5-flash-lite",
        )
        assert result.summary == "Gemini Secondary Model Success"
        assert mock_client.create.await_count == 2
        # Second call used fallback model
        second_call_model = mock_client.create.call_args_list[1].kwargs["model"]
        assert second_call_model == "gemini-2.5-flash"


# =====================================================================
# 4. COMPREHENSIVE SSRF AUDIT MATRIX (is_safe_url)
# =====================================================================

@pytest.mark.parametrize("loopback_url", [
    "http://127.0.0.1/",
    "http://127.0.0.1:8000/api",
    "http://127.0.0.2/",
    "http://127.255.255.254:3000/metrics",
    "http://[::1]/",
    "http://[::1]:9090/",
    "http://[0000:0000:0000:0000:0000:0000:0000:0001]/",
    "http://localhost/",
    "http://localhost:5432/db",
])
def test_ssrf_loopback_addresses_blocked(loopback_url: str):
    """Verify all IPv4 and IPv6 loopback addresses and hostnames are blocked."""
    assert is_safe_url(loopback_url) is False, f"Expected {loopback_url} to be blocked!"


@pytest.mark.parametrize("private_url", [
    # 10.0.0.0/8
    "http://10.0.0.1/",
    "http://10.254.1.1:8080/admin",
    # 172.16.0.0/12
    "http://172.16.0.1/",
    "http://172.24.10.5:9200/",
    "http://172.31.255.255/",
    # 192.168.0.0/16
    "http://192.168.0.1/",
    "http://192.168.1.100:8000/",
    # IPv6 unique local fc00::/7 & link-local fe80::/10
    "http://[fe80::1]/",
    "http://[fe80::abcd:1234]:8080/",
    "http://[fc00::1]/",
    "http://[fd00::1]/",
])
def test_ssrf_private_networks_blocked(private_url: str):
    """Verify RFC 1918 and RFC 4193 private network addresses are blocked."""
    assert is_safe_url(private_url) is False, f"Expected {private_url} to be blocked!"


@pytest.mark.parametrize("cloud_metadata_url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.169.254:80/computeMetadata/v1/",
    "http://169.254.1.1/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://metadata/computeMetadata/v1/",
    "http://instance-data.ec2.internal/",
    "http://nas.local/shares",
    "http://internal-service.local:3000",
])
def test_ssrf_cloud_metadata_and_internal_domains_blocked(cloud_metadata_url: str):
    """Verify link-local cloud metadata IPs and internal top-level domains are blocked."""
    assert is_safe_url(cloud_metadata_url) is False, f"Expected {cloud_metadata_url} to be blocked!"


@pytest.mark.parametrize("dangerous_scheme_url", [
    "ftp://example.com/files.zip",
    "file:///etc/passwd",
    "file:///C:/Windows/win.ini",
    "gopher://127.0.0.1:6379/_FLUSHALL",
    "javascript:alert(1)",
    "data:text/html,<html>alert</html>",
    "ssh://root@192.168.1.1",
    "",
    "   ",
    None,
    12345,
    "http://0.0.0.0/",
    "http://0.0.0.0:80/",
])
def test_ssrf_dangerous_schemes_and_malformed_inputs_blocked(dangerous_scheme_url: Any):
    """Verify non-HTTP(S) schemes, zero IPs, and malformed inputs are rejected."""
    assert is_safe_url(dangerous_scheme_url) is False


@pytest.mark.parametrize("safe_url", [
    "https://www.google.com/search?q=test",
    "https://supabase.com/blog/pgvector-performance",
    "https://en.wikipedia.org/wiki/Vector_database",
    "https://arxiv.org/abs/2301.00001",
    "http://example.com:8080/benchmarks",
    "https://github.com/vectronyx/workbench",
])
def test_safe_public_urls_allowed(safe_url: str):
    """Verify standard legitimate public URLs pass safety verification."""
    assert is_safe_url(safe_url) is True, f"Expected {safe_url} to be allowed!"


# =====================================================================
# 5. OPEN-REDIRECT SSRF DEFENSE IN SCRAPE_PAGE
# =====================================================================

@pytest.mark.asyncio
async def test_scrape_page_blocks_open_redirect_to_internal_ip():
    """
    Verify that when an external public URL redirects to an internal/private IP,
    scrape_page re-verifies the destination and aborts without extracting.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "http://127.0.0.1:8000/internal_admin"
    mock_resp.text = "SECRET INTERNAL CONFIG"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("trafilatura.extract") as mock_extract:
        result = await scrape_page("https://public-portal.com/redirect", max_chars=1000)
        assert "Extraction skipped: restricted or invalid URL" in result
        mock_extract.assert_not_called()


# =====================================================================
# 6. PYDANTIC SCHEMA BOUNDARY & CROSS-FIELD STRESS TESTS
# =====================================================================

def test_web_search_args_boundaries_and_validators():
    """Verify WebSearchArgs bounds, whitespace rejection, and types."""
    # Valid
    args = WebSearchArgs(query="pgvector benchmarking", max_results=5)
    assert args.query == "pgvector benchmarking"
    assert args.max_results == 5

    # Boundary 1 & 10 pass
    assert WebSearchArgs(query="q", max_results=1).max_results == 1
    assert WebSearchArgs(query="q", max_results=10).max_results == 10

    # Whitespace-only query rejected
    with pytest.raises(ValidationError, match="query cannot be blank or whitespace-only"):
        WebSearchArgs(query="    \t  ")

    # Empty query rejected
    with pytest.raises(ValidationError):
        WebSearchArgs(query="")

    # max_results < 1
    with pytest.raises(ValidationError):
        WebSearchArgs(query="test", max_results=0)

    # max_results > 10
    with pytest.raises(ValidationError):
        WebSearchArgs(query="test", max_results=11)


def test_web_scrape_args_boundaries_and_validators():
    """Verify WebScrapeArgs enforces URL scheme and char boundaries."""
    # Valid
    args = WebScrapeArgs(url="https://docs.vectronyx.ai", max_chars=2000)
    assert args.max_chars == 2000

    # Boundary 100 & 10000 pass
    assert WebScrapeArgs(url="http://example.com", max_chars=100).max_chars == 100
    assert WebScrapeArgs(url="http://example.com", max_chars=10000).max_chars == 10000

    # Invalid scheme rejected by field validator
    with pytest.raises(ValidationError, match="url must begin with http:// or https://"):
        WebScrapeArgs(url="ftp://files.com/doc", max_chars=500)

    with pytest.raises(ValidationError, match="url must begin with http:// or https://"):
        WebScrapeArgs(url="file:///etc/passwd", max_chars=500)

    # max_chars < 100
    with pytest.raises(ValidationError):
        WebScrapeArgs(url="https://example.com", max_chars=99)

    # max_chars > 10000
    with pytest.raises(ValidationError):
        WebScrapeArgs(url="https://example.com", max_chars=10001)


def test_data_analyst_args_boundaries_and_validators():
    """Verify DataAnalystArgs enforces prompt and CSV presence."""
    # Valid
    args = DataAnalystArgs(
        prompt="Analyze revenue by product tier",
        csv_data="tier,rev\nCore,100\nPro,250",
    )
    assert args.dataset_name == "dataset.csv"

    # Whitespace-only prompt rejected
    with pytest.raises(ValidationError, match="prompt cannot be blank or whitespace-only"):
        DataAnalystArgs(prompt="   ", csv_data="tier,rev\nCore,100")

    # Empty or trivial CSV rejected (min_length=5)
    with pytest.raises(ValidationError):
        DataAnalystArgs(prompt="Analyze", csv_data="")

    with pytest.raises(ValidationError):
        DataAnalystArgs(prompt="Analyze", csv_data="a,b")


def test_agent_tool_call_decision_cross_field_validation():
    """Verify AgentToolCallDecision model_validator enforces matching tool arguments."""
    # Valid web_search decision
    decision1 = AgentToolCallDecision(
        thought="Query duckduckgo for benchmarks",
        tool="web_search",
        web_search_args=WebSearchArgs(query="pgvector", max_results=4),
    )
    assert decision1.tool == "web_search"

    # Valid web_scrape decision
    decision2 = AgentToolCallDecision(
        thought="Scrape article",
        tool="web_scrape",
        web_scrape_args=WebScrapeArgs(url="https://supabase.com", max_chars=1000),
    )
    assert decision2.tool == "web_scrape"

    # Valid data_analyst decision
    decision3 = AgentToolCallDecision(
        thought="Analyze CSV",
        tool="data_analyst",
        data_analyst_args=DataAnalystArgs(prompt="P", csv_data="col1,col2\n1,2"),
    )
    assert decision3.tool == "data_analyst"

    # Missing web_search_args when tool is web_search raises ValidationError
    with pytest.raises(ValidationError, match="web_search_args must be provided"):
        AgentToolCallDecision(
            thought="Search",
            tool="web_search",
            web_search_args=None,
        )

    # Missing web_scrape_args when tool is web_scrape raises ValidationError
    with pytest.raises(ValidationError, match="web_scrape_args must be provided"):
        AgentToolCallDecision(
            thought="Scrape",
            tool="web_scrape",
            web_scrape_args=None,
        )

    # Missing data_analyst_args when tool is data_analyst raises ValidationError
    with pytest.raises(ValidationError, match="data_analyst_args must be provided"):
        AgentToolCallDecision(
            thought="Analyst",
            tool="data_analyst",
            data_analyst_args=None,
        )

    # Unknown tool name raises ValidationError
    with pytest.raises(ValidationError, match="Invalid tool 'execute_bash'"):
        AgentToolCallDecision(
            thought="Hack",
            tool="execute_bash",
        )


# =====================================================================
# 7. TOOL ROUTER & DISPATCHER STRESS TESTS (dispatch_tool_call)
# =====================================================================

@pytest.mark.asyncio
async def test_dispatch_tool_call_with_pydantic_instance():
    """Verify dispatch_tool_call accepts already-instantiated Pydantic models directly."""
    args = WebSearchArgs(query="hnsw vector index", max_results=3)
    with patch("app.modules.research_agent.tools.search_web", return_value=[]) as mock_search:
        res = await dispatch_tool_call("web_search", args)
        assert res == []
        mock_search.assert_called_once_with(query="hnsw vector index", max_results=3)


@pytest.mark.asyncio
async def test_dispatch_tool_call_with_dictionary():
    """Verify dispatch_tool_call coerces and validates raw python dictionary."""
    dict_payload = {"url": "https://docs.vectronyx.ai/architecture", "max_chars": 800}
    with patch("app.modules.research_agent.tools.scrape_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "parsed content"
        res = await dispatch_tool_call("web_scrape", dict_payload)
        assert res == "parsed content"
        mock_scrape.assert_awaited_once_with(url="https://docs.vectronyx.ai/architecture", max_chars=800)


@pytest.mark.asyncio
async def test_dispatch_tool_call_with_json_string():
    """Verify dispatch_tool_call parses and validates JSON string payload."""
    json_str = json.dumps({"query": "in-memory vs pgvector", "max_results": 5})
    with patch("app.modules.research_agent.tools.search_web", return_value=[]) as mock_search:
        res = await dispatch_tool_call("web_search", json_str)
        assert res == []
        mock_search.assert_called_once_with(query="in-memory vs pgvector", max_results=5)


@pytest.mark.asyncio
async def test_dispatch_tool_call_malformed_json_raises_validation_error():
    """Verify dispatch_tool_call rejects invalid/truncated JSON string."""
    malformed_json = '{"query": "broken json without closing brace'
    with pytest.raises(ValidationError):
        await dispatch_tool_call("web_search", malformed_json)


@pytest.mark.asyncio
async def test_dispatch_tool_call_invalid_field_types_raises_validation_error():
    """Verify dispatch_tool_call rejects invalid argument data types."""
    invalid_payload = {"query": 12345, "max_results": "not_an_int"}
    with pytest.raises(ValidationError):
        await dispatch_tool_call("web_search", invalid_payload)


@pytest.mark.asyncio
async def test_dispatch_tool_call_unknown_tool_raises_value_error():
    """Verify dispatch_tool_call rejects unregistered tools."""
    with pytest.raises(ValueError, match="Unknown tool 'python_repl'"):
        await dispatch_tool_call("python_repl", {"code": "import os"})


@pytest.mark.asyncio
async def test_dispatch_tool_call_casing_and_whitespace_tolerance():
    """Verify dispatch_tool_call tolerates casing and whitespace in tool name."""
    with patch("app.modules.research_agent.tools.search_web", return_value=[]) as mock_search:
        res = await dispatch_tool_call("   WEB_SEARCH   ", {"query": "test", "max_results": 2})
        assert res == []
        mock_search.assert_called_once()


# =====================================================================
# 8. HIGH-CONCURRENCY ASYNC LOAD STRESS TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_dispatch_tool_call_high_concurrency_stress():
    """
    Stress-test the type-safe tool dispatcher with 50 concurrent tool calls
    executed simultaneously via asyncio.gather.
    """
    with patch("app.modules.research_agent.tools.search_web") as mock_search, \
         patch("app.modules.research_agent.tools.scrape_page", new_callable=AsyncMock) as mock_scrape:
        mock_search.return_value = [ResearchSource(title="T", url="https://e.com", snippet="S", domain="e.com")]
        mock_scrape.return_value = "Scraped markdown text"

        tasks = []
        for i in range(50):
            if i % 2 == 0:
                tasks.append(dispatch_tool_call("web_search", {"query": f"vector benchmark {i}", "max_results": 2}))
            else:
                tasks.append(dispatch_tool_call("web_scrape", {"url": f"https://example.com/page{i}", "max_chars": 500}))

        results = await asyncio.gather(*tasks)
        assert len(results) == 50
        for i, res in enumerate(results):
            if i % 2 == 0:
                assert isinstance(res, list)
                assert len(res) == 1
            else:
                assert res == "Scraped markdown text"

        assert mock_search.call_count == 25
        assert mock_scrape.await_count == 25


@pytest.mark.asyncio
async def test_generate_structured_concurrent_load_stress():
    """
    Stress-test generate_structured with 20 simultaneous concurrent calls
    to ensure async context isolation and zero race conditions.
    """
    with patch("app.services.llm.instructor_client._execute_with_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.side_effect = lambda response_model, messages, **kw: response_model(
            summary=f"Processed query: {messages[-1]['content']}",
            confidence=95
        )

        tasks = [
            generate_structured(
                response_model=MockSimpleOutput,
                user_prompt=f"Concurrency stress payload #{idx}",
                provider="groq"
            )
            for idx in range(20)
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 20
        for idx, item in enumerate(results):
            assert isinstance(item, MockSimpleOutput)
            assert f"Concurrency stress payload #{idx}" in item.summary
            assert item.confidence == 95


# =====================================================================
# 9. SELF-CORRECTION FEEDBACK SIMULATION
# =====================================================================

def test_pydantic_validation_error_structure_for_self_correction():
    """
    Verify that Pydantic validation errors generated from invalid tool args
    contain exact field names and descriptive error reasons required by Instructor
    for prompt feedback loop self-correction.
    """
    try:
        WebSearchArgs.model_validate({"query": "   ", "max_results": 25})
    except ValidationError as e:
        errors = e.errors()
        assert len(errors) == 2
        field_names = [err["loc"][0] for err in errors]
        assert "query" in field_names
        assert "max_results" in field_names
        # Ensure errors provide clear feedback for LLM re-prompting
        err_msg_str = str(e)
        assert "query cannot be blank" in err_msg_str
        assert "less than or equal to 10" in err_msg_str
