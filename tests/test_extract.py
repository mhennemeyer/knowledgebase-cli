"""Tests für knowledgebase.core.extract."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledgebase.core.extract import (
    extract_all_pdfs,
    extract_pdf_to_markdown,
    extract_toc,
    format_toc,
    slugify,
)
from knowledgebase.config import KBConfig


# --- slugify ---

def test_slugify_simple():
    assert slugify("Clean-Code.pdf") == "clean-code"


def test_slugify_spaces_and_special_chars():
    assert slugify("My Book (2nd Edition).pdf") == "my-book-2nd-edition"


def test_slugify_multiple_hyphens():
    assert slugify("a---b___c.pdf") == "a-b-c"


def test_slugify_unicode():
    assert slugify("Über Funktoren.pdf") == "ber-funktoren"


def test_slugify_no_extension():
    assert slugify("readme") == "readme"


# --- extract_toc ---

def test_extract_toc_returns_list_of_dicts():
    doc = MagicMock()
    doc.get_toc.return_value = [
        (1, "Chapter 1", 1),
        (2, "Section 1.1", 3),
        (1, "Chapter 2", 10),
    ]
    toc = extract_toc(doc)
    assert len(toc) == 3
    assert toc[0] == {"level": 1, "title": "Chapter 1", "page": 1}
    assert toc[1] == {"level": 2, "title": "Section 1.1", "page": 3}


def test_extract_toc_empty():
    doc = MagicMock()
    doc.get_toc.return_value = []
    assert extract_toc(doc) == []


# --- format_toc ---

def test_format_toc_with_entries():
    toc = [
        {"level": 1, "title": "Intro", "page": 1},
        {"level": 2, "title": "Background", "page": 5},
    ]
    result = format_toc(toc)
    assert "## Inhaltsverzeichnis" in result
    assert "- Intro (S. 1)" in result
    assert "  - Background (S. 5)" in result


def test_format_toc_empty():
    assert format_toc([]) == ""


# --- extract_pdf_to_markdown ---

def test_extract_pdf_to_markdown(tmp_path):
    """Testet PDF-Extraktion mit gemocktem PyMuPDF."""
    pdf_path = tmp_path / "Test-Book.pdf"

    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Content of page one."
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Content of page two."

    mock_doc = MagicMock()
    mock_doc.page_count = 2
    mock_doc.get_toc.return_value = []
    mock_doc.__iter__ = lambda self: iter([mock_page1, mock_page2])

    with patch("knowledgebase.core.extract.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        markdown, page_count = extract_pdf_to_markdown(pdf_path)

    assert page_count == 2
    assert "# Test Book" in markdown
    assert "### Seite 1" in markdown
    assert "### Seite 2" in markdown
    assert "Content of page one." in markdown
    assert "Content of page two." in markdown


def test_extract_pdf_to_markdown_skips_empty_pages(tmp_path):
    pdf_path = tmp_path / "Sparse.pdf"

    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Real content here."
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = ""

    mock_doc = MagicMock()
    mock_doc.page_count = 2
    mock_doc.get_toc.return_value = []
    mock_doc.__iter__ = lambda self: iter([mock_page1, mock_page2])

    with patch("knowledgebase.core.extract.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        markdown, _ = extract_pdf_to_markdown(pdf_path)

    assert "### Seite 1" in markdown
    assert "### Seite 2" not in markdown


# --- extract_all_pdfs ---

def test_extract_all_pdfs_no_pdf_dir():
    config = KBConfig(name="test", pdf_dir=None)
    with pytest.raises(ValueError, match="Kein Buch-Verzeichnis"):
        extract_all_pdfs(config)


def test_extract_all_pdfs_dir_not_found(tmp_path):
    config = KBConfig(name="test", pdf_dir=tmp_path / "nonexistent")
    with pytest.raises(FileNotFoundError, match="nicht gefunden"):
        extract_all_pdfs(config)


def test_extract_all_pdfs_empty_dir(tmp_path):
    config = KBConfig(
        name="test",
        base_dir=tmp_path / ".kb",
        pdf_dir=tmp_path / "pdfs",
    )
    (tmp_path / "pdfs").mkdir()
    with pytest.raises(FileNotFoundError, match="Keine Bücher"):
        extract_all_pdfs(config)


def test_extract_all_pdfs_normal(tmp_path):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "book-one.pdf").touch()
    (pdf_dir / "book-two.pdf").touch()

    config = KBConfig(
        name="test",
        base_dir=tmp_path / ".kb",
        pdf_dir=pdf_dir,
    )

    mock_doc = MagicMock()
    mock_doc.page_count = 3
    mock_doc.get_toc.return_value = []
    page = MagicMock()
    page.get_text.return_value = "Sample text content for testing."
    mock_doc.__iter__ = lambda self: iter([page, page, page])

    with patch("knowledgebase.core.extract.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        results = extract_all_pdfs(config)

    assert len(results) == 2
    assert results[0]["pdf_name"] == "book-one.pdf"
    assert results[0]["page_count"] == 3
    assert (config.markdown_dir / results[0]["md_file"]).exists()
