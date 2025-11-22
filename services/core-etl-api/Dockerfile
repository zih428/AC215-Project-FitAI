# --- Base image ---
FROM python:3.12-slim-bookworm

# --- System dependencies ---
ARG DEBIAN_PACKAGES="build-essential curl libpq5 bash"
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
COPY --chown=app:app pyproject.toml ./
RUN uv sync --no-dev

# --- Copy source code ---
COPY --chown=app:app . ./
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
