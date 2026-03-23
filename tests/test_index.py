"""Tests für knowledgebase.core.index."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from knowledgebase.core.index import build_index, get_embeddings, load_index
from knowledgebase.config import KBConfig
from knowledgebase.models import Chunk


# --- get_embeddings ---

def _mock_openai_client(dim: int = 8) -> MagicMock:
    """Erzeugt einen Mock-OpenAI-Client für Embeddings."""
    client = MagicMock()

    def fake_create(model, input):
        response = MagicMock()
        response.data = [
            MagicMock(embedding=list(np.random.rand(dim).astype(float)))
            for _ in input
        ]
        return response

    client.embeddings.create.side_effect = fake_create
    return client


def test_get_embeddings_single_batch():
    client = _mock_openai_client(dim=8)
    texts = ["hello", "world"]
    result = get_embeddings(texts, client, model="test-model", batch_size=100)

    assert result.shape == (2, 8)
    assert result.dtype == np.float32
    client.embeddings.create.assert_called_once()


def test_get_embeddings_multiple_batches():
    client = _mock_openai_client(dim=8)
    texts = [f"text-{i}" for i in range(5)]
    result = get_embeddings(texts, client, model="test-model", batch_size=2)

    assert result.shape == (5, 8)
    assert client.embeddings.create.call_count == 3  # 2+2+1


# --- build_index ---

def test_build_index_creates_files(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    chunks = [
        Chunk(text="First chunk text", book="Book A", book_file="book-a.md", page=1, chunk_id=0),
        Chunk(text="Second chunk text", book="Book A", book_file="book-a.md", page=2, chunk_id=1),
    ]

    client = _mock_openai_client(dim=8)
    with patch("knowledgebase.core.index.get_openai_api_key", return_value="fake-key"), \
         patch("knowledgebase.core.index.OpenAI", return_value=client):
        build_index(chunks, config)

    assert config.index_path.exists()
    assert config.chunks_path.exists()

    chunks_data = json.loads(config.chunks_path.read_text(encoding="utf-8"))
    assert len(chunks_data) == 2
    assert chunks_data[0]["text"] == "First chunk text"


# --- load_index ---

def test_load_index_roundtrip(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    chunks = [
        Chunk(text="Test chunk", book="Book", book_file="book.md", page=1, chunk_id=0),
    ]

    client = _mock_openai_client(dim=8)
    with patch("knowledgebase.core.index.get_openai_api_key", return_value="fake-key"), \
         patch("knowledgebase.core.index.OpenAI", return_value=client):
        build_index(chunks, config)

    index, loaded_chunks = load_index(config)

    assert index.ntotal == 1
    assert len(loaded_chunks) == 1
    assert loaded_chunks[0].text == "Test chunk"
    assert loaded_chunks[0].book == "Book"


def test_load_index_missing_files(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    with pytest.raises(FileNotFoundError, match="Index nicht gefunden"):
        load_index(config)
