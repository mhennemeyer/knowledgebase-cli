"""
Buch-Extraktion → Markdown mit Seitenreferenzen.

Unterstützt PDF und EPUB. Automatische Format-Erkennung via Dateiendung.
"""
import os
import re
from pathlib import Path
from typing import Callable

import fitz  # PyMuPDF

from knowledgebase.config import KBConfig


SUPPORTED_EXTENSIONS = {".pdf", ".epub"}


def slugify(name: str) -> str:
    """Erzeugt einen sauberen Dateinamen aus dem Buchnamen."""
    base = os.path.splitext(name)[0]
    return re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()


# --- PDF-Extraktion ---

def extract_toc(doc: fitz.Document) -> list[dict]:
    """Extrahiert das Inhaltsverzeichnis als Liste von {level, title, page}."""
    raw = doc.get_toc()
    return [{"level": lvl, "title": title, "page": pg} for lvl, title, pg in raw]


def format_toc(toc: list[dict]) -> str:
    """Formatiert das Inhaltsverzeichnis als Markdown."""
    if not toc:
        return ""
    lines = ["## Inhaltsverzeichnis\n"]
    for entry in toc:
        indent = "  " * (entry["level"] - 1)
        lines.append(f"{indent}- {entry['title']} (S. {entry['page']})")
    return "\n".join(lines)


def extract_pdf_to_markdown(pdf_path: str | Path) -> tuple[str, int]:
    """
    Extrahiert eine PDF zu Markdown mit Seitenreferenzen.

    Returns:
        (markdown_text, page_count)
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))
    filename = pdf_path.name
    title = pdf_path.stem.replace("-", " ").replace("_", " ")

    lines = [f"# {title}\n"]
    lines.append(f"**Quelle**: `{filename}`  ")
    lines.append(f"**Seiten**: {doc.page_count}\n")

    toc = extract_toc(doc)
    if toc:
        lines.append(format_toc(toc))
        lines.append("")

    lines.append("---\n")

    for idx, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        text = text.strip()
        if not text:
            continue
        lines.append(f"### Seite {idx}\n")
        lines.append(text)
        lines.append("")

    page_count = doc.page_count
    doc.close()
    return "\n".join(lines), page_count


# --- EPUB-Extraktion ---

def extract_epub_to_markdown(epub_path: str | Path) -> tuple[str, int]:
    """
    Extrahiert ein EPUB zu Markdown mit Kapitelreferenzen.

    Returns:
        (markdown_text, chapter_count)
    """
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    epub_path = Path(epub_path)
    book = epub.read_epub(str(epub_path), options={"ignore_ncx": False})

    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else epub_path.stem.replace("-", " ").replace("_", " ")
    filename = epub_path.name

    lines = [f"# {title}\n"]
    lines.append(f"**Quelle**: `{filename}`\n")

    # Kapitel extrahieren (nur XHTML-Dokumente mit Inhalt)
    chapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    lines.append("---\n")

    chapter_num = 0
    for chapter in chapters:
        content = chapter.get_content()
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n").strip()

        if not text or len(text) < 50:
            continue

        chapter_num += 1

        # Kapitel-Titel aus erstem Heading extrahieren
        heading = soup.find(["h1", "h2", "h3"])
        chapter_title = heading.get_text().strip() if heading else f"Kapitel {chapter_num}"

        lines.append(f"### Kapitel: {chapter_title}\n")
        lines.append(text)
        lines.append("")

    return "\n".join(lines), chapter_num


# --- Format-Erkennung & Factory ---

Extractor = Callable[[str | Path], tuple[str, int]]


def get_extractor(path: str | Path) -> Extractor:
    """Gibt den passenden Extraktor für die Dateiendung zurück."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_pdf_to_markdown
    elif ext == ".epub":
        return extract_epub_to_markdown
    else:
        raise ValueError(f"Nicht unterstütztes Format: {ext} (unterstützt: {SUPPORTED_EXTENSIONS})")


# --- Batch-Extraktion ---

def extract_all_books(config: KBConfig) -> list[dict]:
    """
    Extrahiert alle Bücher (PDF + EPUB) aus dem konfigurierten Verzeichnis.

    Returns:
        Liste von {"book_name", "slug", "md_file", "page_count", "format"}
    """
    if not config.pdf_dir:
        raise ValueError("Kein Buch-Verzeichnis konfiguriert.")

    book_dir = Path(config.pdf_dir)
    if not book_dir.exists():
        raise FileNotFoundError(f"Buch-Verzeichnis nicht gefunden: {book_dir}")

    config.ensure_dirs()
    books = sorted(
        f for f in os.listdir(book_dir)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not books:
        raise FileNotFoundError(
            f"Keine Bücher in {book_dir} gefunden (unterstützt: {', '.join(SUPPORTED_EXTENSIONS)})."
        )

    results = []
    for book_name in books:
        book_path = book_dir / book_name
        slug = slugify(book_name)
        md_filename = f"{slug}.md"
        md_path = config.markdown_dir / md_filename

        extractor = get_extractor(book_path)
        markdown, page_count = extractor(book_path)
        md_path.write_text(markdown, encoding="utf-8")

        results.append({
            "book_name": book_name,
            "slug": slug,
            "md_file": md_filename,
            "page_count": page_count,
            "format": book_path.suffix.lower(),
        })

    return results


def extract_single_book(book_path: Path, config: KBConfig) -> dict:
    """
    Extrahiert ein einzelnes Buch und speichert das Markdown.
    """
    config.ensure_dirs()
    book_name = book_path.name
    slug = slugify(book_name)
    md_filename = f"{slug}.md"
    md_path = config.markdown_dir / md_filename

    extractor = get_extractor(book_path)
    markdown, page_count = extractor(book_path)
    md_path.write_text(markdown, encoding="utf-8")

    return {
        "book_name": book_name,
        "slug": slug,
        "md_file": md_filename,
        "page_count": page_count,
        "format": book_path.suffix.lower(),
    }


def extract_all_pdfs(config: KBConfig) -> list[dict]:
    """
    Legacy-Wrapper: Extrahiert alle PDFs aus dem konfigurierten Verzeichnis.

    Delegiert an extract_all_books für Abwärtskompatibilität.
    """
    results = extract_all_books(config)
    return [
        {
            "pdf_name": r["book_name"],
            "slug": r["slug"],
            "md_file": r["md_file"],
            "page_count": r["page_count"],
        }
        for r in results
    ]
