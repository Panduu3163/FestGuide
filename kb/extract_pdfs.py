"""Step 1 of cleaning: turn each rulebook PDF into a rough text draft, one marker per page.

    uv run python kb/extract_pdfs.py

The drafts land in rulebooks/draft/. Designed PDFs come out messy (one word per line,
repeated headings, OCR noise), so a person finishes the job: the cleaned, sectioned
files live in rulebooks/clean/ and those are what gets indexed. The page markers
(<!-- p.N -->) are kept so a citation can still name the original PDF page.
"""
import re
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402

# PDF file name -> short event key (same keys as events.yml)
PDFS = {
    "INTRA-IIUC SOLO PROGRAMMING CONTEST  CSE FEST 2026 Rulebook.pdf": "solo_programming",
    "CSE Fest Videography Contest Rulebook 2026.pdf": "videography",
    "Logical Legends Debate Championship 2026 - Official Rulebook (1).pdf": "debate",
    "Tech_Olympiad_2026_Rulebook_and_Syllabus.pdf": "tech_olympiad",
    "rulebook_idea_generation.pdf": "idea_generation",
    "3MT rulebook-1 (1).pdf": "three_mt",
    "Project Showcase Rulebook.pdf": "project_showcase",
}


def tidy(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    words_per_line = sum(len(ln.split()) for ln in lines if ln) / max(1, sum(1 for ln in lines if ln))
    if words_per_line < 1.5:                      # one word per line: glue them back together
        text = " ".join(ln for ln in lines if ln)
        text = re.sub(r"\s*(●|○|•)\s*", r"\n\1 ", text)
        text = re.sub(r"\s+(\d{1,2}\.\s+[A-Z])", r"\n\n\1", text)
        return text.strip()
    out = []
    for ln in lines:                              # drop empty lines and immediate repeats
        if ln and (not out or ln != out[-1]):
            out.append(ln)
    return "\n".join(out)


def main() -> None:
    out_dir = settings.RULEBOOK_DIR / "draft"
    out_dir.mkdir(exist_ok=True)
    for pdf, key in PDFS.items():
        pages = PdfReader(settings.RULEBOOK_DIR / pdf).pages
        body = "\n\n".join(f"<!-- p.{n} -->\n{tidy(p.extract_text() or '')}" for n, p in enumerate(pages, 1))
        (out_dir / f"{key}.txt").write_text(body, encoding="utf-8")
        print(f"{key:17} {len(pages):2} pages  {len(body):6} chars")


if __name__ == "__main__":
    main()
