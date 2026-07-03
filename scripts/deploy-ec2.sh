#!/bin/bash
set -euo pipefail

# =============================================================================
# Script de deploy para AWS EC2 - Asistente Virtual BancoEstado
# Uso: sudo ./scripts/deploy-ec2.sh
#
# Requisitos previos:
#   1. EC2 corriendo Amazon Linux 2023 o Ubuntu 22.04+
#   2. Security Groups: 22 (SSH tu IP), 80 (HTTP)
#   3. Variables de entorno exportadas o archivo .env en /opt/bancoestado/
# =============================================================================

APP_DIR="/opt/bancoestado"
VENV_DIR="${APP_DIR}/.venv"
LOG_DIR="${APP_DIR}/logs"
APP_USER="bancoestado"
GITHUB_REPO="BlackCatVSC/PRUEBA_IA"
BRANCH="${BRANCH:-main}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    err "Este script debe ejecutarse como root (sudo)"
fi

log "Iniciando deploy de Asistente Virtual BancoEstado en $(hostname)..."

# --- 1. Paquetes del sistema ---
log "Instalando paquetes del sistema..."
if command -v dnf &>/dev/null; then
    dnf update -y
    dnf install -y python3 python3-pip python3-devel gcc nginx curl git
elif command -v apt-get &>/dev/null; then
    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv python3-dev build-essential nginx curl git
else
    err "Sistema operativo no soportado. Use Amazon Linux 2023 o Ubuntu 22.04+"
fi
ok "Paquetes del sistema instalados"

# --- 2. Crear usuario de la aplicacion ---
log "Configurando usuario ${APP_USER}..."
if ! id -u "${APP_USER}" &>/dev/null; then
    useradd -r -s /sbin/nologin -d "${APP_DIR}" "${APP_USER}"
    ok "Usuario ${APP_USER} creado"
else
    ok "Usuario ${APP_USER} ya existe"
fi

# --- 3. Crear directorios ---
log "Creando estructura de directorios..."
mkdir -p "${APP_DIR}" "${LOG_DIR}" "${APP_DIR}/memoria" "${APP_DIR}/data"
ok "Directorios creados"

# --- 4. Clonar o actualizar codigo ---
if [ -d "${APP_DIR}/.git" ]; then
    log "Repositorio existente, actualizando..."
    cd "${APP_DIR}"
    git fetch origin "${BRANCH}"
    git reset --hard "origin/${BRANCH}"
    ok "Codigo actualizado desde ${BRANCH}"
else
    log "Clonando repositorio (branch: ${BRANCH})..."
    git clone --branch "${BRANCH}" --single-branch \
        "https://github.com/${GITHUB_REPO}.git" "${APP_DIR}"
    ok "Repositorio clonado"
fi

# --- 5. Configurar entorno virtual Python ---
log "Configurando entorno virtual Python..."
python3 -m venv "${VENV_DIR}" --clear
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
ok "Dependencias Python instaladas"

# --- 6. Configurar variables de entorno ---
log "Verificando variables de entorno..."
if [ ! -f "${APP_DIR}/.env" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
    warn "============================================================"
    warn "  ATENCION: No se encontro .env ni GITHUB_TOKEN exportado"
    warn "  La aplicacion iniciara en MODO DEMO (sin GPT-4o)"
    warn ""
    warn "  Para produccion, crea /opt/bancoestado/.env con:"
    warn "    GITHUB_TOKEN=tu_token"
    warn "    LANGSMITH_API_KEY=tu_key (opcional)"
    warn "    EMAIL_PASSWORD=tu_password (opcional)"
    warn "============================================================"
else
    ok "Variables de entorno configuradas"
fi

# --- 7. Inicializar base de datos ---
log "Inicializando base de datos..."
cd "${APP_DIR}"
"${VENV_DIR}/bin/python" -c "from app import init_db; init_db()" || true
ok "Base de datos inicializada"

# --- 8. Configurar permisos ---
log "Configurando permisos..."
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 750 "${APP_DIR}"
chmod 770 "${LOG_DIR}" "${APP_DIR}/memoria" "${APP_DIR}/data"
ok "Permisos configurados"

# --- 9. Instalar y habilitar systemd services ---
log "Configurando servicios systemd..."
cp "${APP_DIR}/systemd/bancoestado.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable bancoestado.service

# --- 10. Iniciar aplicacion ---
log "Iniciando servicio bancoestado..."
systemctl restart bancoestado.service
sleep 3
if systemctl is-active --quiet bancoestado.service; then
    ok "Servicio bancoestado activo y corriendo"
else
    warn "El servicio no pudo iniciar. Revisa: journalctl -u bancoestado.service"
fi

# --- 11. Configurar nginx ---
log "Configurando nginx..."
if [ -f /etc/nginx/conf.d/default.conf ]; then
    mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
fi
cp "${APP_DIR}/nginx/bancoestado.conf" /etc/nginx/conf.d/bancoestado.conf
sed -i 's|server app:5000;|server 127.0.0.1:5000;|' /etc/nginx/conf.d/bancoestado.conf

nginx -t && systemctl restart nginx && systemctl enable nginx
ok "Nginx configurado y corriendo"

# --- 12. Verificar health check ---
log "Verificando health check..."
sleep 2
if curl -sf http://127.0.0.1:5000/health > /dev/null 2>&1; then
    ok "Health check de la app: OK"
else
    warn "Health check fallo. Revisa los logs: tail -f ${LOG_DIR}/error.log"
fi

# --- Resumen final ---
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "DESCONOCIDA")
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   DEPLOY COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  Aplicacion:  ${BLUE}http://${PUBLIC_IP}${NC}"
echo -e "  Health:      ${BLUE}http://${PUBLIC_IP}/health${NC}"
echo -e "  Dashboard:   ${BLUE}http://${PUBLIC_IP}/dashboard${NC}"
echo -e "  Logs app:    ${BLUE}journalctl -u bancoestado -f${NC}"
echo -e "  Logs nginx:  ${BLUE}tail -f /var/log/nginx/access.log${NC}"
echo ""
