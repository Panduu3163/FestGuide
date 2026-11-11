"""Check full rules answers: right fact, a citation from the right event, and refusal when the rulebook is silent.

    uv run python tests/check_answers.py

This is the seed of the scorecard (milestone M7). Each case lists words the answer must contain
(lowercase), the event the citation must come from, and whether the answer must be grounded.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kb import store  # noqa: E402
from kb.rag import answer_with_rag  # noqa: E402

# (question, words that must appear, event that must be cited or None for "must refuse")
CASES = [
    ("How much is the debate registration fee?", ["1050"], "debate"),
    ("What is the last day to register for the debate?", ["10 june"], "debate"),
    ("How many members are in a debate team?", ["3"], "debate"),
    ("Can I use ChatGPT in the programming contest?", ["not"], "solo_programming"),
    ("How long is the programming contest?", ["3.5"], "solo_programming"),
    ("How many pages can my printed reference document be?", ["25"], "solo_programming"),
    ("What is the maximum video length for the videography contest?", ["2 minutes"], "videography"),
    ("Is AI generated footage allowed in videography?", ["prohibited"], "videography"),
    ("How big can a project showcase team be?", ["3", "5"], "project_showcase"),
    ("How long can the project showcase recorded video be?", ["4 minutes"], "project_showcase"),
    ("What is the 3MT time limit for a presentation?", ["3 minutes|three minutes|3-minute"], "three_mt"),
    ("What is the registration fee for 3MT?", ["100"], "three_mt"),
    ("What is in the Tech Olympiad syllabus?", ["circuits"], "tech_olympiad"),
    ("Are smartwatches allowed in the Tech Olympiad exam?", ["prohibited"], "tech_olympiad"),
    ("How long is the idea generation final presentation?", ["5 minutes|5-minute|five minutes"], "idea_generation"),
    ("What file name format do idea generation submissions use?", ["teamname_ideatitle"], "idea_generation"),
    # the rulebooks are silent: the assistant must say so and cite nothing
    ("What is the prize money for the programming contest winner?", [], None),
    ("What is the registration fee for the solo programming contest?", [], None),
    ("Who won the debate championship last year?", [], None),
]

if __name__ == "__main__":
    bad = 0
    for q, words, event in CASES:
        r = answer_with_rag(q)
        text, problems = r["answer"].lower(), []
        if event is None:
            if r["grounded"] or r["citations"]:
                problems.append("should refuse (rulebook is silent) but answered with citations")
            if "does not say" not in text and "not say" not in text:
                problems.append("refusal wording missing")
        else:
            problems += [f"missing '{w}'" for w in words if not any(alt in text for alt in w.split("|"))]   # "a|b" = either wording
            if not r["grounded"] or not any(c.event == event and c.version == "2026" for c in r["citations"]):
                problems.append(f"no 2026 citation from {event}")
        bad += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {q[:64]:64}")
        for p in problems:
            print(f"       {p}  | answer: {r['answer'][:120]}")
        time.sleep(1)
    store.close()
    print(f"\n{bad} of {len(CASES)} cases failed")
