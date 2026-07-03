"""Similitud de coseno: compara respuestas del agente vs respuestas finales al usuario."""
import math
import re
from collections import Counter
from typing import Optional


class CalculadorSimilitud:
    """Calcula la similitud de coseno entre dos textos.

    Usa un enfoque de vectorizacion TF (term frequency) puro en Python,
    sin dependencias externas como numpy o scikit-learn.
    Opcionalmente puede usar embeddings de OpenAI si se proporciona un LLM.
    """

    _PATRON_PALABRAS = re.compile(r'\b[a-záéíóúüñ]{2,}\b')

    def __init__(self, llm=None, umbral_baja_similitud: float = 0.85):
        self._llm = llm
        self.umbral_baja_similitud = umbral_baja_similitud

    # ─── Tokenizacion y vectorizacion ──────────────────────────

    @staticmethod
    def _tokenizar(texto: str) -> list:
        """Tokeniza un texto en palabras normalizadas (minusculas, >= 2 chars)."""
        if not texto:
            return []
        normalizado = texto.lower()
        return CalculadorSimilitud._PATRON_PALABRAS.findall(normalizado)

    @staticmethod
    def _vectorizar(texto: str) -> dict:
        """Convierte texto en un vector de frecuencias de terminos (TF)."""
        tokens = CalculadorSimilitud._tokenizar(texto)
        total = len(tokens) if tokens else 1
        tf = {}
        for token, count in Counter(tokens).items():
            tf[token] = count / total
        return tf

    # ─── Similitud de coseno basada en TF ───────────────────────

    def similitud_coseno(self, texto_a: str, texto_b: str) -> float:
        """Calcula la similitud de coseno entre dos textos usando TF.

        Returns un float entre 0.0 (completamente distintos) y 1.0 (identicos).
        Si ambos textos son vacios, retorna 1.0.
        Si uno es vacio, retorna 0.0.
        """
        if not texto_a and not texto_b:
            return 1.0
        if not texto_a or not texto_b:
            return 0.0

        vec_a = self._vectorizar(texto_a)
        vec_b = self._vectorizar(texto_b)

        todas_las_palabras = set(vec_a.keys()) | set(vec_b.keys())

        producto_punto = 0.0
        norma_a = 0.0
        norma_b = 0.0

        for palabra in todas_las_palabras:
            va = vec_a.get(palabra, 0.0)
            vb = vec_b.get(palabra, 0.0)
            producto_punto += va * vb
            norma_a += va * va
            norma_b += vb * vb

        if norma_a == 0.0 or norma_b == 0.0:
            return 0.0

        return producto_punto / (math.sqrt(norma_a) * math.sqrt(norma_b))

    # ─── Similitud via embeddings de OpenAI (opcional) ──────────

    def similitud_embeddings(self, texto_a: str, texto_b: str) -> Optional[float]:
        """Calcula similitud de coseno usando embeddings del LLM (OpenAI).

        Requiere que se haya pasado un LLM en el constructor.
        Retorna None si el LLM no esta disponible o falla la llamada.
        """
        if self._llm is None:
            return None

        try:
            emb_a = self._obtener_embedding(texto_a)
            emb_b = self._obtener_embedding(texto_b)
            if emb_a is None or emb_b is None:
                return None
            return self._coseno_vectores(emb_a, emb_b)
        except Exception:
            return None

    def _obtener_embedding(self, texto: str) -> Optional[list]:
        """Obtiene el embedding de un texto usando el cliente OpenAI subyacente."""
        if self._llm is None or not texto:
            return None
        try:
            cliente = getattr(self._llm, 'client', None)
            if cliente is None:
                return None
            resp = cliente.embeddings.create(
                model="text-embedding-3-small",
                input=texto[:8000],
            )
            return resp.data[0].embedding
        except Exception:
            return None

    @staticmethod
    def _coseno_vectores(a: list, b: list) -> float:
        """Calcula coseno entre dos vectores de floats."""
        if len(a) != len(b):
            return 0.0
        producto = sum(x * y for x, y in zip(a, b))
        norma_a = math.sqrt(sum(x * x for x in a))
        norma_b = math.sqrt(sum(y * y for y in b))
        if norma_a == 0.0 or norma_b == 0.0:
            return 0.0
        return producto / (norma_a * norma_b)

    # ─── Metodo principal de comparacion ────────────────────────

    def comparar(self, texto_a: str, texto_b: str) -> dict:
        """Compara dos textos y retorna metrica completa de similitud.

        Args:
            texto_a: texto original / respuesta cruda del agente
            texto_b: texto a comparar / respuesta final al usuario

        Returns:
            dict con:
                - similitud_coseno: float (0.0 a 1.0)
                - metodo: 'tf' o 'embeddings'
                - baja_similitud: bool (True si < umbral_baja_similitud)
                - longitud_a: int
                - longitud_b: int
        """
        similitud = self.similitud_coseno(texto_a, texto_b)
        metodo = "tf"

        embedding_sim = self.similitud_embeddings(texto_a, texto_b)
        if embedding_sim is not None:
            similitud = embedding_sim
            metodo = "embeddings"

        return {
            "similitud_coseno": round(similitud, 4),
            "metodo": metodo,
            "baja_similitud": similitud < self.umbral_baja_similitud,
            "longitud_a": len(texto_a) if texto_a else 0,
            "longitud_b": len(texto_b) if texto_b else 0,
        }

    def es_baja_similitud(self, texto_a: str, texto_b: str) -> bool:
        """Retorna True si la similitud entre los textos esta por debajo del umbral."""
        if not texto_a or not texto_b:
            return True if texto_a != texto_b else False
        similitud = self.similitud_coseno(texto_a, texto_b)
        return similitud < self.umbral_baja_similitud
