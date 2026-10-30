# Ubuntu 24.04 ships Python 3.12 and Tesseract 5 (with Portuguese data) as
# regular packages, so the OCR engine needs no manual install.
FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv ca-certificates \
        tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependencies first: this layer is reused while only source code changes.
COPY pyproject.toml uv.lock README.md ./

FROM base AS dev
RUN uv sync --frozen --no-install-project --python python3.12
COPY src ./src
RUN uv sync --frozen --python python3.12
COPY tests ./tests
RUN chown -R app:app /app
USER app
CMD ["condo-audit", "worker"]

FROM base AS production
RUN uv sync --frozen --no-dev --no-install-project --python python3.12
COPY src ./src
RUN uv sync --frozen --no-dev --python python3.12
USER app
CMD ["condo-audit", "worker"]
