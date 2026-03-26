# Plan: Vision & Bild-Unterstützung für Knowledgebase (REFINED)

Dieses Dokument beschreibt die Erweiterung der Knowledgebase um die Fähigkeit, Bilder aus Büchern zu extrahieren, während der **Init-Phase** mittels Vision AI (GPT-4o) zu beschreiben, zu indexieren und in RAG-Antworten (base64) zurückzugeben.

## 1. Zielsetzung
*   **Extraktion**: Bilder aus PDF und EPUB während des `init`/`add` Prozesses extrahieren.
*   **Filterung**: Sehr kleine Bilder (Icons, Trennlinien, Logos) automatisch ignorieren (Schwellenwert für Pixel/Dateigröße).
*   **Vision-Analyse (Init-Schritt)**: Jedes relevante Bild wird sofort an eine Vision AI (GPT-4o) gesendet, um eine detaillierte textuelle Beschreibung zu generieren.
*   **Vektorisierung**: Diese Beschreibungen werden direkt in die Text-Chunks eingebettet, sodass sie semantisch durchsuchbar sind.
*   **Speicherung**: Originalbilder werden lokal im KB-Verzeichnis abgelegt.
*   **RAG**: Bilder in der `kb ask` Antwort als base64-Strings bereitstellen, wenn der zugehörige Chunk im Kontext ist.
*   **Standard-Verhalten**: Vision ist standardmäßig aktiviert (Deaktivierung via `--no-vision`).

## 2. Technische Umsetzung

### Phase 1: Extraktion, Filterung & Vision-Analyse (`knowledgebase/core/extract.py`)
*   **Verzeichnisstruktur**: `~/Knowledgebase/<kb_name>/images/<book_slug>/`
*   **Filter-Logik**:
    *   Ignoriere Bilder mit einer Breite oder Höhe < 100px.
    *   Ignoriere Bilder < 5 KB.
*   **PDF-Extraktion**:
    *   Nutze `fitz` (PyMuPDF) `page.get_images()`.
    *   Speichere Bilder als PNG/JPG.
    *   Füge im Markdown einen Platzhalter ein: `![[images/<book_slug>/img_p<page>_<idx>.png]]`.
*   **Vision-Prozess (Neu)**:
    *   Rufe für jedes extrahierte Bild die OpenAI Vision API (`gpt-4o`) auf.
    *   Prompt: "Beschreibe dieses Bild aus einem Fachbuch detailliert. Erfasse Diagramme, Formeln, Tabelleninhalte oder Illustrationen, sodass sie textuell suchbar sind."
    *   Speichere die Beschreibung in einer `.desc` Datei neben dem Bild oder direkt in den Metadaten.

### Phase 2: Datenmodell & Chunking
*   **Modell (`knowledgebase/models.py`)**:
    *   `Chunk` erweitern um `image_paths: list[str]`.
    *   `Answer` erweitern um `images: dict[str, str]` (Pfad -> Base64).
*   **Chunking (`knowledgebase/core/chunk.py`)**:
    *   Regex-Suche nach `![[...]]` im Text eines Chunks.
    *   Lade die zugehörige Vision-Beschreibung und füge sie in den Chunk-Text ein:
        `[BILD-BESCHREIBUNG: <beschreibung>]`.
    *   Gefundene Pfade in das `image_paths`-Feld des Chunks übertragen.

### Phase 3: RAG-Prozess (`knowledgebase/core/answer.py` & `search.py`)
*   **Suche**:
    *   Da die Bildbeschreibungen im Text sind, finden semantische Suchen ("Zeig mir ein Diagramm über Monaden") nun auch die entsprechenden Bilder.
*   **Kontext-Aufbereitung**:
    *   `kb ask` lädt für alle Top-K Chunks die referenzierten Bilder von der Festplatte.
*   **Response**:
    *   Sammle alle Bilder der Kontext-Chunks, wandle sie in base64 um und füge sie dem `Answer`-Objekt hinzu.

### Phase 4: CLI & API (`knowledgebase/cli.py`)
*   **Optionen**: Standardmäßig Vision-Analyse bei `init` und `add`.
*   **Flag**: `--no-vision` zum Überspringen der Vision-AI (spart Kosten/Zeit).
*   **JSON-Output**: `kb ask --json` enthält das `images`-Dictionary.

## 5. Fortschritt der Migration

### Knowledgebase 'arch' (1/1) ✅
- [x] Clean-Code.pdf

### Knowledgebase 'fp' (8/8) ✅
- [x] Functional-Anthology.pdf
- [x] Functional-Patterns.pdf
- [x] Functional-Programming-in-Kotlin-by-Tutorials.pdf
- [x] FunctionalBananas.pdf
- [x] FunctionalProgrammingSwift.pdf
- [x] Haskell-Functional-Design-and-Architecture.pdf
- [x] Haskell-pragmatic-type-level-design.pdf
- [x] domain-modeling-made-functional_P1.0.pdf

### Knowledgebase 'cat' (9/9) ✅
- [x] CalculateCategorically.pdf
- [x] Categories-for-the-Working-Mathematician.pdf
- [x] Category Theory Illustrated -.pdf
- [x] CategoryTheoryForProgrammers.pdf
- [x] CategoryTheoryForScientists.pdf
- [x] CategoryTheoryIntro.pdf
- [x] Conceptual-Mathematics-A-first-introduction-to-category-theory.pdf (Indiziert ohne Vision)
- [x] Eugenia-Cheng-The-Joy-of-Abstraction-an-Exploration-of-Math-Category-Theory-And-Life-Cambridge-University-Press-2022.pdf
- [x] What-is-applied-category-theory.pdf

### Knowledgebase 'ai' (25/25) ✅
- [x] azureopenaiessentials.epub
- [x] buildingagenticaisystems.epub
- [x] buildingaiapplicationswithopenaiapis.epub
- [x] buildingdata-drivenapplicationswithllamaindex.epub
- [x] buildingllmpoweredapplications.epub
- [x] common-sense-guide-to-ai-engineering_B3.0.pdf
- [x] essentialguidetollmops.epub
- [x] generativeaifoundationsinpython.epub
- [x] generativeaiwithlangchain2e.epub
- [x] generativeaiwithpythonandpytorch.epub
- [x] learnmodelcontextprotocolwithpython.epub
- [x] learnmodelcontextprotocolwithtypescript.epub
- [x] learnpythonprogramming4e.epub
- [x] llmdesignpatterns.epub
- [x] llmengineershandbook.epub
- [x] llmsinenterprise.epub
- [x] machinelearningwithpytorchandscikit-learn.epub (Indiziert ohne Vision)
- [x] masteringnlpfromfoundationstollms.epub
- [x] masteringpytorch_secondedition.epub (Indiziert ohne Vision)
- [x] moderncomputervisionwithpytorch2e.epub (Indiziert ohne Vision)
- [x] practicalgenerativeaiwithchatgpt.epub (Indiziert ohne Vision)
- [x] process-over-magic-beyond-vibe-coding_B1.0.pdf (Indiziert ohne Vision)
- [x] rag-drivengenerativeai.epub (Indiziert ohne Vision)
- [x] transformersfornaturallanguageprocessing3e.epub (Indiziert ohne Vision)
- [x] unlockingdatawithgenerativeaiandrag.epub (Indiziert ohne Vision)
