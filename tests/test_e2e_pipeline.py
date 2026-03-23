"""
Stufe-1 E2E-Tests: Gesamte Pipeline ohne externe APIs.

Testet den Datenfluss: PDF → extract → chunk → index → search → answer
mit programmatisch erzeugten Test-PDFs und gemockten OpenAI-Calls.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from knowledgebase.cli import app
from knowledgebase.config import KBConfig
from knowledgebase.core.extract import extract_all_books
from knowledgebase.core.chunk import build_all_chunks
from knowledgebase.core.index import build_index, load_index
from knowledgebase.core.search import search
from knowledgebase.core.answer import generate_answer

runner = CliRunner()


def _run_pipeline(pdf_dir: Path, tmp_path: Path, mock_client: MagicMock, kb_name: str = "test") -> KBConfig:
    """Führt die gesamte Pipeline aus: extract → chunk → index."""
    config = KBConfig(
        name=kb_name,
        base_dir=tmp_path / ".kb",
        pdf_dir=pdf_dir,
    )

    # 1. Extract
    results = extract_all_books(config)
    assert len(results) > 0

    # 2. Chunk
    chunks = build_all_chunks(config)
    assert len(chunks) > 0

    # 3. Index (mit gemockten Embeddings)
    with patch("knowledgebase.core.index.get_openai_api_key", return_value="fake-key"), \
         patch("knowledgebase.core.index.OpenAI", return_value=mock_client):
        build_index(chunks, config)

    assert config.index_path.exists()
    assert config.chunks_path.exists()

    return config


class TestE2EInitAndSearch:
    """Test: kb init mit Fixture → kb search liefert Ergebnisse mit korrekten Metadaten."""

    def test_pipeline_produces_searchable_index(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)

        index, chunks = load_index(config)

        assert index.ntotal == len(chunks)
        assert index.ntotal > 0

        # Suche mit gemocktem Embedding-Client
        results = search("functor laws", index, chunks, mock_openai_client, config, top_k=3)

        assert len(results) > 0
        assert len(results) <= 3
        assert all(r.score >= 0 for r in results)

    def test_search_results_have_correct_metadata(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)
        index, chunks = load_index(config)

        results = search("functor", index, chunks, mock_openai_client, config, top_k=5)

        for r in results:
            assert r.chunk.book  # Buchtitel nicht leer
            assert r.chunk.book_file.endswith(".md")
            assert r.chunk.page >= 1
            assert len(r.chunk.text) > 0

    def test_chunks_reference_both_books(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)
        _, chunks = load_index(config)

        book_files = {c.book_file for c in chunks}
        assert "functor-book.md" in book_files
        assert "monad-guide.md" in book_files


class TestE2EInitAndAsk:
    """Test: kb init mit Fixture → kb ask liefert Antwort mit Quellen."""

    def test_ask_returns_answer_with_sources(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)

        fake_llm = lambda system, user: "Funktoren sind Mappings zwischen Kategorien. [Quelle 1]"

        with patch("knowledgebase.core.search.get_openai_api_key", return_value="fake-key"), \
             patch("knowledgebase.core.search.OpenAI", return_value=mock_openai_client):
            answer = generate_answer(
                question="Was sind Funktoren?",
                config=config,
                top_k=3,
                llm_client=fake_llm,
            )

        assert answer.text
        assert "Funktoren" in answer.text
        assert len(answer.sources) > 0
        assert len(answer.sources) <= 3

    def test_ask_no_results_returns_fallback(self, tmp_path, mock_openai_client):
        """Leere KB → Fallback-Antwort."""
        config = KBConfig(name="empty", base_dir=tmp_path / ".kb")
        config.ensure_dirs()

        # Leeren Index bauen
        chunks = []
        with patch("knowledgebase.core.index.get_openai_api_key", return_value="fake-key"), \
             patch("knowledgebase.core.index.OpenAI", return_value=mock_openai_client):
            # Manuell leeren Index + Chunks speichern
            import faiss
            import json as json_mod
            dim = 8
            index = faiss.IndexFlatIP(dim)
            faiss.write_index(index, str(config.index_path))
            config.chunks_path.write_text("[]", encoding="utf-8")

        with patch("knowledgebase.core.search.get_openai_api_key", return_value="fake-key"), \
             patch("knowledgebase.core.search.OpenAI", return_value=mock_openai_client):
            answer = generate_answer(
                question="Was sind Funktoren?",
                config=config,
                top_k=3,
            )

        assert "Keine relevanten Quellen" in answer.text


class TestE2EJsonRoundtrip:
    """Test: CLI JSON-Output ist valides JSON und enthält alle erwarteten Felder."""

    def test_search_json_has_all_fields(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        """Pipeline-erzeugte Daten → CLI JSON-Output enthält alle Felder."""
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)
        index, chunks = load_index(config)

        # Echte Pipeline-Ergebnisse über search() holen
        results = search("functor laws", index, chunks, mock_openai_client, config, top_k=3)
        assert len(results) > 0

        # CLI JSON-Output mit gemocktem run_search testen
        with patch("knowledgebase.core.search.run_search", return_value=results):
            result = runner.invoke(app, [
                "search", "functor laws",
                "--name", config.name,
                "--json",
            ])

        assert result.exit_code == 0, f"CLI error: {result.stdout}"
        data = json.loads(result.stdout)

        assert "query" in data
        assert "results" in data
        assert data["query"] == "functor laws"
        assert len(data["results"]) > 0

        first = data["results"][0]
        expected_fields = {"text", "book", "book_file", "page", "chapter_title", "score", "open_cmd"}
        assert expected_fields.issubset(set(first.keys()))

    def test_ask_json_has_all_fields(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)

        fake_llm_response = "Die Funktor-Gesetze besagen... [Quelle 1]"

        def mock_generate_answer(**kwargs):
            from knowledgebase.models import Answer, SearchResult, Chunk
            return Answer(
                text=fake_llm_response,
                sources=[
                    SearchResult(
                        chunk=Chunk(text="test", book="Book", book_file="b.md", page=1, chunk_id=0),
                        score=0.9,
                    ),
                ],
            )

        with patch("knowledgebase.core.answer.generate_answer", side_effect=mock_generate_answer):
            result = runner.invoke(app, [
                "ask", "Was sind Funktor-Gesetze?",
                "--name", config.name,
                "--json",
            ])

        assert result.exit_code == 0, f"CLI error: {result.stdout}"
        data = json.loads(result.stdout)

        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)

        if data["sources"]:
            source = data["sources"][0]
            expected_fields = {"book", "page", "chapter_title", "score", "open_cmd"}
            assert expected_fields.issubset(set(source.keys()))


class TestE2EBookFilter:
    """Test: Suche mit --book liefert nur Ergebnisse aus dem gefilterten Buch."""

    def test_book_filter_limits_to_matching_book(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)
        index, chunks = load_index(config)

        results = search(
            "programming", index, chunks, mock_openai_client, config,
            top_k=10, book_filter="functor-book",
        )

        assert all(
            "functor-book" in r.chunk.book_file for r in results
        ), f"Book filter broken: {[r.chunk.book_file for r in results]}"

    def test_book_filter_excludes_other_books(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        config = _run_pipeline(pdf_fixture_dir, tmp_path, mock_openai_client)
        index, chunks = load_index(config)

        results = search(
            "programming", index, chunks, mock_openai_client, config,
            top_k=10, book_filter="monad-guide",
        )

        assert all(
            "monad-guide" in r.chunk.book_file for r in results
        ), f"Book filter broken: {[r.chunk.book_file for r in results]}"


class TestE2ENamedKB:
    """Test: Zwei KBs mit --name sind unabhängig."""

    def test_named_kbs_are_independent(self, pdf_fixture_dir, tmp_path, mock_openai_client):
        from tests.conftest import create_test_pdf

        # KB "alpha" mit nur Functor-Book
        alpha_dir = tmp_path / "alpha_books"
        alpha_dir.mkdir()
        create_test_pdf(alpha_dir / "Functor-Book.pdf", {
            1: "Functor laws and category theory fundamentals for functional programming.",
        })
        config_alpha = _run_pipeline(alpha_dir, tmp_path, mock_openai_client, kb_name="alpha")

        # KB "beta" mit nur Monad-Guide
        beta_dir = tmp_path / "beta_books"
        beta_dir.mkdir()
        create_test_pdf(beta_dir / "Monad-Guide.pdf", {
            1: "Monads provide bind and return for handling side effects in programming.",
        })
        config_beta = _run_pipeline(beta_dir, tmp_path, mock_openai_client, kb_name="beta")

        # Beide KBs existieren unabhängig
        _, alpha_chunks = load_index(config_alpha)
        _, beta_chunks = load_index(config_beta)

        alpha_books = {c.book_file for c in alpha_chunks}
        beta_books = {c.book_file for c in beta_chunks}

        assert "functor-book.md" in alpha_books
        assert "monad-guide.md" not in alpha_books

        assert "monad-guide.md" in beta_books
        assert "functor-book.md" not in beta_books
