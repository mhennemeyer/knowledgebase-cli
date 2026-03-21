"""
FAISS-Index bauen, laden und speichern.

Basiert auf: LambdaPy/knowledgebase/build_index.py
"""
import json
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
    model: str = "text-embedding-3-small",
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
