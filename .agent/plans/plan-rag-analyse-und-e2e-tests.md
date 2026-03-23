# Plan: RAG-Zusammenstellung, Vision AI & E2E-Tests

## Kontext

Analyse der optimalen Nutzung des Knowledgebase-Tools aus der Perspektive eines AI-Agenten (Junie), der die erstellten Knowledgebases selbst nutzt, um Antworten mit Quellen zu belegen – analog zum `beuys`-Tool für Bildgenerierung.

---

## 1. Optimale RAG-Zusammenstellung einer Knowledgebase

### 1.1 Maximale Bücherzahl pro Knowledgebase

**Empfehlung: 5–15 Bücher pro KB, Maximum ~25**

Begründung (technische Constraints):
- **Embedding-Dimension**: `text-embedding-3-small` = 1536 Dimensionen
- **FAISS IndexFlatIP**: Brute-Force-Suche, skaliert linear mit Anzahl der Vektoren. Ab ~100.000 Chunks wird die Suche spürbar langsamer (bei 15 Büchern à 300 Seiten ≈ 4.500–15.000 Chunks – unproblematisch)
- **Kontext-Fenster**: `kb ask` nutzt `top_k=5` Chunks à max. 1500 Zeichen = max. 7.500 Zeichen Kontext. Bei zu vielen Büchern sinkt die Wahrscheinlichkeit, dass die 5 relevantesten Chunks tatsächlich die Frage beantworten
- **Kosten**: Jeder `kb init`-Aufruf erzeugt Embeddings über die OpenAI API. 10.000 Chunks ≈ $0.02 (günstig), aber bei häufigem Rebuild summiert sich das

Praktische Faustregel:
| KB-Größe | Bücher | Chunks (geschätzt) | Eignung |
|---|---|---|---|
| Klein | 3–5 | 1.000–3.000 | Ideal für fokussierte Themen |
| Mittel | 6–15 | 3.000–10.000 | Guter Kompromiss |
| Groß | 16–25 | 10.000–20.000 | Noch sinnvoll, Precision sinkt |
| Zu groß | >25 | >20.000 | RAG-Qualität leidet |

### 1.2 Thematische Fokussierung vs. Diversität

**Empfehlung: Fokussierte, thematische KBs – nicht divers**

Begründung:
- **Semantic Search ist kein Allwissender**: Die Cosine Similarity findet textlich ähnliche Passagen. Bei einer KB mit Büchern über FP, Kochen und Quantenphysik konkurrieren irrelevante Chunks mit relevanten um die top_k-Plätze
- **Prompt-Qualität**: Der RAG-Prompt enthält 5 Kontext-Chunks. Wenn 2 davon aus einem themenfremden Buch stammen, wird die Antwort verwässert oder widersprüchlich
- **Agent-Nutzung**: Ein Agent (wie Junie) profitiert davon, gezielt die richtige KB wählen zu können: `kb ask "Was sind Monaden?" --name fp` statt eine globale KB zu durchsuchen
- **Analogie zu beuys**: Wie `beuys` ein spezialisiertes Tool für Bildgenerierung ist, sollte jede KB ein spezialisiertes Wissensdomäne abdecken

Empfohlene KB-Struktur (Beispiele):
```
~/.kb/fp/          → Functional Programming (5-8 Bücher)
~/.kb/math/        → Kategorie-Theorie, Algebra (4-6 Bücher)
~/.kb/arch/        → Software-Architektur, Clean Code (5-7 Bücher)
~/.kb/ml/          → Machine Learning, Deep Learning (6-10 Bücher)
```

**Anti-Pattern**: Eine einzige KB mit allen Büchern. Die Retrieval-Qualität sinkt, weil der Embedding-Raum zu heterogen wird.

### 1.3 Zusammensetzung innerhalb einer thematischen KB

Innerhalb eines Themas ist eine gewisse Diversität sinnvoll:
- **1–2 Grundlagenwerke** (z.B. "Category Theory for Programmers")
- **2–3 Praxisbücher** (z.B. "Functional Programming in Scala")
- **1–2 Referenzwerke** (z.B. Spezifikationen, Standards)
- **Optional**: Papers oder kürzere Texte als Ergänzung

Das sorgt dafür, dass der RAG bei einer Frage sowohl theoretische Grundlagen als auch praktische Anwendungen als Quellen liefern kann.

---

## 2. Vision AI für Bilder in E-Books

### 2.1 Analyse

Viele Fachbücher enthalten informationsreiche Bilder:
- **Diagramme** (UML, Architektur, Datenfluss)
- **Grafiken** (Plots, Charts)
- **Code-Screenshots** (oft in älteren PDFs)
- **Formeln** (als Bilder gerendert)

Aktuell ignoriert die Pipeline alle Bilder – `page.get_text("text")` in PyMuPDF extrahiert nur Text.

### 2.2 Bewertung: Lohnt sich Vision AI?

**Antwort: Ja, aber selektiv und als optionale Erweiterung (Phase 5+)**

| Pro | Contra |
|---|---|
| Diagramme enthalten oft die Kernaussage einer Seite | Hohe API-Kosten (GPT-4o Vision: ~$0.01–0.03 pro Bild) |
| Formeln gehen bei reiner Textextraktion verloren | Viele Bilder sind dekorativ (Cover, Stockfotos) – Noise |
| Architektur-Diagramme sind für Agenten besonders wertvoll | Erhöht die Init-Zeit drastisch (API-Calls pro Bild) |
| Code-Screenshots können in echten Code umgewandelt werden | Qualität der Bildbeschreibung variiert |

### 2.3 Empfohlene Strategie

1. **Bilder extrahieren** (PyMuPDF kann das: `page.get_images()`)
2. **Vorfilterung**: Nur Bilder über einer Mindestgröße (z.B. >100x100px, >5KB) verarbeiten – filtert Icons, Trennlinien etc.
3. **Vision AI Beschreibung**: GPT-4o (nicht mini) mit Prompt: "Beschreibe dieses Diagramm/diese Grafik aus einem Fachbuch präzise. Fokus auf die dargestellten Konzepte und Beziehungen."
4. **Bildbeschreibung als Chunk**: Die Beschreibung wird als normaler Chunk indexiert, mit Metadaten `image=True`, um sie bei der Suche optional ein-/auszuschließen
5. **Opt-in**: `kb init ~/Books --with-images` – standardmäßig deaktiviert wegen Kosten/Zeit

### 2.4 Kosten-Schätzung

Ein typisches Fachbuch (300 Seiten) enthält ~30–80 relevante Bilder nach Filterung.
- Bei 10 Büchern: ~300–800 Bilder
- GPT-4o Vision: ~$3–24 pro KB-Init (vs. ~$0.02 für reine Text-Embeddings)
- **Fazit**: Als Opt-in sinnvoll, nicht als Standard

---

## 3. E2E-Test-Strategie

### 3.1 Ist-Zustand

Die aktuellen 67 Tests sind Unit-/Integration-Tests mit Mocks:
- `test_cli.py`: Typer-Runner mit gemockten Core-Funktionen
- `test_answer.py`: Prompt-Generierung, gemockter LLM-Client
- `test_extract.py`, `test_chunk.py`, `test_index.py`, `test_search.py`: Isolierte Module mit Mocks für OpenAI/FAISS

**Fehlend**: Kein einziger Test, der die gesamte Pipeline ohne Mocks durchläuft.

### 3.2 E2E-Test-Definitionen

Drei Stufen von E2E-Tests:

#### Stufe 1: Pipeline-E2E (ohne externe APIs) – EMPFOHLEN als Erstes
Testet die gesamte Pipeline mit einer Fake-Fixture statt echten Büchern und gemockten API-Calls:

```
Fixture-PDF/EPUB → extract → Markdown → chunk → index (gemockte Embeddings) → search (gemockte Query-Embeddings) → answer (gemockter LLM) → Validierung
```

- **Fixture**: Ein kleines Test-PDF (2-3 Seiten) und ein Test-EPUB (2 Kapitel), die im `tests/fixtures/`-Verzeichnis liegen
- **Mocks**: Nur OpenAI-Calls (Embeddings + LLM) werden gemockt, mit deterministischen Fake-Vektoren
- **Validierung**: Gesamter Datenfluss von Datei bis Antwort, inkl. Quellenangaben mit korrekten Seitenzahlen
- **Vorteil**: Kein API-Key nötig, schnell, deterministisch, CI-fähig

Konkrete Tests:
1. `test_e2e_init_and_search`: `kb init` mit Fixture → `kb search` liefert Ergebnisse mit korrekten Metadaten
2. `test_e2e_init_and_ask`: `kb init` mit Fixture → `kb ask` liefert Antwort mit Quellen
3. `test_e2e_json_roundtrip`: CLI JSON-Output ist valides JSON und enthält alle erwarteten Felder
4. `test_e2e_book_filter`: Suche mit `--book` liefert nur Ergebnisse aus dem gefilterten Buch
5. `test_e2e_named_kb`: Zwei KBs mit `--name` sind unabhängig

#### Stufe 2: API-Integration-E2E (mit echtem OpenAI-Key)
Testet gegen die echte OpenAI API, aber mit minimalen Fixture-Daten:

- **Marker**: `@pytest.mark.integration` – nur bei `pytest -m integration` ausgeführt
- **Voraussetzung**: `OPENAI_API_KEY` gesetzt
- **Fixture**: Dasselbe kleine Test-PDF (minimale API-Kosten)
- **Validierung**: Echte Embeddings werden erzeugt, echte Suche findet semantisch korrekte Ergebnisse, echte LLM-Antwort enthält Quellenreferenzen

Konkrete Tests:
1. `test_integration_real_embeddings`: Embeddings für bekannten Text haben erwartete Dimension (1536)
2. `test_integration_semantic_search`: Semantisch ähnliche Query findet den richtigen Chunk
3. `test_integration_rag_answer`: Frage wird mit plausiblen Quellen beantwortet

#### Stufe 3: CLI-E2E (Subprocess)
Testet das installierte `kb`-Kommando als Subprocess:

```python
result = subprocess.run(["kb", "init", str(fixture_dir)], capture_output=True, text=True)
assert result.returncode == 0
result = subprocess.run(["kb", "ask", "What is X?", "--json"], capture_output=True, text=True)
data = json.loads(result.stdout)
assert "answer" in data
```

- **Vorteil**: Testet die echte Installation, Entry Points, Argument-Parsing
- **Nachteil**: Langsamer, schwerer zu mocken
- **Marker**: `@pytest.mark.e2e`

### 3.3 Test-Fixture-Strategie

Ein dediziertes `tests/fixtures/`-Verzeichnis mit:
- `test-book.pdf` – Ein 3-seitiges PDF mit bekanntem Inhalt (z.B. "Functor laws state that...")
- `test-book.epub` – Ein 2-Kapitel-EPUB mit bekanntem Inhalt
- Alternativ: PDFs/EPUBs programmatisch in Fixtures erzeugen (via `reportlab` für PDF, `ebooklib` für EPUB)

**Empfehlung**: Programmatisch erzeugen – so bleiben die Fixtures im Code, sind versionierbar und der Inhalt ist kontrollierbar.

### 3.4 Empfohlene Reihenfolge

1. **Stufe 1** zuerst implementieren (Pipeline-E2E ohne APIs) – höchster ROI
2. **Stufe 2** als Nächstes (Integration mit echtem API-Key) – fängt API-Breaking-Changes ab
3. **Stufe 3** optional (Subprocess-E2E) – nur nötig wenn Entry-Point-Probleme vermutet werden

### 3.5 Testdatei-Struktur

```
tests/
├── conftest.py              # Shared Fixtures (Fake-Embeddings, Test-PDF-Generator)
├── fixtures/                # (optional, falls nicht programmatisch erzeugt)
├── test_e2e_pipeline.py     # Stufe 1: Pipeline-E2E
├── test_e2e_integration.py  # Stufe 2: API-Integration
├── test_e2e_cli.py          # Stufe 3: Subprocess-E2E
├── test_extract.py          # bestehend
├── ...
```

### 3.6 pytest-Konfiguration

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: Tests mit echtem OpenAI API-Key",
    "e2e: Full CLI E2E-Tests (Subprocess)",
]
```

---

## 4. Zusammenfassung & Empfehlungen

| Thema | Empfehlung |
|---|---|
| **Bücher pro KB** | 5–15, max. 25 |
| **Thematische Ausrichtung** | Fokussiert, nicht divers. Mehrere spezialisierte KBs statt einer großen |
| **KB-Nutzung durch Agent** | Analog zu beuys: `kb ask "Frage" --name <thema> --json` als Tool-Call |
| **Vision AI für Bilder** | Sinnvoll als Opt-in (`--with-images`), nicht als Standard. Phase 5+ |
| **E2E-Tests: Priorität 1** | Pipeline-E2E mit Fixtures + gemockten APIs (Stufe 1) |
| **E2E-Tests: Priorität 2** | API-Integration-Tests mit `@pytest.mark.integration` (Stufe 2) |

---

## 5. Offene Fragen zur Verfeinerung

1. Sollen die E2E-Test-Fixtures (PDF/EPUB) programmatisch erzeugt oder als Binärdateien committed werden?
2. Soll die Vision-AI-Integration als eigenes Modul (`core/vision.py`) oder als Erweiterung von `extract.py` geplant werden?
3. Soll es eine Agent-Integration-Spec geben, die beschreibt wie ein Agent (Junie) die KB als Tool nutzt (analog zur beuys-Doku in rules.md)?
4. Welche konkreten thematischen KBs sollen als Erstes aufgebaut werden?
