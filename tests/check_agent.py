"""Run real messages through the graph and check which tools were called and what came out.

    uv run python tests/check_agent.py

Uses real model calls (about 20, so it takes a couple of minutes on Gemini's free tier).
Runs against a throwaway copy of registrations.db.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402

settings.STATE_DIR = Path(tempfile.mkdtemp())          # before anything opens the database
import fest_data  # noqa: E402
from graph import build_graph, run  # noqa: E402
from kb import store  # noqa: E402

fest_data.seed_db(reset=True)
graph, failures = build_graph(), []


def check(name, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)
        print(f"       {detail}")


def ask(message, student="C233001"):
    return run(graph, message, student, show=lambda *_: None)


def called(state, tool):
    return [c for c in state.get("tool_log", []) if c["tool"] == tool]


s = ask("Do the programming contest and Idea Generation clash?")
check("clash question uses check_schedule_clash", called(s, "check_schedule_clash"), s.get("tool_log"))
check("clash answer says there is no clash", any(w in s["reply"].lower() for w in ("do not clash", "no clash", "not clash", "not overlap")), s["reply"])

s = ask("Do 3MT and Project Showcase clash?")
check("3MT and Project Showcase are reported as a clash", "clash" in s["reply"].lower() and "not clash" not in s["reply"].lower(), s["reply"])

s = ask("Can Tania and I join Idea Generation?")
ids = {c["result"].get("student_id") for c in called(s, "check_eligibility")}
check("eligibility is checked for me and Tania", {"C233001", "E233003"} <= ids, ids)

s = ask("What am I registered for?", "C233002")
check("status uses get_registration_status and shows REG-0002", called(s, "get_registration_status") and "REG-0002" in s["reply"], s["reply"])

s = ask("Register me, Rafi and B243013 for Idea Generation. I am the leader.")
req = s.get("request") or {}
check("a BBA member turns the request into an exception request",
      req.get("kind") == "exception" and any("BBA" in p for p in req.get("problems", [])), req)
check("the request has the 3 team members and a cited rule", len(req.get("member_ids", [])) == 2 and req.get("cited_rules"), req)
check("nothing was written to registrations.db", not fest_data.db().execute("SELECT 1 FROM teams WHERE ref='REG-0004'").fetchall())

s = ask("Register me alone for the debate.")
check("a team of one for the debate (needs 3) is not submitted", s.get("request") is None and "3" in s["reply"], s["reply"])

store.close()
print(f"\n{len(failures)} failed")
