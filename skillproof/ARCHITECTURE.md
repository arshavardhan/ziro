# SkillProof AI — Target System Architecture

## 1. System Overview

SkillProof AI is an autonomous, agentic skill-verification platform designed for the Agentic AI Hackathon 2026 Grand Finale. It verifies candidate software engineering skills directly against real GitHub repositories through deterministic static analysis, repository-grounded RAG retrieval, multi-cycle agent investigation, sandboxed test execution, source-grounded viva interrogation, and cryptographic credential issuance.

```
                              +---------------------------------+
                              |        Candidate Input          |
                              |   (GitHub URL, Claimed Skills)  |
                              +----------------+----------------+
                                               |
                                               v
                              +---------------------------------+
                              |         FastAPI Backend         |
                              |   (Validation, Auth, Routing)   |
                              +----------------+----------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
|                                 LangGraph Agent Orchestrator                                  |
|                                                                                               |
|  [initialize] --> [validate_url] --> [acquire_repository] --> [analyze_source_code]            |
|                                                                      |                        |
|  [execute_investigation] <-- [plan_investigation] <-- [retrieve_rag] <-- [index_rag]           |
|          |                                                                                    |
|          v                                                                                    |
|  [reflect_and_replan] --(missing evidence & budget < MAX_CYCLES)--> [execute_investigation]  |
|          |                                                                                    |
|          +--(evidence sufficient OR budget exhausted)----------------+                        |
|                                                                      |                        |
|                                                                      v                        |
|  [finalize_assessment] <-- [generate_viva] <-- [evaluate_skills] <---+                        |
+-----------------------------------------------------------------------------------------------+
                                               |
            +----------------------------------+----------------------------------+
            |                                  |                                  |
            v                                  v                                  v
+-----------------------+          +-----------------------+          +-----------------------+
|   Interactive Viva    |          |   Human Review Gate   |          | Cryptographic Signing |
| (5 Source-Grounded Qs |          | (Explicit Human Sign- |          | (Canonical HMAC-SHA256|
|  + Follow-up Engine)  |          |  off Required)        |          |  Tamper-Proof Proof)  |
+-----------------------+          +-----------------------+          +-----------------------+
            |                                  |                                  |
            +----------------------------------+----------------------------------+
                                               |
                                               v
                              +---------------------------------+
                              |    Verified Credential Issued   |
                              |   & Nine-Section Report Ready   |
                              +---------------------------------+
```

---

## 2. Core Architectural Components

### 2.1. FastAPI Backend (`backend/api/`)
- **Lifecycle Endpoints**: `/api/analyze`, `/api/session/{id}`, `/api/session/{id}/timeline`, `/api/session/{id}/evidence`, `/api/session/{id}/report`.
- **Viva Interrogation**: `/api/viva/{id}/questions`, `/api/viva/{id}/answer`.
- **Reviewer Approval**: `/api/approve/{id}` (protected by `X-Reviewer-Token`).
- **Credential Issuance & Verification**: `/api/credential/{id}/issue`, `/api/credential/{id}`, `/api/credential/verify`.
- **Strict Validation**: All payloads adhere to typed Pydantic models (`StrictModel`) rejecting extra or malformed fields.

### 2.2. LangGraph Agent Orchestrator (`backend/agents/graph.py`)
- **Framework**: Built on LangGraph with state-machine semantics.
- **State Representation (`AssessmentState`)**: Typed dictionary tracking repository metadata, pinned commit SHA, inventory, code evidence graph, RAG chunks, multi-cycle agent plans, test results, viva questions/answers, and lifecycle status.
- **State Persistence**: Uses `SqliteSaver` checkpointer persisting graph checkpoints to `db.sqlite3` with thread-level isolation (`session_id`).
- **Dynamic Investigation Cycle**:
  1. `plan_investigation`: Criticizes current evidence against claimed skills and emits concrete actions (`inspect_files`, `find_tests`, `read_symbol`).
  2. `execute_investigation`: Dispatches tools safely, recording inputs, execution time, and outputs.
  3. `reflect_and_replan`: Reflects on newly discovered evidence and updates missing evidence gaps.
  4. `route_investigation`: Conditional router branching back to execution if evidence gaps remain and budget (`MAX_CYCLES = 3`) is unexhausted; advances to evaluation upon satisfaction or budget depletion.

### 2.3. Repository-Grounded RAG System (`backend/rag/`)
- **AST-Aware Chunker (`chunker.py`)**:
  - Parses Python files via Python AST to extract classes, functions, async functions, docstrings, and exact 1-indexed line spans (`start_line`, `end_line`).
  - Processes non-Python files using a line-block sliding window with chunk overlap.
- **Embedding Subsystem (`embeddings.py`)**:
  - Primary: Gemini `gemini-embedding-001` yielding normalized high-dimensional vectors.
  - Fallback: Deterministic 384-dimensional n-gram offline embedder ensuring full test-suite isolation without external network flakiness.
- **Scoped Vector Store (`vector_store.py`)**:
  - Backed by SQLite table `rag_chunks`.
  - Scoped strictly to `(session_id, commit_sha)` to prevent cross-assessment leakage.
  - Cosine similarity search with configurable minimum score thresholding.
- **Skill-Targeted Retriever (`retriever.py`)**:
  - Generates targeted queries per claimed skill (e.g., `"Python syntax object-oriented architecture"`).
  - Retrieves top-k relevant code chunks, deduplicates line ranges, and transforms matches into traceable evidence items (`RAG-xxx`).

### 2.4. Static Analysis & Git Forensics (`backend/tools/`)
- **Python AST Tool (`ast_tool.py`)**:
  - Extracts functions, classes, complexity metrics, cyclomatic complexity, docstrings, imports, and call dependencies.
  - Classifies implementation state:
    - `IMPLEMENTED`: Full function body with substantive statements.
    - `PARTIALLY_IMPLEMENTED`: Placeholders, partial logic, or placeholder returns.
    - `PLANNED`: Pure stubs (`pass`, `raise NotImplementedError`, docstring only).
- **Git Forensics Tool (`git_tool.py`)**:
  - Inspects commit count, author diversity, commit timestamp cadence, and file entropy.
  - Flags squashed single-commit repositories or single-author histories.

### 2.5. Safe Test Execution Engine (`backend/tools/pytest_tool.py`)
- **Static Discovery**: Parses test files and discovers test definitions (e.g., 121 in AegisAI baseline) without executing code.
- **Isolated Execution Guard**:
  - Probes for Docker availability (`shutil.which('docker')` and daemon connectivity check).
  - When Docker is unavailable, marks status as `NOT_PERFORMED` (`reason: 'Docker unavailable'`).
  - **Zero Host Execution Rule**: Strictly forbids spawning candidate code directly on the host machine.
  - Does not treat `NOT_PERFORMED` tests as candidate failures; computes evidence coverage separately and leaves `test_score: None`.

### 2.6. LLM Reasoning Adapter (`backend/agents/llm.py`)
- **Model**: Google Gemini `gemini-3.5-flash-lite` configured with Gemini REST API.
- **Structured Outputs**: Pydantic schema validation for plans, assessments, viva questions, and evaluations.
- **Reliability Bounds**: 10-second bounded HTTP timeout, maximum 2 retries, sanitized error handling.

### 2.7. Human-in-the-Loop Viva & Reviewer Approval (`backend/api/routes/`)
- **Source-Grounded Viva**: 5 questions (conceptual, implementation, debugging) citing exact verified code evidence. Evaluates candidate answers against rubrics and requests up to 1 follow-up for incomplete responses.
- **Human Approval**: Mandatory human review step (`/api/approve/{id}`). A human rejection is terminal. A high numerical algorithm score cannot bypass human sign-off.

### 2.8. Cryptographic Credential Issuance (`backend/security/signing.py`)
- **Canonical Payload Normalization**: Recursive sorting of dictionary keys, ISO-8601 UTC timestamps, and compact JSON encoding.
- **HMAC-SHA256 Signature**: Signed with server `SIGNING_SECRET`.
- **Tampering Resistance**: Any alteration of candidate ID, score, skill list, or test execution status invalidates signature verification.

---

## 3. Technology Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| **API Framework** | FastAPI + Uvicorn | Async web framework, OpenAPI contract generation |
| **Agent Orchestration** | LangGraph + LangChain Core | State graph, conditional routing, cyclic investigation |
| **LLM Reasoning** | Google Gemini (`gemini-3.5-flash-lite`) | Code critique, skill assessment, viva generation |
| **Embeddings** | Gemini (`gemini-embedding-001`) + Offline Fallback | RAG vectorization, semantic search |
| **Vector & App Storage** | SQLite (`rag_chunks`, `sessions`, `events`) | Scoped vector storage, state checkpointing |
| **Static Code Analysis** | Python `ast`, `tokenize`, `radon` | Syntax trees, implementation classification |
| **Git Operations** | Git CLI subprocesses | Pinned shallow clone, history & commit analysis |
| **Cryptography** | `hmac`, `hashlib` (SHA-256) | Canonical credential signing and verification |
| **Testing & Evaluation** | Pytest, AnyIO | 77 backend unit/reliability tests, 22 synthetic eval cases |
