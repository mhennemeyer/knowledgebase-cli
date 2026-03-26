"""Tests für knowledgebase.core.chunk."""
from pathlib import Path

import pytest

from knowledgebase.core.chunk import build_all_chunks, parse_markdown_to_chunks
from knowledgebase.config import KBConfig
from knowledgebase.models import Chunk


# --- parse_markdown_to_chunks ---

def _make_md(pages: list[tuple[int, str]]) -> str:
    """Hilfsfunktion: Erzeugt Markdown mit Seitenreferenzen."""
    lines = ["# Test Book\n", "---\n"]
    for page_num, text in pages:
        lines.append(f"### Seite {page_num}\n")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def test_parse_simple_pages(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    md_file = tmp_path / "test-book.md"
    md_file.write_text(
        _make_md([(1, "A" * 100), (2, "B" * 100)]),
        encoding="utf-8",
    )
    chunks = parse_markdown_to_chunks(md_file, config=config)
    assert len(chunks) == 2
    assert chunks[0].page == 1
    assert chunks[1].page == 2
    assert chunks[0].book == "Test Book"
    assert chunks[0].book_file == "test-book.md"


def test_parse_skips_short_pages(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    md_file = tmp_path / "test-book.md"
    md_file.write_text(
        _make_md([(1, "Short"), (2, "A" * 100)]),
        encoding="utf-8",
    )
    chunks = parse_markdown_to_chunks(md_file, config=config)
    assert len(chunks) == 1
    assert chunks[0].page == 2


def test_parse_large_page_splits_with_overlap(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb", chunk_size=1500, chunk_overlap=200)
    md_file = tmp_path / "test-book.md"
    large_text = "A" * 3000
    md_file.write_text(
        _make_md([(1, large_text)]),
        encoding="utf-8",
    )
    chunks = parse_markdown_to_chunks(md_file, config=config)
    assert len(chunks) >= 2
    assert all(c.page == 1 for c in chunks)


def test_parse_chunk_ids_sequential(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    md_file = tmp_path / "test-book.md"
    md_file.write_text(
        _make_md([(1, "A" * 100), (2, "B" * 100), (3, "C" * 100)]),
        encoding="utf-8",
    )
    chunks = parse_markdown_to_chunks(md_file, config=config)
    assert [c.chunk_id for c in chunks] == [0, 1, 2]


# --- build_all_chunks ---

def test_build_all_chunks_global_ids(tmp_path):
    kb_dir = tmp_path / ".kb" / "test"
    md_dir = kb_dir / "markdown"
    md_dir.mkdir(parents=True)

    (md_dir / "book-a.md").write_text(
        _make_md([(1, "A" * 100), (2, "B" * 100)]),
        encoding="utf-8",
    )
    (md_dir / "book-b.md").write_text(
        _make_md([(1, "C" * 100)]),
        encoding="utf-8",
    )

    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    chunks = build_all_chunks(config)

    assert len(chunks) == 3
    assert [c.chunk_id for c in chunks] == [0, 1, 2]
    assert chunks[0].book_file == "book-a.md"
    assert chunks[2].book_file == "book-b.md"


def test_build_all_chunks_missing_dir(tmp_path):
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    with pytest.raises(FileNotFoundError, match="Markdown-Verzeichnis"):
        build_all_chunks(config)


def test_build_all_chunks_empty_dir(tmp_path):
    md_dir = tmp_path / ".kb" / "test" / "markdown"
    md_dir.mkdir(parents=True)
    config = KBConfig(name="test", base_dir=tmp_path / ".kb")
    with pytest.raises(FileNotFoundError, match="Keine Markdown-Dateien"):
        build_all_chunks(config)
