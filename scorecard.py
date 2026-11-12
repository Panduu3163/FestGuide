"""The scorecard (C2): 32 questions run through the whole graph and scored by plain code. Results go to LangSmith.

    uv run python scorecard.py            # run all questions, store the experiment in LangSmith
    uv run python scorecard.py --local    # same run, printed here only (no LangSmith)
    uv run python scorecard.py --limit 5  # just the first 5 questions
    uv run python scorecard.py --reset    # delete and recreate the LangSmith dataset first

Course sessions 4 and 13 (evaluating a model app): a fixed set of questions with known good answers, scored
the same way every time, so a change of model or prompt shows up as a number instead of a feeling.
The questions are in data/scorecard.yml. Each run is one "experiment" in LangSmith; its name carries the model
and the prompt versions, so two runs can be compared side by side. Registrations run against a throwaway
copy of registrations.db, and the organizer's approval gate is never answered (the request just pauses).
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

import yaml

from config import ROOT, settings

settings.STATE_DIR = Path(tempfile.mkdtemp())            # throwaway registrations.db; the Qdrant index lives elsewhere
os.environ["LANGSMITH_TRACING"] = "true"                 # the scorecard is always traced (unless --local)

import fest_data  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

from graph import build_graph, run  # noqa: E402
from kb import store  # noqa: E402
from models import load_prompt  # noqa: E402

DATASET = "festguide-scorecard"
_graph = None


def load_cases() -> list[dict]:
    return yaml.safe_load((ROOT / "data" / "scorecard.yml").read_text(encoding="utf-8"))


def graph():
    global _graph
    if _graph is None:
        fest_data.seed_db(reset=True)
        _graph = build_graph(InMemorySaver())
    return _graph


# ---- run one question ---------------------------------------------------------------------------------

def route_from_nodes(nodes: list[str]) -> str:
    """Which route the message took, read from the nodes that ran (not from what the model says it did)."""
    if "classify" not in nodes:
        return "blocked"
    for node, route in (("draft_request", "register"), ("explain_result", "plan"), ("retrieve", "rules")):
        if node in nodes:
            return route
    return "other"


def run_case(inputs: dict) -> dict:
    thread = f"score-{inputs['id']}"
    student = inputs.get("student") or "C233001"
    for earlier in inputs.get("before") or []:
        run(graph(), earlier, student, show=lambda *_: None, thread_id=thread)
    nodes: list[str] = []
    state = run(graph(), inputs["q"], student, show=lambda line: nodes.append(line.split()[1]) if line.startswith("  -> ") else None,
                thread_id=thread)
    return {"reply": state.get("reply", ""), "route": route_from_nodes(nodes),
            "cited": sorted({c["event"] for c in state.get("citations") or [] if c["version"] == "2026"}),
            "paused": bool(state.get("interrupted")),
            "tools": [c["tool"] for c in state.get("tool_log") or []],
            "standalone": state.get("standalone", "")}


# ---- score it ------------------------------------------------------------------------------------------

def has(text: str, word: str) -> bool:
    return any(alt in text for alt in word.split("|"))


def score(expected: dict, out: dict) -> dict[str, int]:
    """1 or 0 for each thing the case asks for. Only the checks a case defines are scored."""
    text, marks = out["reply"].lower(), {"route": int(out["route"] == expected["route"])}
    if expected.get("contains"):
        marks["contains"] = int(all(has(text, w) for w in expected["contains"]))
    if expected.get("forbid"):
        marks["forbid"] = int(not any(w in text for w in expected["forbid"]))
    if expected.get("cites"):
        marks["citation"] = int(not out["cited"]) if expected["cites"] == "none" else int(expected["cites"] in out["cited"])
    if "paused" in expected:
        marks["paused"] = int(out["paused"] == expected["paused"])
    return marks


# ---- LangSmith -----------------------------------------------------------------------------------------

def sync_dataset(client, cases: list[dict], reset: bool) -> None:
    if client.has_dataset(dataset_name=DATASET):
        have = {e.inputs["id"] for e in client.list_examples(dataset_name=DATASET)}
        if not reset and have == {c["id"] for c in cases}:
            return
        client.delete_dataset(dataset_name=DATASET)
    client.create_dataset(DATASET, description="FestGuide scorecard: questions with expected route, facts and citation.")
    client.create_examples(
        dataset_name=DATASET,
        inputs=[{k: c.get(k) for k in ("id", "q", "student", "before")} for c in cases],
        outputs=[{k: v for k, v in c.items() if k not in ("id", "q", "student", "before")} for c in cases])


def evaluator(outputs: dict, reference_outputs: dict) -> dict:
    marks = score(reference_outputs, outputs)
    return {"results": [{"key": k, "score": v} for k, v in marks.items()]
            + [{"key": "passed", "score": int(all(marks.values()))}]}


def experiment_name() -> str:
    versions = "-".join(load_prompt(p)[1] for p in ("classify_prompt", "rag_prompt", "agent_prompt", "explain_prompt", "rewrite_prompt"))
    return f"{settings.MODEL.split(':')[1]}_prompts-{versions}"


def summarize(rows: list[tuple[dict, dict, dict]]) -> None:
    for case, out, marks in rows:
        bad = [k for k, v in marks.items() if not v]
        print(f"{'FAIL' if bad else 'ok  '} {case['id']:20} route={out['route']:8}" + (f"  failed: {bad}  reply: {out['reply'][:110]!r}" if bad else ""))
    passed = sum(all(m.values()) for _, _, m in rows)
    print(f"\n{passed} of {len(rows)} questions passed")
    for key in ("route", "contains", "forbid", "citation", "paused"):
        scored = [m[key] for _, _, m in rows if key in m]
        print(f"  {key:9} {sum(scored)}/{len(scored)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="do not use LangSmith")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    cases = load_cases()[: args.limit]

    if args.local:
        os.environ["LANGSMITH_TRACING"] = "false"
        rows = []
        for case in cases:
            out = run_case(case)
            rows.append((case, out, score(case, out)))
        summarize(rows)
    else:
        from langsmith import Client, evaluate
        client = Client()
        sync_dataset(client, load_cases(), args.reset)
        examples = list(client.list_examples(dataset_name=DATASET))
        examples = [e for e in examples if e.inputs["id"] in {c["id"] for c in cases}]
        result = evaluate(run_case, data=examples, evaluators=[evaluator], max_concurrency=1,
                          experiment_prefix=experiment_name(),
                          metadata={"model": settings.MODEL, "fallback": settings.FALLBACK, "embeddings": settings.EMBED_MODEL})
        rows = []
        for r in result:
            case = next(c for c in cases if c["id"] == r["example"].inputs["id"])
            rows.append((case, r["run"].outputs or {"reply": "", "route": "error", "cited": [], "paused": False}, score(case, r["run"].outputs or {"reply": "", "route": "error", "cited": [], "paused": False})))
        summarize(rows)
        print(f"\nExperiment stored in LangSmith: project '{result.experiment_name}'")
    store.close()


if __name__ == "__main__":
    main()
