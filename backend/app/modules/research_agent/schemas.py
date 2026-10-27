# backend/app/modules/research_agent/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

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
