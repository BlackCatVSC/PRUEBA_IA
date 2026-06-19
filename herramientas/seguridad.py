"""Seguridad: validacion de entrada, deteccion PII, filtro etico, rate limiter y validador de salida."""
import re
import time
import json
import unicodedata
from datetime import datetime
from typing import Optional

# ─── MAPA DE CARACTERES ESPECIALES Y LEETSPEAK ───────────────
# Caracteres que NO se descomponen con NFKD y son usados para bypass
MAPA_NORMALIZACION = {
    '\u00F8': 'o',  # ø
    '\u00D8': 'O',  # Ø
    '\u0142': 'l',  # ł
    '\u0141': 'L',  # Ł
    '\u0111': 'd',  # đ
    '\u0110': 'D',  # Đ
    '\u014B': 'n',  # ŋ
    '\u014A': 'N',  # Ŋ
    '\u0153': 'oe', # œ
    '\u0152': 'OE', # Œ
    '\u00FE': 'th', # þ
    '\u00DE': 'TH', # Þ
    '\u00DF': 'ss', # ß
}

# Leetspeak: numeros y simbolos comunes (solo mapeo 1:1 para deteccion segura)
# Nota: solo se aplica en la capa de DETECCION, NO en el texto sanitizado
MAPA_LEETSPEAK = {
    '4': 'a', '@': 'a',
    '3': 'e',
    '1': 'i', '!': 'i',
    '0': 'o',
    '5': 's', '$': 's',
    '7': 't',
    '2': 'z',
}

# ─── PATRONES PII ────────────────────────────────────────────
PATRON_RUT = re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}[-]?[\dkK]\b')
PATRON_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PATRON_TELEFONO_CL = re.compile(r'\b(\+?56)?\s*0?9\s*\d{4}\s*\d{4}\b')
PATRON_TARJETA = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')

PII_PATRONES = {
    "RUT": PATRON_RUT,
    "EMAIL": PATRON_EMAIL,
    "TELEFONO": PATRON_TELEFONO_CL,
    "TARJETA": PATRON_TARJETA,
}

# ─── CATEGORIAS DE FILTRO ETICO ──────────────────────────────
CATEGORIAS_RESTRINGIDAS = {
    "violencia": {
        "palabras": ["mata", "matar", "muere", "bomba", "atentado", "arma", "asesinato", "asesinar"],
        "motivo": "Contenido violento no permitido",
    },
    "contenido_ilegal": {
        "palabras": ["hackear", "phishing", "estafa", "fraude", "suplantar", "clonar tarjeta", "robar cuenta"],
        "motivo": "Actividad ilegal no permitida",
    },
    "manipulacion": {
        "palabras": [
            "ignora.*instruccion", "ignora.*indicacion",
            "olvida.*instruccion", "olvida.*indicacion",
            "eres un ai", "eres un robot", "eres una ia",
            "actua como si", "simula ser", "dame acceso",
            "cambia mi saldo", "modifica mi saldo", "busca vulnerabilidad",
        ],
        "motivo": "Intento de manipulacion del asistente detectado",
    },
    "prompt_leak": {
        "palabras": [
            "system prompt", "prompt de sistema",
            "instrucciones de sistema", "instruccion de sistema",
            "instrucciones originales", "instruccion original",
            "reglas de seguridad",
            "dump.*configuracion", "dump.*config",
            "prompt.*json", "prompt en json",
            "lo que te dijeron",
            "tu prompt",
        ],
        "motivo": "Intento de extraccion de configuracion del asistente",
    },
}

# ─── PATRONES DE INYECCION DE PROMPTS ────────────────────────
PATRONES_INYECCION = [
    # Espanol
    r'ignora\s+(las\s+)?instrucciones',
    r'ignora\s+(las\s+)?indicaciones',
    r'olvida\s+(todas\s+)?las\s+(instrucciones|indicaciones)',
    r'eres\s+un\s+(ai|robot|asistente|ia)',
    r'simula\s+ser',
    r'actua\s+como\s+si',
    r'dame\s+(tu\s+)?(contraseña|contrasena|password|clave|token)',
    r'revela\s+(tu\s+)?(contraseña|contrasena|password|clave|token)',
    r'codigo\s+de\s+seguridad',
    r'token\s+de\s+seguridad',
    r'(token|password|clave)\s+de\s+(seguridad|acceso)',
    r'(muestrame|dime|cual\s+es).*(tu\s+)?(token|password|clave|contrasena)',
    # Ingles
    r'ignore\s+(all\s+)?(previous\s+)?instructions',
    r'forget\s+(all\s+)?(previous\s+)?(instructions|restrictions)',
    r'act\s+as\s+if',
    r'give\s+me\s+(your\s+)?(password|passwords|key|keys|token|tokens|credentials)',
    r'reveal\s+(your\s+)?(instructions|password|prompt|config)',
    r'show\s+me\s+(your\s+)?(prompt|instructions|config)',
    r'repeat\s+(your\s+)?(prompt|instructions)',
    r'you\s+are\s+(now\s+)?(a\s+)?(free\s+)?(ai|robot|assistant)',
    r'no\s+(rules|restrictions|limits|boundaries)',
    r'reveal.*(instructions|password|prompt|config|secrets)',
    r'(api|secret|private)\s+(key|keys|token|tokens|credentials)',
    r'(give|show|send|share)\s+(me\s+)?(your\s+)?(api|secret|private)',
    r'(credentials|password|passwords|secret)\s*(extraction|leak|dump)',
    r'need\s+(your\s+)?(credentials|password|access|keys|database)',
    # Codigo/inyeccion
    r'eval\s*\(',
    r'exec\s*\(',
    r'__import__\s*\(',
    r'subprocess',
    r'os\.system',
    r'open\s*\(',
]

LIMITE_LONGITUD_INPUT = 4000
LIMITE_LONGITUD_OUTPUT = 10000
MAX_PETICIONES_POR_VENTANA = 30
VENTANA_SEGUNDOS = 60


# ====================================================================
# 1. DETECCION Y SANITIZACION DE PII
# ====================================================================

class DetectorPII:
    """Detecta informacion de identificacion personal en textos."""

    TIPOS = {
        "RUT": {"label": "RUT", "reemplazo": "[RUT_REDACTADO]", "patron": PATRON_RUT},
        "EMAIL": {"label": "EMAIL", "reemplazo": "[EMAIL_REDACTADO]", "patron": PATRON_EMAIL},
        "TELEFONO": {"label": "TELEFONO", "reemplazo": "[TELEFONO_REDACTADO]", "patron": PATRON_TELEFONO_CL},
        "TARJETA": {"label": "TARJETA", "reemplazo": "[TARJETA_REDACTADO]", "patron": PATRON_TARJETA},
    }

    @classmethod
    def detectar(cls, texto: str) -> list:
        """Retorna lista de PII detectados con tipo y posicion."""
        encontrados = []
        for tipo, config in cls.TIPOS.items():
            for match in config["patron"].finditer(texto):
                encontrados.append({
                    "tipo": tipo,
                    "valor": match.group(),
                    "inicio": match.start(),
                    "fin": match.end(),
                })
        return encontrados

    @classmethod
    def sanitizar(cls, texto: str, tipos_a_redactar: Optional[list] = None) -> str:
        """Reemplaza PII con marcadores."""
        if tipos_a_redactar is None:
            tipos_a_redactar = list(cls.TIPOS.keys())
        resultado = texto
        for tipo in tipos_a_redactar:
            config = cls.TIPOS.get(tipo)
            if config:
                resultado = config["patron"].sub(config["reemplazo"], resultado)
        return resultado

    @classmethod
    def tiene_pii(cls, texto: str) -> bool:
        """Verifica si el texto contiene algun PII."""
        for config in cls.TIPOS.values():
            if config["patron"].search(texto):
                return True
        return False


# ====================================================================
# 2. SANITIZACION DE ENTRADA
# ====================================================================

class SanitizadorEntrada:
    """Valida y sanitiza la entrada del usuario."""

    @staticmethod
    def _normalizar(texto: str) -> str:
        texto = unicodedata.normalize('NFKD', texto)
        return re.sub(r'[\u0300-\u036f]', '', texto)

    @staticmethod
    def _limpiar_zerowidth(texto: str) -> str:
        """Elimina caracteres zero-width e invisibles usados para bypass."""
        return re.sub(r'[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00AD\u2060\u2061\u2062\u2063\u2064]', '', texto)

    @staticmethod
    def _decodificar_leetspeak(texto: str) -> str:
        """Decodifica leetspeak comun para deteccion."""
        resultado = []
        for char in texto:
            resultado.append(MAPA_LEETSPEAK.get(char, char))
        return ''.join(resultado)

    @staticmethod
    def _normalizar_especiales(texto: str) -> str:
        """Normaliza caracteres especiales que NFKD no descompone."""
        resultado = []
        for char in texto:
            resultado.append(MAPA_NORMALIZACION.get(char, char))
        return ''.join(resultado)

    @staticmethod
    def _colapsar_bypass_characters(texto: str) -> str:
        """Colapsa separadores comunes usados para evadir deteccion:
        guiones, asteriscos, puntos, virgulillas.
        i-g-n-o-r-a -> ignora, hack****ear -> hackear, es...tafa -> estafa"""
        return re.sub(r'(\w)[\-\.\*\~\+\#]+(?=\w)', r'\1', texto)

    @classmethod
    def _para_deteccion(cls, texto: str) -> str:
        """Normaliza texto para DETECCION (no para sanitizar output).
        Aplica: NFKD + combining marks + zero-width + especiales + leetspeak + colapso + ASCII + lowercase."""
        texto = cls._normalizar(texto)
        texto = cls._limpiar_zerowidth(texto)
        texto = cls._normalizar_especiales(texto)
        texto = cls._decodificar_leetspeak(texto)
        texto = cls._colapsar_bypass_characters(texto)
        texto = texto.encode('ascii', 'ignore').decode('ascii')
        return texto.lower()

    @classmethod
    def sanitizar(cls, mensaje: str) -> str:
        """Aplica sanitizacion basica: trim, normalizar, limitar longitud, remover chars control."""
        if not mensaje:
            return ""
        texto = mensaje.strip()
        texto = cls._normalizar(texto)
        texto = cls._limpiar_zerowidth(texto)
        texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
        if len(texto) > LIMITE_LONGITUD_INPUT:
            texto = texto[:LIMITE_LONGITUD_INPUT]
        return texto

    @classmethod
    def detectar_inyeccion(cls, mensaje: str) -> Optional[str]:
        """Detecta patrones de inyeccion de prompts. Retorna el patron que coincide o None."""
        mensaje_det = cls._para_deteccion(mensaje)
        for patron in PATRONES_INYECCION:
            if re.search(patron, mensaje_det):
                return patron
        return None

    @classmethod
    def validar_y_sanitizar(cls, mensaje: str) -> dict:
        """Validacion completa de entrada. Retorna dict con resultado."""
        original = mensaje
        sanitizado = cls.sanitizar(mensaje)

        if not sanitizado:
            return {"valido": False, "error": "Mensaje vacio", "sanitizado": "", "original": original}

        inyeccion = cls.detectar_inyeccion(sanitizado)
        if inyeccion:
            return {"valido": False, "error": f"Patron de inyeccion detectado", "sanitizado": sanitizado, "original": original, "patron": inyeccion}

        pii_detectada = DetectorPII.detectar(sanitizado)
        pii_sanitizado = DetectorPII.sanitizar(sanitizado) if pii_detectada else sanitizado

        return {
            "valido": True,
            "sanitizado": pii_sanitizado,
            "original": original,
            "pii_detectada": [p["tipo"] for p in pii_detectada],
            "tiene_pii": len(pii_detectada) > 0,
        }


# ====================================================================
# 3. FILTRO ETICO
# ====================================================================

class FiltroEtico:
    """Filtra mensajes del usuario bloqueando contenido problematico."""

    @staticmethod
    def _convertir_a_regex(termino: str) -> str:
        """Convierte un termino a regex: espacios entre palabras se vuelven .*"""
        partes = termino.split()
        if len(partes) <= 1:
            return termino
        return r'.*'.join(re.escape(p) for p in partes)

    @classmethod
    def clasificar(cls, mensaje: str) -> dict:
        """Clasifica un mensaje en categorias eticas.
        Usa la misma normalizacion de deteccion (leetspeak + especiales + zero-width)."""
        mensaje_det = SanitizadorEntrada._para_deteccion(mensaje)

        for categoria, config in CATEGORIAS_RESTRINGIDAS.items():
            for palabra in config["palabras"]:
                palabra_norm = unicodedata.normalize('NFKD', palabra.lower())
                palabra_norm = palabra_norm.encode('ascii', 'ignore').decode('ascii')

                if ".*" in palabra_norm:
                    if re.search(palabra_norm, mensaje_det):
                        return {
                            "permitido": False,
                            "categoria": categoria,
                            "motivo": config["motivo"],
                            "termino_detectado": palabra,
                        }
                elif " " in palabra_norm:
                    patron_regex = cls._convertir_a_regex(palabra_norm)
                    if re.search(patron_regex, mensaje_det):
                        return {
                            "permitido": False,
                            "categoria": categoria,
                            "motivo": config["motivo"],
                            "termino_detectado": palabra,
                        }
                elif palabra_norm in mensaje_det:
                    return {
                        "permitido": False,
                        "categoria": categoria,
                        "motivo": config["motivo"],
                        "termino_detectado": palabra,
                    }
        return {"permitido": True, "categoria": None, "motivo": ""}


# ====================================================================
# 4. RATE LIMITER
# ====================================================================

class RateLimiter:
    """Rate limiter con ventana deslizante por clave (IP/session)."""

    def __init__(self, max_peticiones: int = MAX_PETICIONES_POR_VENTANA, ventana_segundos: int = VENTANA_SEGUNDOS):
        self.max_peticiones = max_peticiones
        self.ventana_segundos = ventana_segundos
        self._historial: dict[str, list] = {}

    def permitir(self, key: str) -> dict:
        ahora = time.time()
        if key not in self._historial:
            self._historial[key] = []
        self._historial[key] = [t for t in self._historial[key] if ahora - t < self.ventana_segundos]
        if len(self._historial[key]) >= self.max_peticiones:
            tiempo_restante = int(self.ventana_segundos - (ahora - self._historial[key][0]))
            return {"permitido": False, "tiempo_restante": tiempo_restante, "motivo": f"Demasiadas solicitudes. Espera {tiempo_restante}s"}
        self._historial[key].append(ahora)
        return {"permitido": True, "tiempo_restante": 0, "contador": len(self._historial[key])}

    def limpiar(self, key: str):
        self._historial.pop(key, None)


# ====================================================================
# 5. VALIDADOR DE SALIDA
# ====================================================================

class ValidadorSalida:
    """Valida la respuesta del agente antes de enviarla al usuario."""

    @classmethod
    def validar(cls, respuesta: str) -> dict:
        """Valida la respuesta del agente. Retorna dict con resultado."""
        if not respuesta:
            return {"valido": False, "error": "Respuesta vacia", "corregida": ""}

        pii_detectada = DetectorPII.detectar(respuesta)
        tiene_pii = len(pii_detectada) > 0

        respuesta_corregida = DetectorPII.sanitizar(respuesta) if tiene_pii else respuesta

        if len(respuesta_corregida) > LIMITE_LONGITUD_OUTPUT:
            respuesta_corregida = respuesta_corregida[:LIMITE_LONGITUD_OUTPUT]

        return {
            "valido": True,
            "corregida": respuesta_corregida,
            "tiene_pii": tiene_pii,
            "pii_detectada": [p["tipo"] for p in pii_detectada],
        }


# ====================================================================
# 6. ORQUESTADOR DE SEGURIDAD
# ====================================================================

class OrquestadorSeguridad:
    """Orquesta todas las capas de seguridad en un solo flujo."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.metricas = {
            "total_validaciones": 0,
            "bloqueados_inyeccion": 0,
            "bloqueados_etico": 0,
            "bloqueados_rate_limit": 0,
            "pii_detectados_input": 0,
            "pii_detectados_output": 0,
        }

    def validar_entrada(self, mensaje: str, rate_limit_key: str = "default") -> dict:
        """Flujo completo de validacion de entrada."""
        self.metricas["total_validaciones"] += 1

        rate = self.rate_limiter.permitir(rate_limit_key)
        if not rate["permitido"]:
            self.metricas["bloqueados_rate_limit"] += 1
            return {"permitido": False, "error": rate["motivo"], "codigo": "RATE_LIMIT"}

        sanitizado = SanitizadorEntrada.validar_y_sanitizar(mensaje)
        if not sanitizado["valido"]:
            self.metricas["bloqueados_inyeccion"] += 1
            return {"permitido": False, "error": sanitizado["error"], "codigo": "INYECCION"}

        etico = FiltroEtico.clasificar(sanitizado["sanitizado"])
        if not etico["permitido"]:
            self.metricas["bloqueados_etico"] += 1
            return {"permitido": False, "error": etico["motivo"], "codigo": "ETICO", "categoria": etico["categoria"]}

        if sanitizado["tiene_pii"]:
            self.metricas["pii_detectados_input"] += len(sanitizado["pii_detectada"])

        return {
            "permitido": True,
            "mensaje_sanitizado": sanitizado["sanitizado"],
            "pii_removida": sanitizado["tiene_pii"],
        }

    def validar_salida(self, respuesta: str) -> dict:
        """Flujo completo de validacion de salida."""
        validacion = ValidadorSalida.validar(respuesta)
        if validacion["tiene_pii"]:
            self.metricas["pii_detectados_output"] += len(validacion["pii_detectada"])
        return validacion

    def obtener_metricas(self) -> dict:
        return dict(self.metricas)
