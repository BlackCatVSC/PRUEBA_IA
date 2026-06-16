"""
Agente BancoEstado - Script Principal
=======================================
Integra:
  - Herramientas LangChain (IL2.1)
  - Memoria conversacional (IL2.2)
  - Planificacion y toma de decisiones (IL2.3)
  - API ficticia de BancoEstado como backend

Ejecutar: python agente_bancoestado.py
"""

import os
import json
import unicodedata
import re
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Mapear variables para LangChain
os.environ["OPENAI_API_BASE"] = os.environ.get("GITHUB_BASE_URL", "https://models.inference.ai.azure.com")
os.environ["OPENAI_API_KEY"] = os.environ.get("GITHUB_TOKEN", "")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Check config
if not os.environ.get("GITHUB_TOKEN"):
    print("[!] GITHUB_TOKEN no configurado. Revisa tu archivo .env")
    print("[!] El agente usara modo demostracion con datos simulados (sin LLM).")
    MODO_DEMO = True
else:
    MODO_DEMO = False

# =============================================
# 1. CONFIGURACION DEL LLM (IL2.1)
# =============================================

from langchain_openai import ChatOpenAI

if not MODO_DEMO:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    try:
        test = llm.invoke("Hola")
        print("[OK] LLM configurado con GPT-4o")
    except Exception as e:
        print(f"[!] Error LLM: {e}. Usando modo demo.")
        llm = None
        MODO_DEMO = True
else:
    llm = None

# =============================================
# 2. CARGA DE HERRAMIENTAS (IL2.1)
# =============================================

from herramientas_bancoestado import TOOL_LIST

# Mapa nombre -> funcion para busqueda rapida
TOOL_MAP = {tool.name: tool for tool in TOOL_LIST}
print(f"[OK] {len(TOOL_LIST)} herramientas BancoEstado cargadas")

# =============================================
# 3. PLANIFICADOR Y ORQUESTADOR (IL2.3)
# =============================================

from planificador import Planificador, Orquestador

planificador = Planificador()
orquestador = Orquestador(TOOL_MAP)

# =============================================
# 4. MEMORIA CONVERSACIONAL (IL2.2)
# =============================================

from langchain_classic.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
)
from langchain_classic.agents import tool, create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# Memoria Buffer (conversacion completa)
buffer_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
)

# Memoria Window (ultimas k interacciones)
window_memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    k=4,
    return_messages=True,
)

# Memoria Summary (resumen automatico) - solo si hay LLM
summary_memory = None

# =============================================
# 5. SISTEMA DE AGENTES LANGSCHAIN (IL2.1)
# =============================================

prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Eres un asistente virtual de BancoEstado. Tu funcion es orientar a los clientes "
        "con dudas sobre productos, cuentas, tarjetas, creditos y operaciones bancarias. "
        "Usa las herramientas disponibles para consultar informacion y ejecutar operaciones. "
        "Responde siempre en espanol de forma clara, amable y profesional. "
        "Si el cliente reporta perdida o robo de tarjeta, prioriza el bloqueo inmediato. "
        "Para creditos sobre $3.000.000, indica que se requiere verificacion adicional. "
        "Para creditos sobre $5.000.000, indica que debe ir a sucursal. "
        "Usa el historial de chat si esta disponible para mantener contexto."
    )),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

if not MODO_DEMO:
    agent = create_openai_tools_agent(llm, TOOL_LIST, prompt)

    summary_memory = ConversationSummaryMemory(
        llm=llm,
        memory_key="chat_history",
        return_messages=True,
    )

    # Ejecutores con diferentes estrategias de memoria
    executor_buffer = AgentExecutor(
        agent=agent,
        tools=TOOL_LIST,
        memory=buffer_memory,
        verbose=False,
        max_iterations=5,
    )

    executor_window = AgentExecutor(
        agent=agent,
        tools=TOOL_LIST,
        memory=window_memory,
        verbose=False,
        max_iterations=5,
    )

    executor_summary = AgentExecutor(
        agent=agent,
        tools=TOOL_LIST,
        memory=summary_memory,
        verbose=False,
        max_iterations=5,
    )

# =============================================
# 6. SESSION TRACKING
# =============================================

sesion = []
beneficio_obtenido = None


def registrar_accion(consulta: str, herramienta: str, exitoso: bool, resultado: str):
    sesion.append({
        "consulta": consulta,
        "herramienta": herramienta,
        "exitoso": exitoso,
        "resultado": resultado,
        "timestamp": datetime.now().isoformat(),
    })


def enviar_reporte_sesion():
    """Genera y envia el reporte HTML de toda la sesion."""
    from email_sender import generar_reporte_html, enviar_reporte

    if not sesion:
        print("[!] No hay acciones registradas para reportar.")
        return

    global beneficio_obtenido
    html = generar_reporte_html(sesion, beneficio=beneficio_obtenido)
    resultado = enviar_reporte(
        asunto=f"Reporte Sesion BancoEstado - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        cuerpo_html=html,
    )
    print(f"\n{resultado}")


# =============================================
# 6b. BENEFICIOS / TARJETAS
# =============================================

TARJETAS_BENEFICIOS = [
    {
        "nombre": "Bronze",
        "monto_requerido": 5_000_000,
        "credito_maximo": 500_000,
        "descuento": "5%",
        "color": "bronce",
    },
    {
        "nombre": "Plata",
        "monto_requerido": 10_000_000,
        "credito_maximo": 1_000_000,
        "descuento": "10%",
        "color": "plateado",
    },
    {
        "nombre": "AURUM",
        "monto_requerido": 20_000_000,
        "credito_maximo": 3_000_000,
        "descuento": "15%",
        "color": "dorado",
    },
    {
        "nombre": "Platino",
        "monto_requerido": 100_000_000,
        "credito_maximo": 10_000_000,
        "descuento": "25%",
        "color": "platino",
    },
]


def mostrar_beneficios(saldo: float = None):
    """Muestra las tarjetas disponibles y cuales califica segun saldo."""
    print("\n" + "=" * 60)
    print("  TARJETAS DE BENEFICIOS BANCOESTADO")
    print("=" * 60)
    print(f"\n  {'Tarjeta':<10} {'Req. minimo':<15} {'Credito max.':<15} {'Dto.':<8} {'Estado':<10}")
    print(f"  {'-'*10} {'-'*15} {'-'*15} {'-'*8} {'-'*10}")

    disponibles = []
    for t in TARJETAS_BENEFICIOS:
        if saldo is not None and saldo >= t["monto_requerido"]:
            estado = "DISPONIBLE"
            disponibles.append(t)
        elif saldo is not None:
            falta = t["monto_requerido"] - saldo
            estado = f"Faltan ${falta:,.0f}"
        else:
            estado = "---"

        print(f"  {t['nombre']:<10} ${t['monto_requerido']:<12,} ${t['credito_maximo']:<12,} {t['descuento']:<8} {estado:<10}")

    print()

    if disponibles:
        print(f"  Felicidades! Calificas para las tarjetas mostradas como DISPONIBLE.")
        print()
        resp = input("  Deseas obtener alguna de estas tarjetas? [Bronze/Plata/AURUM/Platino/n]: ").strip().lower()
        for t in disponibles:
            if t["nombre"].lower() == resp:
                global beneficio_obtenido
                beneficio_obtenido = t
                print(f"\n  [OK] Has obtenido la tarjeta {t['nombre']}!")
                print(f"       Credito maximo: ${t['credito_maximo']:,}")
                print(f"       Descuento: {t['descuento']}")
                registrar_accion(f"OBTENER {t['nombre']}", "beneficio", True,
                    f"Tarjeta {t['nombre']}: ${t['credito_maximo']:,} credito + {t['descuento']} desc.")
                return
        print("  No seleccionaste ninguna tarjeta.")
    elif saldo is not None:
        print(f"  Con tu saldo actual no calificas para ninguna tarjeta aun.")
    else:
        print("  Usa /verificar para revisar con tu saldo real de CuentaRUT/CuentaAhorros.")
    print("=" * 60)


def verificar_beneficios():
    """Verifica los beneficios con el saldo real de la API y pregunta si desea obtener una."""
    try:
        from herramientas_bancoestado import api
        data_ahorros = json.loads(api.consultar_saldo("12.345.678-9", "CuentaAhorros"))
        data_rut = json.loads(api.consultar_saldo("12.345.678-9", "CuentaRUT"))

        saldo_ahorros = data_ahorros.get("saldo", 0) if data_ahorros.get("success") else 0
        saldo_rut = data_rut.get("saldo", 0) if data_rut.get("success") else 0
        saldo_total = saldo_ahorros + saldo_rut

        print(f"\n  Saldo CuentaRUT: ${saldo_rut:,}")
        print(f"  Saldo Ahorros: ${saldo_ahorros:,}")
        print(f"  Saldo total: ${saldo_total:,}")
        mostrar_beneficios(saldo_total)
    except Exception as e:
        print(f"[!] Error consultando saldo: {e}")
        mostrar_beneficios()


# =============================================
# 7a. FLUJO INTERACTIVO ACTUALIZAR SALDO
# =============================================

def flujo_actualizar_saldo_interactivo() -> bool:
    """Flujo interactivo para que el usuario actualice su saldo paso a paso."""
    from herramientas_bancoestado import api

    print("\n" + "=" * 50)
    print("  ACTUALIZAR SALDO")
    print("=" * 50)

    # Paso 1: elegir cuenta
    print("\n  Selecciona la cuenta:")
    print("  1) CuentaRUT")
    print("  2) Cuenta de Ahorros")
    opcion = input("  Opcion [1/2]: ").strip()
    tipo_cuenta = "CuentaAhorros" if opcion == "2" else "CuentaRUT"
    print(f"  Cuenta seleccionada: {tipo_cuenta}")

    # Paso 2: monto
    try:
        monto_str = input("  Monto a ingresar: $").strip().replace(".", "").replace(",", "")
        monto = float(monto_str)
        if monto <= 0:
            print("[!] El monto debe ser positivo.")
            return False
    except ValueError:
        print("[!] Monto invalido.")
        return False

    # Paso 3: confirmar
    print(f"\n  Resumen:")
    print(f"    Cuenta: {tipo_cuenta}")
    print(f"    Monto:  ${monto:,.0f}")
    confirmar = input("  Confirmar actualizacion? [s/n]: ").strip().lower()
    if confirmar != "s":
        print("  Operacion cancelada.")
        return False

    # Paso 4: ejecutar
    try:
        res = json.loads(api.actualizar_saldo("12.345.678-9", tipo_cuenta, monto))
        if res.get("success"):
            print(f"\n[OK] {res['mensaje']}")
            registrar_accion(f"ACTUALIZAR {tipo_cuenta} ${monto:,.0f}", "actualizar_saldo", True, res["mensaje"])
            print("  Usa /verificar para revisar tus beneficios ahora.")
        else:
            print(f"\n[!] {res.get('error', 'Error desconocido')}")
            registrar_accion(f"ACTUALIZAR {tipo_cuenta} ${monto:,.0f}", "actualizar_saldo", False, res.get("error", ""))
        return res.get("success", False)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        return False


# =============================================
# 7. PROCESAMIENTO DE CONSULTAS
# =============================================

def procesar_consulta_modo_demo(consulta: str) -> str:
    """Procesa consultas en modo demo (sin LLM) usando planificador."""
    plan = planificador.crear_plan(consulta)
    print(planificador.obtener_resumen_plan(plan))
    print()

    if not plan["pasos"]:
        palabras_deposito = ["ingresar", "ingrese", "deposite", "depositar", "monto", "agregar saldo", "poner plata", "agregar dinero"]
        if any(p in consulta.lower() for p in palabras_deposito):
            msg = ("Para ingresar o depositar dinero usa el comando /actualizar_saldo.\n"
                   "Ejemplo: /actualizar_saldo CuentaRUT 5000000\n"
                   "O simplemente dime 'quiero depositar' y te guiare paso a paso.")
        else:
            msg = ("No tengo una herramienta especifica para esa consulta. "
                   "Prueba preguntando por: saldo, estado de cuenta, tarjetas, creditos, "
                   "ahorros, sucursales o productos bancarios. "
                   "Tambien puedes usar /beneficios para ver las tarjetas disponibles.")
        registrar_accion(consulta, "ninguna", False, msg)
        return msg

    resultados = orquestador.ejecutar_plan(consulta)
    respuesta = "Resultados de la operacion:\n\n"
    for r in resultados:
        if r.get("exitoso", False) and "resultado" in r:
            try:
                data = json.loads(r["resultado"])
                if data.get("success"):
                    respuesta += f"- {r['herramienta']}: OK\n"
                    registrar_accion(consulta, r["herramienta"], True, r["resultado"][:200])
                else:
                    respuesta += f"- {r['herramienta']}: {data.get('error', 'Error desconocido')}\n"
                    registrar_accion(consulta, r["herramienta"], False, data.get("error", "Error"))
            except (json.JSONDecodeError, KeyError):
                respuesta += f"- {r['herramienta']}: {str(r['resultado'])[:100]}...\n"
                registrar_accion(consulta, r["herramienta"], True, str(r["resultado"])[:200])
        else:
            respuesta += f"- {r['herramienta']}: ERROR - {r.get('error', 'Error desconocido')}\n"
            registrar_accion(consulta, r["herramienta"], False, r.get("error", "Error desconocido"))

    if any("bloquear" in str(r) for r in resultados):
        respuesta += "\n[PLANIFICACION] Se detecto urgencia (bloqueo de tarjeta). Accion priorizada.\n"

    if any("credito" in str(r) for r in resultados):
        respuesta += "\n[PLANIFICACION] Se recomienda evaluar capacidad de pago antes de solicitar un credito.\n"

    return respuesta


def procesar_consulta_llm(consulta: str, memoria_tipo: str = "buffer") -> str:
    """Procesa consultas usando el LLM con el tipo de memoria especificado."""
    plan = planificador.crear_plan(consulta)
    if plan.get("es_urgente", False):
        print(planificador.obtener_resumen_plan(plan))
    else:
        # Solo sugerir beneficios si NO hay urgencia (bloqueo/robo)
        palabras_beneficios = ["beneficio", "beneficios"]
        if any(p in consulta.lower() for p in palabras_beneficios):
            return ("Para ver los beneficios disponibles usa el comando /beneficios.\n"
                    "Con /verificar puedo revisar tu saldo y decirte cual tarjeta te corresponde.")

    executors = {
        "buffer": executor_buffer,
        "window": executor_window,
        "summary": executor_summary,
    }
    executor = executors.get(memoria_tipo, executor_buffer)

    try:
        response = executor.invoke({"input": consulta})
        texto = response["output"]
        registrar_accion(consulta, "llm", True, texto[:200])
        return texto
    except Exception as e:
        registrar_accion(consulta, "llm", False, str(e))
        return f"Error procesando consulta: {e}"


# =============================================
# 8. CONSOLA INTERACTIVA
# =============================================

print("\n" + "=" * 60)
print("  BANCOESTADO - Asistente Virtual")
print("  " + ("Modo DEMO (sin LLM)" if MODO_DEMO else "Modo COMPLETO (con GPT-4o)"))
print("=" * 60)
print("  Comandos especiales:")
print("  /memoria buffer|window|summary - Cambiar tipo de memoria")
print("  /plan <consulta> - Ver plan antes de ejecutar")
print("  /beneficios - Ver tarjetas de beneficios disponibles")
print("  /verificar - Verifica que tarjeta calificas con tu saldo real")
print("  /actualizar_saldo <tipo> <monto> - Actualiza saldo (ej: /actualizar_saldo CuentaRUT 150000000)")
print("  /decisiones - Ver ejemplos de toma de decisiones")
print("  /reporte - Enviar reporte manualmente")
print("  /finalizar - Terminar y enviar reporte")
print("=" * 60)

memoria_actual = "buffer"


def mostrar_pregunta_final():
    """Pregunta si continuar o finalizar."""
    try:
        print()
        resp = input("  Deseas continuar o finalizar? [c/f]: ").strip().lower()
        return resp != "f"
    except (EOFError, KeyboardInterrupt):
        return False


def loop_principal():
    global memoria_actual
    activo = True
    while activo:
        try:
            consulta = input(f"\nTu consulta [{memoria_actual}]: " if not MODO_DEMO else "\nTu consulta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n[!] Interrupcion detectada.")
            break

        if not consulta:
            continue
        if consulta.lower() in ("/salir", "/finalizar"):
            break
        if consulta.startswith("/memoria "):
            tipo = consulta[9:].strip()
            if tipo in ("buffer", "window", "summary"):
                memoria_actual = tipo
                print(f"[OK] Memoria cambiada a: {tipo}")
            else:
                print("[!] Tipos: buffer, window, summary")
            continue
        if consulta.startswith("/plan "):
            plan = planificador.crear_plan(consulta[6:])
            print(planificador.obtener_resumen_plan(plan))
            continue
        if consulta == "/beneficios":
            mostrar_beneficios()
            continue
        if consulta == "/verificar":
            verificar_beneficios()
            continue
        if consulta.startswith("/actualizar_saldo"):
            partes = consulta.split()
            if len(partes) >= 3:
                tipo = partes[1]
                try:
                    monto = float(partes[2].replace(".", "").replace(",", ""))
                    from herramientas_bancoestado import api
                    res = json.loads(api.actualizar_saldo("12.345.678-9", tipo, monto))
                    if res.get("success"):
                        print(f"\n[OK] {res['mensaje']}")
                        print("  Usa /verificar para ver si ahora calificas para alguna tarjeta.")
                        registrar_accion(f"ACTUALIZAR {tipo} ${monto:,.0f}", "actualizar_saldo", True, res["mensaje"])
                    else:
                        print(f"\n[!] {res.get('error', 'Error desconocido')}")
                        registrar_accion(f"ACTUALIZAR {tipo} ${monto:,.0f}", "actualizar_saldo", False, res.get("error", ""))
                except ValueError:
                    print("\n[!] Monto invalido. Usa: /actualizar_saldo <CuentaRUT|CuentaAhorros> <monto>")
            else:
                print("\n[!] Usa: /actualizar_saldo <CuentaRUT|CuentaAhorros> <monto>")
                print("  Ejemplo: /actualizar_saldo CuentaRUT 150000000")
            continue
        if consulta == "/decisiones":
            print("\n=== EJEMPLOS DE TOMA DE DECISIONES (IE6) ===\n")
            for caso, monto, saldo in [
                ("Transferencia $25.000 (saldo: $120.000)", 25000, 120000),
                ("Transferencia $85.000 (saldo: $120.000)", 85000, 120000),
                ("Transferencia $150.000 (saldo: $120.000)", 150000, 120000),
            ]:
                d = planificador.evaluar_riesgo_transferencia(monto, saldo)
                print(f"  {caso} -> {d['decision'].upper()}: {d['motivo']}")
            print()
            for caso, monto in [
                ("Credito $500.000", 500000),
                ("Credito $3.000.000", 3000000),
                ("Credito $8.000.000", 8000000),
            ]:
                d = planificador.evaluar_credito(monto)
                print(f"  {caso} -> {d['decision'].upper()}: {d['motivo']}")
            print()
            continue
        if consulta == "/reporte":
            enviar_reporte_sesion()
            continue

        # Detectar si el usuario quiere actualizar saldo -> flujo interactivo
        plan_preview = planificador.crear_plan(consulta)
        if "actualizar_saldo" in plan_preview.get("intenciones_detectadas", []):
            print("\n--- Detecte que necesitas actualizar tu saldo ---")
            flujo_actualizar_saldo_interactivo()
            activo = mostrar_pregunta_final()
            continue

        # Sugerir beneficios solo si NO es contexto de bloqueo/robo
        palabras_bloqueo = ["perdi", "perdio", "robo", "robaron", "extravio", "bloquear", "bloqueo"]
        consulta_norm = unicodedata.normalize('NFKD', consulta.lower()).encode('ascii', 'ignore').decode('ascii')
        es_bloqueo = any(p in consulta_norm for p in palabras_bloqueo)
        if not es_bloqueo and any(p in consulta_norm for p in ["beneficio", "beneficios", "tarjeta", "tarjetas"]) \
                and "/beneficios" not in consulta and "/verificar" not in consulta:
            print("\n--- Sugerencia ---")
            print("  Usa /beneficios para ver todas las tarjetas disponibles")
            print("  o /verificar para revisar cual calificas con tu saldo real.")
            print("------------------\n")

        print("\n--- Procesando consulta ---")
        if MODO_DEMO:
            respuesta = procesar_consulta_modo_demo(consulta)
        else:
            respuesta = procesar_consulta_llm(consulta, memoria_actual)
        print(f"\nRespuesta: {respuesta}")

        activo = mostrar_pregunta_final()

    # Finalizar sesion
    print("\n[!] Finalizando sesion...")
    if sesion:
        print(f"  Acciones registradas: {len(sesion)}")
        enviar_reporte_sesion()
    else:
        print("  No hubo acciones que reportar.")
    print("[!] Gracias por usar BancoEstado Asistente Virtual.")


loop_principal()
