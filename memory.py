"""Conversation memory (C4): a checkpointer keeps each chat as a thread; old turns are trimmed.

Course session 6 (checkpointers and threads) and session 11 (SqliteSaver).

    checkpointer()          a SqliteSaver on .state/checkpoints.sqlite. LangGraph saves the whole graph
                            state after every step, under a thread id. Same thread id = same conversation,
                            even after the program restarts. A different thread id starts empty.
    thread_id_for(student)  one thread per student by default: "student-C233001".
    recent(messages)        the last few messages, for prompts (the model never needs the whole history).
    turn_messages(...)      the two messages to store for a finished turn, plus removals so the stored
                            history never grows past MAX_STORED (trimming at the source).

The same checkpoint file is what makes the organizer's approval survive a restart (E1, milestone M5).
"""
import sqlite3

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from config import settings

MAX_STORED = 20      # messages kept in a thread (10 turns)
RECENT = 6           # messages shown to a prompt (3 turns)


def checkpointer(path=None) -> SqliteSaver:
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Two programs (the student chat and the organizer terminal) share this file at the same time.
    # WAL lets one write while the other reads; the timeout makes a busy writer wait instead of failing.
    conn = sqlite3.connect(path or settings.STATE_DIR / "checkpoints.sqlite", check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return SqliteSaver(conn)


def thread_id_for(student_id: str, name: str | None = None) -> str:
    return f"student-{student_id}" + (f"-{name}" if name else "")


def recent(messages: list[AnyMessage], n: int = RECENT) -> list[AnyMessage]:
    return messages[-n:]


def history_text(messages: list[AnyMessage], n: int = RECENT) -> str:
    """The recent turns as plain text for a prompt: 'Student: ...' / 'FestGuide: ...'."""
    return "\n".join(f"{'Student' if m.type == 'human' else 'FestGuide'}: {m.content}" for m in recent(messages, n))


def turn_messages(old: list[AnyMessage], question: str, reply: str) -> list[AnyMessage]:
    """Messages to add for this turn, preceded by removals if the thread would get too long."""
    overflow = len(old) + 2 - MAX_STORED
    removals = [RemoveMessage(id=m.id) for m in old[:max(0, overflow)]]
    return [*removals, HumanMessage(question), AIMessage(reply)]
