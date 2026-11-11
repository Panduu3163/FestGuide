"""Check conversation memory with no model calls (free and exact).

    uv run python tests/check_memory.py

Builds a tiny graph from the REAL State, intake and compose_reply nodes, saved by a real SqliteSaver
on a temporary file, then checks: a thread remembers, threads are separate, memory survives a
"restart" (a brand-new checkpointer on the same file), history is trimmed, and per-turn fields reset.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph  # noqa: E402

import graph as g  # noqa: E402
import memory  # noqa: E402

DB = Path(tempfile.mkdtemp()) / "checkpoints.sqlite"
failures = []


def check(name, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)
        print(f"       {detail}")


def mini(saver):
    """intake -> (pretend answer) -> compose_reply: the real nodes around a fake model."""
    def pretend(state):
        return {"intent": {"intent": "rules"}, "answer": f"echo: {state['question']}"}
    b = StateGraph(g.State)
    b.add_node("intake", g.intake); b.add_node("pretend", pretend); b.add_node("compose_reply", g.compose_reply)
    b.add_edge(START, "intake"); b.add_edge("intake", "pretend"); b.add_edge("pretend", "compose_reply")
    b.add_edge("compose_reply", END)
    return b.compile(checkpointer=saver)


def say(graph, thread, text, **extra):
    return graph.invoke({"question": text, "student_id": "C233001", **extra}, {"configurable": {"thread_id": thread}})


def stored(graph, thread):
    return graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", [])


graph = mini(memory.checkpointer(DB))
say(graph, "student-A", "hello")
say(graph, "student-A", "second question")
check("a thread remembers its turns (2 turns = 4 messages)", len(stored(graph, "student-A")) == 4, len(stored(graph, "student-A")))
check("messages are in order, human then AI", [m.type for m in stored(graph, "student-A")] == ["human", "ai", "human", "ai"])

say(graph, "student-B", "other student's chat")
check("a different thread starts empty (chats are separate)", len(stored(graph, "student-B")) == 2 and "hello" not in str(stored(graph, "student-B")))

restarted = mini(memory.checkpointer(DB))                         # a "restart": new objects, same file
check("memory survives a restart", len(stored(restarted, "student-A")) == 4)
say(restarted, "student-A", "after the restart")
check("the chat continues after the restart", len(stored(restarted, "student-A")) == 6)

for i in range(15):
    say(restarted, "student-C", f"message {i}")
msgs = stored(restarted, "student-C")
check(f"history is trimmed to {memory.MAX_STORED} messages", len(msgs) == memory.MAX_STORED, len(msgs))
check("the NEWEST messages are the ones kept", msgs[-2].content == "message 14" and "message 0" not in str([m.content for m in msgs]))
check("recent() returns only the last few", len(memory.recent(msgs)) == memory.RECENT)

# per-turn fields must not leak into the next turn
say(restarted, "student-D", "first", decision={"status": "rejected", "note": "leftover"})
out = say(restarted, "student-D", "second")
check("a decision from an earlier turn does not leak into the next one", out["decision"] is None and "not approved" not in out["reply"], out["reply"])

print(f"\n{len(failures)} failed")
