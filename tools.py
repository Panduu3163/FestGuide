"""The five tools (C3). The model decides WHEN to call them; the code does the exact work.

    search_rules            READ   rulebook passages with event, section, page      (Qdrant)
    check_eligibility       READ   can this student join this event, and why        (students.yml + events.yml)
    check_schedule_clash    READ   do these events overlap in time                  (schedule.yml)
    get_registration_status READ   the ASKING student's own registrations           (registrations.db)
    register_team           WRITE  saves a team; refuses unless an organizer approved (registrations.db)

Course session 5 (tool anatomy: a name, a docstring the model reads, typed arguments, a result the
model can use) and session 7 (authorization: the program, not the model, decides whose records a tool
may touch). make_tools(student_id) binds the read tools to the student chatting, so
get_registration_status takes NO student argument: there is nothing for a model to get wrong or for an
injected instruction to change. register_team is a plain function and is NOT given to the model at all:
only the register_team graph node calls it, after approval.

Every result says when a fact comes from MOCK data, and null in events.yml means "the rulebook does not say".
"""
import json
import sqlite3
from datetime import date

from langchain_core.tools import tool

from config import settings
from fest_data import db, load_events, load_schedule, load_students
from schemas import EventKey


# ---- helpers ------------------------------------------------------------------------------------

ME_WORDS = {"me", "i", "myself", "my", "self", "mine"}

def resolve_student(ref: str) -> tuple[dict | None, str | None]:
    """A student ID ("C233002") or a name ("Rafi" / "Rafi Ahmed") -> (record, None), or (None, why not)."""
    students, ref = load_students(), ref.strip()
    if ref.upper() in students:
        return students[ref.upper()], None
    hits = [s for s in students.values() if ref.lower() in s["name"].lower()]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, f"no student matches '{ref}'"
    return None, f"'{ref}' matches {len(hits)} students ({', '.join(h['id'] for h in hits)}); give the ID"


def _mock_note(event: dict, *fields: str) -> list[str]:
    used = [f for f in fields if f in (event.get("mock_fields") or [])]
    return [f"{', '.join(used)} for this event is MOCK data (the rulebook does not state it)"] if used else []


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# ---- the tools' logic (plain functions, easy to test) ---------------------------------------------

def search_rules_impl(question: str, event: str | None = None) -> list[dict]:
    from kb.rag import search          # imported here: tools.py must load without opening Qdrant
    return [{"source": f"{d.metadata['event_name']}, {d.metadata['section']}, p.{d.metadata['page']} [{d.metadata['version']}]",
             "source_type": d.metadata["source_type"],
             "text": " ".join(d.page_content.split())[:420]} for d in search(question, k=3, event=event)]


def check_eligibility_impl(student: str, event: str) -> dict:
    ev = load_events().get(event)
    person, why = resolve_student(student)
    if ev is None:
        return {"error": f"unknown event '{event}'"}
    if person is None:
        return {"error": why}
    ok, no, unclear = [], [], []

    depts = ev["eligible_departments"]
    if depts == "all":
        ok.append("open to students of all departments")
    elif depts is None:
        unclear.append("the rulebook does not say which departments may join")
    elif person["department"] in depts:
        ok.append(f"{person['department']} is among the allowed departments ({', '.join(depts)})")
    else:
        no.append(f"{person['department']} is not among the allowed departments ({', '.join(depts)})")

    if ev["eligible_level"] == "undergraduate" and person["level"] != "undergraduate":
        no.append("the event is for undergraduate students only")

    if ev["reg_deadline"] and settings.TODAY > ev["reg_deadline"]:
        no.append(f"registration closed on {ev['reg_deadline']}")
    elif ev["reg_deadline"]:
        ok.append(f"registration is open until {ev['reg_deadline']}")
    else:
        unclear.append("the rulebook gives no registration deadline")
    if ev["event_date"] and settings.TODAY > ev["event_date"]:
        no.append(f"the event took place on {ev['event_date']}")

    with db() as conn:                                     # one participant, one team per event
        row = conn.execute("""SELECT t.ref FROM teams t JOIN team_members m ON m.ref = t.ref
                              WHERE m.student_id = ? AND t.event = ? AND t.status = 'approved'""",
                           (person["id"], event)).fetchone()
    if row:
        no.append(f"already in a registered team for this event ({row['ref']}); a student cannot join two teams")

    eligible = False if no else (None if unclear and depts is None else True)
    return {"student_id": person["id"], "name": person["name"], "department": person["department"],
            "event": event, "event_name": ev["name"], "eligible": eligible,
            "ok": ok, "problems": no, "unclear": unclear,
            "notes": _mock_note(ev, "eligible_departments", "reg_deadline", "event_date") + ["student record is MOCK data"]}


def check_schedule_clash_impl(events: list[str]) -> dict:
    schedule, events = load_schedule(), list(dict.fromkeys(events))
    rows, notes = {}, []
    for e in events:
        row = schedule.get(e)
        if row is None or row["date"] is None:
            notes.append(f"{e}: no date or time is known")
        else:
            rows[e] = row
            if row["source"] == "mock":
                notes.append(f"{e}: its time ({row['start']}-{row['end']}) is MOCK data; the rulebook gives none")
    clashes, same_day, separate = [], [], []
    names = list(rows)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ra, rb = rows[a], rows[b]
            pair = {"events": [a, b], "date": str(ra["date"])}
            if ra["date"] != rb["date"]:
                separate.append({"events": [a, b], "dates": [str(ra["date"]), str(rb["date"])]})
            elif _minutes(ra["start"]) < _minutes(rb["end"]) and _minutes(rb["start"]) < _minutes(ra["end"]):
                clashes.append(pair | {"times": [f"{ra['start']}-{ra['end']}", f"{rb['start']}-{rb['end']}"]})
            else:
                same_day.append(pair | {"times": [f"{ra['start']}-{ra['end']}", f"{rb['start']}-{rb['end']}"]})
    return {"clashes": clashes, "same_day_no_overlap": same_day, "different_days": separate,
            "notes": notes + ["times can change; confirm with the organizers"]}


def get_registration_status_impl(student_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute("""SELECT t.ref, t.event, t.leader_id, t.status, t.organizer_note FROM teams t
                               JOIN team_members m ON m.ref = t.ref WHERE m.student_id = ?
                               ORDER BY t.ref""", (student_id,)).fetchall()
    return [{"ref": r["ref"], "event": r["event"], "you_are": "leader" if r["leader_id"] == student_id else "member",
             "status": r["status"], "organizer_note": r["organizer_note"]} for r in rows]


class NotApproved(Exception):
    pass


def register_team(event: str, leader_id: str, member_ids: list[str], exception_reason: str | None,
                  approval: dict) -> dict:
    """WRITE. Saves a team in registrations.db, and only if an organizer approved.

    Safe to run twice: on resume the graph node can run again from its first line, so an
    existing approved team for the same event and leader is returned instead of added again."""
    if not approval or approval.get("status") != "approved":
        raise NotApproved("register_team needs an organizer's approval")
    ev = load_events().get(event)
    members = list(dict.fromkeys([leader_id, *member_ids]))
    if ev is None or any(m not in load_students() for m in members):
        raise ValueError("unknown event or student")
    if ev["team_min"] and ev["team_max"] and not ev["team_min"] <= len(members) <= ev["team_max"]:
        raise ValueError(f"team size {len(members)} is outside {ev['team_min']}-{ev['team_max']}")
    with db() as conn:
        existing = conn.execute("SELECT ref, status, organizer_note FROM teams WHERE event = ? AND leader_id = ? "
                                "AND status = 'approved'", (event, leader_id)).fetchone()
        if existing:
            return {"ref": existing["ref"], "status": existing["status"], "organizer_note": existing["organizer_note"],
                    "already_registered": True}
        last = conn.execute("SELECT MAX(CAST(SUBSTR(ref, 5) AS INTEGER)) FROM teams").fetchone()[0] or 0
        ref = f"REG-{last + 1:04d}"
        conn.execute("INSERT INTO teams VALUES (?,?,?,?,?,?)",
                     (ref, event, leader_id, "approved", approval.get("note") or exception_reason,
                      settings.TODAY.isoformat()))
        conn.executemany("INSERT INTO team_members VALUES (?,?)", [(ref, m) for m in members])
    return {"ref": ref, "status": "approved", "organizer_note": approval.get("note"), "already_registered": False}


# ---- what the model sees: LangChain tools bound to the asking student ---------------------------

def make_tools(student_id: str) -> list:
    """The READ tools for the student chatting. (register_team is deliberately not here.)"""

    @tool
    def search_rules(question: str, event: EventKey | None = None) -> str:
        """Search the CSE Fest 2026 rulebooks. Returns the best passages with event, section and page.
        Use `event` to search inside one rulebook only."""
        return json.dumps(search_rules_impl(question, event))

    @tool
    def check_eligibility(student: str, event: EventKey) -> str:
        """Check whether ONE student may join ONE event: department, level, deadline, and whether they are
        already in a team for it. `student` is a student ID (like C233002), a first name from the user's message,
        or the word "me" for the asking student. Call once per person."""
        if student.strip().lower() in ME_WORDS:                 # "me" is the asking student, never a name search
            student = student_id
        return json.dumps(check_eligibility_impl(student, event), default=str)

    @tool
    def check_schedule_clash(events: list[EventKey]) -> str:
        """Check whether two or more events overlap in time. Returns clashes, same-day events that do not overlap,
        and notes where a time is missing or MOCK."""
        return json.dumps(check_schedule_clash_impl(events), default=str)

    @tool
    def get_registration_status() -> str:
        """The asking student's own registrations and their status. Takes no argument: it can only ever
        show the student who is chatting, never anyone else."""
        return json.dumps(get_registration_status_impl(student_id), default=str)

    return [search_rules, check_eligibility, check_schedule_clash, get_registration_status]
