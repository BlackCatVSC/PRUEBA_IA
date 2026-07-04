import os
import re
import json
import uuid
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

os.environ["OPENAI_API_BASE"] = os.environ.get("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")
os.environ["OPENAI_API_KEY"] = os.environ.get("GITHUB_TOKEN", "")
os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get("LANGSMITH_TRACING", "false")
os.environ["LANGCHAIN_API_KEY"] = os.environ.get("LANGSMITH_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.environ.get("LANGSMITH_PROJECT", "default")

from herramientas.config import MODELO_POR_DEFECTO
from herramientas.observability import AgenteObservable, get_logger

web_log = get_logger("web.bancoestado")

MODO_DEMO = not bool(os.environ.get("GITHUB_TOKEN"))

if not MODO_DEMO:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=MODELO_POR_DEFECTO, temperature=0)
else:
    llm = None
    web_log.warning("Sin GITHUB_TOKEN - modo demo (respuestas simuladas)")

from herramientas.herramientas_bancoestado import TOOL_LIST
from herramientas.planificador import Planificador, Orquestador
from herramientas.seguridad import OrquestadorSeguridad, DetectorPII, SanitizadorEntrada
from herramientas.bancoestado_api import BancoEstadoAPI
from herramientas.langsmith_config import (LangSmithConfig, traceable_si_habilitado,
                                           registrar_metricas_langsmith)
from herramientas.config import (MODELO_POR_DEFECTO, CACHE_UMBRAL_SIMILITUD,
                                 CACHE_TTL_SEGUNDOS, PROCESADOR_TAMANO_LOTE,
                                 ANOMALIAS_VENTANA, ANOMALIAS_FACTOR_SPIKE,
                                 ANOMALIAS_UMBRAL_ERROR, ANOMALIAS_UMBRAL_CACHE)

TOOL_MAP = {tool.name: tool for tool in TOOL_LIST}
planificador = Planificador()
orquestador = Orquestador(TOOL_MAP)
seguridad = OrquestadorSeguridad(llm=llm)

# ─── OBSERVABILIDAD (IL3.1) ─────────────────────────────────────
agente_obs_web = AgenteObservable("bancoestado-web")

# ─── CACHE + LOTES (IL3.2) ──────────────────────────────────────
from herramientas.cache_semantico import CacheSemantico, estimar_tokens
from herramientas.procesador_lotes import ProcesadorLotes, Prioridad
cache_web = CacheSemantico(umbral_similitud=CACHE_UMBRAL_SIMILITUD, ttl_segundos=CACHE_TTL_SEGUNDOS)
procesador_lotes = ProcesadorLotes(tamano_lote=PROCESADOR_TAMANO_LOTE)

# ─── REPORTE + ANOMALIAS (IL3.4) ─────────────────────────────────
from herramientas.reporte_sostenibilidad import DetectorAnomalias, ReporteSostenibilidad
detector_anomalias = DetectorAnomalias(ventana=ANOMALIAS_VENTANA, factor_spike=ANOMALIAS_FACTOR_SPIKE,
                                       umbral_error_pct=ANOMALIAS_UMBRAL_ERROR,
                                       umbral_cache_drop_pct=ANOMALIAS_UMBRAL_CACHE)
reporte_sost = ReporteSostenibilidad(agente_obs_web, cache_web, seguridad,
                                     detector_anomalias, procesador_lotes)

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = (
    "Eres un asistente virtual de BancoEstado. Tu funcion es orientar a los clientes "
    "con dudas sobre productos, cuentas, tarjetas, creditos y operaciones bancarias. "
    "Usa las herramientas disponibles para consultar informacion y ejecutar operaciones. "
    "Responde siempre en espanol de forma clara, amable y profesional. "
    "Si el cliente reporta perdida o robo de tarjeta, prioriza el bloqueo inmediato. "
    "Para creditos sobre $3.000.000, indica que se requiere verificacion adicional. "
    "Para creditos sobre $5.000.000, indica que debe ir a sucursal. "
    "Usa el historial de chat si esta disponible para mantener contexto."
    "\n\nREGLAS PARA OPERACIONES CON DINERO:"
    "\n- Si el cliente quiere MOVER dinero entre sus cuentas (ej: 'saca de RUT y pon en Ahorros', "
    "o 'saca de Ahorros y pon en RUT', o 'transfiere desde cuenta X a cuenta Y'), USA SIEMPRE "
    "la herramienta 'transferir' con tipo_cuenta_origen y tipo_cuenta_destino adecuados. "
    "transferir funciona en AMBOS sentidos (RUT->Ahorros y Ahorros->RUT)."
    "\n- La herramienta 'actualizar_saldo' es SOLO para depositos externos (loteria, herencia, "
    "ingreso de dinero externo). NO acepta montos negativos. NO la uses para 'sacar' dinero "
    "ni para mover dinero entre cuentas del cliente."
    "\n\nREGLAS PARA CREACION DE CUENTAS:"
    "\n- NUNCA ofrezcas crear una cuenta sin antes verificar si ya existe. "
    "Usa consultar_saldo(tipo_cuenta) para verificar si la cuenta existe. "
    "Si la herramienta devuelve 'success: true', la cuenta ya existe y NO debes crear otra."
    "\n- Si la herramienta devuelve error de cuenta no encontrada, ahi si puedes ofrecer crearla."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

app = Flask(__name__)
CORS(app)

auth_tokens: dict[str, dict] = {}
failed_logins: dict[str, list] = {}

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTOS = 15
MAX_AUTH_TOKEN_AGE_HORAS = 24

# ─── Base de datos de usuarios ────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "usuarios.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rut TEXT NOT NULL DEFAULT '12.345.678-9',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN rut TEXT NOT NULL DEFAULT '12.345.678-9'")
    except sqlite3.OperationalError:
        pass  # Already exists
    conn.commit()
    conn.close()
    web_log.info("Base de datos lista en %s", DB_PATH)


def _send_login_email(email: str, name: str, rut: str = "12.345.678-9"):
    """Envia correo de bienvenida con resumen de cuentas al iniciar sesion."""
    try:
        from herramientas.bancoestado_api import BancoEstadoAPI
        api = BancoEstadoAPI(rut=rut)
        cliente_data = api._get_cliente(rut)
        cuentas = cliente_data["cuentas"]
        cr = cuentas["CuentaRUT"]
        ca = cuentas["CuentaAhorros"]
        total = cr["saldo"] + ca["saldo"]

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cuerpo_html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="color-scheme" content="light">
            <style>
                @media screen and (max-width: 480px) {{
                    .welcome-container {{ max-width: 100% !important; margin: 0 !important; }}
                    .welcome-header {{ padding: 16px !important; border-radius: 0 !important; }}
                    .welcome-header h2 {{ font-size: 18px !important; }}
                    .welcome-body {{ padding: 16px !important; border-radius: 0 !important; }}
                    .welcome-row span {{ font-size: 13px !important; }}
                    .welcome-footer {{ font-size: 11px !important; }}
                }}
            </style>
        </head>
        <body style="font-family:Arial,Helvetica,sans-serif;color:#333;margin:0;padding:0;background:#f5f5f5;-webkit-text-size-adjust:100%;">
            <div class="welcome-container" style="max-width:520px;margin:20px auto;width:100%;">
                <div class="welcome-header" style="background:#0066cc;color:white;padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h2 style="margin:0;font-size:22px;">Bienvenido, {name}!</h2>
                    <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">Has iniciado sesion en BancoEstado</p>
                </div>
                <div class="welcome-body" style="background:white;padding:24px;border-radius:0 0 12px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <p style="font-size:16px;margin:0 0 16px;">Resumen de tus cuentas:</p>
                    <div style="background:#f8f9fb;border-radius:8px;padding:16px;margin-bottom:16px;">
                        <div class="welcome-row" style="display:flex;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;">
                            <span>CuentaRUT</span>
                            <span style="font-weight:bold;">${cr['saldo']:,}</span>
                        </div>
                        <div class="welcome-row" style="display:flex;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;">
                            <span>Cuenta de Ahorros</span>
                            <span style="font-weight:bold;">${ca['saldo']:,}</span>
                        </div>
                        <div style="border-top:1px solid #ddd;padding-top:12px;display:flex;justify-content:space-between;flex-wrap:wrap;">
                            <span style="font-weight:bold;">Total en cuentas</span>
                            <span style="font-weight:bold;color:#0066cc;">${total:,}</span>
                        </div>
                    </div>
                    <p class="welcome-footer" style="font-size:12px;color:#999;margin:0;text-align:center;">
                        Inicio de sesion: {ahora}<br>
                        Asistente Virtual BancoEstado
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        from herramientas.email_sender import enviar_reporte
        resultado = enviar_reporte(f"Inicio de sesion - BancoEstado", cuerpo_html, email)
        web_log.info("EMAIL: %s", resultado)
    except Exception as e:
        web_log.error("EMAIL error enviando bienvenida a %s: %s", email, e)

sessions = {}
MAX_SESIONES = 100
MAX_HORAS_INACTIVIDAD = 1


def limpiar_sesiones_antiguas():
    """Elimina sesiones inactivas por más de MAX_HORAS_INACTIVIDAD."""
    ahora = datetime.now()
    viejas = [
        sid for sid, s in sessions.items()
        if (ahora - datetime.fromisoformat(s["ultima_actividad"])).total_seconds() > MAX_HORAS_INACTIVIDAD * 3600
    ]
    for sid in viejas:
        del sessions[sid]
    if len(sessions) > MAX_SESIONES:
        sobrantes = sorted(sessions.keys(), key=lambda sid: sessions[sid]["ultima_actividad"])[:len(sessions) - MAX_SESIONES]
        for sid in sobrantes:
            del sessions[sid]


def limpiar_auth_tokens_expirados():
    """Elimina tokens de autenticacion expirados por antiguedad."""
    ahora = datetime.now()
    expirados = [
        t for t, info in auth_tokens.items()
        if (ahora - datetime.fromisoformat(info["created"])).total_seconds() > MAX_AUTH_TOKEN_AGE_HORAS * 3600
    ]
    for t in expirados:
        del auth_tokens[t]


def limpiar_failed_logins():
    """Limpia intentos fallidos de login expirados."""
    ahora = time.time()
    for email in list(failed_logins.keys()):
        failed_logins[email] = [t for t in failed_logins[email] if ahora - t < LOCKOUT_MINUTOS * 60]
        if not failed_logins[email]:
            del failed_logins[email]


def create_session(rut: str = "12.345.678-9"):
    session_id = str(uuid.uuid4())
    from langchain_classic.memory import ConversationBufferMemory
    from langchain_classic.agents import create_openai_tools_agent, AgentExecutor

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    ahora = datetime.now()
    session = {
        "memory": memory,
        "history": [],
        "created": ahora.isoformat(),
        "ultima_actividad": ahora.isoformat(),
        "rut": rut,
    }

    if not MODO_DEMO:
        agent = create_openai_tools_agent(llm, TOOL_LIST, prompt)
        ls_callbacks = LangSmithConfig.get_callbacks(
            tags=["web", "agente_bancoestado"],
        )
        executor = AgentExecutor(
            agent=agent,
            tools=TOOL_LIST,
            memory=memory,
            verbose=False,
            max_iterations=5,
            callbacks=ls_callbacks if ls_callbacks else None,
        )
        session["executor"] = executor

    sessions[session_id] = session
    return session_id


def _extraer_monto(texto: str) -> int | None:
    """Extrae un monto numérico desde el texto del usuario."""
    import re
    t = texto.lower().replace('$', '').replace(',', '').strip()
    m = re.search(r'(\d+)\s*(millones|millon|mil)?', t)
    if not m:
        return None
    num = float(m.group(1))
    unidad = m.group(2) or ''
    if 'millon' in unidad:
        return int(num * 1_000_000)
    if 'mil' in unidad:
        return int(num * 1_000)
    if num >= 1000:
        return int(num)
    # Si es un número pequeño suelto como "50000"
    numeros = re.findall(r'\b(\d{3,})\b', t)
    if numeros:
        return int(max(float(n) for n in numeros))
    return None


def _extraer_cuenta(texto: str) -> str | None:
    """Extrae el tipo de cuenta desde el texto del usuario."""
    t = texto.lower()
    if 'ahorro' in t or 'caja de ahorro' in t:
        return 'CuentaAhorros'
    if 'rut' in t or 'cuenta rut' in t:
        return 'CuentaRUT'
    return None


def procesar_demo(consulta: str, session: dict = None) -> str:
    # --- 1. Verificar acción pendiente (multi-turno) ---
    pending = (session or {}).get("pending_action")
    if pending:
        if pending["type"] == "deposito":
            if pending.get("monto") is None:
                monto = _extraer_monto(consulta)
                if monto:
                    pending["monto"] = monto
                    session["pending_action"] = pending
                    return (
                        f"Perfecto, seran ${monto:,}.\n"
                        "¿A que cuenta quieres depositarlo?\n"
                        "  - *CuentaRUT*\n"
                        "  - *Cuenta de Ahorros*"
                    )
                return "No entendi el monto. ¿Cuanto dinero quieres depositar? (ej: 50000, 100 mil, 2 millones)"

            if pending.get("tipo_cuenta") is None:
                cuenta = _extraer_cuenta(consulta)
                if not cuenta:
                    return "¿A que cuenta? Responde *CuentaRUT* o *Cuenta de Ahorros*."
                pending["tipo_cuenta"] = cuenta
                session.pop("pending_action", None)

                # Ejecutar depósito
                resultado = TOOL_MAP["actualizar_saldo"].func(tipo_cuenta=cuenta, monto=pending["monto"])
                try:
                    data = json.loads(resultado)
                    if data.get("success"):
                        return (
                            f"✅ Deposito realizado con exito.\n"
                            f"  Cuenta: {cuenta}\n"
                            f"  Monto: ${pending['monto']:,}\n"
                            f"  Nuevo saldo: ${data['saldo_nuevo']:,}"
                        )
                    return f"Error al depositar: {data.get('error', 'Error desconocido')}"
                except Exception as e:
                    return f"Error al procesar el deposito: {e}"
        return "No entendi. Por favor intenta de nuevo."

    # --- 2. Consulta normal ---
    plan = planificador.crear_plan(consulta)
    es_deposito = any("actualizar_saldo" in str(p.get("herramienta", "")) for p in plan["pasos"])

    if es_deposito:
        monto = _extraer_monto(consulta)
        cuenta = _extraer_cuenta(consulta)

        if monto is None:
            if session is not None:
                session["pending_action"] = {"type": "deposito", "monto": None, "tipo_cuenta": cuenta}
            msg = "¿Cuanto dinero quieres depositar?"
            if cuenta:
                msg += f" en tu {cuenta}."
            return msg

        if cuenta is None:
            if session is not None:
                session["pending_action"] = {"type": "deposito", "monto": monto, "tipo_cuenta": None}
            return (
                f"Seran ${monto:,}.\n"
                "¿A que cuenta quieres depositarlo?\n"
                "  - *CuentaRUT*\n"
                "  - *Cuenta de Ahorros*"
            )

        # Tiene monto y cuenta → ejecutar directo
        resultado = TOOL_MAP["actualizar_saldo"].func(tipo_cuenta=cuenta, monto=monto)
        try:
            data = json.loads(resultado)
            if data.get("success"):
                return (
                    f"✅ Deposito realizado con exito.\n"
                    f"  Cuenta: {cuenta}\n"
                    f"  Monto: ${monto:,}\n"
                    f"  Nuevo saldo: ${data['saldo_nuevo']:,}"
                )
            return f"Error al depositar: {data.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error al procesar el deposito: {e}"

    if not plan["pasos"]:
        return (
            "No tengo una herramienta especifica para esa consulta. "
            "Prueba preguntando por: saldo, estado de cuenta, tarjetas, creditos, "
            "ahorros, sucursales o productos bancarios."
        )

    resultados = orquestador.ejecutar_plan(consulta)
    respuesta = "Resultados:\n\n"
    for r in resultados:
        if r.get("exitoso") and "resultado" in r:
            try:
                data = json.loads(r["resultado"])
                if data.get("success"):
                    respuesta += f"  {r['herramienta']}: OK\n"
                    if "mensaje" in data:
                        respuesta += f"  {data['mensaje']}\n"
                    if "saldo" in data:
                        respuesta += f"  Saldo: ${data['saldo']:,}\n"
                else:
                    respuesta += f"  {r['herramienta']}: {data.get('error', 'Error')}\n"
            except (json.JSONDecodeError, KeyError):
                respuesta += f"  {r['herramienta']}: {str(r['resultado'])[:200]}\n"
        else:
            respuesta += f"  {r['herramienta']}: ERROR - {r.get('error', 'Error desconocido')}\n"

    if any("bloquear" in str(r) for r in resultados):
        respuesta += "\n[!] Se detecto urgencia (bloqueo de tarjeta). Accion priorizada.\n"
    if any("credito" in str(r) for r in resultados):
        respuesta += "\n[i] Se recomienda evaluar capacidad de pago antes de solicitar un credito.\n"

    return respuesta


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' https://lh3.googleusercontent.com data:; "
        "connect-src 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    limpiar_sesiones_antiguas()
    limpiar_auth_tokens_expirados()
    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "")
    token = data.get("token", "")
    rate_key = session_id or request.remote_addr or "anonymous"

    auth_user = auth_tokens.get(token)
    if not auth_user:
        return jsonify({"error": "No autorizado. Inicia sesion para continuar.", "codigo": "NO_AUTH"}), 401

    rut = auth_user["rut"]
    user_name = auth_user["name"]

    if not message:
        return jsonify({"error": "Mensaje vacio"}), 400

    validacion = seguridad.validar_entrada(message, rate_key)
    if not validacion["permitido"]:
        codigo = validacion.get("codigo", "DENEGADO")
        status = 429 if codigo == "RATE_LIMIT" else 403
        web_log.warning("SEGURIDAD %s: %s (key=%s)", codigo, validacion["error"], rate_key)
        return jsonify({"error": validacion["error"], "codigo": codigo}), status

    if not session_id or session_id not in sessions:
        session_id = create_session(rut)
    else:
        sessions[session_id]["rut"] = rut

    session = sessions[session_id]
    session["ultima_actividad"] = datetime.now().isoformat()

    # IL3.4: variables de tracking para detector de anomalias
    inicio_peticion = time.time()
    cache_hit_peticion = False
    exito_peticion = True

    from herramientas.herramientas_bancoestado import api as tools_api, set_rut_actual
    set_rut_actual(session.get("rut", "12.345.678-9"))

    mensaje_procesado = validacion["mensaje_sanitizado"]

    if MODO_DEMO:
        try:
            response = agente_obs_web.medir_demo(lambda c: procesar_demo(c, session), mensaje_procesado)
        except Exception as e:
            exito_peticion = False
            web_log.error("Demo exception: %s: %s", type(e).__name__, str(e)[:200])
            response = "Lo siento, ocurrio un error al procesar tu consulta en modo demo. Por favor intenta de nuevo."
    else:
        # IL3.2: buscar en cache semantico antes de llamar al LLM
        encontrado, respuesta_cache, similitud = cache_web.buscar(mensaje_procesado)
        if encontrado:
            cache_hit_peticion = True
            tokens_ahorrados = estimar_tokens(mensaje_procesado)
            cache_web.registrar_ahorro(tokens=tokens_ahorrados)
            agente_obs_web.metricas.registrar(0.0, tokens_ahorrados, 0, True, modelo="cache")
            registrar_metricas_langsmith(0.0, tokens_ahorrados, 0, True,
                                         modelo="cache", cache_hit=True)
            web_log.info("Cache HIT: similitud=%.4f | tokens_ahorrados=%d | consulta=%r",
                         similitud, tokens_ahorrados, mensaje_procesado[:80])
            response = respuesta_cache
        else:
            try:
                result = agente_obs_web.medir_llm(
                    session["executor"], {"input": mensaje_procesado}, modelo=MODELO_POR_DEFECTO
                )
                response = result["output"]
                # IL3.2: guardar en cache con estimacion real de tokens
                tokens_guardados = estimar_tokens(mensaje_procesado + response)
                cache_web.guardar(mensaje_procesado, response, tokens_usados=tokens_guardados)
            except Exception as e:
                exito_peticion = False
                error_str = str(e)
                web_log.error("Chat exception: %s: %s", type(e).__name__, error_str[:300])
                if "content_filter" in error_str or "ResponsibleAIPolicyViolation" in error_str:
                    response = "Lo siento, no puedo procesar esa solicitud. Por razones de seguridad y politicas de contenido, no puedo dar respuesta a este tipo de consultas. Si necesitas ayuda con productos o servicios de BancoEstado, estoy aqui para orientarte."
                elif "RateLimitError" in type(e).__name__:
                    response = "El servicio esta recibiendo demasiadas solicitudes en este momento. Por favor espera unos segundos y vuelve a intentarlo."
                elif "no encontrad" in error_str.lower() or "not found" in error_str.lower():
                    response = "Lo siento, no se encontro la cuenta o el cliente especificado. Verifica que tengas las cuentas necesarias para esta operacion."
                else:
                    response = "Lo siento, ocurrio un error al procesar tu consulta. Por favor intenta de nuevo."

    validacion_salida = seguridad.validar_salida(response)
    if validacion_salida["tiene_pii"]:
        web_log.warning("PII detectado en salida: %s", validacion_salida["pii_detectada"])
    similitud_info = validacion_salida.get("similitud")
    if similitud_info and similitud_info["baja_similitud"]:
        web_log.warning("Baja similitud coseno raw vs final: %.4f (metodo: %s)",
                        similitud_info["similitud_coseno"], similitud_info["metodo"])
    response = validacion_salida["corregida"]

    # IL3.4: alimentar detector de anomalias con datos de esta peticion
    duracion_peticion_ms = (time.time() - inicio_peticion) * 1000
    detector_anomalias.alimentar(
        latencia_ms=duracion_peticion_ms,
        exitoso=exito_peticion,
        cache_hit=cache_hit_peticion,
    )

    session["history"].append({"role": "user", "message": message, "timestamp": datetime.now().isoformat()})
    session["history"].append({"role": "assistant", "message": response, "timestamp": datetime.now().isoformat()})

    return jsonify({
        "response": response,
        "session_id": session_id,
    })


@app.route("/api/cuentas", methods=["GET"])
def api_cuentas():
    """Devuelve las cuentas del cliente con saldos (sin movimientos)."""
    rate_key = f"cuentas:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429

    token = request.args.get("token", "")
    auth_user = auth_tokens.get(token)
    if not auth_user:
        return jsonify({"error": "No autorizado. Inicia sesion para continuar."}), 401

    rut = auth_user["rut"]
    if not re.match(r'^\d{1,2}\.?\d{3}\.?\d{3}[-]?[\dkK]$', rut):
        return jsonify({"error": "RUT invalido en sesion"}), 400
    api = BancoEstadoAPI(rut=rut)
    try:
        cliente_data = api._get_cliente(rut)
        cuentas = cliente_data["cuentas"]
        return jsonify({
            "cuenta_rut": {
                "numero": cuentas["CuentaRUT"]["numero"],
                "saldo": cuentas["CuentaRUT"]["saldo"],
                "disponible": cuentas["CuentaRUT"]["disponible"],
                "bloqueada": cuentas["CuentaRUT"]["bloqueada"],
                "tipo": "CuentaRUT",
            },
            "cuenta_ahorros": {
                "numero": cuentas["CuentaAhorros"]["numero"],
                "saldo": cuentas["CuentaAhorros"]["saldo"],
                "disponible": cuentas["CuentaAhorros"]["disponible"],
                "bloqueada": cuentas["CuentaAhorros"]["bloqueada"],
                "tasa_interes": cuentas["CuentaAhorros"].get("tasa_interes", 0),
                "tipo": "Cuenta de Ahorros",
            },
        })
    except Exception as e:
        return jsonify({"error": "Error al obtener cuentas"}), 500


@app.route("/api/register", methods=["POST"])
def api_register():
    limpiar_failed_logins()
    limpiar_auth_tokens_expirados()
    rate_key = f"register:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        web_log.warning("SEGURIDAD RATE_LIMIT register: %s", rate_check["motivo"])
        return jsonify({"success": False, "error": rate_check["motivo"]}), 429

    data = request.get_json()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"success": False, "error": "Todos los campos son obligatorios"}), 400
    if "@" not in email or "." not in email:
        return jsonify({"success": False, "error": "Correo electronico invalido"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "La contrasena debe tener al menos 6 caracteres"}), 400

    if DetectorPII.tiene_pii(name):
        return jsonify({"success": False, "error": "El nombre contiene informacion personal no permitida"}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            return jsonify({"success": False, "error": "Este correo ya esta registrado"}), 409

        password_hash = generate_password_hash(password)
        conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                     (name, email, password_hash))
        conn.commit()

        user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
        import hashlib
        rut_seed = hashlib.sha256(f"{user_id}{uuid.uuid4().hex}{email}".encode()).hexdigest()[:8]
        rut_num = (int(rut_seed, 16) % 90_000_000) + 10_000_000
        digito = rut_num % 11
        digito_str = 'K' if digito == 10 else '0' if digito == 11 else str(digito)
        rut_formateado = f"{rut_num // 1_000_000}.{rut_num % 1_000_000 // 1_000:03d}.{rut_num % 1_000:03d}-{digito_str}"
        conn.execute("UPDATE users SET rut = ? WHERE id = ?", (rut_formateado, user_id))
        conn.commit()
        conn.close()

        from herramientas.herramientas_bancoestado import api as tools_api
        tools_api.crear_cuenta_para_nuevo_usuario(rut_formateado, name, email)

        token = str(uuid.uuid4())
        auth_tokens[token] = {"name": name, "email": email, "rut": rut_formateado, "created": datetime.now().isoformat()}

        _send_login_email(email, name, rut_formateado)
        return jsonify({"success": True, "user": {"name": name, "email": email, "rut": rut_formateado}, "token": token})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": "Error interno al registrar. Intenta nuevamente."}), 500


@app.route("/api/login", methods=["POST"])
def api_login():
    limpiar_failed_logins()
    limpiar_auth_tokens_expirados()
    rate_key = f"login:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        web_log.warning("SEGURIDAD RATE_LIMIT login: %s", rate_check["motivo"])
        return jsonify({"success": False, "error": rate_check["motivo"]}), 429

    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Correo y contrasena son obligatorios"}), 400

    ahora_login = time.time()
    intentos = [t for t in failed_logins.get(email, []) if ahora_login - t < LOCKOUT_MINUTOS * 60]
    if len(intentos) >= MAX_FAILED_LOGINS:
        mins_restantes = int(LOCKOUT_MINUTOS - (ahora_login - intentos[0]) / 60) + 1
        return jsonify({"success": False, "error": f"Cuenta bloqueada temporalmente. Intenta de nuevo en {mins_restantes} minuto(s)."}), 429

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT name, email, password_hash, rut FROM users WHERE email = ?",
                           (email,)).fetchone()
        conn.close()

        if not row or not check_password_hash(row[2], password):
            intentos.append(ahora_login)
            failed_logins[email] = intentos
            restantes = MAX_FAILED_LOGINS - len(intentos)
            if restantes > 0:
                return jsonify({"success": False, "error": f"Correo o contrasena incorrectos. {restantes} intento(s) restante(s)."}), 401
            else:
                return jsonify({"success": False, "error": "Cuenta bloqueada por demasiados intentos fallidos. Intenta en 15 minutos."}), 429

        failed_logins.pop(email, None)
        token = str(uuid.uuid4())
        auth_tokens[token] = {"name": row[0], "email": row[1], "rut": row[3], "created": datetime.now().isoformat()}

        _send_login_email(email, row[0], row[3])
        return jsonify({"success": True, "user": {"name": row[0], "email": row[1], "rut": row[3]}, "token": token})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": "Error interno al iniciar sesion. Intenta nuevamente."}), 500


@app.route("/health", methods=["GET"])
def health():
    rate_key = f"health:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429
    return jsonify({
        "status": "ok",
        "modo": "demo" if MODO_DEMO else "gpt-4o",
        "sesiones_activas": len(sessions),
    })


@app.route("/api/security/metrics", methods=["GET"])
def security_metrics():
    rate_key = f"secmetrics:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429
    return jsonify({
        "success": True,
        "metricas": seguridad.obtener_metricas(),
    })


@app.route("/api/observability/metrics", methods=["GET"])
def observability_metrics():
    """Endpoint IL3.1: metricas de observabilidad del agente."""
    rate_key = f"obsmetrics:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429
    return jsonify({
        "success": True,
        **agente_obs_web.reporte_dict(),
    })


# ══════════════════════════════════════════════════════════════════
# IL3.2: Endpoints de Escalabilidad (Cache + Lotes)
# ══════════════════════════════════════════════════════════════════

@app.route("/api/scalability/cache", methods=["GET"])
def scalability_cache():
    """Endpoint IL3.2: estadisticas del cache semantico."""
    rate_key = f"cachestats:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429
    return jsonify({
        "success": True,
        "cache": cache_web.obtener_estadisticas(),
    })


@app.route("/api/scalability/batch/status", methods=["GET"])
def scalability_batch_status():
    """Endpoint IL3.2: estado del procesador de lotes."""
    rate_key = f"batchstatus:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429
    return jsonify({
        "success": True,
        "batch": procesador_lotes.obtener_resumen(),
    })


@app.route("/api/scalability/batch/process", methods=["POST"])
def scalability_batch_process():
    """Endpoint IL3.2: procesar un lote de consultas con prioridad.

    Body JSON: {"consultas": [{"pregunta": "...", "prioridad": "ALTA"}, ...]}
    """
    rate_key = f"batchprocess:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429

    data = request.get_json()
    consultas = data.get("consultas", [])
    if not consultas:
        return jsonify({"error": "Lista de consultas vacia"}), 400

    prioridad_map = {
        "CRITICA": Prioridad.CRITICA,
        "ALTA": Prioridad.ALTA,
        "NORMAL": Prioridad.NORMAL,
        "BAJA": Prioridad.BAJA,
    }

    for c in consultas:
        pregunta = c.get("pregunta", "")
        prio_str = c.get("prioridad", "NORMAL").upper()
        prioridad = prioridad_map.get(prio_str, Prioridad.NORMAL)
        procesador_lotes.agregar(pregunta, prioridad)

    def procesar_una_consulta(pregunta: str) -> str:
        encontrado, resp_cache, _ = cache_web.buscar(pregunta)
        if encontrado:
            tokens_ahorrados = estimar_tokens(pregunta)
            cache_web.registrar_ahorro(tokens=tokens_ahorrados)
            agente_obs_web.metricas.registrar(0.0, tokens_ahorrados, 0, True, modelo="cache")
            return resp_cache
        return "[DEMO] Respuesta para: " + pregunta[:60]

    resultados_lista = procesador_lotes.procesar_todo(procesar_una_consulta)

    return jsonify({
        "success": True,
        "resultados": [
            {
                "id": r.id,
                "pregunta": r.pregunta[:80],
                "prioridad": r.prioridad.name,
                "estado": r.estado,
                "respuesta": r.respuesta[:120] if r.respuesta else None,
                "latencia_ms": round(r.latencia_ms, 2),
            }
            for r in resultados_lista
        ],
        "resumen": procesador_lotes.obtener_resumen(),
    })


# ══════════════════════════════════════════════════════════════════
# IL3.4: Dashboard, Datos e Informe Tecnico
# ══════════════════════════════════════════════════════════════════

@app.route("/dashboard")
def dashboard():
    """IE5: Dashboard visual del comportamiento del agente."""
    return render_template("dashboard.html")


@app.route("/api/dashboard/data", methods=["GET"])
def dashboard_data():
    """Endpoint IL3.4: datos consolidados para el dashboard."""
    rate_key = f"dashdata:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429

    detector_anomalias.analizar()
    return jsonify({
        "success": True,
        **reporte_sost.dashboard_data(),
    })


@app.route("/api/informe", methods=["GET"])
def informe_tecnico():
    """IE8/IE9: Informe tecnico HTML consolidado."""
    rate_key = f"informe:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        return jsonify({"error": rate_check["motivo"]}), 429

    detector_anomalias.analizar()
    return reporte_sost.generar_informe_html()


if __name__ == "__main__":
    init_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    web_log.info("Servidor iniciado en http://%s:%s", host, port)
    web_log.info("Modo: %s", "DEMO (sin GPT-4o)" if MODO_DEMO else "GPT-4o")
    web_log.info("Debug: %s", "ON" if debug_mode else "OFF")
    if not debug_mode:
        web_log.info("ADVERTENCIA: Servidor de desarrollo. Para produccion usar gunicorn.")
    app.run(host=host, port=port, debug=debug_mode)
