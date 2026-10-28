# backend/app/services/llm/instructor_client.py
"""
Centralized Instructor Structured Outputs Client for Vectronyx AI Workbench.
Wraps Groq Cloud and Google Gemini (GenAI) client calls with automatic Pydantic validation,
guaranteeing zero JSON/XML parsing errors, self-correcting feedback loops, and type-safe tool invocations.
"""
import logging
from typing import Type, TypeVar, Optional, Any, List, Dict
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


async def _execute_with_groq(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 4096,
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
            messages=messages,
            model=groq_model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        err_str = str(e).lower()
        tool_calling_err_patterns = [
            "tool choice is required",
            "tool_use_failed",
            "tool_calls",
            "failed to generate tool call",
            "does not support tool",
            "tools is not supported",
            "failed_generation",
        ]
        # If tool choice failed, automatically retry with JSON mode
        if target_mode != Mode.JSON and any(p in err_str for p in tool_calling_err_patterns):
            logger.info(f"Groq tool calling rejected by {groq_model}. Retrying with Instructor Mode.JSON...")
            client = get_groq_instructor(mode=Mode.JSON)
            return await client.create(
                response_model=response_model,
                messages=messages,
                model=groq_model,
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
    max_tokens: int = 4096,
) -> T:
    client = get_genai_instructor()
    gemini_model = model or settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
    fallback_model = "gemini-2.5-flash" if gemini_model == "gemini-3.5-flash-lite" else "gemini-3.5-flash-lite"
    try:
        return await client.create(
            response_model=response_model,
            messages=messages,
            model=gemini_model,
            max_retries=max_retries,
            temperature=temperature,
        )
    except Exception as e:
        logger.warning(f"Gemini {gemini_model} failed ({e}); falling back to {fallback_model}")
        return await client.create(
            response_model=response_model,
            messages=messages,
            model=fallback_model,
            max_retries=max_retries,
            temperature=temperature,
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
    max_tokens: int = 4096,
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

    selected_provider = (provider or settings.LLM_PROVIDER or "groq").lower().strip()
    
    # Establish provider execution order
    if selected_provider == "gemini":
        primary_name, primary_fn = "gemini", _execute_with_gemini
        secondary_name, secondary_fn = "groq", _execute_with_groq
    else:
        primary_name, primary_fn = "groq", _execute_with_groq
        secondary_name, secondary_fn = "gemini", _execute_with_gemini

    errors: List[str] = []

    # 1. Attempt Primary Provider
    try:
        logger.info(f"Generating structured output with Instructor via {primary_name} ({response_model.__name__})")
        return await primary_fn(
            response_model=response_model,
            messages=conversation_messages,
            model=model,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        err_msg = f"Primary provider {primary_name} failed: {e}"
        logger.warning(err_msg)
        errors.append(err_msg)

    # 2. Attempt Secondary Fallback Provider
    try:
        logger.info(f"Failing over structured output generation to {secondary_name} ({response_model.__name__})")
        return await secondary_fn(
            response_model=response_model,
            messages=conversation_messages,
            model=None,  # Reset model so secondary provider uses its native configuration
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        err_msg = f"Secondary provider {secondary_name} failed: {e}"
        logger.warning(err_msg)
        errors.append(err_msg)

    raise InstructorStructuredOutputError(
        f"All structured output providers failed for model {response_model.__name__}: {'; '.join(errors)}"
    )

