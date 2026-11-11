"""Settings for FestGuide: paths now, model names and limits as later milestones need them.

Course pattern (session 3): one typed settings object instead of constants scattered
around. Every field has a working default; override any of them in .env as FESTGUIDE_<NAME>.
Keys (GEMINI_API_KEY ...) are read by the libraries themselves from the environment.
"""
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")          # puts the keys from .env into os.environ


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FESTGUIDE_", extra="ignore")

    DATA_DIR: Path = ROOT / "data"
    RULEBOOK_DIR: Path = ROOT / "rulebooks"
    STATE_DIR: Path = ROOT / ".state"        # git-ignored: Qdrant index, checkpoints, database

    # --- models (course session 4: one string, "provider:model") ---
    MODEL: str = "google_genai:gemini-3.5-flash-lite"
    FALLBACK: str = "openrouter:openai/gpt-oss-20b"   # used only if its key is set (milestone M7)
    MAX_OUTPUT_TOKENS: int = 2048
    REQUEST_TIMEOUT_S: int = 60
    MAX_RETRIES: int = 2

    # --- embeddings: "gemini-embedding-001" (Gemini) or "fastembed:BAAI/bge-small-en-v1.5" (local, no key) ---
    EMBED_MODEL: str = "gemini-embedding-001"
    EMBED_DIM: int = 768

    # --- RAG (course sessions 8-9) ---
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    RAG_K: int = 5

    @property
    def db_path(self) -> Path:
        return self.STATE_DIR / "registrations.db"

    @property
    def qdrant_path(self) -> Path:
        return self.STATE_DIR / "qdrant"

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
