"""
Markdown → Chunks mit Metadaten.

Parst extrahierte Markdown-Dateien und erstellt Chunks mit Buch- und Seitenreferenzen.
Unterstützt Seiten-Referenzen (PDF) und Kapitel-Referenzen (EPUB).

Basiert auf: LambdaPy/knowledgebase/build_index.py (parse_markdown_to_chunks)
"""
import re
from pathlib import Path

from knowledgebase.config import KBConfig
from knowledgebase.models import Chunk


# Pattern für Seiten- und Kapitel-Referenzen
PAGE_PATTERN = re.compile(r"### Seite (\d+)\n")
CHAPTER_PATTERN = re.compile(r"### Kapitel: (.+)\n")
SECTION_PATTERN = re.compile(r"### (?:Seite (\d+)|Kapitel: (.+))\n")
IMAGE_PLACEHOLDER_PATTERN = re.compile(r"!\[\[(images/.+?)\]\]")


def parse_markdown_to_chunks(
    md_path: str | Path,
    config: KBConfig,
) -> list[Chunk]:
    """
    Parst eine extrahierte Markdown-Datei und erstellt Chunks mit Metadaten.

    Erkennt automatisch Seiten-Referenzen (PDF) und Kapitel-Referenzen (EPUB).
    Lädt Bildbeschreibungen (.desc) und fügt sie in den Chunk-Text ein.

    Returns:
        Liste von Chunk-Objekten mit book, book_file, page, text, chapter_title.
    """
    md_path = Path(md_path)
    content = md_path.read_text(encoding="utf-8")
    chunk_size = config.chunk_size
    chunk_overlap = config.chunk_overlap

    filename = md_path.name
    book_name = filename.replace(".md", "").replace("-", " ").title()

    parts = SECTION_PATTERN.split(content)

    chunks = []
    chunk_id = 0
    # parts[0] = Header, dann Gruppen von (page_num, chapter_title, text)
    i = 1
    while i < len(parts) - 2:
        page_match = parts[i]       # Seiten-Nummer oder None
        chapter_match = parts[i + 1]  # Kapitel-Titel oder None
        section_text = parts[i + 2].strip()
        i += 3

        if not section_text or len(section_text) < 50:
            continue

        page_num = int(page_match) if page_match else (chunk_id + 1)
        chapter_title = chapter_match if chapter_match else None

        # Bei Kapitel-Referenzen: page = fortlaufende Kapitelnummer
        if chapter_match and not page_match:
            page_num = len([c for c in chunks if c.chapter_title is not None]) + 1

        # Hilfsfunktion zur Chunk-Erstellung mit Vision-Integration
        def create_chunk(text: str, cid: int) -> Chunk:
            # Bild-Platzhalter finden
            image_paths = IMAGE_PLACEHOLDER_PATTERN.findall(text)
            
            # Bildbeschreibungen injizieren
            enriched_text = text
            for img_rel_path in image_paths:
                img_full_path = config.kb_dir / img_rel_path
                desc_path = img_full_path.with_suffix(".desc")
                if desc_path.exists():
                    description = desc_path.read_text(encoding="utf-8")
                    enriched_text = enriched_text.replace(
                        f"![[{img_rel_path}]]",
                        f"![[{img_rel_path}]]\n[BILD-BESCHREIBUNG: {description}]\n"
                    )
            
            return Chunk(
                text=enriched_text,
                book=book_name,
                book_file=filename,
                page=page_num,
                chunk_id=cid,
                chapter_title=chapter_title,
                image_paths=image_paths
            )

        if len(section_text) <= chunk_size:
            chunks.append(create_chunk(section_text, chunk_id))
            chunk_id += 1
        else:
            for start in range(0, len(section_text), chunk_size - chunk_overlap):
                chunk_text = section_text[start:start + chunk_size]
                if len(chunk_text) < 50:
                    continue
                chunks.append(create_chunk(chunk_text, chunk_id))
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
            config=config,
        )
        renumbered = [
            Chunk(
                text=chunk.text,
                book=chunk.book,
                book_file=chunk.book_file,
                page=chunk.page,
                chunk_id=global_id + idx,
                chapter_title=chunk.chapter_title,
                image_paths=chunk.image_paths,
            )
            for idx, chunk in enumerate(file_chunks)
        ]
        global_id += len(renumbered)
        all_chunks.extend(renumbered)

    return all_chunks
