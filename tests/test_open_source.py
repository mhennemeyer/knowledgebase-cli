"""Tests für knowledgebase.core.open_source."""
from unittest.mock import patch

import pytest

from knowledgebase.core.open_source import build_open_cmd, open_pdf


# --- build_open_cmd ---

def test_build_open_cmd_format():
    with patch("knowledgebase.core.open_source.shutil.which", return_value="/usr/bin/open"):
        cmd = build_open_cmd("/path/to/book.pdf", page=42)

    assert "Skim" in cmd
    assert "-page 42" in cmd
    assert "book.pdf" in cmd


def test_build_open_cmd_default_page():
    with patch("knowledgebase.core.open_source.shutil.which", return_value="/usr/bin/open"):
        cmd = build_open_cmd("/path/to/book.pdf")

    assert "-page 1" in cmd


def test_build_open_cmd_special_chars_in_path():
    with patch("knowledgebase.core.open_source.shutil.which", return_value="/usr/bin/open"):
        cmd = build_open_cmd("/path/to/My Book (2nd).pdf", page=10)

    assert "My Book (2nd).pdf" in cmd


def test_build_open_cmd_no_open_command():
    with patch("knowledgebase.core.open_source.shutil.which", return_value=None):
        cmd = build_open_cmd("/path/to/book.pdf", page=1)

    assert cmd == ""


# --- open_pdf ---

def test_open_pdf_calls_subprocess():
    with patch("knowledgebase.core.open_source.shutil.which", return_value="/usr/bin/open"), \
         patch("knowledgebase.core.open_source.subprocess.run") as mock_run:
        open_pdf("/path/to/book.pdf", page=5)

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert "book.pdf" in call_args[0][0]


def test_open_pdf_raises_when_open_unavailable():
    with patch("knowledgebase.core.open_source.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="nicht verfügbar"):
            open_pdf("/path/to/book.pdf")
