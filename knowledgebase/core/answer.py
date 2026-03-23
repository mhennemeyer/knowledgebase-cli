"""
RAG-Antwortgenerierung: Frage → Kontext-Chunks → LLM → Antwort mit Quellen.

Dependency Injection: LLM-Client wird als Callable injiziert (Higher-Order Function).
"""
from typing import Callable

from knowledgebase.config import KBConfig
from knowledgebase.models import Answer, SearchResult


# Type-Alias für den LLM-Client (Callable statt konkreter OpenAI-Klasse)
LLMClient = Callable[[str, str], str]  # (system_prompt, user_prompt) -> answer_text


def build_system_prompt() -> str:
    """Erstellt den System-Prompt für die RAG-Antwortgenerierung."""
    return (
        "Du bist ein Fachexperte, der Fragen basierend auf den bereitgestellten "
        "Quellen beantwortet. Antworte präzise und fundiert. "
        "Beziehe dich auf die Quellen mit [Quelle N] im Text. "
        "Wenn die Quellen keine Antwort liefern, sage das ehrlich."
    )


def build_user_prompt(question: str, results: list[SearchResult]) -> str:
    """
    Erstellt den User-Prompt mit nummerierten Kontext-Chunks und Quellenangaben.
    """
    context_parts = []
    for i, r in enumerate(results, start=1):
        location = (
            f"Kapitel: {r.chunk.chapter_title}"
            if r.chunk.chapter_title
            else f"Seite {r.chunk.page}"
        )
        context_parts.append(
            f"[Quelle {i}] {r.chunk.book} – {location}\n{r.chunk.text}"
        )

    context = "\n\n---\n\n".join(context_parts)

    return (
        f"Frage: {question}\n\n"
        f"Kontext aus der Knowledgebase:\n\n{context}\n\n"
        "Beantworte die Frage basierend auf dem Kontext. "
        "Referenziere die Quellen mit [Quelle N]."
    )


def make_openai_llm_client(
    api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> LLMClient:
    """
    Erzeugt einen konfigurierten LLM-Client als Closure (Higher-Order Function).

    Returns:
        Callable[[str, str], str] – nimmt (system_prompt, user_prompt) und gibt Antworttext zurück.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    def call_llm(system_prompt: str, user_prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    return call_llm


def generate_answer(
    question: str,
    config: KBConfig,
    top_k: int = 5,
    book_filter: str | None = None,
    llm_client: LLMClient | None = None,
) -> Answer:
    """
    Orchestrierung: Search → Prompt → LLM → Answer mit Quellen.

    Args:
        question: Die Frage an die Knowledgebase.
        config: KB-Konfiguration.
        top_k: Anzahl der Kontext-Chunks.
        book_filter: Optionaler Buch-Filter.
        llm_client: Injizierter LLM-Client. Falls None, wird ein OpenAI-Client erstellt.

    Returns:
        Answer mit Antworttext und Quellen.
    """
    from knowledgebase.core.search import run_search
    from knowledgebase.config import get_openai_api_key

    results = run_search(query=question, config=config, top_k=top_k, book_filter=book_filter)

    if not results:
        return Answer(
            text="Keine relevanten Quellen gefunden. Bitte überprüfe die Frage oder den Index.",
            sources=results,
        )

    if llm_client is None:
        api_key = get_openai_api_key()
        llm_client = make_openai_llm_client(
            api_key=api_key,
            model=config.llm_model,
        )

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(question, results)
    answer_text = llm_client(system_prompt, user_prompt)

    return Answer(text=answer_text, sources=results)
