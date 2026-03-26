"""
CLI Entry Point für die Knowledgebase.

Nutzung:
    kb init ~/Books
    kb search "functor laws"
    kb ask "Was sind Monaden?"
    kb list
    kb open "Clean-Code.pdf" --page 42
"""
import json
import sys
from pathlib import Path

import typer

from knowledgebase.config import DEFAULT_KB_DIR, KBConfig

app = typer.Typer(
    name="kb",
    help="Knowledgebase – Semantische Suche über deine E-Books.",
    no_args_is_help=True,
)


@app.command()
def init(
    pdf_dir: str = typer.Argument(..., help="Verzeichnis mit PDF-/EPUB-Dateien"),
    name: str = typer.Option("default", "--name", "-n", help="Name der Knowledgebase"),
    base_dir: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs (Standard: ~/Knowledgebase)"),
    no_vision: bool = typer.Option(False, "--no-vision", help="Vision-Analyse deaktivieren (Standard: aktiviert)"),
) -> None:
    """Bücher extrahieren und FAISS-Index aufbauen."""
    from knowledgebase.core.extract import extract_all_books
    from knowledgebase.core.chunk import build_all_chunks
    from knowledgebase.core.index import build_index

    config = KBConfig(
        name=name,
        pdf_dir=Path(pdf_dir).expanduser().resolve(),
        base_dir=Path(base_dir).expanduser().resolve() if base_dir else DEFAULT_KB_DIR,
        use_vision=not no_vision,
    )

    typer.echo(f"📚 Initialisiere KB '{config.name}' aus {config.pdf_dir} (Vision: {'An' if config.use_vision else 'Aus'})...\n")

    typer.echo("1/3 Bücher extrahieren...")
    results = extract_all_books(config)
    for r in results:
        typer.echo(f"  ✓ {r['book_name']} ({r['page_count']} Seiten/Kapitel, {r['format']})")

    typer.echo("\n2/3 Chunks erstellen...")
    chunks = build_all_chunks(config)
    typer.echo(f"  {len(chunks)} Chunks erstellt")

    typer.echo("\n3/3 FAISS-Index bauen...")
    build_index(chunks, config)

    typer.echo(f"\n✓ KB '{config.name}' erfolgreich aufgebaut!")
    typer.echo(f"  {len(results)} Bücher, {len(chunks)} Chunks")
    typer.echo(f"  Index: {config.index_path}")


@app.command()
def add(
    path: str = typer.Argument(..., help="Pfad zu einem Buch oder Verzeichnis mit Büchern"),
    name: str = typer.Option("default", "--name", "-n", help="Name der Knowledgebase"),
    base_dir: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs"),
    no_vision: bool = typer.Option(False, "--no-vision", help="Vision-Analyse deaktivieren"),
) -> None:
    """Bestehende Knowledgebase um neue Bücher erweitern."""
    from knowledgebase.core.extract import extract_single_book, SUPPORTED_EXTENSIONS
    from knowledgebase.core.chunk import parse_markdown_to_chunks
    from knowledgebase.core.index import append_to_index, load_index

    config = KBConfig(
        name=name,
        base_dir=Path(base_dir).expanduser().resolve() if base_dir else DEFAULT_KB_DIR,
        use_vision=not no_vision,
    )

    # Bestehende Bücher laden, um Duplikate zu vermeiden
    try:
        _, existing_chunks = load_index(config)
        # Wir nutzen book_file für die Duplikat-Prüfung (ist der MD-Dateiname)
        existing_md_files = {c.book_file for c in existing_chunks}
    except FileNotFoundError:
        typer.echo(f"❌ KB '{name}' nicht gefunden unter {config.base_dir}. Bitte zuerst `kb init` verwenden.")
        raise typer.Exit(1)

    input_path = Path(path).expanduser().resolve()
    if input_path.is_dir():
        books_to_scan = [
            f for f in input_path.iterdir()
            if f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    elif input_path.is_file() and input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
        books_to_scan = [input_path]
    else:
        typer.echo(f"❌ Pfad {input_path} ist keine unterstützte Datei oder Verzeichnis (.pdf, .epub).")
        raise typer.Exit(1)

    if not books_to_scan:
        typer.echo("Keine unterstützten Dateien gefunden.")
        return

    new_all_chunks = []
    added_count = 0

    typer.echo(f"➕ Erweitere KB '{name}'...\n")

    for book_path in sorted(books_to_scan):
        book_filename = book_path.name
        from knowledgebase.core.extract import slugify
        slug = slugify(book_filename)
        md_filename = f"{slug}.md"

        if md_filename in existing_md_files:
            typer.echo(f"  ⏩ Überspringe '{book_filename}' (bereits im Index)")
            continue

        typer.echo(f"  📖 Extrahiere '{book_filename}'...")
        try:
            book_info = extract_single_book(book_path, config)
            md_path = config.markdown_dir / book_info["md_file"]
            
            # Chunks erstellen
            book_chunks = parse_markdown_to_chunks(md_path, config=config)
            
            # Die Chunks haben bereits book_file=md_filename (durch parse_markdown_to_chunks)
            # Wir müssen nichts weiter tun.
            
            new_all_chunks.extend(book_chunks)
            added_count += 1
            typer.echo(f"     ✓ {len(book_chunks)} Chunks erzeugt")
        except Exception as e:
            typer.echo(f"     ❌ Fehler: {e}")

    if new_all_chunks:
        typer.echo(f"\n🚀 Berechne Embeddings für {len(new_all_chunks)} Chunks und aktualisiere Index...")
        append_to_index(new_all_chunks, config)
        typer.echo(f"\n✅ Erfolgreich {added_count} Bücher zur KB '{name}' hinzugefügt!")
    else:
        typer.echo("\nKeine neuen Bücher zum Hinzufügen gefunden.")


@app.command()
def search(
    query: str = typer.Argument(..., help="Suchanfrage"),
    top: int = typer.Option(10, "--top", "-n", help="Anzahl Ergebnisse"),
    book: str | None = typer.Option(None, "--book", "-b", help="Buch-Filter (Teilname)"),
    output_json: bool = typer.Option(False, "--json", "-j", help="JSON-Ausgabe"),
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
    pdf_dir: str | None = typer.Option(None, "--pdf-dir", help="PDF-Verzeichnis für Open-Links"),
    base_dir_opt: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs"),
) -> None:
    """Semantische Suche in der Knowledgebase."""
    from knowledgebase.core.search import run_search

    config = KBConfig(
        name=name,
        pdf_dir=Path(pdf_dir).expanduser().resolve() if pdf_dir else None,
        base_dir=Path(base_dir_opt).expanduser().resolve() if base_dir_opt else DEFAULT_KB_DIR,
    )

    results = run_search(query, config, top_k=top, book_filter=book)

    if output_json:
        data = [
            {
                "text": r.chunk.text[:500],
                "book": r.chunk.book,
                "book_file": r.chunk.book_file,
                "page": r.chunk.page,
                "chapter_title": r.chunk.chapter_title,
                "score": r.score,
                "open_cmd": r.open_cmd,
                "images": r.chunk.image_paths,
            }
            for r in results
        ]
        typer.echo(json.dumps({"query": query, "results": data}, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"\n🔍 Suche: \"{query}\"")
        if book:
            typer.echo(f"📚 Filter: {book}")
        typer.echo(f"   {len(results)} Ergebnisse\n")

        for i, r in enumerate(results, start=1):
            typer.echo(f"━━━ Ergebnis {i} (Score: {r.score:.3f}) ━━━")
            location = (
                f"Kapitel: {r.chunk.chapter_title}"
                if r.chunk.chapter_title
                else f"Seite {r.chunk.page}"
            )
            typer.echo(f"📖 {r.chunk.book}  |  {location}")
            if r.open_cmd:
                typer.echo(f"🔗 {r.open_cmd}")
            typer.echo("")
            typer.echo(r.chunk.text[:800] + ("..." if len(r.chunk.text) > 800 else ""))
            typer.echo("")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Frage an die Knowledgebase"),
    top: int = typer.Option(10, "--top", "-n", help="Anzahl Kontext-Chunks"),
    book: str | None = typer.Option(None, "--book", "-b", help="Buch-Filter"),
    output_json: bool = typer.Option(False, "--json", "-j", help="JSON-Ausgabe"),
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
    pdf_dir: str | None = typer.Option(None, "--pdf-dir", help="PDF-Verzeichnis für Open-Links"),
    base_dir_opt: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs"),
) -> None:
    """Frage an die Knowledgebase stellen (RAG)."""
    from knowledgebase.core.answer import generate_answer

    config = KBConfig(
        name=name,
        pdf_dir=Path(pdf_dir).expanduser().resolve() if pdf_dir else None,
        base_dir=Path(base_dir_opt).expanduser().resolve() if base_dir_opt else DEFAULT_KB_DIR,
    )

    answer = generate_answer(question=question, config=config, top_k=top, book_filter=book)

    if output_json:
        sources = [
            {
                "book": s.chunk.book,
                "page": s.chunk.page,
                "chapter_title": s.chunk.chapter_title,
                "score": s.score,
                "open_cmd": s.open_cmd,
                "images": s.chunk.image_paths,
            }
            for s in answer.sources
        ]
        data = {
            "answer": answer.text, 
            "sources": sources,
            "images": answer.images # Base64 Map
        }
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"\n💬 Antwort:\n")
        typer.echo(answer.text)
        if answer.sources:
            typer.echo(f"\n📚 Quellen ({len(answer.sources)}):\n")
            for i, s in enumerate(answer.sources, start=1):
                location = (
                    f"Kapitel: {s.chunk.chapter_title}"
                    if s.chunk.chapter_title
                    else f"Seite {s.chunk.page}"
                )
                typer.echo(f"  {i}. {s.chunk.book} – {location} (Score: {s.score:.3f})")
                if s.chunk.image_paths:
                    typer.echo(f"     🖼️  Bilder: {', '.join(s.chunk.image_paths)}")
                if s.open_cmd:
                    typer.echo(f"     🔗 {s.open_cmd}")


@app.command(name="list")
def list_books(
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
    base_dir: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs"),
) -> None:
    """Alle indizierten Bücher anzeigen."""
    from knowledgebase.core.index import load_index

    config = KBConfig(
        name=name,
        base_dir=Path(base_dir).expanduser().resolve() if base_dir else DEFAULT_KB_DIR,
    )
    _, chunks = load_index(config)

    books = {}
    for c in chunks:
        if c.book_file not in books:
            books[c.book_file] = {"book": c.book, "chunks": 0, "pages": set()}
        books[c.book_file]["chunks"] += 1
        books[c.book_file]["pages"].add(c.page)

    typer.echo(f"\n📚 KB '{name}' – {len(books)} Bücher\n")
    for i, (file, info) in enumerate(sorted(books.items()), start=1):
        typer.echo(f"  {i:3d}. {info['book']}")
        typer.echo(f"       {info['chunks']} Chunks, {len(info['pages'])} Seiten")


@app.command()
def status(
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
    base_dir: str | None = typer.Option(None, "--base-dir", help="Basis-Verzeichnis für KBs"),
) -> None:
    """Index-Statistiken anzeigen."""
    config = KBConfig(
        name=name,
        base_dir=Path(base_dir).expanduser().resolve() if base_dir else DEFAULT_KB_DIR,
    )

    if not config.index_path.exists():
        typer.echo(f"❌ KB '{name}' nicht gefunden. Bitte `kb init` ausführen.")
        raise typer.Exit(1)

    from knowledgebase.core.index import load_index
    index, chunks = load_index(config)

    books = {c.book_file for c in chunks}
    total_images = sum(len(c.image_paths) for c in chunks)
    typer.echo(f"\n📊 KB '{name}'")
    typer.echo(f"   Bücher:   {len(books)}")
    typer.echo(f"   Chunks:   {len(chunks)}")
    typer.echo(f"   Bilder:   {total_images}")
    typer.echo(f"   Vektoren: {index.ntotal}")
    typer.echo(f"   Index:    {config.index_path}")
    typer.echo(f"   Größe:    {config.index_path.stat().st_size / 1024 / 1024:.1f} MB")


@app.command(name="open")
def open_book(
    pdf_file: str = typer.Argument(..., help="PDF-Dateiname oder -pfad"),
    page: int = typer.Option(1, "--page", "-p", help="Seitenzahl"),
) -> None:
    """PDF auf einer bestimmten Seite öffnen."""
    from knowledgebase.core.open_source import open_pdf
    open_pdf(pdf_file, page)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
