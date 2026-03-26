# Plan: LambdaPy KB-Migration auf Knowledgebase-Projekt

**Ziel**: Die lokale KB-Implementierung in LambdaPy (extract_pdfs.py, build_index.py, search.py) durch das Knowledgebase-Projekt ersetzen.

**Status**: Entscheidungen getroffen, bereit zur Umsetzung.

---

## 0. Entscheidungen (ehemals offene Fragen)

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Unterordner vs. Filter? | **Unterordner** – Bücher physisch in thematische Unterordner sortieren. KBs ebenfalls in Unterordnern speichern (nicht in `~/.kb/`). |
| 2 | domain-modeling → fp oder arch? | **fp** – Das Buch ist stark FP-orientiert. |
| 3 | Eine große KB vs. mehrere kleine? | **Mehrere kleine KBs**, die noch erweitert werden können. |
| 4 | Agent-Integration: CLI oder Python-Import? | **CLI** – global verfügbar. Nutzungs-Info in `~/.agent/rules.md` aufnehmen, damit alle Agent-Instanzen die KBs nutzen können. |
| 5 | Bestehende Artikel? | **Belassen** – Keine Änderungen an bestehenden Artikeln, da diese teilweise manuell bearbeitet wurden. |

---

## 1. Ist-Analyse

### LambdaPy KB (aktuell)
| Aspekt | Details |
|---|---|
| **Pipeline** | `extract_pdfs.py` → `markdown/` → `build_index.py` → `data/faiss.index` + `data/chunks.json` |
| **Bücher** | 20 PDFs in `resources/books/` (5.588 Seiten) |
| **Chunks** | 8.961 Chunks mit Keys: `{text, book, book_file, page}` |
| **Embedding** | `text-embedding-3-small` (1536 Dimensionen) |
| **Index** | FAISS `IndexFlatIP`, Brute-Force |
| **Suche** | `search.py` mit CLI (argparse): `python search.py "query" --top 5 --book X` |
| **Nutzung** | AI-Agent nutzt KB als Recherche-Tool beim Artikel-Schreiben; Zitate mit Buch+Seite |
| **Kein `ask`** | Es gibt keine Antwort-Generierung, nur Suche → der Agent synthetisiert selbst |

### Knowledgebase-Projekt (neu)
| Aspekt | Details |
|---|---|
| **Pipeline** | `extract.py` → `markdown/` → `chunk.py` → `index.py` → `<kb-dir>/data/` |
| **Embedding** | `text-embedding-3-large` (3072 Dimensionen) |
| **LLM** | `gpt-4o` (für `kb ask`) |
| **Index** | FAISS `IndexFlatIP` |
| **Chunks** | `{text, book, book_file, page, chunk_id, chapter_title}` |
| **CLI** | `kb init`, `kb search`, `kb ask`, `kb list`, `kb open` (typer) |
| **Installierbar** | `pip install -e .` → `kb` CLI-Kommando |
| **Named KBs** | `--name fp` → `~/.kb/fp/` |

---

## 2. Thematische Aufteilung der 20 Bücher

### KB `fp` – Functional Programming (8 Bücher)
- Functional-Anthology.pdf
- Functional-Patterns.pdf
- Functional-Programming-in-Kotlin-by-Tutorials.pdf
- FunctionalBananas.pdf
- FunctionalProgrammingSwift.pdf
- Haskell-Functional-Design-and-Architecture.pdf
- Haskell-pragmatic-type-level-design.pdf
- **domain-modeling-made-functional_P1.0.pdf** ← (Entscheidung: gehört zu fp)

### KB `cat` – Kategorientheorie (9 Bücher)
- CalculateCategorically.pdf
- Categories-for-the-Working-Mathematician.pdf
- Category Theory Illustrated -.pdf
- CategoryTheoryForProgrammers.pdf
- CategoryTheoryForScientists.pdf
- CategoryTheoryIntro.pdf
- Conceptual-Mathematics-A-first-introduction-to-category-theory.pdf
- Eugenia-Cheng-The-Joy-of-Abstraction-...pdf
- What-is-applied-category-theory.pdf

### KB `arch` – Software-Architektur (1 Buch)
- Clean-Code.pdf

### KB `ai` – AI & Vibe Coding (2 Bücher)
- common-sense-guide-to-ai-engineering_B3.0.pdf
- process-over-magic-beyond-vibe-coding_B1.0.pdf

> Alle KBs sind klein und erweiterbar – weitere Bücher können jederzeit hinzugefügt werden.

---

## 3. Zielstruktur: Unterordner

### 3.1 Bücher in LambdaPy – thematische Unterordner

```
LambdaPy/resources/books/
├── fp/
│   ├── Functional-Anthology.pdf
│   ├── Functional-Patterns.pdf
│   ├── Functional-Programming-in-Kotlin-by-Tutorials.pdf
│   ├── FunctionalBananas.pdf
│   ├── FunctionalProgrammingSwift.pdf
│   ├── Haskell-Functional-Design-and-Architecture.pdf
│   ├── Haskell-pragmatic-type-level-design.pdf
│   └── domain-modeling-made-functional_P1.0.pdf
├── cat/
│   ├── CalculateCategorically.pdf
│   ├── Categories-for-the-Working-Mathematician.pdf
│   ├── Category Theory Illustrated -.pdf
│   ├── CategoryTheoryForProgrammers.pdf
│   ├── CategoryTheoryForScientists.pdf
│   ├── CategoryTheoryIntro.pdf
│   ├── Conceptual-Mathematics-A-first-introduction-to-category-theory.pdf
│   ├── Eugenia-Cheng-The-Joy-of-Abstraction-...pdf
│   └── What-is-applied-category-theory.pdf
├── arch/
│   └── Clean-Code.pdf
└── ai/
    ├── common-sense-guide-to-ai-engineering_B3.0.pdf
    └── process-over-magic-beyond-vibe-coding_B1.0.pdf
```

### 3.2 KBs – Unterordner in LambdaPy

Die generierten Knowledgebases sollen ebenfalls als Unterordner in LambdaPy gespeichert werden (nicht im globalen `~/.kb/`):

```
LambdaPy/knowledgebase/kbs/
├── fp/
│   └── data/
│       ├── faiss.index
│       └── chunks.json
├── cat/
│   └── data/
│       ├── faiss.index
│       └── chunks.json
├── arch/
│   └── data/
│       ├── faiss.index
│       └── chunks.json
└── ai/
    └── data/
        ├── faiss.index
        └── chunks.json
```

> **Hinweis**: Das erfordert ggf. eine Anpassung in `kb init` / `kb search`, um einen benutzerdefinierten Speicherort (`--kb-dir`) zu unterstützen, statt nur `~/.kb/<name>/`. Alternativ könnte man Symlinks nutzen.

---

## 4. Migrations-Schritte

### Schritt 1: KB-Projekt global installieren
```bash
cd /Users/mhennemeyer/Desktop/Work/Articles/Knowledgebase
pip install -e .
```
Verifizierung: `kb --help` funktioniert global.

### Schritt 2: Custom KB-Verzeichnis unterstützen
Das Knowledgebase-Projekt muss einen `--kb-dir` Parameter unterstützen (oder ähnlich), damit KBs nicht nur in `~/.kb/` gespeichert werden können, sondern auch in einem Projekt-Unterordner.

**Option A**: `--kb-dir /path/to/LambdaPy/knowledgebase/kbs` Parameter für `init`, `search`, `ask`
**Option B**: Umgebungsvariable `KB_BASE_DIR` die `~/.kb` überschreibt
**Option C**: Symlinks von `~/.kb/fp` → `LambdaPy/knowledgebase/kbs/fp`

**Empfehlung**: Option A oder B – sauberer als Symlinks.

### Schritt 3: Bücher in Unterordner sortieren
PDFs in `LambdaPy/resources/books/` in thematische Unterordner verschieben (siehe 3.1).

### Schritt 4: Thematische KBs erstellen
```bash
kb init ~/Desktop/Work/Articles/LambdaPy/resources/books/fp --name fp --kb-dir ~/Desktop/Work/Articles/LambdaPy/knowledgebase/kbs
kb init ~/Desktop/Work/Articles/LambdaPy/resources/books/cat --name cat --kb-dir ~/Desktop/Work/Articles/LambdaPy/knowledgebase/kbs
kb init ~/Desktop/Work/Articles/LambdaPy/resources/books/arch --name arch --kb-dir ~/Desktop/Work/Articles/LambdaPy/knowledgebase/kbs
kb init ~/Desktop/Work/Articles/LambdaPy/resources/books/ai --name ai --kb-dir ~/Desktop/Work/Articles/LambdaPy/knowledgebase/kbs
```

### Schritt 5: ~/.agent/rules.md aktualisieren
Folgende Sektion in die globalen Agent-Regeln aufnehmen:

```markdown
#### kb – Knowledgebase-Suche via CLI

**Basis-Aufruf:**
```bash
kb search "Suchbegriff" --name <kb-name> --json
```

**Verfügbare KBs:**
| Name | Thema | Bücher |
|---|---|---|
| `fp` | Functional Programming | 8 |
| `cat` | Kategorientheorie | 9 |
| `arch` | Software-Architektur | 1 |
| `ai` | AI & Vibe Coding | 2 |

**Wichtige Parameter:**
* `--name <kb>` – Knowledgebase auswählen (Pflicht)
* `--json` – JSON-Output für maschinelle Verarbeitung
* `--book <Buchname>` – Ergebnisse auf ein Buch filtern
* `--top <N>` – Anzahl der Ergebnisse (Standard: 10)

**Weitere Befehle:**
* `kb ask "Frage" --name <kb>` – Beantwortet eine Frage mit Quellenangaben (nutzt GPT-4o)
* `kb list` – Zeigt alle verfügbaren Knowledgebases
* `kb open --name <kb>` – Öffnet das KB-Verzeichnis

**Zitier-Konvention:**
Ergebnisse enthalten `book` und `page` – Zitate immer mit Buch und Seitenzahl belegen.
```

### Schritt 6: LambdaPy Agent-Config anpassen
In LambdaPy's `.agent/specification.md` oder `.agent/rules.md` auf die globale KB-Konfiguration verweisen.

### Schritt 7: Alte KB-Dateien in LambdaPy entfernen
Nach erfolgreicher Validierung:
- `knowledgebase/extract_pdfs.py` → gelöscht
- `knowledgebase/build_index.py` → gelöscht
- `knowledgebase/search.py` → gelöscht
- `knowledgebase/markdown/` → gelöscht
- `knowledgebase/data/` → gelöscht
- `knowledgebase/BOOKS_INDEX.md` → gelöscht

**NICHT** ändern: Bestehende Artikel in `topics/` bleiben unverändert.

---

## 5. Kompatibilitäts-Analyse (Referenz)

### 5.1 Chunk-Format
| Feld | LambdaPy | Knowledgebase | Kompatibel? |
|---|---|---|---|
| `text` | ✓ | ✓ | ✅ Identisch |
| `book` | ✓ (Title-Case) | ✓ (Title-Case) | ✅ Identisch |
| `book_file` | ✓ | ✓ | ✅ Identisch |
| `page` | ✓ | ✓ | ✅ Identisch |
| `chunk_id` | ✗ | ✓ | ✅ Neues Feld, kein Konflikt |
| `chapter_title` | ✗ | ✓ (optional) | ✅ Neues Feld, kein Konflikt |

### 5.2 Embedding-Dimension
| | LambdaPy | Knowledgebase |
|---|---|---|
| Modell | `text-embedding-3-small` | `text-embedding-3-large` |
| Dimensionen | 1536 | 3072 |

→ **Nicht kompatibel** → Neuaufbau via `kb init`.

### 5.3 Chunking-Logik: Identische Parameter (1500/200, PyMuPDF).

### 5.4 CLI: Knowledgebase-CLI ist eine Obermenge der LambdaPy-CLI.
