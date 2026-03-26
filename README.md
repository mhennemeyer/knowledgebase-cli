# Knowledgebase

A CLI-based knowledgebase for e-books — semantic search and RAG answers with source references and deep links to open PDFs at the exact page.

## Features

- **Semantic search** across all indexed books (FAISS + OpenAI Embeddings)
- **RAG answers** — ask questions, get answers with source references (`kb ask`)
- **Vision AI** — extract and describe images from books (GPT-4o Vision), included in RAG answers as base64
- **PDF & EPUB support** — automatic format detection
- **Source references** with book title, page number / chapter title
- **Deep links** — open PDFs at the correct page (macOS / Skim)
- **JSON output** for piping and AI agent integration
- **Multiple knowledgebases** — independent named KBs (e.g. `--name fp`)
- **Incremental updates** — add single books to an existing KB (`kb add`)

## Prerequisites

- Python ≥ 3.11
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/knowledgebase.git
cd knowledgebase

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode (makes `kb` available system-wide)
pip install -e .
```

## Configuration

The only required configuration is the OpenAI API key, provided via environment variable:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

> **Tip:** Add this to your `~/.zshrc` or `~/.bashrc` for persistence.

All knowledgebase data is stored under `~/Knowledgebase/<name>/`.

## Usage

### Build a Knowledgebase

```bash
# Initialize from a directory of PDFs and/or EPUBs (with Vision AI)
kb init ~/Books

# Named knowledgebase
kb init ~/Books --name fp

# Without Vision AI (saves cost/time)
kb init ~/Books --no-vision

# Custom base directory
kb init ~/Books --name fp --base-dir /custom/path
```

### Add Books to an Existing Knowledgebase

```bash
# Add a single book
kb add ~/Books/new-book.pdf

# Add a directory of books to a named KB
kb add ~/Books/new-books/ --name fp
```

### Ask Questions (RAG)

```bash
kb ask "What are the functor laws?"
kb ask "Explain monads" --json
kb ask "clean code principles" --name dev
```

### Semantic Search

```bash
kb search "functor laws"
kb search "monad tutorial" --top 10
kb search "clean code" --book "Clean-Code"

# JSON output (for scripts / AI agents)
kb search "category theory" --json
```

### List Available Knowledgebases

```bash
# Show all KBs with book titles (for humans)
kb kbs

# JSON output (for AI agents — discover which KB to query)
kb kbs --json
```

> **Note:** Without `--name`, commands like `kb ask` and `kb search` query only the `default` KB, not all KBs. Use `kb kbs` to discover available KBs and then target the right one with `--name`.

### Other Commands

```bash
# List all indexed books in a KB
kb list
kb list --name fp

# Show index statistics
kb status

# Open a PDF at a specific page (macOS)
kb open ~/Books/Clean-Code.pdf --page 42
```

### JSON Output Examples

```bash
kb ask "What are monads?" --json
```

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
  ]
}
```

```bash
kb search "functor laws" --json
```

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

## Architecture

```
knowledgebase/
├── cli.py              # Typer CLI entry point (kb command)
├── config.py           # Configuration (paths, models, vision flag)
├── models.py           # Data classes (Chunk, SearchResult, Answer)
└── core/
    ├── extract.py      # PDF/EPUB → Markdown with page/chapter references + image extraction
    ├── chunk.py        # Markdown → Chunks with metadata (page, chapter, images)
    ├── index.py        # FAISS index (build, load, save)
    ├── search.py       # Semantic search with book filter
    ├── answer.py       # RAG answer generation (LLM + sources + images)
    ├── vision.py       # Vision AI: image description via GPT-4o, base64 encoding
    └── open_source.py  # Open PDF at page (macOS / Skim)
```

### Pipeline

```
PDF/EPUB → extract → Markdown + Images → chunk → Chunks → index → FAISS
              ↓                                                     ↓
        Vision AI (GPT-4o)              Question → search → Chunks → LLM → Answer + Sources + Images
         describes images
```

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python ≥ 3.11 |
| PDF extraction | PyMuPDF (fitz) |
| EPUB extraction | ebooklib + BeautifulSoup4 |
| Embeddings | OpenAI text-embedding-3-large |
| Vector index | FAISS (faiss-cpu) |
| LLM (RAG) | OpenAI GPT-4o |
| Vision AI | OpenAI GPT-4o Vision |
| CLI framework | Typer |
| Tests | pytest |
| Packaging | pyproject.toml + pip install -e . |

## Roadmap

- [x] Phase 1: Core pipeline (extract, chunk, index, search)
- [x] Phase 2: CLI with Typer
- [x] Phase 3: RAG answer generation (`kb ask`)
- [x] EPUB support (extraction abstraction + EPUB extractor)
- [x] Vision AI — image extraction, GPT-4o description, indexing, base64 in RAG answers
- [x] Model upgrades (`text-embedding-3-large`, `gpt-4o`, `top_k=10`)
- [x] E2E test suite (pipeline tests with programmatic PDF fixtures)
- [x] Multi-KB management (`--name`, `--base-dir`)
- [x] Global CLI installation (`pip install -e .`)
- [x] LambdaPy migration — 4 thematic KBs (fp, cat, arch, ai) from 43 books
- [x] Incremental updates (`kb add` for single books)
- [ ] Configuration file (`~/Knowledgebase/config.toml`)
- [ ] `kb rebuild` — rebuild index from scratch
- [ ] `kb config` — show/edit configuration

## Development

```bash
# Run tests
pytest

# Run a specific test file
pytest tests/test_extract.py -v

# Run all tests with verbose output
pytest -v
```

## License

MIT
