# Laptop 2 handoff

Contract version **2.0**. Breaking changes from the original MVP: uppercase states, HTTP 202 for analysis submission, five base viva questions and bounded follow-ups, typed error envelopes, additional timeline/evidence/report endpoints, new score weights, and commit-pinned credentials. Use `CONTRACT.md` and generated `openapi.json`/`schemas.json`.

Running API: http://127.0.0.1:8001/docs (use the backend laptop's LAN IP from Laptop 2). Port 8000 belongs to an existing Teklozy service and was left untouched. Configure the frontend origin in `backend/.env` and restart before cross-origin use.

Saved real-source baseline session:

`25b09616-1cea-4b7d-8f9f-a53359c8f800`

Example live read:

`GET /api/session/25b09616-1cea-4b7d-8f9f-a53359c8f800/report`

This baseline returns **FAILED** for verification completion because live LLM reasoning, candidate answers and human review are pending. It nevertheless contains actual evidence at commit `79112160653cc38cdcbddaf578e29ecfbd58a70a`: 52 files, 383 findings, 33 commits, 121 statically discovered test definitions. Display `NOT PERFORMED` for test execution and null pass/fail counts. Do not render this as a verified candidate.

Configuration still required: provider URL/model/key, reviewer token, signing secret. No secrets are included in handoff artifacts. Draft viva questions in `artifacts/aegis-draft-viva.json` are human-authored source-grounded preparation material, not live model output. A new real session should use `artifacts/aegis-request.json` after configuration.

Verification performed:

- 49 backend tests passed, including API integration, recovery, guardrails, five-question viva/follow-ups, approval gates, credential round-trip/tampering and real-source entropy tracing.
- 22 synthetic evaluation cases passed. Classification accuracy/precision/recall/F1 are 1.0 over six small fixtures; these are not real-world accuracy claims.
- Real Uvicorn startup, health, OpenAPI, and saved report HTTP retrieval passed.
- All 52 exported AegisAI source files match their pinned Git blobs. No AegisAI code was modified or executed on the host.
- Docker is unavailable, so isolated candidate test execution has not been validated here.
- Live provider calls and real candidate viva have not occurred. The synthetic HTTP adapter test demonstrates multiple API requests with a mock transport only.

Run instructions are in `backend/README.md`. No frontend files were created or modified. No message was sent to another laptop; this is the reviewable handoff package.
