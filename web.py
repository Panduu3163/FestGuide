"""The web version: a student page and an organizer page, one small server.

    uv run python web.py                 # http://127.0.0.1:8000/  (student)   /organizer  (organizer)
    uv run python web.py --langsmith     # also send every run to LangSmith

It adds no new logic. Every endpoint calls what the terminals already call: graph.run (the student's
message), approvals.pending / decide (the organizer's inbox and decision). The two pages are "connected"
the same way the two terminals were: through the checkpoint file. A request that pauses at the approval
gate is saved there; the organizer page lists it; the decision resumes it; the student page notices.

Optional: set ORGANIZER_PIN in .env and the organizer endpoints need that PIN (sent as the X-Pin header).
All students are mock data. The student picker stands in for a login.
"""
import argparse
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from approvals import decide, is_waiting, last_reply, pending, pending_for_student
from chat import friendly_error
from fest_data import load_students
from graph import build_graph, run
from kb import store
from memory import checkpointer, thread_id_for

STATIC = Path(__file__).parent / "static"
app_state: dict = {}
thread_locks: dict[str, threading.Lock] = {}          # one message at a time per conversation


@asynccontextmanager
async def lifespan(_app):
    saver = checkpointer()
    app_state.update(saver=saver, graph=build_graph(saver))
    yield
    store.close()


app = FastAPI(title="FestGuide", lifespan=lifespan)


def need_pin(x_pin: str | None = Header(default=None)) -> None:
    pin = os.getenv("ORGANIZER_PIN")
    if pin and x_pin != pin:
        raise HTTPException(401, "Wrong or missing organizer PIN.")


def student_or_404(student_id: str) -> dict:
    student = load_students().get(student_id.upper())
    if student is None:
        raise HTTPException(404, f"Unknown student {student_id} (mock data only).")
    return student


class ChatIn(BaseModel):
    student_id: str
    message: str = Field(min_length=1, max_length=1000)


class DecisionIn(BaseModel):
    thread_id: str
    status: str                                         # "approved" or "rejected"
    note: str = ""


# ---------------------------------------------------------------- student side

@app.get("/api/students")
def students() -> list[dict]:
    """Only what the picker needs. Phone numbers never leave the server."""
    return [{"id": s["id"], "name": s["name"], "department": s["department"]} for s in load_students().values()]


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    student = student_or_404(body.student_id)
    sid = student["id"]
    graph = app_state["graph"]
    thread = thread_id_for(sid, "web")
    lock = thread_locks.setdefault(thread, threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Still working on your previous message.")
    try:
        if is_waiting(graph, thread):                   # a new message would discard the paused request
            return {"reply": "Your request is waiting for an organizer's decision. You will see the result here.",
                    "trace": [], "waiting": True}
        trace: list[str] = []
        try:
            state = run(graph, body.message, sid, show=trace.append, thread_id=thread)
        except Exception as err:                        # a rate limit or outage must not break the page
            return {"reply": friendly_error(err), "trace": trace, "waiting": False}
        return {"reply": state["reply"], "trace": trace, "waiting": bool(state.get("interrupted"))}
    finally:
        lock.release()


@app.get("/api/chat/{student_id}")
def conversation(student_id: str) -> dict:
    """The saved conversation, whether a request is waiting, and (polled by the page) any decision that arrived."""
    sid = student_or_404(student_id)["id"]
    graph = app_state["graph"]
    thread = thread_id_for(sid, "web")
    messages = graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", [])
    waiting = is_waiting(graph, thread)
    return {"messages": [{"role": "student" if m.type == "human" else "festguide", "text": m.content} for m in messages],
            "waiting": waiting, "last_reply": "" if waiting else last_reply(graph, thread)}


# ---------------------------------------------------------------- organizer side

@app.get("/api/organizer/pending", dependencies=[Depends(need_pin)])
def waiting_requests() -> list[dict]:
    students_ = load_students()
    out = []
    for p in pending(app_state["graph"], app_state["saver"]):
        req = p["request"]
        name = lambda i: students_[i]["name"] if i in students_ else i  # noqa: E731
        out.append({**p, "leader_name": name(req["leader_id"]),
                    "member_names": [name(m) for m in req["member_ids"]]})
    return out


@app.post("/api/organizer/decide", dependencies=[Depends(need_pin)])
def decision(body: DecisionIn) -> dict:
    try:
        out = decide(app_state["graph"], body.thread_id, body.status, body.note)
    except LookupError as err:
        raise HTTPException(404, str(err))
    except ValueError as err:                           # e.g. a rejection without a reason
        msg = err.errors()[0]["msg"].removeprefix("Value error, ") if hasattr(err, "errors") else str(err)
        raise HTTPException(422, msg)
    return {"reply": out["reply"]}


# ---------------------------------------------------------------- pages

@app.get("/")
def student_page():
    return FileResponse(STATIC / "index.html")


@app.get("/organizer")
def organizer_page():
    return FileResponse(STATIC / "organizer.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--langsmith", action="store_true", help="trace every run in LangSmith")
    args = ap.parse_args()
    if args.langsmith:
        os.environ["LANGSMITH_TRACING"] = "true"
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
