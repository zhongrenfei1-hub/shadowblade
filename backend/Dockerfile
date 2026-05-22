# ShadowBlade backend — Python 3.11 + ffmpeg + yt-dlp + edge-tts + faster-whisper
#
# Targets Railway / Render / Fly.io / any Docker host. Vercel cannot host this
# image because (a) ffmpeg is a ~50 MB native binary, and (b) one mix run
# regularly exceeds Vercel's 60s function timeout.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SHADOWBLADE_STORAGE_ROOT=/data/storage

# System: ffmpeg (with libass + libfreetype for subtitles + drawtext), fonts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache layer for Python deps
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend /app/backend

# Storage volume — Railway/Render/Fly mount a persistent disk here so
# generated MP4s survive restarts.
RUN mkdir -p /data/storage && chmod -R 755 /data

EXPOSE 8000

# Honour platform-injected $PORT (Railway / Render / Fly all set it),
# otherwise default to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend --proxy-headers --forwarded-allow-ips='*'"]
