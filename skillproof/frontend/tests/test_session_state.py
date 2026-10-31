import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.session_manager import (
    get_empty_session,
    compute_signature,
    verify_signature,
)
from services.validators import generate_candidate_id_from_repo


def test_empty_session_integrity():
    """Verify clean initial empty session structure."""
    session = get_empty_session()
    assert session["candidate_id"] == ""
    assert session["repo_url"] == ""
    assert len(session["claimed_skills"]) == 0
    assert session["status"] == "NOT_STARTED"
    assert session["approval_status"] == "pending"


def test_auto_generate_candidate_id():
    """Verify Candidate ID auto-generation from repository URLs."""
    assert generate_candidate_id_from_repo("https://github.com/octocat/Hello-World") == "CAND-OCTOCAT-HELLOWORLD"
    assert generate_candidate_id_from_repo("https://github.com/torvalds/linux.git") == "CAND-TORVALDS-LINUX"
    assert generate_candidate_id_from_repo("https://github.com/arshavardhan/ziro") == "CAND-ARSHAVARDHAN-ZIRO"
    assert generate_candidate_id_from_repo("") == ""


def test_cryptographic_signature_and_tamper_detection():
    """Verify HMAC signature validity and rejection of tampered payloads."""
    payload = {
        "credential_id": "SP-CRED-2026-LIVE-01",
        "candidate_id": "CAND-DEV-01",
        "score": 94,
        "skills": ["Python", "OOP", "Machine Learning"]
    }
    sig = compute_signature(payload)
    assert len(sig) == 64
    assert verify_signature(payload, sig) is True

    # Tampering test
    tampered = payload.copy()
    tampered["score"] = 99
    assert verify_signature(tampered, sig) is False
