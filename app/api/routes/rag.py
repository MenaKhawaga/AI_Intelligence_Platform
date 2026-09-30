from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.dependencies import current_user
from app.rag.indexer import build_rag_index
from app.rag.retriever import search_knowledge_base

router = APIRouter(prefix="/rag", tags=["rag"])

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=20)
    category: str | None = Field(default=None, description="Optional article category to filter results by.")

class IndexRequest(BaseModel):
    limit: int = Field(default=1000, ge=1, le=5000)

@router.post("/index")
def index(payload: IndexRequest, user=Depends(current_user)):
    try:
        return build_rag_index(payload.limit)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to build the RAG index.")

@router.post("/search")
def search(payload: SearchRequest, user=Depends(current_user)):
    try:
        results = search_knowledge_base(payload.query, payload.limit, payload.category)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to search the knowledge base.")
    return {"query": payload.query, "count": len(results), "results": results}
