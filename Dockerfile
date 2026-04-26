# Multi-stage build for production
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Production stage
FROM python:3.14-slim-bookworm AS production

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY api/ ./api/
COPY cli/ ./cli/
COPY config/ ./config/
COPY core/ ./core/
COPY messaging/ ./messaging/
COPY providers/ ./providers/
COPY server.py ./

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/agent_workspace && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/health')" || exit 1

EXPOSE 8082

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8082", "--proxy-headers"]
