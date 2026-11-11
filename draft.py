"""Build the registration or exception request the organizer will see (the draft_request node).

The model only helps find WHO is in the team (it resolves the names in the message). Everything the
organizer relies on is recomputed here in plain code: the team, the eligibility of every member, the
team-size check and the cited rule. A model slip can therefore not hide a problem from the organizer.

build_request(...) returns (request, None) when a human should decide, or (None, message) when the
request cannot even be submitted (no single event, unknown person, wrong team size).
"""
from fest_data import load_events
from tools import check_eligibility_impl, search_rules_impl


def build_request(student_id: str, question: str, events: list[str], wants_exception: bool,
                  log: list[dict]) -> tuple[dict | None, str | None]:
    if len(events) != 1:
        return None, "Which single event do you want to register for? Please name one event."
    event = events[0]
    ev = load_events()[event]

    ids, unknown = [student_id], []
    for entry in log:                                     # people the tool loop found, in order
        res = entry["result"]
        if entry["tool"] == "check_eligibility" and isinstance(res, dict):
            if "student_id" in res and res["student_id"] not in ids:
                ids.append(res["student_id"])
            elif "error" in res:
                unknown.append(res["error"])
    if unknown:
        return None, "I could not identify everyone in your team: " + "; ".join(unknown) + ". Please give student IDs."

    lo, hi = ev["team_min"], ev["team_max"]
    if lo and hi and not lo <= len(ids) <= hi:
        size = f"{lo}" if lo == hi else f"{lo} to {hi}"
        return None, f"{ev['name']} needs a team of {size}, but you listed {len(ids)}. Please correct the team."

    checks = [check_eligibility_impl(i, event) for i in ids]
    problems = [f"{c['name']} ({c['student_id']}, {c['department']}): {p}" for c in checks for p in c["problems"]]
    # The organizer must always see the cited rule, so the code searches for it itself instead of
    # hoping the model called search_rules.
    rules = search_rules_impl(f"who may join and how many members: {ev['name']} eligibility and team size", event)[:2]
    kind = "exception" if problems or wants_exception else "registration"
    return {
        "kind": kind, "event": event, "event_name": ev["name"],
        "leader_id": student_id, "member_ids": ids[1:],
        "student_message": question,
        "exception_reason": question if kind == "exception" else None,
        "checks": [{"student": f"{c['name']} ({c['student_id']}, {c['department']})", "eligible": c["eligible"],
                    "problems": c["problems"], "unclear": c["unclear"]} for c in checks],
        "problems": problems,
        "cited_rules": rules,
        "fee_note": (f"fee {ev['fee_bdt']} BDT per {ev['fee_per']}" if ev["fee_bdt"] else "no fee stated in the rulebook")
                    + (" (MOCK)" if "fee_bdt" in (ev.get("mock_fields") or []) else ""),
    }, None
