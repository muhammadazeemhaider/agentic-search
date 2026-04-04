import asyncio
import logging
import re
import time

from src.models.schemas import Entity, SearchRequest, SearchResponse
from src.services.search import web_search
from src.services.scraper import fetch_pages
from src.services.extractor import extract_entities

log = logging.getLogger("pipeline")

# In-memory cache: maps (normalized_query, top_n) → SearchResponse.
_cache: dict[tuple[str, int], SearchResponse] = {}

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "of", "for", "to", "and", "or",
    "is", "are", "was", "were", "be", "been", "best", "top", "most",
    "with", "by", "from", "about", "into", "its", "it", "my", "your",
}

def _normalize_query(query: str) -> str:
    """Reduce a query to a canonical form for cache matching.

    lowercase → strip punctuation → remove stop words →
    depluralize (strip trailing 's') → sort alphabetically.

    "best pizza places in karachi"  → "karachi pizza place"
    "karachis best pizza places"    → "karachi pizza place"
    """
    text = re.sub(r"[^a-z0-9\s]", "", query.lower())
    words = [w for w in text.split() if w not in STOP_WORDS]
    words = [w.rstrip("s") if len(w) > 3 else w for w in words]
    words.sort()
    return " ".join(words)

async def run(req: SearchRequest, providers: list[dict]) -> SearchResponse:
    """Execute the full Search → Fetch → Extract → Return pipeline."""
    cache_key = (_normalize_query(req.query), req.top_n)

    if cache_key in _cache:
        log.info("Cache hit for '%s'", req.query)
        cached = _cache[cache_key]
        return SearchResponse(
            query=req.query,
            entities=cached.entities,
            metadata={**cached.metadata, "cached": True},
        )

    t0 = time.time()

    try:
        # Step 1 — Web search
        urls = await asyncio.to_thread(web_search, req.query, req.top_n)
        pages_fetched = len(urls)

        # Step 2 — Fetch & extract page text
        pages = await fetch_pages(urls)
        pages_succeeded = len(pages)

        # Step 3 — LLM entity extraction
        raw_entities = await extract_entities(req.query, pages, providers)

        # Step 4 — Build response
        entities = []
        for e in raw_entities:
            if "name" not in e:
                continue
            sources = e.get("sources") or []
            if isinstance(sources, str):
                sources = [sources]
            # Fallback: accept old single-source format from LLM
            if not sources and "source" in e:
                sources = [e["source"]]
            entities.append(Entity(
                name=e["name"],
                description=e.get("description", ""),
                # category=e.get("category", ""),
                sources=[s for s in sources if isinstance(s, str)],
            ))

        response = SearchResponse(
            query=req.query,
            entities=entities,
            metadata={
                "pages_fetched": pages_fetched,
                "pages_succeeded": pages_succeeded,
                "time_seconds": round(time.time() - t0, 1),
            },
        )
        _cache[cache_key] = response
        return response

    except Exception as exc:
        log.exception("Pipeline failed: %s", exc)
        return SearchResponse(
            query=req.query,
            entities=[],
            metadata={
                "pages_fetched": 0,
                "pages_succeeded": 0,
                "time_seconds": round(time.time() - t0, 1),
                "error": str(exc),
            },
        )
