"""The fallback model (C2): when Gemini fails, the same request is answered by OpenRouter.

    uv run python tests/check_fallback.py

Gemini is broken on purpose: its key is replaced with a wrong one BEFORE anything loads (the real key in .env
is untouched; this only changes this process). Then the graph's three kinds of model call are run:
a structured classification, a grounded rules answer, and the tool loop. A small callback records which
model really answered each call. The test checks the MECHANISM (the call succeeds and OpenRouter answered), not
the quality: the small fallback model is weaker, and scorecard.py measures how much weaker. Uses about 12 model calls.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["GEMINI_API_KEY"] = "this-key-is-wrong-on-purpose"       # load_dotenv does not override variables that are already set
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402

settings.STATE_DIR = Path(tempfile.mkdtemp())
import fest_data  # noqa: E402
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from graph import build_graph, run  # noqa: E402
from kb import store  # noqa: E402
from models import build_model  # noqa: E402
from schemas import Intent  # noqa: E402


class WhoAnswered(BaseCallbackHandler):
    """Records the model name of every chat call that finished (a failed Gemini call does not finish)."""
    def __init__(self):
        self.finished, self.started = [], {}

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kw):
        self.started[run_id] = (metadata or {}).get("ls_model_name", "?")

    def on_llm_end(self, response, *, run_id, **kw):
        self.finished.append(self.started.get(run_id, "?"))


failures = []


def check(name, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)
        print(f"       {detail}")


fest_data.seed_db(reset=True)

# 1. With no fallback, the wrong key really does break the call (so the test below proves something).
saved, settings.FALLBACK = settings.FALLBACK, ""
try:
    build_model(schema=Intent).invoke("Can I use ChatGPT in the programming contest?")
    broke = False
except Exception:
    broke = True
settings.FALLBACK = saved
check("without the fallback, the broken Gemini key makes the call fail", broke)

# 2. With the fallback, the same call is answered, and OpenRouter did it.
who = WhoAnswered()
intent = build_model(schema=Intent).invoke("Can I use ChatGPT in the programming contest?", config={"callbacks": [who]})
check("structured output (classifier) still returns a valid Intent", isinstance(intent, Intent), intent)
check("the answering model was the OpenRouter one", who.finished and all("gpt-oss" in m for m in who.finished), who.finished)

# 3. The whole graph: a cited answer, and the tool loop with real tool calls.
graph, who = build_graph(InMemorySaver()), WhoAnswered()


def ask(q, n):
    return run(graph, q, "C233001", show=lambda *_: None, thread_id=f"fb-{n}")


from contextvars import ContextVar  # noqa: E402
from langchain_core.tracers.context import register_configure_hook  # noqa: E402
handler_var = ContextVar("fallback_test_handler", default=None)
register_configure_hook(handler_var, True)       # every model call made inside the graph reports to `who`
handler_var.set(who)

s = ask("How much is the debate registration fee?", 1)
check("a rules question gets a reply through the whole graph", bool(s["reply"]) and "went wrong" not in s["reply"], s["reply"])
s = ask("Do the programming contest and Idea Generation clash?", 2)
check("a plan question gets a reply through the tool loop", bool(s["reply"]) and "went wrong" not in s["reply"], s["reply"])
check("every model call in the graph was answered by OpenRouter", who.finished and all("gpt-oss" in m for m in who.finished), set(who.finished))

store.close()
print(f"\n{len(failures)} failed")
