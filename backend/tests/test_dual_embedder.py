# backend/tests/test_dual_embedder.py
"""
Test Suite: Dual-Mode Embedding Engine (Zero PyTorch)
===================================================
Tests Google Gemini Cloud Embedder, FastEmbed Local Embedder,
Auto-Fallback mechanism, Cosine Similarity, and FastAPI endpoints.
"""

import pytest
import numpy as np
from app.modules.memory.embedder import (
    GeminiCloudEmbedder,
    FastEmbedLocalEmbedder,
    DualModeEmbedder,
    get_embedder,
    embed_text,
    embed_texts,
    async_embed_text,
    async_embed_texts,
)
from app.modules.memory.memory_store import cosine_similarity
from app.core.config import settings


def test_cosine_similarity_identity():
    """Identical vectors must have cosine similarity of 1.0."""
    v1 = [1.0, 0.0, 0.5, -0.2]
    sim = cosine_similarity(v1, v1)
    assert pytest.approx(sim, 0.0001) == 1.0


def test_cosine_similarity_orthogonal():
    """Orthogonal vectors must have cosine similarity of 0.0."""
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    sim = cosine_similarity(v1, v2)
    assert pytest.approx(sim, 0.0001) == 0.0


def test_fastembed_local_offline():
    """Verify FastEmbed runs 100% locally with ONNX (zero PyTorch)."""
    embedder = FastEmbedLocalEmbedder()
    assert embedder.provider_name == "fastembed_local"

    # Single embedding
    vec = embedder.embed_query("Vectronyx autonomous intelligence")
    assert isinstance(vec, list)
    assert len(vec) == embedder.dimension
    assert all(isinstance(x, float) for x in vec)

    # Batch embedding
    batch = embedder.embed_documents(["First query", "Second query"])
    assert len(batch) == 2
    assert len(batch[0]) == embedder.dimension
    assert len(batch[1]) == embedder.dimension


@pytest.mark.asyncio
async def test_fastembed_local_async():
    """Verify FastEmbed async methods work without blocking event loop."""
    embedder = FastEmbedLocalEmbedder()
    vec = await embedder.async_embed_query("Async query test")
    assert isinstance(vec, list)
    assert len(vec) == embedder.dimension

    batch = await embedder.async_embed_documents(["Doc A", "Doc B"])
    assert len(batch) == 2


def test_gemini_cloud_online():
    """Verify Google Gemini Cloud Embedder with live API key."""
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not configured.")

    embedder = GeminiCloudEmbedder()
    assert embedder.provider_name == "gemini_cloud"
    assert embedder.dimension == settings.VECTOR_DIMENSION

    # Single text
    vec = embedder.embed_query("Vectronyx Cloud Embedding Test")
    assert isinstance(vec, list)
    assert len(vec) == settings.VECTOR_DIMENSION
    assert all(isinstance(x, float) for x in vec)


@pytest.mark.asyncio
async def test_gemini_cloud_async_and_batch():
    """Verify Gemini batch and async endpoints."""
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not configured.")

    embedder = GeminiCloudEmbedder()
    vec = await embedder.async_embed_query("Async Gemini Test")
    assert len(vec) == settings.VECTOR_DIMENSION

    batch = await embedder.async_embed_documents(["Vectronyx Alpha", "Vectronyx Beta"])
    assert len(batch) == 2
    assert len(batch[0]) == settings.VECTOR_DIMENSION
    assert len(batch[1]) == settings.VECTOR_DIMENSION


def test_dual_mode_forced_fastembed():
    """Verify DualModeEmbedder respects forced fastembed mode."""
    dual = DualModeEmbedder(mode="fastembed")
    vec = dual.embed_query("Forced FastEmbed test")
    assert len(vec) == dual._fastembed.dimension
    assert dual.provider_name == "fastembed_local"


def test_dual_mode_auto_fallback():
    """Verify auto mode seamlessly falls back to FastEmbed if Gemini fails."""
    # Create a Gemini embedder with an invalid dummy key
    bad_gemini = GeminiCloudEmbedder(api_key="AIzaSy_INVALID_KEY_FOR_TESTING")
    good_fastembed = FastEmbedLocalEmbedder()

    dual = DualModeEmbedder(
        mode="auto",
        gemini_embedder=bad_gemini,
        fastembed_embedder=good_fastembed,
    )

    # Should not raise exception; must gracefully fall back to FastEmbed
    vec = dual.embed_query("Test fallback handling")
    assert isinstance(vec, list)
    assert len(vec) == good_fastembed.dimension
    assert dual.provider_name == "fastembed_local"


def test_memory_routes_api():
    """Test FastAPI memory endpoints using TestClient."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.modules.memory.routes import router as memory_router

    test_app = FastAPI()
    test_app.include_router(memory_router, prefix="/api/memory")
    client = TestClient(test_app)

    # 1. Test status endpoint
    res_status = client.get("/api/memory/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert "active_provider" in data
    assert "offline_fastembed" in data

    # 2. Test embed endpoint in fastembed mode
    res_embed = client.post("/api/memory/embed?text=TestText&mode=fastembed")
    assert res_embed.status_code == 200
    embed_data = res_embed.json()
    assert embed_data["provider"] == "fastembed_local"
    assert len(embed_data["embedding"]) > 0
