import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from app.graph.agent_graph import build_agent_graph, run_agent
from tests.graph.fakes import FakeToolCallingChatModel


@pytest.mark.asyncio
async def test_agent_can_answer_without_tool():
    model = FakeToolCallingChatModel(messages=iter([AIMessage(content="Hello from the agent.")]))
    graph = build_agent_graph(model=model, tools=[])
    state = await run_agent(graph, "Hello")
    assert state.messages[-1].content == "Hello from the agent."
    assert state.tool_calls == 0


@pytest.mark.asyncio
async def test_agent_executes_tool_then_returns_final_answer():
    calls = []

    def lookup(term: str) -> str:
        calls.append(term)
        return "AI news result: LangGraph supports tool calling."

    tool = StructuredTool.from_function(
        lookup,
        name="lookup_intelligence",
        description="Look up intelligence by term.",
    )
    model = FakeToolCallingChatModel(messages=iter([
        AIMessage(content="", tool_calls=[{"name": "lookup_intelligence", "args": {"term": "LangGraph"}, "id": "call-1", "type": "tool_call"}]),
        AIMessage(content="LangGraph supports tool calling."),
    ]))
    graph = build_agent_graph(model=model, tools=[tool])
    state = await run_agent(graph, "What does LangGraph support?")
    assert calls == ["LangGraph"]
    assert state.tool_calls == 1
    assert state.messages[-1].content == "LangGraph supports tool calling."
