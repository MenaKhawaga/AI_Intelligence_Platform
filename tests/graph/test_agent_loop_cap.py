"""Guards against an unbounded agent <-> tool loop (spec Step 5/6).

``GenericFakeChatModel`` only replays a fixed, finite sequence of
messages, so it can't stand in for a model that *keeps* requesting tools
forever. This test uses a tiny always-call-a-tool fake chat model instead,
to prove ``MAX_TOOL_CALLS`` actually stops the graph rather than looping
until LangGraph's own recursion_limit raises ``GraphRecursionError``.
"""
from __future__ import annotations

from typing import Any, List, Optional

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import StructuredTool

from app.graph.agent_graph import MAX_TOOL_CALLS, build_agent_graph, run_agent


class AlwaysCallToolChatModel(BaseChatModel):
    """A fake chat model that always asks to call the same tool again."""

    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "always-call-tool-fake"

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001 - matches BaseChatModel signature
        # Real production code (build_agent_graph) always calls
        # model.bind_tools(...) before using the model, since that's the
        # real contract a live ChatOpenAI needs. This fake ignores the tool
        # schema and always emits the same canned tool call regardless, so
        # binding is a no-op that just returns the (already tool-calling)
        # model itself.
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.call_count += 1
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "loop_tool",
                    "args": {},
                    "id": f"call-{self.call_count}",
                    "type": "tool_call",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.mark.asyncio
async def test_agent_stops_after_max_tool_calls_instead_of_looping_forever():
    def loop_tool() -> str:
        return "still nothing useful"

    tool = StructuredTool.from_function(loop_tool, name="loop_tool", description="Always callable test tool.")
    model = AlwaysCallToolChatModel()

    graph = build_agent_graph(model=model, tools=[tool])
    # No manual recursion_limit override -- the cap inside the graph itself
    # (not LangGraph's default) must be what ends the run.
    state = await run_agent(graph, "Trigger the loop")

    assert state.tool_calls == MAX_TOOL_CALLS
    # The graph ended cleanly at the cap: no exception propagated, and the
    # tool really was invoked MAX_TOOL_CALLS times, not more.
    assert model.call_count == MAX_TOOL_CALLS
