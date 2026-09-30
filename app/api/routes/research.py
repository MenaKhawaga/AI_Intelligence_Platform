from __future__ import annotations
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from app.api.dependencies import current_user
from app.graph.factory import build_production_graph
from app.graph.research_graph import run_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])

@router.post("/run")
async def run(background_tasks: BackgroundTasks, user=Depends(current_user)):
    # Explicit endpoint for the demo; the agent can invoke the same capability as a tool.
    try:
        graph = build_production_graph()
        state = await run_research(graph)
    except Exception as exc:  # noqa: BLE001 - collectors/DB/LLM errors surface here
        logger.exception("Research run failed")
        raise HTTPException(status_code=500, detail="The research run failed. Check server logs for details.")
    return {
        "status": state.run_status,
        "collected": len(state.collected_items),
        "processed": len(state.processed_items),
        "summaries": len(state.summaries),
        "persisted_articles": state.persisted_articles,
    }
