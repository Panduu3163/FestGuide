"""Build the knowledge base: load -> chunk -> embed -> write to Qdrant.

    uv run python kb/ingest.py            # build or refresh
    uv run python kb/ingest.py --reset    # drop the collection first

Course session 8 (kb/ingest.py). What goes in:
    rulebooks/clean/*.md          the 7 real rulebooks      version "2026"     source_type "rulebook"
    rulebooks/clean_v1_mock/*.md  mock earlier versions     version "v1-mock"  source_type "mock"
    data/faq.yml                  the mock fest FAQ         version "2026"     source_type "mock"
Every chunk keeps what a citation needs: event, section, page, version, source_type.
Chunk ids come from WHERE the text came from, so running ingest twice changes nothing.
"""
import argparse
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from config import settings  # noqa: E402
from fest_data import load_events, load_faq  # noqa: E402
from kb import store  # noqa: E402

NAMESPACE = uuid.UUID("fe570000-0000-4000-8000-000000002026")   # fixed forever: changing it duplicates every chunk
PAGE = re.compile(r"<!-- p\.(\d+) -->")


def load_rulebook(path: Path, event: str, version: str, source_type: str) -> list[Document]:
    """One Document per (section, page): a section that runs over a page break becomes two,
    so every citation names the page the text really sits on."""
    docs, section, page, buf = [], "Introduction", 1, []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            # The event and section go INTO the embedded text: a chunk that only says "fee: 1050 BDT"
            # does not know which event it belongs to, so a question about "debate fee" cannot find it.
            name = load_events()[event]["name"]
            docs.append(Document(page_content=f"{name} - {section}\n{text}", metadata=dict(
                event=event, event_name=load_events()[event]["name"], section=section, page=page,
                version=version, source_type=source_type)))
        buf.clear()

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("<!--") and not PAGE.match(line):
            continue                                    # the MOCK banner
        if m := PAGE.match(line):
            flush()
            page = int(m.group(1))
        elif line.startswith("## "):
            flush()
            section = line[3:].strip()
        elif not line.startswith("# "):
            buf.append(line)
    flush()
    return docs


def load_faq_docs() -> list[Document]:
    return [Document(page_content=f"Q: {f['q']}\nA: {f['a']}", metadata=dict(
        event="faq", event_name="Fest FAQ (mock)", section=f"FAQ {i}", page=0,
        version="2026", source_type="mock")) for i, f in enumerate(load_faq(), 1)]


def load_corpus() -> list[Document]:
    docs = []
    for event in load_events():
        docs += load_rulebook(settings.RULEBOOK_DIR / "clean" / f"{event}.md", event, "2026", "rulebook")
        docs += load_rulebook(settings.RULEBOOK_DIR / "clean_v1_mock" / f"{event}.md", event, "v1-mock", "mock")
    return docs + load_faq_docs()


def chunk(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE,
                                              chunk_overlap=settings.CHUNK_OVERLAP, add_start_index=True)
    return splitter.split_documents(docs)


def chunk_id(d: Document) -> str:
    m = d.metadata
    return str(uuid.uuid5(NAMESPACE, f"{m['event']}#{m['version']}#{m['section']}#{m['page']}#{m['start_index']}"))


def ingest(reset: bool = False) -> None:
    print(f"embedding model : {settings.EMBED_MODEL}   collection: {settings.collection}")
    if reset and store.client().collection_exists(settings.collection):
        store.client().delete_collection(settings.collection)
        print("reset           : collection dropped")
    store.ensure_collection()
    chunks = chunk(load_corpus())
    ids = [chunk_id(c) for c in chunks]
    store.vector_store("hybrid").add_documents(chunks, ids=ids)
    # Remove points left over from an earlier chunking or an older version of a rulebook file.
    stored, _ = store.client().scroll(settings.collection, limit=10_000, with_payload=False, with_vectors=False)
    stale = [p.id for p in stored if str(p.id) not in set(ids)]
    if stale:
        store.client().delete(settings.collection, points_selector=stale)
        print(f"stale points removed: {len(stale)}")
    total = store.client().count(settings.collection).count
    print(f"chunks          : {len(chunks)}   points stored: {total}")
    by = {}
    for c in chunks:
        key = (c.metadata["event"], c.metadata["version"])
        by[key] = by.get(key, 0) + 1
    for (event, version), n in sorted(by.items()):
        print(f"  {event:17} {version:8} {n:3} chunks")
    store.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ingest(ap.parse_args().reset)
