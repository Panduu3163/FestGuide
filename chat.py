"""The student's terminal: chat with FestGuide.

    uv run python chat.py --student C233001            # your chat is remembered between runs
    uv run python chat.py --student C233001 --trace    # also show every graph node and tool call
    uv run python chat.py --student C233001 --new      # start a fresh conversation

Commands inside the chat:  /history  show the saved conversation   /new  start over   /quit  leave

One thread per chat (course session 6): the thread id is "student-<ID>", so closing the program and
coming back continues the same conversation. The program, not the model, decides who is chatting:
the student ID comes from --student and is handed to every node.
"""
import argparse
import sys
import uuid

from fest_data import load_students
from graph import build_graph, run
from kb import store
from memory import checkpointer, history_text, thread_id_for

BUSY = "Sorry, the AI service is busy right now (free-tier limit). Please try again in a minute."


def friendly_error(err: Exception) -> str:
    text = str(err)
    if "RESOURCE_EXHAUSTED" in text or "429" in text or "rate limit" in text.lower():
        return BUSY
    return f"Sorry, something went wrong ({type(err).__name__}). Please try again, or ask an organizer."


def main() -> None:
    ap = argparse.ArgumentParser(description="FestGuide student chat")
    ap.add_argument("--student", required=True, help="your student ID, e.g. C233001 (mock data)")
    ap.add_argument("--trace", action="store_true", help="show graph nodes and tool calls")
    ap.add_argument("--new", action="store_true", help="start a fresh conversation")
    args = ap.parse_args()

    student = load_students().get(args.student.upper())
    if student is None:
        sys.exit(f"Unknown student ID {args.student}. Try one from data/students.yml (mock data).")
    sid = student["id"]
    graph = build_graph(checkpointer())
    thread = thread_id_for(sid, uuid.uuid4().hex[:6] if args.new else None)
    config = {"configurable": {"thread_id": thread}}

    print(f"FestGuide | chatting as {student['name']} ({sid}, {student['department']}) | mock student record")
    earlier = graph.get_state(config).values.get("messages", [])
    if earlier:
        print(f"Resuming your earlier chat ({len(earlier)} messages). Last turns:\n{history_text(earlier, 2)}\n")
    print("Ask about CSE Fest 2026 rules, eligibility, clashes or registration. /quit to leave.\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/history":
            print(history_text(graph.get_state(config).values.get("messages", []), 20) or "(empty)")
            continue
        if text == "/new":
            thread = thread_id_for(sid, uuid.uuid4().hex[:6])
            config = {"configurable": {"thread_id": thread}}
            print("Started a new conversation.")
            continue
        try:
            state = run(graph, text, sid, show=print if args.trace else (lambda _: None), thread_id=thread)
            print(f"\nFestGuide: {state['reply']}\n")
        except Exception as err:                       # a rate limit or outage must not end the chat
            print(f"\nFestGuide: {friendly_error(err)}\n")
    store.close()


if __name__ == "__main__":
    main()
