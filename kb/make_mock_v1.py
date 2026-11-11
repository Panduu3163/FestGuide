"""Make a MOCK earlier version (v1) of every rulebook, to show version handling.

    uv run python kb/make_mock_v1.py

The real 2026 rulebooks have no earlier versions we can use, so this script copies each
cleaned rulebook and changes a few facts (fee, team size, date, time limits). The copies
are labelled MOCK and live in rulebooks/clean_v1_mock/. The retriever tags their chunks
version="v1-mock", prefers the 2026 text, and mentions a difference when it sees one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402

# event -> [(text in the 2026 rulebook, text in the mock v1)]
CHANGES = {
    "solo_programming": [("June 15, 2026 at 9:00 AM", "June 14, 2026 at 10:00 AM"),
                         ("plus 20 minutes", "plus 10 minutes"),
                         ("up to 25 pages", "up to 20 pages")],
    "videography": [("must not exceed 2 minutes", "must not exceed 3 minutes"),
                    ("fee of 50 BDT", "fee of 30 BDT")],
    "debate": [("Each team has 3 members.", "Each team has 2 members."),
               ("1050 BDT per team", "900 BDT per team"),
               ("2 June 2026 to 10 June 2026", "2 June 2026 to 8 June 2026")],
    "tech_olympiad": [("at least 30 minutes", "at least 15 minutes")],
    "idea_generation": [("Team size: 2-3 members.", "Team size: 3-4 members."),
                        ("5 minutes presentation", "7 minutes presentation")],
    "three_mt": [("Registration fee: 100 BDT.", "Registration fee: 150 BDT."),
                 ("12 June 2026 (Friday)", "10 June 2026 (Wednesday)")],
    "project_showcase": [("Teams may consist of 3-5 members.", "Teams may consist of 3-4 members."),
                         ("duration up to 4 minutes", "duration up to 5 minutes")],
}


def main() -> None:
    out = settings.RULEBOOK_DIR / "clean_v1_mock"
    out.mkdir(exist_ok=True)
    for event, edits in CHANGES.items():
        text = (settings.RULEBOOK_DIR / "clean" / f"{event}.md").read_text(encoding="utf-8")
        for old, new in edits:
            assert old in text, f"{event}: '{old}' not found"      # a typo here must fail loudly
            text = text.replace(old, new)
        banner = "<!-- MOCK earlier version (v1), invented for the version-handling demo. Not an official rulebook. -->\n"
        (out / f"{event}.md").write_text(banner + text, encoding="utf-8")
        print(f"{event:17} {len(edits)} changes")


if __name__ == "__main__":
    main()
