"""Settings for FestGuide: paths now, model names and limits as later milestones need them.

Course pattern (session 3): one typed settings object instead of constants scattered
around. Every field has a working default; override any of them in .env as FESTGUIDE_<NAME>.
Keys (GEMINI_API_KEY ...) are read by the libraries themselves from the environment.
"""
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")          # puts the keys from .env into os.environ


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FESTGUIDE_", extra="ignore")

    DATA_DIR: Path = ROOT / "data"
    RULEBOOK_DIR: Path = ROOT / "rulebooks"
    STATE_DIR: Path = ROOT / ".state"        # git-ignored: checkpoints and the registrations database
    QDRANT_DIR: Path = ROOT / ".state" / "qdrant"   # git-ignored: the rulebook index (its own folder, so tests can move STATE_DIR)

    # --- models (course session 4: one string, "provider:model") ---
    MODEL: str = "google_genai:gemini-3.5-flash-lite"
    FALLBACK: str = "openrouter:openai/gpt-oss-120b"  # fallback; used only if OPENROUTER_API_KEY is set (the 20b version often failed to return valid structured output)
    MAX_OUTPUT_TOKENS: int = 2048
    REQUEST_TIMEOUT_S: int = 60
    MAX_RETRIES: int = 2
    REQUESTS_PER_SECOND: float = 0.22        # Gemini free tier: 15 requests a minute for this model

    # --- embeddings: "gemini-embedding-001" (Gemini) or "fastembed:BAAI/bge-small-en-v1.5" (local, no key) ---
    EMBED_MODEL: str = "gemini-embedding-001"
    EMBED_DIM: int = 768

    # --- the "pretend today" for deadline checks: the fest dates are in June 2026, so the demo sets
    #     a date inside the fest window (proposal, risk table). Registration for the debate is 2-10 June. ---
    TODAY: date = date(2026, 6, 5)
    MAX_TOOL_STEPS: int = 6                  # the fuse: the tool loop stops after this many model calls
    MAX_QUESTION_CHARS: int = 600            # longer messages are refused (cost and injection limit)
    MAX_TURNS_PER_THREAD: int = 40           # a chat stops after this many messages (cost fuse)

    # --- RAG (course sessions 8-9) ---
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    RAG_K: int = 5
    RETRIEVAL_MODE: str = "dense"       # "dense", "keyword" or "hybrid" (E3; see kb/compare_retrieval.py)
    EVENT_FILTER: bool = True          # E3: when the message names exactly one event, search only that rulebook

    @property
    def db_path(self) -> Path:
        return self.STATE_DIR / "registrations.db"

    @property
    def qdrant_path(self) -> Path:
        return self.QDRANT_DIR

    @property
    def embed_provider(self) -> str:
        return "fastembed" if self.EMBED_MODEL.startswith("fastembed:") else "google_genai"

    @property
    def embed_name(self) -> str:
        return self.EMBED_MODEL.removeprefix("fastembed:")

    @property
    def collection(self) -> str:
        """The collection name carries the embedding model, so two models never share one."""
        return f"rulebooks__{self.embed_name.replace('/', '-')}-{self.EMBED_DIM}"


settings = Settings()
