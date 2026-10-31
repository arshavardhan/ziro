# SkillProof AI — Security Architecture & Threat Model

## 1. Threat Modeling Overview

SkillProof AI processes untrusted candidate GitHub repositories and evaluates candidate technical claims. Security controls are established to protect backend infrastructure, prevent unauthorized code execution, and guarantee credential integrity.

```
+-----------------------------------------------------------------------------------------+
|                                    THREAT SURFACE                                       |
|                                                                                         |
|  1. Untrusted Code Execution  --> [Docker Sandbox Check]  --> Host Execution FORBIDDEN  |
|  2. SSRF & Malicious Repos    --> [URL Guard & Whitelist] --> GitHub Public HTTPS Only  |
|  3. Path Traversal & Secrets  --> [Path Guard & Redaction]--> Workspace Isolation       |
|  4. LLM Prompt Injection      --> [Whitelisted Tool Schemas]-> Strict Tool Boundary     |
|  5. Credential Forgery        --> [HMAC-SHA256 Signing]   --> Canonical Tamper-Proof    |
|  6. Autonomous Misjudgment    --> [Human Reviewer Gate]   --> Token-Protected Approval  |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Sandbox Execution & Docker-Unavailable Policy

### 2.1. Host Execution Forbidden
Candidate test files and repository scripts contain untrusted, arbitrary code. **SkillProof strictly prohibits executing candidate code directly on the host machine.**

### 2.2. Capability Probing
Before executing tests, `tools/pytest_tool.py` performs a two-tier capability check:
1. Verifies `shutil.which("docker")` is present on the system path.
2. Executes `docker info` to verify the Docker daemon is responsive.

### 2.3. The `NOT_PERFORMED` Guarantee
If Docker is unavailable or cannot establish an isolated container environment:
- `test_execution['status']` is set strictly to `NOT_PERFORMED`.
- `test_execution['reason']` is recorded as `'Docker unavailable'`.
- `tests_executed` and `tests_passed` are set to `0`.
- `test_score` in skill assessment is set to `None`.
- **Candidate Non-Penalization**: The candidate is not failed due to host infrastructure limitations. Skill scores are computed based on evidence coverage and code quality, while test limitations are explicitly disclosed.

---

## 3. SSRF & Repository Acquisition Security (`backend/tools/security_tool.py`)

All submitted GitHub URLs are validated against strict criteria:
- **Protocol**: Only `https://` is permitted (plain `http://`, `ssh://`, `file://` are rejected).
- **Hostname**: Strictly `github.com`.
- **Path Structure**: Must match `/owner/repo` pattern without URL path traversal (`..`), query parameters (`?x=1`), or fragment identifiers.
- **Credential Stripping**: Embedded credentials (`https://user:password@github.com/...`) are strictly blocked.
- **Network Boundaries**: IP addresses, private subnets (e.g. `10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.1`, `localhost`), and internal metadata services (e.g. `169.254.169.254`) are rejected before any network socket is opened.

---

## 4. Path Traversal & Workspace Isolation

- **Jail Directory**: Repositories are cloned into dedicated, unique workspace directories (`workspaces/{session_id}-{uuid}`).
- **Path Sanitization**: Every file path accessed during analysis is checked against `Path.resolve()`. Any path resolving outside the assigned workspace is rejected with an `ACCESS_DENIED` error.
- **Sensitive File Exclusion**:
  - Excluded from analysis: `.env`, `.env.*`, `*.pem`, `*.key`, `id_rsa`, `secrets.txt`, `.git/config`.
  - Content redactor scans for API tokens, secret keys, and passwords, replacing them with `[REDACTED_SECRET]` before storage or LLM ingestion.

---

## 5. LLM Prompt Injection & Tool Whitelisting

- **No Shell Execution**: The agent cannot execute bash, PowerShell, or cmd commands.
- **Strict Tool Whitelist**: The LLM planner may only select from explicitly registered tools:
  - `inspect_files`: Reads designated files within the verified inventory.
  - `find_tests`: Searches for test definitions matching source symbols.
  - `check_dependencies`: Inspects package manager files.
  - `read_symbol`: Fetches AST definitions.
- **Invalid Action Quota**: An invalid tool name or out-of-inventory file path causes immediate action rejection. Two consecutive invalid tool proposals trigger an `INVALID_TOOL_SELECTION` abort.

---

## 6. Cryptographic Credential Integrity (`backend/security/signing.py`)

- **HMAC-SHA256**: Issued credentials contain a cryptographic signature computed over the canonicalized JSON payload using the server's secret `SIGNING_SECRET`.
- **Canonical Payload Normalization**:
  - Nested dictionary keys sorted alphabetically.
  - Timestamps normalized to UTC ISO-8601 strings.
  - Spaces stripped from JSON separators (`separators=(',', ':')`).
- **Tampering Resistance**: Any client-side or third-party modification (e.g. elevating a score, appending a skill, or flipping `NOT_PERFORMED` to `PASSED`) causes immediate verification failure (`valid: false`).

---

## 7. Human Reviewer Governance

- **Token Authentication**: Reviewer actions (`/api/approve/{session_id}`) require the `X-Reviewer-Token` HTTP header matching `REVIEWER_TOKEN`.
- **Viva Gate**: Approval cannot be submitted until all 5 viva questions have been answered.
- **Terminal Rejection**: If a reviewer rejects an assessment (`approved: false`), the session permanently transitions to `REJECTED`, blocking credential issuance.
