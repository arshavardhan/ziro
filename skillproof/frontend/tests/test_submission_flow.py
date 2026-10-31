"""Unit tests for GitHub repository URL validation, dynamic candidate management, and preparation workflow."""
import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure skillproof/frontend is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.validators import validate_github_url, validate_candidate_id
from services.session_manager import SessionManager, get_empty_session, get_default_aegis_session
from services.api_client import APIClient


class TestGitHubUrlValidation:
    """Validate GitHub repository URL rules."""

    def test_valid_urls(self):
        valid_urls = [
            "https://github.com/torvalds/linux",
            "https://github.com/psf/requests/",
            "https://github.com/facebook/react.git",
            "https://github.com/huggingface/transformers",
            "https://github.com/scikit-learn/scikit-learn",
            "https://www.github.com/pallets/flask",
            "https://github.com/org123/project_alpha-1",
        ]
        for url in valid_urls:
            is_valid, err = validate_github_url(url)
            assert is_valid is True, f"Expected '{url}' to be valid, got error: {err}"
            assert err == ""

    def test_reject_http_and_insecure_schemes(self):
        insecure = [
            "http://github.com/scikit-learn/scikit-learn",
            "http://github.com/torvalds/linux",
            "ftp://github.com/user/repo",
        ]
        for url in insecure:
            is_valid, err = validate_github_url(url)
            assert is_valid is False
            assert "https" in err.lower() or "scheme" in err.lower() or "insecure" in err.lower()

    def test_empty_or_whitespace_urls(self):
        invalid_urls = ["", "   ", "\t\n"]
        for url in invalid_urls:
            is_valid, err = validate_github_url(url)
            assert is_valid is False
            assert "cannot be empty" in err.lower() or "required" in err.lower()

    def test_non_github_and_deceptive_urls(self):
        non_gh = [
            "https://gitlab.com/arshavardhan/AegisAi",
            "https://bitbucket.org/arshavardhan/AegisAi",
            "https://google.com",
            "not_a_url",
            "https://github.com.example.com/user/repo",
            "https://example.com/github.com/user/repo",
        ]
        for url in non_gh:
            is_valid, err = validate_github_url(url)
            assert is_valid is False
            assert (
                "unsupported url domain" in err.lower()
                or "invalid url format" in err.lower()
                or "github.com" in err.lower()
                or "deceptive" in err.lower()
                or "scheme" in err.lower()
            )

    def test_missing_username_or_repository_name(self):
        cases = [
            ("https://github.com", "missing repository username"),
            ("https://github.com/", "missing repository username"),
            ("https://github.com/onlyuser", "missing repository name"),
            ("https://github.com/onlyuser/", "missing repository name"),
            ("https://github.com/user/repo/extra/path", "invalid github repository url"),
        ]
        for url, expected_sub in cases:
            is_valid, err = validate_github_url(url)
            assert is_valid is False, f"Expected '{url}' to fail"
            assert expected_sub in err.lower(), f"Expected '{expected_sub}' in '{err}'"

    def test_reserved_github_keywords(self):
        reserved_urls = [
            "https://github.com/login/repo",
            "https://github.com/settings/repo",
            "https://github.com/explore/repo",
            "https://github.com/trending/repo",
        ]
        for url in reserved_urls:
            is_valid, err = validate_github_url(url)
            assert is_valid is False
            assert "reserved" in err.lower()


class TestCandidateIdValidation:
    """Validate Candidate ID requirements."""

    def test_valid_candidate_ids(self):
        valid_ids = ["CAND-001", "CAND-1024", "DEV-99", "AliceDev", "bob_ross"]
        for cid in valid_ids:
            is_valid, err = validate_candidate_id(cid)
            assert is_valid is True
            assert err == ""

    def test_empty_candidate_id(self):
        for cid in ["", "   ", None]:
            is_valid, err = validate_candidate_id(cid or "")
            assert is_valid is False
            assert "cannot be empty" in err.lower() or "required" in err.lower()


class TestDynamicCandidateManagement:
    """Validate dynamic candidate preparation and session state switching."""

    def test_empty_initial_session(self):
        empty_sess = get_empty_session()
        assert empty_sess["candidate_id"] == ""
        assert empty_sess["repo_url"] == ""
        assert empty_sess["claimed_skills"] == []
        assert empty_sess["status"] == "NOT_STARTED"
        assert empty_sess["timeline"] == []

    def test_prepare_and_switch_candidates_without_reusing_old_repo(self):
        # 1. Prepare first candidate
        cand1_data = {
            "session_id": "prep_CAND-101",
            "candidate_id": "CAND-101",
            "repo_url": "https://github.com/alice/project-alpha",
            "claimed_skills": ["Python", "FastAPI"],
            "description": "Alice Alpha Project",
            "status": "PREPARED",
            "timeline": [],
        }
        SessionManager.set_session(cand1_data)
        sess1 = SessionManager.get_session()
        assert sess1["candidate_id"] == "CAND-101"
        assert sess1["repo_url"] == "https://github.com/alice/project-alpha"

        # 2. Prepare second candidate - ensure complete overwrite with no leftover from cand 1
        cand2_data = {
            "session_id": "prep_CAND-202",
            "candidate_id": "CAND-202",
            "repo_url": "https://github.com/bob/deep-learning-suite",
            "claimed_skills": ["PyTorch", "CUDA"],
            "description": "Bob DL Suite",
            "status": "PREPARED",
            "timeline": [],
        }
        SessionManager.set_session(cand2_data)
        sess2 = SessionManager.get_session()
        assert sess2["candidate_id"] == "CAND-202"
        assert sess2["repo_url"] == "https://github.com/bob/deep-learning-suite"
        assert "alice" not in sess2["repo_url"]
        assert sess2["claimed_skills"] == ["PyTorch", "CUDA"]

        # 3. Clear session
        SessionManager.clear_session()
        cleared = SessionManager.get_session()
        assert cleared["candidate_id"] == ""
        assert cleared["repo_url"] == ""


class TestSubmissionWorkflow:
    """Test start_analysis integration with APIClient."""

    def test_successful_submission_returns_session_id(self):
        client = APIClient(base_url="http://127.0.0.1:8000")
        mock_resp = {
            "session_id": "sess_cand001_abc123",
            "status": "running",
            "candidate_id": "CAND-001",
            "repo_url": "https://github.com/user/custom-repo",
        }

        with patch.object(client, "_safe_request", return_value=(True, mock_resp, "")):
            ok, resp, err = client.start_analysis(
                candidate_id="CAND-001",
                repo_url="https://github.com/user/custom-repo",
                claimed_skills=["Python", "Machine Learning"],
                description="Test submission",
            )
            assert ok is True
            assert err == ""
            assert resp["session_id"] == "sess_cand001_abc123"
            assert resp["status"] == "running"

    def test_failed_submission_returns_backend_error_without_simulating_success(self):
        client = APIClient(base_url="http://127.0.0.1:8000")
        backend_err = "Cannot connect to backend at http://127.0.0.1:8000. Ensure Laptop 1 is running and reachable."

        with patch.object(client, "_safe_request", return_value=(False, {}, backend_err)):
            ok, resp, err = client.start_analysis(
                candidate_id="CAND-001",
                repo_url="https://github.com/user/custom-repo",
                claimed_skills=["Python"],
            )
            assert ok is False
            assert "Cannot connect" in err
            assert resp == {}
