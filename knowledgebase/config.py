"""Konfiguration für die Knowledgebase."""
import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_KB_DIR = Path.home() / "Knowledgebase"
DEFAULT_KB_NAME = "default"
EMBEDDING_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-4o"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


@dataclass
class KBConfig:
    """Konfiguration einer Knowledgebase-Instanz."""
    name: str = DEFAULT_KB_NAME
    base_dir: Path = DEFAULT_KB_DIR
    pdf_dir: Path | None = None
    embedding_model: str = EMBEDDING_MODEL
    llm_model: str = LLM_MODEL
    chunk_size: int = CHUNK_SIZE
    chunk_overlap: int = CHUNK_OVERLAP

    @property
    def kb_dir(self) -> Path:
        """Verzeichnis dieser KB-Instanz."""
        return self.base_dir / self.name

    @property
    def markdown_dir(self) -> Path:
        """Verzeichnis für extrahierte Markdown-Dateien."""
        return self.kb_dir / "markdown"

    @property
    def data_dir(self) -> Path:
        """Verzeichnis für Index und Chunk-Daten."""
        return self.kb_dir / "data"

    @property
    def index_path(self) -> Path:
        """Pfad zur FAISS-Index-Datei."""
        return self.data_dir / "faiss.index"

    @property
    def chunks_path(self) -> Path:
        """Pfad zur Chunk-Metadaten-Datei."""
        return self.data_dir / "chunks.json"

    def ensure_dirs(self) -> None:
        """Erstellt alle benötigten Verzeichnisse."""
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


def get_openai_api_key() -> str:
    """Liest den OpenAI API-Key aus der Umgebung."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY Umgebungsvariable nicht gesetzt.\n"
            "  export OPENAI_API_KEY='sk-...'"
        )
    return key
