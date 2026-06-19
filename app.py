import os
import json
import uuid
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

MODO_DEMO = not bool(os.environ.get("GITHUB_TOKEN"))

if not MODO_DEMO:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
else:
    llm = None
    print("[!] Sin GITHUB_TOKEN - modo demo (respuestas simuladas)")

from herramientas.herramientas_bancoestado import TOOL_LIST
from herramientas.planificador import Planificador, Orquestador
from herramientas.seguridad import OrquestadorSeguridad, DetectorPII

TOOL_MAP = {tool.name: tool for tool in TOOL_LIST}
planificador = Planificador()
orquestador = Orquestador(TOOL_MAP)
seguridad = OrquestadorSeguridad()

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

# ─── Base de datos de usuarios ────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "usuarios.db")


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
    print(f"[DB] Base de datos lista en {DB_PATH}")


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
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family:Arial,sans-serif;color:#333;margin:0;padding:0;background:#f5f5f5;">
            <div style="max-width:520px;margin:30px auto;">
                <div style="background:#0066cc;color:white;padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h2 style="margin:0;font-size:22px;">Bienvenido, {name}!</h2>
                    <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">Has iniciado sesion en BancoEstado</p>
                </div>
                <div style="background:white;padding:24px;border-radius:0 0 12px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <p style="font-size:16px;margin:0 0 16px;">Resumen de tus cuentas:</p>
                    <div style="background:#f8f9fb;border-radius:8px;padding:16px;margin-bottom:16px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                            <span>CuentaRUT</span>
                            <span style="font-weight:bold;">${cr['saldo']:,}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                            <span>Cuenta de Ahorros</span>
                            <span style="font-weight:bold;">${ca['saldo']:,}</span>
                        </div>
                        <div style="border-top:1px solid #ddd;padding-top:12px;display:flex;justify-content:space-between;">
                            <span style="font-weight:bold;">Total en cuentas</span>
                            <span style="font-weight:bold;color:#0066cc;">${total:,}</span>
                        </div>
                    </div>
                    <p style="font-size:12px;color:#999;margin:0;text-align:center;">
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
        print(f"[EMAIL] {resultado}")
    except Exception as e:
        print(f"[EMAIL] Error enviando email de bienvenida a {email}: {e}")

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
        executor = AgentExecutor(
            agent=agent,
            tools=TOOL_LIST,
            memory=memory,
            verbose=False,
            max_iterations=5,
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    limpiar_sesiones_antiguas()
    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "")
    rut = data.get("rut") or "12.345.678-9"
    rate_key = session_id or request.remote_addr or "anonymous"

    if not message:
        return jsonify({"error": "Mensaje vacio"}), 400

    validacion = seguridad.validar_entrada(message, rate_key)
    if not validacion["permitido"]:
        codigo = validacion.get("codigo", "DENEGADO")
        status = 429 if codigo == "RATE_LIMIT" else 403
        print(f"[SEGURIDAD] {codigo}: {validacion['error']} (key={rate_key})")
        return jsonify({"error": validacion["error"], "codigo": codigo}), status

    if not session_id or session_id not in sessions:
        session_id = create_session(rut)
    else:
        sessions[session_id]["rut"] = rut

    session = sessions[session_id]
    session["ultima_actividad"] = datetime.now().isoformat()

    from herramientas.herramientas_bancoestado import api as tools_api
    tools_api.rut = session.get("rut", "12.345.678-9")

    mensaje_procesado = validacion["mensaje_sanitizado"]

    if MODO_DEMO:
        response = procesar_demo(mensaje_procesado, session)
    else:
        try:
            result = session["executor"].invoke({"input": mensaje_procesado})
            response = result["output"]
        except Exception as e:
            error_str = str(e)
            if "content_filter" in error_str or "ResponsibleAIPolicyViolation" in error_str:
                response = "Lo siento, no puedo procesar esa solicitud. Por razones de seguridad y políticas de contenido, no puedo dar respuesta a este tipo de consultas. Si necesitas ayuda con productos o servicios de BancoEstado, estoy aqui para orientarte."
            else:
                response = f"Lo siento, ocurrio un error al procesar tu consulta. Por favor intenta de nuevo o reformula tu pregunta."

    validacion_salida = seguridad.validar_salida(response)
    if validacion_salida["tiene_pii"]:
        print(f"[SEGURIDAD] PII detectado en salida: {validacion_salida['pii_detectada']}")
    response = validacion_salida["corregida"]

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

    from herramientas.bancoestado_api import BancoEstadoAPI
    rut = request.args.get("rut", "12.345.678-9")
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
        return jsonify({"error": str(e)}), 500


@app.route("/api/register", methods=["POST"])
def api_register():
    rate_key = f"register:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        print(f"[SEGURIDAD] RATE_LIMIT register: {rate_check['motivo']}")
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
        rut = f"99.888.{user_id:03d}-{user_id % 9}"
        conn.execute("UPDATE users SET rut = ? WHERE id = ?", (rut, user_id))
        conn.commit()
        conn.close()

        from herramientas.herramientas_bancoestado import api as tools_api
        tools_api.crear_cuenta_para_nuevo_usuario(rut, name, email)

        _send_login_email(email, name, rut)
        return jsonify({"success": True, "user": {"name": name, "email": email, "rut": rut}})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def api_login():
    rate_key = f"login:{request.remote_addr or 'unknown'}"
    rate_check = seguridad.rate_limiter.permitir(rate_key)
    if not rate_check["permitido"]:
        print(f"[SEGURIDAD] RATE_LIMIT login: {rate_check['motivo']}")
        return jsonify({"success": False, "error": rate_check["motivo"]}), 429

    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Correo y contrasena son obligatorios"}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT name, email, password_hash, rut FROM users WHERE email = ?",
                           (email,)).fetchone()
        conn.close()

        if not row or not check_password_hash(row[2], password):
            return jsonify({"success": False, "error": "Correo o contrasena incorrectos"}), 401

        _send_login_email(email, row[0], row[3])
        return jsonify({"success": True, "user": {"name": row[0], "email": row[1], "rut": row[3]}})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "modo": "demo" if MODO_DEMO else "gpt-4o",
        "sesiones_activas": len(sessions),
    })


@app.route("/api/security/metrics", methods=["GET"])
def security_metrics():
    return jsonify({
        "success": True,
        "metricas": seguridad.obtener_metricas(),
    })


if __name__ == "__main__":
    init_db()
    print(f"[OK] Servidor iniciado en http://localhost:5000")
    print(f"[OK] Modo: {'DEMO (sin GPT-4o)' if MODO_DEMO else 'GPT-4o'}")
    app.run(port=5000, debug=True)
