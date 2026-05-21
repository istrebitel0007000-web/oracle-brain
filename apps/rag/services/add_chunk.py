import re
from apps.rag.models.rag_chunk import RagChunk


def _tokenize(text: str) -> list:
    """Simple whitespace + punctuation tokenizer for TF-IDF."""
    tokens = re.findall(r"\b[a-z0-9]{2,}\b", text.lower())
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "this", "that", "it", "its", "with",
    }
    return [t for t in tokens if t not in stop_words]


def add_chunk(user_id: int, text: str, source: str = "") -> RagChunk:
    """
    Add a text chunk to the RAG knowledge base.
    Computes TF-IDF tokens for similarity search.
    """
    tokens = _tokenize(text)
    return RagChunk.objects.create(
        user_id=user_id,
        text=text,
        source=source,
        tfidf_tokens=tokens,
    )


def add_chunks_from_text(user_id: int, text: str, source: str = "", chunk_size: int = 500) -> list:
    """
    Split text into overlapping chunks and add each to RAG.
    Returns list of created RagChunk instances.
    """
    words = text.split()
    overlap = chunk_size // 5
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        chunk = add_chunk(user_id=user_id, text=chunk_text, source=source)
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
