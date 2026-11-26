# backend/app/services/llm/instructor_client.py
"""
Centralized Instructor Structured Outputs Client for Vectronyx AI Workbench.
Wraps Groq Cloud, Google Gemini (GenAI), and NVIDIA NIM client calls with automatic Pydantic
validation, guaranteeing zero JSON/XML parsing errors, self-correcting feedback loops,
and type-safe tool invocations.
"""
import asyncio
import contextvars
import logging
import re
import time
from typing import Type, TypeVar, Optional, Any, List, Dict, cast
from pydantic import BaseModel
import instructor
from instructor import Mode

from app.core.config import settings

logger = logging.getLogger("vectronyx.instructor")

T = TypeVar("T", bound=BaseModel)


class InstructorStructuredOutputError(RuntimeError):
    """Raised when structured LLM output generation fails across all available providers."""
    pass


def _normalize_mode(mode: Any) -> Mode:
    """Normalizes string or enum representation of Instructor Mode."""
    if isinstance(mode, Mode):
        return mode
    if isinstance(mode, str):
        cleaned = mode.strip().lower().replace("mode.", "")
        if cleaned in ("json",):
            return Mode.JSON
        if cleaned in ("tools", "tool_call", "function"):
            return Mode.TOOLS
        if cleaned in ("md_json",):
            return Mode.MD_JSON
    return Mode.TOOLS


def get_groq_instructor(
    api_key: Optional[str] = None,
    mode: Optional[Any] = None,
) -> instructor.AsyncInstructor:
    """
    Creates an AsyncInstructor client wrapping Groq Cloud with appropriate parsing mode.
    Accepts Mode enum or case-insensitive string ('json', 'tools', 'md_json').
    """
    raw_key = api_key if api_key is not None else settings.GROQ_API_KEY
    key = raw_key.strip() if raw_key else ""
    if not key:
        raise ValueError("GROQ_API_KEY is not configured or is empty.")
    from groq import AsyncGroq
    client = AsyncGroq(api_key=key)
    selected_mode = _normalize_mode(mode) if mode is not None else Mode.TOOLS
    return instructor.from_groq(client, mode=selected_mode)


_TOOL_CALLING_ERR_PATTERNS = (
    "tool choice is required",
    "tool_use_failed",
    "tool_calls",
    "failed to generate tool call",
    "does not support tool",
    "tools is not supported",
    "failed_generation",
)

_NVIDIA_PROVIDER_ALIASES = frozenset({"nvidia", "nvidia_nim", "nvidia-nim", "nim"})

_DEFAULT_RATE_LIMIT_COOLDOWN_SEC = 30.0
_PROVIDER_COOLDOWNS: Dict[str, float] = {}
_LAST_PROVIDER_USED: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "vectronyx_last_provider_used", default=None
)

_RATE_LIMIT_PATTERNS = (
    "429",
    "rate limit",
    "rate_limit",
    "rate-limit",
    "too many requests",
    "requests per minute",
    "resource_exhausted",
    "resource exhausted",
    "quota exceeded",
    "quota_exceeded",
)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detect HTTP 429 / RPM / quota exhaustion errors across LLM providers."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status == 429:
        return True
    err_str = str(exc).lower()
    return any(p in err_str for p in _RATE_LIMIT_PATTERNS)


def _extract_retry_after_seconds(exc: Exception) -> float:
    """Parse retry-after seconds from an exception or default to 30s."""
    err_str = str(exc)
    match = re.search(r"(?:retry[- ]after|try again in)\s*[:=]?\s*(\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
    if match:
        try:
            return max(5.0, min(60.0, float(match.group(1))))
        except ValueError:
            pass
    return _DEFAULT_RATE_LIMIT_COOLDOWN_SEC


def mark_provider_cooldown(
    provider: str,
    exc: Optional[Exception] = None,
    seconds: Optional[float] = None,
) -> float:
    """Place a rate-limited provider on temporary cooldown so calls route to healthy providers."""
    ttl = seconds if seconds is not None else (_extract_retry_after_seconds(exc) if exc else _DEFAULT_RATE_LIMIT_COOLDOWN_SEC)
    _PROVIDER_COOLDOWNS[provider] = time.monotonic() + ttl
    return ttl


def is_provider_on_cooldown(provider: str) -> bool:
    """Return True if provider is currently cooling down after a rate-limit response."""
    expires_at = _PROVIDER_COOLDOWNS.get(provider)
    if expires_at is None:
        return False
    if time.monotonic() >= expires_at:
        _PROVIDER_COOLDOWNS.pop(provider, None)
        return False
    return True


def clear_provider_cooldowns() -> None:
    """Reset all provider cooldown timers (useful in tests)."""
    _PROVIDER_COOLDOWNS.clear()


def get_last_provider_used() -> Optional[str]:
    """Return the provider name that actually fulfilled the latest generate_structured call."""
    return _LAST_PROVIDER_USED.get()


def normalize_provider_name(provider: Optional[str]) -> str:
    cleaned = (provider or "").lower().strip()
    if cleaned in _NVIDIA_PROVIDER_ALIASES:
        return "nvidia"
    return cleaned


def get_configured_providers() -> List[str]:
    """
    Return configured providers ordered by active LLM_PROVIDER preference,
    putting healthy (non-cooldown) providers ahead of cooling ones.
    """
    configured: List[str] = []
    if (settings.NVIDIA_API_KEY or "").strip():
        configured.append("nvidia")
    if (settings.GROQ_API_KEY or "").strip():
        configured.append("groq")
    if (settings.GEMINI_API_KEY or "").strip():
        configured.append("gemini")

    preferred = normalize_provider_name(settings.LLM_PROVIDER)
    if preferred in configured:
        configured.remove(preferred)
        configured.insert(0, preferred)

    healthy = [p for p in configured if not is_provider_on_cooldown(p)]
    cooling = [p for p in configured if is_provider_on_cooldown(p)]
    return healthy + cooling


def format_provider_model_label(provider: str) -> str:
    """Format '<provider>/<model>' telemetry label for the given provider."""
    norm = normalize_provider_name(provider)
    if norm == "nvidia":
        return f"nvidia/{settings.NVIDIA_MODEL}"
    if norm == "groq":
        return f"groq/{settings.GROQ_MODEL}"
    return f"gemini/{settings.GEMINI_MODEL}"


def get_genai_instructor(
    api_key: Optional[str] = None,
    mode: Any = Mode.TOOLS,
) -> instructor.AsyncInstructor:
    """
    Creates an AsyncInstructor client wrapping Google GenAI (Gemini).
    """
    raw_key = api_key if api_key is not None else settings.GEMINI_API_KEY
    key = raw_key.strip() if raw_key else ""
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured or is empty.")
    from google import genai
    client = genai.Client(api_key=key)
    selected_mode = _normalize_mode(mode)
    return instructor.from_genai(client, use_async=True, mode=selected_mode)


def get_nvidia_instructor(
    api_key: Optional[str] = None,
    mode: Optional[Any] = None,
    base_url: Optional[str] = None,
) -> instructor.AsyncInstructor:
    """
    Creates an AsyncInstructor client wrapping NVIDIA NIM's OpenAI-compatible API.
    """
    raw_key = api_key if api_key is not None else settings.NVIDIA_API_KEY
    key = raw_key.strip() if raw_key else ""
    if not key:
        raise ValueError("NVIDIA_API_KEY is not configured or is empty.")
    from openai import AsyncOpenAI
    resolved_base_url = (base_url or settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1").strip()
    client = AsyncOpenAI(api_key=key, base_url=resolved_base_url, max_retries=0)
    selected_mode = _normalize_mode(mode) if mode is not None else Mode.TOOLS
    return instructor.from_openai(client, mode=selected_mode)


async def _execute_with_groq(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 16384,
    mode: Optional[Any] = None,
) -> T:
    groq_model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
    
    # Auto-select mode: models starting with "openai/" prefer JSON mode over tool calling on Groq
    if mode is not None:
        target_mode = _normalize_mode(mode)
    elif groq_model.startswith("openai/"):
        target_mode = Mode.JSON
    else:
        target_mode = Mode.TOOLS

    try:
        client = get_groq_instructor(mode=target_mode)
        return await client.create(
            response_model=response_model,
            messages=cast(Any, messages),
            model=groq_model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        if _is_rate_limit_error(e):
            raise
        err_str = str(e).lower()
        # If Groq free-tier TPM (8K) rejects prompt + max_tokens (HTTP 413), step down max_tokens on the active model
        if (
            "max_tokens" in err_str
            or "request too large" in err_str
            or "tokens per minute" in err_str
            or "error code: 413" in err_str
        ) and max_tokens > 2500:
            stepped_tokens = 2500
            logger.info(
                f"Groq {groq_model} hit TPM/size limit with max_tokens={max_tokens}; retrying with max_tokens={stepped_tokens}..."
            )
            client = get_groq_instructor(mode=target_mode)
            return await client.create(
                response_model=response_model,
                messages=cast(Any, messages),
                model=groq_model,
                max_retries=max_retries,
                temperature=temperature,
                max_tokens=stepped_tokens,
            )
        # If tool choice failed, automatically retry with JSON mode
        if target_mode != Mode.JSON and any(p in err_str for p in _TOOL_CALLING_ERR_PATTERNS):
            logger.info(f"Groq tool calling rejected by {groq_model}. Retrying with Instructor Mode.JSON...")
            client = get_groq_instructor(mode=Mode.JSON)
            return await client.create(
                response_model=response_model,
                messages=cast(Any, messages),
                model=groq_model,
                max_retries=max_retries,
                temperature=temperature,
                max_tokens=min(max_tokens, 4096),
            )
        raise


async def _execute_with_nvidia(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 16384,
    mode: Optional[Any] = None,
) -> T:
    nvidia_model = model or settings.NVIDIA_MODEL or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    target_mode = _normalize_mode(mode) if mode is not None else Mode.TOOLS
    try:
        client = get_nvidia_instructor(mode=target_mode)
        return await client.create(
            response_model=response_model,
            messages=cast(Any, messages),
            model=nvidia_model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        if _is_rate_limit_error(e):
            raise
        err_str = str(e).lower()
        if (
            "max_tokens" in err_str
            or "context length" in err_str
            or "error code: 413" in err_str
        ) and max_tokens > 4096:
            stepped_tokens = 4096
            logger.info(
                f"NVIDIA NIM {nvidia_model} hit payload/token limit with max_tokens={max_tokens}; retrying with max_tokens={stepped_tokens}..."
            )
            client = get_nvidia_instructor(mode=target_mode)
            return await client.create(
                response_model=response_model,
                messages=cast(Any, messages),
                model=nvidia_model,
                max_retries=max_retries,
                temperature=temperature,
                max_tokens=stepped_tokens,
            )
        if target_mode != Mode.JSON and any(p in err_str for p in _TOOL_CALLING_ERR_PATTERNS):
            logger.info(f"NVIDIA NIM tool calling rejected by {nvidia_model}. Retrying with Instructor Mode.JSON...")
            client = get_nvidia_instructor(mode=Mode.JSON)
            return await client.create(
                response_model=response_model,
                messages=cast(Any, messages),
                model=nvidia_model,
                max_retries=max_retries,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise


async def _execute_with_gemini(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 16384,
) -> T:
    client = get_genai_instructor()
    gemini_model = model or settings.GEMINI_MODEL or "gemini-3.8-flash"
    fallback_model = "gemini-3.8-flash" if gemini_model != "gemini-3.8-flash" else "gemini-3.5-flash-lite"
    try:
        return await client.create(
            response_model=response_model,
            messages=cast(Any, messages),
            model=gemini_model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        if _is_rate_limit_error(e):
            raise
        logger.warning(f"Gemini {gemini_model} failed ({e}); falling back to {fallback_model}")
        return await client.create(
            response_model=response_model,
            messages=cast(Any, messages),
            model=fallback_model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )


async def generate_structured(
    response_model: Type[T],
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 16384,
) -> T:
    """
    Synthesizes guaranteed type-safe Pydantic structured output using Instructor.
    
    Features:
    1. Zero JSON parsing errors: automatically parses directly into response_model.
    2. Self-correcting retry: sends validation error feedback back to the LLM if schema fails.
    3. Multi-provider resiliency: automatically fails over between primary and secondary providers.
    """
    if messages is not None:
        conversation_messages = list(messages)
    else:
        conversation_messages = []
        if system_prompt:
            conversation_messages.append({"role": "system", "content": system_prompt})
        if user_prompt:
            conversation_messages.append({"role": "user", "content": user_prompt})

    if not conversation_messages:
        raise ValueError("At least one prompt or message must be provided to generate_structured.")

    _LAST_PROVIDER_USED.set(None)

    selected_provider = normalize_provider_name(provider or settings.LLM_PROVIDER or "groq") or "groq"

    provider_executors = {
        "nvidia": _execute_with_nvidia,
        "gemini": _execute_with_gemini,
        "groq": _execute_with_groq,
    }

    has_nvidia_key = bool((settings.NVIDIA_API_KEY or "").strip())
    if selected_provider == "nvidia":
        base_chain = ["nvidia", "gemini", "groq"]
    elif selected_provider == "gemini":
        base_chain = ["gemini", "groq"] + (["nvidia"] if has_nvidia_key else [])
    else:
        base_chain = ["groq", "gemini"] + (["nvidia"] if has_nvidia_key else [])

    # Prefer healthy providers first; defer rate-limited providers on cooldown to avoid 429 thrashing.
    healthy_chain = [p for p in base_chain if not is_provider_on_cooldown(p)]
    cooling_chain = [p for p in base_chain if is_provider_on_cooldown(p)]
    provider_chain = healthy_chain + cooling_chain

    errors: List[str] = []

    for idx, prov_name in enumerate(provider_chain):
        fn = provider_executors[prov_name]
        is_primary = idx == 0
        try:
            if is_primary:
                logger.info(f"Generating structured output with Instructor via {prov_name} ({response_model.__name__})")
            else:
                logger.info(f"Failing over structured output generation to {prov_name} ({response_model.__name__})")
            result = await asyncio.wait_for(
                fn(
                    response_model=response_model,
                    messages=conversation_messages,
                    model=model if (is_primary and prov_name == selected_provider) else None,
                    max_retries=max_retries,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=60.0,
            )
            _LAST_PROVIDER_USED.set(prov_name)
            return result
        except Exception as e:
            if _is_rate_limit_error(e):
                ttl = mark_provider_cooldown(prov_name, e)
                logger.warning(f"Rate limit hit on provider {prov_name}; marked cooldown for {ttl:.0f}s and failing over.")
            label = "Primary" if is_primary else "Secondary"
            err_msg = f"{label} provider {prov_name} failed: {e}"
            logger.warning(err_msg)
            errors.append(err_msg)

    raise InstructorStructuredOutputError(
        f"All structured output providers failed for model {response_model.__name__}: {'; '.join(errors)}"
    )

