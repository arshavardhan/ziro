# Backend Audit — SkillProof AI

## 1. Executive Summary & Baseline Preservation

SkillProof AI is an Autonomous Skill-Proof Verification Agent backend built for the Agentic AI Hackathon 2026 Grand Finale.

### Historical Verified Baseline (AegisAI)
The historical repository baseline analysis of AegisAI (`https://github.com/arshavardhan/AegisAi`, commit `79112160653cc38cdcbddaf578e29ecfbd58a70a`, session `25b09616-1cea-4b7d-8f9f-a53359c8f800`) is preserved intact:
- **Text files analyzed**: 52
- **Static source findings**: 383
- **Git commits discovered**: 33
- **Discovered test definitions**: 121
- **Test execution status**: `NOT_PERFORMED` (Docker unavailable on host; host execution strictly blocked for safety)
- **Zero live model calls during initial static baseline capture**: Deterministic acquisition precedes model evaluation to prevent missing API keys from erasing the baseline.
- **Artifact integrity**: Preserved byte-for-byte in `skillproof/artifacts/` (`aegis-static-report.json`, `aegis-summary.json`, `evaluation-results.json`) and verified against `manifest.json`.

### Synthetic Evaluation Status
- **Regression test result**: 22 / 22 synthetic test cases passed (100% pass rate).
- **Classification fixtures**: 6 small fixtures used for regression testing.
- **Mandatory Disclosure**: All 22 synthetic evaluation cases passed. Classification metrics are calculated from six small fixtures and are intended for internal regression testing, not as estimates of real-world accuracy. This result is never advertised as production model accuracy or conflated with candidate skill confidence.

---

## 2. Component-by-Component Audit

| Component | Status | Verification & Code Evidence |
|---|---|---|
| **FastAPI Backend & API Endpoints** | **COMPLETED** | Strict Pydantic models for all requests/responses (`schemas/session.py`, `schemas/credential.py`, etc.). Read and write endpoints for session lifecycle, evidence inspection, timeline, viva interrogation, human reviewer approval, and credential issuance/verification. Validated via `test_api.py`. |
| **LangGraph Agent Orchestration** | **COMPLETED** | Fully implemented in `agents/graph.py` with typed `AssessmentState`, granular functional nodes, dynamic investigation routing (`route_investigation`), and state persistence via `SqliteSaver` checkpointer. Verified in `test_langgraph_rag.py`. |
| **Repository-Grounded RAG** | **COMPLETED** | Implemented in `skillproof/backend/rag/` (`chunker.py`, `embeddings.py`, `vector_store.py`, `retriever.py`). AST-aware Python chunker extracts classes, functions, docstrings, and line ranges. SQLite-backed vector store strictly scoped to `(session_id, commit_sha)`. Cosine similarity search with threshold filtering. Verified in `test_langgraph_rag.py`. |
| **Gemini LLM & Embedding Integration** | **COMPLETED** | Configured for active models `gemini-3.5-flash-lite` and `gemini-embedding-001`. Includes deterministic offline fallback embeddings for test isolation and offline resilience. Verified with live API connectivity. |
| **Repository Acquisition & Pinned Snapshots** | **COMPLETED** | Real git shallow/commit-pinned acquisition in `services/repository_service.py` and `tools/github_tool.py`. Stores clone timestamp, pinned commit SHA, default branch, file hashes, and acquisition metadata. Rejects moving branch references for assessment identity. |
| **Static Code Analysis (AST)** | **COMPLETED** | `tools/ast_tool.py` analyzes Python AST for functions, classes, complexity, docstrings, imports, call graphs, and implementation state (`IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `PLANNED`). Produces structured, traceable evidence items with line numbers. |
| **Git History Analysis** | **COMPLETED** | `tools/git_tool.py` analyzes git log, commit count, authorship distribution, commit cadence, and entropy. Detects squashed histories and single-committer anomalies. |
| **Test Discovery & Sandbox Execution** | **COMPLETED** | `tools/pytest_tool.py` statically parses test definitions (121 in AegisAI baseline). Safely checks Docker availability (`shutil.which('docker')` and daemon ping); if Docker is missing, returns `NOT_PERFORMED` (`reason: 'Docker unavailable'`) and strictly refuses to execute untrusted candidate code on host. |
| **Dynamic Tool Selection & Agent Cycles** | **COMPLETED** | Multi-cycle dynamic loop bounded by `MAX_CYCLES=3` and time budget. The agent planner critiques missing evidence and selects specific tools (`inspect_files`, `find_tests`, etc.) rather than following a static pipeline. Records full cycle executions, inputs, and outputs. |
| **Evidence Traceability & Scoring** | **COMPLETED** | `services/scoring_service.py` enforces that every numerical score requires valid supporting evidence citations. Duplicate evidence does not inflate scores; missing or fabricated citations invalidate score eligibility. Unexecuted tests are graded as `test_score: None` without failing the candidate. |
| **Repository-Specific Viva Interrogation** | **COMPLETED** | `agents/viva_generator.py` and `viva_evaluator.py` generate 5 source-grounded questions targeting verified code symbols and line ranges. Evaluates conceptual, implementation, and debugging knowledge with follow-up questions for incomplete answers. |
| **Human Reviewer Gate & Terminal Rejection** | **COMPLETED** | Protected by `X-Reviewer-Token`. Reviewer can approve or reject. Rejection is terminal and prevents credential issuance. Issuance requires passing viva and evidence eligibility gates. |
| **Cryptographic Credential Issuance & Signing** | **COMPLETED** | `security/signing.py` canonicalizes credential payloads and generates HMAC-SHA256 signatures. Verification endpoint detects any field tampering (e.g. changing candidate ID or test execution status). |
| **SQLite Checkpointing & Crash Recovery** | **COMPLETED** | State and timeline events persisted to SQLite. `orchestrator.recover()` resumes interrupted sessions from their last durable checkpoint at the pinned commit SHA. |
| **Synthetic Evaluation Harness** | **COMPLETED** | `evaluation/run_evaluation.py` executes 22 synthetic test cases against 6 fixtures. Explicit disclosure reports regression purpose without making real-world accuracy claims. |
| **Frontend Integration** | **PENDING USER INPUT** | Frontend is deliberately untouched in accordance with Section 1 requirements. Backend OpenAPI spec and offline schemas are exported and ready for handoff. |
| **Real Candidate Viva Session** | **PENDING USER INPUT** | Backend viva engine is ready; awaiting actual user candidate session. |

---

## 3. Architecture & Agent Orchestration Audit

### Agent Loop Evolution
- **Previous Implementation**: Custom orchestrator loop in `orchestrator.py` executing synchronous phases with checkpointing.
- **Target Implementation**: State-machine-driven LangGraph orchestrator in `agents/graph.py` with typed `AssessmentState`, conditional branching (`route_investigation`), and persistent SQLite checkpointing via `SqliteSaver`.
- **Dynamic Tool Selection**: Not a fixed linear sequence. After initial deterministic baseline capture, the planner analyzes observed facts and gaps (`missing_evidence`), emits tool actions with rationale, executes tools, reflects on findings, and replans until either evidence is sufficient, no useful actions remain, or budget is exhausted.

### RAG Architecture
- **Chunker**: AST-aware chunking parses Python files into top-level functions, classes, and methods with docstrings and exact line ranges. Non-Python files use sliding-window line chunks.
- **Embeddings**: Utilizes Gemini `gemini-embedding-001` with normalized vector output. Features a deterministic n-gram fallback embedder ensuring zero test failures in offline or sandboxed environments.
- **Storage**: Scoped SQLite table `rag_chunks` indexed by `(session_id, commit_sha)` with cosine similarity search and minimum score thresholding.
- **Retrieval**: Maps claimed candidate skills to semantic queries, retrieves top-k chunks, deduplicates line ranges, and transforms them into traceable evidence objects.

---

## 4. Test Suite Verification Summary

All test suites pass completely:
1. **Reliability Regression Suite (`tests/test_reliability.py`)**: 21/21 PASSED.
   - Separate test discovery vs execution semantics.
   - Docker-unavailable safety enforcement (no host execution).
   - Baseline serialization, SHA verification, and immutability.
   - Repeated same-commit vs new-commit classification.
   - Original AegisAI artifact hash preservation.
   - Synthetic evaluation limitations disclosure.
   - Evidence context and citation traceability.
   - Duplicate evidence non-inflation.
   - Missing citation score invalidation.
   - Unavailable tests not treated as failures.
   - Viva source range grounding and invalid citation rejection.
   - Human approval and signed execution limits.
   - Bounded LLM timeouts and retry limits.
   - Multi-cycle dynamic tool execution logging.
   - Repository failure recording.
   - Missing LLM key baseline preservation.
   - SQLite recovery and state preservation.
   - Nine-section report generation.
2. **LangGraph & RAG Test Suite (`tests/test_langgraph_rag.py`)**: 7/7 PASSED.
   - AST-aware Python code chunking.
   - Text/line-block chunking.
   - Cross-session vector store isolation.
   - Skill retrieval and evidence traceability.
   - LangGraph graph compilation.
   - Conditional routing and investigation cycle termination.
   - SQLite checkpointer state recovery.
3. **Core Unit Test Suite (`tests/test_*.py`)**: 49/49 PASSED.
   - Snapshot entropy and trust scoring.
   - Agent restart and recovery.
   - Read/write API endpoints.
   - Human approval and rejection lifecycle.
   - Viva question generation, follow-ups, and grading.
   - HMAC credential signing, verification, and tampering detection.
   - AST implementation states (`IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `PLANNED`).
   - Pytest output parser.
   - Security guards (SSRF, path traversal, sensitive file redaction).
4. **Synthetic Evaluation Harness (`evaluation/run_evaluation.py`)**: 22/22 PASSED.
   - 100% pass rate across 6 fixtures with regression disclosure.

**Total pytest tests**: 77 / 77 PASSED.
