# FestGuide

IIUC CSE Fest 2026 rulebook and registration assistant. Terminal chat for students,
a second terminal for the organizer. Built for the CSE Industrial Training 2026
(AI/LLM Application Builder, Grow with Data) by Mynul Kabir Nayem, C223163.

All student and registration data is **mock** (synthetic). Rulebooks are the real
CSE Fest 2026 PDFs, used with permission.

    uv sync
    Copy-Item .env.example .env      # then paste your keys into .env (it is git-ignored)
    uv run python fest_data.py       # create the mock database and print a summary
    uv run python -m kb.ingest       # build the rulebook index (156 chunks, embedded Qdrant in .state/)

Keys in `.env`: `GEMINI_API_KEY` (chat + embeddings), `OPENROUTER_API_KEY` (fallback model), `LANGSMITH_API_KEY`
(tracing + scorecard). Without the Gemini embedding quota, set `FESTGUIDE_EMBED_MODEL=fastembed:BAAI/bge-small-en-v1.5`
and `FESTGUIDE_EMBED_DIM=384` and run the ingest again (local, no key).

Run it:

    uv run python chat.py --student C233001        # the student terminal (try --trace and --langsmith)
    uv run python organizer.py --watch             # the organizer terminal
    uv run python web.py                           # the web version: http://127.0.0.1:8000/ and /organizer
    uv run python demo.py                          # all seven demo moments in one scripted run
    uv run python scorecard.py                     # 32-question scorecard, stored in LangSmith

The live demo script is in `docs/demo.md`; a recorded backup run is in `docs/backup_run.txt`.

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
- M6 follow-up rewriting (E2): the `rewrite` node in graph.py, `rewrite_prompt` in prompts.yml

    uv run python tests/check_rewrite.py                # "the second one" becomes a standalone question (about 15 model calls)

  Local embeddings (no Gemini embedding quota): set `FESTGUIDE_EMBED_MODEL=fastembed:BAAI/bge-small-en-v1.5`
  and `FESTGUIDE_EMBED_DIM=384`, then run `uv run python -m kb.ingest` once.
- M7 model layer proof (C2): LangSmith tracing, fallback test, scorecard

    uv run python chat.py --student C233001 --langsmith   # every run is traced in LangSmith (project "festguide")
    uv run python tests/check_fallback.py                 # wrong Gemini key on purpose: OpenRouter answers instead
    uv run python scorecard.py                            # 32 questions from data/scorecard.yml, stored as a LangSmith experiment
    uv run python scorecard.py --local                    # same, printed here only

  Change the model or a prompt, run the scorecard again, and compare the two experiments in LangSmith.
  Traces contain what students type (private numbers are hidden only after the first step), so use mock data.
- M8 advanced retrieval (E3, stretch): event filter on, hybrid search available but off

    uv run python kb/compare_retrieval.py                 # dense vs filter vs hybrid, no model calls

  Measured with the local embedder (26 questions): the event filter raised hit@1 from 4 to 8 of 10 on questions
  that do not name the event; hybrid (BM25 + dense) added nothing and lost some. So `EVENT_FILTER=true` is the
  default and `RETRIEVAL_MODE` stays "dense" (`FESTGUIDE_RETRIEVAL_MODE=hybrid` to try it).
- M9 the demo: demo.py (scripted run of all seven moments), docs/demo.md (live script), docs/backup_run.txt (recording)

    uv run python demo.py --step --out docs/backup_run.txt

  The fallback model is now gpt-oss-120b: the 20b version returned unusable structured output about half the time.
- M10 the web version: web.py (FastAPI) and static/ (a student page and an organizer page, plain HTML and JavaScript)

    uv run python web.py                  # student: http://127.0.0.1:8000/   organizer: http://127.0.0.1:8000/organizer
    uv run python tests/check_web.py      # 21 checks through the real endpoints (add --offline to skip the model calls)

  No new logic: each endpoint calls what the terminals call (`graph.run`, `approvals.pending`, `approvals.decide`),
  and the two pages are connected through the same checkpoint file as the two terminals. The student page shows each
  answer with a collapsible "graph steps" trace, holds new messages while a request waits, and shows the organizer's
  decision by itself (it asks the server every 2 seconds). The organizer page lists waiting requests with the checks,
  the cited rule and what the student wrote; approve with a note, or reject with a reason. Set `ORGANIZER_PIN` in
  `.env` to make the organizer endpoints need a PIN. The student picker stands in for a login (mock students only;
  phone numbers never leave the server). To publish it, put it behind real sign-in first.
- M11 hosted-demo mode: `DEMO_MODE=1` in web.py, `/demo` page, Dockerfile, render.yaml, docs/deploy.md

    DEMO_MODE=1 uv run python web.py      # then http://127.0.0.1:8000/demo (student and organizer side by side)

  For a public site: per-visitor chats and inboxes, rate limits (30 messages per hour per visitor, 300 a day), registrations
  reset to the seed teams every 30 minutes and on "Reset demo". The host must be a container host (Render, Fly, Railway), not
  Vercel: the pause-and-approve flow needs a disk that persists between requests. See `docs/deploy.md`.
