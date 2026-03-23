"""Shared Fixtures für Knowledgebase-Tests."""
import numpy as np
import fitz  # PyMuPDF
import pytest
from pathlib import Path
from unittest.mock import MagicMock


FAKE_DIM = 8  # Kleine Dimension für schnelle Tests


def create_test_pdf(path: Path, pages: dict[int, str]) -> None:
    """
    Erzeugt eine Test-PDF mit bekanntem Inhalt.

    Args:
        path: Zielpfad für die PDF-Datei.
        pages: Dict von Seitennummer → Text-Inhalt.
    """
    doc = fitz.open()
    for page_num in sorted(pages.keys()):
        page = doc.new_page()
        page.insert_text((72, 72), pages[page_num], fontsize=11)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def fake_embedding_dim() -> int:
    """Gibt die Dimension der Fake-Embeddings zurück."""
    return FAKE_DIM


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """
    Erzeugt einen Mock-OpenAI-Client der deterministische Fake-Embeddings liefert.

    Jeder Text bekommt einen reproduzierbaren Vektor basierend auf einem Hash.
    """
    client = MagicMock()

    def fake_create(model, input):
        response = MagicMock()
        response.data = []
        for text in input:
            # Deterministischer Vektor basierend auf Text-Hash
            seed = hash(text) % (2**31)
            rng = np.random.RandomState(seed)
            embedding = rng.rand(FAKE_DIM).astype(float).tolist()
            item = MagicMock()
            item.embedding = embedding
            response.data.append(item)
        return response

    client.embeddings.create.side_effect = fake_create
    return client


@pytest.fixture
def pdf_fixture_dir(tmp_path) -> Path:
    """
    Erzeugt ein Verzeichnis mit zwei Test-PDFs mit bekanntem Inhalt.

    - Functor-Book.pdf: 3 Seiten über Funktoren
    - Monad-Guide.pdf: 2 Seiten über Monaden
    """
    pdf_dir = tmp_path / "books"
    pdf_dir.mkdir()

    create_test_pdf(pdf_dir / "Functor-Book.pdf", {
        1: (
            "A functor is a mapping between categories that preserves "
            "the structure of morphisms. The functor laws state that "
            "identity morphisms and composition must be preserved. "
            "This is fundamental to category theory and functional programming."
        ),
        2: (
            "In Haskell, a Functor is defined by the fmap function. "
            "fmap applies a function to the value inside a context "
            "without altering the structure. Lists, Maybe, and IO "
            "are common functor instances in Haskell."
        ),
        3: (
            "The first functor law states fmap id equals id. "
            "The second functor law states fmap (f . g) equals "
            "fmap f . fmap g. These laws ensure consistent behavior "
            "across all functor implementations."
        ),
    })

    create_test_pdf(pdf_dir / "Monad-Guide.pdf", {
        1: (
            "A monad is a design pattern used in functional programming "
            "to handle side effects. Monads provide bind and return "
            "operations. The monad laws are left identity, right identity, "
            "and associativity."
        ),
        2: (
            "In Haskell, the Monad typeclass extends Applicative. "
            "The bind operator (>>=) chains computations that produce "
            "monadic values. Common monads include Maybe, Either, IO, "
            "and State."
        ),
    })

    return pdf_dir
