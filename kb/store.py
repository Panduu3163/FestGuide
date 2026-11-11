"""Opening the vector store: one door, used by ingest, search and every tool.

Course session 8 (kb/store.py), trimmed. Embedded Qdrant keeps the index in a folder on disk,
so there is no server to run. Each chunk gets two vectors:
    "dense"  meaning (the embedding model), and
    "bm25"   keywords, computed on the CPU with no key.
"""
import logging
import threading
import time
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models

from config import settings

DENSE, SPARSE = "dense", "bm25"
logging.getLogger("pypdf").setLevel(logging.ERROR)


class FastEmbedEmbeddings(Embeddings):
    """The keyless option: a small embedding model on your CPU (set FESTGUIDE_EMBED_MODEL=fastembed:...)."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name)

    def embed_documents(self, texts):
        return [v.tolist() for v in self.model.embed(texts)]

    def embed_query(self, text):
        return next(iter(self.model.query_embed(text))).tolist()


class PacedEmbeddings(Embeddings):
    """Gemini's free tier allows 100 embedding texts a minute. Indexing sends 150+, so this
    counts the texts sent in the last 60 seconds and waits when the next batch would go over."""

    LIMIT, WINDOW_S = 95, 62

    def __init__(self, inner: Embeddings):
        self.inner = inner
        self.sent: list[tuple[float, int]] = []          # (time, how many texts)

    def embed_documents(self, texts):
        out = []
        for i in range(0, len(texts), 50):
            group = texts[i:i + 50]
            while True:
                now = time.time()
                self.sent = [(t, n) for t, n in self.sent if now - t < self.WINDOW_S]
                if sum(n for _, n in self.sent) + len(group) <= self.LIMIT:
                    break
                wait = self.WINDOW_S - (now - self.sent[0][0])
                print(f"  (free-tier pacing: waiting {wait:.0f}s)", flush=True)
                time.sleep(max(wait, 1))
            for attempt in range(4):                       # a 429 can come from earlier runs too: wait and retry
                try:
                    out += self.inner.embed_documents(group)
                    break
                except Exception as err:
                    if "RESOURCE_EXHAUSTED" not in str(err) or attempt == 3:
                        raise
                    print("  (quota hit: waiting 35s)", flush=True)
                    time.sleep(35)
            self.sent.append((time.time(), len(group)))
        return out

    def embed_query(self, text):
        return self.inner.embed_query(text)


@lru_cache
def embeddings() -> Embeddings:
    if settings.embed_provider == "fastembed":
        return FastEmbedEmbeddings(settings.embed_name)
    from langchain.embeddings import init_embeddings
    return PacedEmbeddings(init_embeddings(f"google_genai:{settings.embed_name}",
                                           output_dimensionality=settings.EMBED_DIM))


@lru_cache
def bm25() -> FastEmbedSparse:
    return FastEmbedSparse(model_name="Qdrant/bm25")


_client: QdrantClient | None = None
_lock = threading.Lock()


def client() -> QdrantClient:
    """One client per process: embedded Qdrant allows only one per folder."""
    global _client
    with _lock:
        if _client is None:
            settings.qdrant_path.mkdir(parents=True, exist_ok=True)
            _client = QdrantClient(path=str(settings.qdrant_path))
        return _client


def close() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None


def ensure_collection() -> None:
    if not client().collection_exists(settings.collection):
        client().create_collection(
            settings.collection,
            vectors_config={DENSE: models.VectorParams(size=settings.EMBED_DIM, distance=models.Distance.COSINE)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )


def vector_store(mode: str = "dense") -> QdrantVectorStore:
    """LangChain's view of the collection. mode: "dense", "keyword" or "hybrid" (writing uses hybrid)."""
    rm = {"dense": RetrievalMode.DENSE, "keyword": RetrievalMode.SPARSE, "hybrid": RetrievalMode.HYBRID}[mode]
    return QdrantVectorStore(
        client=client(), collection_name=settings.collection,
        embedding=None if mode == "keyword" else embeddings(),
        sparse_embedding=None if mode == "dense" else bm25(),
        retrieval_mode=rm, vector_name=DENSE, sparse_vector_name=SPARSE)


def where(**fields: str) -> models.Filter:
    """A payload filter on metadata, e.g. where(event="debate"). Used by E3 (event filter)."""
    return models.Filter(must=[models.FieldCondition(key=f"metadata.{k}", match=models.MatchValue(value=v))
                               for k, v in fields.items()])
