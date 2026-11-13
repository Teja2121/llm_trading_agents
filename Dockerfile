FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer stays cached until the lock file changes
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY trading_agents ./trading_agents

# Run as a non-root user. /app/data is where the SQLite file lives.
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser

ENTRYPOINT ["python", "-m", "trading_agents"]
CMD ["--help"]