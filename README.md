returns 10 results always. Have added this as a condition.

# Agentic Search

A web application that takes a topic query, searches the web, scrapes the top results, passes the content to an open-source LLM (Llama 3.1 70B), extracts named entities matching the query, and returns them in a structured table with source URLs. The entire system is a linear four-step pipeline: **Search → Fetch → Extract → Return.**

## Architecture

```
Query
  │
  ▼
┌─────────────────┐
│  1. Web Search   │  DuckDuckGo (duckduckgo-search)
│     → URLs       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Fetch Pages  │  httpx (async, concurrent) + trafilatura
│     → Text       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. LLM Extract  │  Llama 3.1 70B via OpenRouter or NVIDIA NIM
│     → Entities   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Return JSON  │  FastAPI response with entities + metadata
└─────────────────┘
```

The backend is a single FastAPI file (`main.py`). The frontend is a single HTML file (`static/index.html`) with all CSS and JavaScript inline. No frameworks, no build step.

## Design Decisions

- **trafilatura over BeautifulSoup**: Purpose-built for web content extraction. One function call replaces 30+ lines of manual HTML stripping — it handles navigation, scripts, footers, sidebars, and ads automatically.
- **httpx over requests**: Async-native HTTP client that pairs with FastAPI's async model and enables parallel fetching with `asyncio.gather()`.
- **Concurrent fetching**: `asyncio.gather()` fetches all pages in parallel, reducing 5 sequential HTTP requests from ~10s to ~2-3s.
- **DuckDuckGo**: Zero API key friction — no account required, no billing setup. Good enough result quality for entity discovery.
- **Open-source LLM via API**: Llama 3.1 70B is powerful enough for structured entity extraction. Hosted APIs (OpenRouter / NVIDIA NIM) avoid GPU infrastructure management.
- **Dual provider support**: OpenRouter and NVIDIA NIM both use OpenAI-compatible chat completions format, so only the endpoint URL, model string, and API key differ. Minimal code to support both.
- **Raw httpx for LLM calls**: No `openai` SDK dependency. A single `httpx.post()` to an OpenAI-compatible endpoint is simpler and more transparent.
- **Single-file simplicity**: Entire backend is one Python file, entire frontend is one HTML file — easy to read, easy to modify, easy to deploy.
- **Text truncation at 3,000 characters**: Keeps token usage low and reduces latency. Entities typically appear early in page content.

## Known Limitations

- **No caching** — repeated queries re-search and re-fetch every time.
- **Bot-blocked pages** — sites that block automated requests or require JavaScript rendering will be skipped silently.
- **Truncation** — cutting text at 3,000 characters may miss entities mentioned later in long articles.
- **Deduplication** — relies on the LLM's in-prompt instructions to avoid duplicates; no post-processing dedup.
- **Search quality** — depends on DuckDuckGo's ranking for the given query.
- **Rate limits** — heavy use may trigger rate limits on the LLM provider.

## Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd <repo-name>

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys — edit .env with at least one key:
#    OPENROUTER_API_KEY=your_key
#    NVIDIA_API_KEY=your_key

# 5. Run the server
uvicorn main:app --reload

# 6. Open http://localhost:8000
```

## Example Queries

- "AI startups in healthcare"
- "open source database tools"
- "top pizza places in brooklyn"
- "electric vehicle companies"
