# Explicitly target ARM64 (Apple Silicon M1/M2/M3/M4)
# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM --platform=linux/arm64 python:3.11-slim AS builder

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

COPY requirements.txt .

# Upgrade pip + install Cython first (insightface needs it to compile)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel Cython==3.0.11

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM --platform=linux/arm64 python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN pip install --no-cache-dir packaging

WORKDIR /app
COPY main.py .

# Pre-download buffalo_s model (~85 MB)
RUN python -c "\
from insightface.app import FaceAnalysis; \
a = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider']); \
a.prepare(ctx_id=0, det_size=(640,640)); \
print('Model ready')"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
