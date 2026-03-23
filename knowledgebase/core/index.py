"""
FAISS-Index bauen, laden und speichern.

Basiert auf: LambdaPy/knowledgebase/build_index.py
"""
import json
import os
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from knowledgebase.config import KBConfig, get_openai_api_key
from knowledgebase.models import Chunk


def get_embeddings(
    texts: list[str],
    client: OpenAI,
    model: str = "text-embedding-3-large",
    batch_size: int = 100,
) -> np.ndarray:
    """Erzeugt Embeddings in Batches über die OpenAI API."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
    return np.array(all_embeddings, dtype=np.float32)


def build_index(chunks: list[Chunk], config: KBConfig) -> None:
    """
    Baut einen FAISS-Index aus Chunks und speichert Index + Metadaten.
    """
    config.ensure_dirs()
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key)

    # Chunks als JSON speichern
    chunks_data = [asdict(c) for c in chunks]
    config.chunks_path.write_text(
        json.dumps(chunks_data, ensure_ascii=False), encoding="utf-8"
    )

    # Embeddings erzeugen
    texts = [c.text for c in chunks]
    embeddings = get_embeddings(texts, client, model=config.embedding_model)

    # FAISS-Index bauen (Cosine Similarity via Inner Product nach Normalisierung)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(config.index_path))


def load_index(config: KBConfig) -> tuple[faiss.Index, list[Chunk]]:
    """
    Lädt FAISS-Index und Chunk-Metadaten.

    Returns:
        (faiss_index, chunks)
    """
    if not config.index_path.exists() or not config.chunks_path.exists():
        raise FileNotFoundError(
            "Index nicht gefunden. Bitte zuerst `kb init` ausführen."
        )

    index = faiss.read_index(str(config.index_path))

    chunks_data = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    chunks = [Chunk(**c) for c in chunks_data]

    return index, chunks


def append_to_index(new_chunks: list[Chunk], config: KBConfig) -> None:
    """
    Fügt neue Chunks zu einem bestehenden Index hinzu.
    """
    if not new_chunks:
        return

    config.ensure_dirs()
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key)

    # Bestehenden Index laden
    index, existing_chunks = load_index(config)

    # Neue Embeddings erzeugen
    texts = [c.text for c in new_chunks]
    new_embeddings = get_embeddings(texts, client, model=config.embedding_model)

    # FAISS-Index erweitern
    faiss.normalize_L2(new_embeddings)
    index.add(new_embeddings)

    # Chunks mergen und IDs anpassen (fortlaufend)
    last_id = existing_chunks[-1].chunk_id if existing_chunks else -1
    renumbered_new_chunks = [
        Chunk(
            text=c.text,
            book=c.book,
            book_file=c.book_file,
            page=c.page,
            chunk_id=last_id + 1 + i,
            chapter_title=c.chapter_title
        )
        for i, c in enumerate(new_chunks)
    ]

    all_chunks = existing_chunks + renumbered_new_chunks
    chunks_data = [asdict(c) for c in all_chunks]
    config.chunks_path.write_text(
        json.dumps(chunks_data, ensure_ascii=False), encoding="utf-8"
    )

    # Index speichern
    faiss.write_index(index, str(config.index_path))
