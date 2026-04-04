import logging
from ddgs import DDGS

log = logging.getLogger("pipeline.search")

def web_search(query: str, max_results: int = 1) -> list[str]:
    results = DDGS().text(query, max_results=max_results)   
    urls = [r["href"] for r in results]
    log.info("Searched '%s' — got %d URLs", query, len(urls))
    return urls