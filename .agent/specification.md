# Knowledgebase – Spezifikation

## Vision

Eine ubiquitär auf dem Rechner verfügbare, CLI-basierte Knowledgebase (KB) für E-Books (PDFs).
Zielgruppen: Mensch (Terminal) und KI-Agent (programmatischer Zugriff).

**Kernfähigkeiten:**
- Semantische Suche über alle indizierten Bücher
- Fachliche Antworten mit exakten Quellenangaben (Buch, Seite)
- Deep-Link zum Öffnen des PDFs auf der richtigen Seite (`open` / Preview.app)
- Unix-artiges CLI mit Pipes, JSON-Output, Filtern
- Mehrere unabhängige Knowledgebases möglich (z. B. "dev", "math", "personal")

## Architektur

```
knowledgebase/
├── cli.py                  # Haupt-CLI Entry Point (kb)
├── core/
│   ├── __init__.py
│   ├── extract.py          # PDF → Markdown mit Seitenreferenzen
│   ├── chunk.py            # Markdown → Chunks mit Metadaten
│   ├── index.py            # FAISS-Index bauen & verwalten
│   ├── search.py           # Semantische Suche
│   ├── answer.py           # RAG: Frage → Antwort + Quellen (LLM)
│   └── open_source.py      # PDF auf Seite öffnen (macOS open -a Preview)
├── config.py               # Konfiguration (Pfade, Modelle, API-Keys)
├── models.py               # Datenklassen (Chunk, SearchResult, Source)
├── tests/
│   ├── test_extract.py
│   ├── test_chunk.py
│   ├── test_search.py
│   └── test_cli.py
├── .agent/
│   └── specification.md    # Diese Datei
├── pyproject.toml           # Projekt-Metadaten, CLI Entry Point
├── requirements.txt
└── README.md
```

### Ports & Adapters

- **Port (Eingang):** CLI (`kb`-Kommando), Python-API
- **Port (Ausgang):** Embedding-Provider (OpenAI), LLM-Provider (OpenAI), Dateisystem
- **Adapter:** OpenAI-Client, FAISS, PyMuPDF, macOS `open`-Kommando

## CLI Design

```bash
# Knowledgebase initialisieren / PDFs indizieren
kb init ~/Books                     # PDFs extrahieren + Index bauen
kb init ~/Books --name dev          # Benannte KB erstellen
kb add ~/Books/new-book.pdf         # Einzelnes Buch hinzufügen
kb list                             # Alle indizierten Bücher anzeigen

# Suche (semantisch)
kb search "functor laws"            # Top-5 relevante Passagen
kb search "monad tutorial" -n 10    # Mehr Ergebnisse
kb search "clean code" --book "Clean-Code"  # Buch-Filter
kb search "category theory" --json  # JSON-Output für Piping/Agent

# Fragen (RAG – Antwort + Quellen)
kb ask "Was sind die Funktor-Gesetze?"
kb ask "Erkläre Monaden" --json     # Strukturierte Antwort für Agent

# Quelle öffnen
kb open "Clean-Code.pdf" --page 42  # PDF auf Seite 42 öffnen
kb open --result 1                  # Letztes Suchergebnis #1 öffnen

# Verwaltung
kb status                           # Index-Statistiken
kb rebuild                          # Index neu aufbauen
kb config                           # Konfiguration anzeigen
```

### JSON-Output (für KI-Agent)

```json
{
  "query": "functor laws",
  "results": [
    {
      "text": "A functor must preserve identity and composition...",
      "book": "Category Theory For Programmers",
      "book_file": "CategoryTheoryForProgrammers.pdf",
      "page": 42,
      "score": 0.89,
      "open_cmd": "open -a Preview 'CategoryTheoryForProgrammers.pdf' --args -p 42"
    }
  ]
}
```

## Datenmodell

```python
@dataclass(frozen=True)
class Chunk:
    text: str
    book: str           # Lesbarer Buchtitel
    book_file: str      # Original PDF-Dateiname
    page: int           # Seitenzahl im PDF
    chunk_id: int       # Eindeutige ID im Index

@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
    open_cmd: str       # macOS-Kommando zum Öffnen

@dataclass(frozen=True)
class Answer:
    text: str           # Fachliche Antwort
    sources: list[SearchResult]  # Verwendete Quellen
```

## Implementierungsplan

### Phase 1 – Core Pipeline (MVP)
1. **Projektstruktur** aufsetzen (`pyproject.toml`, `requirements.txt`, Verzeichnisse)
2. **config.py** – Konfiguration: PDF-Verzeichnis, Index-Verzeichnis, API-Key, Modelle
3. **models.py** – Datenklassen `Chunk`, `SearchResult`, `Answer`
4. **core/extract.py** – PDF → Markdown (aus LambdaPy portiert, verallgemeinert)
5. **core/chunk.py** – Markdown → Chunks mit Metadaten
6. **core/index.py** – FAISS-Index bauen, laden, speichern
7. **core/search.py** – Semantische Suche mit Filtern
8. **core/open_source.py** – `open -a Preview <pdf> --args -p <page>` 
9. **Tests** für alle Core-Module

### Phase 2 – CLI
10. **cli.py** – Click/Typer-basiertes CLI mit allen Subcommands
11. **pyproject.toml** – `[project.scripts] kb = "knowledgebase.cli:app"` Entry Point
12. **Installation** – `pip install -e .` → `kb` systemweit verfügbar

### Phase 3 – RAG (Frage-Antwort)
13. **core/answer.py** – LLM-basierte Antwortgenerierung mit Quellenangabe
14. **`kb ask`** Subcommand

### Phase 4 – Multi-KB & Erweiterungen
15. Mehrere benannte Knowledgebases (`--name`)
16. Inkrementelles Hinzufügen (`kb add`)
17. Konfigurationsdatei (`~/.kb/config.toml`)

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python ≥ 3.11 |
| PDF-Extraktion | PyMuPDF (fitz) |
| Embeddings | OpenAI text-embedding-3-small |
| Vektor-Index | FAISS (faiss-cpu) |
| LLM (RAG) | OpenAI GPT-4o-mini |
| CLI-Framework | Typer (oder Click) |
| Tests | pytest |
| Paketierung | pyproject.toml + pip install -e . |

## Herkunft

Basiert auf der Knowledgebase-Implementierung im LambdaPy-Projekt:
- `knowledgebase/extract_pdfs.py` → `core/extract.py`
- `knowledgebase/build_index.py` → `core/chunk.py` + `core/index.py`
- `knowledgebase/search.py` → `core/search.py`

Verallgemeinerungen gegenüber LambdaPy:
- Konfigurierbare Pfade (nicht hardcoded)
- CLI statt einzelner Skripte
- Deep-Links zum PDF-Öffnen
- RAG-Antwortgenerierung
- Multi-KB-Support
- Systemweite Installation via `pip install -e .`
