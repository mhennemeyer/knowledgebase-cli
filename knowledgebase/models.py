"""Datenklassen für die Knowledgebase."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    """Ein Text-Chunk aus einem Buch mit Metadaten."""
    text: str
    book: str           # Lesbarer Buchtitel
    book_file: str      # Original PDF-Dateiname
    page: int           # Seitenzahl im PDF
    chunk_id: int = 0   # Eindeutige ID im Index


@dataclass(frozen=True)
class SearchResult:
    """Ein Suchergebnis mit Score und Öffnungs-Kommando."""
    chunk: Chunk
    score: float
    open_cmd: str = ""  # macOS-Kommando zum Öffnen auf der richtigen Seite


@dataclass(frozen=True)
class Answer:
    """Eine RAG-generierte Antwort mit Quellenangaben."""
    text: str
    sources: list[SearchResult] = field(default_factory=list)
