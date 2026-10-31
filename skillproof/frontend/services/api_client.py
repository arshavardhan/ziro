import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

logger = logging.getLogger(__name__)


class APIClient:
    """Robust API Client for interacting with the SkillProof AI FastAPI backend on Laptop 1."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _safe_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Tuple[bool, Any, str]:
        """Execute HTTP request with uniform error handling and status extraction."""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code in (200, 201, 202):
                try:
                    return True, resp.json(), ""
                except ValueError:
                    return (
                        True,
                        {"raw_content": resp.text},
                        "",
                    )

            # Handle explicit HTTP error codes
            err_msg = f"HTTP {resp.status_code}: {resp.text}"
            if resp.status_code == 400:
                err_msg = f"Bad Request (400): {resp.text}"
            elif resp.status_code in (401, 403):
                err_msg = f"Authorization Required ({resp.status_code}): Access denied."
            elif resp.status_code == 404:
                err_msg = f"Resource Not Found (404) at {endpoint}"
            elif resp.status_code == 422:
                err_msg = f"Unprocessable Entity (422) - Schema validation failure: {resp.text}"
            elif resp.status_code >= 500:
                err_msg = f"Backend Server Error ({resp.status_code}): {resp.text}"

            return False, {}, err_msg

        except (ConnectionError, Timeout) as e:
            return (
                False,
                {},
                f"Cannot connect to backend at {self.base_url}. Ensure Laptop 1 is running and reachable.",
            )
        except RequestException as e:
            return False, {}, f"Network request error: {str(e)}"
        except Exception as e:
            return False, {}, f"Unexpected client error: {str(e)}"

    def check_health(self) -> Tuple[bool, str]:
        """Check GET /health."""
        ok, data, err = self._safe_request("GET", "/health")
        if ok:
            status = data.get("status", "healthy") if isinstance(data, dict) else "ok"
            return True, f"Online ({status})"
        return False, err

    def start_analysis(
        self,
        candidate_id: str,
        repo_url: str,
        claimed_skills: List[str],
        description: str = "",
        resume_text: Optional[str] = None,
        resume_filename: Optional[str] = None,
        resume_skills: Optional[List[str]] = None,
        commit_sha: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/analyze."""
        payload = {
            "candidate_id": candidate_id,
            "github_url": repo_url,
            "repo_url": repo_url,
            "claimed_skills": claimed_skills,
            "description": description,
        }
        if resume_text:
            payload["resume_text"] = resume_text
        if resume_filename:
            payload["resume_filename"] = resume_filename
        if resume_skills:
            payload["resume_skills"] = resume_skills
        if commit_sha:
            payload["commit_sha"] = commit_sha
        return self._safe_request("POST", "/api/analyze", json=payload)

    def parse_resume(
        self,
        resume_text: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/resume/parse with either file multipart or JSON text."""
        if file_bytes and filename:
            files = {"file": (filename, file_bytes, "application/octet-stream")}
            return self._safe_request("POST", "/api/resume/parse", files=files)
        return self._safe_request(
            "POST",
            "/api/resume/parse",
            json={"resume_text": resume_text or "", "filename": filename or "resume.txt"},
        )

    def attach_resume(
        self,
        session_id: str,
        resume_text: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/session/{session_id}/resume."""
        if file_bytes and filename:
            files = {"file": (filename, file_bytes, "application/octet-stream")}
            return self._safe_request("POST", f"/api/session/{session_id}/resume", files=files)
        return self._safe_request(
            "POST",
            f"/api/session/{session_id}/resume",
            json={"resume_text": resume_text or "", "filename": filename or "resume.txt"},
        )

    def get_session(self, session_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """Call GET /api/session/{session_id}."""
        return self._safe_request("GET", f"/api/session/{session_id}")

    def get_timeline(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Call GET /api/session/{session_id}/timeline."""
        ok, data, err = self._safe_request(
            "GET", f"/api/session/{session_id}/timeline"
        )
        if ok and isinstance(data, dict) and "timeline" in data:
            return True, data["timeline"], ""
        return ok, data if isinstance(data, list) else [], err

    def get_evidence(self, session_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """Call GET /api/session/{session_id}/evidence."""
        return self._safe_request("GET", f"/api/session/{session_id}/evidence")

    def get_report(self, session_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """Call GET /api/session/{session_id}/report."""
        return self._safe_request("GET", f"/api/session/{session_id}/report")

    def get_viva_questions(
        self, session_id: str
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Call GET /api/viva/{session_id}/questions."""
        ok, data, err = self._safe_request(
            "GET", f"/api/viva/{session_id}/questions"
        )
        if ok and isinstance(data, dict) and "questions" in data:
            return True, data["questions"], ""
        return ok, data if isinstance(data, list) else [], err

    def submit_viva_answer(
        self, session_id: str, question_id: str, answer: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/viva/{session_id}/answer."""
        payload = {"question_id": question_id, "answer": answer}
        return self._safe_request(
            "POST", f"/api/viva/{session_id}/answer", json=payload
        )

    def submit_approval(
        self,
        session_id: str,
        decision: str,
        reviewer_notes: str,
        reviewer_id: str = "auditor_lead_01",
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/approve/{session_id}."""
        payload = {
            "decision": decision,
            "reviewer_notes": reviewer_notes,
            "reviewer_id": reviewer_id,
        }
        return self._safe_request(
            "POST", f"/api/approve/{session_id}", json=payload
        )

    def issue_credential(
        self, session_id: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/credential/{session_id}/issue."""
        return self._safe_request("POST", f"/api/credential/{session_id}/issue")

    def get_credential(
        self, credential_id: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call GET /api/credential/{credential_id}."""
        return self._safe_request("GET", f"/api/credential/{credential_id}")

    def verify_credential(
        self, credential_id: str, credential_payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Call POST /api/credential/verify or fallback to GET /api/credential/{id}/verify."""
        # Try POST verification first as specified in contract
        post_payload = {"credential_id": credential_id}
        if credential_payload:
            post_payload.update(credential_payload)

        ok, data, err = self._safe_request(
            "POST", "/api/credential/verify", json=post_payload
        )
        if ok:
            is_valid = data.get("status") == "VALID" or data.get("valid", False) is True
            return is_valid, data, ""

        # Fallback to GET /api/credential/{id}/verify if POST not matched
        ok_get, data_get, err_get = self._safe_request(
            "GET", f"/api/credential/{credential_id}/verify"
        )
        if ok_get:
            is_valid = (
                data_get.get("status") == "VALID"
                or data_get.get("valid", False) is True
            )
            return is_valid, data_get, ""

        return False, {}, err
