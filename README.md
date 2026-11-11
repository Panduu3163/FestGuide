# FestGuide

IIUC CSE Fest 2026 rulebook and registration assistant. Terminal chat for students,
a second terminal for the organizer. Built for the CSE Industrial Training 2026
(AI/LLM Application Builder, Grow with Data) by Mynul Kabir Nayem, C223163.

All student and registration data is **mock** (synthetic). Rulebooks are the real
CSE Fest 2026 PDFs, used with permission.

    uv sync
    Copy-Item .env.example .env      # keys are needed from milestone M2 on
    uv run python fest_data.py       # create the mock database and print a summary
