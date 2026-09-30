"""AI agent state for the intelligence assistant"""

from __future__ import annotations

from typing import Annotated, List

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """State carried through an agent run."""

    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    tool_calls: int = 0
