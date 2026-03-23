# Änderungslog

## 2026-03-21 – Phase 3: RAG, EPUB-Support & Tests

### Umgesetzte Schritte (Plan: plan-phase3-and-tests.md)

**Schritt 1: Tests für bestehenden Code**
- `tests/test_extract.py` – slugify, extract_toc, format_toc, extract_pdf_to_markdown, extract_all_pdfs
- `tests/test_chunk.py` – parse_markdown_to_chunks, build_all_chunks
- `tests/test_index.py` – get_embeddings, build_index, load_index
- `tests/test_search.py` – search, _resolve_pdf_path
- `tests/test_open_source.py` – build_open_cmd, open_pdf
- `tests/test_cli.py` – Smoke-Tests für alle Subcommands (init, search, ask, list, status, open)

**Schritt 2: Extraktions-Abstraktion & EPUB-Support**
- `models.py`: `Chunk` um optionales `chapter_title: str | None` erweitert
- `core/extract.py`: Refactored – `extract_epub_to_markdown`, `get_extractor` Factory, `extract_all_books` (PDF + EPUB), `extract_all_pdfs` als Legacy-Wrapper
- `core/chunk.py`: `SECTION_PATTERN` für Seiten- und Kapitel-Referenzen, `chapter_title` wird durchgereicht
- `pyproject.toml` + `requirements.txt`: `ebooklib>=0.18`, `beautifulsoup4>=4.12` ergänzt
- `tests/test_extract_epub.py` – Factory, EPUB-Extraktion, mixed-format Batch, Kapitel-Chunk-Integration

**Schritt 3: RAG-Antwortgenerierung (Phase 3)**
- `core/answer.py`: `build_system_prompt`, `build_user_prompt`, `make_openai_llm_client` (Closure/DI), `generate_answer`
- `cli.py`: `kb ask` vollständig implementiert (Human-readable + JSON Output, `--book` Filter, `--name` KB-Auswahl)
- `tests/test_answer.py` – Prompt-Generierung, DI, Answer-Parsing, Quellenangaben

**Schritt 4: CLI-Vereinfachung**
- `kb init` zeigt jetzt Format-Info (PDF/EPUB) an
- `kb search` zeigt Kapitel-Titel bei EPUB-Ergebnissen
- `kb ask` mit `--json` liefert `answer` + `sources`

**Schritt 5: Dokumentation**
- `README.md` aktualisiert: EPUB-Support, `kb ask`, Roadmap, Architecture, Tech Stack

### Getroffene Entscheidungen
- EPUB-Support via `ebooklib` + `beautifulsoup4`
- Chunk-Location: `page`-Feld beibehalten (EPUB = Kapitelnummer), `chapter_title` optional
- LLM-Client als `Callable` injiziert (Higher-Order Function / Closure)
- Prompt: System-Prompt + User-Prompt mit nummerierten Kontext-Chunks
- JSON-Output: `answer` + `sources` bei `kb ask --json`

### Testabdeckung
67 Tests, alle bestanden.
