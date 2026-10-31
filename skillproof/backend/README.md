# SkillProof AI — backend v2

One backend implementation; no frontend. See `../CONTRACT.md`, `../openapi.json`, `../schemas.json` and `../examples/` for Laptop 2. Version 2 replaces the previous lowercase statuses and three-question viva.

## Windows setup

```powershell
cd C:\Users\dumpa\python\ziro\skillproof\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32)); print(secrets.token_hex(32))"
```

Put the two independent generated values in `SIGNING_SECRET` and `REVIEWER_TOKEN`. Configure `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` locally. The provider must support OpenAI-compatible `/chat/completions` with JSON-object responses. `.env` is ignored by Git. The key is never returned by an API. No credential is issued when the signing secret is absent. Analysis fails explicitly if the model key is absent; there is no fake model fallback.

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health: http://127.0.0.1:8000/health. Interactive docs: http://127.0.0.1:8000/docs. OpenAPI: http://127.0.0.1:8000/openapi.json.

The instance started in this workspace uses **8001**, because 8000 is already serving another application. Its docs are http://127.0.0.1:8001/docs. To reproduce that instance, use `--port 8001`. Restart the backend after editing `.env`; the current hidden process PID is recorded in `outputs/server.pid`.

Use one worker. `--reload` is optional during development. Background jobs persist checkpoints in SQLite and recover in-flight sessions on startup; pending viva and human decisions remain pending. The worker pool allows two concurrent investigations and a bounded dispatch queue. Source snapshots are pinned to full commit SHA; a changed HEAD prevents resumption. This is a local hackathon backend, not a multi-tenant service. Session reads and candidate answer submission have no identity authentication. Restrict the network to the two trusted laptops. Reviewer-token possession authorizes review; the reviewer name is recorded but not independently identity-verified.

For Laptop 2, set `CORS_ORIGINS` to the actual frontend origin, e.g. `http://192.168.1.20:5173`. The frontend calls `http://<backend-ip>:8000`. The reviewer token belongs only in the human review flow; never send signing or LLM secrets to the frontend. State, error and response definitions are in the contract.

## AegisAI baseline and live run

The separate, unmodified source snapshot is under `workspaces/aegis-fixed`, pinned to:

`79112160653cc38cdcbddaf578e29ecfbd58a70a`

The saved static report is `../artifacts/aegis-static-report.json`, with a short summary and five source-grounded **human-authored draft** questions alongside it. These drafts are not live model output or an evaluated candidate interview. The baseline session is marked `FAILED` for completion purposes, with a clear explanation that model reasoning and candidate viva are pending. Its collected source evidence is still available through session/evidence/report endpoints.

After configuring the provider, submit `../artifacts/aegis-request.json` to `POST /api/analyze`. It pins the same SHA and all seven requested skills. The live sequence is:

1. Initial model planning; clone public GitHub source and record SHA.
2. Inspect planned files, Git progression and within-repository similarity.
3. Model critique and re-plan. Execute allowlisted `inspect_files`, `trace_calls`, or `find_tests`. At most three investigation cycles, with no LLM-selected shell commands.
4. Discover tests and execute only in the restricted Docker environment, or explicitly report `NOT_PERFORMED`.
5. Model assessment with validated evidence IDs, followed by five code-specific questions: two conceptual, two implementation, one debugging.
6. Submit answers. Incomplete base answers create one follow-up each; all must be answered. The five base answers retain their original scores.
7. Reviewer reads `/api/session/{id}/report`, then explicitly approves or rejects with `X-Reviewer-Token`. Rejection is terminal. Approval requires evidence and viva criteria.
8. Issue the signed credential using the same reviewer header. Verify retrieved or submitted JSON. Repeated issuance returns the same credential.

The runtime makes separate model calls for planning, critique, skill assessment, question generation and each answer. Structured JSON is validated, references are checked against observed evidence, transient/invalid responses get at most one retry, and failures are persisted without exposing provider payloads. Successful logical reasoning calls are counted; retry attempts are not additional counted reasoning steps. Source excerpts are sent only to the configured provider. Context is bounded and selected across files; omissions and static limitations are not runtime verification.

## Evidence and scoring

AST findings include functions, classes, methods, signatures, hints, docstrings, exception handlers, complexity and line ranges. Findings distinguish `IMPLEMENTED`, `PARTIALLY_IMPLEMENTED`, `PLANNED`, `UNVERIFIED`, `NOT_DEMONSTRATED` and `TESTED`. A static test import does **not** justify marking a function `TESTED`; the current runner does not establish function coverage.

The graph records file containment, imports, resolved calls, test imports and limited assignment-based value tracing. Constructor and assignment inference can trace AegisAI entropy into `TrustScorer.compute`; dynamic dispatch, branches and aliasing remain incomplete. All graph relations disclose their resolution method. Evidence is source-grounded; AST presence does not establish algorithm correctness or authorship.

Weights: implementation 30%, tests 20%, architecture 15%, Git progression 10%, viva 25%. Scores normalize over available factors, with coverage shown separately. Implementation and architecture come from grounded model assessments. Test score is the repository-wide passed/(passed+failed) ratio applied only to statically linked modules; unavailable execution stays null. Git score is `min(100, commit_count × 20)`, a coarse progression heuristic, **not proof of contribution**. Viva averages five base-answer scores using correctness 30%, code understanding 25%, reasoning 20%, evidence alignment 15%, limitations awareness 10%.

Credential eligibility requires complete pinned analysis, five base answers plus follow-ups, a fully implemented production evidence citation, model confidence ≥0.7, score ≥`MIN_SCORE` (65), coverage ≥55%, viva ≥`MIN_VIVA` (60), and explicit human approval. Only eligible skills are signed. A final `VERIFIED` verdict appears only after human approval. Numerical scores and confidence are not scientifically calibrated probabilities.

Git records author metadata, timestamps, changed files, change sizes, test/doc changes and earliest observed file modification. History is limited to 100 commits; metadata does not prove personal authorship. Similarity compares internal AST bodies and token sequences, capped at 200 substantial functions and 100 findings. Common boilerplate can produce matches. No internet-wide plagiarism or certain AI-generation claims are made.

## Isolated test execution

Docker Desktop with Linux containers is required to execute candidate tests. Build the trusted basic image:

```powershell
docker build -f tools/Dockerfile.tests -t skillproof-tests:local .
```

For AegisAI, a separately reviewed image includes the known numerical libraries without installing the candidate package or its scripts:

```powershell
docker build -f tools/Dockerfile.aegis-tests -t skillproof-tests:local .
```

Containers have no network, a read-only filesystem and repository, non-root user, dropped capabilities, no new privileges, a process cap, 512 MB memory, one CPU, and a 60-second deadline. No host secrets are passed. No untrusted requirements or setup scripts run on the host. Optional wrappers may need packages absent from this image; results report those failures rather than installing them automatically. Docker/image unavailable means `NOT_PERFORMED`, not passed. Docker isolation shares the host kernel and is not a hardened hostile-code service.

Static test count means function definitions, not parametrized runtime cases. Runtime counts are parsed from the final pytest summary and remain null when unavailable. Repository tests are untrusted and can falsify their own output; these results are not external coverage attestation.

## Storage, limits and signing

SQLite lives in `outputs/skillproof.sqlite3` (override `DATA_DIR`). Required tables hold sessions, plans, observations, tool executions, snapshots, files, claims, evidence, test/Git/similarity findings, viva, approval and credentials. Checkpoints and observations are saved transactionally. Schema version 2 leaves old v1 tables as archival SQL data; it does not reinterpret old sessions under the new contract.

Git cloning is public HTTPS GitHub only, no interactive credentials, checkout filters, hooks, symlinks or submodules. Clone history is capped at 150 MB and 120 seconds; expanded source at 50 MB; individual text files at 100 KB; inventory at 500 files. Transfer monitoring is best effort, not an OS disk quota. Common secret filenames and literal values are excluded/redacted; this is not a complete secret scanner. Only submit suitable public repositories. Partial clone attempts are retained separately, not silently reused.

Credentials use canonical sorted compact UTF-8 JSON and HMAC-SHA256, after Pydantic type normalization. Independent `security.signing.verify(payload, secret)` does not need SQLite. HMAC is server/shared-secret verification, not public-key signing. Key rotation invalidates old signatures. There is no credential revocation endpoint. SQLite credential issuance and session state change are atomic; credential JSON export is recoverable by repeating issuance.

## Tests, evaluation and handoff artifacts

```powershell
python -m pytest -q
python evaluation/run_evaluation.py
python scripts/smoke_server.py
python scripts/export_contract.py
python scripts/analyze_aegis.py
```

Tests use synthetic provider responses and local Git repositories, cover the full API, state gates, recovery, five questions and follow-ups, canonical signature round trips, URL/path guards, evidence and scoring. An optional snapshot regression reads real AegisAI source without executing it. The LLM HTTP adapter test makes multiple requests through a mock transport; this does not demonstrate live model quality.

`evaluation/test_cases.json` defines 22 deterministic cases. Results in `../artifacts/evaluation-results.json` label their synthetic nature and metric denominators. Classification metrics use six implementation fixtures; other cases measure regression, tool, guardrail and signing behavior. Actual sandbox test-execution success is null when no sandbox was available. No benchmark claims are made beyond these cases.

The AegisAI snapshot and baseline report have been generated in this workspace. Live provider reasoning, candidate answers and human approval require the real configuration and participants; these are not fabricated by the test suite.
