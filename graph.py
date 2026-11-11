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
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from kb import rag, store
from agent import run_tools
from draft import build_request
from memory import turn_messages
from models import build_model, load_prompt
from schemas import Citation, Intent


class State(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]   # the chat history (C4); saved by the checkpointer
    student_id: str            # who is chatting (set by the chat program, not by the model)
    question: str              # what the student typed
    standalone: str            # the question after rewriting (E2)
    intent: dict               # the classifier's Intent, as a dict
    documents: list            # retrieved chunks (rules route)
    answer: str                # answer text (rules route)
    citations: list            # citations as plain dicts (see schemas.Citation)
    version_note: str
    tool_log: list             # every tool call and result of the tool loop (plan / register routes)
    request: dict              # a drafted registration or exception request
    decision: dict             # the organizer's decision {"status": "approved" | "rejected", "note": ...}
    reply: str                 # the final text shown to the student


# ---- nodes ---------------------------------------------------------------------------------

def intake(state: State) -> dict:
    """Guardrails: PII hiding, prompt-injection and off-topic filter, step limit. (guards: M5)

    It also RESETS the per-turn fields. The checkpointer keeps the whole state between turns, so without
    this a decision or tool log from the last message would still be sitting there for this one."""
    return {"standalone": state["question"], "documents": [], "answer": "", "citations": [], "version_note": "",
            "tool_log": [], "request": None, "decision": None, "reply": "", "intent": {}}


def rewrite(state: State) -> dict:
    """Turn a follow-up ("the second one") into a standalone question using the chat history. (stub: M6)"""
    return {}


def classify(state: State) -> dict:
    """C1: the model returns an Intent object (Pydantic). Its `intent` field picks the route."""
    template, version = load_prompt("classify_prompt")
    prompt = template.format(question=state["standalone"])
    intent: Intent = _classifier().invoke(prompt, config={"run_name": "classify", "tags": [f"prompt:classify_prompt:{version}"]})
    return {"intent": intent.model_dump()}


_cls = None


def _classifier():
    global _cls
    _cls = _cls or build_model(schema=Intent)
    return _cls


def retrieve(state: State) -> dict:
    """C6: search the rulebooks. If the question names exactly one event we could filter (E3 stretch)."""
    return rag.retrieve({"question": state["standalone"]})


def answer(state: State) -> dict:
    """C6: a cited answer, or "the rulebook does not say"."""
    out = rag.generate({"question": state["standalone"], "documents": state["documents"]})
    # Plain dicts, not Citation objects: the checkpointer saves state to disk and should only hold plain data.
    return {"answer": out["answer"], "citations": [c.model_dump() for c in out["citations"]], "version_note": out["version_note"]}


def tool_agent(state: State) -> dict:
    """C3: the tool loop. The model picks tools (eligibility, clash, status, rule search); the code runs them."""
    intent = state["intent"]
    log = run_tools(state["standalone"], state["student_id"], intent["intent"], intent["events"])
    return {"tool_log": log}


def explain_result(state: State) -> dict:
    """Turn the tool results into a plain-words answer. It may use only what the tools returned."""
    template, version = load_prompt("explain_prompt")
    log = json.dumps(state["tool_log"], default=str, indent=1)
    if not state["tool_log"]:
        return {"answer": "I could not find anything to check for that. Which events or which student do you mean?"}
    text = _explainer().invoke(template.format(question=state["standalone"], log=log),
                               config={"run_name": "explain_result", "tags": [f"prompt:explain_prompt:{version}"]}).text
    return {"answer": text}


_exp = None


def _explainer():
    global _exp
    _exp = _exp or build_model()
    return _exp


def draft_request(state: State) -> dict:
    """Build the registration / exception request from the checked facts (draft.py), or say why it cannot be built."""
    intent = state["intent"]
    request, message = build_request(state["student_id"], state["standalone"], intent["events"],
                                     intent["wants_exception"], state["tool_log"])
    if request is None:
        return {"request": None, "answer": message}
    return {"request": request}


def approval_gate(state: State) -> dict:
    """E1: interrupt() here until an organizer approves or rejects. (stub: M5, so it rejects: nothing is written)"""
    return {"decision": {"status": "rejected", "note": "approval is built in milestone M5"}}


def register_team(state: State) -> dict:
    """The ONLY node that writes registrations.db, reached only after approval. (stub: M5)"""
    return {"answer": "(register_team: milestone M5)"}


def out_of_scope(state: State) -> dict:
    if state["intent"].get("asks_about_other_person"):          # C5: a student sees only their own records
        return {"answer": "I can't share another student's personal details or registrations. "
                          "Each student can check their own status in their own chat."}
    return {"answer": "I can only help with the IIUC CSE Fest 2026 events: their rules, your eligibility, "
                      "schedule clashes and registration. For anything else, please contact the organizers."}


def compose_reply(state: State) -> dict:
    """Build the final text, and add this turn to the chat history. The checkpointer saves it (C4)."""
    decision = state.get("decision")
    if state.get("request") is None and state["intent"].get("intent") == "register":      # could not even draft it
        text = state["answer"]
    elif decision and decision["status"] == "rejected":
        text = f"Your request was not approved. Reason: {decision['note']}"
    else:
        lines = [state.get("answer", "")]
        if state.get("version_note"):
            lines.append(f"(Version note: {state['version_note']})")
        lines += [f"  [cite] {Citation(**c).label()}" for c in state.get("citations") or []]
        text = "\n".join(lines)
    return {"reply": text, "messages": turn_messages(state.get("messages", []), state["question"], text)}


# ---- routes: functions that return the NAME of the next node --------------------------------

def after_classify(state: State) -> str:
    if state["intent"]["asks_about_other_person"]:               # never reaches a tool: nothing to leak
        return "out_of_scope"
    return {"rules": "retrieve", "plan": "tool_agent", "register": "tool_agent"}.get(state["intent"]["intent"], "out_of_scope")


def after_tools(state: State) -> str:
    return "draft_request" if state["intent"]["intent"] == "register" else "explain_result"


def after_draft(state: State) -> str:
    return "approval_gate" if state.get("request") else "compose_reply"


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
    g.add_conditional_edges("draft_request", after_draft, ["approval_gate", "compose_reply"])
    g.add_conditional_edges("approval_gate", after_approval, ["register_team", "compose_reply"])
    for last in ("answer", "explain_result", "register_team", "out_of_scope"):
        g.add_edge(last, "compose_reply")
    g.add_edge("compose_reply", END)
    return g.compile(checkpointer=checkpointer)


def run(graph, question: str, student_id: str = "C233001", show=print, thread_id: str | None = None) -> dict:
    """Stream one message through the graph, printing each node as it finishes.

    With a checkpointer, `thread_id` picks the conversation: the same id continues it."""
    state: dict[str, Any] = {"question": question, "student_id": student_id}
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None
    for update in graph.stream(state, config, stream_mode="updates"):
        for node, changes in update.items():
            changes = changes or {}          # a node that changed nothing reports None
            state |= changes
            extra = f"  {json.dumps(changes['intent'])}" if node == "classify" else ""
            show(f"  -> {node}{extra}")
            if node == "draft_request" and changes.get("request"):           # what the organizer will see
                req = changes["request"]
                show(f"       [request] {req['kind']} for {req['event_name']}: team {[req['leader_id']] + req['member_ids']}; "
                     f"problems: {req['problems'] or 'none'}; {req['fee_note']}")
            for call in changes.get("tool_log") or []:                       # show every tool call
                show(f"       [tool] {call['tool']}({json.dumps(call['args'])}) -> {json.dumps(call['result'], default=str)[:150]}")
    return state


SAMPLES = [   # (message, asking student)
    ("Can I use ChatGPT during the programming contest?", "C233001"),
    ("Do the programming contest and Idea Generation clash?", "C233001"),
    ("Do 3MT and Project Showcase clash?", "C233001"),
    ("Can Tania and I join Idea Generation?", "C233001"),
    ("What am I registered for?", "C233002"),
    ("Register me, Rafi and Tania for Idea Generation. I'm the leader.", "C233001"),
    ("What's the weather in Chittagong tomorrow?", "C233001"),
]

if __name__ == "__main__":
    graph = build_graph()
    print(graph.get_graph().draw_mermaid() if "--mermaid" in sys.argv else "")
    cli = [(" ".join(sys.argv[1:]), "C233001")] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else SAMPLES
    for q, student in cli:
        print(f"\nQ ({student}): {q}")
        print(run(graph, q, student)["reply"])
    store.close()
