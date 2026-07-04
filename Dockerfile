FROM python:3.14-slim-bookworm

LABEL maintainer="luciano.garrido@bancoestado.cl"
LABEL description="Asistente Virtual BancoEstado con IA"
LABEL version="1.0.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r bancoestado && useradd -r -g bancoestado -d /app -s /sbin/nologin bancoestado

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bancoestado:bancoestado . .

RUN mkdir -p /app/logs /app/memoria /app/data \
    && touch /app/logs/.keep /app/memoria/.keep /app/data/.keep \
    && chown -R bancoestado:bancoestado /app/logs /app/memoria /app/data \
    && chmod +x /app/entrypoint.sh

USER bancoestado

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_DEBUG=0

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--worker-class", "gthread", "--threads", "4", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log", "--log-level", "info", "app:app"]
