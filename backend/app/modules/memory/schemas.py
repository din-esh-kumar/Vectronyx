# backend/app/modules/memory/schemas.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MemoryCreate(BaseModel):
    """Payload for storing a new contextual memory."""
    content: str = Field(..., min_length=1, description="Memory text or note content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary metadata key-values")


class MemoryResponse(BaseModel):
    """Response returned upon saving or fetching a memory."""
    id: int
    user_id: int
    content: str
    similarity: Optional[float] = None
    created_at: Optional[datetime] = None


class MemorySearchQuery(BaseModel):
    """Payload for performing semantic search over memory store."""
    query: str = Field(..., min_length=1, description="Query string for cosine similarity search")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum items to return")
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity threshold")


class EmbeddingResponse(BaseModel):
    """Inspection response showing active provider and vector metadata."""
    provider: str
    model: str
    dimension: int
    embedding: List[float]
