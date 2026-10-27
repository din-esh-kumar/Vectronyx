# backend/app/modules/research_agent/tools.py
import logging
import urllib.parse
from typing import List
import httpx
import trafilatura
from app.modules.research_agent.schemas import ResearchSource

logger = logging.getLogger("vectronyx.research_tools")

# Private and loopback CIDRs to prevent SSRF
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google.internal"
}

def is_safe_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname in BLOCKED_HOSTS or hostname.startswith("192.168.") or hostname.startswith("10."):
            return False
        return True
    except Exception:
        return False


def search_web(query: str, max_results: int = 4) -> List[ResearchSource]:
    """
    Executes a web search via DuckDuckGo without tracking or cost.
    Returns structured ResearchSource objects.
    """
    sources: List[ResearchSource] = []
    
    # 1. Try modern `ddgs` library
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
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
        with FallbackDDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
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
    """
    if not is_safe_url(url):
        return "Extraction skipped: restricted or invalid URL."

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VectronyxBot/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                extracted = trafilatura.extract(resp.text, include_comments=False, include_tables=True)
                if extracted:
                    return extracted[:max_chars].strip()
    except Exception as e:
        logger.debug(f"Trafilatura extraction failed for {url}: {e}")

    return ""
