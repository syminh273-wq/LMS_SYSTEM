# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gcc \
    g++ \
    libgomp1 \
    libstdc++6 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# package-mode = false in pyproject.toml means this isn't an installable
# package — Poetry only resolves/installs the dependencies from poetry.lock.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel Cython==3.0.11 poetry==2.3.2 \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main --no-interaction --no-ansi \
    && pip uninstall -y poetry

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

WORKDIR /app
COPY . .
RUN chmod +x docker/backend/entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LMS_SYSTEM.settings

EXPOSE 8000
# Entrypoint runs sync_cassandra (creates any missing column families) before
# exec-ing into CMD.
ENTRYPOINT ["docker/backend/entrypoint.sh"]
# `manage.py runserver` (not raw `daphne LMS_SYSTEM.asgi:application`) — the
# latter imports asgi.py before django.setup() runs, which crashes with
# AppRegistryNotReady because asgi.py imports app models at module level.
# channels/daphne being in INSTALLED_APPS makes runserver itself serve ASGI.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
