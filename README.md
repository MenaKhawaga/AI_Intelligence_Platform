# AI Intelligence Platform

An AI-powered intelligence platform that collects technology/AI information from multiple sources, processes and summarizes it, detects trends, and exposes an authenticated **AI Agent** that can autonomously choose application tools to answer questions with evidence from the platform.

## Core capabilities

- Multi-source collection: RSS, GitHub, Hacker News, arXiv, Reddit
- Cleaning, normalization, filtering, deduplication, classification, entity extraction, ranking
- LLM-based structured summarization
- SQLAlchemy database with Alembic migrations
- Trend clustering and explainable trend scoring
- LangGraph Research Graph
- **RAG / local knowledge base**: chunking, TF-IDF embeddings, cosine-similarity retrieval, lightweight reranking, and persisted metadata (article, source, URL, published date, category) — see `app/rag/`
- LangChain + LangGraph tool-calling AI Agent, with a hard cap on tool-call rounds (`MAX_TOOL_CALLS` in `app/graph/agent_graph.py`) to prevent runaway loops
- FastAPI backend with centralized logging, CORS, and friendly (non-leaking) error responses
- JWT authentication with salted (PBKDF2-HMAC-SHA256) password hashing
- Polished dark-themed vanilla HTML/CSS/JS dashboard (login/register, chat, intelligence feed, trends, knowledge base, analytics)
- Direct Python/virtual-environment execution — no Docker, no external infra

## AI Agent flow

```text
User -> FastAPI -> JWT Auth -> AI Agent (LangGraph, max 6 tool-call rounds)
                              |
                              +-> search_articles          (stored articles, keyword match)
                              +-> get_topic_articles        (articles for a stored topic)
                              +-> list_trends                (stored topics/trends)
                              +-> search_knowledge_base      (RAG: local vector index)
                              +-> run_fresh_research          (re-runs the research graph)
                              |
                              v
                         Tool Results
                              |
                              v
                         Final Answer + Sources
```

The model decides when a tool is needed. The agent can call multiple tools before returning its final answer, up to `MAX_TOOL_CALLS` rounds, after which the graph ends gracefully with whatever answer/context it has rather than looping indefinitely.

## Research flow

```text
Sources -> Collect -> Process -> Summarize -> Persist -> Trends -> Index hook
```

## Run directly with Python

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

The API is then available at `http://127.0.0.1:8000` and interactive docs at `/docs`.

Set a strong `JWT_SECRET_KEY` and an `OPENAI_API_KEY` in `.env` before using the real AI Agent.

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Protected intelligence/agent endpoints require `Authorization: Bearer <token>`.

## Main API

- `GET /health`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `POST /chat` — authenticated AI Agent (tool-calling, capped at `MAX_TOOL_CALLS` rounds)
- `GET /intelligence/articles`
- `GET /trends`
- `GET /repositories` — GitHub-sourced items
- `GET /analytics/overview` — totals, source/category distribution, average relevance, recent intelligence
- `POST /research/run` — runs the collect -> process -> summarize -> persist -> trends pipeline once
- `POST /rag/index` — build/rebuild the knowledge-base index for up to `limit` articles
- `POST /rag/search` — search the knowledge base (`query`, `limit`, optional `category`)
- `POST /knowledge/rebuild` — zero-argument rebuild (used by the frontend's "Build / Rebuild Knowledge Base" button)

All routes above except `/health`, `/auth/register`, and `/auth/login` require `Authorization: Bearer <token>`. Every route appears in Swagger at `/docs`.

## Frontend

Served by FastAPI itself at `/frontend` (mounted from `create_app()`), or open `frontend/index.html` directly / via a static server such as VS Code Live Server on `:5500` — `frontend/app.js` picks the right `API_BASE` automatically (same-origin when served on `:8000`, otherwise `http://127.0.0.1:8000`).

Pages: Dashboard, AI Agent chat (with sources and tool-call count shown per answer), Intelligence Feed, Trends, Knowledge Base (build/rebuild + search), Analytics. Login/registration have client-side validation, loading states, and error messages; the JWT is stored in `localStorage` for this local academic project (not intended for production use).

## End-to-end demo

Run the server, then execute:

```bash
./scripts/e2e_demo.sh
```

The complete scenario is: register/login -> authenticated agent request -> model chooses tools -> tools query intelligence -> agent synthesizes evidence -> API returns answer and sources.

## Project documentation

- `docs/FINAL_PRESENTATION.md` — final presentation narrative and architecture
- `docs/GIT_WORKFLOW.md` — Git/GitHub team workflow
- `scripts/e2e_demo.sh` — live demo script

## Optional enhancements after mandatory requirements

RAG / knowledge base is implemented (see `app/rag/` and the AI Agent flow above) — it is not treated as a future enhancement. Customer satisfaction analysis, voice support, multi-agent architecture beyond the current tool-calling agent, real-time WebSocket chat, cloud deployment, and advanced monitoring remain intentionally out of scope for the core delivery.

## Tests

Run:

```bash
pytest -q
```

Tests cover collectors, processing, summarization, database/repositories, LangGraph research/chat/agent orchestration (including the tool-call loop cap), the RAG pipeline (indexing, retrieval, metadata, empty database, top-k, category filtering, persistence/reload), trends, and authentication/API behavior.

## Verification status of this revision

This revision was produced and statically reviewed in an environment with no network access, so dependencies could not be installed and nothing below could be executed there. Before a demo, run these yourself from the project root with the virtual environment activated:

```bash
python -m compileall -q app main.py       # syntax check (already passed statically)
python -m alembic upgrade head             # requires local execution
pytest -q                                  # requires local execution
python main.py                             # requires local execution + OPENAI_API_KEY for /chat
```

If anything fails, the fastest path to a fix is pasting the exact error output back for another pass.
