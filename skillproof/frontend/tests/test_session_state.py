import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.session_manager import (
    get_default_aegis_session,
    compute_signature,
    verify_signature,
)


def test_aegis_session_integrity():
    """Verify primary candidate AegisAI session fixture data."""
    session = get_default_aegis_session()
    assert session["candidate_id"] == "CAND-001"
    assert session["repo_url"] == "https://github.com/arshavardhan/AegisAi"
    assert len(session["claimed_skills"]) == 7
    assert "aegis/core/base.py" in session["code_files"]
    assert "aegis/uncertainty/monte_carlo.py" in session["code_files"]
    assert len(session["timeline"]) >= 7
    assert len(session["git_commits"]) >= 5
    assert len(session["viva_questions"]) == 3


def test_cryptographic_signature_and_tamper_detection():
    """Verify HMAC signature validity and rejection of tampered payloads."""
    payload = {
        "credential_id": "SP-CRED-2026-AEGIS-01",
        "candidate_id": "CAND-001",
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
