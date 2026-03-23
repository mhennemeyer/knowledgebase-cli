"""Tests für knowledgebase.cli – Smoke-Tests mit Typer TestRunner."""
import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from knowledgebase.cli import app
from knowledgebase.models import Answer, Chunk, SearchResult

runner = CliRunner()


# --- init ---

def test_init_smoke(tmp_path):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "test.pdf").touch()

    mock_results = [{"book_name": "test.pdf", "slug": "test", "md_file": "test.md", "page_count": 5, "format": ".pdf"}]
    mock_chunks = [
        Chunk(text="x" * 100, book="Test", book_file="test.md", page=1, chunk_id=0),
    ]

    with patch("knowledgebase.core.extract.extract_all_books", return_value=mock_results), \
         patch("knowledgebase.core.chunk.build_all_chunks", return_value=mock_chunks), \
         patch("knowledgebase.core.index.build_index"):
        result = runner.invoke(app, ["init", str(pdf_dir)])

    assert result.exit_code == 0
    assert "erfolgreich" in result.stdout


# --- search ---

def test_search_smoke():
    mock_results = [
        SearchResult(
            chunk=Chunk(text="Functor laws", book="CT", book_file="ct.md", page=10, chunk_id=0),
            score=0.95,
            open_cmd="open -a Skim 'ct.pdf' --args -page 10",
        ),
    ]

    with patch("knowledgebase.core.search.run_search", return_value=mock_results):
        result = runner.invoke(app, ["search", "functor"])

    assert result.exit_code == 0
    assert "Functor laws" in result.stdout
    assert "0.950" in result.stdout


def test_search_json_output():
    mock_results = [
        SearchResult(
            chunk=Chunk(text="Functor laws", book="CT", book_file="ct.md", page=10, chunk_id=0),
            score=0.95,
            open_cmd="",
        ),
    ]

    with patch("knowledgebase.core.search.run_search", return_value=mock_results):
        result = runner.invoke(app, ["search", "functor", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["query"] == "functor"
    assert len(data["results"]) == 1


# --- ask ---

def test_ask_human_readable():
    mock_answer = Answer(
        text="Monaden sind ein Designpattern.",
        sources=[
            SearchResult(
                chunk=Chunk(text="x" * 100, book="FP Book", book_file="fp.md", page=5, chunk_id=0),
                score=0.92,
                open_cmd="",
            ),
        ],
    )

    with patch("knowledgebase.core.answer.generate_answer", return_value=mock_answer):
        result = runner.invoke(app, ["ask", "Was sind Monaden?"])

    assert result.exit_code == 0
    assert "Monaden sind ein Designpattern" in result.stdout
    assert "FP Book" in result.stdout


def test_ask_json_output():
    mock_answer = Answer(
        text="Answer text",
        sources=[
            SearchResult(
                chunk=Chunk(text="x" * 100, book="Book", book_file="b.md", page=1, chunk_id=0),
                score=0.9,
                open_cmd="",
            ),
        ],
    )

    with patch("knowledgebase.core.answer.generate_answer", return_value=mock_answer):
        result = runner.invoke(app, ["ask", "Test?", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) == 1


# --- list ---

def test_list_books():
    chunks = [
        Chunk(text="x" * 100, book="Book A", book_file="book-a.md", page=1, chunk_id=0),
        Chunk(text="y" * 100, book="Book A", book_file="book-a.md", page=2, chunk_id=1),
        Chunk(text="z" * 100, book="Book B", book_file="book-b.md", page=1, chunk_id=2),
    ]
    mock_index = MagicMock()

    with patch("knowledgebase.core.index.load_index", return_value=(mock_index, chunks)):
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Book A" in result.stdout
    assert "Book B" in result.stdout
    assert "2 Bücher" in result.stdout


# --- status ---

def test_status_missing_index(tmp_path):
    with patch("knowledgebase.config.DEFAULT_KB_DIR", tmp_path / ".kb"):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1


# --- open ---

def test_open_calls_open_pdf():
    with patch("knowledgebase.core.open_source.open_pdf") as mock_open:
        result = runner.invoke(app, ["open", "/path/to/book.pdf", "--page", "42"])

    assert result.exit_code == 0
    mock_open.assert_called_once_with("/path/to/book.pdf", 42)
