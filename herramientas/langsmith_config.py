"""Configuracion centralizada de LangSmith para monitoreo y trazabilidad."""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ─── Variables de entorno ──────────────────────────────────────

LANGSMITH_TRACING = os.environ.get("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "default")
LANGSMITH_ENDPOINT = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

# Configurar variables que LangChain/LangSmith leen automaticamente
if LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGSMITH_ENDPOINT


class LangSmithConfig:
    """Provee callbacks y utilidades para tracing con LangSmith."""

    _cliente = None

    @classmethod
    def habilitado(cls) -> bool:
        return LANGSMITH_TRACING and bool(LANGSMITH_API_KEY)

    @classmethod
    def get_cliente(cls):
        """Retorna una instancia del cliente LangSmith (lazy init)."""
        if not cls.habilitado():
            return None
        if cls._cliente is None:
            try:
                from langsmith import Client
                cls._cliente = Client(
                    api_key=LANGSMITH_API_KEY,
                    api_url=LANGSMITH_ENDPOINT,
                )
            except Exception:
                return None
        return cls._cliente

    @classmethod
    def get_callbacks(cls, tags: Optional[list] = None, metadata: Optional[dict] = None) -> list:
        """Retorna una lista de callbacks configurados para LangSmith.

        Args:
            tags: Etiquetas para filtrar en la UI de LangSmith.
            metadata: Metadatos adicionales para enriquecer las trazas.

        Returns:
            Lista de callbacks (vacia si LangSmith no esta habilitado).
        """
        if not cls.habilitado():
            return []

        try:
            from langchain_core.tracers import LangChainTracer
            tracer = LangChainTracer(
                project_name=LANGSMITH_PROJECT,
            )
            return [tracer]
        except Exception:
            return []

    @classmethod
    def crear_metadata_run(
        cls,
        ambiente: str = "produccion",
        usuario: str = "anonimo",
        session_id: str = "",
        modo: str = "llm",
        extras: Optional[dict] = None,
    ) -> dict:
        """Crea metadata estandarizada para las trazas de LangSmith."""
        meta = {
            "ambiente": ambiente,
            "usuario": usuario,
            "session_id": session_id,
            "modo": modo,
            "proyecto": LANGSMITH_PROJECT,
        }
        if extras:
            meta.update(extras)
        return meta

    @classmethod
    def get_tags_base(cls, modulo: str = "general") -> list:
        """Tags base para filtrar en la UI de LangSmith."""
        tags = [
            f"modulo:{modulo}",
            f"proyecto:{LANGSMITH_PROJECT}",
        ]
        return tags


def traceable_si_habilitado(func=None, *, name: str = None, tags: list = None, metadata: dict = None):
    """Decorador @traceable condicional: solo traza si LangSmith esta habilitado.

    Uso:
        @traceable_si_habilitado(name="mi_funcion")
        def mi_funcion():
            ...
    """
    if not LangSmithConfig.habilitado():
        if func is not None:
            return func

        def decorator_noop(fn):
            return fn
        return decorator_noop

    try:
        from langsmith.run_helpers import traceable as _traceable

        if func is not None:
            kwargs = {}
            if name:
                kwargs["name"] = name
            if tags:
                kwargs["tags"] = tags
            if metadata:
                kwargs["metadata"] = metadata
            return _traceable(**kwargs)(func)

        def decorator(fn):
            kwargs = {}
            if name:
                kwargs["name"] = name
            if tags:
                kwargs["tags"] = tags
            if metadata:
                kwargs["metadata"] = metadata
            return _traceable(**kwargs)(fn)
        return decorator
    except ImportError:
        if func is not None:
            return func
        def decorator_noop(fn):
            return fn
        return decorator_noop


# ─── Estado de configuracion ───────────────────────────────────

def obtener_estado_configuracion() -> dict:
    """Retorna el estado actual de la configuracion LangSmith."""
    return {
        "habilitado": LangSmithConfig.habilitado(),
        "tracing": LANGSMITH_TRACING,
        "api_key_configurada": bool(LANGSMITH_API_KEY),
        "api_key_prefijo": LANGSMITH_API_KEY[:12] + "..." if LANGSMITH_API_KEY else "N/A",
        "proyecto": LANGSMITH_PROJECT,
        "endpoint": LANGSMITH_ENDPOINT,
    }


# ─── Envio de metricas custom a LangSmith ──────────────────────

def _enviar_feedback(key: str, score: float, comment: str = "",
                     run_id: str = None, tags: list = None):
    """Envia una metrica como feedback a un run de LangSmith."""
    if not LangSmithConfig.habilitado():
        return

    cliente = LangSmithConfig.get_cliente()
    if cliente is None:
        return

    try:
        cliente.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
    except Exception:
        pass


def _obtener_run_id_actual() -> str | None:
    """Intenta obtener el run_id del contexto @traceable activo."""
    try:
        from langsmith.run_helpers import get_current_run_tree
        run_tree = get_current_run_tree()
        if run_tree is not None:
            return str(run_tree.id)
    except Exception:
        pass
    return None

from herramientas.config import MODELO_POR_DEFECTO


def registrar_metricas_langsmith(
    latencia_ms: float,
    tokens_entrada: int,
    tokens_salida: int,
    exitoso: bool,
    modelo: str = None,
    cache_hit: bool = False,
    anomalias: list = None,
):
    """Envia las metricas del agente como feedback a LangSmith.

    Se llama despues de cada procesamiento LLM/demo.
    Si hay un trace activo (@traceable), se asocia a ese run.
    """
    if modelo is None:
        modelo = MODELO_POR_DEFECTO
    if not LangSmithConfig.habilitado():
        return

    run_id = _obtener_run_id_actual()

    _enviar_feedback("latencia_ms", round(latencia_ms, 2),
                     f"Latencia: {latencia_ms:.1f}ms", run_id)
    _enviar_feedback("tokens_entrada", float(tokens_entrada),
                     f"Input tokens: {tokens_entrada}", run_id)
    _enviar_feedback("tokens_salida", float(tokens_salida),
                     f"Output tokens: {tokens_salida}", run_id)
    _enviar_feedback("exitoso", 1.0 if exitoso else 0.0,
                     "Exito" if exitoso else "Error", run_id)
    _enviar_feedback("cache_hit", 1.0 if cache_hit else 0.0,
                     "Cache HIT" if cache_hit else "Cache MISS", run_id)
    _enviar_feedback("modelo", 0.0, modelo, run_id)

    if anomalias:
        for alerta in anomalias:
            _enviar_feedback(
                "anomalia", 0.0,
                f"[{alerta.get('severidad', '?')}] {alerta.get('mensaje', '')}",
                run_id,
            )
