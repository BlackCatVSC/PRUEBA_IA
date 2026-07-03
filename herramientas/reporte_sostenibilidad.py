"""
IL3.4: Reporte de Sostenibilidad, Dashboard y Deteccion de Anomalias
=====================================================================
Consolida metricas de IL3.1 (observabilidad), IL3.2 (cache/lotes)
e IL3.3 (seguridad) para generar:
  - Dashboard data JSON (IE5)
  - Deteccion de patrones y anomalias (IE4)
  - Informe tecnico HTML (IE8/IE9)

Sin hardcodeos: todos los umbrales son parametros de constructor.
"""

import json
import math
from datetime import datetime
from typing import Optional


class DetectorAnomalias:
    """Detecta patrones anormales en metricas de rendimiento mediante
    ventana deslizante y comparacion contra medias moviles.

    Uso:
        detector = DetectorAnomalias(ventana=20, factor_spike=2.5)
        detector.alimentar(latencia_ms=450.0, exitoso=True, cache_hit=False)
        anomalias = detector.analizar()
    """

    def __init__(self, ventana: int = 20, factor_spike: float = 2.5,
                 umbral_error_pct: float = 20.0, umbral_cache_drop_pct: float = 50.0):
        self.ventana = ventana
        self.factor_spike = factor_spike
        self.umbral_error_pct = umbral_error_pct
        self.umbral_cache_drop_pct = umbral_cache_drop_pct

        self.latencias: list[float] = []
        self.errores: list[bool] = []
        self.cache_hits: list[bool] = []
        self.alertas: list[dict] = []

    def alimentar(self, latencia_ms: float, exitoso: bool, cache_hit: bool) -> None:
        self.latencias.append(latencia_ms)
        self.errores.append(not exitoso)
        self.cache_hits.append(cache_hit)

        if len(self.latencias) > self.ventana:
            self.latencias.pop(0)
            self.errores.pop(0)
            self.cache_hits.pop(0)

    def analizar(self) -> list[dict]:
        self.alertas = []
        if len(self.latencias) < 3:
            return self.alertas

        media_latencia = sum(self.latencias) / len(self.latencias)
        ultima_latencia = self.latencias[-1]

        if media_latencia > 0 and ultima_latencia > media_latencia * self.factor_spike:
            self.alertas.append({
                "tipo": "LATENCIA_ANOMALA",
                "severidad": "ALTA",
                "mensaje": f"Latencia {ultima_latencia:.0f}ms supera {self.factor_spike}x la media ({media_latencia:.0f}ms)",
                "timestamp": datetime.now().isoformat(),
            })

        recientes = self.errores[-min(5, len(self.errores)):]
        tasa_error_reciente = (sum(1 for e in recientes if e) / len(recientes)) * 100
        if tasa_error_reciente > self.umbral_error_pct:
            self.alertas.append({
                "tipo": "TASA_ERROR_ELEVADA",
                "severidad": "CRITICA",
                "mensaje": f"Tasa de error {tasa_error_reciente:.1f}% supera umbral {self.umbral_error_pct}%",
                "timestamp": datetime.now().isoformat(),
            })

        if len(self.cache_hits) >= 5:
            tasa_cache = (sum(1 for h in self.cache_hits if h) / len(self.cache_hits)) * 100
            if tasa_cache < self.umbral_cache_drop_pct:
                self.alertas.append({
                    "tipo": "CAIDA_CACHE",
                    "severidad": "MEDIA",
                    "mensaje": f"Tasa de cache {tasa_cache:.1f}% bajo umbral {self.umbral_cache_drop_pct}%",
                    "timestamp": datetime.now().isoformat(),
                })

        return self.alertas

    def resumen(self) -> dict:
        if not self.latencias:
            return {"estado": "sin_datos"}
        return {
            "muestras": len(self.latencias),
            "latencia_promedio_ms": round(sum(self.latencias) / len(self.latencias), 2),
            "tasa_error_pct": round((sum(1 for e in self.errores if e) / len(self.errores)) * 100, 2),
            "tasa_cache_pct": round((sum(1 for h in self.cache_hits if h) / len(self.cache_hits)) * 100, 2),
            "alertas_activas": len(self.alertas),
            "ultimas_alertas": self.alertas[-5:],
        }


class ReporteSostenibilidad:
    """Consolida todas las metricas del sistema en un unico reporte
    para dashboard (JSON) e informe tecnico (HTML).

    Uso:
        reporte = ReporteSostenibilidad(agente_obs, cache, seguridad, detector, procesador_lotes)
        data = reporte.dashboard_data()        # para /api/dashboard/data
        html = reporte.generar_informe_html()  # para /api/informe
    """

    def __init__(self, agente_obs, cache, seguridad, detector: DetectorAnomalias,
                 procesador_lotes=None):
        self.agente_obs = agente_obs
        self.cache = cache
        self.seguridad = seguridad
        self.detector = detector
        self.procesador_lotes = procesador_lotes

    def dashboard_data(self) -> dict:
        obs_metrics = self.agente_obs.metricas.resumen()
        cache_stats = self.cache.obtener_estadisticas()
        seguridad_metrics = self.seguridad.obtener_metricas()
        anomalias = self.detector.resumen()

        registros_obs = self.agente_obs.metricas.registros
        timeline = [
            {
                "timestamp": r.timestamp,
                "tiempo_respuesta_ms": r.tiempo_respuesta_ms,
                "tokens_entrada": r.tokens_entrada,
                "tokens_salida": r.tokens_salida,
                "exitoso": r.exitoso,
                "modelo": r.modelo,
            }
            for r in registros_obs
        ]

        batch_summary = {}
        if self.procesador_lotes is not None:
            batch_summary = self.procesador_lotes.obtener_resumen()

        return {
            "generado": datetime.now().isoformat(),
            "observabilidad": {
                "resumen": obs_metrics,
                "timeline": timeline[-50:],
            },
            "cache": cache_stats,
            "seguridad": seguridad_metrics,
            "anomalias": anomalias,
            "procesador_lotes": batch_summary,
            "modelos_utilizados": list(set(r.modelo for r in registros_obs)),
        }

    def generar_informe_html(self) -> str:
        data = self.dashboard_data()
        obs = data["observabilidad"]["resumen"]
        cache_stats = data["cache"]
        seguridad_stats = data["seguridad"]
        anomalias = data["anomalias"]

        filas_timeline = ""
        for r in data["observabilidad"]["timeline"][-20:]:
            estado = "OK" if r["exitoso"] else "ERROR"
            filas_timeline += (
                f"<tr>"
                f"<td>{r['timestamp'][:19]}</td>"
                f"<td>{r['modelo']}</td>"
                f"<td>{r['tiempo_respuesta_ms']:.0f}ms</td>"
                f"<td>{r['tokens_entrada']}</td>"
                f"<td>{r['tokens_salida']}</td>"
                f"<td>{estado}</td>"
                f"</tr>"
            )

        alertas_html = ""
        for a in anomalias.get("ultimas_alertas", []):
            alertas_html += (
                f"<tr><td>{a['tipo']}</td><td>{a['severidad']}</td>"
                f"<td>{a['mensaje']}</td><td>{a['timestamp'][:19]}</td></tr>"
            )

        total_cache = cache_stats.get("total_consultas", 0)
        tasa_cache = cache_stats.get("tasa_hits", 0)

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Informe Tecnico — BancoEstado Agente IA</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
  .container {{ max-width: 900px; margin: 20px auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .header {{ background: #0066cc; color: white; padding: 24px; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .header p {{ margin: 4px 0 0; font-size: 14px; opacity: 0.9; }}
  .body {{ padding: 24px; }}
  h2 {{ color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 6px; margin-top: 28px; }}
  .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 16px 0; }}
  .metric-card {{ background: #f8f9fb; border-radius: 8px; padding: 16px; text-align: center; }}
  .metric-card .value {{ font-size: 28px; font-weight: bold; color: #0066cc; }}
  .metric-card .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
  th {{ background: #f0f0f0; padding: 8px; text-align: left; border: 1px solid #ddd; }}
  td {{ padding: 6px 8px; border: 1px solid #ddd; }}
  .footer {{ font-size: 11px; color: #999; text-align: center; padding: 16px; }}
  .anomaly-severity-CRITICA {{ background: #ffe0e0; }}
  .anomaly-severity-ALTA {{ background: #fff3e0; }}
  .anomaly-severity-MEDIA {{ background: #fffde0; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>Informe Tecnico de Sostenibilidad</h1>
  <p>BancoEstado — Asistente Virtual con IA | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
<div class="body">

<h2>1. Resumen Ejecutivo</h2>
<p>Este informe consolida las metricas de rendimiento, escalabilidad, seguridad y sostenibilidad
del agente de IA de BancoEstado, implementando los indicadores de evaluacion IE1 a IE9.</p>

<h2>2. Metricas de Rendimiento (IE1, IE2)</h2>
<div class="metric-grid">
  <div class="metric-card">
    <div class="value">{obs.get('total_peticiones', 0)}</div>
    <div class="label">Total Peticiones</div>
  </div>
  <div class="metric-card">
    <div class="value">{obs.get('tiempo_promedio_ms', 0):.0f}ms</div>
    <div class="label">Latencia Promedio</div>
  </div>
  <div class="metric-card">
    <div class="value">{obs.get('tasa_errores_pct', 0):.1f}%</div>
    <div class="label">Tasa de Errores</div>
  </div>
  <div class="metric-card">
    <div class="value">{obs.get('total_tokens', 0):,}</div>
    <div class="label">Tokens Totales</div>
  </div>
  <div class="metric-card">
    <div class="value">{obs.get('tiempo_maximo_ms', 0):.0f}ms</div>
    <div class="label">Latencia Maxima</div>
  </div>
  <div class="metric-card">
    <div class="value">{obs.get('tokens_promedio_por_peticion', 0):.0f}</div>
    <div class="label">Tokens / Peticion</div>
  </div>
</div>

<h2>3. Cache Semantico (IE7 — Escalabilidad)</h2>
<div class="metric-grid">
  <div class="metric-card">
    <div class="value">{tasa_cache:.1f}%</div>
    <div class="label">Tasa de Cache Hits</div>
  </div>
  <div class="metric-card">
    <div class="value">{cache_stats.get('tokens_ahorrados_total', 0):,}</div>
    <div class="label">Tokens Ahorrados</div>
  </div>
  <div class="metric-card">
    <div class="value">${cache_stats.get('costo_ahorrado_usd', 0):.4f}</div>
    <div class="label">Costo Ahorrado (USD)</div>
  </div>
</div>

<h2>4. Seguridad (IE6)</h2>
<table>
<tr><th>Metrica</th><th>Valor</th></tr>
<tr><td>Total Validaciones</td><td>{seguridad_stats.get('total_validaciones', 0)}</td></tr>
<tr><td>Bloqueos por Inyeccion</td><td>{seguridad_stats.get('bloqueados_inyeccion', 0)}</td></tr>
<tr><td>Bloqueos por Filtro Etico</td><td>{seguridad_stats.get('bloqueados_etico', 0)}</td></tr>
<tr><td>Bloqueos por Rate Limit</td><td>{seguridad_stats.get('bloqueados_rate_limit', 0)}</td></tr>
<tr><td>Bloqueos Semanticos</td><td>{seguridad_stats.get('bloqueados_semantico', 0)}</td></tr>
<tr><td>PII Detectados (Input)</td><td>{seguridad_stats.get('pii_detectados_input', 0)}</td></tr>
<tr><td>PII Detectados (Output)</td><td>{seguridad_stats.get('pii_detectados_output', 0)}</td></tr>
<tr><td>Similitud Coseno Promedio</td><td>{seguridad_stats.get('similitud_coseno_promedio', 0)}</td></tr>
<tr><td>Alertas Baja Similitud</td><td>{seguridad_stats.get('baja_similitud_salida', 0)}</td></tr>
</table>

<h2>5. Procesador de Lotes (IE7 — Escalabilidad)</h2>
<table>
<tr><th>Metrica</th><th>Valor</th></tr>
<tr><td>Total Procesadas</td><td>{data['procesador_lotes'].get('total_procesadas', 0)}</td></tr>
<tr><td>Completadas</td><td>{data['procesador_lotes'].get('completadas', 0)}</td></tr>
<tr><td>Errores</td><td>{data['procesador_lotes'].get('errores', 0)}</td></tr>
<tr><td>Pendientes en Cola</td><td>{data['procesador_lotes'].get('pendientes', 0)}</td></tr>
<tr><td>Latencia Promedio Lote</td><td>{data['procesador_lotes'].get('latencia_promedio_ms', 0):.0f}ms</td></tr>
</table>

<h2>5. Procesador de Lotes (IE7 — Escalabilidad)</h2>
<table>
<tr><th>Metrica</th><th>Valor</th></tr>
<tr><td>Total Procesadas</td><td>{data['procesador_lotes'].get('total_procesadas', 0)}</td></tr>
<tr><td>Completadas</td><td>{data['procesador_lotes'].get('completadas', 0)}</td></tr>
<tr><td>Errores</td><td>{data['procesador_lotes'].get('errores', 0)}</td></tr>
<tr><td>Pendientes en Cola</td><td>{data['procesador_lotes'].get('pendientes', 0)}</td></tr>
<tr><td>Latencia Promedio Lote</td><td>{data['procesador_lotes'].get('latencia_promedio_ms', 0):.0f}ms</td></tr>
</table>

<h2>6. Deteccion de Anomalias (IE4)</h2>
<p>Alertas activas: {anomalias.get('alertas_activas', 0)}</p>
<table>
<tr><th>Tipo</th><th>Severidad</th><th>Mensaje</th><th>Timestamp</th></tr>
{alertas_html if alertas_html else '<tr><td colspan="4">Sin anomalias detectadas</td></tr>'}
</table>

<h2>7. Timeline de Peticiones (IE3)</h2>
<table>
<tr><th>Timestamp</th><th>Modelo</th><th>Latencia</th><th>Tokens In</th><th>Tokens Out</th><th>Estado</th></tr>
{filas_timeline if filas_timeline else '<tr><td colspan="6">Sin peticiones registradas</td></tr>'}
</table>

<h2>8. Conclusiones y Recomendaciones (IE7)</h2>
<ul>
<li><strong>Latencia:</strong> Promedio de {obs.get('tiempo_promedio_ms', 0):.0f}ms.
{'Dentro de parametros aceptables (< 2s).' if obs.get('tiempo_promedio_ms', 9999) < 2000 else 'Requiere optimizacion.'}</li>
<li><strong>Cache:</strong> Tasa de hits del {tasa_cache:.1f}%.
{'Efectivo en reduccion de costos.' if tasa_cache > 30 else 'Se recomienda ajustar umbral de similitud para mejorar tasa de hits.'}</li>
<li><strong>Errores:</strong> Tasa del {obs.get('tasa_errores_pct', 0):.1f}%.
{'Dentro de margen aceptable.' if obs.get('tasa_errores_pct', 100) < 10 else 'Investigar causas de errores frecuentes.'}</li>
<li><strong>Seguridad:</strong> {seguridad_stats.get('total_validaciones', 0)} validaciones realizadas.
El sistema bloquea proactivamente inyecciones, contenido no etico y PII.</li>
</ul>

</div>
<div class="footer">Generado automaticamente por el modulo IL3.4 — ReporteSostenibilidad | BancoEstado Asistente Virtual</div>
</div>
</body>
</html>"""
        return html
