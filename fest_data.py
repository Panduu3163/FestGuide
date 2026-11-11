"""Mock backend data for the tools: students, events, schedule, FAQ and the registrations database.

    from fest_data import load_students, load_events, load_schedule, load_faq, db

The YAML files are read-only. registrations.db (SQLite) is the one place the assistant
WRITES, and only register_team does that, after an organizer approves (milestone M5).

    uv run python fest_data.py        # (re)create the database and print a summary
"""
import sqlite3
from datetime import date
from functools import lru_cache

import yaml

from config import settings


def _yaml(name: str):
    return yaml.safe_load((settings.DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache
def load_students() -> dict[str, dict]:
    """student id -> record."""
    return {s["id"]: s for s in _yaml("students.yml")["students"]}


@lru_cache
def load_events() -> dict[str, dict]:
    """event key -> record (team size, fee, dates, eligibility)."""
    return _yaml("events.yml")["events"]


@lru_cache
def load_schedule() -> dict[str, dict]:
    """event key -> {date, start, end, source}."""
    return {row["event"]: row for row in _yaml("schedule.yml")["schedule"]}


@lru_cache
def load_faq() -> list[dict]:
    return _yaml("faq.yml")["faq"]


# ---- registrations.db ------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    ref            TEXT PRIMARY KEY,         -- REG-0001 ...
    event          TEXT NOT NULL,            -- key from events.yml
    leader_id      TEXT NOT NULL,
    status         TEXT NOT NULL,            -- approved | rejected
    organizer_note TEXT,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS team_members (
    ref        TEXT NOT NULL REFERENCES teams(ref),
    student_id TEXT NOT NULL,
    PRIMARY KEY (ref, student_id)
);
"""

# A few existing teams so get_registration_status and the clash/one-team rules have something to find.
SEED_TEAMS = [
    ("REG-0001", "debate",           "C243005", "approved", "Fee received (mock)", date(2026, 6, 3).isoformat(),
     ["C243005", "C233007", "C223008"]),
    ("REG-0002", "solo_programming", "C233002", "approved", None,                  date(2026, 6, 4).isoformat(),
     ["C233002"]),
    ("REG-0003", "three_mt",         "T223006", "rejected", "Not a CSE student",   date(2026, 6, 5).isoformat(),
     ["T223006"]),
]


def db() -> sqlite3.Connection:
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def seed_db(reset: bool = False) -> None:
    if reset and settings.db_path.exists():
        settings.db_path.unlink()
    with db() as conn:
        if conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]:
            return
        for ref, event, leader, status, note, created, members in SEED_TEAMS:
            conn.execute("INSERT INTO teams VALUES (?,?,?,?,?,?)", (ref, event, leader, status, note, created))
            conn.executemany("INSERT INTO team_members VALUES (?,?)", [(ref, m) for m in members])


if __name__ == "__main__":
    seed_db(reset=True)
    students, events = load_students(), load_events()
    print(f"students  {len(students)}  (e.g. {next(iter(students.values()))['name']}, mock)")
    print(f"events    {len(events)}")
    for key, e in events.items():
        size = f"{e['team_min']}-{e['team_max']}" if e["team_max"] else "?"
        print(f"  {key:17} team {size:4} fee {str(e['fee_bdt']):>5} date {e['event_date']}")
    print(f"schedule  {len(load_schedule())} rows,  faq {len(load_faq())} entries")
    with db() as conn:
        rows = conn.execute("SELECT ref, event, status FROM teams").fetchall()
    print("registrations.db:", [tuple(r) for r in rows])
