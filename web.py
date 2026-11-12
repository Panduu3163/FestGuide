"""The web version: a student page and an organizer page, one small server.

    uv run python web.py                 # http://127.0.0.1:8000/  (student)   /organizer  (organizer)
    uv run python web.py --langsmith     # also send every run to LangSmith

It adds no new logic. Every endpoint calls what the terminals already call: graph.run (the student's
message), approvals.pending / decide (the organizer's inbox and decision). The two pages are "connected"
the same way the two terminals were: through the checkpoint file. A request that pauses at the approval
gate is saved there; the organizer page lists it; the decision resumes it; the student page notices.

Optional: set ORGANIZER_PIN in .env and the organizer endpoints need that PIN (sent as the X-Pin header).
All students are mock data. The student picker stands in for a login.

DEMO_MODE=1 is for a public site (docs/deploy.md). Many strangers share one server, so:
  - each visitor gets a cookie, their own conversation thread, and an organizer inbox that shows only
    their own requests (no PIN needed, and nobody can approve someone else's request);
  - messages are rate limited per IP and per day, to protect the model quota;
  - the registrations table goes back to its three seed teams every DEMO_RESET_MINUTES (default 30)
    and when a visitor presses "Reset demo";
  - /demo shows the student page and the organizer page side by side.
"""
import argparse
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import fest_data
from approvals import decide, is_waiting, last_reply, pending, thread_ids
from chat import friendly_error
from fest_data import SEED_TEAMS, load_students
from graph import build_graph, run
from kb import store
from memory import checkpointer, thread_id_for

STATIC = Path(__file__).parent / "static"
app_state: dict = {}
thread_locks: dict[str, threading.Lock] = {}          # one message at a time per conversation
SESSION_COOKIE = "fg_session"
HOURLY_PER_IP, DAILY_TOTAL = 30, 300                  # demo mode: messages per IP per hour, and per day for everyone
hits: dict[str, deque] = defaultdict(deque)           # ip -> times of recent messages
day_count = {"day": "", "n": 0}


def demo() -> bool:
    return os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")


def restore_registrations() -> None:
    """Back to the three seed teams: what visitors registered is mock data and is not kept."""
    refs = [t[0] for t in SEED_TEAMS]
    marks = ",".join("?" * len(refs))
    with fest_data.db() as conn:
        conn.execute(f"DELETE FROM team_members WHERE ref NOT IN ({marks})", refs)
        conn.execute(f"DELETE FROM teams WHERE ref NOT IN ({marks})", refs)


def reset_loop(minutes: float) -> None:
    while True:
        time.sleep(minutes * 60)
        try:
            restore_registrations()
        except Exception:
            pass                                       # a busy file: try again next round


@asynccontextmanager
async def lifespan(_app):
    saver = checkpointer()
    app_state.update(saver=saver, graph=build_graph(saver))
    if demo():
        fest_data.seed_db()                            # a fresh container has no registrations.db yet
        threading.Thread(target=reset_loop, args=(float(os.getenv("DEMO_RESET_MINUTES", "30")),), daemon=True).start()
    yield
    store.close()


app = FastAPI(title="FestGuide", lifespan=lifespan)


def need_pin(x_pin: str | None = Header(default=None)) -> None:
    pin = os.getenv("ORGANIZER_PIN")
    if pin and not demo() and x_pin != pin:            # in demo mode the inbox is already limited to the visitor's own requests
        raise HTTPException(401, "Wrong or missing organizer PIN.")


def student_or_404(student_id: str) -> dict:
    student = load_students().get(student_id.upper())
    if student is None:
        raise HTTPException(404, f"Unknown student {student_id} (mock data only).")
    return student


def session(request: Request, response: Response) -> str:
    """Demo mode: a random id in a cookie tells visitors apart. Outside demo mode there is one shared session ""."""
    if not demo():
        return ""
    sid = request.cookies.get(SESSION_COOKIE, "")
    if not re.fullmatch(r"[0-9a-f]{8}", sid):          # never trust the cookie as a thread name
        sid = uuid.uuid4().hex[:8]
    response.set_cookie(SESSION_COOKIE, sid, max_age=86400, httponly=True, samesite="lax")
    return sid


def thread_of(student_id: str, sid: str) -> str:
    return thread_id_for(student_id, "web" + (f"-{sid}" if sid else ""))


def mine(thread_id: str, sid: str) -> bool:
    return not sid or thread_id.endswith(f"-web-{sid}")


def limit(request: Request) -> None:
    """Demo mode: stop one visitor, or a crowd, from spending the whole model quota."""
    if not demo():
        return
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[-1].strip()   # the last entry is the one our own proxy added; earlier ones the visitor could fake
    now, today = time.time(), time.strftime("%Y-%m-%d")
    if day_count["day"] != today:
        day_count.update(day=today, n=0)
    recent = hits[ip]
    while recent and now - recent[0] > 3600:
        recent.popleft()
    if len(recent) >= HOURLY_PER_IP:
        raise HTTPException(429, f"Demo limit: {HOURLY_PER_IP} messages per hour per visitor. Please try again later.")
    if day_count["n"] >= DAILY_TOTAL:
        raise HTTPException(429, "The demo has reached its daily limit (free model quota). Please come back tomorrow.")
    recent.append(now)
    day_count["n"] += 1


class ChatIn(BaseModel):
    student_id: str
    message: str = Field(min_length=1, max_length=1000)


class DecisionIn(BaseModel):
    thread_id: str
    status: str                                         # "approved" or "rejected"
    note: str = ""


# ---------------------------------------------------------------- student side

@app.get("/api/config")
def config() -> dict:
    return {"demo": demo()}


@app.get("/api/students")
def students() -> list[dict]:
    """Only what the picker needs. Phone numbers never leave the server."""
    return [{"id": s["id"], "name": s["name"], "department": s["department"]} for s in load_students().values()]


@app.post("/api/chat")
def chat(body: ChatIn, request: Request, ses: str = Depends(session)) -> dict:
    student = student_or_404(body.student_id)
    sid = student["id"]
    graph = app_state["graph"]
    thread = thread_of(sid, ses)
    lock = thread_locks.setdefault(thread, threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Still working on your previous message.")
    try:
        if is_waiting(graph, thread):                   # a new message would discard the paused request
            return {"reply": "Your request is waiting for an organizer's decision. You will see the result here.",
                    "trace": [], "waiting": True}
        limit(request)                                  # only a message that would really run counts
        trace: list[str] = []
        try:
            state = run(graph, body.message, sid, show=trace.append, thread_id=thread)
        except Exception as err:                        # a rate limit or outage must not break the page
            return {"reply": friendly_error(err), "trace": trace, "waiting": False}
        return {"reply": state["reply"], "trace": trace, "waiting": bool(state.get("interrupted"))}
    finally:
        lock.release()


@app.get("/api/chat/{student_id}")
def conversation(student_id: str, ses: str = Depends(session)) -> dict:
    """The saved conversation, whether a request is waiting, and (polled by the page) any decision that arrived."""
    sid = student_or_404(student_id)["id"]
    graph = app_state["graph"]
    thread = thread_of(sid, ses)
    messages = graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", [])
    waiting = is_waiting(graph, thread)
    return {"messages": [{"role": "student" if m.type == "human" else "festguide", "text": m.content} for m in messages],
            "waiting": waiting, "last_reply": "" if waiting else last_reply(graph, thread)}


# ---------------------------------------------------------------- organizer side

@app.get("/api/organizer/pending", dependencies=[Depends(need_pin)])
def waiting_requests(ses: str = Depends(session)) -> list[dict]:
    students_ = load_students()
    out = []
    for p in pending(app_state["graph"], app_state["saver"]):
        if not mine(p["thread_id"], ses):
            continue
        req = p["request"]
        name = lambda i: students_[i]["name"] if i in students_ else i  # noqa: E731
        out.append({**p, "leader_name": name(req["leader_id"]),
                    "member_names": [name(m) for m in req["member_ids"]]})
    return out


@app.post("/api/organizer/decide", dependencies=[Depends(need_pin)])
def decision(body: DecisionIn, ses: str = Depends(session)) -> dict:
    if not mine(body.thread_id, ses):
        raise HTTPException(404, "nothing is waiting for you in that thread")
    try:
        out = decide(app_state["graph"], body.thread_id, body.status, body.note)
    except LookupError as err:
        raise HTTPException(404, str(err))
    except ValueError as err:                           # e.g. a rejection without a reason
        msg = err.errors()[0]["msg"].removeprefix("Value error, ") if hasattr(err, "errors") else str(err)
        raise HTTPException(422, msg)
    return {"reply": out["reply"]}


@app.post("/api/demo/reset")
def reset_demo(ses: str = Depends(session)) -> dict:
    """Demo mode: forget this visitor's chats and put the registrations back to the seed teams."""
    if not demo():
        raise HTTPException(404, "Not in demo mode.")
    saver = app_state["saver"]
    for tid in [t for t in thread_ids(saver) if mine(t, ses)]:
        saver.delete_thread(tid)
    restore_registrations()
    return {"ok": True}


# ---------------------------------------------------------------- pages

@app.get("/")
def student_page():
    return FileResponse(STATIC / "index.html")


@app.get("/organizer")
def organizer_page():
    return FileResponse(STATIC / "organizer.html")


@app.get("/demo")
def demo_page():
    return FileResponse(STATIC / "demo.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    ap.add_argument("--langsmith", action="store_true", help="trace every run in LangSmith")
    args = ap.parse_args()
    if args.langsmith:
        os.environ["LANGSMITH_TRACING"] = "true"
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", proxy_headers=True, forwarded_allow_ips="*")
