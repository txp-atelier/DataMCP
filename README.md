# DataMCP

DataMCP is an AI-powered assistant for querying multiple databases using natural language.

It currently supports PostgreSQL, MySQL, and MongoDB. The backend uses an AI agent to select the required database tools through MCP, while RAG is used for database schema retrieval and saved knowledge.

## Features

* Natural-language queries across multiple databases
* PostgreSQL, MySQL, and MongoDB support
* MCP server for database and knowledge tools
* Agent-based tool and database selection
* RAG-based schema search
* Notion integration for persistent knowledge
* Conversation saving to Notion
* Semantic search over saved Notion knowledge
* Read-only database query execution
* Encrypted integration credentials
* Docker Compose development environment

## Architecture

```text
Next.js
   │
   ▼
FastAPI
   │
   ▼
Agent Service
   │
   ├───────────────┐
   ▼               ▼
MCP Server         RAG
   │               │
   ├───────┐       ├── Schema Search
   │       │       └── Knowledge Search
   ▼       ▼
Postgres  MySQL
   │
   └──── MongoDB

MCP / Backend
      │
      ▼
    Notion
```

The agent is responsible for deciding which tools are required for a request. MCP exposes the database and knowledge operations as tools.

## Example

A request such as:

```text
How many customers are there in MongoDB?
```

is handled roughly as:

```text
User question
      ↓
Agent
      ↓
MongoDB tool
      ↓
MongoDB
      ↓
Result
      ↓
Agent response
```

For a question where the database is not specified:

```text
Show me all customers
```

the agent can inspect the connected databases and ask the user to specify the database when the same table exists in multiple databases.

## MCP Tools

The MCP server currently exposes tools for:

### Databases

* `list_connections`
* `get_database_schema`
* `search_schema`
* `describe_table`
* `get_sample_data`
* `execute_read_query`
* `execute_mongodb_query`

### Knowledge / Notion

* `notion_connection_status`
* `search_knowledge`
* `search_notion`
* `get_notion_page`
* `create_notion_page`
* `update_notion_page`
* `ingest_notion_page`

## RAG

RAG is used in two areas.

### Database schema

Database schemas are converted into documents and stored in ChromaDB. The agent can search the relevant schema before working with a database.

```text
Database
   ↓
Schema extraction
   ↓
Documents
   ↓
Embeddings
   ↓
ChromaDB
   ↓
Semantic search
```

### Saved knowledge

Notion pages can be ingested into the same retrieval layer. This allows information saved from previous conversations or documentation to be searched later.

## Database Support

| Database   | Status    |
| ---------- | --------- |
| PostgreSQL | Supported |
| MySQL      | Supported |
| MongoDB    | Supported |

Database-specific connection and query logic is separated into adapters.

## Notion

Notion is used as the external knowledge layer.

The integration supports:

* OAuth connection
* Connection status
* Disconnecting the integration
* Searching pages
* Reading pages
* Creating pages
* Updating pages
* Ingesting pages into RAG
* Saving conversations

Before creating or updating a page, the agent checks whether the Notion integration is connected.

## Query Safety

SQL execution is restricted to read operations.

The backend rejects operations including:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
```

Multiple SQL statements and SQL comments are also rejected.

Database and integration credentials are kept outside the source code. Local secret files and environment files are excluded through `.gitignore`.

## Project Structure

```text
DataMCP/
├── backend/
│   ├── app/
│   │   ├── adapters/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── layout.tsx
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
│
├── mcp-server/
│   ├── app/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── rag/
│   ├── app/
│   │   ├── embeddings.py
│   │   ├── main.py
│   │   └── vector_store.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Tech Stack

* **Frontend:** Next.js, React, TypeScript
* **Backend:** Python, FastAPI, Pydantic
* **AI:** Groq, Agentic AI
* **Tooling:** MCP
* **RAG:** ChromaDB, Sentence Transformers
* **Databases:** PostgreSQL, MySQL, MongoDB
* **Integration:** Notion API, OAuth
* **Infrastructure:** Docker, Docker Compose

## Running Locally

The project is designed to run through Docker Compose.

Create the environment file:

```bash
cp .env.example .env
```

Add the required API and integration credentials to `.env`.

Start the services:

```bash
docker compose up --build
```

Main services:

```text
Frontend    http://localhost:3000
Backend     http://localhost:8000
MCP Server  http://localhost:8001
RAG         http://localhost:8002
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

## Environment Variables

The exact values depend on the local setup. See `.env.example` for the required variables.

Do not commit `.env` or other secret files.

## Current Scope

DataMCP is currently focused on:

* Multi-database querying
* Agentic tool selection
* MCP-based integrations
* Schema and knowledge retrieval
* Notion-backed persistent knowledge

Production authentication, deployment, observability, and additional database integrations are outside the current scope.
