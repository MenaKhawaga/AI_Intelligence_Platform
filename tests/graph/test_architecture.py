"""Guards for the graph package scope: the architecture stays as specified
and the package carries no old-project functionality.

Phase 6 shipped the research/chat graph modules below. A later, approved
phase added the autonomous tool-calling Agent (agent_state.py /
agent_tools.py / agent_graph.py) alongside them -- those are legitimate,
intended modules, not leftover scope creep, so they belong in
``EXPECTED_MODULES`` rather than being deleted to satisfy this guard.
"""

from __future__ import annotations

from pathlib import Path

import app.graph

GRAPH_DIR = Path(app.graph.__file__).parent

EXPECTED_MODULES = {
    "__init__.py",
    "state.py",
    "nodes.py",
    "tools.py",
    "router.py",
    "research_graph.py",
    "chat_graph.py",
    "agent_state.py",
    "agent_tools.py",
    "agent_graph.py",
}

FORBIDDEN_TERMS = ("telegram", "linkedin", "newsletter")


def test_graph_package_contains_exactly_the_specified_modules():
    found = {p.name for p in GRAPH_DIR.glob("*.py")}
    assert found == EXPECTED_MODULES


def test_graph_package_has_no_old_project_functionality():
    for path in GRAPH_DIR.glob("*.py"):
        text = path.read_text().lower()
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"{term!r} found in {path.name}"
