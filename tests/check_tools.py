"""Check the tools' logic with no model involved: fast, free and exact.

    uv run python tests/check_tools.py

Runs against a throwaway copy of registrations.db (a temp folder), so it never touches your real one.
"""
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

settings.STATE_DIR = Path(tempfile.mkdtemp())          # BEFORE the database is first opened
import fest_data  # noqa: E402
import tools  # noqa: E402

fest_data.seed_db(reset=True)
students = fest_data.load_students()
ARIF, RAFI, TANIA = "C233001", "C233002", "E233003"
BBA = next(i for i, s in students.items() if s["department"] == "BBA")

failures = []


def check(name: str, cond: bool, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)
        print(f"       {detail}")


def elig(student, event):
    return tools.check_eligibility_impl(student, event)


# --- check_eligibility ---
check("CSE student can join the programming contest", elig(ARIF, "solo_programming")["eligible"] is True)
check("EEE student can join Idea Generation (FSE includes EEE)", elig(TANIA, "idea_generation")["eligible"] is True)
r = elig(BBA, "idea_generation")
check("BBA student cannot join Idea Generation (not FSE)", r["eligible"] is False and r["problems"], r)
check("EEE student cannot join 3MT (CSE only)", elig(TANIA, "three_mt")["eligible"] is False)
check("any department may join the debate", elig(BBA, "debate")["eligible"] is True)
check("a name resolves to one student", elig("Rafi", "videography")["student_id"] == RAFI)
check("student already in a team for the event is flagged", elig(RAFI, "solo_programming")["eligible"] is False)
check("unknown student gives an error, not a crash", "error" in elig("Nobody", "debate"))
check("Tech Olympiad answers are labelled MOCK", any("MOCK" in n for n in elig(ARIF, "tech_olympiad")["notes"]))
check("missing deadline is reported as unclear", any("no registration deadline" in u for u in elig(ARIF, "solo_programming")["unclear"]))
settings.TODAY = date(2026, 6, 11)
check("registration closes after the debate deadline (10 June)", elig(BBA, "debate")["eligible"] is False)
settings.TODAY = date(2026, 6, 5)

# --- check_schedule_clash ---
c = tools.check_schedule_clash_impl(["solo_programming", "idea_generation"])
check("programming and Idea Generation: same day, no overlap, MOCK time noted",
      not c["clashes"] and c["same_day_no_overlap"] and any("MOCK" in n for n in c["notes"]), c)
c = tools.check_schedule_clash_impl(["three_mt", "project_showcase"])
check("3MT and Project Showcase overlap on 14 June", len(c["clashes"]) == 1, c)
c = tools.check_schedule_clash_impl(["videography", "debate"])
check("videography and debate are on different days", not c["clashes"] and c["different_days"], c)

# --- get_registration_status: only the asking student ---
check("status shows the student's own registration", [r["ref"] for r in tools.get_registration_status_impl(RAFI)] == ["REG-0002"])
check("student with no registrations gets an empty list", tools.get_registration_status_impl(ARIF) == [])
bound = {t.name: t for t in tools.make_tools(ARIF)}
check("the status tool takes no student argument", not bound["get_registration_status"].args, bound["get_registration_status"].args)
check("register_team is not offered to the model", "register_team" not in bound)

# --- register_team (WRITE) ---
try:
    tools.register_team("idea_generation", ARIF, [RAFI], None, {"status": "pending"})
    check("register_team refuses without approval", False)
except tools.NotApproved:
    check("register_team refuses without approval", True)
approval = {"status": "approved", "note": "EEE allowed this year"}
first = tools.register_team("idea_generation", ARIF, [RAFI, TANIA], None, approval)
check("approved registration is saved with a new reference", first["ref"] == "REG-0004" and not first["already_registered"], first)
again = tools.register_team("idea_generation", ARIF, [RAFI, TANIA], None, approval)
check("running it twice does not add a second team", again["ref"] == "REG-0004" and again["already_registered"], again)
check("the new team shows in each member's status", [r["ref"] for r in tools.get_registration_status_impl(TANIA)] == ["REG-0004"])
for label, args in [("team too big", ("idea_generation", RAFI, ["C233001", "E233003", "T233004"], None)),
                    ("teammate already in another approved team", ("idea_generation", "C233007", [RAFI], None)),
                    ("unknown student", ("debate", RAFI, ["X999999", "C233001"], None))]:
    try:
        tools.register_team(*args, approval)
        check(f"register_team rejects {label}", False)
    except ValueError:
        check(f"register_team rejects {label}", True)
exc_team = tools.register_team("debate", "C243009", [], "solo exception approved", approval)
check("register_team allows out-of-range size when approved with exception_reason", exc_team["ref"] == "REG-0005", exc_team)

# --- draft.build_request + paused_reply for ineligible BBA student ---
from draft import build_request  # noqa: E402
from graph import paused_reply  # noqa: E402
req_bba_solo, msg_bba_solo = build_request("B243013", "Register me for Project Showcase", ["project_showcase"], False, [])
check("BBA solo for Project Showcase reports both team size and BBA ineligibility",
      req_bba_solo is None and "3 to 5" in msg_bba_solo and "BBA" in msg_bba_solo, msg_bba_solo)
req_bba_3mt, msg_bba_3mt = build_request("B243013", "Register me for 3MT", ["three_mt"], False, [])
check("BBA solo for 3MT drafts an exception request with paused_reply surfacing BBA issue",
      req_bba_3mt is not None and req_bba_3mt["kind"] == "exception" and "BBA" in paused_reply(req_bba_3mt),
      (req_bba_3mt, msg_bba_3mt))

# --- non-engineering mocked events eligibility & clashes ---
check("CSE student cannot join Business Case Challenge (BBA only)", elig(ARIF, "business_case")["eligible"] is False)
check("BBA student can join Business Case Challenge", elig("B243013", "business_case")["eligible"] is True)
check("CSE student cannot join English Literary & Eloquence (ELL only)", elig(ARIF, "literary_eloquence")["eligible"] is False)
check("ELL student can join English Literary & Eloquence", elig("L233031", "literary_eloquence")["eligible"] is True)
check("EB student can join Economics & Banking Policy Pitch", elig("N233033", "econ_policy_pitch")["eligible"] is True)
c_econ = tools.check_schedule_clash_impl(["econ_policy_pitch", "videography"])
check("Economics Pitch and Videography overlap on 16 June (MOCK)", len(c_econ["clashes"]) == 1, c_econ)

from kb import store  # noqa: E402
store.close()
print(f"\n{len(failures)} failed")
