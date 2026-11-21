# syntax=docker/dockerfile:1

# Pinned by digest (python:3.11-slim) rather than a floating tag so rebuilds
# are reproducible. Keep in sync via the docker-ecosystem Dependabot entry.
FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535 AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535

LABEL org.opencontainers.image.source="https://github.com/by-tayo/sys-exp" \
      org.opencontainers.image.description="Cross-platform system metrics exporter for Prometheus" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as a non-root user rather than the image default (root).
RUN groupadd --gid 1000 exporter \
    && useradd --uid 1000 --gid exporter --shell /usr/sbin/nologin --no-create-home exporter \
    && mkdir -p /app/data \
    && chown -R exporter:exporter /app

COPY --from=builder /install /usr/local
# Explicit allow-list (not a wildcard COPY) to keep the image minimal.
# Add any new top-level module here, or it won't ship in the image.
COPY main.py metrics.py net_observer.py config.py ./

USER exporter

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["python", "main.py", "--port", "8000"]
