# SkillProof AI — RAG Architecture & Design

## 1. Overview & Objectives

The SkillProof AI RAG (Retrieval-Augmented Generation) subsystem provides repository-grounded semantic intelligence. It allows the agent to locate, cite, and cross-reference code structures relevant to candidate claimed skills with exact file and line traceability.

```
Repository Snapshot Files
          |
          +---> Python Files (.py) ---------> AST-Aware Chunker (Functions, Classes, Methods)
          |
          +---> Non-Python Files -----------> Sliding-Window Line Chunker (60 lines, 15 overlap)
                                                           |
                                                           v
                                              Normalized Chunks with Line Spans
                                                           |
                                                           v
                                              Embeddings Adapter
                                     (Gemini gemini-embedding-001 /
                                      Deterministic Offline Fallback)
                                                           |
                                                           v
                                            SQLite Vector Store (rag_chunks)
                                            Scoped to (session_id, commit_sha)
                                                           |
                                                           v
                                              Skill-Targeted Retriever
                                         (Cosine Similarity + Thresholding)
                                                           |
                                                           v
                                            Verifiable RAG Evidence (RAG-xxx)
```

---

## 2. Chunking Strategy (`backend/rag/chunker.py`)

### 2.1. AST-Aware Python Chunking
Python code is parsed into an Abstract Syntax Tree (`ast.parse`). Chunks are extracted at logical code boundaries:
- **Classes**: Class definition, docstring, and base classes.
- **Methods**: Member methods of classes, capturing both class context and method body.
- **Functions**: Top-level synchronous and asynchronous functions (`FunctionDef`, `AsyncFunctionDef`).
- **Exact Line Ranges**: Every chunk stores 1-indexed `start_line` and `end_line` derived directly from AST node positions (`lineno` to `end_lineno`).
- **Docstrings**: Docstrings are extracted via `ast.get_docstring(node)` and stored distinctly.
- **Module Fallback**: Module-level code outside functions or classes is chunked with a fallback parser if syntax parsing fails or for script-style files.

### 2.2. Non-Python File Chunking
Files such as configuration (`pyproject.toml`, `requirements.txt`, Dockerfiles, CI workflows) and documentation (`README.md`, `ROADMAP.md`) are processed using a sliding-window text chunker:
- **Window Size**: 60 lines.
- **Overlap**: 15 lines.
- **Line Preservation**: Maintains 1-indexed line numbers (`start_line`, `end_line`).

---

## 3. Embedding Subsystem (`backend/rag/embeddings.py`)

### 3.1. Gemini Embedding API
- **Model**: `gemini-embedding-001` (configured via `EMBEDDING_MODEL` in `config.py`).
- **Request Format**: REST call to `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent`.
- **Normalization**: Vectors are L2-normalized (`v / ||v||`) upon receipt to enable fast cosine similarity computations via dot products.
- **Retry & Bounded Timeout**: 10-second timeout with single retry on rate-limiting (HTTP 429/503).

### 3.2. Deterministic Offline Fallback Embedder
To guarantee offline test isolation and withstand sandbox network boundaries, a mathematical n-gram vectorizer is embedded:
- **Dimensionality**: Fixed 384 dimensions.
- **Algorithm**:
  - Word tokens hashed into vector indices with logarithmic position weighting.
  - Character 3-grams hashed with SHA-256 into vector buckets.
  - Final L2-normalization.
- **Properties**: Deterministic, zero external dependencies, stable cosine similarities for semantically related tokens.

---

## 4. Vector Store Architecture (`backend/rag/vector_store.py`)

### 4.1. Storage Engine
Implemented directly in SQLite using a dedicated table:
```sql
CREATE TABLE IF NOT EXISTS rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    symbol TEXT,
    chunk_type TEXT NOT NULL,
    content TEXT NOT NULL,
    docstring TEXT,
    vector TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_session ON rag_chunks(session_id, commit_sha);
```

### 4.2. Multi-Tenant Session Isolation
- Every storage operation and query is strictly filtered by `session_id` and `commit_sha`.
- Chunks from different candidate assessment sessions or different commits of the same repository never bleed across queries.

### 4.3. Cosine Similarity & Threshold Filtering
- Embeddings are deserialized from JSON vectors in SQLite.
- Similarity is computed as the inner product of normalized vectors:
  $$\text{sim}(u, v) = \sum_{i=1}^{d} u_i \cdot v_i$$
- A `min_score` threshold (default 0.35) filters out low-relevance noise.

---

## 5. Skill Retriever (`backend/rag/retriever.py`)

### 5.1. Semantic Query Expansion
Claimed skills are mapped to contextual queries:
- `"Python"` $\rightarrow$ `"Python functions classes syntax and decorators"`
- `"Software Architecture"` $\rightarrow$ `"design patterns abstraction interfaces architecture"`
- `"Testing"` $\rightarrow$ `"pytest unit tests assertions test cases fixtures"`
- `"Machine Learning"` $\rightarrow$ `"model training inference neural networks dataset"`

### 5.2. Evidence Conversion & Traceability
Retrieved chunks are converted into traceable evidence items:
```json
{
  "evidence_id": "RAG-a1b2c3d4",
  "symbol": "total",
  "file": "orders.py",
  "start_line": 15,
  "end_line": 35,
  "chunk_type": "function",
  "docstring": "Compute order total with discount.",
  "observed_facts": ["RAG match for claimed skill 'Python' (similarity: 0.78)"],
  "inference_limitations": ["Retrieved via semantic embedding; requires AST validation"]
}
```
- **Provenance Guarantee**: Stored in `data['rag_evidence']` rather than mutated into `data['code_evidence']` to maintain strict baseline counts of AST-extracted source findings.
