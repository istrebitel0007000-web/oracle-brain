import re
from apps.rag.models.rag_chunk import RagChunk


def _tokenize(text: str) -> set:
    tokens = re.findall(r"\b[a-z0-9]{2,}\b", text.lower())
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "this", "that", "it", "its", "with",
    }
    return {t for t in tokens if t not in stop_words}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def search_chunks(user_id: int, query: str, top_k: int = 5) -> list:
    """
    Search RAG knowledge base using Jaccard similarity on TF-IDF tokens.
    Returns top_k most relevant RagChunk instances.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    chunks = RagChunk.objects.filter(user_id=user_id)
    scored = []

    for chunk in chunks:
        chunk_tokens = set(chunk.tfidf_tokens)
        score = _jaccard_similarity(query_tokens, chunk_tokens)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]
