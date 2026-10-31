import hashlib
import math
import re
import time
from typing import List
import httpx
import config

EMBEDDING_DIM = 384

def _deterministic_fallback_embed(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Deterministic offline vector generator based on word/character n-grams.
    Ensures unit tests, offline environments, and rate-limited calls continue without failure.
    Produces stable, normalized vectors suitable for cosine similarity.
    """
    vector = [0.0] * dim
    words = re.findall(r"\w+", text.lower())
    if not words:
        return vector

    for i, word in enumerate(words):
        # Hash word and character 3-grams into vector buckets
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vector[idx] += 1.0 / (1.0 + math.log(1 + i))
        
        for j in range(len(word) - 2):
            gram = word[j:j+3]
            gh = int(hashlib.sha256(gram.encode("utf-8")).hexdigest(), 16)
            vector[gh % dim] += 0.5

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector

def embed_text(text: str) -> List[float]:
    """Generate embedding vector for a single text chunk."""
    if not config.LLM_API_KEY:
        return _deterministic_fallback_embed(text)

    model = getattr(config, "EMBEDDING_MODEL", "gemini-embedding-001")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": config.LLM_API_KEY
    }
    payload = {
        "content": {
            "parts": [{"text": text[:4000]}]
        }
    }

    try:
        with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
            for attempt in range(2):
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    vals = response.json().get("embedding", {}).get("values", [])
                    if vals:
                        # L2 normalize
                        norm = math.sqrt(sum(v * v for v in vals))
                        return [v / norm for v in vals] if norm > 0 else vals
                elif response.status_code in {429, 500, 503} and attempt == 0:
                    time.sleep(0.5)
                    continue
                else:
                    break
    except Exception:
        pass

    # Fallback if network/API fails or times out
    return _deterministic_fallback_embed(text)

def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts with batching and error resilience."""
    embeddings = []
    for text in texts:
        embeddings.append(embed_text(text))
    return embeddings
