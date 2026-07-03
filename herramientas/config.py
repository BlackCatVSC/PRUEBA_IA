"""
Configuracion centralizada para todos los modulos IL3.x.
Evita hardcodeos: todos los valores se definen aqui o via variables de entorno.

Usar:
    from herramientas.config import (
        COSTOS_POR_MODELO, costo_por_1k,
        CACHE_UMBRAL_SIMILITUD, CACHE_TTL_SEGUNDOS,
        PROCESADOR_TAMANO_LOTE,
        ANOMALIAS_VENTANA, ANOMALIAS_FACTOR_SPIKE,
        ANOMALIAS_UMBRAL_ERROR, ANOMALIAS_UMBRAL_CACHE,
    )
"""

import os

# ─── Modelo LLM ─────────────────────────────────────────────────

MODELO_POTENTE = os.environ.get("LLM_MODELO_POTENTE", "gpt-4o")
MODELO_LIGERO = os.environ.get("LLM_MODELO_LIGERO", "gpt-4o-mini")
MODELO_POR_DEFECTO = os.environ.get("LLM_MODELO_DEFECTO", MODELO_POTENTE)

# ─── Costos por 1K tokens (input + output) ──────────────────────

COSTOS_POR_MODELO = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "cache": {"input": 0.0, "output": 0.0},
    "offline": {"input": 0.0, "output": 0.0},
}

COSTO_PROMEDIO_POR_1K = float(os.environ.get("LLM_COSTO_POR_1K", "0.00075"))


def costo_por_1k(modelo: str) -> float:
    """Retorna el costo promedio por 1K tokens para un modelo dado."""
    precios = COSTOS_POR_MODELO.get(modelo)
    if precios is None:
        return COSTO_PROMEDIO_POR_1K
    return (precios["input"] + precios["output"]) / 2


# ─── Cache Semantico ────────────────────────────────────────────

CACHE_UMBRAL_SIMILITUD = float(os.environ.get("CACHE_UMBRAL_SIMILITUD", "0.75"))
CACHE_TTL_SEGUNDOS = int(os.environ.get("CACHE_TTL_SEGUNDOS", "3600"))

# ─── Procesador de Lotes ────────────────────────────────────────

PROCESADOR_TAMANO_LOTE = int(os.environ.get("PROCESADOR_TAMANO_LOTE", "5"))

# ─── Detector de Anomalias ──────────────────────────────────────

ANOMALIAS_VENTANA = int(os.environ.get("ANOMALIAS_VENTANA", "20"))
ANOMALIAS_FACTOR_SPIKE = float(os.environ.get("ANOMALIAS_FACTOR_SPIKE", "2.5"))
ANOMALIAS_UMBRAL_ERROR = float(os.environ.get("ANOMALIAS_UMBRAL_ERROR_PCT", "20.0"))
ANOMALIAS_UMBRAL_CACHE = float(os.environ.get("ANOMALIAS_UMBRAL_CACHE_PCT", "50.0"))

# ─── Observabilidad ─────────────────────────────────────────────

OBS_TRUNCAR_ENTRADA = int(os.environ.get("OBS_TRUNCAR_ENTRADA", "100"))
OBS_TRUNCAR_ERROR = int(os.environ.get("OBS_TRUNCAR_ERROR", "120"))
