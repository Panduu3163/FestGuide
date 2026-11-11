"""The organizer's terminal: see requests waiting for approval, approve with a note or reject with a reason.

    uv run python organizer.py                 # go through the waiting requests one by one
    uv run python organizer.py --watch         # stay open and show new requests as students send them
    uv run python organizer.py --list          # just list them
    uv run python organizer.py --approve THREAD --note "EEE allowed this year"
    uv run python organizer.py --reject  THREAD --reason "Fee not paid"

This is the second terminal of the demo. It never calls a model: it reads the saved (checkpointed) runs
from .state/checkpoints.sqlite and resumes one with the organizer's decision (approvals.py). The student's
program can be closed meanwhile: the request stays saved and the student sees the result next time.
"""
import argparse
import time

from approvals import decide, pending
from fest_data import load_students
from graph import build_graph
from memory import checkpointer


def show(p: dict, n: int | None = None) -> None:
    req, students = p["request"], load_students()
    who = lambda i: f"{students[i]['name']} ({i}, {students[i]['department']})" if i in students else i  # noqa: E731
    print("\n" + "=" * 78)
    print(f"{'#' + str(n) + '  ' if n else ''}{req['kind'].upper()} REQUEST  |  {req['event_name']}  |  thread {p['thread_id']}")
    print(f"Leader : {who(req['leader_id'])}")
    for m in req["member_ids"]:
        print(f"Member : {who(m)}")
    print(f"Fee    : {req['fee_note']}")
    print("Checks :")
    for c in req["checks"]:
        flag = {True: "eligible", False: "NOT eligible", None: "unclear"}[c["eligible"]]
        print(f"  - {c['student']}: {flag}")
        for prob in c["problems"]:
            print(f"      problem: {prob}")
        for note in c["unclear"]:
            print(f"      unclear: {note}")
    for r in req["cited_rules"]:
        print(f"Rule   : [{r['source']}]\n         {r['text'][:260]}")
    print(f"Student wrote: \"{req['student_message']}\"")
    print("=" * 78)


def interactive(graph, saver) -> None:
    items = pending(graph, saver)
    if not items:
        print("No requests are waiting.")
        return
    for i, p in enumerate(items, 1):
        show(p, i)
        while True:
            choice = input("[a]pprove  [r]eject  [s]kip  [q]uit > ").strip().lower()
            if choice in ("a", "approve"):
                note = input("Note for the student (optional) > ").strip()
                out = decide(graph, p["thread_id"], "approved", note)
                print(f"-> approved. Student will see: {out['reply']}")
                break
            if choice in ("r", "reject"):
                reason = ""
                while not reason:
                    reason = input("Reason for the student (required) > ").strip()
                out = decide(graph, p["thread_id"], "rejected", reason)
                print(f"-> rejected. Student will see: {out['reply']}")
                break
            if choice in ("s", "skip"):
                break
            if choice in ("q", "quit"):
                return


def main() -> None:
    ap = argparse.ArgumentParser(description="FestGuide organizer terminal")
    ap.add_argument("--watch", action="store_true", help="keep waiting for new requests")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--approve", metavar="THREAD")
    ap.add_argument("--reject", metavar="THREAD")
    ap.add_argument("--note", default="")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    saver = checkpointer()
    graph = build_graph(saver)

    if args.approve or args.reject:
        thread = args.approve or args.reject
        try:
            out = decide(graph, thread, "approved" if args.approve else "rejected", args.note if args.approve else args.reason)
        except (ValueError, LookupError) as err:
            raise SystemExit("Not done: " + (err.errors()[0]["msg"].removeprefix("Value error, ") if hasattr(err, "errors") else str(err)))
        print(out["reply"])
    elif args.list:
        items = pending(graph, saver)
        for i, p in enumerate(items, 1):
            show(p, i)
        print(f"\n{len(items)} request(s) waiting.")
    elif args.watch:
        print("Organizer terminal. Waiting for requests (Ctrl+C to leave)...")
        try:
            while True:
                if pending(graph, saver):
                    interactive(graph, saver)
                    print("\nWaiting for requests (Ctrl+C to leave)...")
                time.sleep(2)
        except KeyboardInterrupt:
            print()
    else:
        interactive(graph, saver)


if __name__ == "__main__":
    main()
