"""Tests für EPUB-Extraktion und Format-Factory."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledgebase.core.extract import (
    extract_all_books,
    extract_epub_to_markdown,
    extract_pdf_to_markdown,
    get_extractor,
    slugify,
    SUPPORTED_EXTENSIONS,
)
from knowledgebase.config import KBConfig


# --- get_extractor ---

def test_get_extractor_pdf():
    ext = get_extractor("book.pdf")
    assert ext is extract_pdf_to_markdown


def test_get_extractor_epub():
    ext = get_extractor("book.epub")
    assert ext is extract_epub_to_markdown


def test_get_extractor_unsupported():
    with pytest.raises(ValueError, match="Nicht unterstütztes Format"):
        get_extractor("book.txt")


def test_get_extractor_case_insensitive():
    assert get_extractor("book.PDF") is extract_pdf_to_markdown
    assert get_extractor("book.EPUB") is extract_epub_to_markdown


# --- extract_epub_to_markdown ---

def _mock_epub_chapter(text: str, heading: str | None = None) -> MagicMock:
    """Erzeugt ein Mock-EPUB-Kapitel mit HTML-Inhalt."""
    heading_html = f"<h1>{heading}</h1>" if heading else ""
    html = f"<html><body>{heading_html}<p>{text}</p></body></html>"
    chapter = MagicMock()
    chapter.get_content.return_value = html.encode("utf-8")
    return chapter


def test_extract_epub_to_markdown(tmp_path):
    epub_path = tmp_path / "Test-Book.epub"

    mock_book = MagicMock()
    mock_book.get_metadata.return_value = [("Test Book Title", {})]

    chapters = [
        _mock_epub_chapter("A" * 100, heading="Introduction"),
        _mock_epub_chapter("B" * 100, heading="Chapter One"),
    ]
    mock_book.get_items_of_type.return_value = chapters

    with patch("ebooklib.epub.read_epub", return_value=mock_book):
        markdown, chapter_count = extract_epub_to_markdown(epub_path)

    assert chapter_count == 2
    assert "# Test Book Title" in markdown
    assert "### Kapitel: Introduction" in markdown
    assert "### Kapitel: Chapter One" in markdown


def test_extract_epub_skips_short_chapters(tmp_path):
    epub_path = tmp_path / "Sparse.epub"

    mock_book = MagicMock()
    mock_book.get_metadata.return_value = [("Sparse Book", {})]

    chapters = [
        _mock_epub_chapter("Short"),  # < 50 chars
        _mock_epub_chapter("A" * 100, heading="Real Chapter"),
    ]

    with patch("ebooklib.epub.read_epub", return_value=mock_book):
        mock_book.get_items_of_type.return_value = chapters
        markdown, chapter_count = extract_epub_to_markdown(epub_path)

    assert chapter_count == 1
    assert "Real Chapter" in markdown


def test_extract_epub_fallback_title(tmp_path):
    epub_path = tmp_path / "no-title.epub"

    mock_book = MagicMock()
    mock_book.get_metadata.return_value = []  # Kein Titel in Metadaten

    with patch("ebooklib.epub.read_epub", return_value=mock_book):
        mock_book.get_items_of_type.return_value = []
        markdown, chapter_count = extract_epub_to_markdown(epub_path)

    assert "# no title" in markdown
    assert chapter_count == 0


# --- extract_all_books ---

def test_extract_all_books_mixed_formats(tmp_path):
    book_dir = tmp_path / "books"
    book_dir.mkdir()
    (book_dir / "book-a.pdf").touch()
    (book_dir / "book-b.epub").touch()

    config = KBConfig(name="test", base_dir=tmp_path / ".kb", pdf_dir=book_dir)

    with patch("knowledgebase.core.extract.extract_pdf_to_markdown", return_value=("# PDF\n### Seite 1\ntext", 5)) as m_pdf, \
         patch("knowledgebase.core.extract.extract_epub_to_markdown", return_value=("# EPUB\n### Kapitel: Ch1\ntext", 3)) as m_epub:
        results = extract_all_books(config)

    assert len(results) == 2
    formats = {r["format"] for r in results}
    assert formats == {".pdf", ".epub"}
    assert all("slug" in r and "md_file" in r for r in results)


def test_extract_all_books_ignores_unsupported(tmp_path):
    book_dir = tmp_path / "books"
    book_dir.mkdir()
    (book_dir / "notes.txt").touch()
    (book_dir / "book.pdf").touch()

    config = KBConfig(name="test", base_dir=tmp_path / ".kb", pdf_dir=book_dir)

    with patch("knowledgebase.core.extract.extract_pdf_to_markdown", return_value=("md", 1)):
        results = extract_all_books(config)

    assert len(results) == 1
    assert results[0]["format"] == ".pdf"


def test_extract_all_books_empty_dir(tmp_path):
    book_dir = tmp_path / "books"
    book_dir.mkdir()

    config = KBConfig(name="test", base_dir=tmp_path / ".kb", pdf_dir=book_dir)

    with pytest.raises(FileNotFoundError, match="Keine Bücher"):
        extract_all_books(config)


# --- Chunk-Kapitel-Integration ---

def test_chunk_parses_chapter_references(tmp_path):
    """Prüft, dass Kapitel-Referenzen aus EPUB korrekt gechunked werden."""
    from knowledgebase.core.chunk import parse_markdown_to_chunks

    md_file = tmp_path / "epub-book.md"
    md_file.write_text(
        "# Test\n---\n"
        "### Kapitel: Introduction\n\n" + "A" * 100 + "\n\n"
        "### Kapitel: Monads\n\n" + "B" * 100 + "\n",
        encoding="utf-8",
    )

    chunks = parse_markdown_to_chunks(md_file)

    assert len(chunks) == 2
    assert chunks[0].chapter_title == "Introduction"
    assert chunks[1].chapter_title == "Monads"
    assert chunks[0].page == 1
    assert chunks[1].page == 2
