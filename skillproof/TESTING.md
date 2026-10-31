# SkillProof AI — Testing & Evaluation Guide

## 1. Test Suite Summary

SkillProof AI maintains a multi-layer test suite covering deterministic static tools, LangGraph orchestration, RAG retrieval, API contract enforcement, security boundaries, and synthetic evaluation regressions.

```
+-----------------------------------------------------------------------------------------+
|                                    TEST MATRIX SUMMARY                                  |
|                                                                                         |
|  1. Core Unit Tests (`tests/test_*.py`)                : 49 tests  --> 49/49 PASSED     |
|  2. Reliability Regressions (`tests/test_reliability.py`): 21 tests  --> 21/21 PASSED     |
|  3. LangGraph & RAG Tests (`tests/test_langgraph_rag.py`):  7 tests  -->  7/7  PASSED     |
|                                                          ------------------------------ |
|     Total Automated Pytest Suite                        : 77 tests  --> 77/77 PASSED     |
|                                                                                         |
|  4. Synthetic Evaluation Suite (`evaluation/run_evaluation.py`): 22 cases -> 22/22 PASSED|
+-----------------------------------------------------------------------------------------+
```

---

## 2. Test Suite Breakdown

### 2.1. Core Unit Tests (49 Tests)
Located in `skillproof/backend/tests/`:
- `test_aegis_snapshot.py`: Entropy-to-trust scoring and planned wrapper behavior.
- `test_agents.py`: LLM adapter, structured output parsing, restart recovery, missing evidence handling, invalid JSON bounding.
- `test_api.py`: FastAPI read/write endpoints, lifecycle state transitions, approval/rejection logic, viva answer submissions, follow-up generation, CORS, and error schemas.
- `test_credentials.py`: Independent HMAC signing, verification, and wrong secret rejection.
- `test_evaluation.py`: Classification metric fixtures and error counting.
- `test_evidence.py`: AST implementation states (`IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `PLANNED`), docstring vs implementation separation, empty repository handling, line reference call graphs, duplicate code detection, pytest result parser, missing test handling.
- `test_security.py`: URL guard (SSRF prevention, non-GitHub rejection, credential stripping), path traversal prevention (`..`, `.env`, private keys), secret redaction, sandbox execution limits, shell command injection prevention.

### 2.2. Reliability Regression Tests (21 Tests)
Located in `skillproof/backend/tests/test_reliability.py`:
- `test_discovery_execution_separate`: Validates test discovery counts vs test execution status separation.
- `test_docker_unavailable_never_spawns_candidate`: Enforces host execution prohibition when Docker is absent.
- `test_docker_present_but_unusable_is_blocked`: Handles non-responsive Docker daemons safely.
- `test_baseline_serialization_and_sha`: Verifies commit SHA identity and baseline immutability.
- `test_frozen_baseline_does_not_change`: Proves baseline remains unchanged when subsequent data is mutated.
- `test_repeated_and_new_commit_classification`: Distinguishes `REPEATED_SAME_COMMIT` from `NEW_COMMIT`.
- `test_original_files_preserved`: Verifies SHA256 hashes of original AegisAI baseline artifacts (`manifest.json`).
- `test_synthetic_disclosure_not_skill_confidence`: Verifies mandatory synthetic disclosure text.
- `test_evidence_context_and_traceability`: Confirms evidence items have session ID, candidate ID, and verified line spans.
- `test_duplicate_evidence_no_score_inflation`: Proves repeating evidence does not inflate numerical scores.
- `test_missing_citation_invalidates_score`: Verifies invented citations invalidate score eligibility.
- `test_unavailable_tests_not_failure`: Confirms `NOT_PERFORMED` tests do not fail candidate skills.
- `test_viva_source_ranges`: Validates viva questions link to real symbols and line ranges.
- `test_bad_viva_citation_rejected`: Rejects questions citing non-existent evidence.
- `test_human_approval_and_signed_execution_limit`: Enforces token protection and terminal rejection.
- `test_llm_timeout_is_bounded`: Proves model calls timeout within 10s and retry at most once.
- `test_cycles_include_real_outputs_and_limit`: Confirms agent cycles record real tool outputs up to `MAX_CYCLES`.
- `test_repository_failure_recorded`: Verifies repository acquisition errors are logged without model calls.
- `test_model_missing_preserves_collected_repository`: Proves missing LLM keys preserve collected baseline and repository snapshots.
- `test_resume_preserves_baseline`: Verifies session recovery restores state without corrupting baseline.
- `test_nine_report_sections`: Confirms generation of all 9 required report sections with disclosures.

### 2.3. LangGraph & RAG Tests (7 Tests)
Located in `skillproof/backend/tests/test_langgraph_rag.py`:
- `test_rag_ast_chunking`: AST-aware Python chunking into functions/classes with exact line numbers.
- `test_rag_text_chunking`: Sliding-window chunking for non-Python repository files.
- `test_rag_vector_store_cross_session_isolation`: Verifies vector store isolates chunks by `(session_id, commit_sha)`.
- `test_rag_skill_retrieval_and_traceability`: Validates semantic search, cosine similarity ranking, and evidence transformation.
- `test_langgraph_compilation`: Validates LangGraph state machine structure, nodes, and entry points.
- `test_langgraph_routing_decisions`: Tests `route_investigation` conditional branching logic.
- `test_langgraph_sqlite_checkpointing`: Verifies `SqliteSaver` checkpointer state persistence and thread recovery.

---

## 3. Synthetic Evaluation Harness

Located in `skillproof/backend/evaluation/run_evaluation.py`:
- **Results**: 22 / 22 cases passed (100% pass rate).
- **Fixtures**: Evaluates 6 standardized code fixtures with known implementation patterns.
- **Mandatory Reporting Disclosure**:
  > *"All 22 synthetic evaluation cases passed. Classification metrics are calculated from six small fixtures and are intended for internal regression testing, not as estimates of real-world accuracy."*

---

## 4. Running the Tests

From the backend root directory (`c:\Users\dumpa\python\ziro\skillproof\backend`):

### Run All Pytest Tests
```bash
python -m pytest -v
```

### Run Specific Test Suites
```bash
# Core Unit Tests
python -m pytest tests/test_agents.py tests/test_api.py tests/test_security.py -v

# Reliability Regressions
python -m pytest tests/test_reliability.py -v

# LangGraph and RAG Tests
python -m pytest tests/test_langgraph_rag.py -v
```

### Run Synthetic Evaluation Harness
```bash
python evaluation/run_evaluation.py
```
