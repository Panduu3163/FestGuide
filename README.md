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
- M2 structured output (Intent, EventRules), offline rule extractor, graph skeleton (C1, C7)

    uv run python extract_rules.py       # rulebooks -> data/events.yml (checked against the text)
    uv run python graph.py               # run four sample messages through the graph
    uv run python kb/audit.py            # check cleaned rulebooks and retrieval
- M3 tools and agent loop (C3): tools.py, agent.py, draft.py

    uv run python tests/check_tools.py      # tool logic, no model, free
    uv run python tests/check_agent.py      # real messages through the graph (about 20 model calls)
    uv run python graph.py                  # seven sample messages with tool calls shown
- M4 conversation memory (C4): memory.py, chat.py (student terminal)

    uv run python chat.py --student C233001            # chat; closing and reopening continues it
    uv run python tests/check_memory.py                # memory checks, no model needed
- M5 guardrails (C5) and human approval (E1): guards.py, approvals.py, organizer.py

    uv run python chat.py --student C233001             # terminal 1: the student
    uv run python organizer.py --watch                  # terminal 2: the organizer (approve with a note, reject with a reason)
    uv run python tests/check_guards.py                 # attacks blocked, normal questions pass
    uv run python tests/check_approval.py               # pause, restart, approve, reject (no model)
