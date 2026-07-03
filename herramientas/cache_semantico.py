"""
IL3.2: Cache Semantico para LLMs
=================================
Cache inteligente que usa similitud coseno (TF) para reutilizar
respuestas de consultas semanticamente similares. Incluye TTL
para mantener las respuestas actualizadas, estimacion real de
tokens via tiktoken y registro de ahorros.

Integrado con:
  - agent_bancoestado.py (CLI)
  - app.py (Web)
  - herramientas/observability.py (metricas de ahorro)
"""

import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


def estimar_tokens(texto: str) -> int:
    """Estima el numero de tokens de un texto usando tiktoken (cl100k_base)."""
    try:
        import tiktoken
        codificador = tiktoken.get_encoding("cl100k_base")
        return len(codificador.encode(texto))
    except Exception:
        return len(texto.split()) * 2


@dataclass
class EntradaCache:
    consulta: str
    respuesta: str
    timestamp: float
    ttl_segundos: float
    tokens_ahorrados: int = 0
    accesos: int = 0

    def esta_vigente(self) -> bool:
        return (time.time() - self.timestamp) < self.ttl_segundos


class CacheSemantico:
    """Cache que usa similitud semantica (coseno TF) para encontrar respuestas previas."""

    def __init__(self, umbral_similitud: float = None, ttl_segundos: float = None):
        from herramientas.config import CACHE_UMBRAL_SIMILITUD, CACHE_TTL_SEGUNDOS
        self.umbral_similitud = umbral_similitud if umbral_similitud is not None else CACHE_UMBRAL_SIMILITUD
        self.ttl_segundos = ttl_segundos if ttl_segundos is not None else CACHE_TTL_SEGUNDOS
        self.entradas: list[EntradaCache] = []
        self.estadisticas = {
            "hits": 0,
            "misses": 0,
            "tokens_ahorrados_total": 0,
            "costo_ahorrado_usd": 0.0,
        }

    def _normalizar_texto(self, texto: str) -> str:
        texto = texto.lower().strip()
        texto = re.sub(r"[^\w\s]", "", texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto

    def _similitud_coseno(self, texto1: str, texto2: str) -> float:
        def _freq(t: str) -> dict:
            freq: dict[str, int] = defaultdict(int)
            for p in t.split():
                freq[p] += 1
            return freq

        t1 = self._normalizar_texto(texto1)
        t2 = self._normalizar_texto(texto2)
        freq1 = _freq(t1)
        freq2 = _freq(t2)

        todas = set(freq1.keys()) | set(freq2.keys())
        producto = sum(freq1.get(p, 0) * freq2.get(p, 0) for p in todas)
        mag1 = math.sqrt(sum(v**2 for v in freq1.values()))
        mag2 = math.sqrt(sum(v**2 for v in freq2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0
        return producto / (mag1 * mag2)

    def buscar(self, consulta: str) -> tuple[bool, Optional[str], float]:
        mejor_similitud = 0.0
        mejor_entrada: Optional[EntradaCache] = None

        for entrada in self.entradas:
            if not entrada.esta_vigente():
                continue
            similitud = self._similitud_coseno(consulta, entrada.consulta)
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_entrada = entrada

        if mejor_entrada and mejor_similitud >= self.umbral_similitud:
            mejor_entrada.accesos += 1
            self.estadisticas["hits"] += 1
            return True, mejor_entrada.respuesta, mejor_similitud

        self.estadisticas["misses"] += 1
        return False, None, mejor_similitud

    def guardar(self, consulta: str, respuesta: str, tokens_usados: int = 0):
        entrada = EntradaCache(
            consulta=consulta,
            respuesta=respuesta,
            timestamp=time.time(),
            ttl_segundos=self.ttl_segundos,
            tokens_ahorrados=tokens_usados,
        )
        self.entradas.append(entrada)

    def registrar_ahorro(self, tokens: int, costo_por_1k: float = None):
        if costo_por_1k is None:
            from herramientas.config import COSTO_PROMEDIO_POR_1K
            costo_por_1k = COSTO_PROMEDIO_POR_1K
        self.estadisticas["tokens_ahorrados_total"] += tokens
        self.estadisticas["costo_ahorrado_usd"] += (tokens / 1000) * costo_por_1k

    def limpiar_expirados(self) -> int:
        antes = len(self.entradas)
        self.entradas = [e for e in self.entradas if e.esta_vigente()]
        return antes - len(self.entradas)

    def obtener_estadisticas(self) -> dict:
        total = self.estadisticas["hits"] + self.estadisticas["misses"]
        tasa_hits = (self.estadisticas["hits"] / total * 100) if total > 0 else 0
        return {
            **self.estadisticas,
            "total_consultas": total,
            "tasa_hits": round(tasa_hits, 2),
            "entradas_activas": len([e for e in self.entradas if e.esta_vigente()]),
            "entradas_total": len(self.entradas),
        }
