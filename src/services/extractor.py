import json
import logging
import re

from src.models.llm import call_llm

log = logging.getLogger("pipeline.extractor")

MAX_ENTITIES = 10

SYSTEM_PROMPT = (
    """You are an entity extraction assistant. Given web page content from a 
    search query, extract all distinct real-world entities that are relevant 
    to the query. Return ONLY a valid JSON array with no markdown formatting,
    no backticks, no explanation before or after."""
)


def _build_user_prompt(query: str, pages: list[dict]) -> str:
    """Assemble the user prompt from the query and fetched page texts."""
    parts = [f'Query: "{query}"\n']
    for i, page in enumerate(pages, 1):
        parts.append(f"--- Page {i} (source: {page['url']}) ---")
        parts.append(page["text"])
        parts.append("")
    parts.append(
        "Extract every distinct entity relevant to the query from the pages above.\n"
        "\n"
        "Return this exact JSON format:\n"
        '[{"name": "Entity Name", "description": "One sentence describing this entity", "sources": ["url1", "url2", ... , "urlN"]}]\n'
        "\n"
        "Rules:\n"
        "- Only include entities that are actual specific real-world things matching the query intent\n"
        "- No duplicate entity names\n"
        "- description: one concise sentence about the entity based on the page content\n"
        "- sources: list ALL page URLs where the entity was mentioned, not just the first\n"
        "- Every URL in sources must be one of the page URLs listed above\n"
        "- Return at most 10 entities\n"
        "- Return ONLY the JSON array, nothing else"
    )
    return "\n".join(parts)


def _parse_llm_json(raw: str) -> list[dict]:
    """Extract a JSON array from the LLM response with multiple fallbacks."""
    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 3: regex for the outermost [...] block
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    log.warning("Could not parse LLM response as JSON")
    return []

async def extract_entities(
    query: str,
    pages: list[dict],
    providers: list[dict],
) -> list[dict]:
    """Build the extraction prompt, call the LLM, and parse the result."""
    if not pages:
        return []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(query, pages)},
    ]

    raw = await call_llm(providers, messages)
    entities = _parse_llm_json(raw)[:MAX_ENTITIES]
    log.info("Parsed %d entities from LLM response", len(entities))
    return entities
