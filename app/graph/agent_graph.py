from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.agent_state import AgentState
from app.graph.agent_tools import agent_tools




AGENT_SYSTEM_PROMPT = """
You are the AI Intelligence Platform agent.

You answer questions using the intelligence collected by the platform.

You can:
- search stored articles
- explore topics
- list current trends
- search the knowledge base
- run fresh research

Use a tool when it is needed.
Do not invent information.
Use stored information first.
If fresh information is needed, use run_fresh_research.
Give a clear and concise final answer.
"""


def create_llm() -> BaseChatModel:
    """Create the LLM used by agent"""

    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError(
                "langchain-groq is required. "
                "Install it with: pip install langchain-groq"
            ) from exc

        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is required when LLM_PROVIDER=groq"
            )

        return ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.2,
        )

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "langchain-openai is required. "
                "Install it with: pip install langchain-openai"
            ) from exc

        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
        )

    raise RuntimeError(
        f"Unsupported agent LLM provider: {settings.LLM_PROVIDER}"
    )


MAX_TOOL_CALLS = 6 # to prevent agent call more than 6 tools


def route_agent(state: AgentState) -> str:
    # route the agent to tools or end

    if state.tool_calls >= MAX_TOOL_CALLS:
        return "end"

    if not state.messages:
        return "end"

    last_message = state.messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


def build_agent_graph():

    # tools
    tools = agent_tools

    # LLM
    llm = create_llm()

    # give the LLM access to the tools
    llm_with_tools = llm.bind_tools(tools)

    # ToolNode executes the  selected tool
    tool_node = ToolNode(tools)

    # Agent node
    async def call_llm(state: AgentState) -> dict[str, Any]:
        messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            *state.messages,
        ]

        response = await llm_with_tools.ainvoke(messages)

        return {
            "messages": [response],
            "tool_calls": state.tool_calls + len(response.tool_calls),
        }

    # build graph
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("agent", call_llm)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_edge(START, "agent")

    graph_builder.add_conditional_edges(
        "agent",
        route_agent,
        {
            "tools": "tools",
            "end": END,
        },
    )

    graph_builder.add_edge("tools", "agent")

    graph = graph_builder.compile()
    
    return graph

async def run_agent(graph, query: str) -> AgentState:
    """Run the agent for one user query."""

    query = query.strip()
    if not query:
        raise ValueError("query must not be blank")

    result = await graph.ainvoke(
        {
        "messages" : [ HumanMessage(content=query) ]
        } 
        )

    return AgentState.model_validate(result)