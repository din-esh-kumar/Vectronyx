# backend/app/modules/research_agent/schemas.py
from pydantic import BaseModel, Field
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


# ============================================================
# Type-Safe Agent Tool Call & Structured Output Models (Instructor)
# ============================================================

class WebSearchArgs(BaseModel):
    """Guaranteed type-safe arguments for DuckDuckGo web search tool."""
    query: str = Field(..., description="Target search query keywords")
    max_results: int = Field(default=4, ge=1, le=10, description="Maximum number of search results to retrieve (1-10)")


class WebScrapeArgs(BaseModel):
    """Guaranteed type-safe arguments for Trafilatura web scraping tool."""
    url: str = Field(..., description="Target HTTP or HTTPS URL to fetch and parse")
    max_chars: int = Field(default=1500, ge=100, le=10000, description="Maximum number of clean characters to extract")


class DataAnalystArgs(BaseModel):
    """Guaranteed type-safe arguments for invoking the Intelligent Data Analyst & Dashboard Generator."""
    prompt: str = Field(..., description="Analytical mandate or user inquiry guiding dashboard and KPI synthesis")
    csv_data: str = Field(..., description="Raw CSV string content of the dataset to profile and analyze")
    dataset_name: Optional[str] = Field(default="dataset.csv", description="Identifier filename for the dataset")


class ResearchPlanningDecision(BaseModel):
    """Structured plan emitted by the ReAct agent via Instructor with guaranteed types."""
    thought: str = Field(..., description="Agent reasoning analyzing inquiry complexity and information needs")
    search_args: WebSearchArgs = Field(..., description="Type-safe DuckDuckGo search arguments")
    scrape_required: bool = Field(default=True, description="Whether deep URL article scraping is needed")
    scrape_max_chars: int = Field(default=1200, ge=200, le=5000, description="Character limit for the scraper")


class ResearchFindingsExtraction(BaseModel):
    """Structured extraction of key findings and summary validated by Instructor."""
    executive_summary: str = Field(..., description="Authoritative 2-sentence executive summary")
    confidence_score: int = Field(default=95, ge=50, le=100, description="Overall confidence score from 50 to 100")
    key_findings: List[KeyFinding] = Field(..., min_length=1, max_length=5, description="Structured key findings")
