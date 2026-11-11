"""Pydantic models: the fixed shapes the model's output must fit (course session 3).

M1 has the answer shapes. M2 adds the intent classifier and the rule extractor here.
"""
from pydantic import BaseModel, Field


class RagAnswer(BaseModel):
    """What the model returns for a rules question. It never writes citations itself:
    it only says which numbered sources it used, and the code turns those into citations."""
    answer: str = Field(description="The answer in plain English, 1-4 sentences, using only the numbered sources.")
    grounded: bool = Field(description="True only if the sources contain the answer. False means 'the rulebook does not say'.")
    sources: list[int] = Field(default_factory=list, description="Numbers of the sources the answer relies on, e.g. [2, 5].")
    version_note: str = Field(default="", description="One sentence if sources of different versions disagree, else empty.")


class Citation(BaseModel):
    """Built by our code from chunk metadata, so it can never be invented by the model."""
    event: str
    event_name: str
    section: str
    page: int
    version: str
    source_type: str

    def label(self) -> str:
        page = f", p.{self.page}" if self.page else ""
        return f"{self.event_name}, {self.section}{page} [{self.version}]"
