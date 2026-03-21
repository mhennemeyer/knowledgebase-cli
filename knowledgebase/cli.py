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

from knowledgebase.config import KBConfig

app = typer.Typer(
    name="kb",
    help="Knowledgebase – Semantische Suche über deine E-Books.",
    no_args_is_help=True,
)


@app.command()
def init(
    pdf_dir: str = typer.Argument(..., help="Verzeichnis mit PDF-Dateien"),
    name: str = typer.Option("default", "--name", "-n", help="Name der Knowledgebase"),
) -> None:
    """PDFs extrahieren und FAISS-Index aufbauen."""
    from knowledgebase.core.extract import extract_all_pdfs
    from knowledgebase.core.chunk import build_all_chunks
    from knowledgebase.core.index import build_index

    config = KBConfig(name=name, pdf_dir=Path(pdf_dir).expanduser().resolve())

    typer.echo(f"📚 Initialisiere KB '{config.name}' aus {config.pdf_dir}...\n")

    # PDFs extrahieren
    typer.echo("1/3 PDFs extrahieren...")
    results = extract_all_pdfs(config)
    for r in results:
        typer.echo(f"  ✓ {r['pdf_name']} ({r['page_count']} Seiten)")

    # Chunks erstellen
    typer.echo("\n2/3 Chunks erstellen...")
    chunks = build_all_chunks(config)
    typer.echo(f"  {len(chunks)} Chunks erstellt")

    # Index bauen
    typer.echo("\n3/3 FAISS-Index bauen...")
    build_index(chunks, config)

    typer.echo(f"\n✓ KB '{config.name}' erfolgreich aufgebaut!")
    typer.echo(f"  {len(results)} Bücher, {len(chunks)} Chunks")
    typer.echo(f"  Index: {config.index_path}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Suchanfrage"),
    top: int = typer.Option(5, "--top", "-n", help="Anzahl Ergebnisse"),
    book: str | None = typer.Option(None, "--book", "-b", help="Buch-Filter (Teilname)"),
    output_json: bool = typer.Option(False, "--json", "-j", help="JSON-Ausgabe"),
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
    pdf_dir: str | None = typer.Option(None, "--pdf-dir", help="PDF-Verzeichnis für Open-Links"),
) -> None:
    """Semantische Suche in der Knowledgebase."""
    from knowledgebase.core.search import run_search

    config = KBConfig(
        name=name,
        pdf_dir=Path(pdf_dir).expanduser().resolve() if pdf_dir else None,
    )

    results = run_search(query, config, top_k=top, book_filter=book)

    if output_json:
        data = [
            {
                "text": r.chunk.text[:500],
                "book": r.chunk.book,
                "book_file": r.chunk.book_file,
                "page": r.chunk.page,
                "score": r.score,
                "open_cmd": r.open_cmd,
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
            typer.echo(f"📖 {r.chunk.book}  |  Seite {r.chunk.page}")
            if r.open_cmd:
                typer.echo(f"🔗 {r.open_cmd}")
            typer.echo("")
            typer.echo(r.chunk.text[:800] + ("..." if len(r.chunk.text) > 800 else ""))
            typer.echo("")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Frage an die Knowledgebase"),
    top: int = typer.Option(5, "--top", "-n", help="Anzahl Kontext-Chunks"),
    output_json: bool = typer.Option(False, "--json", "-j", help="JSON-Ausgabe"),
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
) -> None:
    """Frage an die Knowledgebase stellen (RAG)."""
    typer.echo("⚠️  RAG-Antwortgenerierung ist noch nicht implementiert (Phase 3).")
    typer.echo("   Verwende `kb search` für semantische Suche.")


@app.command(name="list")
def list_books(
    name: str = typer.Option("default", "--name", help="Name der Knowledgebase"),
) -> None:
    """Alle indizierten Bücher anzeigen."""
    from knowledgebase.core.index import load_index

    config = KBConfig(name=name)
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
) -> None:
    """Index-Statistiken anzeigen."""
    config = KBConfig(name=name)

    if not config.index_path.exists():
        typer.echo(f"❌ KB '{name}' nicht gefunden. Bitte `kb init` ausführen.")
        raise typer.Exit(1)

    from knowledgebase.core.index import load_index
    index, chunks = load_index(config)

    books = {c.book_file for c in chunks}
    typer.echo(f"\n📊 KB '{name}'")
    typer.echo(f"   Bücher:  {len(books)}")
    typer.echo(f"   Chunks:  {len(chunks)}")
    typer.echo(f"   Vektoren: {index.ntotal}")
    typer.echo(f"   Index:   {config.index_path}")
    typer.echo(f"   Größe:   {config.index_path.stat().st_size / 1024 / 1024:.1f} MB")


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
