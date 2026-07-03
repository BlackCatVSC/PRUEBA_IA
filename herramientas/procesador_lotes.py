"""
IL3.2: Procesamiento por Lotes (Batch)
=======================================
Procesa solicitudes en lotes con cola de prioridad. Agrupa
consultas similares y las procesa juntas, reduciendo la sobrecarga
de red y permitiendo priorizar solicitudes criticas.

Integrado con:
  - app.py (Web) - encola multiples usuarios concurrentes
  - agent_bancoestado.py (CLI) - disponible aunque single-user
"""

import heapq
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


def _costo_promedio() -> float:
    from herramientas.config import COSTO_PROMEDIO_POR_1K
    return COSTO_PROMEDIO_POR_1K


class Prioridad(IntEnum):
    CRITICA = 1
    ALTA = 2
    NORMAL = 3
    BAJA = 4


@dataclass
class Solicitud:
    id: str
    pregunta: str
    prioridad: Prioridad
    timestamp: float = field(default_factory=time.time)
    respuesta: str | None = None
    estado: str = "pendiente"
    tokens_usados: int = 0
    latencia_ms: float = 0.0

    def __lt__(self, other: "Solicitud") -> bool:
        if self.prioridad != other.prioridad:
            return self.prioridad < other.prioridad
        return self.timestamp < other.timestamp


class ProcesadorLotes:
    """Procesa solicitudes en lotes con cola de prioridad."""

    def __init__(self, tamano_lote: int = None):
        from herramientas.config import PROCESADOR_TAMANO_LOTE
        self.tamano_lote = tamano_lote if tamano_lote is not None else PROCESADOR_TAMANO_LOTE
        self.cola: list[Solicitud] = []
        self.procesadas: list[Solicitud] = []
        self.contador_id = 0

    def agregar(self, pregunta: str, prioridad: Prioridad = Prioridad.NORMAL) -> str:
        self.contador_id += 1
        solicitud = Solicitud(
            id=f"SOL-{self.contador_id:04d}",
            pregunta=pregunta,
            prioridad=prioridad,
        )
        heapq.heappush(self.cola, solicitud)
        return solicitud.id

    def _procesar_solicitud(self, solicitud: Solicitud, funcion_procesamiento: Any) -> Solicitud:
        solicitud.estado = "procesando"
        inicio = time.time()

        try:
            solicitud.respuesta = funcion_procesamiento(solicitud.pregunta)
            solicitud.estado = "completada"
        except Exception as e:
            solicitud.respuesta = f"Error: {str(e)}"
            solicitud.estado = "error"

        solicitud.latencia_ms = (time.time() - inicio) * 1000
        return solicitud

    def procesar_lote(self, funcion_procesamiento: Any) -> list[Solicitud]:
        lote: list[Solicitud] = []
        for _ in range(min(self.tamano_lote, len(self.cola))):
            if self.cola:
                lote.append(heapq.heappop(self.cola))

        if not lote:
            return []

        resultados: list[Solicitud] = []
        for solicitud in lote:
            resultado = self._procesar_solicitud(solicitud, funcion_procesamiento)
            resultados.append(resultado)
            self.procesadas.append(resultado)

        return resultados

    def procesar_todo(self, funcion_procesamiento: Any) -> list[Solicitud]:
        todos: list[Solicitud] = []
        while self.cola:
            resultados = self.procesar_lote(funcion_procesamiento)
            todos.extend(resultados)
        return todos

    def pendientes(self) -> int:
        return len(self.cola)

    def obtener_resumen(self) -> dict:
        if not self.procesadas:
            return {"mensaje": "No hay solicitudes procesadas"}

        completadas = [s for s in self.procesadas if s.estado == "completada"]
        errores = [s for s in self.procesadas if s.estado == "error"]
        tokens_total = sum(s.tokens_usados for s in self.procesadas)
        latencias = [s.latencia_ms for s in self.procesadas if s.latencia_ms > 0]

        return {
            "total_procesadas": len(self.procesadas),
            "completadas": len(completadas),
            "errores": len(errores),
            "pendientes": len(self.cola),
            "tokens_total": tokens_total,
            "latencia_promedio_ms": round(sum(latencias) / len(latencias), 2) if latencias else 0.0,
            "costo_estimado_usd": round((tokens_total / 1000) * _costo_promedio(), 6),
        }
