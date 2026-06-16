"""
BancoEstado API Ficticia
========================
Simula los endpoints del sistema cerrado de BancoEstado.
Proporciona datos realistas para las herramientas del agente.

Arquitectura:
  - Almacena clientes, cuentas, tarjetas y créditos en memoria
  - Cada método representa un "endpoint" del banco
  - Los datos incluyen transacciones simuladas con fechas
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional


class BancoEstadoAPI:
    """Simulación del backend bancario de BancoEstado."""

    def __init__(self):
        self._clientes = {}
        self._init_datos()

    def _init_datos(self):
        """Inicializa datos de prueba realistas."""
        hoy = datetime.now()

        cliente_ejemplo = {
            "rut": "12.345.678-9",
            "nombre": "Juan Pérez González",
            "email": "juan.perez@email.com",
            "telefono": "+56 9 1234 5678",
            "direccion": "Av. Providencia 1234, Santiago",
            "fecha_ingreso": (hoy - timedelta(days=365 * 3)).isoformat(),
        }

        self._clientes[cliente_ejemplo["rut"]] = {
            "datos": cliente_ejemplo,
            "cuentas": {
                "CuentaRUT": {
                    "tipo": "CuentaRUT",
                    "numero": "123456789",
                    "saldo": 120_000,
                    "disponible": 115_000,
                    "bloqueada": False,
                    "fecha_creacion": (hoy - timedelta(days=365 * 2)).isoformat(),
                    "movimientos": [
                        {"fecha": (hoy - timedelta(days=1)).isoformat(), "tipo": "Depósito", "monto": 50_000, "saldo_post": 120_000},
                        {"fecha": (hoy - timedelta(days=3)).isoformat(), "tipo": "Giro", "monto": -20_000, "saldo_post": 70_000},
                        {"fecha": (hoy - timedelta(days=5)).isoformat(), "tipo": "Transferencia recibida", "monto": 30_000, "saldo_post": 90_000},
                        {"fecha": (hoy - timedelta(days=7)).isoformat(), "tipo": "Carga de sueldo", "monto": 400_000, "saldo_post": 60_000},
                        {"fecha": (hoy - timedelta(days=10)).isoformat(), "tipo": "Pago cuenta", "monto": -350_000, "saldo_post": -340_000},
                    ],
                },
                "CuentaAhorros": {
                    "tipo": "Cuenta de Ahorros",
                    "numero": "987654321",
                    "saldo": 450_000,
                    "disponible": 450_000,
                    "bloqueada": False,
                    "tasa_interes": 0.5,
                    "fecha_creacion": (hoy - timedelta(days=365)).isoformat(),
                    "movimientos": [
                        {"fecha": (hoy - timedelta(days=2)).isoformat(), "tipo": "Depósito", "monto": 100_000, "saldo_post": 450_000},
                        {"fecha": (hoy - timedelta(days=15)).isoformat(), "tipo": "Interés", "monto": 1_250, "saldo_post": 350_000},
                        {"fecha": (hoy - timedelta(days=30)).isoformat(), "tipo": "Depósito", "monto": 200_000, "saldo_post": 348_750},
                    ],
                },
            },
            "tarjetas": [
                {
                    "numero": "4532-7890-1234-5678",
                    "tipo": "Débito",
                    "asociada_a": "CuentaRUT",
                    "estado": "activa",
                    "fecha_vencimiento": "12/2027",
                    "cvv": "***",
                    "limite_diario": 500_000,
                },
                {
                    "numero": "5123-4567-8901-2345",
                    "tipo": "Crédito",
                    "asociada_a": "CuentaAhorros",
                    "estado": "activa",
                    "fecha_vencimiento": "08/2028",
                    "cvv": "***",
                    "limite_credito": 2_000_000,
                    "deuda_actual": 350_000,
                    "credito_disponible": 1_650_000,
                },
            ],
            "creditos": [
                {
                    "id": "CR-001",
                    "tipo": "Crédito de Consumo",
                    "monto_solicitado": 3_000_000,
                    "monto_aprobado": 2_500_000,
                    "plazo_meses": 24,
                    "tasa_interes_anual": 0.19,
                    "cuota_mensual": 125_456,
                    "saldo_adeudado": 1_800_000,
                    "estado": "activo",
                    "fecha_inicio": (hoy - timedelta(days=180)).isoformat(),
                    "proximo_vencimiento": (hoy + timedelta(days=15)).isoformat(),
                    "pagos_realizados": 6,
                    "total_cuotas": 24,
                },
            ],
        }

    def _get_cliente(self, rut: str) -> tuple:
        cliente = self._clientes.get(rut)
        if not cliente:
            raise ValueError(f"Cliente con RUT {rut} no encontrado")
        return cliente

    # ==================== ENDPOINTS ====================

    def consultar_datos_cliente(self, rut: str) -> str:
        """Obtiene los datos personales del cliente."""
        cliente = self._get_cliente(rut)
        return json.dumps({"success": True, "datos": cliente["datos"]}, indent=2, ensure_ascii=False)

    def consultar_saldo(self, rut: str, tipo_cuenta: str = "CuentaRUT") -> str:
        """Consulta el saldo de una cuenta específica."""
        cliente = self._get_cliente(rut)
        cuenta = cliente["cuentas"].get(tipo_cuenta)
        if not cuenta:
            return json.dumps({"success": False, "error": f"Cuenta {tipo_cuenta} no encontrada"}, ensure_ascii=False)
        if cuenta["bloqueada"]:
            return json.dumps({"success": False, "error": "La cuenta se encuentra bloqueada"}, ensure_ascii=False)
        return json.dumps({
            "success": True,
            "rut": rut,
            "cuenta": tipo_cuenta,
            "numero": cuenta["numero"],
            "saldo": cuenta["saldo"],
            "disponible": cuenta["disponible"],
            "ultimos_movimientos": cuenta["movimientos"][-3:],
        }, indent=2, ensure_ascii=False)

    def consultar_estado_cuenta(self, rut: str, tipo_cuenta: str = "CuentaRUT") -> str:
        """Obtiene el estado de cuenta completo con todos los movimientos."""
        cliente = self._get_cliente(rut)
        cuenta = cliente["cuentas"].get(tipo_cuenta)
        if not cuenta:
            return json.dumps({"success": False, "error": f"Cuenta {tipo_cuenta} no encontrada"}, ensure_ascii=False)
        total_ingresos = sum(m["monto"] for m in cuenta["movimientos"] if m["monto"] > 0)
        total_egresos = sum(abs(m["monto"]) for m in cuenta["movimientos"] if m["monto"] < 0)
        return json.dumps({
            "success": True,
            "periodo": "Últimos 30 días",
            "cuenta": tipo_cuenta,
            "numero": cuenta["numero"],
            "saldo_actual": cuenta["saldo"],
            "saldo_disponible": cuenta["disponible"],
            "total_ingresos": total_ingresos,
            "total_egresos": total_egresos,
            "cantidad_movimientos": len(cuenta["movimientos"]),
            "movimientos": cuenta["movimientos"],
        }, indent=2, ensure_ascii=False)

    def crear_cuenta_rut(self, rut: str) -> str:
        """Crea una nueva CuentaRUT para el cliente."""
        cliente = self._get_cliente(rut)
        if "CuentaRUT" in cliente["cuentas"]:
            return json.dumps({"success": False, "error": "El cliente ya posee una CuentaRUT"}, ensure_ascii=False)
        numero = str(random.randint(100_000_000, 999_999_999))
        cliente["cuentas"]["CuentaRUT"] = {
            "tipo": "CuentaRUT",
            "numero": numero,
            "saldo": 0,
            "disponible": 0,
            "bloqueada": False,
            "fecha_creacion": datetime.now().isoformat(),
            "movimientos": [],
        }
        return json.dumps({
            "success": True,
            "mensaje": "CuentaRUT creada exitosamente",
            "numero_cuenta": numero,
            "rut_asociado": rut,
        }, indent=2, ensure_ascii=False)

    def crear_cuenta_ahorros(self, rut: str, deposito_inicial: float = 0) -> str:
        """Crea una nueva Cuenta de Ahorros."""
        cliente = self._get_cliente(rut)
        numero = str(random.randint(100_000_000, 999_999_999))
        cliente["cuentas"]["CuentaAhorros"] = {
            "tipo": "Cuenta de Ahorros",
            "numero": numero,
            "saldo": deposito_inicial,
            "disponible": deposito_inicial,
            "bloqueada": False,
            "tasa_interes": 0.5,
            "fecha_creacion": datetime.now().isoformat(),
            "movimientos": [],
        }
        return json.dumps({
            "success": True,
            "mensaje": "Cuenta de Ahorros creada exitosamente",
            "numero_cuenta": numero,
            "deposito_inicial": deposito_inicial,
            "tasa_interes_anual": "0.5%",
            "rut_asociado": rut,
        }, indent=2, ensure_ascii=False)

    def bloquear_tarjeta(self, rut: str, numero_tarjeta: str, motivo: str = "extravio") -> str:
        """Bloquea una tarjeta por pérdida, robo o sospecha."""
        cliente = self._get_cliente(rut)
        for tarjeta in cliente["tarjetas"]:
            if tarjeta["numero"] == numero_tarjeta:
                tarjeta["estado"] = "bloqueada"
                return json.dumps({
                    "success": True,
                    "mensaje": f"Tarjeta {numero_tarjeta[-4:]} bloqueada exitosamente",
                    "motivo": motivo,
                    "fecha_bloqueo": datetime.now().isoformat(),
                    "recomendacion": "Solicita un reemplazo en tu sucursal más cercana o llama al 600 200 7000",
                }, indent=2, ensure_ascii=False)
        return json.dumps({"success": False, "error": "Número de tarjeta no encontrado"}, ensure_ascii=False)

    def desbloquear_tarjeta(self, rut: str, numero_tarjeta: str) -> str:
        """Desbloquea una tarjeta previamente bloqueada."""
        cliente = self._get_cliente(rut)
        for tarjeta in cliente["tarjetas"]:
            if tarjeta["numero"] == numero_tarjeta:
                tarjeta["estado"] = "activa"
                return json.dumps({
                    "success": True,
                    "mensaje": f"Tarjeta {numero_tarjeta[-4:]} desbloqueada exitosamente",
                }, indent=2, ensure_ascii=False)
        return json.dumps({"success": False, "error": "Número de tarjeta no encontrado"}, ensure_ascii=False)

    def buscar_tarjeta_por_cuenta(self, rut: str, tipo_cuenta: str) -> str:
        """Retorna el número de tarjeta asociado a un tipo de cuenta (CuentaRUT o CuentaAhorros)."""
        cliente = self._get_cliente(rut)
        for tarjeta in cliente["tarjetas"]:
            if tarjeta["asociada_a"] == tipo_cuenta:
                return json.dumps({"success": True, "numero": tarjeta["numero"], "tipo": tarjeta["tipo"]}, ensure_ascii=False)
        return json.dumps({"success": False, "error": f"No se encontró tarjeta asociada a {tipo_cuenta}"}, ensure_ascii=False)

    def simular_credito(self, rut: str, monto: float, plazo_meses: int) -> str:
        """Simula un crédito y calcula cuotas, intereses y costo total."""
        if plazo_meses not in [12, 24, 36, 48]:
            return json.dumps({"success": False, "error": "Plazo no disponible. Opciones: 12, 24, 36, 48 meses"}, ensure_ascii=False)

        # Tasas según plazo
        tasas = {12: 0.15, 24: 0.19, 36: 0.23, 48: 0.27}
        tasa_anual = tasas[plazo_meses]
        tasa_mensual = tasa_anual / 12
        cuota = (monto * tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) ** plazo_meses - 1)
        total_pagar = cuota * plazo_meses
        total_intereses = total_pagar - monto

        return json.dumps({
            "success": True,
            "rut": rut,
            "monto_solicitado": monto,
            "plazo_meses": plazo_meses,
            "tasa_interes_anual": f"{tasa_anual*100:.1f}%",
            "tasa_interes_mensual": f"{tasa_mensual*100:.2f}%",
            "cuota_mensual": round(cuota),
            "total_a_pagar": round(total_pagar),
            "total_intereses": round(total_intereses),
            "costo_total_credito": round(total_intereses),
            "tabla_pagos": [
                {
                    "cuota": i + 1,
                    "monto_cuota": round(cuota),
                    "interes": round(monto * tasa_mensual),
                    "amortizacion": round(cuota - monto * tasa_mensual),
                    "saldo_restante": round(monto - (cuota - monto * tasa_mensual) * (i + 1)),
                }
                for i in range(min(plazo_meses, 6))  # primeras 6 cuotas como ejemplo
            ],
        }, indent=2, ensure_ascii=False)

    def solicitar_credito(self, rut: str, monto: float, plazo_meses: int) -> str:
        """Solicita un crédito formalmente. Si el monto es > 5MM, requiere validación adicional."""
        cliente = self._get_cliente(rut)
        if monto > 5_000_000:
            return json.dumps({
                "success": False,
                "error": "validacion_requerida",
                "mensaje": "Montos superiores a $5.000.000 requieren validación presencial en sucursal",
                "codigo": "VAL_ALTO_MONTO",
            }, indent=2, ensure_ascii=False)
        if monto > 3_000_000:
            return json.dumps({
                "success": False,
                "error": "validacion_requerida",
                "mensaje": "Montos superiores a $3.000.000 requieren verificación de ingresos adicional",
                "codigo": "VAL_VERIFICACION_INGRESOS",
            }, indent=2, ensure_ascii=False)

        tasa = {12: 0.15, 24: 0.19, 36: 0.23, 48: 0.27}.get(plazo_meses, 0.19)
        tasa_mensual = tasa / 12
        cuota = round((monto * tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) ** plazo_meses - 1))

        credito = {
            "id": f"CR-{len(cliente['creditos'])+1:03d}",
            "tipo": "Crédito de Consumo",
            "monto_solicitado": monto,
            "monto_aprobado": monto,
            "plazo_meses": plazo_meses,
            "tasa_interes_anual": tasa,
            "cuota_mensual": cuota,
            "saldo_adeudado": monto,
            "estado": "activo",
            "fecha_inicio": datetime.now().isoformat(),
            "pagos_realizados": 0,
            "total_cuotas": plazo_meses,
        }
        cliente["creditos"].append(credito)

        return json.dumps({
            "success": True,
            "mensaje": "Crédito aprobado y desembolsado",
            "id_credito": credito["id"],
            "monto": monto,
            "plazo_meses": plazo_meses,
            "cuota_mensual": cuota,
            "total_a_pagar": round(cuota * plazo_meses),
        }, indent=2, ensure_ascii=False)

    def consultar_creditos(self, rut: str) -> str:
        """Lista todos los créditos activos del cliente."""
        cliente = self._get_cliente(rut)
        if not cliente["creditos"]:
            return json.dumps({"success": True, "mensaje": "No tienes créditos activos", "creditos": []}, ensure_ascii=False)
        return json.dumps({
            "success": True,
            "cantidad_creditos": len(cliente["creditos"]),
            "creditos": [
                {
                    "id": c["id"],
                    "tipo": c["tipo"],
                    "monto_original": c["monto_aprobado"],
                    "saldo_adeudado": c["saldo_adeudado"],
                    "cuota_mensual": c["cuota_mensual"],
                    "plazo": f"{c['pagos_realizados']}/{c['total_cuotas']} cuotas",
                    "estado": c["estado"],
                    "proximo_vencimiento": c.get("proximo_vencimiento", "N/A"),
                }
                for c in cliente["creditos"]
            ],
        }, indent=2, ensure_ascii=False)

    def transferir(self, rut_origen: str, tipo_cuenta_origen: str, rut_destino: str, tipo_cuenta_destino: str, monto: float) -> str:
        """Realiza una transferencia entre cuentas del mismo o distinto cliente."""
        if monto <= 0:
            return json.dumps({"success": False, "error": "El monto debe ser positivo"}, ensure_ascii=False)

        cliente_origen = self._get_cliente(rut_origen)
        cuenta_origen = cliente_origen["cuentas"].get(tipo_cuenta_origen)
        if not cuenta_origen:
            return json.dumps({"success": False, "error": f"Cuenta origen {tipo_cuenta_origen} no encontrada"}, ensure_ascii=False)
        if cuenta_origen["bloqueada"]:
            return json.dumps({"success": False, "error": "La cuenta origen está bloqueada"}, ensure_ascii=False)
        if cuenta_origen["saldo"] < monto:
            return json.dumps({"success": False, "error": "Saldo insuficiente"}, ensure_ascii=False)

        try:
            cliente_destino = self._get_cliente(rut_destino)
        except ValueError:
            return json.dumps({"success": False, "error": "Cliente destino no encontrado"}, ensure_ascii=False)

        cuenta_destino = cliente_destino["cuentas"].get(tipo_cuenta_destino)
        if not cuenta_destino:
            return json.dumps({"success": False, "error": f"Cuenta destino {tipo_cuenta_destino} no encontrada"}, ensure_ascii=False)

        # Ejecutar transferencia
        ahora = datetime.now().isoformat()
        cuenta_origen["saldo"] -= monto
        cuenta_origen["disponible"] -= monto
        cuenta_origen["movimientos"].append({"fecha": ahora, "tipo": "Transferencia enviada", "monto": -monto, "saldo_post": cuenta_origen["saldo"]})

        cuenta_destino["saldo"] += monto
        cuenta_destino["disponible"] += monto
        cuenta_destino["movimientos"].append({"fecha": ahora, "tipo": "Transferencia recibida", "monto": monto, "saldo_post": cuenta_destino["saldo"]})

        return json.dumps({
            "success": True,
            "mensaje": "Transferencia realizada exitosamente",
            "monto": monto,
            "origen": f"{tipo_cuenta_origen} {cuenta_origen['numero'][-4:]}",
            "destino": f"{tipo_cuenta_destino} {cuenta_destino['numero'][-4:]}",
            "saldo_origen_post": cuenta_origen["saldo"],
            "comprobante": f"TFR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }, indent=2, ensure_ascii=False)

    def simular_ahorro(self, monto_mensual: float, plazo_meses: int, tasa_anual: float = 0.005) -> str:
        """Simula el crecimiento de un ahorro programado."""
        tasa_mensual = tasa_anual / 12
        monto_total = 0
        proyeccion = []
        for mes in range(1, plazo_meses + 1):
            interes = monto_total * tasa_mensual
            monto_total += monto_mensual + interes
            proyeccion.append({"mes": mes, "deposito": monto_mensual, "interes": round(interes), "saldo_acumulado": round(monto_total)})

        return json.dumps({
            "success": True,
            "ahorro_mensual": monto_mensual,
            "plazo_meses": plazo_meses,
            "tasa_anual": f"{tasa_anual*100:.1f}%",
            "total_aportado": round(monto_mensual * plazo_meses),
            "total_intereses_generados": round(monto_total - monto_mensual * plazo_meses),
            "saldo_final_estimado": round(monto_total),
            "proyeccion": proyeccion,
        }, indent=2, ensure_ascii=False)

    def listar_sucursales(self) -> str:
        """Lista sucursales de BancoEstado."""
        sucursales = [
            {"nombre": "Casa Matriz", "direccion": "Av. Libertador Bernardo O'Higgins 1111, Santiago", "horario": "Lun-Vie 9:00-14:00"},
            {"nombre": "Providencia", "direccion": "Av. Providencia 2001, Santiago", "horario": "Lun-Vie 9:00-17:00, Sáb 9:00-13:00"},
            {"nombre": "Las Condes", "direccion": "Av. Apoquindo 4000, Las Condes", "horario": "Lun-Vie 9:00-17:00"},
            {"nombre": "Viña del Mar", "direccion": "Av. Libertad 500, Viña del Mar", "horario": "Lun-Vie 9:00-14:00"},
            {"nombre": "Concepción", "direccion": "Calle Aníbal Pinto 200, Concepción", "horario": "Lun-Vie 9:00-14:00"},
        ]
        return json.dumps({"success": True, "sucursales": sucursales}, indent=2, ensure_ascii=False)

    def actualizar_saldo(self, rut: str, tipo_cuenta: str, monto: float) -> str:
        """Actualiza el saldo de una cuenta (ej: deposito por loteria, herencia, etc.)."""
        cliente = self._get_cliente(rut)
        cuenta = cliente["cuentas"].get(tipo_cuenta)
        if not cuenta:
            return json.dumps({"success": False, "error": f"Cuenta {tipo_cuenta} no encontrada"}, ensure_ascii=False)
        if monto <= 0:
            return json.dumps({"success": False, "error": "El monto debe ser positivo"}, ensure_ascii=False)

        ahora = datetime.now().isoformat()
        cuenta["saldo"] += monto
        cuenta["disponible"] += monto
        cuenta["movimientos"].append({
            "fecha": ahora,
            "tipo": "Depósito por actualización",
            "monto": monto,
            "saldo_post": cuenta["saldo"],
        })
        return json.dumps({
            "success": True,
            "mensaje": f"Saldo actualizado exitosamente. Nuevo saldo en {tipo_cuenta}: ${cuenta['saldo']:,}",
            "tipo_cuenta": tipo_cuenta,
            "monto_ingresado": monto,
            "saldo_nuevo": cuenta["saldo"],
        }, indent=2, ensure_ascii=False)

    def consultar_productos(self) -> str:
        """Lista los productos disponibles de BancoEstado."""
        productos = [
            {
                "nombre": "CuentaRUT",
                "tipo": "Cuenta Vista",
                "descripcion": "Cuenta de bajo costo con tarjeta de débito asociada",
                "requisitos": "Cédula de identidad vigente",
                "costo": "Sin costo de mantención",
            },
            {
                "nombre": "Cuenta de Ahorros",
                "tipo": "Ahorro",
                "descripcion": "Cuenta que genera intereses sobre el saldo",
                "tasa_interes": "0.5% anual",
                "requisitos": "Tener CuentaRUT o Cuenta Corriente",
            },
            {
                "nombre": "Crédito de Consumo",
                "tipo": "Crédito",
                "descripcion": "Préstamo personal para diversos fines",
                "plazos": "12 a 48 meses",
                "tasa_desde": "desde 15% anual",
                "requisitos": "Ingresos mínimos de $300.000 y evaluación crediticia",
            },
            {
                "nombre": "Tarjeta de Crédito",
                "tipo": "Tarjeta",
                "descripcion": "Línea de crédito rotativa con límite asignado",
                "costo_anual": "0 UF primera año",
                "requisitos": "Evaluación crediticia",
            },
            {
                "nombre": "Seguro de Vida",
                "tipo": "Seguro",
                "descripcion": "Protección para ti y tu familia",
                "costo_desde": "desde $3.500/mes",
                "cobertura": "Muerte accidental, invalidez total",
            },
        ]
        return json.dumps({"success": True, "productos": productos}, indent=2, ensure_ascii=False)
