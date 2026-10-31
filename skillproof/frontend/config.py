import os

APP_NAME = "SkillProof AI"
APP_TAGLINE = "Verify Skills. Inspect Evidence. Build Trust."
APP_ICON = "🛡️"

# Backend Base URL (Configurable for local and Streamlit Cloud)
DEFAULT_BACKEND_URL = os.environ.get("SKILLPROOF_BACKEND_URL", "http://127.0.0.1:8001")
API_TIMEOUT = int(os.environ.get("SKILLPROOF_API_TIMEOUT", "10"))

# Supported Skills Taxonomy
SUPPORTED_SKILLS = [
    "Python",
    "OOP",
    "Machine Learning",
    "Software Architecture",
    "Testing",
    "Git/GitHub",
    "API Development",
    "JavaScript",
    "React",
    "SQL",
    "FastAPI"
]

# 12 Navigation Pages
NAVIGATION_PAGES = [
    ("📊 Overview", "Overview"),
    ("🔍 Candidate Verification", "Candidate Verification"),
    ("⚡ Agent Workspace", "Agent Workspace"),
    ("🧠 Repository Intelligence", "Repository Intelligence"),
    ("🔎 Evidence Explorer", "Evidence Explorer"),
    ("📜 Git Forensics", "Git Forensics"),
    ("🔬 Originality Analysis", "Originality Analysis"),
    ("🎯 Skill Assessment", "Skill Assessment"),
    ("🎙️ Technical Viva", "Technical Viva"),
    ("👤 Reviewer Approval", "Reviewer Approval"),
    ("🛡️ Credentials", "Credentials"),
    ("📈 Evaluation Lab", "Evaluation Lab"),
]

# Evidence Classification Labels
EVIDENCE_CLASSIFICATIONS = [
    "IMPLEMENTED",
    "TESTED",
    "PARTIALLY_IMPLEMENTED",
    "PLANNED",
    "UNVERIFIED",
    "NOT_DEMONSTRATED"
]

# Verdict Options
VERDICTS = [
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "INSUFFICIENT_EVIDENCE",
    "NOT_DEMONSTRATED"
]
