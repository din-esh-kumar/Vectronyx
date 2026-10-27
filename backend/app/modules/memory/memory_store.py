# backend/app/modules/memory/memory_store.py
"""
Vectronyx Memory Store
======================
High-level memory orchestration layer combining the dual-mode embedder
with PostgreSQL / Supabase storage and vector similarity search.
"""

import json
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.db.models.memory import Memory
from app.db.repositories.memory_repo import save_memory
from app.modules.memory.embedder import get_embedder, BaseEmbedder
from app.modules.memory.schemas import MemoryResponse


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two dense vectors."""
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = sum(x * x for x in v1) ** 0.5
    norm_v2 = sum(y * y for y in v2) ** 0.5
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))


class MemoryStore:
    """Orchestrates memory storage, vectorization, and similarity retrieval."""

    def __init__(self, embedder: Optional[BaseEmbedder] = None):
        self.embedder = embedder or get_embedder()

    async def async_add_memory(
        self,
        db: Session,
        user_id: int,
        content: str,
    ) -> MemoryResponse:
        """Embed text asynchronously and store in PostgreSQL / Supabase."""
        vector = await self.embedder.async_embed_query(content)
        vector_json = json.dumps(vector)

        memory_record: Any = save_memory(
            db=db,
            user_id=user_id,
            content=content,
            embedding=vector_json,
        )

        return MemoryResponse(
            id=int(memory_record.id),
            user_id=int(memory_record.user_id),
            content=str(memory_record.content),
        )

    def add_memory(
        self,
        db: Session,
        user_id: int,
        content: str,
    ) -> MemoryResponse:
        """Embed text synchronously and store in PostgreSQL / Supabase."""
        vector = self.embedder.embed_query(content)
        vector_json = json.dumps(vector)

        memory_record: Any = save_memory(
            db=db,
            user_id=user_id,
            content=content,
            embedding=vector_json,
        )

        return MemoryResponse(
            id=int(memory_record.id),
            user_id=int(memory_record.user_id),
            content=str(memory_record.content),
        )

    async def async_search_memories(
        self,
        db: Session,
        user_id: int,
        query: str,
        limit: int = 5,
        min_threshold: float = 0.0,
    ) -> List[MemoryResponse]:
        """Perform semantic cosine similarity search across user memories."""
        query_vector = await self.embedder.async_embed_query(query)
        memories = db.query(Memory).filter(Memory.user_id == user_id).all()

        scored_memories = []
        for mem in memories:
            raw_emb = getattr(mem, "embedding", None)
            if not raw_emb:
                continue
            try:
                emb = json.loads(str(raw_emb))
                sim = cosine_similarity(query_vector, emb)
                if sim >= min_threshold:
                    scored_memories.append((sim, mem))
            except Exception as e:
                logger.debug(f"Skipping malformed memory id {getattr(mem, 'id', None)}: {e}")

        # Sort descending by similarity
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        top_k = scored_memories[:limit]

        return [
            MemoryResponse(
                id=int(m.id),
                user_id=int(m.user_id),
                content=str(m.content),
                similarity=round(sim, 4),
            )
            for sim, m in top_k
        ]
