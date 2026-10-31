import hashlib
from typing import List, Dict, Any
from rag.vector_store import search

SKILL_QUERY_MAP = {
    "Python": "Python class definition function decorator generator list comprehension typing type hint",
    "Machine Learning": "model training dataset pipeline feature drift uncertainty predict fit score classification regression",
    "Object-Oriented Programming": "class inheritance encapsulation polymorphism method abstract base class super init interface",
    "Software Architecture": "design pattern architecture pipeline modular decoupled factory registry service adapter engine",
    "Testing": "pytest test assertions fixture mock test case parametrized unit test assertion error",
    "Git/GitHub": "version control git commit history branch workflow ci action release",
    "API and Package Development": "FastAPI router endpoint REST API request validation serializer schema response package setup",
    "Security": "sanitization validation authentication authorization token encryption hashing secret guardrail",
    "Database": "sqlite database query transaction schema table migration execute fetchall ORM connection"
}

def get_skill_query(skill: str) -> str:
    """Map skill to targeted domain retrieval query."""
    return SKILL_QUERY_MAP.get(skill, f"{skill} implementation pattern architecture function class")

def retrieve_for_skill(
    session_id: str,
    commit_sha: str,
    skill: str,
    top_k: int = 5,
    min_score: float = 0.1
) -> List[Dict[str, Any]]:
    """Retrieve top relevant code chunks for a given skill with relevance filtering."""
    query = get_skill_query(skill)
    chunks = search(session_id, commit_sha, query, top_k=top_k * 2)
    
    # Filter by minimum score and deduplicate
    filtered = []
    seen_ranges = set()

    for chunk in chunks:
        if chunk["score"] < min_score:
            continue
        range_key = (chunk["file"], chunk["line_start"], chunk["line_end"])
        if range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)
        
        filtered.append(chunk)
        if len(filtered) >= top_k:
            break

    return filtered

def retrieve_evidence_for_skills(
    session_id: str,
    commit_sha: str,
    skills: List[str],
    top_k_per_skill: int = 3
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve grounded code evidence for all claimed skills."""
    evidence_by_skill = {}
    for skill in skills:
        chunks = retrieve_for_skill(session_id, commit_sha, skill, top_k=top_k_per_skill)
        evidence_by_skill[skill] = chunks
    return evidence_by_skill

def chunks_to_evidence_items(
    session_id: str,
    candidate_id: str,
    commit_sha: str,
    skill: str,
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Convert RAG chunks into formal SkillProof evidence objects."""
    evidence_items = []
    for chunk in chunks:
        content_hash = chunk["content_hash"][:12]
        evidence_id = f"rag-{chunk['file'].replace('/', '_')}-{chunk['line_start']}-{content_hash}"
        kind = chunk["chunk_type"]
        if kind not in {"function", "method", "class", "documentation", "module"}:
            kind = "module"
        
        item = {
            "evidence_id": evidence_id,
            "commit_sha": commit_sha,
            "assessment_id": session_id,
            "candidate_id": candidate_id,
            "claimed_skills": [skill],
            "evidence_type": "CODE_IMPLEMENTATION" if kind in {"function", "method"} else "ARCHITECTURE",
            "file": chunk["file"],
            "line_start": max(1, chunk["line_start"]),
            "line_end": max(1, chunk["line_end"]),
            "symbol": chunk["symbol"],
            "kind": kind,
            "state": "IMPLEMENTED",
            "source": chunk["content"][:2000],
            "docstring": None,
            "type_hints": [],
            "calls": [],
            "imports": [],
            "exceptions": [],
            "complexity": None,
            "signature": "",
            "collection_tool": "rag_semantic_retriever",
            "raw_observation": {
                "symbol": chunk["symbol"],
                "relevance_score": chunk["score"],
                "language": chunk["language"],
                "chunk_type": chunk["chunk_type"]
            },
            "interpretation": f"Retrieved via repository RAG for skill '{skill}' (similarity {chunk['score']})",
            "evidence_strength": "RETRIEVED_SOURCE_EVIDENCE",
            "verification_status": "IMPLEMENTED",
            "observed_facts": [
                f"Source segment in {chunk['file']}:{chunk['line_start']}-{chunk['line_end']} defines {chunk['symbol']}"
            ],
            "limitations": [
                "Semantic similarity indicates thematic relevance, not candidate personal authorship."
            ]
        }
        evidence_items.append(item)
    return evidence_items
