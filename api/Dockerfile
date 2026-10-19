# syntax=docker/dockerfile:1

# ---------- Builder: dependencias de runtime ----------
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ---------- Builder de desarrollo: runtime + herramientas de test ----------
FROM builder AS builder-dev

RUN /opt/venv/bin/pip install ".[dev]"

# ---------- Base común de runtime ----------
FROM python:3.12-slim-bookworm AS base

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system app \
    && useradd --system --gid app --create-home app

WORKDIR /app
COPY --chown=app:app src ./src
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini
RUN chown app:app /app

USER app
EXPOSE 8000

# ---------- Desarrollo: hot-reload y dependencias de test ----------
FROM base AS dev

COPY --from=builder-dev /opt/venv /opt/venv

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- Runtime de producción ----------
FROM base AS runtime

COPY --from=builder /opt/venv /opt/venv

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=3)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
