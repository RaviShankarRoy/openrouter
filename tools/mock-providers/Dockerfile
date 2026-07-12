# Multi-stage build keeps the runtime image lean (< 200MB target per DRD §22.2).
# Stage 1: build wheels into an isolated layer so the runtime stage has no compilers.
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip build \
 && pip wheel --no-cache-dir --wheel-dir /wheels .

# Stage 2: minimal runtime — only the wheel + its deps.
FROM python:3.12-slim AS runtime

# Run as a non-root user; the gateway never trusts mock data anyway,
# but it keeps Trivy clean (DRD §22 / SE-009).
RUN groupadd --system mock && useradd --system --gid mock --home /app mock

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl \
 && rm -rf /wheels

USER mock
ENV MOCK_PORT=9100
EXPOSE 9100

# uvicorn invoked directly — the FastAPI app is `src.main:app`.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9100", "--no-access-log"]
