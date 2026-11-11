"""Finding and answering the requests that are waiting for an organizer (E1).

A pending request is not stored anywhere special. When the approval_gate node calls interrupt(), LangGraph
saves the whole run in the checkpoint file and stops. The "inbox" is simply: every thread in that file whose
saved run is paused at an interrupt. Because the checkpoint is on disk, the request survives a restart of
either program, and the organizer terminal can answer it from a different process.

    pending(graph, saver)                  all waiting requests: thread, student, the drafted request
    pending_for_student(graph, saver, id)  the same, for one student
    decide(graph, thread_id, status, note) resume the paused run with the organizer's decision; returns the final state

Course session 11 (interrupt lifecycle: pause, save, resume with Command).
"""
from langgraph.types import Command

from schemas import Decision


def thread_ids(saver) -> list[str]:
    with saver.lock:
        rows = saver.conn.execute("SELECT DISTINCT thread_id FROM checkpoints").fetchall()
    return [r[0] for r in rows]


def pending(graph, saver) -> list[dict]:
    found = []
    for tid in thread_ids(saver):
        snap = graph.get_state({"configurable": {"thread_id": tid}})
        for task in snap.tasks:
            for it in task.interrupts:
                if isinstance(it.value, dict) and it.value.get("kind") == "approval":
                    found.append({"thread_id": tid, "student_id": it.value["student_id"],
                                  "request": it.value["request"], "asked_at": snap.created_at})
    return sorted(found, key=lambda p: p["asked_at"] or "")


def pending_for_student(graph, saver, student_id: str) -> list[dict]:
    return [p for p in pending(graph, saver) if p["student_id"] == student_id]


def decide(graph, thread_id: str, status: str, note: str = "") -> dict:
    """Resume one paused run. Raises ValueError for a bad decision, LookupError if nothing is waiting."""
    decision = Decision(status=status, note=note)               # validates: a rejection needs a reason
    config = {"configurable": {"thread_id": thread_id}}
    snap = graph.get_state(config)
    if not any(task.interrupts for task in snap.tasks):
        raise LookupError(f"nothing is waiting for approval in thread {thread_id}")
    return graph.invoke(Command(resume=decision.model_dump()), config)


def is_waiting(graph, thread_id: str) -> bool:
    snap = graph.get_state({"configurable": {"thread_id": thread_id}})
    return any(task.interrupts for task in snap.tasks)


def last_reply(graph, thread_id: str) -> str:
    """The newest assistant message saved in a thread (what the student should now see)."""
    msgs = graph.get_state({"configurable": {"thread_id": thread_id}}).values.get("messages", [])
    return next((m.content for m in reversed(msgs) if m.type == "ai"), "")
