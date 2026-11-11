"""Audit the hand-cleaned rulebooks and the index. Prints problems; prints nothing scary if all is well.

    uv run python kb/audit.py

1. PAGES    every page marker in rulebooks/clean/*.md: does that PDF page really contain the words
            of the text after it?
2. NUMBERS  every number in a cleaned file: does it appear in the PDF's own text? (A number I
            mistyped while cleaning would be a wrong fact in an answer.)
3. SEARCH   retrieval-only smoke test: for each question, does the expected rulebook section come
            back in the top results?
"""
import re
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402
from fest_data import load_events  # noqa: E402
from kb import store  # noqa: E402
from kb.ingest import PAGE  # noqa: E402
from kb.rag import search  # noqa: E402

# 3MT is a scanned design: its PDF text is OCR noise, so word and number checks mean little there.
NOISY = {"three_mt"}

# (question, expected event, expected section fragment)
SEARCH_CASES = [
    ("How much is the debate registration fee?", "debate", "Registration"),
    ("What is the deadline to register for debate?", "debate", "Registration"),
    ("How many members in a debate team?", "debate", "Team Formation"),
    ("Can I use ChatGPT in the programming contest?", "solo_programming", "Conduct"),
    ("How long is the programming contest?", "solo_programming", "Contest Structure"),
    ("How many pages can my printed reference be?", "solo_programming", "Reference"),
    ("What is the maximum video length for videography?", "videography", "Video Requirements"),
    ("Is AI generated footage allowed in videography?", "videography", "Video Requirements"),
    ("How big can a project showcase team be?", "project_showcase", "Eligibility"),
    ("How long can the project showcase video be?", "project_showcase", "Submission"),
    ("What is the 3MT time limit?", "three_mt", "Competition Information"),
    ("What is the fee for 3MT?", "three_mt", "Competition Information"),
    ("What topics are in the Tech Olympiad syllabus?", "tech_olympiad", "Syllabus"),
    ("Are smartwatches allowed in the Tech Olympiad exam?", "tech_olympiad", "Rules"),
    ("How long is the idea generation presentation?", "idea_generation", "Presentation"),
    ("What is the file name format for idea generation submissions?", "idea_generation", "Submission Format"),
]


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", text.lower())}


def check_files() -> int:
    problems = 0
    for event, info in load_events().items():
        pdf = PdfReader(settings.RULEBOOK_DIR / info["rulebook"])
        raw = [(p.extract_text() or "") for p in pdf.pages]
        clean = (settings.RULEBOOK_DIR / "clean" / f"{event}.md").read_text(encoding="utf-8")
        if event not in NOISY:
            # 1. pages: split the cleaned file at page markers and compare with that PDF page
            parts = PAGE.split(clean)               # [before, "3", text, "4", text, ...]
            for n, text in zip(parts[1::2], parts[2::2]):
                n, w = int(n), words(text)
                page_words = words(raw[n - 1]) if n <= len(raw) else set()
                if len(w) >= 4 and len(w & page_words) / len(w) < 0.5:   # tiny pages (just a date) say too little to check
                    print(f"  PAGE?   {event} p.{n}: only {len(w & page_words)}/{len(w)} words found on that PDF page")
                    problems += 1
            # 2. numbers: join the PDF text so "1050" is found even if the layout split it
            raw_all = re.sub(r"\s+", " ", " ".join(raw))
            for num in sorted(set(re.findall(r"\d[\d,.]*\d|\d", PAGE.sub("", clean)))):
                if num not in raw_all and num.replace(",", "") not in raw_all:
                    print(f"  NUMBER? {event}: '{num}' is in the cleaned file but not in the PDF text")
                    problems += 1
    return problems


def check_search() -> int:
    problems = 0
    for q, event, frag in SEARCH_CASES:
        docs = search(q)
        ok = any(d.metadata["event"] == event and frag.lower() in d.metadata["section"].lower() for d in docs[:6])
        if not ok:
            got = [f"{d.metadata['event']}:{d.metadata['section'][:22]}" for d in docs[:4]]
            print(f"  SEARCH? '{q}' expected {event}/{frag}, got {got}")
            problems += 1
    return problems


if __name__ == "__main__":
    print("1-2. cleaned files vs PDFs")
    n1 = check_files()
    print("3. retrieval smoke test")
    n2 = check_search()
    store.close()
    print(f"\n{n1} file problems, {n2} search problems")
