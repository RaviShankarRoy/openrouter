# syntax=docker/dockerfile:1.7
# Two stages: builder installs deps, runtime ships only the wheel + venv.

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml ./
RUN pip install --upgrade pip wheel && \
    pip install -e .
COPY . .

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/* && \
    useradd --uid 65532 --no-create-home --shell /bin/false app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build /app
USER 65532
EXPOSE 8000 9092 50051
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", "--error-logfile", "-"]
