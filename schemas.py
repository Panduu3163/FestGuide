"""Pydantic models: the fixed shapes the model's output must fit (course session 3).

    RagAnswer / Citation   the answer to a rules question (M1)
    Intent                 the classifier's result: where a message goes next (C1)
    EventRules             what the offline extractor reads out of one rulebook (C1)
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# The seven events, by the same keys as data/events.yml.
EventKey = Literal["solo_programming", "videography", "debate", "tech_olympiad",
                   "idea_generation", "three_mt", "project_showcase"]


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


class Intent(BaseModel):
    """The classify node's result. `intent` picks the route; the rest are facts for later nodes."""
    intent: Literal["rules", "plan", "register", "other"] = Field(
        description="rules = a question about fest rules, fees, dates, eligibility text. "
                    "plan = check whether the student can join events, or whether events clash, or their own registration status. "
                    "register = the student wants to register a team, or asks for an exception. "
                    "other = anything not about the CSE Fest 2026 events.")
    events: list[EventKey] = Field(default_factory=list, description="Events the message names, by key. Empty if none.")
    student_id: str | None = Field(default=None, description="A student ID like C233001 if the message gives one, else null.")
    wants_exception: bool = Field(default=False, description="True if the student asks for an exception, waiver or special permission.")
    reason: str = Field(description="One short sentence: why this intent.")


class EventRules(BaseModel):
    """Facts the extractor reads from ONE rulebook. A value the rulebook does not state stays null."""
    team_min: int | None = Field(default=None, description="Smallest allowed team size.")
    team_max: int | None = Field(default=None, description="Largest allowed team size.")
    fee_bdt: int | None = Field(default=None, description="Registration fee in BDT, as a number.")
    fee_per: Literal["participant", "team"] | None = Field(default=None, description="Whether the fee is per participant or per team.")
    event_date: date | None = Field(default=None, description="The (first) competition date.")
    reg_deadline: date | None = Field(default=None, description="Last day to register.")
    all_departments: bool | None = Field(default=None, description="True if students of every department may join.")
    departments: list[str] = Field(default_factory=list, description="Allowed departments if limited, e.g. ['CSE']. Empty if all or unknown.")
    eligible_level: Literal["any", "undergraduate"] | None = Field(default=None, description="'undergraduate' only if the rulebook limits it to undergraduates.")
    one_team_only: bool | None = Field(default=None, description="True if a student may join only one team or entry.")
    evidence: list[str] = Field(default_factory=list, description="Short VERBATIM quotes from the rulebook that support the values above.")
