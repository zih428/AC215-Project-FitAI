# --- Base image ---
FROM python:3.12-slim-bookworm

# --- System dependencies ---
ARG DEBIAN_PACKAGES="build-essential curl libpq5"
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/.venv

# --- Install deps & create non-root user ---
RUN set -ex; \
    for i in $(seq 1 8); do mkdir -p "/usr/share/man/man${i}"; done && \
    apt-get update && \
    apt-get install -y --no-install-recommends $DEBIAN_PACKAGES && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install uv && \
    useradd -ms /bin/bash app -d /home/app -u 1000 && \
    mkdir -p /app /.venv && chown -R app:app /app /.venv

USER app
WORKDIR /app

# --- Dependency installation ---
COPY --chown=app:app pyproject.toml uv.lock* ./
RUN uv sync --frozen

# --- Copy source code ---
RUN echo "Verifying entrypoint exists in build context:" && ls -al .
COPY --chown=app:app . ./
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8002

ENV GOOGLE_APPLICATION_CREDENTIALS=/secrets/rich-access-471117-r0-f17d92fbf298.json \
    GCP_PROJECT=rich-access-471117 \
    CHROMADB_HOST=chromadb \
    CHROMADB_PORT=8000

ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]