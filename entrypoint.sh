#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Asistente Virtual BancoEstado - Inicio"
echo "  $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "============================================"

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "[ADVERTENCIA] GITHUB_TOKEN no configurado - iniciando en modo DEMO"
    echo "[ADVERTENCIA] Las respuestas seran simuladas, sin llamadas a GPT-4o"
fi

echo "[INFO] Verificando directorios..."
mkdir -p /app/logs /app/memoria /app/data

echo "[INFO] Inicializando base de datos..."
python -c "from app import init_db; init_db()" || echo "[WARN] No se pudo inicializar la base de datos - verificar logs"

echo "[INFO] Iniciando Gunicorn en 0.0.0.0:5000..."
echo "============================================"

exec "$@"
