# SkillProof AI — Deployment & Operations Guide

## 1. System Requirements

- **Operating System**: Windows 10/11, Windows Server, or Linux/macOS.
- **Python**: Version 3.11, 3.12, 3.13, or 3.14.
- **Git**: System Git CLI installed and available on PATH (`git --version`).
- **Docker** (Optional): If Docker is installed and running, test execution can run in isolated containers. If Docker is absent, the system safely records `test_execution['status'] = 'NOT_PERFORMED'` without failing candidate evaluations.

---

## 2. Environment Configuration

Configuration is managed via environment variables or a `.env` file located in `skillproof/backend/.env`.

### Environment Variables Reference

| Variable | Description | Default / Recommended |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for LLM and embeddings | *(Required for live reasoning)* |
| `LLM_MODEL` | Gemini LLM model identifier | `gemini-3.5-flash-lite` |
| `EMBEDDING_MODEL` | Gemini Embedding model identifier | `gemini-embedding-001` |
| `SIGNING_SECRET` | Secret key used for HMAC-SHA256 credential signatures | *(32+ char random string)* |
| `REVIEWER_TOKEN` | Token required in `X-Reviewer-Token` header for approvals | *(Strong secret string)* |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `http://localhost:3000,http://localhost:5173` |
| `DB_PATH` | Path to the SQLite database file | `db.sqlite3` |
| `PORT` | HTTP server listening port | `8001` *(8000 reserved for Teklozy)* |
| `ORCHESTRATOR_ENGINE`| Agent orchestration engine | `langgraph` |
| `RAG_TOP_K` | Number of chunks retrieved per claimed skill | `5` |
| `MAX_CYCLES` | Maximum dynamic investigation cycles | `3` |
| `AGENT_BUDGET_SECONDS` | Maximum allowed runtime per assessment | `300` |

### Sample `.env` File
```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-3.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001
SIGNING_SECRET=synthetic-production-signing-secret-key-32chars
REVIEWER_TOKEN=production-reviewer-token-secret
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
PORT=8001
ORCHESTRATOR_ENGINE=langgraph
RAG_TOP_K=5
MAX_CYCLES=3
AGENT_BUDGET_SECONDS=300
```

---

## 3. Database Initialization & Migrations

Database tables (`sessions`, `events`, `tool_executions`, `agent_plans`, `skill_evidence`, `viva_questions`, `credentials`, `rag_chunks`) are initialized automatically on application startup.

To run migrations manually:
```bash
cd skillproof/backend
python -c "from database.migrations import migrate; migrate()"
```

---

## 4. Starting the Backend Server

To start the FastAPI application with Uvicorn:

```bash
cd skillproof/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

> **Note on Port 8001**: Port 8001 is configured because port 8000 serves an existing local Teklozy service on this machine.

---

## 5. Health Check & Verification

Once started, verify service availability:

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "orchestrator": "langgraph",
  "rag_enabled": true,
  "database": "connected"
}
```

Interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`
