# ---- MedAlert API image ----
# slim = smaller image -> faster pulls, smaller attack surface.
FROM python:3.12-slim

# Don't write .pyc files; flush logs immediately (so `docker logs` is live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDALERT_DB_PATH=/data/medalert.db

WORKDIR /app

# Copy requirements first: Docker caches this layer, so dependencies are only
# reinstalled when requirements.txt changes, not on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Security: don't run as root inside the container.
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000

# Docker marks the container "unhealthy" if /health fails.
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
