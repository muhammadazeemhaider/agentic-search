from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    top_n: int = 10

class Entity(BaseModel):
    name: str
    description: str
    # category: str
    sources: list[str]

class SearchResponse(BaseModel):
    query: str
    entities: list[Entity]
    metadata: dict