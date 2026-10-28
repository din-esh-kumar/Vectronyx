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


def get_groq_instructor(
    api_key: Optional[str] = None,
    mode: Mode = Mode.TOOLS,
) -> instructor.AsyncInstructor:
    """
    Creates an AsyncInstructor client wrapping Groq Cloud.
    """
    key = api_key or settings.GROQ_API_KEY
    if not key:
        raise ValueError("GROQ_API_KEY is not configured.")
    from groq import AsyncGroq
    client = AsyncGroq(api_key=key)
    return instructor.from_groq(client, mode=mode)


def get_genai_instructor(
    api_key: Optional[str] = None,
    mode: Mode = Mode.TOOLS,
) -> instructor.AsyncInstructor:
    """
    Creates an AsyncInstructor client wrapping Google GenAI (Gemini).
    """
    key = api_key or settings.GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    from google import genai
    client = genai.Client(api_key=key)
    return instructor.from_genai(client, use_async=True, mode=mode)


async def _execute_with_groq(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
) -> T:
    client = get_groq_instructor()
    groq_model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
    return await client.create(
        response_model=response_model,
        messages=messages,
        model=groq_model,
        max_retries=max_retries,
        temperature=temperature,
    )


async def _execute_with_gemini(
    response_model: Type[T],
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
) -> T:
    client = get_genai_instructor()
    gemini_model = model or settings.GEMINI_MODEL or "gemini-3.8-flash"
    return await client.create(
        response_model=response_model,
        messages=messages,
        model=gemini_model,
        max_retries=max_retries,
        temperature=temperature,
    )


async def generate_structured(
    response_model: Type[T],
    system_prompt: str,
    user_prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 3,
    temperature: float = 0.2,
) -> T:
    """
    Synthesizes guaranteed type-safe Pydantic structured output using Instructor.
    
    Features:
    1. Zero JSON parsing errors: automatically parses directly into response_model.
    2. Self-correcting retry: sends validation error feedback back to the LLM if schema fails.
    3. Multi-provider resiliency: automatically fails over between primary and secondary providers.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    selected_provider = (provider or settings.LLM_PROVIDER or "groq").lower()
    
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
            messages=messages,
            model=model,
            max_retries=max_retries,
            temperature=temperature,
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
            messages=messages,
            model=model if provider else None,
            max_retries=max_retries,
            temperature=temperature,
        )
    except Exception as e:
        err_msg = f"Secondary provider {secondary_name} failed: {e}"
        logger.warning(err_msg)
        errors.append(err_msg)

    raise InstructorStructuredOutputError(
        f"All structured output providers failed for model {response_model.__name__}: {'; '.join(errors)}"
    )

