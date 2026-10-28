# backend/app/modules/research_agent/schemas.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Union

class ResearchSource(BaseModel):
    title: str
    url: str
    snippet: str
    reliability: int = 95
    domain: str

class ReActStep(BaseModel):
    step: int
    thought: str
    action: str
    observation: str

class KeyFinding(BaseModel):
    title: str
    description: str
    impact: str = Field(default="High", description="High, Medium, or Critical")
    category: str

class ResearchReport(BaseModel):
    id: str
    query: str
    timestamp: str
    executiveSummary: str
    confidenceScore: int
    timeElapsed: str
    keyFindings: List[KeyFinding]
    sources: List[ResearchSource]
    reactTraces: List[ReActStep]
    synthesisMarkdown: str

class ResearchStreamRequest(BaseModel):
    query: str
    depth: Optional[str] = "react"
    domain_filter: Optional[str] = "all"
    csv_data: Optional[str] = None


# ============================================================
# Type-Safe Agent Tool Call & Structured Output Models (Instructor)
# ============================================================

class WebSearchArgs(BaseModel):
    """Guaranteed type-safe arguments for DuckDuckGo web search tool."""
    query: str = Field(..., min_length=1, description="Target search query keywords")
    max_results: int = Field(default=4, ge=1, le=10, description="Maximum number of search results to retrieve (1-10)")

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("query cannot be blank or whitespace-only")
        return s


class WebScrapeArgs(BaseModel):
    """Guaranteed type-safe arguments for Trafilatura web scraping tool."""
    url: str = Field(..., min_length=4, description="Target HTTP or HTTPS URL to fetch and parse")
    max_chars: int = Field(default=1500, ge=100, le=10000, description="Maximum number of clean characters to extract")

    @field_validator("url")
    @classmethod
    def url_must_have_valid_scheme(cls, v: str) -> str:
        s = v.strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError("url must begin with http:// or https://")
        return s


class DataAnalystArgs(BaseModel):
    """Guaranteed type-safe arguments for invoking the Intelligent Data Analyst & Dashboard Generator."""
    prompt: str = Field(..., min_length=1, description="Analytical mandate or user inquiry guiding dashboard and KPI synthesis")
    csv_data: str = Field(..., min_length=5, description="Raw CSV string content of the dataset to profile and analyze")
    dataset_name: Optional[str] = Field(default="dataset.csv", description="Identifier filename for the dataset")

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("prompt cannot be blank or whitespace-only")
        return s


class AgentToolCallDecision(BaseModel):
    """Guaranteed type-safe agent tool call decision emitted via Instructor."""
    thought: str = Field(..., description="Agent reasoning analyzing next operational step")
    tool: str = Field(..., description="Target tool: 'web_search', 'web_scrape', or 'data_analyst'")
    web_search_args: Optional[WebSearchArgs] = Field(None, description="Arguments when tool is web_search")
    web_scrape_args: Optional[WebScrapeArgs] = Field(None, description="Arguments when tool is web_scrape")
    data_analyst_args: Optional[DataAnalystArgs] = Field(None, description="Arguments when tool is data_analyst")

    @model_validator(mode="after")
    def validate_tool_and_args(self) -> "AgentToolCallDecision":
        valid_tools = {"web_search", "web_scrape", "data_analyst"}
        normalized = self.tool.strip().lower()
        if normalized not in valid_tools:
            raise ValueError(f"Invalid tool '{self.tool}'. Must be one of: {list(valid_tools)}")
        if normalized == "web_search" and not self.web_search_args:
            raise ValueError("web_search_args must be provided when tool is 'web_search'")
        if normalized == "web_scrape" and not self.web_scrape_args:
            raise ValueError("web_scrape_args must be provided when tool is 'web_scrape'")
        if normalized == "data_analyst" and not self.data_analyst_args:
            raise ValueError("data_analyst_args must be provided when tool is 'data_analyst'")
        return self


class ResearchPlanningDecision(BaseModel):
    """Structured plan emitted by the ReAct agent via Instructor with guaranteed types."""
    thought: str = Field(..., description="Agent reasoning analyzing inquiry complexity and information needs")
    search_args: WebSearchArgs = Field(..., description="Type-safe DuckDuckGo search arguments")
    scrape_required: bool = Field(default=True, description="Whether deep URL article scraping is needed")
    scrape_max_chars: int = Field(default=1200, ge=200, le=5000, description="Character limit for the scraper")
    data_analyst_required: bool = Field(default=False, description="Whether dataset profiling/dashboard analysis is needed")
    data_analyst_args: Optional[DataAnalystArgs] = Field(default=None, description="Type-safe Data Analyst arguments if CSV present")


class ResearchFindingsExtraction(BaseModel):
    """Structured extraction of key findings and summary validated by Instructor."""
    executive_summary: str = Field(..., description="Authoritative 2-sentence executive summary")
    confidence_score: int = Field(default=95, ge=50, le=100, description="Overall confidence score from 50 to 100")
    key_findings: List[KeyFinding] = Field(..., min_length=1, max_length=5, description="Structured key findings")
