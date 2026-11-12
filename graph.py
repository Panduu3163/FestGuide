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
import re
import sys
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from pydantic import ValidationError

from kb import rag, store
from agent import run_tools
from draft import build_request
from config import settings
from guards import check_message
from memory import history_text, turn_messages
from models import build_model, load_prompt
from schemas import Citation, Decision, Intent, Rewrite
from tools import NotApproved
from tools import register_team as save_registration


class State(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]   # the chat history (C4); saved by the checkpointer
    student_id: str            # who is chatting (set by the chat program, not by the model)
    question: str              # what the student typed
    masked: str                # what the student typed, private numbers hidden (this is what the history stores)
    standalone: str            # the question after rewriting (E2); what every later node works from
    intent: dict               # the classifier's Intent, as a dict
    documents: list            # retrieved chunks (rules route)
    answer: str                # answer text (rules route)
    citations: list            # citations as plain dicts (see schemas.Citation)
    version_note: str
    tool_log: list             # every tool call and result of the tool loop (plan / register routes)
    request: dict              # a drafted registration or exception request
    decision: dict             # the organizer's decision {"status": "approved" | "rejected", "note": ...}
    reply: str                 # the final text shown to the student
    blocked: dict              # set by intake when a guardrail refuses the message: {"kind", "message"}
    notes: list                # things the student should be told ("I hid a private number")
    turns: int                 # messages so far in this chat (the cost fuse)


# ---- nodes ---------------------------------------------------------------------------------

def intake(state: State) -> dict:
    """C5 guardrails (guards.py, plain code): hide private numbers, block injection, abuse, requests for
    another student's details, over-long messages and chats past the limit.

    It also RESETS the per-turn fields. The checkpointer keeps the whole state between turns, so without
    this a decision or tool log from the last message would still be sitting there for this one."""
    turns = state.get("turns", 0)
    result = check_message(state["question"], state["student_id"], turns)
    reset = {"documents": [], "answer": "", "citations": [], "version_note": "", "tool_log": [], "request": None,
             "decision": None, "reply": "", "intent": {}, "turns": turns + 1}
    if result.blocked:
        return reset | {"masked": "", "standalone": "", "blocked": result.blocked, "notes": []}
    return reset | {"masked": result.text, "standalone": result.text, "blocked": None, "notes": result.notes}


FOLLOW_UP_CUES = re.compile(r"\b(it|its|that|this|those|these|they|them|their|he|him|she|her|one|ones|same|other|also|"
                            r"both|first|second|third|last|former|latter|again|there|then)\b|^(and|what about|how about|so|but)\b", re.I)


def needs_rewrite(question: str, history: list) -> bool:
    """A cheap check before spending a model call: no history means nothing to resolve, and a long message
    with no reference word ("it", "the second one", "what about...") already stands on its own."""
    if not history:
        return False
    return len(question.split()) <= 6 or bool(FOLLOW_UP_CUES.search(question))


def rewrite(state: State) -> dict:
    """E2: turn a follow-up ("how big can a team be for the second one?") into a standalone question using the
    last few turns. The classifier, retriever and tools then work from `standalone`; the history keeps what
    the student really typed. If rewriting fails or its output is not safe, the original message is used."""
    original, history = state["masked"], state.get("messages", [])
    if not needs_rewrite(original, history):
        return {}
    template, version = load_prompt("rewrite_prompt")
    try:
        out: Rewrite = _rewriter().invoke(template.format(history=history_text(history), question=original),
                                          config={"run_name": "rewrite", "tags": [f"prompt:rewrite_prompt:{version}"]})
    except Exception:
        return {}
    text = out.standalone.strip()
    # the rewrite is model output: it goes through the same guards as the student's own text
    if not out.was_follow_up or not text or check_message(text, state["student_id"], 0).blocked:
        return {}
    return {"standalone": text}


_rw = None


def _rewriter():
    global _rw
    _rw = _rw or build_model(schema=Rewrite)
    return _rw


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
    events = state["intent"].get("events") or []
    only = events[0] if settings.EVENT_FILTER and len(events) == 1 else None   # exactly one event named: search only its rulebook
    return rag.retrieve({"question": state["standalone"], "event": only})


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
    request, message = build_request(state["student_id"], state["masked"], intent["events"],
                                     intent["wants_exception"], state["tool_log"])
    if request is None:
        return {"request": None, "answer": message}
    return {"request": request}


def approval_gate(state: State) -> dict:
    """E1: pause the whole run until an organizer decides. interrupt() saves the state to the checkpoint file
    and stops; Command(resume=...) from the organizer terminal (approvals.py) continues from this line.

    RULE: on resume this node runs again from its first line, so nothing before interrupt() may have a side
    effect. Writing to registrations.db happens in the NEXT node, after the decision is saved."""
    payload = {"kind": "approval", "student_id": state["student_id"], "request": state["request"]}
    while True:
        answer = interrupt(payload)
        try:
            return {"decision": Decision.model_validate(answer).model_dump()}
        except ValidationError:      # an invalid answer (e.g. a rejection with no reason): ask again
            payload = payload | {"error": "a decision needs status approved or rejected, and a rejection needs a reason"}


def register_team(state: State) -> dict:
    """The ONLY node that writes registrations.db, reached only through an approved decision.
    tools.register_team checks the approval again and is safe to run twice."""
    req, decision = state["request"], state["decision"]
    try:
        result = save_registration(req["event"], req["leader_id"], req["member_ids"], req["exception_reason"], decision)
    except (ValueError, NotApproved) as err:
        return {"answer": f"An organizer approved your request, but I could not save the registration ({err}). "
                          "Please contact the organizers."}
    note = f" Organizer's note: {decision['note']}" if decision["note"] else ""
    again = " (it was already registered)" if result["already_registered"] else ""
    return {"answer": f"Approved! Your team for {req['event_name']} is registered{again}. "
                      f"Reference: {result['ref']} (mock data, not an official registration).{note}"}


def out_of_scope(state: State) -> dict:
    if state["intent"].get("asks_about_other_person"):          # C5: a student sees only their own records
        return {"answer": "I can't share another student's personal details or registrations. "
                          "Each student can check their own status in their own chat."}
    return {"answer": "I can only help with the IIUC CSE Fest 2026 events: their rules, your eligibility, "
                      "schedule clashes and registration. For anything else, please contact the organizers."}


def compose_reply(state: State) -> dict:
    """Build the final text, and add this turn to the chat history. The checkpointer saves it (C4)."""
    decision, blocked = state.get("decision"), state.get("blocked")
    stored_question = state["masked"]                          # what the student typed, private numbers hidden
    if blocked:
        text = blocked["message"]
        stored_question = f"[message blocked: {blocked['kind']}]"     # an attack must not sit in the history
    elif state.get("request") is None and state["intent"].get("intent") == "register":      # could not even draft it
        text = state["answer"]
    elif decision and decision["status"] == "rejected":
        text = f"Your {state['request']['kind']} request was not approved by the organizer. Reason: {decision['note']}"
    else:
        lines = [state.get("answer", "")]
        if state.get("version_note"):
            lines.append(f"(Version note: {state['version_note']})")
        lines += [f"  [cite] {Citation(**c).label()}" for c in state.get("citations") or []]
        text = "\n".join(lines)
    text = "\n".join([*(f"({n})" for n in state.get("notes") or []), text])
    return {"reply": text, "messages": turn_messages(state.get("messages", []), stored_question, text)}


# ---- routes: functions that return the NAME of the next node --------------------------------

def after_intake(state: State) -> str:
    return "compose_reply" if state.get("blocked") else "rewrite"


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
    g.add_conditional_edges("intake", after_intake, ["rewrite", "compose_reply"])
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
            if node == "__interrupt__":                   # the graph paused at the approval gate
                req = state["request"]
                state["interrupted"] = True
                state["reply"] = (f"I checked your request and sent it to a fest organizer for approval "
                                  f"({req['kind']}: {req['event_name']}, team of {1 + len(req['member_ids'])}). "
                                  "Nothing is saved until they decide. You will see the result here.")
                show("  -> approval_gate  (paused: waiting for an organizer)")
                continue
            changes = changes or {}          # a node that changed nothing reports None
            state |= changes
            extra = f"  {json.dumps(changes['intent'])}" if node == "classify" else ""
            if node == "rewrite":
                extra = f'  "{state["masked"]}"  =>  "{changes["standalone"]}"' if changes.get("standalone") else "  (unchanged)"
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
    graph = build_graph(InMemorySaver())             # interrupt() needs a checkpointer; samples need no file
    print(graph.get_graph().draw_mermaid() if "--mermaid" in sys.argv else "")
    cli = [(" ".join(sys.argv[1:]), "C233001")] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else SAMPLES
    for q, student in cli:
        print(f"\nQ ({student}): {q}")
        print(run(graph, q, student, thread_id=f"sample-{student}-{abs(hash(q))}")["reply"])
    store.close()
