"""
IL3.1: Herramientas de Observabilidad y Metricas
=================================================
Logging estructurado con timestamps, recoleccion de metricas
(tiempos de respuesta, uso de tokens reales via callback de LangChain,
tasa de errores) y wrapper de agente que registra todas las interacciones.

Integrado con:
  - agent_bancoestado.py (CLI)
  - app.py (Web/Flask)
"""

import logging
import time
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from herramientas.config import OBS_TRUNCAR_ENTRADA, OBS_TRUNCAR_ERROR, MODELO_POR_DEFECTO

# ══════════════════════════════════════════════════════════════════
# 1. LOGGING ESTRUCTURADO CON TIMESTAMPS
# ══════════════════════════════════════════════════════════════════

_formato = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formato)

_logger_raiz = logging.getLogger("observabilidad")
_logger_raiz.setLevel(logging.DEBUG)
if not _logger_raiz.handlers:
    _logger_raiz.addHandler(_console_handler)


def get_logger(nombre: str) -> logging.Logger:
    """Obtiene un logger configurado para un componente especifico."""
    log = logging.getLogger(nombre)
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        log.addHandler(_console_handler)
    return log


# ══════════════════════════════════════════════════════════════════
# 2. CALLBACK DE LANGCHAIN PARA CAPTURA REAL DE TOKENS
# ══════════════════════════════════════════════════════════════════

class TokenCallbackHandler(BaseCallbackHandler):
    """Callback que captura el uso real de tokens del LLM via LangChain.

    Se pasa a executor.invoke() via config={'callbacks': [handler]}.
    LangChain propaga automaticamente los callbacks al LLM subyacente.
    """

    def __init__(self) -> None:
        self.tokens_entrada: int = 0
        self.tokens_salida: int = 0
        self.tokens_total: int = 0

    def reset(self) -> None:
        self.tokens_entrada = 0
        self.tokens_salida = 0
        self.tokens_total = 0

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        token_usage: dict = {}

        if response is not None and hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        if not token_usage and hasattr(response, "generations"):
            try:
                for gen_list in response.generations:
                    for gen in gen_list:
                        msg = getattr(gen, "message", None)
                        if msg is None:
                            continue
                        um = getattr(msg, "usage_metadata", None)
                        if um and isinstance(um, dict):
                            token_usage = um
                            break
                        rm = getattr(msg, "response_metadata", None)
                        if rm and isinstance(rm, dict):
                            tu = rm.get("token_usage")
                            if tu:
                                token_usage = tu
                                break
                        gi = getattr(gen, "generation_info", None)
                        if gi and isinstance(gi, dict):
                            tu = gi.get("token_usage")
                            if tu:
                                token_usage = tu
                                break
            except Exception:
                pass

        self.tokens_entrada += token_usage.get("prompt_tokens", token_usage.get("input_tokens", 0))
        self.tokens_salida += token_usage.get("completion_tokens", token_usage.get("output_tokens", 0))
        self.tokens_total = self.tokens_entrada + self.tokens_salida


# ══════════════════════════════════════════════════════════════════
# 3. REGISTRO DE METRICA INDIVIDUAL
# ══════════════════════════════════════════════════════════════════

@dataclass
class RegistroMetrica:
    timestamp: str
    tiempo_respuesta_ms: float
    tokens_entrada: int
    tokens_salida: int
    exitoso: bool
    modelo: str


# ══════════════════════════════════════════════════════════════════
# 4. RECOLECTOR DE METRICAS
# ══════════════════════════════════════════════════════════════════

class RecolectorMetricas:
    """Recolecta y resume metricas de rendimiento del agente."""

    def __init__(self) -> None:
        self.registros: list[RegistroMetrica] = []

    def registrar(
        self,
        tiempo_ms: float,
        tokens_in: int,
        tokens_out: int,
        exitoso: bool,
        modelo: str = MODELO_POR_DEFECTO,
    ) -> None:
        registro = RegistroMetrica(
            timestamp=datetime.now().isoformat(),
            tiempo_respuesta_ms=round(tiempo_ms, 2),
            tokens_entrada=tokens_in,
            tokens_salida=tokens_out,
            exitoso=exitoso,
            modelo=modelo,
        )
        self.registros.append(registro)

    def resumen(self) -> dict:
        if not self.registros:
            return {"total_peticiones": 0}

        tiempos = [r.tiempo_respuesta_ms for r in self.registros]
        total_tokens_entrada = sum(r.tokens_entrada for r in self.registros)
        total_tokens_salida = sum(r.tokens_salida for r in self.registros)
        total_tokens = total_tokens_entrada + total_tokens_salida
        errores = sum(1 for r in self.registros if not r.exitoso)
        exitos = sum(1 for r in self.registros if r.exitoso)

        return {
            "total_peticiones": len(self.registros),
            "exitosas": exitos,
            "fallidas": errores,
            "tasa_errores_pct": round((errores / len(self.registros)) * 100, 2),
            "tiempo_promedio_ms": round(sum(tiempos) / len(tiempos), 2),
            "tiempo_maximo_ms": round(max(tiempos), 2),
            "tiempo_minimo_ms": round(min(tiempos), 2),
            "total_tokens": total_tokens,
            "tokens_entrada": total_tokens_entrada,
            "tokens_salida": total_tokens_salida,
            "tokens_promedio_por_peticion": round(total_tokens / len(self.registros), 2),
        }

    def exportar_registros(self) -> str:
        return json.dumps(
            {
                "generado": datetime.now().isoformat(),
                "resumen": self.resumen(),
                "registros": [
                    {
                        "timestamp": r.timestamp,
                        "tiempo_respuesta_ms": r.tiempo_respuesta_ms,
                        "tokens_entrada": r.tokens_entrada,
                        "tokens_salida": r.tokens_salida,
                        "exitoso": r.exitoso,
                        "modelo": r.modelo,
                    }
                    for r in self.registros
                ],
            },
            indent=2,
            ensure_ascii=False,
        )


# ══════════════════════════════════════════════════════════════════
# 5. WRAPPER DE AGENTE OBSERVABLE
# ══════════════════════════════════════════════════════════════════

class AgenteObservable:
    """Agente que registra cada interaccion con metricas de rendimiento.

    Uso tipico:
        obs = AgenteObservable("bancoestado")

        # Modo LLM
        resultado = obs.medir_llm(executor, {"input": consulta}, modelo="gpt-4o")

        # Modo offline
        resultado = obs.medir_demo(orquestador.ejecutar_plan, consulta)

        # Obtener metricas
        print(obs.reporte())
        obs.metricas.resumen()  # -> dict
    """

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.metricas = RecolectorMetricas()
        self.logger = get_logger(f"agente.{nombre}")
        self.token_callback = TokenCallbackHandler()

    # ── Medición LLM ─────────────────────────────────────────────

    def medir_llm(self, executor: Any, input_dict: dict, modelo: str = "gpt-4o") -> dict:
        """Envuelve executor.invoke() con medicion de metricas.

        Args:
            executor: AgentExecutor de LangChain.
            input_dict: Diccionario con la consulta (ej: {"input": "texto"}).
            modelo: Identificador del modelo usado.

        Returns:
            El dict resultado de executor.invoke() con la clave "output".
        """
        entrada_preview = str(input_dict.get("input", ""))[:OBS_TRUNCAR_ENTRADA]
        self.logger.info("LLM entrada: %r", entrada_preview)
        inicio = time.perf_counter()
        self.token_callback.reset()

        try:
            resultado = executor.invoke(
                input_dict,
                {"callbacks": [self.token_callback]},
            )
            duracion_ms = (time.perf_counter() - inicio) * 1000
            tokens_in = self.token_callback.tokens_entrada
            tokens_out = self.token_callback.tokens_salida

            if tokens_in == 0 and tokens_out == 0:
                try:
                    from herramientas.cache_semantico import estimar_tokens
                    entrada = str(input_dict.get("input", ""))
                    salida = str(resultado.get("output", ""))
                    tokens_in = estimar_tokens(entrada)
                    tokens_out = estimar_tokens(salida)
                except Exception:
                    pass

            self.metricas.registrar(duracion_ms, tokens_in, tokens_out, True, modelo)
            self._enviar_a_langsmith(duracion_ms, tokens_in, tokens_out, True, modelo)
            self.logger.info(
                "LLM completado: %.1fms | tokens=%d (in=%d out=%d) | modelo=%s",
                duracion_ms,
                tokens_in + tokens_out,
                tokens_in,
                tokens_out,
                modelo,
            )
            return resultado

        except Exception as e:
            duracion_ms = (time.perf_counter() - inicio) * 1000
            tokens_in = self.token_callback.tokens_entrada
            tokens_out = self.token_callback.tokens_salida

            self.metricas.registrar(duracion_ms, tokens_in, tokens_out, False, modelo)
            self._enviar_a_langsmith(duracion_ms, tokens_in, tokens_out, False, modelo)
            self.logger.warning(
                "LLM error: %s: %s | %.1fms | modelo=%s",
                type(e).__name__,
                str(e)[:OBS_TRUNCAR_ERROR],
                duracion_ms,
                modelo,
            )
            raise

    # ── Medición modo offline/demo ───────────────────────────────

    def medir_demo(self, funcion: Any, consulta: str) -> Any:
        """Envuelve procesamiento en modo demo con medicion de metricas.

        Args:
            funcion: Funcion de procesamiento offline (ej: orquestador.ejecutar_plan).
            consulta: Texto de la consulta del usuario.

        Returns:
            El resultado de la funcion (str o list).
        """
        self.logger.info("DEMO entrada: %r", consulta[:OBS_TRUNCAR_ENTRADA])
        inicio = time.perf_counter()

        try:
            resultado = funcion(consulta)
            duracion_ms = (time.perf_counter() - inicio) * 1000

            self.metricas.registrar(duracion_ms, 0, 0, True, "offline")
            self._enviar_a_langsmith(duracion_ms, 0, 0, True, "offline")
            self.logger.info("DEMO completado: %.1fms", duracion_ms)
            return resultado

        except Exception as e:
            duracion_ms = (time.perf_counter() - inicio) * 1000

            self.metricas.registrar(duracion_ms, 0, 0, False, "offline")
            self._enviar_a_langsmith(duracion_ms, 0, 0, False, "offline")
            self.logger.warning(
                "DEMO error: %s: %s | %.1fms",
                type(e).__name__,
                str(e)[:OBS_TRUNCAR_ERROR],
                duracion_ms,
            )
            raise

    # ── Envio a LangSmith ───────────────────────────────────────

    def _enviar_a_langsmith(self, latencia_ms: float, tokens_in: int,
                            tokens_out: int, exitoso: bool, modelo: str,
                            cache_hit: bool = False):
        try:
            from herramientas.langsmith_config import registrar_metricas_langsmith
            registrar_metricas_langsmith(
                latencia_ms=latencia_ms,
                tokens_entrada=tokens_in,
                tokens_salida=tokens_out,
                exitoso=exitoso,
                modelo=modelo,
                cache_hit=cache_hit,
            )
        except Exception:
            pass

    # ── Reportes ─────────────────────────────────────────────────

    def reporte(self) -> str:
        """Retorna un reporte de metricas formateado para CLI."""
        r = self.metricas.resumen()

        if r.get("total_peticiones", 0) == 0:
            return "No hay metricas registradas."

        return (
            f"{'=' * 60}\n"
            f"  REPORTE DE OBSERVABILIDAD — {self.nombre}\n"
            f"{'=' * 60}\n"
            f"  Total peticiones:        {r['total_peticiones']}\n"
            f"  Exitosas:                {r.get('exitosas', 0)}\n"
            f"  Fallidas:                {r.get('fallidas', 0)}\n"
            f"  Tasa de errores:         {r['tasa_errores_pct']}%\n"
            f"\n"
            f"  Tiempo promedio:         {r['tiempo_promedio_ms']} ms\n"
            f"  Tiempo minimo:           {r['tiempo_minimo_ms']} ms\n"
            f"  Tiempo maximo:           {r['tiempo_maximo_ms']} ms\n"
            f"\n"
            f"  Tokens totales:          {r['total_tokens']}\n"
            f"  Tokens entrada:          {r.get('tokens_entrada', 0)}\n"
            f"  Tokens salida:           {r.get('tokens_salida', 0)}\n"
            f"  Tokens promedio/pet.:    {r.get('tokens_promedio_por_peticion', 0)}\n"
            f"{'=' * 60}"
        )

    def reporte_dict(self) -> dict:
        """Retorna metricas como diccionario (para endpoints JSON)."""
        return {
            "nombre": self.nombre,
            **self.metricas.resumen(),
            "registros_detalle": [
                {
                    "timestamp": r.timestamp,
                    "tiempo_respuesta_ms": r.tiempo_respuesta_ms,
                    "tokens_entrada": r.tokens_entrada,
                    "tokens_salida": r.tokens_salida,
                    "exitoso": r.exitoso,
                    "modelo": r.modelo,
                }
                for r in self.metricas.registros
            ],
        }
