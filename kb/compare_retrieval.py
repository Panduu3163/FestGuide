"""E3: does the event filter and hybrid search actually help? Measure, do not guess.

    uv run python kb/compare_retrieval.py

Each question has a known right place (event + section). Four setups are tried:

    dense            meaning-based search only (the default since M1)
    dense + filter   same, but only inside the rulebook of the event the message names
    hybrid           dense + BM25 keyword search, fused
    hybrid + filter  both

"hit@1" = the right section is the first result, "hit@3" = in the first three, "hit@5" = in the five
sections the model would see. No model calls: only the index is searched.
The first group names the event in the question. The second group is harder: shared vocabulary
("team size", "registration fee") that every rulebook uses, where the event is known only from the chat.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kb import store  # noqa: E402
from kb.audit import SEARCH_CASES  # noqa: E402
from kb.rag import search  # noqa: E402

# (question, event, section fragment): the event is NOT in the question text. In the real app it comes from the
# rewrite step / classifier ("what about the fee for it?" -> debate).
HARD = [
    ("What is the maximum team size?", "debate", "Team Formation"),
    ("What is the registration fee?", "debate", "Registration"),
    ("When is the registration deadline?", "debate", "Registration"),
    ("How long can the video be?", "videography", "Video Requirements"),
    ("What is the time limit for the presentation?", "three_mt", "Competition Information"),
    ("Are phones or smartwatches allowed?", "tech_olympiad", "Rules"),
    ("How do I name my submission file?", "idea_generation", "Submission Format"),
    ("Who is allowed to join?", "project_showcase", "Eligibility"),
    ("Is AI allowed?", "solo_programming", "Conduct"),
    ("How long does it run?", "solo_programming", "Contest Structure"),
]
SETUPS = [("dense", False), ("dense", True), ("hybrid", False), ("hybrid", True)]


def rank(docs, event, frag):
    sections = []
    for d in docs:                                         # one entry per section (twin versions are already grouped)
        key = (d.metadata["event"], d.metadata["section"])
        if key not in sections:
            sections.append(key)
    for i, (e, s) in enumerate(sections, 1):
        if e == event and frag.lower() in s.lower():
            return i
    return None


def evaluate(cases, label):
    print(f"\n{label} ({len(cases)} questions)")
    print(f"  {'setup':16} hit@1  hit@3  hit@5")
    for mode, filtered in SETUPS:
        ranks = [rank(search(q, event=ev if filtered else None, mode=mode), ev, frag) for q, ev, frag in cases]
        at = lambda n: sum(1 for r in ranks if r is not None and r <= n)  # noqa: E731
        print(f"  {mode + (' + filter' if filtered else ''):16} {at(1):>3}    {at(3):>3}    {at(5):>3}")


if __name__ == "__main__":
    evaluate(SEARCH_CASES, "Event named in the question")
    evaluate(HARD, "Event known only from the chat")
    store.close()
