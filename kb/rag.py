"""Rules questions: retrieve, then answer from the retrieved text with citations (C6).

    uv run python kb/rag.py "Can I use ChatGPT during the programming contest?"

Course sessions 8-9 (kb/rag.py): two functions with a seam between them, the shape of a
LangGraph node: retrieve(state) -> {"documents": [...]}, generate(state) -> {"answer": ...}.
The grounding contract is enforced twice: the prompt says "answer only from the sources",
and the code drops any source number the model invents and turns an answer with no valid
source into "the rulebook does not say".
"""
import sys
import re
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document  # noqa: E402

from config import settings  # noqa: E402
from kb import store  # noqa: E402
from models import build_model, load_prompt  # noqa: E402
from schemas import Citation, RagAnswer  # noqa: E402

NOT_SAID = "The rulebook does not say."


VERSION_WORDS = re.compile(r"\b(older|old|previous|earlier|prior|original|newer|new|current|last year'?s?)"
                           r"(\s+(rulebook|rulebooks|version|versions|edition|rules))?\b|\b(rulebook|version) history\b", re.I)


def search(question: str, k: int | None = None, event: str | None = None, version: str | None = None) -> list[Document]:
    """The best k SECTIONS for a question, each with its versions.

    The 2026 text and its mock v1 twin score almost the same, so taking the top k chunks would
    spend half the slots on twins. Instead: fetch 3x as many, group chunks that share
    (event, section, page), keep the best k groups, and give the model every version in them.
    That is how it can notice that v1 said something different."""
    k = k or settings.RAG_K
    # "older rulebook" says nothing about WHERE the answer is; left in, it pulls in unrelated sections
    question = " ".join(VERSION_WORDS.sub(" ", question).split()) or question
    fields = {name: value for name, value in (("event", event), ("version", version)) if value}
    flt = store.where(**fields) if fields else None      # `version="2026"`: only the current rulebook text
    hits = store.vector_store("dense").similarity_search(question, k=k * 3, filter=flt)
    groups: dict[tuple, list[Document]] = {}
    for d in hits:                                   # hits are best-first, so groups keep that order
        m = d.metadata
        groups.setdefault((m["event"], m["section"], m["page"]), []).append(d)
    kept = list(groups.values())[:k]
    return [d for g in kept for d in sorted(g, key=lambda x: x.metadata["version"] != "2026")]


def format_context(docs: list[Document]) -> str:
    """Each chunk under a number and its metadata, so the model can only cite what it was shown."""
    return "\n\n".join(
        f"[{i}] {d.metadata['event_name']} | {d.metadata['section']} | p.{d.metadata['page']} | "
        f"version {d.metadata['version']} | source_type {d.metadata['source_type']}\n{' '.join(d.page_content.split())}"
        for i, d in enumerate(docs, 1))


@lru_cache
def _model():
    return build_model(schema=RagAnswer)


def retrieve(state: dict) -> dict:
    return {"documents": search(state["question"], event=state.get("event"))}


def generate(state: dict) -> dict:
    docs = state["documents"]
    template, version = load_prompt("rag_prompt")
    prompt = template.format(context=format_context(docs), question=state["question"])
    raw: RagAnswer = _model().invoke(prompt, config={"run_name": "generate", "tags": [f"prompt:rag_prompt:{version}"]})
    # Our code, not the model, decides what counts as a citation.
    valid = [n for n in dict.fromkeys(raw.sources) if 1 <= n <= len(docs)]
    if not raw.grounded or not valid:
        said = "does not say" in raw.answer.lower() or "not say" in raw.answer.lower()
        text = raw.answer if said else f"{NOT_SAID} {raw.answer}".strip()
        return {"answer": text, "grounded": False, "citations": [], "version_note": ""}
    cites = [Citation(**{k: docs[n - 1].metadata[k] for k in Citation.model_fields}) for n in valid]
    return {"answer": raw.answer, "grounded": True, "citations": cites, "version_note": raw.version_note}


def answer_with_rag(question: str, event: str | None = None) -> dict:
    state = {"question": question, "event": event}
    state |= retrieve(state)
    state |= generate(state)
    return state


def render(result: dict) -> str:
    out = [result["answer"]]
    if result["version_note"]:
        out.append(f"(Version note: {result['version_note']})")
    out += [f"  [cite] {c.label()}" for c in result["citations"]]
    return "\n".join(out)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Can I use ChatGPT during the programming contest?"
    result = answer_with_rag(question)
    print(f"Q: {question}\n")
    for d in result["documents"]:
        m = d.metadata
        print(f"  retrieved: {m['event']} | {m['section']} | p.{m['page']} | {m['version']}")
    print(f"\n{render(result)}")
    store.close()
