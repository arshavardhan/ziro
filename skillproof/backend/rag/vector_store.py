import json
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from database.connection import connect
from rag.chunker import chunk_repository
from rag.embeddings import embed_text

def ensure_tables():
    """Ensure the rag_chunks table and indexes exist in the SQLite database."""
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                symbol TEXT,
                language TEXT,
                chunk_type TEXT,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_rag_session_commit ON rag_chunks(session_id, commit_sha)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_rag_file ON rag_chunks(file_path)")

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        # If dimensions differ, project or compare shared prefix
        min_len = min(len(v1), len(v2))
        if min_len == 0:
            return 0.0
        v1 = v1[:min_len]
        v2 = v2[:min_len]

    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def index_repository(session_id: str, commit_sha: str, files: Dict[str, str]) -> Dict[str, Any]:
    """Index an entire repository snapshot into the vector store.
    Strictly scoped to session_id and commit_sha.
    """
    ensure_tables()
    
    # Check if already indexed for this session & commit
    with connect() as db:
        existing = db.execute(
            "SELECT COUNT(*) as cnt FROM rag_chunks WHERE session_id = ? AND commit_sha = ?",
            (session_id, commit_sha)
        ).fetchone()
        if existing and existing["cnt"] > 0:
            return {
                "status": "ALREADY_INDEXED",
                "chunks_count": existing["cnt"],
                "session_id": session_id,
                "commit_sha": commit_sha
            }

    chunks = chunk_repository(files)
    now = datetime.now(timezone.utc).isoformat()
    indexed_count = 0

    with connect() as db:
        for chunk in chunks:
            # Generate embedding
            emb = embed_text(chunk["content"])
            emb_json = json.dumps(emb)
            
            # Use unique compound ID to prevent collision across sessions
            unique_id = f"{session_id}:{chunk['chunk_id']}"
            db.execute("""
                INSERT OR REPLACE INTO rag_chunks (
                    chunk_id, session_id, commit_sha, file_path, line_start, line_end,
                    symbol, language, chunk_type, content, content_hash, embedding, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                unique_id,
                session_id,
                commit_sha,
                chunk["file"],
                chunk["line_start"],
                chunk["line_end"],
                chunk["symbol"],
                chunk["language"],
                chunk["chunk_type"],
                chunk["content"],
                chunk["content_hash"],
                emb_json,
                now
            ))
            indexed_count += 1

    return {
        "status": "INDEXED",
        "chunks_count": indexed_count,
        "files_count": len(files),
        "session_id": session_id,
        "commit_sha": commit_sha
    }

def search(
    session_id: str,
    commit_sha: str,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0,
    file_filter: Optional[str] = None,
    symbol_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve the most relevant code chunks for a query within a specific session & commit."""
    ensure_tables()
    query_emb = embed_text(query)
    
    with connect() as db:
        query_sql = "SELECT * FROM rag_chunks WHERE session_id = ? AND commit_sha = ?"
        params: List[Any] = [session_id, commit_sha]
        
        if file_filter:
            query_sql += " AND file_path LIKE ?"
            params.append(f"%{file_filter}%")
        if symbol_filter:
            query_sql += " AND symbol LIKE ?"
            params.append(f"%{symbol_filter}%")

        rows = db.execute(query_sql, params).fetchall()

    results = []
    for row in rows:
        chunk_emb = json.loads(row["embedding"])
        sim = cosine_similarity(query_emb, chunk_emb)
        if sim < min_score:
            continue
        results.append({
            "chunk_id": row["chunk_id"],
            "file": row["file_path"],
            "line_start": row["line_start"],
            "line_end": row["line_end"],
            "symbol": row["symbol"],
            "language": row["language"],
            "chunk_type": row["chunk_type"],
            "content": row["content"],
            "content_hash": row["content_hash"],
            "score": round(sim, 4)
        })

    # Sort descending by similarity
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def get_chunks_count(session_id: str, commit_sha: str) -> int:
    """Return number of indexed chunks for this session and commit."""
    ensure_tables()
    with connect() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM rag_chunks WHERE session_id = ? AND commit_sha = ?",
            (session_id, commit_sha)
        ).fetchone()
        return row["cnt"] if row else 0
