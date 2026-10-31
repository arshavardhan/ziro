# 🛡️ SkillProof AI — Enterprise Frontend Architecture

> **Hackathon MVP**: Autonomous agentic skill-proof verification platform for the **Agentic AI Hackathon 2026 Grand Finale (Problem 08)**.

---

## 🌟 Primary Demonstration Target

- **Candidate ID:** `CAND-001`
- **Candidate Repository:** `https://github.com/arshavardhan/AegisAi`
- **Claimed Skills:**
  1. Python
  2. OOP
  3. Machine Learning
  4. Software Architecture
  5. Testing
  6. Git/GitHub
  7. API Development

---

## 🏗️ Directory Architecture

```
skillproof/
  frontend/
    app.py                      # Main Streamlit router with 12 enterprise pages
    config.py                   # Design tokens, AegisAI candidate presets, module list
    requirements.txt            # Streamlit, Requests, Pandas, Plotly, Pytest
    .env.example                # Environment variables template

    services/
      api_client.py             # HTTP client matching Laptop 1's CONTRACT.md
      session_manager.py        # Unified state store, AegisAI fixtures, HMAC signing

    components/
      sidebar.py                # Consistent sidebar with 12 pages & connection status
      dashboard.py              # Platform KPI metrics, charts, recent audit logs
      candidate_form.py         # Submission form with live backend polling
      agent_timeline.py         # Plan -> Act -> Observe -> Critique -> Re-plan -> Act Again -> Verify
      repository_explorer.py    # AegisAI module tree (core, uncertainty, ood, drift, etc.)
      code_inspector.py         # AST signatures, cyclomatic complexity, linked tests
      evidence_graph.py         # Skill evidence cards with classification filtering
      test_results.py           # Sandboxed pytest execution view (18/18 passed)
      git_analysis.py           # Git forensics Plotly charts, commit size, author provenance
      originality_analysis.py   # Similarity indicators with responsible ethical language
      skill_assessment.py       # Radar charts, coverage bars, and dual-axis scores
      viva_interface.py         # Code-specific viva Q&A with 5-metric AI rubric
      reviewer_console.py       # Mandatory human auditor gate (APPROVE / REJECT)
      credential_viewer.py      # HMAC-SHA256 digital certificate, employer verify & tamper test
      evaluation_dashboard.py   # 16-case benchmark metrics, confusion matrix, case ledger

    pages/
      overview.py
      verification.py
      agent_workspace.py
      repository_intelligence.py
      evidence_explorer.py
      git_forensics.py
      originality.py
      skill_assessment.py
      technical_viva.py
      reviewer_approval.py
      credentials.py
      evaluation_lab.py

    evaluation/
      test_cases.json           # 16 deterministic synthetic benchmark cases
      run_evaluation.py         # Automated benchmark execution harness (CLI & UI)
      metrics.py                # Precision, recall, F1, confusion matrix engine
      test_evaluation.py        # Pytest test file for evaluation metrics

    tests/
      test_api_client.py        # API client error handling & connection test
      test_session_state.py     # State store & cryptographic HMAC test
      test_evaluation_ui.py     # 16-case benchmark test suite

    assets/
      styles.css                # Enterprise dark navy theme design system
```

---

## 💻 Two-Laptop Setup & Network Instructions

SkillProof AI is designed for distributed two-laptop hackathon architecture:
- **Laptop 1 (Backend):** Runs FastAPI on `http://LAPTOP1_IP:8000` with:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
- **Laptop 2 (Frontend):** Runs Streamlit.

### Configuring the Backend URL on Laptop 2:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set the IP address of Laptop 1:
   ```env
   SKILLPROOF_BACKEND_URL=http://192.168.1.100:8000
   ```
3. Alternatively, adjust the **Backend IP / Port** in the Streamlit sidebar under **⚙️ Two-Laptop Integration**.

---

## 🚀 Running the Application

### Step 1: Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r skillproof\frontend\requirements.txt
```

### Step 3: Start Streamlit
From the root workspace directory or from `skillproof/frontend/`:
```powershell
streamlit run app.py
```
App opens in browser at: `http://localhost:8501`

---

## 🧪 Automated Testing

Run the full pytest test suite:
```powershell
pytest skillproof\frontend\tests -v
```
Run the 16-case evaluation benchmark via CLI:
```powershell
python skillproof\frontend\evaluation\run_evaluation.py
```
