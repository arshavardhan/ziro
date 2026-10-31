# SkillProof AI — Master Implementation Plan

## 1. Development Principles & Anti-Fabrication Rules

SkillProof AI adheres strictly to truth-in-verification standards. The following anti-fabrication rules govern all phases of backend development:

- **No Fake Repositories**: Assessments are performed only on real repository snapshots cloned at pinned commit SHAs. Demo repositories are prohibited for candidate evaluations.
- **No Fabricated Commit Histories**: Git findings must derive from actual git logs; no synthetic commit histories are created.
- **No Fabricated Test Results**: Statically discovered test definitions (e.g. 121 in AegisAI) are never conflated with executed tests. When isolated execution is unavailable (Docker unavailable), test execution is strictly recorded as `NOT_PERFORMED`.
- **No Placeholder Credentials**: Verified credentials are issued only after passing deterministic evidence checks, source-grounded viva, and explicit human reviewer approval.
- **No Hardcoded Evaluation Scores**: Scores derive from verified code evidence citations. Duplicate evidence does not inflate scores; missing citations invalidate scores.
- **No Fake Viva Sessions**: Questions cite exact verified symbols and line numbers from the analyzed repository.
- **Baseline Provenance Preservation**: The AegisAI baseline (`52` text files, `383` source findings, `33` commits, `121` test definitions, `NOT_PERFORMED` test execution) is an immutable historical observation and is preserved intact.

---

## 2. Phased Implementation Roadmap

### Phase 1: Backend Architecture & Persistence
- **Status**: `COMPLETED`
- Built FastAPI application (`main.py`, `api/routes/`).
- Designed SQLite relational schema (`sessions`, `events`, `tool_executions`, `agent_plans`, `skill_evidence`, `viva_questions`, `credentials`).
- Created database migration system (`database/migrations.py`).
- Implemented static AST analyzer (`tools/ast_tool.py`), Git forensics tool (`tools/git_tool.py`), and test discovery tool (`tools/pytest_tool.py`).

### Phase 2: LangGraph Agent Orchestrator
- **Status**: `COMPLETED`
- Replaced custom linear sequences with a compiled stateful LangGraph graph (`agents/graph.py`).
- Defined typed `AssessmentState` holding full pipeline state.
- Implemented functional nodes: `initialize`, `validate_url`, `acquire_repository`, `analyze_source_code`, `index_repository_rag`, `retrieve_skill_evidence_rag`, `plan_investigation`, `execute_investigation`, `reflect_and_replan`, `evaluate_skills`, `generate_viva`, `finalize_assessment`.
- Added conditional routing `route_investigation` dynamically deciding whether to replan and run additional investigation tools or advance to skill evaluation based on evidence gaps and budget (`MAX_CYCLES = 3`).
- Integrated `SqliteSaver` checkpointer for thread-level state persistence and crash recovery.

### Phase 3: Repository-Grounded RAG Intelligence
- **Status**: `COMPLETED`
- Implemented AST-aware Python chunker (`rag/chunker.py`) extracting classes, functions, docstrings, and line ranges.
- Implemented line-block chunker with overlap for non-Python repository files.
- Built embedding adapter (`rag/embeddings.py`) supporting Gemini `gemini-embedding-001` with deterministic offline n-gram fallback for test resilience.
- Created SQLite vector store (`rag/vector_store.py`) strictly isolated by `(session_id, commit_sha)` with cosine similarity search and thresholding.
- Implemented semantic skill retriever (`rag/retriever.py`) producing traceable `RAG-xxx` evidence items.

### Phase 4: Complete Assessment Pipeline
- **Status**: `COMPLETED`
- Pinned commit SHA acquisition and snapshot hashing in `services/repository_service.py`.
- Deterministic baseline capture precedes model calls.
- Scoring service (`services/scoring_service.py`) enforcing citation integrity.
- Source-grounded viva generation with follow-up support (`agents/viva_generator.py`, `viva_evaluator.py`).
- Human reviewer gate requiring `X-Reviewer-Token` (`api/routes/approve.py`).
- Cryptographic HMAC-SHA256 credential signing (`security/signing.py`).

### Phase 5: Backend Testing, Security & Reliability
- **Status**: `COMPLETED`
- 77 pytest backend unit and reliability tests passing (100% pass rate).
- 22 synthetic evaluation cases passing (100% pass rate).
- Docker-unavailable safety gate preventing untrusted host code execution.
- Security URL guard against SSRF and private IPs.
- Path traversal guard preventing access to host files or credentials.
- Bounded LLM execution timeouts (10s) and bounded agent cycles.

### Phase 6: API Documentation & Schema Contract
- **Status**: `COMPLETED`
- Exported OpenAPI specification (`openapi.json`).
- Exported offline schema definitions (`schemas.json`).
- Updated API Contract v2.0 (`CONTRACT.md`) with RAG fields (`rag_indexed`, `rag_chunks_count`, `rag_evidence`).
- Generated comprehensive architecture and design documents.

### Phase 7: Frontend Integration
- **Status**: `PENDING USER INPUT`
- Per user instructions, frontend integration is strictly deferred until the user provides:
  1. The actual GitHub repository URL to analyze.
  2. The CI/CD pipeline configuration and requirements.
  3. The frontend project details.
