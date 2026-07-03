#!/bin/bash
# =============================================================================
# EC2 User Data Script - Amazon Linux 2023
# Pega esto en "User data" al lanzar la instancia EC2.
#
# La instancia se auto-configura en el primer boot:
#   - Instala Docker + docker-compose
#   - Clona el repo
#   - Levanta con docker-compose
# =============================================================================

set -euo pipefail
exec > /var/log/user-data.log 2>&1

# --- 1. Instalar Docker ---
yum update -y
yum install -y docker git curl

systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# --- 2. Instalar docker-compose ---
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# --- 3. Clonar repo ---
APP_DIR="/opt/bancoestado"
mkdir -p "${APP_DIR}"

git clone --branch main https://github.com/BlackCatVSC/PRUEBA_IA.git "${APP_DIR}" 2>/dev/null || \
    (cd "${APP_DIR}" && git fetch origin main && git reset --hard origin/main)

# --- 4. Crear .env para docker-compose ---
# IMPORTANTE: Reemplaza GITHUB_TOKEN con tu token real.
# Si lo dejas vacio la app corre en modo DEMO (respuestas simuladas).
cat > "${APP_DIR}/.env" << 'ENVEOF'
GITHUB_TOKEN=
GITHUB_BASE_URL=https://models.inference.ai.azure.com
LANGSMITH_TRACING=false
FLASK_DEBUG=0
ENVEOF

# --- 5. Levantar contenedores ---
cd "${APP_DIR}"
docker-compose up -d --build

echo "[$(date)] User data completado. App corriendo en http://$(curl -s http://checkip.amazonaws.com || echo 'localhost')"
