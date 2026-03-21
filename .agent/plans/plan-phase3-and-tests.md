# Plan: Nächste Schritte – Phase 3 (RAG), Tests & E-Book-Formate

## Ist-Zustand (Analyse 2026-03-21)

### Implementiert (Phase 1 + 2)
- **extract.py** – PDF → Markdown mit Seitenreferenzen (PyMuPDF), TOC-Extraktion
- **chunk.py** – Markdown → Chunks mit konfigurierbarem Size/Overlap, Seitenreferenz-Parsing
- **index.py** – FAISS-Index (IndexFlatIP + L2-Normalisierung = Cosine Similarity), OpenAI Embeddings, Batch-Verarbeitung, Chunk-Metadaten als JSON
- **search.py** – Semantische Suche mit Buch-Filter, PDF-Pfad-Auflösung über Slug-Matching, Open-Cmd-Generierung
- **open_source.py** – macOS PDF-Öffnung via Skim mit Seitenangabe
- **config.py** – `KBConfig` Dataclass mit Properties für Pfade (`~/.kb/<name>/`)
- **models.py** – Frozen Dataclasses: `Chunk`, `SearchResult`, `Answer`
- **cli.py** – Typer CLI mit `init`, `search`, `list`, `status`, `open`; `ask` ist Stub
- **pyproject.toml** – Entry Point `kb = knowledgebase.cli:main`

### Nicht implementiert / Fehlend
1. **Keine Tests vorhanden** – `tests/` enthält nur `__init__.py`
2. **`core/answer.py`** fehlt – RAG-Antwortgenerierung (Phase 3)
3. **`kb ask`** – CLI-Subcommand ist nur Platzhalter
4. **EPUB-Support** fehlt – Extraktion ausschließlich für PDF
5. **Phase 4** – Multi-KB (`--name` Parameter existiert bereits in CLI), `kb add`, `kb rebuild`, `kb config`, Config-Datei

### Architektur-Beobachtungen
- **Ports & Adapters** teilweise umgesetzt: OpenAI-Client wird direkt in `index.py` und `search.py` instanziiert (kein Dependency Injection / Port-Abstraktion)
- **`book_file`** speichert den Markdown-Dateinamen (nicht den PDF-Namen), was die Rück-Auflösung in `search.py._resolve_pdf_path` über Slug-Matching erfordert
- **Keine Fehlerbehandlung** bei API-Fehlern (Rate Limits, Timeouts)
- **`Answer`-Dataclass** in `models.py` bereits definiert, aber nirgends verwendet

---

## Entscheidung: E-Book-Format

### Analyse

| Kriterium | PDF | EPUB |
|---|---|---|
| **Textqualität** | Variabel – Layout-basiert, Spalten/Header/Footer vermischt, Bindestriche bei Zeilenumbrüchen | Hervorragend – strukturierter Fließtext (XHTML), saubere Absätze |
| **Struktur (TOC, Kapitel)** | TOC oft vorhanden (via Bookmarks), aber Kapitelgrenzen unzuverlässig | Nativ strukturiert – `toc.ncx`/`nav.xhtml`, XHTML-Kapitel-Dateien |
| **Seitenreferenzen** | Echte Seitenzahlen vorhanden | Keine physischen Seiten – nur Positionen/Kapitel (manche EPUBs haben `pageList`) |
| **Verfügbarkeit** | Sehr verbreitet (Fachbücher, Papers, Scans) | Verbreitet bei Belletristik; Fachbücher oft nur als PDF |
| **Bibliothek (Python)** | PyMuPDF (`fitz`) – robust, schnell | `ebooklib` – liest EPUB3, gibt XHTML-Kapitel zurück |
| **Öffnen auf Seite** | Direkt möglich (`open -a Preview --args -p 42`) | Nicht trivial – kein universeller Deep-Link zu Position |
| **RAG-Eignung** | Gut, wenn Extraktion sauber | Sehr gut – sauberer Text, natürliche Chunk-Grenzen an Kapiteln |

### Empfehlung: Beide Formate unterstützen, EPUB bevorzugen

**Begründung:**
- EPUB liefert saubereren Text und bessere Chunk-Qualität → bessere RAG-Ergebnisse
- PDF bleibt wichtig, weil viele Fachbücher/Papers nur als PDF vorliegen
- Der Aufwand für EPUB-Support ist gering (ein zusätzlicher Extraktor, ~60 Zeilen)
- Die bestehende Pipeline (Markdown → Chunk → Index → Search) bleibt unverändert – nur der Einstieg (Extraktion) wird abstrahiert

**Quellenreferenz-Strategie:**
- PDF: Seitenzahl (wie bisher)
- EPUB: Kapitel-Titel + Position innerhalb des Kapitels (z.B. "Kapitel 3: Monaden, Abschnitt 2")
- `open_cmd` bei EPUB: Datei öffnen ohne Seitenangabe (oder Kapitel-basierter Deep-Link, falls Reader das unterstützt)

**Format-Erkennung:** Automatisch via Dateiendung (`.pdf` / `.epub`). Der `kb init`-Befehl verarbeitet alle erkannten Formate im Quellverzeichnis.

---

## Plan: Schritte

### Schritt 1: Tests für bestehenden Code (Phase 1+2)

Gemäß `rules.md`: „Schreibe aussagekräftige Tests mit Assertions für den gesamten Code."

#### 1.1 `tests/test_extract.py`
- `slugify`: Sonderzeichen, Leerzeichen, Mehrfach-Bindestriche
- `extract_toc`: Leeres TOC, Mehrstufiges TOC
- `format_toc`: Formatierung, leere Eingabe
- `extract_pdf_to_markdown`: Seitenreferenzen im Output, Page-Count
- `extract_all_pdfs`: Verzeichnis ohne PDFs, normaler Ablauf (Mock für PyMuPDF)

#### 1.2 `tests/test_chunk.py`
- `parse_markdown_to_chunks`: Einfache Seite, große Seite mit Overlap-Splitting, kurze Seiten (< 50 Zeichen) werden übersprungen
- `build_all_chunks`: Globale ID-Vergabe, leeres Verzeichnis

#### 1.3 `tests/test_index.py`
- `get_embeddings`: Batch-Verarbeitung (Mock für OpenAI)
- `build_index`: Index-Erstellung + Dateien werden geschrieben
- `load_index`: Laden von Index + Chunks, Fehler bei fehlenden Dateien

#### 1.4 `tests/test_search.py`
- `search`: Ergebnisse mit korrektem Score, Buch-Filter, Open-Cmd
- `_resolve_pdf_path`: Slug-Matching, fehlendes PDF-Dir

#### 1.5 `tests/test_open_source.py`
- `build_open_cmd`: Korrekte Kommando-Formatierung, Sonderzeichen in Pfaden
- `open_pdf`: Fehler wenn `open` nicht verfügbar

#### 1.6 `tests/test_cli.py`
- Typer-Test-Client für alle Subcommands
- Smoke-Tests mit Mocks für externe Abhängigkeiten

### Schritt 2: Extraktions-Abstraktion & EPUB-Support

#### 2.1 Extraktor-Port (Abstraktion)
- **`core/extract.py`** refactoren: Gemeinsame Signatur `extract_book(path: Path) -> tuple[str, BookMeta]` als Port definieren
- `BookMeta`-Dataclass in `models.py`: `title`, `filename`, `page_count`, `format` (pdf/epub)
- Factory-Funktion `get_extractor(path: Path) -> Callable` die anhand der Dateiendung den passenden Extraktor zurückgibt
- `extract_all_books(config)` statt `extract_all_pdfs(config)` – verarbeitet `.pdf` und `.epub`

#### 2.2 EPUB-Extraktor
- **`core/extract_epub.py`** – EPUB → Markdown mit Kapitelreferenzen
- Bibliothek: `ebooklib` + `beautifulsoup4` (XHTML → Text)
- Kapitel-basierte Seitenreferenzen: `### Kapitel: <titel>` statt `### Seite <n>`
- TOC-Extraktion aus `toc.ncx` / `nav.xhtml`
- `requirements.txt` und `pyproject.toml` erweitern

#### 2.3 Chunk-Anpassung
- `chunk.py` erweitern: Kapitel-Referenzen (`### Kapitel:`) neben Seiten-Referenzen (`### Seite`) erkennen
- **Entscheidung Chunk-Location-Modell**: `page`-Feld beibehalten (bei EPUB = Kapitelnummer), optionales `chapter_title: str | None`-Feld in `Chunk`-Dataclass ergänzen. Minimaler Breaking Change, bestehender Code (search.py, cli.py) funktioniert weiterhin über `page`.

#### 2.4 Tests für EPUB-Extraktion
- `tests/test_extract_epub.py`: Kapitel-Extraktion, TOC, leeres EPUB
- `tests/test_extract.py` erweitern: `get_extractor` Factory, gemischte Verzeichnisse

### Schritt 3: `core/answer.py` – RAG-Antwortgenerierung (Phase 3)

#### 3.1 Architektur
```
Frage → search (top_k Chunks) → Prompt bauen → LLM (GPT-4o-mini) → Answer mit Quellen
```

#### 3.2 Implementierung
- **`build_rag_prompt(question, chunks)`** – System-Prompt mit klarer Rollenanweisung + User-Prompt mit Kontext-Chunks und Quellenangaben (Buch + Seite/Kapitel)
- **`generate_answer(question, config, top_k, llm_client)`** – Orchestrierung: Search → Prompt → LLM → Answer-Objekt
- **Entscheidung Prompt-Format**: System-Prompt mit Rollenanweisung ("Du bist ein Fachexperte...") + User-Prompt mit nummerierten Kontext-Chunks inkl. Quellenangaben. Quellenreferenzen im Antwortformat erzwingen.
- **Entscheidung Dependency Injection**: OpenAI-Client wird als `Callable`-Parameter injiziert (Higher-Order Function gemäß `functional.md`). Gilt für `generate_answer` (LLM) sowie bestehende Funktionen in `index.py` und `search.py` (Embedding-Client). Refactoring der direkten Instanziierung erfolgt in Schritt 2.1 (Extraktor-Port) bzw. Schritt 3.
- Konfigurierbare Modellparameter (Temperature, Max-Tokens) über `KBConfig`

#### 3.3 CLI-Integration
- `kb ask` in `cli.py` mit echtem Code verbinden
- **Entscheidung JSON-Output**: `kb ask --json` liefert `answer` (Antworttext) + `sources` (Liste der verwendeten Quellen mit Buch, Seite/Kapitel, Score, open_cmd) – konsistent mit `Answer`-Dataclass in `models.py`
- Human-readable Output mit Antworttext + nummerierter Quellenliste

#### 3.4 Tests
- `tests/test_answer.py`: Prompt-Generierung, Answer-Parsing, Quellenangaben
- Mock für OpenAI Chat-Completion

### Schritt 4: CLI-Vereinfachung für systemweite Nutzung

Das Kernziel: Knowledgebases mit **einem einzigen CLI-Befehl** erstellen/aktualisieren und abfragen.

#### 4.1 `kb init` vereinfachen
- `kb init ~/Books` – erstellt/aktualisiert die Default-KB aus dem E-Book-Ordner
- `kb init ~/Books --name dev` – benannte KB
- Automatische Erkennung: neue/geänderte Bücher werden hinzugefügt, fehlende entfernt (inkrementelles Update)
- Fortschrittsanzeige pro Buch

#### 4.2 `kb ask` als primärer Befehl
- `kb ask "Was sind Monaden?"` – direkte Antwort mit Quellen
- `kb ask "..." --json` – maschinenlesbar für Agent-Integration
- `kb ask "..." --name dev` – spezifische KB abfragen

#### 4.3 Systemweite Verfügbarkeit
- `pip install -e .` macht `kb` überall verfügbar (bereits implementiert)
- Dokumentation in README.md aktualisieren mit EPUB-Support und `kb ask`

### Schritt 5: Empfohlene Reihenfolge der Umsetzung

1. **Tests schreiben** (Schritt 1) – sichert bestehenden Code ab
2. **Extraktions-Abstraktion** (Schritt 2.1) – Refactoring mit Testnetz
3. **EPUB-Extraktor** (Schritt 2.2 + 2.3 + 2.4) – neues Format
4. **`core/answer.py`** implementieren (Schritt 3.2)
5. **Tests für answer.py** (Schritt 3.4)
6. **CLI-Integration** von `kb ask` (Schritt 3.3)
7. **CLI-Vereinfachung** (Schritt 4) – inkrementelles Update, Doku
8. **`log.md` aktualisieren**, README.md erweitern

---

## Getroffene Entscheidungen (ehemals offene Fragen)

| Frage | Entscheidung | Eingearbeitet in |
|---|---|---|
| **Chunk-Location-Modell** | `page`-Feld beibehalten (EPUB = Kapitelnummer), optionales `chapter_title`-Feld ergänzen. Minimaler Breaking Change. | Schritt 2.3 |
| **Dependency Injection für OpenAI-Client** | Ja – als `Callable`-Parameter (Higher-Order Function gemäß `functional.md`). Gilt für LLM-Client und Embedding-Client. | Schritt 3.2 |
| **Prompt-Format für RAG** | System-Prompt mit klarer Rollenanweisung + User-Prompt mit nummerierten Kontext-Chunks inkl. Quellenangaben. | Schritt 3.2 |
| **JSON-Output bei `kb ask --json`** | Beides: `answer` + `sources` – konsistent mit `Answer`-Dataclass. | Schritt 3.3 |
