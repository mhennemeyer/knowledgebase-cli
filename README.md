# Knowledgebase

A CLI-based knowledgebase for e-books — semantic search with source references and deep links to open PDFs at the exact page.

## Features

- **Semantic search** across all indexed books (FAISS + OpenAI Embeddings)
- **Source references** with book title and page number
- **Deep links** — open PDFs at the correct page (macOS)
- **JSON output** for piping and AI agent integration
- **Multiple knowledgebases** — independent named KBs (e.g. `--name dev`)
- **PDF & EPUB support** (planned — currently PDF only)

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

All knowledgebase data is stored under `~/.kb/<name>/`.

## Usage

### Build a Knowledgebase

```bash
# Initialize from a directory of PDFs
kb init ~/Books

# Named knowledgebase
kb init ~/Books --name dev
```

### Semantic Search

```bash
kb search "functor laws"
kb search "monad tutorial" --top 10
kb search "clean code" --book "Clean-Code"

# JSON output (for scripts / AI agents)
kb search "category theory" --json
```

### Ask Questions (RAG)

> **Note:** RAG answer generation (`kb ask`) is under development (Phase 3).

```bash
kb ask "What are the functor laws?"
kb ask "Explain monads" --json
```

### Other Commands

```bash
# List all indexed books
kb list

# Show index statistics
kb status

# Open a PDF at a specific page (macOS)
kb open ~/Books/Clean-Code.pdf --page 42
```

### JSON Output Example

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
├── config.py           # Configuration (paths, models)
├── models.py           # Data classes (Chunk, SearchResult, Answer)
└── core/
    ├── extract.py      # PDF → Markdown with page references
    ├── chunk.py        # Markdown → Chunks with metadata
    ├── index.py        # FAISS index (build, load, save)
    ├── search.py       # Semantic search
    └── open_source.py  # Open PDF at page (macOS)
```

### Pipeline

```
PDF → extract → Markdown → chunk → Chunks → index → FAISS
                                                      ↓
                             Query → search → Results + Sources
```

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python ≥ 3.11 |
| PDF extraction | PyMuPDF (fitz) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector index | FAISS (faiss-cpu) |
| LLM (RAG) | OpenAI GPT-4o-mini |
| CLI framework | Typer |
| Tests | pytest |
| Packaging | pyproject.toml + pip install -e . |

## Roadmap

- [x] Phase 1: Core pipeline (extract, chunk, index, search)
- [x] Phase 2: CLI with Typer
- [ ] Phase 3: RAG answer generation (`kb ask`)
- [ ] EPUB support (extraction abstraction + EPUB extractor)
- [ ] Phase 4: Multi-KB, incremental updates, config file

## Development

```bash
# Run tests
pytest

# Run a specific test file
pytest tests/test_extract.py -v
```

## License

MIT
