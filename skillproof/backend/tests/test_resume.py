import pytest
from services.resume_service import parse_resume, match_resume_to_repository, extract_text_from_bytes

def test_resume_text_extraction_and_parsing():
    sample = """
    Alex Rivera
    Senior Software Engineer
    alex.rivera@example.com | (555) 987-6543
    https://github.com/alexrivera/distributed-systems

    Professional Summary:
    Full stack engineer with 6+ years building microservices and web platforms.

    Technical Skills:
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, React, TypeScript, Git, Testing
    """
    parsed = parse_resume(sample, "alex_rivera_resume.txt")
    assert parsed["candidate_name"] == "Alex Rivera"
    assert parsed["email"] == "alex.rivera@example.com"
    assert parsed["phone"] == "(555) 987-6543"
    assert "https://github.com/alexrivera/distributed-systems" in parsed["github_url"]
    assert "Python" in parsed["extracted_skills"]
    assert "FastAPI" in parsed["extracted_skills"]
    assert "Docker" in parsed["extracted_skills"]
    assert "React" in parsed["extracted_skills"]
    assert "Testing" in parsed["extracted_skills"]

def test_resume_matching_to_repository():
    resume_skills = ["Python", "FastAPI", "Docker", "React", "Rust"]
    code_evidence = [
        {"symbol": "create_app", "file": "main.py", "docstring": "FastAPI application factory"},
        {"symbol": "dockerfile_step", "file": "Dockerfile", "docstring": "Container build"},
    ]
    languages = ["Python", "Dockerfile"]

    match = match_resume_to_repository(resume_skills, code_evidence, languages=languages)
    assert match["total_resume_skills"] == 5
    # Python, FastAPI, Docker should be demonstrated
    assert match["demonstrated_count"] >= 3
    # Rust and React should be unverified
    unverified_skills = [u["skill"] for u in match["unverified_skills"]]
    assert "Rust" in unverified_skills
    assert match["alignment_score"] > 0

def test_resume_parse_api_endpoint(client):
    payload = {
        "resume_text": """
        Morgan Vance
        morgan.vance@tech.co
        Skills: Python, Machine Learning, PyTorch, SQL, Git
        """
    }
    r = client.post("/api/resume/parse", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    profile = data["profile"]
    assert profile["candidate_name"] == "Morgan Vance"
    assert profile["email"] == "morgan.vance@tech.co"
    assert "Python" in profile["extracted_skills"]
    assert "Machine Learning" in profile["extracted_skills"]

def test_analyze_with_resume_stores_info(client, workflow):
    sid, _ = workflow
    # Test attaching resume to existing session
    resume_text = """
    Jordan Lee
    jordan@dev.org
    Skills: Python, Testing, Git
    """
    r = client.post(f"/api/session/{sid}/resume", json={"resume_text": resume_text, "filename": "jordan.txt"})
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["resume_info"]["candidate_name"] == "Jordan Lee"
    assert res["resume_info"]["email"] == "jordan@dev.org"
    assert "Python" in res["resume_info"]["extracted_skills"]

    # Verify session GET includes resume_info and resume_verification
    session_data = client.get(f"/api/session/{sid}").json()
    assert session_data["resume_info"] is not None
    assert session_data["resume_info"]["candidate_name"] == "Jordan Lee"
    assert session_data["resume_verification"] is not None
