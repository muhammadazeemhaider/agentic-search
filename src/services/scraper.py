import asyncio
import logging
import httpx
import trafilatura

log = logging.getLogger("pipeline.scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_TEXT_CHARS = 3000
FETCH_TIMEOUT = 4  # seconds per page

async def _fetch_one(client: httpx.AsyncClient, url: str) -> dict | None:
    """Fetch a single URL and extract its body text with trafilatura."""
    try:
        resp = await client.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        log.warning("Fetch failed for %s: %s", url, exc)
        return None

    # trafilatura ensuring that the header footer and ads are removed
    text = await asyncio.to_thread(trafilatura.extract, html)
    if not text:
        log.warning("trafilatura returned None for %s", url)
        return None

    return {"url": url, "text": text[:MAX_TEXT_CHARS]}

async def fetch_pages(urls: list[str]) -> list[dict]:
    """Fetch all URLs concurrently and return successfully extracted pages."""
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        tasks = [_fetch_one(client, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    pages = [r for r in results if isinstance(r, dict)]
    log.info("Fetched %d/%d pages successfully", len(pages), len(urls))
    return pages
