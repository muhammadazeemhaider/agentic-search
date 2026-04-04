import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.models.llm import get_providers
from src.models.schemas import SearchRequest, SearchResponse
from src.pipeline import run

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve available LLM providers once at startup.
providers = get_providers()

@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    return await run(req, providers)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")
