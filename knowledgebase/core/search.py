"""
Semantische Suche im FAISS-Index.

Basiert auf: LambdaPy/knowledgebase/search.py
"""
import faiss
import numpy as np
from openai import OpenAI

from knowledgebase.config import KBConfig, get_openai_api_key
from knowledgebase.core.index import load_index, get_embeddings
from knowledgebase.core.open_source import build_open_cmd
from knowledgebase.models import Chunk, SearchResult


def search(
    query: str,
    index: faiss.Index,
    chunks: list[Chunk],
    client: OpenAI,
    config: KBConfig,
    top_k: int = 5,
    book_filter: str | None = None,
) -> list[SearchResult]:
    """
    Semantische Suche im FAISS-Index.

    Returns:
        Liste von SearchResult mit Chunk, Score und Open-Kommando.
    """
    response = client.embeddings.create(
        model=config.embedding_model, input=[query]
    )
    query_vec = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    search_k = top_k * 5 if book_filter else top_k
    scores, indices = index.search(query_vec, min(search_k, index.ntotal))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]

        if book_filter and book_filter.lower() not in chunk.book_file.lower():
            continue

        pdf_path = _resolve_pdf_path(chunk.book_file, config)
        open_cmd = build_open_cmd(pdf_path, chunk.page) if pdf_path else ""

        results.append(SearchResult(
            chunk=chunk,
            score=float(score),
            open_cmd=open_cmd,
        ))

        if len(results) >= top_k:
            break

    return results


def _resolve_pdf_path(book_file: str, config: KBConfig) -> str:
    """Versucht den vollständigen Pfad zur PDF-Datei zu ermitteln."""
    if not config.pdf_dir:
        return ""
    # book_file ist der Markdown-Dateiname; PDF-Name rekonstruieren
    # Wir suchen nach einer PDF, deren slugifizierter Name passt
    from knowledgebase.core.extract import slugify
    import os

    pdf_dir = config.pdf_dir
    if not pdf_dir.exists():
        return ""

    md_slug = book_file.replace(".md", "")
    for f in os.listdir(pdf_dir):
        if f.lower().endswith(".pdf") and slugify(f) == md_slug:
            return str(pdf_dir / f)
    return ""


def run_search(
    query: str,
    config: KBConfig,
    top_k: int = 5,
    book_filter: str | None = None,
) -> list[SearchResult]:
    """
    Convenience-Funktion: Lädt Index und führt Suche durch.
    """
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key)
    index, chunks = load_index(config)
    return search(query, index, chunks, client, config, top_k, book_filter)
