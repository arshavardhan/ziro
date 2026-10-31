# SkillProof API Contract v2.0 — Frontend Handoff

**Notice for Frontend Integration:** Replaces v1 lowercase states and three-question viva. All endpoints are implemented under `skillproof/backend`. Frontend files are intentionally untouched. This document, `openapi.json`, and `schemas.json` serve as the canonical integration artifacts.

- **Base URL**: `http://<backend-host>:8001` (or `http://localhost:8001`).
- **Protocols**: REST over HTTP, JSON payloads.
- **Headers**:
  - `Content-Type: application/json`
  - `X-Reviewer-Token`: Required for reviewer endpoints (`/api/approve/{id}`).
- **Timestamps**: UTC ISO-8601 strings.
- **IDs**: Opaque unique identifiers (`session_id`, `credential_id`, `evidence_id`, `question_id`).

---

## 1. Endpoints

| Method | Path | Status | Request Body | Response Body | Description |
|---|---|---|---|---|---|
| `POST` | `/api/analyze` | 202 | `AnalyzeRequest` | `AnalyzeResponse` | Submit repository for analysis |
| `GET` | `/api/session/{session_id}` | 200 | None | `SessionResponse` | Poll analysis state, scores, RAG info |
| `GET` | `/api/session/{session_id}/timeline` | 200 | None | `TimelineResponse` | Streamed timeline events |
| `GET` | `/api/session/{session_id}/evidence` | 200 | None | `EvidenceResponse` | Traceable source & RAG evidence graph |
| `GET` | `/api/session/{session_id}/report` | 200 | None | `ReportResponse` | Full 9-section verification report |
| `GET` | `/api/viva/{session_id}/questions` | 200 | None | `QuestionsResponse` | Get 5 source-grounded viva questions |
| `POST` | `/api/viva/{session_id}/answer` | 200 | `AnswerRequest` | `AnswerResponse` | Submit viva answer (may return follow-up) |
| `POST` | `/api/approve/{session_id}` | 200 | `ApprovalRequest` | `ApprovalResponse` | Human reviewer sign-off or rejection |
| `POST` | `/api/credential/{session_id}/issue` | 200 | None | `Credential` | Issue signed cryptographic credential |
| `GET` | `/api/credential/{credential_id}` | 200 | None | `Credential` | Retrieve issued credential |
| `POST` | `/api/credential/verify` | 200 | `Credential` | `VerificationResponse` | Verify credential HMAC signature & fields |
| `GET` | `/api/credential/{credential_id}/verify`| 200 | None | `VerificationResponse` | Verify stored credential |
| `GET` | `/health` | 200 | None | `HealthResponse` | Service health status |

---

## 2. Session Lifecycle States

```
QUEUED --> PLANNING --> ANALYSING --> TESTING --> EVALUATING --> VIVA_PENDING --> APPROVAL_PENDING --> APPROVED --> ISSUED
                                                                                      |
                                                                                      +--> REJECTED (Terminal)
[Any tool/config failure] --> FAILED (Terminal)
```

- `REJECTED`: Reviewer rejected the candidate assessment; terminal.
- `FAILED`: Unrecoverable error (e.g. invalid repo URL); terminal.
- On backend restart, in-flight sessions resume automatically from durable SQLite checkpoints at the recorded commit SHA.

---

## 3. RAG Intelligence Response Fields

`SessionResponse` includes repository-grounded RAG intelligence:
- `rag_indexed` (`bool`): `True` once repository text and code chunks are vectorized into SQLite.
- `rag_chunks_count` (`int`): Total count of AST and line-block chunks indexed for this session snapshot.
- `rag_evidence` (`dict`): Retrieved top-k RAG chunks grouped by claimed skill with line ranges and content snippets.

---

## 4. Error Schema

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Session not found",
    "details": []
  }
}
```

- `400`: Bad request / invalid lifecycle transition.
- `403`: Missing or invalid `X-Reviewer-Token`.
- `404`: Resource not found.
- `409`: Conflict (e.g. approving without completing viva, repeated answer).
- `422`: Unprocessable entity / validation error.
- `500`: Sanitized internal error.
- `502`: LLM response error or invalid schema from provider.
- `503`: External service unavailable (e.g. LLM not configured).

---

## 5. Sample Payloads

### Start Analysis (`POST /api/analyze`)
```json
{
  "github_url": "https://github.com/arshavardhan/AegisAi",
  "candidate_id": "CAND-001",
  "claimed_skills": [
    "Python",
    "Object-Oriented Programming",
    "Machine Learning",
    "Software Architecture",
    "Testing"
  ],
  "commit_sha": "79112160653cc38cdcbddaf578e29ecfbd58a70a"
}
```

### Viva Answer Submission (`POST /api/viva/{id}/answer`)
```json
{
  "question_id": "q1",
  "answer": "The function validates input bounds before delegating computation to the transformer layer."
}
```

### Human Reviewer Approval (`POST /api/approve/{id}`)
```json
{
  "approved": true,
  "reviewer": "Senior Engineering Reviewer",
  "reason": "Verified code implementation, inspected AST line ranges, validated candidate viva answers."
}
```

### Credential Verification Response (`POST /api/credential/verify`)
```json
{
  "valid": true,
  "credential_id": "CRED-001-a1b2c3",
  "issued_to": "CAND-001",
  "repository": {
    "url": "https://github.com/arshavardhan/AegisAi",
    "commit_sha": "79112160653cc38cdcbddaf578e29ecfbd58a70a"
  },
  "verified_skills": ["Python", "Software Architecture"],
  "signature": "hmac_sha256_hex_digest"
}
```
