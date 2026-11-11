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

    @property
    def db_path(self) -> Path:
        return self.STATE_DIR / "registrations.db"


settings = Settings()
