"""Tests für knowledgebase.core.search."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

from knowledgebase.core.search import _resolve_pdf_path, search
from knowledgebase.config import KBConfig
from knowledgebase.models import Chunk


def _build_test_index(chunks: list[Chunk], dim: int = 8) -> faiss.Index:
    """Erzeugt einen FAISS-Index mit zufälligen Vektoren."""
    embeddings = np.random.rand(len(chunks), dim).astype(np.float32)
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def _mock_embedding_client(dim: int = 8) -> MagicMock:
    client = MagicMock()
    embedding = list(np.random.rand(dim).astype(float))
    response = MagicMock()
    response.data = [MagicMock(embedding=embedding)]
    client.embeddings.create.return_value = response
    return client


# --- search ---

def test_search_returns_results():
    chunks = [
        Chunk(text="Functor laws explained", book="CT Book", book_file="ct-book.md", page=10, chunk_id=0),
        Chunk(text="Monad tutorial", book="CT Book", book_file="ct-book.md", page=20, chunk_id=1),
    ]
    index = _build_test_index(chunks)
    client = _mock_embedding_client()
    config = KBConfig(name="test")

    results = search("functor", index, chunks, client, config, top_k=2)

    assert len(results) == 2
    assert all(r.score >= 0 for r in results)
    assert all(r.chunk in chunks for r in results)


def test_search_with_book_filter():
    chunks = [
        Chunk(text="A" * 100, book="Book A", book_file="book-a.md", page=1, chunk_id=0),
        Chunk(text="B" * 100, book="Book B", book_file="book-b.md", page=1, chunk_id=1),
    ]
    index = _build_test_index(chunks)
    client = _mock_embedding_client()
    config = KBConfig(name="test")

    results = search("query", index, chunks, client, config, top_k=5, book_filter="book-a")

    assert all(r.chunk.book_file == "book-a.md" for r in results)


def test_search_top_k_limits_results():
    chunks = [
        Chunk(text=f"Chunk {i}" + "x" * 100, book="Book", book_file="book.md", page=i, chunk_id=i)
        for i in range(10)
    ]
    index = _build_test_index(chunks)
    client = _mock_embedding_client()
    config = KBConfig(name="test")

    results = search("query", index, chunks, client, config, top_k=3)

    assert len(results) <= 3


# --- _resolve_pdf_path ---

def test_resolve_pdf_path_finds_matching_pdf(tmp_path):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "Clean-Code.pdf").touch()

    config = KBConfig(name="test", pdf_dir=pdf_dir)
    result = _resolve_pdf_path("clean-code.md", config)

    assert "Clean-Code.pdf" in result


def test_resolve_pdf_path_no_pdf_dir():
    config = KBConfig(name="test", pdf_dir=None)
    assert _resolve_pdf_path("book.md", config) == ""


def test_resolve_pdf_path_missing_dir(tmp_path):
    config = KBConfig(name="test", pdf_dir=tmp_path / "nonexistent")
    assert _resolve_pdf_path("book.md", config) == ""


def test_resolve_pdf_path_no_match(tmp_path):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "Other-Book.pdf").touch()

    config = KBConfig(name="test", pdf_dir=pdf_dir)
    assert _resolve_pdf_path("clean-code.md", config) == ""
