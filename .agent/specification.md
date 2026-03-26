# Knowledgebase – Spezifikation

## Vision

Eine ubiquitär auf dem Rechner verfügbare, CLI-basierte Knowledgebase (KB) für E-Books (PDFs & EPUBs).
Zielgruppen: Mensch (Terminal) und KI-Agent (programmatischer Zugriff).

**Kernfähigkeiten:**
- Semantische Suche über alle indizierten Bücher
- RAG-Antworten mit exakten Quellenangaben (Buch, Seite/Kapitel)
- Vision AI – Bilder aus Büchern extrahieren, beschreiben und indexieren
- Deep-Link zum Öffnen des PDFs auf der richtigen Seite (Skim)
- Unix-artiges CLI mit Pipes, JSON-Output, Filtern
- Mehrere unabhängige Knowledgebases möglich (z. B. `--name fp`, `--name cat`)
- PDF- und EPUB-Support mit automatischer Format-Erkennung

## Architektur

```
knowledgebase/
├── cli.py                  # Typer CLI Entry Point (kb)
├── config.py               # KBConfig Dataclass (Pfade, Modelle, Vision-Flag)
├── models.py               # Frozen Dataclasses: Chunk, SearchResult, Answer
├── core/
│   ├── __init__.py
│   ├── extract.py          # PDF/EPUB → Markdown mit Seiten-/Kapitelreferenzen + Vision-Bildextraktion
│   ├── chunk.py            # Markdown → Chunks mit Metadaten (Seite, Kapitel, Bilder)
│   ├── index.py            # FAISS-Index bauen, laden, speichern (OpenAI Embeddings)
│   ├── search.py           # Semantische Suche mit Buch-Filter
│   ├── answer.py           # RAG: Frage → Antwort + Quellen + Bilder (LLM)
│   ├── vision.py           # Vision AI: Bildbeschreibung via GPT-4o, Base64-Encoding
│   └── open_source.py      # PDF auf Seite öffnen (macOS Skim)
├── tests/
│   ├── conftest.py         # Shared Fixtures (Fake-Embeddings, Test-PDF/EPUB-Generatoren)
│   ├── test_extract.py
│   ├── test_extract_epub.py
│   ├── test_chunk.py
│   ├── test_index.py
│   ├── test_search.py
│   ├── test_answer.py
│   ├── test_open_source.py
│   ├── test_cli.py
│   ├── test_e2e_pipeline.py  # Stufe-1 E2E-Tests (Pipeline ohne externe APIs)
│   ├── test_e2e_add.py       # E2E-Tests für kb add
│   └── test_vision_feature.py
├── pyproject.toml           # Projekt-Metadaten, CLI Entry Point
├── requirements.txt
└── README.md
```

### Ports & Adapters

- **Port (Eingang):** CLI (`kb`-Kommando), Python-API
- **Port (Ausgang):** Embedding-Provider (OpenAI), LLM-Provider (OpenAI), Vision AI (GPT-4o), Dateisystem
- **Adapter:** OpenAI-Client (Embedding + LLM + Vision), FAISS, PyMuPDF, ebooklib, macOS `open`-Kommando
- **Dependency Injection:** LLM-Client als Callable injiziert (Higher-Order Function gemäß functional.md)

## CLI Design

```bash
# Knowledgebase initialisieren / Bücher indizieren
kb init ~/Books                          # PDFs/EPUBs extrahieren + Index bauen (mit Vision)
kb init ~/Books --name dev               # Benannte KB erstellen
kb init ~/Books --no-vision              # Ohne Vision-Analyse (spart Kosten/Zeit)
kb init ~/Books --base-dir /custom/path  # Eigenes Basis-Verzeichnis

# Einzelne Bücher hinzufügen
kb add ~/Books/new-book.pdf              # Einzelnes Buch hinzufügen
kb add ~/Books/new-books/ --name dev     # Verzeichnis zu benannter KB hinzufügen
kb add ~/Books/book.epub --no-vision     # Ohne Vision-Analyse

# Suche (semantisch)
kb search "functor laws"                 # Top-10 relevante Passagen
kb search "monad tutorial" --top 20      # Mehr Ergebnisse
kb search "clean code" --book "Clean-Code"  # Buch-Filter
kb search "category theory" --json       # JSON-Output für Piping/Agent

# Fragen (RAG – Antwort + Quellen + Bilder)
kb ask "Was sind die Funktor-Gesetze?"
kb ask "Erkläre Monaden" --json          # Strukturierte Antwort für Agent
kb ask "clean code" --name arch          # Spezifische KB abfragen

# Quelle öffnen
kb open "Clean-Code.pdf" --page 42       # PDF auf Seite 42 öffnen

# Verwaltung
kb list                                  # Alle indizierten Bücher anzeigen
kb list --name fp                        # Bücher einer benannten KB
kb status                                # Index-Statistiken
kb status --name fp                      # Status einer benannten KB
```

### JSON-Output (für KI-Agent)

#### `kb ask --json`
```json
{
  "answer": "Monads are a design pattern...",
  "sources": [
    {
      "book": "Category Theory For Programmers",
      "page": 42,
      "chapter_title": null,
      "score": 0.89,
      "open_cmd": "open -a Skim '~/Books/CategoryTheoryForProgrammers.pdf' --args -page 42"
    }
  ],
  "images": {
    "images/categorytheoryforprogrammers/img_p42_0.png": "<base64>"
  }
}
```

#### `kb search --json`
```json
{
  "query": "functor laws",
  "results": [
    {
      "text": "A functor must preserve identity and composition...",
      "book": "Category Theory For Programmers",
      "book_file": "categorytheoryforprogrammers.md",
      "page": 42,
      "chapter_title": null,
      "score": 0.89,
      "open_cmd": "open -a Skim '~/Books/CategoryTheoryForProgrammers.pdf' --args -page 42"
    }
  ]
}
```

## Datenmodell

```python
@dataclass(frozen=True)
class Chunk:
    text: str
    book: str              # Lesbarer Buchtitel
    book_file: str         # Original Dateiname
    page: int              # Seitenzahl (PDF) oder Kapitelnummer (EPUB)
    chunk_id: int = 0      # Eindeutige ID im Index
    chapter_title: str | None = None  # Optionaler Kapitel-Titel (v.a. bei EPUB)
    image_paths: list[str] = field(default_factory=list)  # Relative Pfade zu Bildern

@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
    open_cmd: str = ""     # macOS-Kommando zum Öffnen

@dataclass(frozen=True)
class Answer:
    text: str              # Fachliche Antwort
    sources: list[SearchResult] = field(default_factory=list)
    images: dict[str, str] = field(default_factory=dict)  # Pfad -> Base64
```

## Implementierungsstand

### Abgeschlossen ✅

- **Phase 1 – Core Pipeline:** extract (PDF+EPUB), chunk, index (FAISS + OpenAI Embeddings), search, open_source
- **Phase 2 – CLI:** Typer-basiertes CLI mit allen Subcommands (init, search, ask, add, list, status, open)
- **Phase 3 – RAG:** answer.py mit LLM-basierter Antwortgenerierung, Quellenangaben, DI via Higher-Order Functions
- **EPUB-Support:** Extraktions-Abstraktion mit automatischer Format-Erkennung, EPUB-Extraktor mit Kapitelreferenzen
- **Vision AI:** Bildextraktion aus PDFs/EPUBs, GPT-4o Vision-Beschreibung, Indexierung, Base64 in RAG-Antworten
- **Multi-KB:** Benannte Knowledgebases (`--name`), eigenes Basis-Verzeichnis (`--base-dir`)
- **Inkrementelle Updates:** `kb add` für einzelne Bücher oder Verzeichnisse
- **Model-Upgrades:** text-embedding-3-large (3072d), GPT-4o, top_k=10
- **Tests:** Unit-Tests für alle Module + E2E-Pipeline-Tests mit programmatischen Fixtures
- **LambdaPy-Migration:** 4 thematische KBs (fp, cat, arch, ai) aus 43 Büchern

### Offen

- Konfigurationsdatei (`~/Knowledgebase/config.toml`)
- `kb rebuild` – Index komplett neu aufbauen
- `kb config` – Konfiguration anzeigen/bearbeiten
- API-Integration-E2E-Tests (Stufe 2 mit echtem API-Key)
- CLI-Subprocess-E2E-Tests (Stufe 3)

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python ≥ 3.11 |
| PDF-Extraktion | PyMuPDF (fitz) |
| EPUB-Extraktion | ebooklib + BeautifulSoup4 |
| Embeddings | OpenAI text-embedding-3-large (3072d) |
| Vektor-Index | FAISS (faiss-cpu), IndexFlatIP |
| LLM (RAG) | OpenAI GPT-4o |
| Vision AI | OpenAI GPT-4o Vision |
| CLI-Framework | Typer |
| Tests | pytest |
| Paketierung | pyproject.toml + pip install -e . |

## Herkunft

Basiert auf der Knowledgebase-Implementierung im LambdaPy-Projekt:
- `knowledgebase/extract_pdfs.py` → `core/extract.py`
- `knowledgebase/build_index.py` → `core/chunk.py` + `core/index.py`
- `knowledgebase/search.py` → `core/search.py`

Verallgemeinerungen gegenüber LambdaPy:
- PDF- und EPUB-Support mit automatischer Format-Erkennung
- Vision AI für Bilder in Büchern
- Konfigurierbare Pfade und benannte KBs
- CLI statt einzelner Skripte
- RAG-Antwortgenerierung mit Quellenangaben und Bildern
- Systemweite Installation via `pip install -e .`
