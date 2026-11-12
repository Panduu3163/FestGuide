# Putting the demo on a public URL (portfolio)

## Where it can run

| Host | Works? | Why |
|---|---|---|
| **Render** (free Docker web service) | yes | one long-running container, a normal disk, no short time limit. `render.yaml` is ready. **Checked: Render asks for a credit card to verify identity, even for the free plan** (a temporary $1 authorization). The free plan has 512 MB; the app measured about 225 MB resident after real questions |
| Hugging Face Spaces (Docker) | only with a paid PRO plan | **Checked: free accounts can create Static Spaces only.** `deploy/hf_push.sh` is ready if you subscribe: it pushes a clean one-commit snapshot without the large PDFs (HF refuses files over 10 MB) |
| Fly.io, Railway, any VPS | yes | same `Dockerfile`; they ask for a card too |
| Your own PC + a tunnel (Cloudflare Tunnel, ngrok) | yes, free | live only while the PC is on; run `DEMO_MODE=1 uv run python web.py` and tunnel port 8000 |
| **Vercel** | **no, not for this backend** | functions are short-lived, the disk is read-only apart from a temporary `/tmp` that is not shared between runs, and one reply can take up to 30 seconds. A request that pauses for the organizer would be lost, and the vector index and embedding library are too big for a function |

A static front end on Vercel with the API on Render is possible, but it needs cross-site cookies and CORS for no benefit. One service that serves both pages is simpler.

## What demo mode does (`DEMO_MODE=1`, already set in the `Dockerfile`)

- Each visitor gets a cookie, their own chat, and an organizer inbox that shows only their own requests. Nobody can approve someone else's request.
- 30 messages per hour per visitor and 300 per day for everyone, so a crowd cannot use up the free model quota.
- The registrations table returns to its three seed teams every 30 minutes (`DEMO_RESET_MINUTES`) and when a visitor presses **Reset demo**.
- **`/demo`** is the page to link from the portfolio: student and organizer side by side. `/` and `/organizer` still work alone.
- Tracing to LangSmith is off unless you set `LANGSMITH_TRACING=true` and a key on the host. Leave it off: traces keep what strangers type.

## Steps (you do these; they need your accounts)

1. **Push the repo to GitHub** (private is fine; Render can read private repos).
   Before making it public, decide about `rulebooks/*.pdf`: they are the organizers' real documents. The image does not need
   them (`.dockerignore` skips them; the demo uses `rulebooks/clean/*.md`), so you can remove the PDFs from the repo first.
2. On render.com: **New > Blueprint**, pick the repo. Render reads `render.yaml`.
3. In the service's **Environment** tab, set the two secrets: `GEMINI_API_KEY` and `OPENROUTER_API_KEY`.
   Never put them in a file in the repo. (`.env` is git-ignored and is not copied into the image.)
4. Deploy. The first build takes several minutes: it installs the packages and builds the rulebook index with the local embedding model.
5. Open `https://<your-service>.onrender.com/demo` and run the same demo as `docs/demo.md` (moments 1 to 6).

## Things to know

- The free plan sleeps after about 15 minutes without visitors; the first visit after that takes up to a minute. Open it once before showing anyone.
- The free plan has 512 MB of memory. The local embedding model plus the app should fit, but if the service restarts with an out-of-memory message, use the smallest paid plan.
- The disk is not permanent, so the checkpoint file and registrations vanish on every redeploy. That is fine for mock data.
- The chat uses Gemini first and falls back to OpenRouter. If Gemini's free quota is used up, replies are slower (about 30 seconds) but still work.
- The image build has not been tested on this machine (no Docker here). The same startup was run locally with `DEMO_MODE=1` and passes `tests/check_web.py`.
- Run locally in demo mode: `DEMO_MODE=1 uv run python web.py`, then open http://127.0.0.1:8000/demo
