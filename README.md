# AI Intelligence Platform

An AI-powered intelligence platform for collecting, processing, analyzing, and presenting AI and technology information from multiple sources.

The platform combines automated data collection, AI-based processing, PostgreSQL storage, trend analysis, RAG-based knowledge retrieval, and a LangGraph tool-calling AI Agent through a FastAPI backend and a web dashboard.

---

## Overview

The **AI Intelligence Platform** is designed to transform raw AI and technology information into structured and useful intelligence.

The platform collects information from multiple sources, processes and filters the collected data, generates summaries, stores the results in PostgreSQL, and provides users with an AI Agent that can search the platform's knowledge and use application tools to answer questions.

It also provides an administration dashboard for managing platform data and monitoring AI Agent activity.

---

## Main Features

### Data Collection

The platform can collect AI and technology information from multiple sources, including:

* RSS feeds
* GitHub
* Hacker News
* arXiv
* Reddit

Collected data is normalized before entering the processing pipeline.

---

### Data Processing

The research pipeline performs several processing stages:

* Data cleaning
* Normalization
* Filtering
* Deduplication
* Classification
* Entity extraction
* Relevance scoring
* AI summarization
* Database persistence
* Trend analysis

The processing pipeline is designed to convert raw collected information into structured intelligence articles.

---

### PostgreSQL Database

The project uses **PostgreSQL** as the main database.

Database access is implemented using:

* SQLAlchemy ORM
* SQLAlchemy sessions
* Alembic migrations
* Repository-based database operations

The database contains the main platform entities such as:

* Users
* Articles
* Topics
* Sources
* Agent Activity
* Other application-related data

---

## AI Agent

The platform includes an authenticated AI Agent built using:

* LangChain
* LangGraph
* LLM APIs
* Tool Calling

The Agent receives a user query and can decide whether it needs to use one or more application tools before generating the final answer.

### Agent Flow

```text
User
  |
  v
FastAPI /chat
  |
  v
Authentication
  |
  v
LangGraph AI Agent
  |
  +----> search_articles
  |
  +----> get_topic_articles
  |
  +----> list_trends
  |
  +----> search_knowledge_base
  |
  +----> run_fresh_research
  |
  v
Tool Results
  |
  v
AI Agent
  |
  v
Final Answer
```

The Agent uses tool calling to access information stored inside the platform instead of relying only on the model's internal knowledge.

A maximum number of tool-call rounds is used to prevent the Agent from entering an endless tool-calling loop.

---

## Agent Tools

The current Agent can use application tools such as:

### `search_articles`

Searches stored intelligence articles using the user's query.

### `get_topic_articles`

Retrieves articles related to a stored topic.

### `list_trends`

Retrieves available trend information used by the platform.

### `search_knowledge_base`

Searches the local knowledge base using the RAG pipeline.

### `run_fresh_research`

Triggers fresh research through the platform's research pipeline when new information is required.

---

## RAG / Knowledge Base

The platform includes a local knowledge-base system used by the AI Agent.

The RAG pipeline allows the platform to retrieve relevant information from stored articles before generating an answer.

The knowledge-base functionality includes:

* Article indexing
* Text chunking
* Embedding generation
* Similarity-based retrieval
* Metadata storage
* Relevant document retrieval
* Category filtering
* Knowledge-base rebuilding

Relevant metadata can include:

* Article ID
* Title
* Source
* URL
* Published date
* Category

The RAG implementation is located under:

```text
app/rag/
```

---

## Research Pipeline

The main research workflow follows this general structure:

```text
Sources
   |
   v
Collect
   |
   v
Process
   |
   v
Summarize
   |
   v
Persist
   |
   v
Trend Analysis
   |
   v
Knowledge Base
```

The research pipeline can be executed through the FastAPI backend.

The system can also trigger fresh research when requested by the AI Agent.

---

## Admin Dashboard

The platform includes an administration interface for managing and monitoring the system.

The Admin Dashboard provides functionality for managing platform data such as:

* Users
* Topics
* Sources
* Articles
* AI Agent activity

The Admin functionality is protected through authentication and admin-level authorization.

### Agent Activity

The platform records AI Agent activity to provide administrators with information about Agent usage.

Agent activity can include:

* User ID
* User query
* Tools used
* Success status
* Creation timestamp

This information can be used to monitor how the AI Agent is being used inside the platform.

---

## FastAPI Backend

The backend is implemented using **FastAPI**.

The backend provides:

* Authentication
* User management
* Intelligence APIs
* Research APIs
* RAG APIs
* AI Agent APIs
* Analytics
* Admin functionality
* Database access

Interactive API documentation is available through:

```text
http://127.0.0.1:8000/docs
```

---

## Authentication

The platform uses JWT-based authentication.

Authentication includes:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

Protected endpoints require:

```text
Authorization: Bearer <token>
```

Passwords are stored using secure password hashing rather than storing plain-text passwords.

---

## Main API Areas

The exact available routes can be viewed through the FastAPI Swagger documentation.

Important API areas include:

```text
/health
/auth
/chat
/intelligence
/research
/rag
/knowledge
/analytics
/admin
```

The `/docs` endpoint provides the current API specification generated directly from the FastAPI application.

---

## Frontend

The platform includes a web frontend built using:

* HTML
* CSS
* JavaScript

The frontend communicates with the FastAPI backend.

Main application pages include:

* Login
* Registration
* Dashboard
* Intelligence Feed
* AI Agent Chat
* Trends
* Knowledge Base
* Analytics
* Admin Dashboard

The frontend is located under:

```text
frontend/
```

The FastAPI application can serve the frontend directly.

---

## n8n Integration

The project also includes **n8n** workflows for automation and notifications.

The n8n integration can be used for automation tasks such as:

* High-relevance article notifications
* Research-related automation
* Platform event handling
* External workflow execution

The n8n-related files are located under:

```text
n8n/
```

Webhook URLs and other sensitive configuration values should be stored in `.env` and should never be committed to GitHub.

---

## Project Structure

The main project structure is organized as follows:

```text
AI_Intelligence_Platform/
│
├── app/
│   ├── api/
│   │   ├── admin/
│   │   ├── ...
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── database/
│   │   ├── base_class.py
│   │   ├── session.py
│   │   ├── repositories/
│   │   └── migrations/
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── article.py
│   │   ├── topic.py
│   │   ├── source.py
│   │   ├── agent_activity.py
│   │   └── ...
│   │
│   ├── graph/
│   │   ├── agent_graph.py
│   │   ├── agent_state.py
│   │   └── agent_tools.py
│   │
│   ├── rag/
│   │   └── ...
│   │
│   ├── processing/
│   │   └── ...
│   │
│   ├── collectors/
│   │   └── ...
│   │
│   ├── summarization/
│   │   └── ...
│   │
│   ├── trends/
│   │   └── ...
│   │
│   └── services/
│       └── ...
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── admin/
│   ├── ...
│   ├── style.css
│   └── app.js
│
├── n8n/
│   └── ...
│
├── scripts/
│   └── ...
│
├── tests/
│   └── ...
│
├── docs/
│   └── ...
│
├── alembic.ini
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Configuration

The project uses environment variables for configuration.

Create a local `.env` file based on `.env.example`.

Example:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/ai_intelligence_platform

JWT_SECRET_KEY=your-secret-key

LLM_PROVIDER=groq
LLM_MODEL=your-model-name

GROQ_API_KEY=your-api-key

N8N_HIGH_RELEVANCE_WEBHOOK_URL=your-webhook-url
```

The exact variables depend on the current configuration in:

```text
app/core/config.py
```

### Important

Never commit `.env` to GitHub.

The project uses `.gitignore` to exclude sensitive configuration files such as:

```text
.env
.venv/
__pycache__/
*.pyc
```

Only `.env.example` should be committed if it is provided without real secrets.

---

## PostgreSQL Setup

Create a PostgreSQL database for the project.

Example database name:

```text
ai_intelligence_platform
```

Then configure the connection string in `.env`:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/ai_intelligence_platform
```

The application uses SQLAlchemy to connect to PostgreSQL.

---

## Database Migrations

Alembic is used for database migrations.

After configuring the database, run:

```bash
python -m alembic upgrade head
```

To create a new migration after model changes:

```bash
python -m alembic revision --autogenerate -m "update database models"
```

Then apply the migration:

```bash
python -m alembic upgrade head
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/MenaKhawaga/AI_Intelligence_Platform.git
cd AI_Intelligence_Platform
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create:

```text
.env
```

from:

```text
.env.example
```

Then configure PostgreSQL, authentication, LLM, and n8n settings.

### 5. Run database migrations

```bash
python -m alembic upgrade head
```

### 6. Start the application

```bash
python main.py
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Running the Frontend

The frontend can be served through the FastAPI application.

Alternatively, the `frontend/` directory can be opened using a local static server such as VS Code Live Server.

The frontend communicates with the FastAPI backend running on:

```text
http://127.0.0.1:8000
```

---

## Testing

Run the test suite from the project root:

```bash
pytest -q
```

Tests cover major application components including:

* Authentication
* Database operations
* Repositories
* Collectors
* Processing
* Summarization
* Research workflow
* AI Agent
* LangGraph orchestration
* Tool calling
* RAG
* Trends
* API behavior

---

## Technology Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* Pydantic

### AI / Agent

* LangChain
* LangGraph
* LLM APIs
* Tool Calling
* RAG

### Data Sources

* RSS
* GitHub
* Hacker News
* arXiv
* Reddit

### Frontend

* HTML
* CSS
* JavaScript

### Automation

* n8n

### Development

* Git
* GitHub
* Pytest
* Python Virtual Environment

---

## Security

The project follows several security practices:

* JWT authentication
* Password hashing
* Protected API endpoints
* Admin authorization
* Environment variables for secrets
* `.env` excluded from Git
* Non-sensitive `.env.example` configuration
* Input validation through FastAPI/Pydantic
* Controlled AI Agent tool execution

This project is intended primarily as an academic project and local development system and should be further hardened before production deployment.

---

## Future Improvements

Possible future improvements include:

* Cloud deployment
* Advanced monitoring
* Real-time notifications
* WebSocket-based Agent communication
* More data sources
* Improved semantic search
* Advanced vector databases
* More advanced multi-agent workflows
* Automated evaluation of AI Agent responses
* Production-grade observability
* Role-based permissions with more granular access control

---

## Academic Project

**AI Intelligence Platform** is an academic software project focused on combining:

* Artificial Intelligence
* AI Agents
* LLMs
* Tool Calling
* RAG
* Data Engineering
* Backend Development
* Database Systems
* Information Retrieval
* Trend Analysis
* Web Development
* Workflow Automation

The project demonstrates how these technologies can be integrated into a single end-to-end intelligence platform.

---

## Repository

GitHub:

https://github.com/MenaKhawaga/AI_Intelligence_Platform
