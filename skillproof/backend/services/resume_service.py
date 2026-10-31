import io
import re
from typing import Any, Dict, List, Optional, Tuple

TECH_TAXONOMY = {
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "go": "Go",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "shell": "Shell",

    # Frameworks & Libraries
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "angular": "Angular",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "transformers": "Transformers",
    "huggingface": "HuggingFace",

    # DevOps & Infrastructure
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "git": "Git",
    "github": "Git/GitHub",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "terraform": "Terraform",
    "linux": "Linux",

    # Databases
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "chromadb": "ChromaDB",

    # Architecture & Practices
    "rest": "REST APIs",
    "restful": "REST APIs",
    "api development": "API Development",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    "object-oriented programming": "OOP",
    "oop": "OOP",
    "rag": "RAG",
    "retrieval augmented generation": "RAG",
    "llm": "LLMs",
    "machine learning": "Machine Learning",
    "software architecture": "Software Architecture",
    "unit testing": "Testing",
    "pytest": "Testing",
    "testing": "Testing",
    "system design": "Software Architecture",
}


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from uploaded file bytes (PDF, DOCX, TXT, MD)."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext == "pdf":
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip()
        except Exception:
            try:
                from pdfminer.high_level import extract_text
                return extract_text(io.BytesIO(file_bytes)).strip()
            except Exception:
                # Fallback to UTF-8 / latin-1 regex extraction
                return re.sub(r"[^\x20-\x7E\n]", " ", file_bytes.decode("latin-1", errors="ignore"))

    elif ext in {"docx", "doc"}:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception:
            return file_bytes.decode("utf-8", errors="ignore").strip()

    else:
        # Default text decode
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_bytes.decode(enc).strip()
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="ignore").strip()


def parse_resume(text: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """Parse resume text and extract candidate profile, contact info, and skills."""
    if not text:
        return {
            "candidate_name": None,
            "email": None,
            "phone": None,
            "github_url": None,
            "extracted_skills": [],
            "experience_summary": None,
            "raw_text_length": 0,
            "filename": filename,
        }

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Extract email
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    email = email_match.group(0) if email_match else None

    # Extract phone
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    phone = phone_match.group(0) if phone_match else None

    # Extract GitHub URL
    gh_match = re.search(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]+)?", text, re.IGNORECASE)
    github_url = gh_match.group(0) if gh_match else None

    # Extract candidate name (heuristics from first 5 non-empty lines)
    candidate_name = None
    for line in lines[:5]:
        if email and email in line:
            continue
        if phone and phone in line:
            continue
        if "curriculum vitae" in line.lower() or "resume" in line.lower():
            continue
        # Names are typically 2-4 capitalized words
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() or "." in w for w in words) and len(line) < 40:
            candidate_name = line
            break

    if not candidate_name and lines:
        first_line = lines[0]
        if len(first_line) < 40 and not any(char in first_line for char in "@/:{}[]"):
            candidate_name = first_line

    # Extract skills using word boundaries & taxonomy
    lower_text = " " + text.lower() + " "
    detected_skills = set()

    for term, canonical_name in TECH_TAXONOMY.items():
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        if re.search(pattern, lower_text):
            detected_skills.add(canonical_name)

    # Sort detected skills alphabetically
    sorted_skills = sorted(detected_skills)

    # Experience summary extraction
    exp_snippets = []
    exp_keywords = ["experience", "employment", "work history", "projects", "education"]
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in exp_keywords):
            # Take next 3-5 lines as context
            exp_snippets.extend(lines[i:i+6])
            break

    summary = "\n".join(exp_snippets[:6]) if exp_snippets else "\n".join(lines[:4])

    return {
        "candidate_name": candidate_name,
        "email": email,
        "phone": phone,
        "github_url": github_url,
        "extracted_skills": sorted_skills,
        "experience_summary": summary[:500],
        "raw_text_length": len(text),
        "filename": filename,
    }


def match_resume_to_repository(
    resume_skills: List[str],
    code_evidence: List[Dict[str, Any]],
    rag_evidence: Optional[Dict[str, Any]] = None,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compare resume claimed skills against actual repository findings."""
    languages_lower = {lang.lower() for lang in (languages or [])}
    evidence_text = " ".join([
        e.get("symbol", "") + " " + e.get("file", "") + " " + (e.get("docstring") or "")
        for e in (code_evidence or [])
    ]).lower()

    if rag_evidence:
        for skill_chunks in rag_evidence.values():
            if isinstance(skill_chunks, list):
                for chunk in skill_chunks:
                    evidence_text += " " + chunk.get("content", "").lower()

    demonstrated = []
    unverified = []

    for skill in resume_skills:
        skill_lower = skill.lower()
        # Direct match in languages, symbols, or evidence text
        is_in_languages = skill_lower in languages_lower or any(skill_lower in l for l in languages_lower)
        is_in_evidence = skill_lower in evidence_text or any(part in evidence_text for part in skill_lower.split())

        if is_in_languages or is_in_evidence:
            demonstrated.append({
                "skill": skill,
                "status": "DEMONSTRATED_IN_REPO",
                "evidence_type": "LANGUAGE" if is_in_languages else "CODE_FINDINGS",
            })
        else:
            unverified.append({
                "skill": skill,
                "status": "NOT_DEMONSTRATED_IN_REPO",
                "notes": "Claimed on resume, but no supporting source code, tests, or dependencies found in repository snapshot.",
            })

    total = len(resume_skills)
    demonstrated_count = len(demonstrated)
    alignment_score = round((demonstrated_count / total * 100), 1) if total > 0 else 0.0

    return {
        "total_resume_skills": total,
        "demonstrated_count": demonstrated_count,
        "unverified_count": len(unverified),
        "alignment_score": alignment_score,
        "demonstrated_skills": demonstrated,
        "unverified_skills": unverified,
    }
