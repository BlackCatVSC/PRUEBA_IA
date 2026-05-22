"""
Herramientas BancoEstado para LangChain
========================================
Wrappers LangChain que consumen la API ficticia de BancoEstado.
Cada herramienta sigue el patrón JSON Schema para Function Calling.
"""

import json
from langchain_classic.agents import tool
from bancoestado_api import BancoEstadoAPI

RUT_POR_DEFECTO = "12.345.678-9"
api = BancoEstadoAPI()


@tool
def consultar_saldo(tipo_cuenta: str = "CuentaRUT") -> str:
    """Consulta el saldo disponible de una cuenta bancaria. Recibe el tipo de cuenta (CuentaRUT o CuentaAhorros)."""
    return api.consultar_saldo(RUT_POR_DEFECTO, tipo_cuenta)


@tool
def consultar_estado_cuenta(tipo_cuenta: str = "CuentaRUT") -> str:
    """Obtiene el estado de cuenta completo con todos los movimientos e ingresos/egresos del período."""
    return api.consultar_estado_cuenta(RUT_POR_DEFECTO, tipo_cuenta)


@tool
def crear_cuenta_rut() -> str:
    """Crea una nueva CuentaRUT para el cliente. No requiere parámetros."""
    return api.crear_cuenta_rut(RUT_POR_DEFECTO)


@tool
def crear_cuenta_ahorros(deposito_inicial: float = 0) -> str:
    """Crea una nueva Cuenta de Ahorros. Recibe un monto opcional como depósito inicial."""
    return api.crear_cuenta_ahorros(RUT_POR_DEFECTO, deposito_inicial)


@tool
def bloquear_tarjeta(numero_tarjeta: str, motivo: str = "extravio") -> str:
    """Bloquea una tarjeta bancaria por pérdida, robo o sospecha de fraude. Recibe número de tarjeta y motivo."""
    return api.bloquear_tarjeta(RUT_POR_DEFECTO, numero_tarjeta, motivo)


@tool
def desbloquear_tarjeta(numero_tarjeta: str) -> str:
    """Desbloquea una tarjeta que fue bloqueada previamente. Recibe el número de tarjeta."""
    return api.desbloquear_tarjeta(RUT_POR_DEFECTO, numero_tarjeta)


@tool
def simular_credito(monto: float, plazo_meses: int) -> str:
    """Simula un crédito de consumo. Calcula cuota mensual, interés total y tabla de pagos según monto y plazo (12,24,36,48 meses)."""
    return api.simular_credito(RUT_POR_DEFECTO, monto, plazo_meses)


@tool
def solicitar_credito(monto: float, plazo_meses: int) -> str:
    """Solicita un crédito formalmente. Montos sobre $3.000.000 requieren verificación adicional. Montos sobre $5.000.000 requieren ir a sucursal."""
    return api.solicitar_credito(RUT_POR_DEFECTO, monto, plazo_meses)


@tool
def consultar_creditos() -> str:
    """Lista todos los créditos activos del cliente con su estado, saldo y próxima cuota."""
    return api.consultar_creditos(RUT_POR_DEFECTO)


@tool
def transferir(tipo_cuenta_origen: str, rut_destino: str, tipo_cuenta_destino: str, monto: float) -> str:
    """Realiza una transferencia entre cuentas. Recibe tipo cuenta origen, RUT destino, tipo cuenta destino y monto."""
    return api.transferir(RUT_POR_DEFECTO, tipo_cuenta_origen, rut_destino, tipo_cuenta_destino, monto)


@tool
def simular_ahorro(monto_mensual: float, plazo_meses: int) -> str:
    """Simula un ahorro programado. Muestra proyección mes a mes con intereses según monto mensual y plazo."""
    return api.simular_ahorro(monto_mensual, plazo_meses)


@tool
def listar_sucursales() -> str:
    """Lista las sucursales de BancoEstado con dirección y horario de atención."""
    return api.listar_sucursales()


@tool
def consultar_productos() -> str:
    """Lista los productos bancarios disponibles (CuentaRUT, Ahorros, Créditos, Seguros, etc.)."""
    return api.consultar_productos()


@tool
def actualizar_saldo(tipo_cuenta: str, monto: float) -> str:
    """Actualiza el saldo de una cuenta (CuentaRUT o CuentaAhorros) agregando un monto. Usar cuando el cliente reporte depositos, ganancias de loteria, herencias, etc."""
    return api.actualizar_saldo(RUT_POR_DEFECTO, tipo_cuenta, monto)


@tool
def obtener_fecha_hora() -> str:
    """Devuelve la fecha y hora actual del sistema."""
    from datetime import datetime
    return f"La fecha y hora actual es: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def buscar_wikipedia(query: str) -> str:
    """Busca información en Wikipedia sobre cualquier tema. Útil para consultas generales."""
    import wikipedia as wk
    try:
        wk.set_lang("es")
        return wk.summary(query, sentences=3)
    except wk.exceptions.PageError:
        return f"No se encontró información sobre '{query}'."
    except wk.exceptions.DisambiguationError as e:
        return f"La búsqueda es ambigua. Opciones: {e.options[:3]}"
    except Exception as e:
        return f"Error: {e}"


TOOL_LIST = [
    consultar_saldo,
    consultar_estado_cuenta,
    crear_cuenta_rut,
    crear_cuenta_ahorros,
    bloquear_tarjeta,
    desbloquear_tarjeta,
    simular_credito,
    solicitar_credito,
    consultar_creditos,
    transferir,
    simular_ahorro,
    listar_sucursales,
    consultar_productos,
    actualizar_saldo,
    obtener_fecha_hora,
    buscar_wikipedia,
]
