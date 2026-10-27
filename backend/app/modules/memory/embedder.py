# backend/app/modules/memory/embedder.py
"""
Vectronyx Dual-Mode Embedding Engine
====================================
High-performance, lightweight embedding architecture with ZERO PyTorch dependencies.
Supports:
1. Online Cloud: Google Gemini Embeddings (gemini-embedding-001 / gemini-embedding-2)
   - Zero local model files, sub-100ms boot, native Matryoshka dimension scaling (e.g. 768d).
2. Offline Local: FastEmbed (ONNX Runtime by Qdrant)
   - 100% offline, ~80MB lightweight wheels, runs on CPU without PyTorch or MSVC.
3. Auto-Fallback: Tries Gemini online; seamlessly falls back to FastEmbed when offline.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional, Union
import httpx
from loguru import logger
from app.core.config import settings

try:
    import anyio
except ImportError:
    anyio = None


class BaseEmbedder(ABC):
    """Abstract base class for Vectronyx embedders."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model being utilized."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query or text string synchronously."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document strings synchronously."""
        pass

    @abstractmethod
    async def async_embed_query(self, text: str) -> List[float]:
        """Embed a single query asynchronously without blocking event loop."""
        pass

    @abstractmethod
    async def async_embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document strings asynchronously."""
        pass


class GeminiCloudEmbedder(BaseEmbedder):
    """
    Online Cloud Embedder using Google Generative Language API.
    Zero local PyTorch or ONNX dependencies, uses httpx REST calls.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout: float = 12.0,
    ):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model_name = model_name or settings.EMBEDDING_MODEL or "gemini-embedding-001"
        self._dimension = dimension or settings.VECTOR_DIMENSION or 768
        self._timeout = timeout

        if not self._api_key:
            logger.warning("GeminiCloudEmbedder initialized without GEMINI_API_KEY.")

    @property
    def provider_name(self) -> str:
        return "gemini_cloud"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_api_url(self, method: str = "embedContent") -> str:
        clean_model = self._model_name.replace("models/", "")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:{method}?key={self._api_key}"

    def embed_query(self, text: str) -> List[float]:
        """Synchronously embed a single text string."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiCloudEmbedder.")

        url = self._get_api_url("embedContent")
        payload = {
            "model": f"models/{self._model_name.replace('models/', '')}",
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": self._dimension,
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Synchronously embed a batch of texts using batchEmbedContents."""
        if not texts:
            return []
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiCloudEmbedder.")

        url = self._get_api_url("batchEmbedContents")
        model_path = f"models/{self._model_name.replace('models/', '')}"
        
        requests = [
            {
                "model": model_path,
                "content": {"parts": [{"text": text}]},
                "output_dimensionality": self._dimension,
            }
            for text in texts
        ]

        with httpx.Client(timeout=self._timeout * 2) as client:
            response = client.post(url, json={"requests": requests})
            response.raise_for_status()
            data = response.json()
            return [entry["values"] for entry in data["embeddings"]]

    async def async_embed_query(self, text: str) -> List[float]:
        """Asynchronously embed a single text string."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiCloudEmbedder.")

        url = self._get_api_url("embedContent")
        payload = {
            "model": f"models/{self._model_name.replace('models/', '')}",
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": self._dimension,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]

    async def async_embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Asynchronously embed a batch of texts using batchEmbedContents."""
        if not texts:
            return []
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiCloudEmbedder.")

        url = self._get_api_url("batchEmbedContents")
        model_path = f"models/{self._model_name.replace('models/', '')}"

        requests = [
            {
                "model": model_path,
                "content": {"parts": [{"text": text}]},
                "output_dimensionality": self._dimension,
            }
            for text in texts
        ]

        async with httpx.AsyncClient(timeout=self._timeout * 2) as client:
            response = await client.post(url, json={"requests": requests})
            response.raise_for_status()
            data = response.json()
            return [entry["values"] for entry in data["embeddings"]]


class FastEmbedLocalEmbedder(BaseEmbedder):
    """
    Offline Local Embedder using Qdrant's FastEmbed (ONNX Runtime).
    100% offline, zero PyTorch dependency, lazy loading to preserve startup speed.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        self._model_name = model_name or getattr(settings, "FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        self._cache_dir = cache_dir
        self._model = None
        self._dimension = None

    def _ensure_loaded(self):
        """Lazy load the ONNX model upon first invocation."""
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading FastEmbed ONNX model: {self._model_name}...")
                self._model = TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=self._cache_dir,
                )
                # Test vector to ascertain true output dimension
                sample = list(self._model.embed(["test"]))[0]
                self._dimension = len(sample)
                logger.info(f"FastEmbed model {self._model_name} loaded successfully (dim={self._dimension}).")
            except Exception as e:
                logger.error(f"Failed to load FastEmbed model {self._model_name}: {e}")
                raise

    def _get_model(self):
        """Ensure ONNX model is loaded and return non-null reference."""
        if self._model is None:
            self._ensure_loaded()
        assert self._model is not None, "FastEmbed model failed to load"
        return self._model

    @property
    def provider_name(self) -> str:
        return "fastembed_local"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._ensure_loaded()
        return self._dimension or 384

    def embed_query(self, text: str) -> List[float]:
        model = self._get_model()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = list(model.embed(texts))
        return [e.tolist() for e in embeddings]

    async def async_embed_query(self, text: str) -> List[float]:
        if anyio:
            return await anyio.to_thread.run_sync(self.embed_query, text)
        return self.embed_query(text)

    async def async_embed_documents(self, texts: List[str]) -> List[List[float]]:
        if anyio:
            return await anyio.to_thread.run_sync(self.embed_documents, texts)
        return self.embed_documents(texts)


class DualModeEmbedder(BaseEmbedder):
    """
    Unified Dual-Mode Embedder with intelligent fallback.
    - If mode is 'gemini', routes exclusively to GeminiCloudEmbedder.
    - If mode is 'fastembed', routes exclusively to FastEmbedLocalEmbedder.
    - If mode is 'auto', tries GeminiCloudEmbedder first; if offline or failing,
      automatically falls back to FastEmbedLocalEmbedder.
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        gemini_embedder: Optional[GeminiCloudEmbedder] = None,
        fastembed_embedder: Optional[FastEmbedLocalEmbedder] = None,
    ):
        self._mode = (mode or getattr(settings, "EMBEDDING_PROVIDER", "auto")).lower()
        self._gemini = gemini_embedder or GeminiCloudEmbedder()
        self._fastembed = fastembed_embedder or FastEmbedLocalEmbedder()
        self._active_provider = None

    @property
    def provider_name(self) -> str:
        if self._mode == "fastembed":
            return self._fastembed.provider_name
        elif self._mode == "gemini":
            return self._gemini.provider_name
        return self._active_provider or "auto (gemini/fastembed)"

    @property
    def model_name(self) -> str:
        if self._mode == "fastembed":
            return self._fastembed.model_name
        elif self._mode == "gemini":
            return self._gemini.model_name
        return f"{self._gemini.model_name} [auto-fallback to {self._fastembed.model_name}]"

    @property
    def dimension(self) -> int:
        if self._mode == "fastembed":
            return self._fastembed.dimension
        return self._gemini.dimension

    def embed_query(self, text: str) -> List[float]:
        if self._mode == "fastembed":
            self._active_provider = self._fastembed.provider_name
            return self._fastembed.embed_query(text)

        if self._mode == "gemini":
            self._active_provider = self._gemini.provider_name
            return self._gemini.embed_query(text)

        # Auto Mode: Try Gemini first, fallback to FastEmbed
        try:
            res = self._gemini.embed_query(text)
            self._active_provider = self._gemini.provider_name
            return res
        except Exception as exc:
            logger.warning(f"Gemini cloud embedding failed ({exc}). Falling back to local FastEmbed...")
            self._active_provider = self._fastembed.provider_name
            return self._fastembed.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self._mode == "fastembed":
            self._active_provider = self._fastembed.provider_name
            return self._fastembed.embed_documents(texts)

        if self._mode == "gemini":
            self._active_provider = self._gemini.provider_name
            return self._gemini.embed_documents(texts)

        # Auto Mode: Try Gemini first, fallback to FastEmbed
        try:
            res = self._gemini.embed_documents(texts)
            self._active_provider = self._gemini.provider_name
            return res
        except Exception as exc:
            logger.warning(f"Gemini batch embedding failed ({exc}). Falling back to local FastEmbed...")
            self._active_provider = self._fastembed.provider_name
            return self._fastembed.embed_documents(texts)

    async def async_embed_query(self, text: str) -> List[float]:
        if self._mode == "fastembed":
            self._active_provider = self._fastembed.provider_name
            return await self._fastembed.async_embed_query(text)

        if self._mode == "gemini":
            self._active_provider = self._gemini.provider_name
            return await self._gemini.async_embed_query(text)

        # Auto Mode
        try:
            res = await self._gemini.async_embed_query(text)
            self._active_provider = self._gemini.provider_name
            return res
        except Exception as exc:
            logger.warning(f"Gemini async embedding failed ({exc}). Falling back to local FastEmbed...")
            self._active_provider = self._fastembed.provider_name
            return await self._fastembed.async_embed_query(text)

    async def async_embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self._mode == "fastembed":
            self._active_provider = self._fastembed.provider_name
            return await self._fastembed.async_embed_documents(texts)

        if self._mode == "gemini":
            self._active_provider = self._gemini.provider_name
            return await self._gemini.async_embed_documents(texts)

        # Auto Mode
        try:
            res = await self._gemini.async_embed_documents(texts)
            self._active_provider = self._gemini.provider_name
            return res
        except Exception as exc:
            logger.warning(f"Gemini async batch embedding failed ({exc}). Falling back to local FastEmbed...")
            self._active_provider = self._fastembed.provider_name
            return await self._fastembed.async_embed_documents(texts)


# Singleton embedder instance for Vectronyx
_global_embedder: Optional[DualModeEmbedder] = None


def get_embedder(mode: Optional[str] = None) -> DualModeEmbedder:
    """Get or initialize the global DualModeEmbedder instance."""
    global _global_embedder
    if _global_embedder is None or mode is not None:
        _global_embedder = DualModeEmbedder(mode=mode)
    return _global_embedder


def embed_text(text: str) -> List[float]:
    """Convenience helper to embed a single query text."""
    return get_embedder().embed_query(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenience helper to embed multiple texts."""
    return get_embedder().embed_documents(texts)


async def async_embed_text(text: str) -> List[float]:
    """Convenience helper to asynchronously embed a single text."""
    return await get_embedder().async_embed_query(text)


async def async_embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenience helper to asynchronously embed multiple texts."""
    return await get_embedder().async_embed_documents(texts)
