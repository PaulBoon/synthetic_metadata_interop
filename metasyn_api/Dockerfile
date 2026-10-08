FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.13@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first so this layer is cached until the lock file changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --extra frontend

COPY main.py docker-entrypoint.sh ./
COPY frontend ./frontend

RUN useradd --create-home --uid 1000 metasyn && chmod +x docker-entrypoint.sh
USER metasyn

# 8000: Metasyn API (FastAPI), 5000: web UI (Flask)
EXPOSE 8000 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/'); u.urlopen('http://127.0.0.1:5000/')"

ENTRYPOINT ["./docker-entrypoint.sh"]
