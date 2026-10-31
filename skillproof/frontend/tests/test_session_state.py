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


def test_autonomous_verification_33_commits_and_viva():
    """Verify autonomous verification pipeline pulls 33 commits and generates code-grounded viva."""
    from services.autonomous_agent import execute_autonomous_verification, evaluate_viva_answer

    session = execute_autonomous_verification(
        candidate_id="CAND-ARSHAVARDHAN-AEGISAI",
        repo_url="https://github.com/arshavardhan/AegisAi",
        claimed_skills=["Python", "Machine Learning"],
    )

    # 1. 33 Git Commits
    assert len(session["git_commits"]) == 33
    assert session["git_commits"][0]["commit_hash"] == "7911216"

    # 2. Viva inquiries grounded in code
    assert len(session["viva_questions"]) >= 4
    q1 = session["viva_questions"][0]
    assert "entropy" in q1["question"].lower() or "architecture" in q1["question"].lower()

    # 3. Dynamic Viva Response Grading
    ans = "In entropy.py, we divide Shannon entropy by log2(K) to normalize uncertainty between 0 and 1. Zero probabilities are handled with an epsilon clamp."
    eval_res = evaluate_viva_answer(q1, ans)
    assert eval_res["overall_score"] >= 75
    assert eval_res["technical_correctness"] >= 75
    assert len(eval_res["feedback"]) > 20

    # 4. Skill Matrix
    assert "Python" in session["skill_assessment"]["skills"]
    assert session["skill_assessment"]["overall_score"] >= 80

    # 5. Auditor approval remains pending
    assert session["approval_status"] == "pending"
