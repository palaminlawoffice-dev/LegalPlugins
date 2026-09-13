from pydantic import BaseModel, Field
from typing import Literal

class Citation(BaseModel):
    id: str
    source: str
    title: str
    url: str
    retrieved_at: str
    content_hash: str | None = None
    verified: bool = False
    verification_note: str = ""

class SearchHit(BaseModel):
    source: Literal["ocs", "supreme_court", "gazette"]
    title: str
    url: str
    snippet: str = ""
    citation_id: str

class ResearchBundle(BaseModel):
    query: str
    hits: list[SearchHit] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
