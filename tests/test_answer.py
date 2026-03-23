"""Tests für knowledgebase.core.answer – RAG-Antwortgenerierung."""
from unittest.mock import MagicMock, patch

import pytest

from knowledgebase.core.answer import (
    build_system_prompt,
    build_user_prompt,
    generate_answer,
)
from knowledgebase.config import KBConfig
from knowledgebase.models import Answer, Chunk, SearchResult


# --- build_system_prompt ---

def test_build_system_prompt():
    prompt = build_system_prompt()
    assert "Fachexperte" in prompt
    assert "[Quelle N]" in prompt


# --- build_user_prompt ---

def _make_results(count: int = 2) -> list[SearchResult]:
    return [
        SearchResult(
            chunk=Chunk(
                text=f"Text of chunk {i}",
                book=f"Book {i}",
                book_file=f"book-{i}.md",
                page=i * 10,
                chunk_id=i,
            ),
            score=0.9 - i * 0.1,
            open_cmd="",
        )
        for i in range(1, count + 1)
    ]


def test_build_user_prompt_contains_question():
    results = _make_results(1)
    prompt = build_user_prompt("Was sind Monaden?", results)
    assert "Was sind Monaden?" in prompt


def test_build_user_prompt_contains_numbered_sources():
    results = _make_results(3)
    prompt = build_user_prompt("Frage", results)
    assert "[Quelle 1]" in prompt
    assert "[Quelle 2]" in prompt
    assert "[Quelle 3]" in prompt


def test_build_user_prompt_shows_page_reference():
    results = _make_results(1)
    prompt = build_user_prompt("Frage", results)
    assert "Seite 10" in prompt
    assert "Book 1" in prompt


def test_build_user_prompt_shows_chapter_reference():
    results = [
        SearchResult(
            chunk=Chunk(
                text="EPUB content",
                book="EPUB Book",
                book_file="epub.md",
                page=1,
                chunk_id=0,
                chapter_title="Monads Explained",
            ),
            score=0.9,
            open_cmd="",
        ),
    ]
    prompt = build_user_prompt("Frage", results)
    assert "Kapitel: Monads Explained" in prompt


# --- generate_answer ---

def test_generate_answer_with_mock_llm():
    mock_results = _make_results(2)

    def mock_llm(system_prompt: str, user_prompt: str) -> str:
        return "Monaden sind ein Designpattern [Quelle 1]."

    with patch("knowledgebase.core.search.run_search", return_value=mock_results):
        answer = generate_answer(
            question="Was sind Monaden?",
            config=KBConfig(name="test"),
            llm_client=mock_llm,
        )

    assert isinstance(answer, Answer)
    assert "Monaden" in answer.text
    assert "[Quelle 1]" in answer.text
    assert len(answer.sources) == 2


def test_generate_answer_no_results():
    with patch("knowledgebase.core.search.run_search", return_value=[]):
        answer = generate_answer(
            question="Nonsense query",
            config=KBConfig(name="test"),
            llm_client=lambda s, u: "Should not be called",
        )

    assert "Keine relevanten Quellen" in answer.text
    assert answer.sources == []


def test_generate_answer_creates_client_when_none():
    mock_results = _make_results(1)

    with patch("knowledgebase.core.search.run_search", return_value=mock_results), \
         patch("knowledgebase.config.get_openai_api_key", return_value="fake-key"), \
         patch("knowledgebase.core.answer.make_openai_llm_client") as mock_make:
        mock_make.return_value = lambda s, u: "Auto-created client answer"
        answer = generate_answer(
            question="Test",
            config=KBConfig(name="test"),
            llm_client=None,
        )

    mock_make.assert_called_once()
    assert answer.text == "Auto-created client answer"
