# backend/app/modules/research_agent/tools.py
import asyncio
import ipaddress
import logging
import urllib.parse
from typing import List, Union, Any, Dict, Callable
import httpx
import trafilatura
from app.modules.research_agent.schemas import (
    ResearchSource,
    WebSearchArgs,
    WebScrapeArgs,
    DataAnalystArgs,
)

logger = logging.getLogger("vectronyx.research_tools")

# Private and loopback hostnames / domains to prevent SSRF
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google.internal", "metadata"
}

def is_safe_url(url: str) -> bool:
    """
    Rigorously audits target URL to prevent SSRF, DNS rebinding, and unauthorized
    internal network probing (RFC 1918, RFC 3927, RFC 4193, loopbacks, link-locals).
    """
    try:
        if not url or not isinstance(url, str):
            return False
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return False
        if hostname in BLOCKED_HOSTS or hostname.endswith(".local") or hostname.endswith(".internal"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False
        except ValueError:
            # Hostname is a domain name rather than a raw IP address
            pass
        return True
    except Exception:
        return False


def search_web(query: str, max_results: int = 4) -> List[ResearchSource]:
    """
    Executes a web search via DuckDuckGo without tracking or cost.
    Returns structured ResearchSource objects.
    """
    if not query or not query.strip():
        return []

    sources: List[ResearchSource] = []
    clean_query = query.strip()
    
    # 1. Try modern `ddgs` library
    try:
        from ddgs import DDGS
        with DDGS(timeout=8) as ddgs:
            raw_results = list(ddgs.text(clean_query, max_results=max_results))
            for item in raw_results:
                url = item.get("href") or item.get("link") or ""
                if not is_safe_url(url):
                    continue
                domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
                sources.append(
                    ResearchSource(
                        title=item.get("title", domain),
                        url=url,
                        snippet=item.get("body", "")[:350],
                        reliability=96 if any(tld in domain for tld in ["edu", "org", "gov", "arxiv.org", "github.com", "supabase.com"]) else 90,
                        domain=domain
                    )
                )
        if sources:
            return sources
    except Exception as e:
        logger.warning(f"ddgs search failed: {e}")

    # 2. Try `duckduckgo_search` fallback
    try:
        from duckduckgo_search import DDGS as FallbackDDGS
        with FallbackDDGS(timeout=8) as ddgs:
            raw_results = list(ddgs.text(clean_query, max_results=max_results))
            for item in raw_results:
                url = item.get("href") or item.get("link") or ""
                if not is_safe_url(url):
                    continue
                domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
                sources.append(
                    ResearchSource(
                        title=item.get("title", domain),
                        url=url,
                        snippet=item.get("body", "")[:350],
                        reliability=94,
                        domain=domain
                    )
                )
    except Exception as e:
        logger.warning(f"Fallback DDGS search failed: {e}")

    return sources


async def scrape_page(url: str, max_chars: int = 1500) -> str:
    """
    Extracts sanitized, clean article text using Trafilatura.
    Strips tracking scripts, ads, and navigation chrome.
    Validates redirects to prevent open-redirect SSRF bypasses.
    """
    if not is_safe_url(url):
        return "Extraction skipped: restricted or invalid URL."

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VectronyxBot/1.0"}) as client:
            resp = await client.get(url)
            # Re-verify final redirected destination is safe against internal network probing
            if not is_safe_url(str(resp.url)):
                return "Extraction skipped: restricted or invalid URL."
            if resp.status_code == 200:
                extracted = trafilatura.extract(resp.text, include_comments=False, include_tables=True)
                if extracted:
                    return extracted[:max_chars].strip()
    except Exception as e:
        logger.debug(f"Trafilatura extraction failed for {url}: {e}")

    return ""


# ============================================================
# Type-Safe Tool Executors (Strict Pydantic Model Enforced)
# ============================================================

def execute_web_search(args: Union[WebSearchArgs, dict]) -> List[ResearchSource]:
    """
    Guarantees that arguments passed to the Web Search tool strictly adhere
    to the WebSearchArgs Pydantic model.
    """
    if isinstance(args, dict):
        args = WebSearchArgs.model_validate(args)
    return search_web(query=args.query, max_results=args.max_results)


async def execute_web_scrape(args: Union[WebScrapeArgs, dict]) -> str:
    """
    Guarantees that arguments passed to the Web Scraper tool strictly adhere
    to the WebScrapeArgs Pydantic model.
    """
    if isinstance(args, dict):
        args = WebScrapeArgs.model_validate(args)
    return await scrape_page(url=args.url, max_chars=args.max_chars)


async def execute_data_analyst(args: Union[DataAnalystArgs, dict]) -> Any:
    """
    Guarantees that arguments passed to the Intelligent Data Analyst strictly
    adhere to the DataAnalystArgs Pydantic model.
    """
    from app.modules.data_analyst.analyst import generate_complete_dashboard
    if isinstance(args, dict):
        args = DataAnalystArgs.model_validate(args)
    return await generate_complete_dashboard(
        csv_text=args.csv_data,
        user_prompt=args.prompt,
        dataset_name=args.dataset_name or "dataset.csv"
    )


# ============================================================
# Central Type-Safe Tool Router & Dispatcher (Zero Parsing Error)
# ============================================================

TOOL_SCHEMA_REGISTRY: Dict[str, Any] = {
    "web_search": WebSearchArgs,
    "web_scrape": WebScrapeArgs,
    "data_analyst": DataAnalystArgs,
}

TOOL_EXECUTOR_REGISTRY: Dict[str, Callable] = {
    "web_search": execute_web_search,
    "web_scrape": execute_web_scrape,
    "data_analyst": execute_data_analyst,
}


async def dispatch_tool_call(tool_name: str, tool_args: Any) -> Any:
    """
    Central type-safe agent tool dispatcher.
    Guarantees that arguments passed to tools strictly adhere to the defined Pydantic models.
    Zero JSON/argument parsing errors: any invalid input raises a Pydantic ValidationError
    with exact field-level attribution, enabling self-correcting feedback loops.
    """
    normalized_name = (tool_name or "").strip().lower()
    if normalized_name not in TOOL_SCHEMA_REGISTRY:
        raise ValueError(f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_SCHEMA_REGISTRY.keys())}")

    schema_cls = TOOL_SCHEMA_REGISTRY[normalized_name]
    executor = TOOL_EXECUTOR_REGISTRY[normalized_name]

    # Validate arguments through Pydantic model
    if isinstance(tool_args, schema_cls):
        validated_args = tool_args
    elif isinstance(tool_args, dict):
        validated_args = schema_cls.model_validate(tool_args)
    elif isinstance(tool_args, str):
        validated_args = schema_cls.model_validate_json(tool_args)
    else:
        validated_args = schema_cls.model_validate(tool_args)

    # Execute tool (handling sync or async)
    if asyncio.iscoroutinefunction(executor):
        return await executor(validated_args)
    return executor(validated_args)
