# backend/app/modules/memory/routes.py
"""
Memory API Endpoints
====================
Provides memory storage, semantic search, and embedding diagnostics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.migrations.database import SessionLocal
from app.modules.memory.embedder import get_embedder, GeminiCloudEmbedder, FastEmbedLocalEmbedder
from app.modules.memory.schemas import (
    MemoryCreate,
    MemoryResponse,
    MemorySearchQuery,
    EmbeddingResponse,
)
from app.modules.memory.memory_store import MemoryStore

router = APIRouter(tags=["Contextual Memory & Embeddings"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/status")
def get_embedding_status():
    """Returns the operational status of both online and offline embedders."""
    embedder = get_embedder()
    gemini = GeminiCloudEmbedder()
    fastembed = FastEmbedLocalEmbedder()

    online_status = "unconfigured"
    if gemini._api_key:
        try:
            sample = gemini.embed_query("ping")
            online_status = f"healthy (dim={len(sample)})"
        except Exception as e:
            online_status = f"error: {str(e)}"

    offline_status = "available"
    try:
        sample_off = fastembed.embed_query("ping")
        offline_status = f"healthy (dim={len(sample_off)})"
    except Exception as e:
        offline_status = f"error: {str(e)}"

    return {
        "active_provider": embedder.provider_name,
        "active_model": embedder.model_name,
        "active_dimension": embedder.dimension,
        "online_gemini": {
            "status": online_status,
            "model": gemini.model_name,
            "target_dimension": gemini.dimension,
        },
        "offline_fastembed": {
            "status": offline_status,
            "model": fastembed.model_name,
            "dimension": fastembed.dimension,
        },
    }


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(
    text: str = Query(..., description="Text string to embed"),
    mode: Optional[str] = Query(None, description="'gemini', 'fastembed', or 'auto'"),
):
    """Generate and inspect an embedding vector in real-time."""
    embedder = get_embedder(mode=mode) if mode else get_embedder()
    try:
        vector = await embedder.async_embed_query(text)
        return EmbeddingResponse(
            provider=embedder.provider_name,
            model=embedder.model_name,
            dimension=len(vector),
            embedding=vector,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")


@router.post("/add", response_model=MemoryResponse)
async def add_memory_endpoint(
    payload: MemoryCreate,
    user_id: int = Query(1, description="Authenticated User ID"),
    db: Session = Depends(get_db),
):
    """Save text memory with dense vector embedding."""
    store = MemoryStore()
    try:
        return await store.async_add_memory(db=db, user_id=user_id, content=payload.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save memory: {e}")


@router.post("/search", response_model=List[MemoryResponse])
async def search_memories_endpoint(
    payload: MemorySearchQuery,
    user_id: int = Query(1, description="Authenticated User ID"),
    db: Session = Depends(get_db),
):
    """Search user memories via semantic similarity."""
    store = MemoryStore()
    try:
        return await store.async_search_memories(
            db=db,
            user_id=user_id,
            query=payload.query,
            limit=payload.limit,
            min_threshold=payload.threshold or 0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory search failed: {e}")
