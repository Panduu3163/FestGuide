"""Run a few rules questions through the RAG and print answers with citations.

    uv run python kb/try_questions.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kb import store  # noqa: E402
from kb.rag import answer_with_rag, render  # noqa: E402

QUESTIONS = [
    "How much is the debate registration fee, and can I get it back?",
    "How big can a team be for Idea Generation?",
    "Can EEE students join Idea Generation?",
    "Is there a prize money for the programming contest winner?",
    "What is the time limit of the videography contest video?",
]

for q in QUESTIONS:
    print(f"\nQ: {q}\n{render(answer_with_rag(q))}")
store.close()
