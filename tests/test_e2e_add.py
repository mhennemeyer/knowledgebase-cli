import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from knowledgebase.cli import app
from knowledgebase.config import KBConfig
from knowledgebase.core.index import load_index

runner = CliRunner()


@patch("knowledgebase.core.index.get_openai_api_key", return_value="fake-key")
@patch("knowledgebase.core.index.OpenAI")
def test_kb_add_incremental(mock_openai, mock_key_index, pdf_fixture_dir, tmp_path, mock_openai_client):
    """
    Test: kb init (1 Buch) -> kb add (anderes Buch) -> Index enthält beide.
    
    Verifiziert:
    1. Inkrementelles Hinzufügen von Dateien.
    2. Fortlaufende Chunk-IDs.
    3. Korrekte Metadaten (book_file).
    """
    mock_openai.return_value = mock_openai_client
    
    kb_name = "test_add"
    base_dir = tmp_path / "kb_root"
    base_dir.mkdir()
    
    book1 = pdf_fixture_dir / "functor-book.pdf"
    book2 = pdf_fixture_dir / "monad-guide.pdf"
    
    # 1. Init mit nur einem Buch
    init_dir = tmp_path / "init_books"
    init_dir.mkdir()
    shutil.copy(book1, init_dir)
    
    # kb init
    # Wir müssen base_dir explizit übergeben
    result = runner.invoke(app, [
        "init", str(init_dir), 
        "--name", kb_name, 
        "--base-dir", str(base_dir)
    ])
    
    if result.exit_code != 0:
        print(result.stdout)
        print(result.stderr)
    assert result.exit_code == 0
    
    config = KBConfig(name=kb_name, base_dir=base_dir)
    _, chunks = load_index(config)
    
    initial_books = {c.book_file for c in chunks}
    assert len(initial_books) == 1
    assert "functor-book.md" in initial_books
    initial_chunk_count = len(chunks)
    
    # 2. kb add mit dem zweiten Buch (als Datei)
    result = runner.invoke(app, [
        "add", str(book2), 
        "--name", kb_name, 
        "--base-dir", str(base_dir)
    ])
    
    assert result.exit_code == 0
    assert "Erfolgreich 1 Bücher" in result.stdout
    
    # 3. Verifikation
    _, chunks = load_index(config)
    book_files = {c.book_file for c in chunks}
    
    assert len(book_files) == 2
    assert "functor-book.md" in book_files
    assert "monad-guide.md" in book_files
    assert len(chunks) > initial_chunk_count
    
    # Prüfen ob IDs fortlaufend sind (wichtig für Suche)
    ids = [c.chunk_id for c in chunks]
    assert ids == list(range(len(chunks)))
    
    # 4. kb add mit dem gleichen Buch noch einmal (Überspringen)
    result = runner.invoke(app, [
        "add", str(book2), 
        "--name", kb_name, 
        "--base-dir", str(base_dir)
    ])
    assert "Überspringe" in result.stdout
    assert "Keine neuen Bücher" in result.stdout
