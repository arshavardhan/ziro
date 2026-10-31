# SkillProof AI (Ziro) — Autonomous Skill-Proof Verification Agent

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_Agents-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://python.org)

SkillProof AI is an enterprise-grade autonomous skill-verification agent built for the **Agentic AI Hackathon 2026 Grand Finale**. It cross-verifies candidate software engineering claims against actual code evidence from public GitHub repositories using deterministic AST static analysis, repository-grounded RAG retrieval, multi-cycle agent orchestration, source-grounded technical viva, and cryptographic credential signing.

---

## 🌟 Key Features

1. **Section 1: Paste GitHub Repository Link**:
   - Accepts public GitHub repository URLs (`https://github.com/owner/repo`).
   - Pin specific 40-character commit SHAs for reproducible, immutable assessments.
   - Quick "Open Repository on GitHub" source inspection.
2. **Section 2: Candidate Resume Upload & Skill Extraction**:
   - Upload candidate resumes in **PDF, DOCX, TXT, or Markdown** format (or paste raw text).
   - Automatically extracts candidate name, contact info, and technical skills using a comprehensive taxonomy.
   - "Apply Resume Skills" quick-fill button to synchronize claimed skills.
   - **Resume Claims vs. Repository Reality**: Cross-verifies resume claims against code evidence found in the repo snapshot, categorizing skills as `DEMONSTRATED_IN_REPO` vs `UNVERIFIED_IN_REPO` with an Alignment Score.
3. **LangGraph Agent Orchestration**:
   - Stateful directed graph (`skillproof/backend/agents/graph.py`) with dynamic investigation cycles.
   - Dynamic tool selection (`inspect_files`, `find_tests`, `read_symbol`) based on evidence gaps.
   - Persistent checkpointing with `SqliteSaver` for crash recovery.
4. **Repository-Grounded RAG Subsystem**:
   - AST-aware Python code chunking into classes and functions with 1-indexed line spans.
   - Google Gemini `gemini-embedding-001` with deterministic offline fallback embedder.
   - Scoped SQLite vector store isolated per `(session_id, commit_sha)`.
5. **Technical Viva & Reviewer Governance**:
   - 5 source-grounded questions targeting verified AST line ranges with dynamic follow-ups.
   - Token-protected Human Reviewer Gate (`X-Reviewer-Token`); rejection is terminal.
6. **Cryptographic HMAC-SHA256 Signing**:
   - Canonical JSON normalization with tamper detection.

---

## 🚀 Deploying to Streamlit Community Cloud

1. Fork or push this repository to GitHub: [`arshavardhan/ziro`](https://github.com/arshavardhan/ziro).
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in.
3. Click **New App** and select:
   - **Repository**: `arshavardhan/ziro`
   - **Branch**: `main`
   - **Main file path**: `app.py` (or `streamlit_app.py`)
4. Under **Advanced Settings**, add Secrets (optional for live Gemini reasoning):
   ```toml
   GEMINI_API_KEY = "your-google-gemini-api-key"
   LLM_MODEL = "gemini-3.5-flash-lite"
   EMBEDDING_MODEL = "gemini-embedding-001"
   SIGNING_SECRET = "your-secret-hmac-key"
   ```
5. Click **Deploy!** The app will boot the frontend and embedded verification engine automatically.

---

## 💻 Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Streamlit Application
```bash
streamlit run app.py
```
Or start the FastAPI backend separately:
```bash
cd skillproof/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🧪 Testing & Verification

Run the full automated test suite (77 tests):
```bash
cd skillproof/backend
python -m pytest -v
```

Run the synthetic evaluation regression harness (22 cases):
```bash
cd skillproof/backend
python evaluation/run_evaluation.py
```

> **Mandatory Disclosure**: All 22 synthetic evaluation cases passed. Classification metrics are calculated from six small fixtures and are intended for internal regression testing, not as estimates of real-world accuracy.
