# Agentic Search

The system takes a topic query, then searches the web, scrapes the top results, sends the content to the LLM, and extracts real-world entities into a structured table — with descriptions, and traceable source URLs.

**Live Demo:** [https://agentic-search-vm0s.onrender.com/](https://agentic-search-vm0s.onrender.com/)

> Using Renders Free tier - first load may take ~30s if the instance has spun down.

---

## The solution and how it works

The system runs a four-step pipeline for every query:

```
Query: "top pizza places in brooklyn"
  │
  ▼
┌──────────────────┐
│  1. Web Search   │
│     → URLs       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  2. Fetch Pages  │
│     → Clean Text │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  3. LLM Extract  │
│     → Entities   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  4. Return JSON  │
└──────────────────┘
```

1. **Search** — Sends the query to DuckDuckGo and collects the top result URLs.
2. **Fetch** — Downloads all pages concurrently with `asyncio.gather()` and extracts clean body text using trafilatura (strips nav, ads, scripts, footers).
3. **Extract** — Builds a prompt containing the query + page texts, sends it to Llama 3.1 70B, and parses the structured JSON response.
4. **Return** — Validates entities with Pydantic, attaches timing/page metadata, and sends the response to the frontend.

---

## Features

### Core (Challenge Requirements)

- **Topic query input** — search bar for testing
- **Web search** — DuckDuckGo is used for websearch. Chosen over Serper because Serper only gives 2500 free searches.
- **Page scraping** — concurrent async fetching with trafilatura for clean text extraction
- **LLM entity extraction** — LLM extracts structured entity data from scraped content
- **Structured output** — 3-column table: Entity, Description, Sources
- **Source traceability** — every entity links back to the specific page(s) it was found on

### Beyond the Basics

- **LLM provider fallback chain** — OpenRouter is the primary provider; if it fails (rate limit, timeout, server error), the system automatically retries with nv-api.
- **Session caching with query normalization** — Same queries return instantly from an in-memory cache. Normalization lowercases, strips punctuation, removes stop words, deplurializes, and sorts alphabetically. So `"best pizza places in karachi"` and `"Karachi pizza place"` hit the same cache entry.
- **Entity descriptions** — each entity includes a one-sentence description.
- **Multiple source citations** — entities list every page URL where they were mentioned.
- **JSON and CSV export** — download results with one click for further analysis.
---

## File Structure

```
├── main.py                    # FastAPI entry point — routes, CORS, static files
├── requirements.txt           # Python dependencies
├── .env                       # API keys (not committed to git)
│
├── src/
│   ├── pipeline.py            # Orchestrator — wires the 4 steps, caching, error handling
│   │
│   ├── models/
│   │   ├── schemas.py         # Pydantic models (SearchRequest, Entity, SearchResponse)
│   │   └── llm.py             # LLM client — provider fallback, raw httpx calls
│   │
│   └── services/
│       ├── search.py          # Step 1: DuckDuckGo web search
│       ├── scraper.py         # Step 2: async page fetching + trafilatura extraction
│       └── extractor.py       # Step 3: prompt building + LLM JSON parsing
│
└── static/
    ├── index.html             # Frontend — vanilla HTML/JS, no framework
    └── style.css              # Dark theme, DM Mono font, CSS variables
```

---

## Local Setup

### Prerequisites

- Python 3.10+
- At least one API key: [OpenRouter](https://openrouter.ai/) or nv-api

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/agentic-search.git
cd agentic-search

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with your API key(s)
echo "OPENROUTER_API_KEY=your_key_here" > .env
echo "NVIDIA_API_KEY=your_key_here" >> .env
# At least one key is required. Both enables automatic fallback.

# 5. Start the server
uvicorn main:app --reload
```

---

## Design Decisions

| Decision | Why |
|---|---|
| **trafilatura** | Purpose-built for web content extraction. One function call replaces 30+ lines of manual HTML stripping — handles nav, scripts, footers, ads automatically. |
| **Service Providers** | Provided two API service providers in openrouter and nv-api, so if fails, there is a fallback. |
| **Normalized caching** | Caching for semantically matching queries would require using an embedding model which adds another overhead compute cost and will slow down the system. As a result, simple lexical and normalized caching is implemented. |
| **Number of Pages being retrieved** | The number of pages to retrieve is kept 5. A higher number of pages was taking longer time for the entire solution to complete. |
| **Number of Entities** | 10 entities will be retrieved everytime. This is because if I do not set a number, at times the system takes close to 3-4 minutes to retrieve 50-60 entities. |
| **Text truncation** | page text capped at 3,000 characters to reduce token usage and latency. Most important information in articles and pages are usually found in the earlier part of the articles. |
---

## Known Limitations

- **Bot-blocked pages** — sites that block automated requests or require JavaScript rendering are silently skipped.
- **Text truncation** — cutting at 3,000 characters may miss entities mentioned later in long articles.
- **Search quality** — depends entirely on DuckDuckGo's ranking for the query.
- **Cache is in-memory** — cleared on server restart; not persisted across sessions.

---