# FestGuide

IIUC CSE Fest 2026 rulebook and registration assistant. Terminal chat for students,
a second terminal for the organizer. Built for the CSE Industrial Training 2026
(AI/LLM Application Builder, Grow with Data) by Mynul Kabir Nayem, C223163.

All student and registration data is **mock** (synthetic). Rulebooks are the real
CSE Fest 2026 PDFs, used with permission.

    uv sync
    Copy-Item .env.example .env      # keys are needed from milestone M2 on
    uv run python fest_data.py       # create the mock database and print a summary

## Milestones

- M0 setup and mock data
- M1 RAG with citations (C6)

    uv run python kb/extract_pdfs.py     # PDF -> rough text drafts (rulebooks/draft)
    uv run python kb/make_mock_v1.py     # mock earlier versions for version handling
    uv run python kb/ingest.py           # build the Qdrant index in .state/qdrant
    uv run python kb/rag.py "Can I use ChatGPT during the programming contest?"
