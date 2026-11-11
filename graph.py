"""The FestGuide workflow as a LangGraph graph (C7). Milestone M2: the skeleton.

    START -> intake -> rewrite -> classify --rules-----> retrieve -> answer ------------------------> compose_reply
                                          \\--plan/register--> tool_agent --plan--> explain_result --> compose_reply
                                          |                              \\-register--> draft_request -> approval_gate
                                          |                                     --approved--> register_team --> compose_reply
                                          |                                     --rejected--------------------> compose_reply
                                          \\--other---------> out_of_scope ------------------------> compose_reply -> END

Course session 10 (a graph is nodes + edges over a shared state) and session 11 (the approval gate).
Every node takes the state and returns ONLY the keys it changes. Nodes marked (stub) have their
place in the graph now and get real code in the milestone named next to them.

    uv run python graph.py                      # print the diagram and run four sample messages
    uv run python graph.py "your question"      # run one message
"""
import json
import sys
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from kb import rag, store
from models import build_model, load_prompt
from schemas import Intent


class State(TypedDict, total=False):
    student_id: str            # who is chatting (set by the chat program, not by the model)
    question: str              # what the student typed
    standalone: str            # the question after rewriting (E2)
    intent: dict               # the classifier's Intent, as a dict
    documents: list            # retrieved chunks (rules route)
    answer: str                # answer text (rules route)
    citations: list            # Citation objects
    version_note: str
    tool_result: str           # result of the tools (plan / register routes)
    request: dict              # a drafted registration or exception request
    decision: dict             # the organizer's decision {"status": "approved" | "rejected", "note": ...}
    reply: str                 # the final text shown to the student


# ---- nodes ---------------------------------------------------------------------------------

def intake(state: State) -> dict:
    """Guardrails: PII hiding, prompt-injection and off-topic filter, step limit. (stub: M5)"""
    return {"standalone": state["question"]}


def rewrite(state: State) -> dict:
    """Turn a follow-up ("the second one") into a standalone question using the chat history. (stub: M6)"""
    return {}


def classify(state: State) -> dict:
    """C1: the model returns an Intent object (Pydantic). Its `intent` field picks the route."""
    template, version = load_prompt("classify_prompt")
    prompt = template.format(question=state["standalone"], student_id=state.get("student_id") or "unknown")
    intent: Intent = _classifier().invoke(prompt, config={"run_name": "classify", "tags": [f"prompt:classify_prompt:{version}"]})
    return {"intent": intent.model_dump()}


_cls = None


def _classifier():
    global _cls
    _cls = _cls or build_model().with_structured_output(Intent)
    return _cls


def retrieve(state: State) -> dict:
    """C6: search the rulebooks. If the question names exactly one event we could filter (E3 stretch)."""
    return rag.retrieve({"question": state["standalone"]})


def answer(state: State) -> dict:
    """C6: a cited answer, or "the rulebook does not say"."""
    out = rag.generate({"question": state["standalone"], "documents": state["documents"]})
    return {"answer": out["answer"], "citations": out["citations"], "version_note": out["version_note"]}


def tool_agent(state: State) -> dict:
    """C3: calls check_eligibility, check_schedule_clash, get_registration_status. (stub: M3)"""
    return {"tool_result": "(tool agent: milestone M3)"}


def explain_result(state: State) -> dict:
    """Explain a clash or eligibility result in plain words. (stub: M3)"""
    return {"answer": state["tool_result"]}


def draft_request(state: State) -> dict:
    """Build the registration / exception request from the checked facts. (stub: M5)"""
    return {"request": {"student_id": state.get("student_id"), "events": state["intent"]["events"]}}


def approval_gate(state: State) -> dict:
    """E1: interrupt() here until an organizer approves or rejects. (stub: M5, so it rejects: nothing is written)"""
    return {"decision": {"status": "rejected", "note": "approval is built in milestone M5"}}


def register_team(state: State) -> dict:
    """The ONLY node that writes registrations.db, reached only after approval. (stub: M5)"""
    return {"answer": "(register_team: milestone M5)"}


def out_of_scope(state: State) -> dict:
    return {"answer": "I can only help with the IIUC CSE Fest 2026 events: their rules, your eligibility, "
                      "schedule clashes and registration. For anything else, please contact the organizers."}


def compose_reply(state: State) -> dict:
    """Build the final text. Memory (C4) is saved by the checkpointer around the whole run. (M4)"""
    decision = state.get("decision")
    if decision and decision["status"] == "rejected":
        return {"reply": f"Your request was not approved. Reason: {decision['note']}"}
    lines = [state.get("answer", "")]
    if state.get("version_note"):
        lines.append(f"(Version note: {state['version_note']})")
    lines += [f"  [cite] {c.label()}" for c in state.get("citations") or []]
    return {"reply": "\n".join(lines)}


# ---- routes: functions that return the NAME of the next node --------------------------------

def after_classify(state: State) -> str:
    return {"rules": "retrieve", "plan": "tool_agent", "register": "tool_agent"}.get(state["intent"]["intent"], "out_of_scope")


def after_tools(state: State) -> str:
    return "draft_request" if state["intent"]["intent"] == "register" else "explain_result"


def after_approval(state: State) -> str:
    return "register_team" if state["decision"]["status"] == "approved" else "compose_reply"


def build_graph(checkpointer=None):
    g = StateGraph(State)
    for fn in (intake, rewrite, classify, retrieve, answer, tool_agent, explain_result, draft_request,
               approval_gate, register_team, out_of_scope, compose_reply):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "intake")
    g.add_edge("intake", "rewrite")
    g.add_edge("rewrite", "classify")
    g.add_conditional_edges("classify", after_classify, ["retrieve", "tool_agent", "out_of_scope"])
    g.add_edge("retrieve", "answer")
    g.add_conditional_edges("tool_agent", after_tools, ["draft_request", "explain_result"])
    g.add_edge("draft_request", "approval_gate")
    g.add_conditional_edges("approval_gate", after_approval, ["register_team", "compose_reply"])
    for last in ("answer", "explain_result", "register_team", "out_of_scope"):
        g.add_edge(last, "compose_reply")
    g.add_edge("compose_reply", END)
    return g.compile(checkpointer=checkpointer)


def run(graph, question: str, student_id: str = "C233001", show=print) -> dict:
    """Stream one message through the graph, printing each node as it finishes."""
    state: dict[str, Any] = {"question": question, "student_id": student_id}
    for update in graph.stream(state, stream_mode="updates"):
        for node, changes in update.items():
            changes = changes or {}          # a node that changed nothing reports None
            state |= changes
            extra = f"  {json.dumps(changes['intent'])}" if node == "classify" else ""
            show(f"  -> {node}{extra}")
    return state


SAMPLES = [
    "Can I use ChatGPT during the programming contest?",
    "Do the programming contest and Idea Generation clash? I'm C233001.",
    "Register me, Rafi and Tania for Idea Generation. I'm the leader.",
    "What's the weather in Chittagong tomorrow?",
]

if __name__ == "__main__":
    graph = build_graph()
    print(graph.get_graph().draw_mermaid() if "--mermaid" in sys.argv else "")
    for q in ([" ".join(sys.argv[1:])] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else SAMPLES):
        print(f"\nQ: {q}")
        print(run(graph, q)["reply"])
    store.close()
