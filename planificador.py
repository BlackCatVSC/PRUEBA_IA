"""
Planificador y Orquestador (IL2.3)
===================================
Implementa estrategias de planificación y toma de decisiones:
- Descomposición jerárquica de tareas
- Planificación condicional según contexto
- Ejecución multi-paso con dependencias
- Decisión adaptativa según estado del sistema
"""

import json
import inspect
import unicodedata
import re
from datetime import datetime
from typing import Callable

# ========================
# CLASIFICADOR DE INTENCIONES
# ========================

INTENCIONES = {
    "consulta_saldo": {
        "palabras": ["saldo", "cuánto tengo", "dinero disponible", "mi plata", "cuenta rut", "cuenta de ahorros"],
        "herramientas_requeridas": ["consultar_saldo"],
        "criticidad": "baja",
        "prioridad": 3,
    },
    "estado_cuenta": {
        "palabras": ["estado de cuenta", "movimientos", "mis gastos", "ingresos", "egresos", "cartola"],
        "herramientas_requeridas": ["consultar_estado_cuenta"],
        "criticidad": "baja",
        "prioridad": 3,
    },
    "crear_cuenta": {
        "palabras": ["crear cuenta", "crea una cuenta", "crea cuenta", "abrir cuenta", "abrir una cuenta", "abre una cuenta", "nueva cuenta", "quiero una cuenta", "quisiera una cuenta", "necesito una cuenta", "quiero abrir", "quiero crear"],
        "herramientas_requeridas": ["crear_cuenta_rut", "crear_cuenta_ahorros"],
        "criticidad": "media",
        "prioridad": 4,
    },
    "bloquear_tarjeta": {
        "palabras": ["bloquear tarjeta", "bloquea", "bloquearla", "perdi", "perdio", "perdida", "perdido", "robo", "me robaron", "extravio", "tarjeta bloqueada", "robaron", "robo de tarjeta", "hurto", "susto"],
        "herramientas_requeridas": ["bloquear_tarjeta"],
        "criticidad": "alta",
        "prioridad": 1,
    },
    "desbloquear_tarjeta": {
        "palabras": ["desbloquear tarjeta", "reactivar tarjeta", "destrabar tarjeta"],
        "herramientas_requeridas": ["desbloquear_tarjeta"],
        "criticidad": "media",
        "prioridad": 3,
    },
    "simular_credito": {
        "palabras": ["simular credito", "simula", "simulacion", "cuanto me prestan", "quiero un credito", "necesito un prestamo", "credito de"],
        "herramientas_requeridas": ["simular_credito"],
        "criticidad": "media",
        "prioridad": 4,
    },
    "solicitar_credito": {
        "palabras": ["solicitar credito", "pedir prestado", "solicitar prestamo", "necesito plata", "necesito dinero", "necesito un prestamo", "necesito un credito"],
        "herramientas_requeridas": ["simular_credito", "solicitar_credito"],
        "criticidad": "alta",
        "prioridad": 2,
    },
    "consultar_creditos": {
        "palabras": ["mis creditos", "mis deudas", "cuanto debo", "estado de mis creditos"],
        "herramientas_requeridas": ["consultar_creditos"],
        "criticidad": "baja",
        "prioridad": 3,
    },
    "transferir": {
        "palabras": ["transferir", "transferencia", "enviar dinero", "giro", "mandar plata"],
        "herramientas_requeridas": ["transferir"],
        "criticidad": "alta",
        "prioridad": 2,
    },
    "simular_ahorro": {
        "palabras": ["simular ahorro", "ahorro programado", "cuánto puedo ahorrar", "meta de ahorro"],
        "herramientas_requeridas": ["simular_ahorro"],
        "criticidad": "baja",
        "prioridad": 5,
    },
    "info_productos": {
        "palabras": ["productos", "qué ofrece", "servicios", "tipos de cuenta", "quiero saber"],
        "herramientas_requeridas": ["consultar_productos"],
        "criticidad": "baja",
        "prioridad": 5,
    },
    "sucursales": {
        "palabras": ["sucursal", "oficina", "dónde queda", "dirección", "horario"],
        "herramientas_requeridas": ["listar_sucursales"],
        "criticidad": "baja",
        "prioridad": 5,
    },
    "actualizar_saldo": {
        "palabras": ["loteria", "gane", "gané", "herencia", "deposito", "depósito", "depositar", "actualizar", "me depositaron", "recibi plata", "recibí plata", "ingresar dinero", "nuevo saldo", "cambiar saldo", "deposite", "ingrese"],
        "herramientas_requeridas": ["actualizar_saldo"],
        "criticidad": "media",
        "prioridad": 3,
    },
    "info_general": {
        "palabras": ["qué es", "quién fue", "historia", "explica", "define", "wikipedia"],
        "herramientas_requeridas": ["buscar_wikipedia"],
        "criticidad": "baja",
        "prioridad": 5,
    },
}


class Planificador:
    """
    Planificador jerárquico (IL2.3).
    Descompone una consulta en pasos ordenados por criticidad y dependencias.
    """

    def __init__(self):
        self.historial_acciones = []

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        """Elimina acentos/tildes y pasa a minúsculas para matching."""
        texto = texto.lower()
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        return texto

    def clasificar(self, consulta: str) -> list:
        """Clasifica una consulta en intenciones detectadas, ordenadas por criticidad."""
        consulta_norm = self._normalizar_texto(consulta)
        detectadas = []

        for intencion, config in INTENCIONES.items():
            for palabra in config["palabras"]:
                palabra_norm = self._normalizar_texto(palabra)
                if palabra_norm in consulta_norm:
                    detectadas.append({
                        "intencion": intencion,
                        "criticidad": config["criticidad"],
                        "prioridad": config["prioridad"],
                        "herramientas": config["herramientas_requeridas"],
                    })
                    break

        # Ordenar por criticidad (alta > media > baja) y luego por prioridad
        orden_criticidad = {"alta": 0, "media": 1, "baja": 2}
        detectadas.sort(key=lambda x: (orden_criticidad.get(x["criticidad"], 9), x["prioridad"]))

        return detectadas

    def crear_plan(self, consulta: str) -> dict:
        """
        Crea un plan de ejecución multi-paso.
        Retorna una estructura con pasos ordenados, dependencias y validaciones.
        """
        intenciones = self.clasificar(consulta)

        if not intenciones:
            return {
                "consulta": consulta,
                "pasos": [],
                "mensaje": "No se detectaron intenciones bancarias claras.",
                "tipo_plan": "consulta_general",
            }

        pasos = []
        herramientas_usadas = set()
        es_urgente = any(i["criticidad"] == "alta" for i in intenciones)

        consulta_norm = self._normalizar_texto(consulta) if intenciones else ""

        for idx, intento in enumerate(intenciones):
            herramientas = intento["herramientas"]
            # Para "crear_cuenta", elegir segun contexto en vez de ejecutar ambas
            if intento["intencion"] == "crear_cuenta":
                if "ahorro" in consulta_norm:
                    herramientas = [h for h in herramientas if "ahorro" in h]
                else:
                    herramientas = [h for h in herramientas if "ahorro" not in h]
            for herramienta in herramientas:
                if herramienta not in herramientas_usadas:
                    pasos.append({
                        "orden": len(pasos) + 1,
                        "accion": f"Ejecutar {herramienta}",
                        "herramienta": herramienta,
                        "criticidad": intento["criticidad"],
                        "dependencias": list(herramientas_usadas) if intento["criticidad"] == "baja" else [],
                    })
                    herramientas_usadas.add(herramienta)

        return {
            "consulta": consulta,
            "pasos": pasos,
            "total_pasos": len(pasos),
            "es_urgente": es_urgente,
            "tipo_plan": "urgencia" if es_urgente else "consulta_normal",
            "intenciones_detectadas": [i["intencion"] for i in intenciones],
        }

    # ========================
    # TOMA DE DECISIONES (IE6)
    # ========================

    def evaluar_riesgo_transferencia(self, monto: float, saldo_disponible: float) -> dict:
        """Evalúa el riesgo de una transferencia y decide acción."""
        if monto <= 0:
            return {"decision": "rechazar", "motivo": "Monto inválido", "criticidad": "alta"}

        relacion = monto / saldo_disponible if saldo_disponible > 0 else float("inf")

        if relacion > 1.0:
            return {"decision": "rechazar", "motivo": "Saldo insuficiente", "criticidad": "alta"}
        elif relacion > 0.7:
            return {"decision": "requiere_validacion", "motivo": "Transferencia de alto monto (>70% del saldo)", "criticidad": "alta"}
        elif relacion > 0.3:
            return {"decision": "advertir", "motivo": "Transferencia de monto considerable", "criticidad": "media"}
        else:
            return {"decision": "aprobar", "motivo": "Transferencia dentro de parámetros normales", "criticidad": "baja"}

    def evaluar_credito(self, monto: float, ingresos_mensuales: float = 800_000) -> dict:
        """Evalúa la viabilidad de un crédito según capacidad de pago."""
        cuota_estimada = monto * 0.05  # aproximación
        relacion_cuota_ingreso = cuota_estimada / ingresos_mensuales

        if relacion_cuota_ingreso > 0.4:
            return {"decision": "rechazar", "motivo": f"La cuota estimada ({cuota_estimada:,.0f}) excede el 40% de tus ingresos", "criticidad": "alta"}
        elif relacion_cuota_ingreso > 0.25:
            return {"decision": "revisar", "motivo": f"La cuota estimada representa el {relacion_cuota_ingreso*100:.0f}% de tus ingresos. Se recomienda evaluar con cuidado.", "criticidad": "media"}
        else:
            return {"decision": "recomendar", "motivo": f"La cuota estimada ({cuota_estimada:,.0f}) es viable según tus ingresos.", "criticidad": "baja"}

    def registrar_accion(self, accion: str, resultado: str):
        self.historial_acciones.append({
            "timestamp": datetime.now().isoformat(),
            "accion": accion,
            "resultado": resultado[:100],
        })

    def obtener_resumen_plan(self, plan: dict) -> str:
        """Genera resumen legible del plan."""
        if not plan["pasos"]:
            return plan["mensaje"]

        lineas = [f"Plan de {plan['total_pasos']} paso(s):"]
        tipo_emoji = {"alta": "[URGENTE]", "media": "[PRECAUCION]", "baja": "[INFO]"}
        for paso in plan["pasos"]:
            emoji = tipo_emoji.get(paso["criticidad"], "[INFO]")
            deps = f" (tras: {', '.join(paso['dependencias'])})" if paso["dependencias"] else ""
            lineas.append(f"  {emoji} {paso['orden']}. {paso['accion']}{deps}")

        if plan["es_urgente"]:
            lineas.append("\n[!] Se detectaron acciones urgentes - priorizando ejecucion")

        return "\n".join(lineas)


class Orquestador:
    """
    Orquestador multi-paso (IL2.3).
    Coordina la ejecución secuencial de múltiples herramientas.
    """

    def __init__(self, tool_map: dict[str, Callable]):
        self.tool_map = tool_map
        self.planificador = Planificador()

    def _preparar_argumentos(self, tool_obj, consulta: str) -> dict:
        """Inspecciona la herramienta y prepara argumentos por defecto."""
        import inspect
        import re
        nombre_herramienta = getattr(tool_obj, "name", str(tool_obj))
        if hasattr(tool_obj, "func"):
            sig = inspect.signature(tool_obj.func)
        else:
            sig = inspect.signature(tool_obj)
        args = {}
        for name, param in sig.parameters.items():
            if param.default is not inspect.Parameter.empty:
                args[name] = param.default
            elif name == "query":
                args[name] = consulta
            elif name == "monto":
                args[name] = 2000000
            elif name == "plazo_meses":
                args[name] = 24
            elif name == "numero_tarjeta":
                consulta_lower = consulta.lower()
                tipo_cuenta = "CuentaAhorros" if "ahorro" in consulta_lower else "CuentaRUT"
                try:
                    from herramientas_bancoestado import api as api_bee
                    card_data = json.loads(api_bee.buscar_tarjeta_por_cuenta("12.345.678-9", tipo_cuenta))
                    if card_data.get("success"):
                        args[name] = card_data["numero"]
                    else:
                        args[name] = "4532-7890-1234-5678"
                except Exception:
                    args[name] = "4532-7890-1234-5678"
            elif name == "tipo_cuenta_origen":
                consulta_lower = consulta.lower()
                if "ahorro" in consulta_lower and ("desde" in consulta_lower or "de" in consulta_lower):
                    args[name] = "CuentaAhorros"
                else:
                    args[name] = "CuentaRUT"
            elif name == "rut_destino":
                match_rut = re.search(r'\b(\d{1,2}\.?\d{3}\.?\d{3}[-]?[\dkK])\b', consulta)
                args[name] = match_rut.group(1) if match_rut else "12.345.678-9"
            elif name == "tipo_cuenta_destino":
                consulta_lower = consulta.lower()
                if "ahorro" in consulta_lower and ("a " in consulta_lower or "para" in consulta_lower or "destino" in consulta_lower):
                    args[name] = "CuentaAhorros"
                elif "rut" in consulta_lower and ("a " in consulta_lower or "para" in consulta_lower or "destino" in consulta_lower):
                    args[name] = "CuentaRUT"
                else:
                    args[name] = "CuentaAhorros"
            elif name == "monto_mensual":
                args[name] = 50000
            elif name == "tipo_cuenta":
                consulta_lower = consulta.lower()
                if "ahorro" in consulta_lower or "cuenta de ahorros" in consulta_lower:
                    args[name] = "CuentaAhorros"
                else:
                    args[name] = "CuentaRUT"

        # Extraer montos desde la consulta (ej: "150 millones", "$500.000", "5000000")
        consulta_num = consulta.lower().replace('$', '').replace(',', '').strip()
        patron_monto = r'(\d+(?:\.\d+)?)\s*(millones|mil)\b'
        coincidencia = re.search(patron_monto, consulta_num)
        if coincidencia:
            num = float(coincidencia.group(1))
            if coincidencia.group(2) == "millones":
                args["monto"] = int(num * 1_000_000)
            elif coincidencia.group(2) == "mil":
                args["monto"] = int(num * 1_000)
        else:
            consulta_limpia = re.sub(r'(\d)\.(\d{3})', r'\1\2', consulta_num)
            numeros = re.findall(r'\b(\d{4,})\b', consulta_limpia)
            if numeros:
                args["monto"] = int(max(float(n) for n in numeros))

        return args

    def ejecutar_plan(self, consulta: str) -> list[dict]:
        """Ejecuta un plan paso a paso, encadenando resultados."""
        plan = self.planificador.crear_plan(consulta)
        resultados = []

        for paso in plan["pasos"]:
            herramienta = paso["herramienta"]
            if herramienta in self.tool_map:
                try:
                    tool_obj = self.tool_map[herramienta]
                    args = self._preparar_argumentos(tool_obj, consulta)
                    if hasattr(tool_obj, "func"):
                        resultado = tool_obj.func(**args)
                    else:
                        resultado = tool_obj(**args)
                    resultados.append({
                        "paso": paso["orden"],
                        "herramienta": herramienta,
                        "exitoso": True,
                        "resultado": resultado,
                    })
                except Exception as e:
                    resultados.append({
                        "paso": paso["orden"],
                        "herramienta": herramienta,
                        "exitoso": False,
                        "error": str(e),
                    })

        return resultados
