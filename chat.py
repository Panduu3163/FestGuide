"""The student's terminal: chat with FestGuide.

    uv run python chat.py --student C233001            # your chat is remembered between runs
    uv run python chat.py --student C233001 --trace    # also show every graph node and tool call
    uv run python chat.py --student C233001 --new      # start a fresh conversation
    uv run python chat.py --student C233001 --langsmith   # send every run to LangSmith (needs LANGSMITH_API_KEY in .env)

Commands inside the chat:  /status  your requests waiting for an organizer   /history  the saved conversation
                           /new  start a fresh conversation   /quit  leave

One thread per chat (course session 6): the thread id is "student-<ID>", so closing the program and
coming back continues the same conversation. The program, not the model, decides who is chatting:
the student ID comes from --student and is handed to every node.

A registration or exception request pauses at the organizer's approval gate (the other terminal,
organizer.py). While it waits, a small background watcher checks the saved state every two seconds and
prints the organizer's decision as soon as it arrives, even if you restarted this program meanwhile.
"""
import argparse
import os
import sys
import threading
import time
import uuid

from approvals import is_waiting, last_reply, pending_for_student
from fest_data import load_students
from graph import build_graph, run
from kb import store
from memory import checkpointer, history_text, thread_id_for

BUSY = "Sorry, the AI service is busy right now (free-tier limit). Please try again in a minute."
WAITING = ("Your request is waiting for an organizer's decision. Until then you can use /status, "
           "/history, or /new to chat about something else in a fresh conversation.")


def friendly_error(err: Exception) -> str:
    text = str(err)
    if "RESOURCE_EXHAUSTED" in text or "429" in text or "rate limit" in text.lower():
        return BUSY
    return f"Sorry, something went wrong ({type(err).__name__}). Please try again, or ask an organizer."


class Watcher:
    """Background thread: tells the student when an organizer has decided a request they are waiting for."""

    def __init__(self):
        self.threads: set[str] = set()
        self.lock = threading.Lock()
        self.started = False

    def add(self, thread_id: str) -> None:
        with self.lock:
            self.threads.add(thread_id)
            if not self.started:
                self.started = True
                threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        graph = build_graph(checkpointer())               # its own connection: sqlite objects stay in their thread
        while True:
            time.sleep(2)
            with self.lock:
                waiting = list(self.threads)
            for tid in waiting:
                try:
                    if not is_waiting(graph, tid):
                        with self.lock:
                            self.threads.discard(tid)
                        print(f"\n\n[Organizer decided]\nFestGuide: {last_reply(graph, tid)}\n\nYou: ", end="", flush=True)
                except Exception:
                    pass                                    # a busy file: try again in two seconds


def main() -> None:
    ap = argparse.ArgumentParser(description="FestGuide student chat")
    ap.add_argument("--student", required=True, help="your student ID, e.g. C233001 (mock data)")
    ap.add_argument("--trace", action="store_true", help="show graph nodes and tool calls")
    ap.add_argument("--new", action="store_true", help="start a fresh conversation")
    ap.add_argument("--langsmith", action="store_true", help="trace every run in LangSmith")
    args = ap.parse_args()
    if args.langsmith:                                  # must be set before the first model call
        os.environ["LANGSMITH_TRACING"] = "true"

    student = load_students().get(args.student.upper())
    if student is None:
        sys.exit(f"Unknown student ID {args.student}. Try one from data/students.yml (mock data).")
    sid = student["id"]
    saver = checkpointer()
    graph = build_graph(saver)
    thread = thread_id_for(sid, uuid.uuid4().hex[:6] if args.new else None)
    watcher = Watcher()

    print(f"FestGuide | chatting as {student['name']} ({sid}, {student['department']}) | mock student record")
    earlier = graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", [])
    if earlier:
        print(f"Resuming your earlier chat ({len(earlier)} messages). Last turns:\n{history_text(earlier, 2)}\n")
    for p in pending_for_student(graph, saver, sid):
        print(f"Waiting for an organizer: {p['request']['kind']} request for {p['request']['event_name']}.")
        watcher.add(p["thread_id"])
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
            print(history_text(graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", []), 20) or "(empty)")
            continue
        if text == "/status":
            mine = pending_for_student(graph, saver, sid)
            print("\n".join(f"- {p['request']['kind']} request for {p['request']['event_name']}: waiting for an organizer"
                            for p in mine) or "Nothing is waiting for an organizer.")
            continue
        if text == "/new":
            thread = thread_id_for(sid, uuid.uuid4().hex[:6])
            print("Started a new conversation.")
            continue
        if is_waiting(graph, thread):          # a new message would discard the paused request: refuse it
            print(f"\nFestGuide: {WAITING}\n")
            continue
        try:
            state = run(graph, text, sid, show=print if args.trace else (lambda _: None), thread_id=thread)
            print(f"\nFestGuide: {state['reply']}\n")
            if state.get("interrupted"):
                watcher.add(thread)
        except Exception as err:                       # a rate limit or outage must not end the chat
            print(f"\nFestGuide: {friendly_error(err)}\n")
    store.close()


if __name__ == "__main__":
    main()
