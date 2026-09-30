"""Knowledge-base management endpoints.

Thin wrapper around ``app.rag.indexer`` for the Knowledge Base page: a
single "Build / Rebuild Knowledge Base" action that (re)indexes every
stored article and reports how much was indexed. This is the
``POST /knowledge/rebuild`` endpoint referenced throughout the project
spec/README, separate from ``/rag/index`` (which takes an explicit
``limit`` payload for programmatic/agent use) so the frontend has a
zero-argument action to bind a single button to.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import current_user
from app.rag.indexer import build_rag_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["rag"])


@router.post("/rebuild")
def rebuild(user=Depends(current_user)):
    """Rebuild the local knowledge-base index from every stored article."""

    try:
        result = build_rag_index()
    except Exception as exc:  # noqa: BLE001 - filesystem/DB errors surface here
        logger.exception("Knowledge base rebuild failed")
        raise HTTPException(status_code=500, detail="Failed to rebuild the knowledge base.")
    return {
        "status": "ok",
        "indexed_articles": result["indexed_articles"],
        "indexed_chunks": result["indexed_chunks"],
    }
