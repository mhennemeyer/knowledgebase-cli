Sprache: Deutsch
Ansprache: Du (nicht Sie)

In diesem Ordner befinden sich 
    * Anweisungen für den AI-Agent 
    * und Möglichkeiten zur Ablage von Informationen für den AI-Agent.

### Globale Regeln (via Symlink aus `~/.agent/`)
Die folgenden Dateien sind Symlinks auf `~/.agent/` und gelten projektübergreifend:
* `rules.md` – Coding-Standards, Architektur, Workflow, Commit-Strategie
* `functional.md` – FP-Regeln für Code-Generierung

### Projektspezifisch
Die spezifischen Anforderungen für dieses Projekt befinden sich 
in der Datei `specification.md` und README.md, wobei das README in 
inhaltlichen Fragen Vorrang haben sollte.

### Pläne & Features
Alle bisherigen Pläne wurden umgesetzt und befinden sich im Archiv:
*   [Archiv: Phase 3, Tests & EPUB](plans/archived/plan-phase3-and-tests.md)
*   [Archiv: RAG-Analyse & E2E-Tests](plans/archived/plan-rag-analyse-und-e2e-tests.md)
*   [Archiv: Vision & Bild-Unterstützung](plans/archived/plan-vision-image-support.md)
*   [Archiv: LambdaPy KB-Migration](plans/archived/plan-lambdapy-kb-migration.md)

### Offene Punkte (nicht begonnen)
*   Konfigurationsdatei (`~/Knowledgebase/config.toml`)
*   `kb rebuild` – Index komplett neu aufbauen
*   `kb config` – Konfiguration anzeigen/bearbeiten
*   API-Integration-E2E-Tests (Stufe 2 mit echtem API-Key)

Bei Fragen zur Generierung von Bildern bitte das CLI-Tool beuys benutzen.
