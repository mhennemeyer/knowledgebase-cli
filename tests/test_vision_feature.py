"""Tests für das Vision & Bild-Feature."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from knowledgebase.config import KBConfig
from knowledgebase.core.extract import extract_pdf_to_markdown
from knowledgebase.core.chunk import parse_markdown_to_chunks
from knowledgebase.core.answer import generate_answer
from knowledgebase.models import Chunk


@pytest.fixture
def mock_config(tmp_path):
    return KBConfig(
        name="vision-test",
        base_dir=tmp_path / "kbs",
        use_vision=True
    )


@patch("knowledgebase.core.extract.fitz.open")
@patch("knowledgebase.core.extract.get_image_description")
def test_pdf_extraction_with_images(mock_desc, mock_fitz_open, mock_config, tmp_path):
    # Mock PDF document and page
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.page_count = 1
    mock_fitz_open.return_value = mock_doc
    
    # Mock images on page
    mock_page.get_images.return_value = [(123, 0, 200, 200, 8, "DeviceRGB", "", "img1", "FlateDecode")]
    mock_doc.extract_image.return_value = {
        "image": b"fake_image_bytes" * 500, # > 5000 bytes
        "width": 200,
        "height": 200,
        "ext": "png"
    }
    mock_page.get_text.return_value = "Page text"
    
    mock_desc.return_value = "A beautiful diagram about Monads."
    
    pdf_path = tmp_path / "test.pdf"
    pdf_path.touch()
    
    md_text, page_count = extract_pdf_to_markdown(pdf_path, config=mock_config)
    
    assert "![[images/test/img_p1_0.png]]" in md_text
    assert page_count == 1
    
    # Check if image was saved
    img_path = mock_config.images_dir / "test" / "img_p1_0.png"
    assert img_path.exists()
    assert img_path.read_bytes() == b"fake_image_bytes" * 500
    
    # Check if description was saved
    desc_path = img_path.with_suffix(".desc")
    assert desc_path.exists()
    assert desc_path.read_text() == "A beautiful diagram about Monads."


def test_chunking_with_images_and_descriptions(mock_config, tmp_path):
    # Setup markdown with image placeholder
    md_file = tmp_path / "test.md"
    long_text = "This is a long enough text to avoid being skipped during chunking. " * 10
    md_file.write_text(
        "### Seite 1\n"
        "![[images/test/img1.png]]\n"
        f"{long_text}",
        encoding="utf-8"
    )
    
    # Setup image and description on disk
    img_dir = mock_config.images_dir / "test"
    img_dir.mkdir(parents=True)
    (img_dir / "img1.png").touch()
    (img_dir / "img1.desc").write_text("Diagram showing a Functor.", encoding="utf-8")
    
    chunks = parse_markdown_to_chunks(md_file, config=mock_config)
    
    assert len(chunks) == 1
    assert "![[images/test/img1.png]]" in chunks[0].text
    assert "[BILD-BESCHREIBUNG: Diagram showing a Functor.]" in chunks[0].text
    assert chunks[0].image_paths == ["images/test/img1.png"]


@patch("knowledgebase.core.search.run_search")
@patch("knowledgebase.core.answer.make_openai_llm_client")
@patch("knowledgebase.config.get_openai_api_key")
def test_answer_includes_base64_images(mock_key, mock_llm_factory, mock_search, mock_config):
    mock_key.return_value = "fake-key"
    mock_llm = MagicMock()
    mock_llm.return_value = "The answer is Monads."
    mock_llm_factory.return_value = mock_llm
    
    # Mock search result with chunk containing images
    chunk = Chunk(
        text="[BILD-BESCHREIBUNG: A Monad diagram] Some text",
        book="Haskell",
        book_file="haskell.md",
        page=10,
        image_paths=["images/haskell/img1.png"]
    )
    from knowledgebase.models import SearchResult
    mock_search.return_value = [SearchResult(chunk=chunk, score=0.9)]
    
    # Setup image on disk
    img_path = mock_config.kb_dir / "images/haskell/img1.png"
    img_path.parent.mkdir(parents=True)
    img_path.write_bytes(b"dummy_bytes")
    
    answer = generate_answer("What are monads?", config=mock_config)
    
    assert answer.text == "The answer is Monads."
    assert "images/haskell/img1.png" in answer.images
    # Base64 of b"dummy_bytes" is "ZHVtbXlfYnl0ZXM="
    assert answer.images["images/haskell/img1.png"] == "ZHVtbXlfYnl0ZXM="
