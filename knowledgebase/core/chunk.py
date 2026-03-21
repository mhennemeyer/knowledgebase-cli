"""
Markdown → Chunks mit Metadaten.

Parst extrahierte Markdown-Dateien und erstellt Chunks mit Buch- und Seitenreferenzen.

Basiert auf: LambdaPy/knowledgebase/build_index.py (parse_markdown_to_chunks)
"""
import re
from pathlib import Path

from knowledgebase.config import KBConfig
from knowledgebase.models import Chunk


def parse_markdown_to_chunks(
    md_path: str | Path,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> list[Chunk]:
    """
    Parst eine extrahierte Markdown-Datei und erstellt Chunks mit Metadaten.

    Returns:
        Liste von Chunk-Objekten mit book, book_file, page, text.
    """
    md_path = Path(md_path)
    content = md_path.read_text(encoding="utf-8")

    filename = md_path.name
    book_name = filename.replace(".md", "").replace("-", " ").title()

    page_pattern = re.compile(r"### Seite (\d+)\n")
    parts = page_pattern.split(content)

    chunks = []
    chunk_id = 0
    for i in range(1, len(parts) - 1, 2):
        page_num = int(parts[i])
        page_text = parts[i + 1].strip()
        if not page_text or len(page_text) < 50:
            continue

        if len(page_text) <= chunk_size:
            chunks.append(Chunk(
                text=page_text,
                book=book_name,
                book_file=filename,
                page=page_num,
                chunk_id=chunk_id,
            ))
            chunk_id += 1
        else:
            for start in range(0, len(page_text), chunk_size - chunk_overlap):
                chunk_text = page_text[start:start + chunk_size]
                if len(chunk_text) < 50:
                    continue
                chunks.append(Chunk(
                    text=chunk_text,
                    book=book_name,
                    book_file=filename,
                    page=page_num,
                    chunk_id=chunk_id,
                ))
                chunk_id += 1

    return chunks


def build_all_chunks(config: KBConfig) -> list[Chunk]:
    """
    Erstellt Chunks aus allen Markdown-Dateien im KB-Verzeichnis.

    Returns:
        Liste aller Chunks mit fortlaufenden IDs.
    """
    md_dir = config.markdown_dir
    if not md_dir.exists():
        raise FileNotFoundError(
            f"Markdown-Verzeichnis nicht gefunden: {md_dir}\n"
            "Bitte zuerst PDFs extrahieren (kb init)."
        )

    md_files = sorted(md_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"Keine Markdown-Dateien in {md_dir}.")

    all_chunks = []
    global_id = 0
    for md_file in md_files:
        file_chunks = parse_markdown_to_chunks(
            md_file,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        # Fortlaufende globale IDs vergeben
        renumbered = []
        for chunk in file_chunks:
            renumbered.append(Chunk(
                text=chunk.text,
                book=chunk.book,
                book_file=chunk.book_file,
                page=chunk.page,
                chunk_id=global_id,
            ))
            global_id += 1
        all_chunks.extend(renumbered)

    return all_chunks
