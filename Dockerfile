FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libsqlcipher-dev \
    sqlcipher \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir sqlcipher3

COPY src/ ./src/
COPY run.py .

RUN groupadd -g 1000 seednox && useradd -u 1000 -g seednox -s /bin/sh appuser \
    && mkdir -p /app/data && chown -R appuser:seednox /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/seednox.db

CMD ["python", "run.py"]
