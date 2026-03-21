"""
PDF → Markdown Extraktor.

Extrahiert PDFs zu strukturierten Markdown-Dateien mit Seitenreferenzen,
sodass Chunks später Buch und Seite referenzieren können.

Basiert auf: LambdaPy/knowledgebase/extract_pdfs.py
"""
import os
import re
from pathlib import Path

import fitz  # PyMuPDF

from knowledgebase.config import KBConfig


def slugify(name: str) -> str:
    """Erzeugt einen sauberen Dateinamen aus dem PDF-Namen."""
    base = os.path.splitext(name)[0]
    return re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()


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


def extract_all_pdfs(config: KBConfig) -> list[dict]:
    """
    Extrahiert alle PDFs aus dem konfigurierten PDF-Verzeichnis.

    Returns:
        Liste von {"pdf_name", "slug", "md_file", "page_count"}
    """
    if not config.pdf_dir:
        raise ValueError("Kein PDF-Verzeichnis konfiguriert.")

    pdf_dir = Path(config.pdf_dir)
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF-Verzeichnis nicht gefunden: {pdf_dir}")

    config.ensure_dirs()
    pdfs = sorted(f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf"))

    if not pdfs:
        raise FileNotFoundError(f"Keine PDFs in {pdf_dir} gefunden.")

    results = []
    for pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        slug = slugify(pdf_name)
        md_filename = f"{slug}.md"
        md_path = config.markdown_dir / md_filename

        markdown, page_count = extract_pdf_to_markdown(pdf_path)
        md_path.write_text(markdown, encoding="utf-8")

        results.append({
            "pdf_name": pdf_name,
            "slug": slug,
            "md_file": md_filename,
            "page_count": page_count,
        })

    return results
