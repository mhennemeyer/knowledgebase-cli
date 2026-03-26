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
from knowledgebase.core.vision import get_image_description


SUPPORTED_EXTENSIONS = {".pdf", ".epub"}
IMAGE_MIN_WIDTH = 100
IMAGE_MIN_HEIGHT = 100
IMAGE_MIN_SIZE = 5000  # 5 KB


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


def extract_pdf_to_markdown(pdf_path: str | Path, config: KBConfig | None = None) -> tuple[str, int]:
    """
    Extrahiert eine PDF zu Markdown mit Seitenreferenzen und Bildern.

    Returns:
        (markdown_text, page_count)
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))
    filename = pdf_path.name
    title = pdf_path.stem.replace("-", " ").replace("_", " ")
    slug = slugify(filename)

    lines = [f"# {title}\n"]
    lines.append(f"**Quelle**: `{filename}`  ")
    lines.append(f"**Seiten**: {doc.page_count}\n")

    toc = extract_toc(doc)
    if toc:
        lines.append(format_toc(toc))
        lines.append("")

    lines.append("---\n")

    # Verzeichnis für Bilder vorbereiten
    book_images_dir = None
    if config:
        book_images_dir = config.images_dir / slug
        book_images_dir.mkdir(parents=True, exist_ok=True)

    for idx, page in enumerate(doc, start=1):
        # 1. Raster-Bilder extrahieren
        image_placeholders = []
        if book_images_dir:
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                width = base_image["width"]
                height = base_image["height"]
                ext = base_image["ext"]

                if width < IMAGE_MIN_WIDTH or height < IMAGE_MIN_HEIGHT or len(image_bytes) < IMAGE_MIN_SIZE:
                    continue

                img_filename = f"img_p{idx}_{img_idx}.{ext}"
                img_path = book_images_dir / img_filename
                img_path.write_bytes(image_bytes)

                placeholder = f"![[images/{slug}/{img_filename}]]"
                image_placeholders.append(placeholder)

                # Vision-Analyse (optional)
                if config and config.use_vision:
                    desc_path = img_path.with_suffix(".desc")
                    if not desc_path.exists():
                        try:
                            description = get_image_description(img_path)
                            desc_path.write_text(description, encoding="utf-8")
                        except Exception as e:
                            print(f"Vision-Fehler für {img_filename}: {e}")

        # 1.5 Vektorgrafiken erkennen (Fallback für eingebettete Zeichnungen)
        if book_images_dir and not image_placeholders:
            drawings = page.get_drawings()
            if len(drawings) > 50:
                # Umschließendes Rechteck aller Zeichnungen berechnen (begrenzt auf die Seite)
                rect = fitz.Rect()
                for d in drawings:
                    d_rect = d["rect"] & page.rect
                    if not d_rect.is_empty:
                        rect |= d_rect
                
                
                # Nur rastern wenn die Grafik signifikant ist (mind. 50x50)
                if not rect.is_empty and rect.width > 50 and rect.height > 50:
                    # Etwas Padding hinzufügen
                    rect.x0 = max(0, rect.x0 - 5)
                    rect.y0 = max(0, rect.y0 - 5)
                    rect.x1 = min(page.rect.width, rect.x1 + 5)
                    rect.y1 = min(page.rect.height, rect.y1 + 5)

                    img_filename = f"vector_p{idx}.png"
                    img_path = book_images_dir / img_filename
                    
                    # Grafik-Bereich rastern
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                    pix.save(str(img_path))
                    
                    placeholder = f"![[images/{slug}/{img_filename}]]"
                    image_placeholders.append(placeholder)
                    
                    if config and config.use_vision:
                        desc_path = img_path.with_suffix(".desc")
                        if not desc_path.exists():
                            try:
                                description = get_image_description(img_path)
                                desc_path.write_text(description, encoding="utf-8")
                            except Exception as e:
                                print(f"Vision-Fehler für {img_filename}: {e}")

        # 2. Text extrahieren
        text = page.get_text("text") or ""
        text = text.strip()
        if not text and not image_placeholders:
            continue

        lines.append(f"### Seite {idx}\n")
        # Bilder vor dem Text platzieren
        for ph in image_placeholders:
            lines.append(ph)
        if text:
            lines.append(text)
        lines.append("")

    page_count = doc.page_count
    doc.close()
    return "\n".join(lines), page_count


# --- EPUB-Extraktion ---

def extract_epub_to_markdown(epub_path: str | Path, config: KBConfig | None = None) -> tuple[str, int]:
    """
    Extrahiert ein EPUB zu Markdown mit Kapitelreferenzen und Bildern.

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
    slug = slugify(filename)

    lines = [f"# {title}\n"]
    lines.append(f"**Quelle**: `{filename}`\n")

    # Verzeichnis für Bilder vorbereiten
    book_images_dir = None
    if config:
        book_images_dir = config.images_dir / slug
        book_images_dir.mkdir(parents=True, exist_ok=True)

    # 1. Bilder extrahieren und speichern
    image_map = {} # Original Name -> New Slug Path
    if book_images_dir:
        # Alle Items prüfen, die Bilder sein könnten (inkl. SVGs)
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE or item.get_name().lower().endswith((".svg", ".png", ".jpg", ".jpeg", ".gif")):
                img_content = item.get_content()
                img_name = Path(item.get_name()).name
                
                # Grobe Filterung nach Dateigröße
                if len(img_content) < IMAGE_MIN_SIZE and not img_name.endswith(".svg"):
                    continue

                img_path = book_images_dir / img_name
                img_path.write_bytes(img_content)
                
                image_map[img_name] = f"![[images/{slug}/{img_name}]]"

                # Vision-Analyse
                if config and config.use_vision:
                    desc_path = img_path.with_suffix(".desc")
                    if not desc_path.exists():
                        try:
                            description = get_image_description(img_path)
                            desc_path.write_text(description, encoding="utf-8")
                        except Exception as e:
                            print(f"Vision-Fehler für {img_name}: {e}")

    # 2. Kapitel extrahieren
    chapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    lines.append("---\n")

    chapter_num = 0
    for chapter in chapters:
        content = chapter.get_content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Bilder im HTML durch Platzhalter ersetzen
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if src:
                src_name = Path(src).name
                if src_name in image_map:
                    img_tag.replace_with("\n" + image_map[src_name] + "\n")
                else:
                    img_tag.decompose() # Entferne kleine/unwichtige Bilder

        text = soup.get_text(separator="\n").strip()

        if not text or (len(text) < 50 and not image_map):
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

Extractor = Callable[[str | Path, KBConfig | None], tuple[str, int]]


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
    for idx, book_name in enumerate(books, start=1):
        print(f"  [{idx}/{len(books)}] Extrahiere {book_name}...")
        book_path = book_dir / book_name
        slug = slugify(book_name)
        md_filename = f"{slug}.md"
        md_path = config.markdown_dir / md_filename

        extractor = get_extractor(book_path)
        markdown, page_count = extractor(book_path, config)
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
    markdown, page_count = extractor(book_path, config)
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
