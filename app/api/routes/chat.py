from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import current_user
from app.database.session import get_session
from app.models.agent_activity import AgentActivity
from app.graph.agent_graph import build_agent_graph, run_agent
from app.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["ai-agent"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


@router.post("")
async def chat(payload: ChatRequest, user=Depends(current_user)):
    try:
        graph = build_agent_graph()
        state = await run_agent(graph, payload.query)
    except (LLMServiceError, RuntimeError) as exc:
        # Missing/invalid OPENAI_API_KEY, unsupported provider, etc. -- a
        # configuration problem the caller can act on, not a server bug.
        logger.warning("Agent could not run: %s", exc)
        raise HTTPException(status_code=503, detail=f"AI agent is unavailable: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - final safety net at the API boundary
        logger.exception("Unhandled error running the AI agent")
        raise HTTPException(status_code=500, detail="The AI agent failed to produce a response. Please try again.")

    answer = "No final answer was produced."
    sources: list[str] = []

    for message in reversed(state.messages):
        if getattr(message, "type", None) == "ai" and getattr(message, "content", None):
            answer = message.content
            break

    for message in state.messages:
        content = str(getattr(message, "content", ""))
        for line in content.splitlines():
            if "url=" in line:
                sources.append(line.split("url=", 1)[1].split()[0])
    
    # Save agent activity
    try:
        tools_used = []

        for message in state.messages:
            if getattr(message, "type", None) == "ai":
                for tool_call in getattr(message, "tool_calls", []):
                    tools_used.append(tool_call["name"])

        with get_session() as session:
            activity = AgentActivity(
                user_id=user.id,
                query=payload.query,
                tools_used=tools_used,
                success=True,
            )

            session.add(activity)

    except Exception:
        logger.exception("Failed to save agent activity")


    return {
        "answer": answer,
        "tool_calls": state.tool_calls,
        "sources": list(dict.fromkeys(sources)),
        "user": user.email,
    }
