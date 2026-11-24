"""Mock backend data for the tools: students, events, schedule, FAQ and the registrations database.

    from fest_data import load_students, load_events, load_schedule, load_faq, db

The YAML files are read-only. registrations.db (SQLite) is the one place the assistant
WRITES, and only register_team does that, after an organizer approves (milestone M5).

    uv run python fest_data.py        # (re)create the database and print a summary
"""
import re
import sqlite3
from datetime import date
from functools import lru_cache

import yaml

from config import settings


def _yaml(name: str):
    return yaml.safe_load((settings.DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache
def _seed_students() -> dict[str, dict]:
    return {s["id"]: {**s, "custom": False} for s in _yaml("students.yml")["students"]}


@lru_cache
def load_students() -> dict[str, dict]:
    """student id -> record (seed YAML students + live custom_students from SQLite)."""
    out = dict(_seed_students())
    if settings.db_path.exists():
        with db() as conn:
            rows = conn.execute("SELECT id, name, department, year, level, gender, phone FROM custom_students ORDER BY created_at, id").fetchall()
        for r in rows:
            out[r["id"]] = {
                "id": r["id"], "name": r["name"], "department": r["department"],
                "year": r["year"], "level": r["level"], "gender": r["gender"],
                "phone": r["phone"], "source": "live", "custom": True,
            }
    return out


DEPT_CANON = {"CSE": "CSE", "EEE": "EEE", "ETE": "ETE", "CE": "CE", "CCE": "CCE",
              "PHARMACY": "Pharmacy", "BBA": "BBA", "ELL": "ELL", "EB": "EB"}


def create_student(student_id: str, name: str, department: str, year: int = 1,
                   level: str = "undergraduate", gender: str = "male", phone: str = "") -> dict:
    """Create a live student account in SQLite for demos/sign-up."""
    sid = (student_id or "").strip().upper()
    clean_name = " ".join((name or "").split())
    dept_raw = (department or "").strip()
    dept = DEPT_CANON.get(dept_raw.upper(), dept_raw.upper())
    lvl = (level or "undergraduate").strip().lower()
    gnd = (gender or "male").strip().lower()
    if not re.fullmatch(r"[A-Z]{1,4}\d{3,8}", sid):
        raise ValueError("Student ID must look like C223163 or B243013 (1-4 letters + 3-8 digits).")
    if len(clean_name) < 2:
        raise ValueError("Please enter the student's full name.")
    if not dept:
        raise ValueError("Please select a department.")
    if lvl not in ("undergraduate", "postgraduate"):
        raise ValueError("Level must be undergraduate or postgraduate.")
    if not 1 <= int(year) <= 5:
        raise ValueError("Year must be between 1 and 5.")
    if sid in _seed_students():
        raise ValueError(f"{sid} is a built-in demo student; choose another ID to create a new account.")
    with db() as conn:
        if conn.execute("SELECT 1 FROM custom_students WHERE id = ?", (sid,)).fetchone():
            raise ValueError(f"Student ID {sid} already exists. Select it from the switcher to sign in.")
        conn.execute(
            "INSERT INTO custom_students VALUES (?,?,?,?,?,?,?,?)",
            (sid, clean_name, dept, int(year), lvl, gnd, phone.strip(), date.today().isoformat()),
        )
    load_students.cache_clear()
    return load_students()[sid]


def delete_student(student_id: str) -> None:
    """Delete a live-created student account (built-in seed students cannot be deleted)."""
    sid = (student_id or "").strip().upper()
    if sid in _seed_students():
        raise ValueError("Built-in demo students cannot be deleted.")
    with db() as conn:
        cur = conn.execute("DELETE FROM custom_students WHERE id = ?", (sid,))
        if cur.rowcount == 0:
            raise LookupError(f"Custom student {sid} not found.")
        conn.execute("DELETE FROM team_members WHERE student_id = ?", (sid,))
        conn.execute("DELETE FROM teams WHERE leader_id = ? AND ref NOT IN ('REG-0001','REG-0002','REG-0003')", (sid,))
    load_students.cache_clear()


def clear_custom_students() -> int:
    """Delete all live-created student accounts."""
    with db() as conn:
        n = conn.execute("DELETE FROM custom_students").rowcount
    load_students.cache_clear()
    return n


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
CREATE TABLE IF NOT EXISTS custom_students (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    department TEXT NOT NULL,
    year       INTEGER NOT NULL DEFAULT 1,
    level      TEXT NOT NULL DEFAULT 'undergraduate',
    gender     TEXT NOT NULL DEFAULT 'male',
    phone      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
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
    load_students.cache_clear()
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
