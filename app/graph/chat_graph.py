"""Phase 6 — Graph: the user-question workflow.

    START
      -> retrieve   find relevant knowledge        (Retriever, Phase 8)
      -> rerank     reorder it, if a reranker is available (Reranker, Phase 8)
      -> answer     grounded answer + sources      (AnswerGenerator)
      -> END

Conditional exits (see router.py): a failed retrieval ends the run with no
answer; an empty retrieval skips rerank and returns a graceful "no
relevant knowledge" answer without calling the LLM.

The RAG pieces themselves are NOT implemented here. ``Retriever`` and
``Reranker`` are interfaces (tools.py) that Phase 8 will satisfy; until a
retriever is supplied, ``retrieve`` records a failure and the run ends.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.router import route_after_retrieve
from app.graph.state import ChatState
from app.graph.tools import AnswerGenerator, LLMAnswerGenerator, Reranker, Retriever
from app.graph.rag_to_chatgraph import LocalRAGRetriever, LocalRAGReranker

def build_chat_graph(
    *,
    retriever: Optional[Retriever] = None,
    reranker: Optional[Reranker] = None,
    answerer: Optional[AnswerGenerator] = None,
    top_k: int = 8,
):
    """Build and compile the chat graph.

    Args:
        retriever: Phase 8 retriever. Without one, every run ends with a recorded
            ``retrieve`` failure.
        reranker: optional Phase 8 reranker; the rerank step is skipped without one.
        answerer: answer step; defaults to ``LLMAnswerGenerator`` on the configured LLM.
        top_k: how many documents to ask the retriever for.
    """

    graph = StateGraph(ChatState)

    retriever = retriever or LocalRAGRetriever()
    reranker = reranker or LocalRAGReranker()

    graph.add_node(nodes.RETRIEVE, nodes.make_retrieve_node(retriever, top_k))
    graph.add_node(nodes.RERANK, nodes.make_rerank_node(reranker))
    graph.add_node(nodes.ANSWER, nodes.make_answer_node(answerer or LLMAnswerGenerator()))

    graph.add_edge(START, nodes.RETRIEVE)
    graph.add_conditional_edges(
        nodes.RETRIEVE,
        route_after_retrieve,
        {"rerank": nodes.RERANK, "answer": nodes.ANSWER, "end": END},
    )
    graph.add_edge(nodes.RERANK, nodes.ANSWER)
    graph.add_edge(nodes.ANSWER, END)

    return graph.compile()


async def run_chat(compiled_graph, query: str) -> ChatState:
    """Ask one question and return the final typed state.

    Raises ``pydantic.ValidationError`` for a blank question.
    """

    result = await compiled_graph.ainvoke(ChatState(query=query))
    return ChatState.model_validate(result)
