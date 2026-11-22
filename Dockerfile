FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    yt-dlp

WORKDIR /app
COPY main.py .

# Render uses PORT env var (default 10000)
ENV PORT=10000
EXPOSE 10000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
