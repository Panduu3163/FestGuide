# FestGuide as a public demo (docs/deploy.md). Build once, run anywhere that runs a container
# (Hugging Face Spaces, Render, Fly, Railway).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Hugging Face runs containers as user 1000, not root, so the app lives in a folder that user owns.
RUN useradd -m -u 1000 user
WORKDIR /app
RUN chown user:user /app
USER user

# dependencies first, so a code change does not reinstall them
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=user . .

# The rulebook index is built HERE, at image build time, with the small local embedding model:
# no API key is needed to build it, no embedding quota is used at run time, and a restart does not rebuild it.
ENV FESTGUIDE_EMBED_MODEL=fastembed:BAAI/bge-small-en-v1.5 \
    FESTGUIDE_EMBED_DIM=384 \
    FASTEMBED_CACHE_PATH=/app/.fastembed
RUN python -m kb.ingest

# Run-time settings. The two API keys come from the host's secret settings, never from the image.
# 7860 is the port Hugging Face expects; Render sets PORT itself and overrides this.
ENV DEMO_MODE=1 HOST=0.0.0.0 PORT=7860
EXPOSE 7860
CMD ["python", "web.py"]
