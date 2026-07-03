# Informe Técnico — Asistente Virtual BancoEstado con IA

**Asignatura:** ISY0101 — Ingeniería de Soluciones con Inteligencia Artificial  
**Evaluación Final Transversal (EFT)**  
**Autores:** Luciano Garrido, Isidora Ayala  
**Fecha:** Julio 2026

---

## Resumen Ejecutivo

Este informe documenta el diseño, implementación y evaluación de un asistente virtual inteligente para BancoEstado, desarrollado con GPT-4o (GitHub Models API) y LangChain. El sistema integra 16 herramientas bancarias simuladas, tres estrategias de memoria conversacional, un planificador con clasificación de 14 intenciones, seis capas de seguridad en profundidad, y módulos de observabilidad, escalabilidad y sostenibilidad (IL3.1-IL3.4). Se incluye un dashboard interactivo con métricas en tiempo real, detección de anomalías, caché semántico, procesamiento por lotes con prioridad, informe técnico autogenerado y trazabilidad con LangSmith. El proyecto demuestra la viabilidad de agentes de IA en contextos financieros con criterios de seguridad, ética y eficiencia operativa.

---

## 1. Análisis del Caso Organizacional

### 1.1 Contexto

BancoEstado es la principal institución financiera estatal de Chile, con más de 13 millones de clientes. Sus canales de atención (sucursales, call center, web) enfrentan alta demanda de consultas recurrentes:

- Creación de cuentas (CuentaRUT, CuentaAhorros)
- Bloqueo y gestión de tarjetas por pérdida o robo
- Transferencias entre cuentas propias y a terceros
- Simulación y solicitud de créditos
- Consulta de sucursales, productos y horarios

### 1.2 Requerimientos

| Requerimiento | Descripción |
|---|---|
| Disponibilidad 24/7 | Atención automatizada sin depender de horarios de sucursal |
| Respuesta inmediata | Latencia menor a 5 segundos para consultas frecuentes |
| Seguridad multicapa | Protección contra inyección de prompts, filtro ético, detección de PII |
| Trazabilidad | Registro de cada interacción con métricas de rendimiento |
| Escalabilidad | Capacidad de manejar múltiples usuarios concurrentes |
| Sostenibilidad | Optimización de costos mediante caché y enrutamiento inteligente |

### 1.3 Desafíos

- La API real de BancoEstado es un sistema cerrado → se implementó una API simulada completa
- Los LLMs pueden alucinar o ser manipulados → 6 capas de defensa en profundidad
- Los costos de API escalan con el uso → caché semántico + procesamiento por lotes
- Se requiere monitoreo continuo → dashboard con métricas y detección de anomalías

---

## 2. Diseño de la Solución

### 2.1 Formulación de Prompts (IE1)

El system prompt define rol, reglas de negocio y restricciones:

```
Eres un asistente virtual de BancoEstado. Tu función es orientar a los clientes
con dudas sobre productos, cuentas, tarjetas, créditos y operaciones bancarias.
Usa las herramientas disponibles para consultar información y ejecutar operaciones.
Responde siempre en español de forma clara, amable y profesional.

REGLAS:
- Si el cliente reporta pérdida o robo de tarjeta, prioriza el bloqueo inmediato.
- Para créditos sobre $3.000.000, indica que se requiere verificación adicional.
- Para créditos sobre $5.000.000, indica que debe ir a sucursal.
- transferir funciona en AMBOS sentidos (RUT→Ahorros y Ahorros→RUT).
- NUNCA ofrezcas crear una cuenta sin verificar si ya existe.
```

**Archivo:** `agente_bancoestado.py:124-145`, `app.py:42-64`

### 2.2 Implementación de Pipelines RAG (IE2)

El sistema integra recuperación de información externa mediante la herramienta `buscar_wikipedia`, que consulta la API de Wikipedia en español para enriquecer respuestas con conocimiento general. Si bien no se implementó un pipeline RAG completo con embeddings y vector store, la arquitectura es extensible para incorporarlo.

**Archivo:** `herramientas/herramientas_bancoestado.py:140-148`

### 2.3 Diseño de Arquitectura (IE3)

```
┌──────────────────────────────────────────────────────────────────────┐
│                           USUARIO                                      │
│   ┌─────────────────────────┐   ┌──────────────────────────────┐     │
│   │  CLI (consola)          │   │  Web (Flask + HTML/CSS/JS)   │     │
│   │  agente_bancoestado.py  │   │  app.py + templates/static/  │     │
│   └───────────┬─────────────┘   └──────────────┬───────────────┘     │
└───────────────┼────────────────────────────────┼─────────────────────┘
                │                                │
                ▼                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  6 CAPAS DE SEGURIDAD (seguridad.py) — IL3.3                          │
│  Rate Limiter → Sanitizador → Inyección → Ético → Semántico → PII   │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CACHÉ SEMÁNTICO (IL3.2) + OBSERVABILIDAD (IL3.1)                    │
│  CacheSemantico (coseno TF) → si HIT, retorna sin llamar al LLM      │
│  AgenteObservable → mide latencia, tokens, éxito/fallo               │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PLANIFICADOR + ORQUESTADOR (planificador.py) — IL2.3                 │
│  14 intenciones → criticidad → pasos con dependencias                │
│  Toma de decisiones: riesgo transferencia, evaluación crédito        │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  AGENTE LANGSCHAIN — GPT-4o via GitHub Models API                     │
│  AgentExecutor + 16 herramientas @tool                                │
│  Memoria: Buffer | Window (k=4) | Summary                             │
│  ContextVar para RUT thread-safe                                      │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BANCOESTADO API SIMULADA + CIFRADO (bancoestado_api.py)              │
│  Fernet AES-128-CBC para datos en reposo                              │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DASHBOARD + INFORME + LANGMSITH (IL3.4)                              │
│  Dashboard.html (Chart.js) → 8 gráficos en tiempo real               │
│  /api/informe → HTML técnico autogenerado                             │
│  LangSmith → trazabilidad de cada ejecución                          │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.4 Justificación de Decisiones de Diseño (IE4)

| Decisión | Justificación |
|---|---|
| **LangChain sobre CrewAI** | CrewAI es incompatible con Python 3.14.5 (entorno del equipo). LangChain ofrece ecosistema maduro con `AgentExecutor`, `@tool` y tres tipos de memoria. |
| **GPT-4o como modelo principal** | Balance óptimo entre calidad de respuesta y latencia para un chatbot financiero. La arquitectura soporta enrutamiento futuro a GPT-4o-mini para consultas simples. |
| **Planificador offline propio** | Evita depender del LLM para clasificación de intenciones en modo demo. Usa palabras clave (0ms, sin costo) en vez de tokens del LLM. |
| **API bancaria simulada** | BancoEstado es un sistema cerrado. Una simulación completa permite demostrar todas las funcionalidades sin exponer datos reales. |
| **6 capas de seguridad** | Defensa en profundidad: cada capa agrega protección incremental. Capa 1-4 son determinísticas (regex, 0ms). Capa 5 es semántica con LLM (deep defense). Capa 6 valida salida (PII leakage). |
| **Caché semántico con coseno TF** | Reduce llamadas al LLM para consultas similares. Sin depender de embeddings externos. TTL de 1 hora mantiene respuestas actualizadas. |
| **Procesador de lotes con prioridad** | Bloqueos de tarjeta (CRÍTICA) se procesan antes que consultas de sucursales (BAJA). Heapq garantiza orden O(log n). |
| **Dashboard con Chart.js** | Visualización en tiempo real sin dependencias pesadas. CSP configurado para permitir CDN. Auto-refresh cada 30s. |
| **LangSmith para trazabilidad** | Cada ejecución del agente se traza automáticamente. Feedback custom: latencia, tokens, cache_hit, modelo, anomalías. |
| **ContextVar para RUT** | Aislamiento thread-safe en Flask multi-hilo. Evita condiciones de carrera entre requests concurrentes. |

---

## 3. Desarrollo del Agente Funcional

### 3.1 Herramientas Integradas (IE5)

16 herramientas decoradas con `@tool` de LangChain, cada una con JSON Schema para Function Calling:

| # | Herramienta | Tipo | Descripción |
|---|---|---|---|
| 1 | `consultar_saldo` | Consulta | Saldo de CuentaRUT o CuentaAhorros |
| 2 | `consultar_estado_cuenta` | Consulta | Estado completo con movimientos |
| 3 | `crear_cuenta_rut` | Escritura | Crea nueva CuentaRUT |
| 4 | `crear_cuenta_ahorros` | Escritura | Crea cuenta de ahorros |
| 5 | `bloquear_tarjeta` | Escritura | Bloqueo por pérdida/robo |
| 6 | `desbloquear_tarjeta` | Escritura | Desbloqueo de tarjeta |
| 7 | `simular_credito` | Razonamiento | Simulación con cuotas e intereses |
| 8 | `solicitar_credito` | Escritura | Solicitud formal con validaciones |
| 9 | `consultar_creditos` | Consulta | Lista créditos activos |
| 10 | `transferir` | Escritura | Transferencia entre cuentas |
| 11 | `simular_ahorro` | Razonamiento | Proyección de ahorro |
| 12 | `listar_sucursales` | Consulta | Sucursales con dirección |
| 13 | `consultar_productos` | Consulta | Productos disponibles |
| 14 | `actualizar_saldo` | Escritura | Depósito externo |
| 15 | `buscar_wikipedia` | Externa | Búsqueda en Wikipedia |
| 16 | `obtener_fecha_hora` | Utilidad | Fecha y hora actual |

**Archivo:** `herramientas/herramientas_bancoestado.py`

### 3.2 Configuración de Memoria (IE6)

Tres estrategias intercambiables en runtime (`/memoria buffer|window|summary`):

| Estrategia | Ventaja | Desventaja | Uso recomendado |
|---|---|---|---|
| `ConversationBufferMemory` | Contexto completo | Alto consumo de tokens | Conversaciones cortas |
| `ConversationBufferWindowMemory (k=4)` | Bajo consumo, contexto reciente | Pierde historia antigua | Consultas rápidas |
| `ConversationSummaryMemory` | Compresión inteligente | Depende del LLM para resumir | Sesiones prolongadas |

**Archivo:** `agente_bancoestado.py:96-175`

### 3.3 Estrategias de Planificación (IE7)

`Planificador` en `planificador.py`:

1. **Clasificación**: 14 categorías de intención por palabras clave
2. **Ordenamiento**: Por criticidad (alta → media → baja) y prioridad numérica
3. **Urgencia**: Si hay intenciones de criticidad "alta" (bloqueo de tarjeta), se marca `es_urgente=True`
4. **Pasos**: Cada herramienta única genera un paso, con dependencias resueltas

**Toma de Decisiones Adaptativa:**

- `evaluar_riesgo_transferencia(monto, saldo)`: RECHAZAR (>100%), REQUIERE VALIDACIÓN (>70%), ADVERTIR (>30%), APROBAR
- `evaluar_credito(monto, ingresos)`: RECHAZAR (>40% de ingresos), REVISAR (25-40%), RECOMENDAR

**Archivo:** `herramientas/planificador.py`

### 3.4 Documentación de la Orquestación (IE8)

El flujo de trabajo automatizado completo está documentado en el diagrama de la Sección 2.3. La orquestación entre componentes sigue el patrón:

```
Usuario → Seguridad (6 capas) → Caché semántico → Planificador → Agente LangChain (LLM + herramientas + memoria) → API Bancaria → Validación de salida → Respuesta
```

Cada componente es independiente y reemplazable, siguiendo el principio de responsabilidad única.

---

## 4. Observabilidad, Trazabilidad y Seguridad

### 4.1 Métricas de Observabilidad — IL3.1 (IE9)

Módulo `herramientas/observability.py`:

| Métrica | Descripción | IE |
|---|---|---|
| `tiempo_respuesta_ms` | Latencia de cada petición (promedio, min, max) | IE9 |
| `tokens_entrada` / `tokens_salida` | Tokens consumidos por el LLM (vía callback + fallback tiktoken) | IE9 |
| `tasa_errores_pct` | Porcentaje de peticiones fallidas | IE9 |
| `modelo` | Modelo utilizado (gpt-4o, cache, offline) | IE9 |
| `cache_hit` | Si la respuesta vino del caché semántico | IE9 |

**Endpoints:**
- `GET /api/observability/metrics` — JSON con todas las métricas y timeline
- `GET /api/dashboard/data` — Datos consolidados para el dashboard

**Dashboard interactivo** (`/dashboard`):
- 12 tarjetas de KPIs (peticiones, latencia, tasa caché, anomalías, tokens, errores, PII, similitud coseno, cola batch)
- 8 gráficos Chart.js: latencia (línea), tokens por modelo (dona), cache hits/misses (dona), bloqueos seguridad (barras), tokens in/out (barras), PII y similitud (barras), tasa errores (línea)
- Sección de alertas de anomalías con badges de severidad
- Auto-refresh cada 30 segundos

### 4.2 Análisis de Registros y Mejoras — IL3.2 + IL3.4 (IE10, IE12)

**Caché Semántico** (`herramientas/cache_semantico.py`):
- Similitud coseno TF entre consultas
- TTL configurable (1 hora por defecto)
- Registro de tokens y costo ahorrado
- Tasa de hits/misses en tiempo real

**Procesador de Lotes** (`herramientas/procesador_lotes.py`):
- Cola de prioridad con heap (`Prioridad`: CRITICA > ALTA > NORMAL > BAJA)
- Bloqueos de tarjeta = CRITICA, consultas de sucursales = BAJA
- Endpoint `POST /api/scalability/batch/process`

**Detección de Anomalías** (`herramientas/reporte_sostenibilidad.py`):
- Ventana deslizante de N muestras
- Detecta: latencia anómala (>2.5x media), tasa de error elevada (>20%), caída de caché (<50%)
- Alertas con severidad CRITICA/ALTA/MEDIA

**Informe Técnico Autogenerado** (`/api/informe`):
- HTML con todas las métricas consolidadas
- Secciones: rendimiento, caché, seguridad, anomalías, timeline, conclusiones
- Recomendaciones basadas en datos observados

**Trazabilidad LangSmith:**
- Cada ejecución del agente se traza automáticamente
- Feedback custom por trace: latencia_ms, tokens_entrada, tokens_salida, exitoso, cache_hit, modelo, anomalia
- `@traceable_si_habilitado` en funciones clave del CLI

### 4.3 Protocolos de Seguridad — IL3.3 (IE11)

6 capas de defensa en profundidad en `herramientas/seguridad.py`:

| Capa | Componente | Mecanismo |
|---|---|---|
| 1 | Rate Limiter | Ventana deslizante, 30 req/60s por IP/sesión |
| 2 | Sanitizador | NFKD, zero-width chars, Unicode confusables, leetspeak |
| 3 | Detección Inyección | 24 patrones regex ES+EN para prompt/code injection |
| 4 | Filtro Ético | 4 categorías: violencia, ilegal, manipulación, prompt leak |
| 5 | Clasificación Semántica | LLM multilingüe (degradación elegante sin LLM) |
| 6 | Validador Salida | Detección PII (RUT, email, teléfono, tarjeta) en respuestas |

**Cifrado en reposo:** Fernet AES-128-CBC para `datos_clientes.json`

**Testing:** `test_jailbreak.py` — 133 tests en 18 categorías (inyección, jailbreak, encoding bypass, leetspeak, zero-width, multi-lenguaje, PII, rate limit). Efectividad del 100%.

**Endpoints:**
- `GET /api/security/metrics` — Métricas de seguridad en JSON
- `GET /api/scalability/cache` — Estadísticas del caché
- `GET /api/scalability/batch/status` — Estado del procesador de lotes

---

## 5. Configuración y Ejecución

### 5.1 Variables de Entorno (`.env`)

```bash
GITHUB_TOKEN="tu_token"                  # Token de GitHub Models API
LANGSMITH_TRACING="true"                 # Activar trazabilidad LangSmith
LANGSMITH_API_KEY="tu_langsmith_key"     # API key de LangSmith
LANGSMITH_PROJECT="bancoestado"          # Proyecto en LangSmith

# IL3.x — Configuración avanzada (opcional, tiene valores por defecto)
LLM_MODELO_DEFECTO="gpt-4o"             # Modelo LLM principal
CACHE_UMBRAL_SIMILITUD="0.75"           # Umbral de similitud coseno
CACHE_TTL_SEGUNDOS="3600"               # TTL de entradas en caché
ANOMALIAS_VENTANA="20"                  # Ventana para detección de anomalías
ANOMALIAS_FACTOR_SPIKE="2.5"            # Factor multiplicador para spikes
```

### 5.2 Ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# CLI — Consola interactiva
python agente_bancoestado.py

# Web + Dashboard — Servidor Flask
python app.py
# Chat:        http://localhost:5000
# Dashboard:   http://localhost:5000/dashboard
# Informe:     http://localhost:5000/api/informe
```

---

## 6. Evidencias por Indicador de Evaluación

### Dimensión Encargo (Informe Escrito)

| IE | Indicador | Peso | Evidencia en el proyecto |
|----|-----------|------|--------------------------|
| IE1 | Formula prompts | 2% | System prompt en `agente_bancoestado.py:124-145` y `app.py:42-64` |
| IE2 | Flujos RAG | 2% | `buscar_wikipedia` en `herramientas_bancoestado.py:140-148`. Arquitectura extensible. |
| IE3 | Diseña arquitecturas | 2% | `Diagrama.png` + diagrama ASCII en Sección 2.3 |
| IE4 | Justifica decisiones | 1% | Tabla de justificación en Sección 2.4 |
| IE5 | Agentes funcionales | 2% | 16 herramientas, AgentExecutor, ciclo ReAct |
| IE6 | Memoria y contexto | 2% | 3 estrategias intercambiables en runtime |
| IE7 | Planificación | 2% | Planificador 14 intenciones + decisiones adaptativas |
| IE8 | Documenta diseño | 1% | Este informe + `README_AGENTE.md` + `Diagrama.png` |
| IE9 | Métricas observabilidad | 1% | Dashboard con 12 KPIs + 8 gráficos + timeline |
| IE10 | Analiza registros | 2% | LangSmith + detección de anomalías + informe autogenerado |
| IE11 | Seguridad | 2% | 6 capas defensa + 133 tests jailbreak + cifrado Fernet |
| IE12 | Propone mejoras | 1% | Informe HTML con conclusiones y recomendaciones basadas en datos |

### Dimensión Defensa (Presentación Oral)

| IE | Indicador | Peso | Qué mostrar en el video |
|----|-----------|------|------------------------|
| IE1 | Formula prompts | 10% | Mostrar system prompt y ejemplos de respuestas |
| IE4 | Justifica diseño | 10% | Explicar por qué LangChain, GPT-4o, planificador propio |
| IE5 | Agente funcional | 10% | Demo en vivo: saldo, bloquear tarjeta, simular crédito |
| IE6 | Memoria | 5% | Cambiar memoria con `/memoria` y mostrar continuidad |
| IE7 | Planificación | 10% | Mostrar `/plan` y cómo prioriza urgencias |
| IE8 | Documentación | 5% | Mostrar `Diagrama.png` y explicar arquitectura |
| IE9 | Observabilidad | 5% | **Dashboard en vivo con gráficos poblados** |
| IE11 | Seguridad | 5% | Mostrar prompt injection bloqueado + métricas de seguridad |
| IE12 | Mejoras | 5% | Mostrar informe HTML + caché semántico + ahorro de tokens |
| IE13 | Evidencia | 5% | Respaldar cada afirmación con datos del dashboard |
| IE14 | Lenguaje técnico | 5% | Usar términos: AgentExecutor, ReAct, coseno TF, circuit breaker |
| IE15 | Responde preguntas | 5% | Preparado para preguntas técnicas del docente |

---

## 7. Conclusiones

El asistente virtual de BancoEstado integra exitosamente un agente LLM con 16 herramientas bancarias, tres estrategias de memoria, planificación por criticidad, seis capas de seguridad y un sistema completo de observabilidad con dashboard interactivo, detección de anomalías y trazabilidad LangSmith.

**Logros principales:**
- Agente funcional con GPT-4o + LangChain que responde consultas bancarias en español
- Seguridad multicapa con 133 tests de jailbreak y 100% de efectividad
- Dashboard en tiempo real con 8 gráficos que cubren IE1-IE12
- Caché semántico que reduce llamadas al LLM y costo operativo
- Procesador de lotes con prioridad para consultas urgentes
- Informe técnico autogenerado con métricas consolidadas
- Cero hardcodeos en módulos IL3.x — toda configuración vía variables de entorno

**Trabajo futuro:**
- Pipeline RAG completo con embeddings y vector store (ChromaDB/Pinecone)
- Enrutamiento inteligente de modelos (GPT-4o-mini para consultas simples)
- Persistencia de métricas en base de datos (SQLite/PostgreSQL)
- Exportación de informe a PDF
- Integración con APIs bancarias reales mediante MCP (Model Context Protocol)

---

## Referencias

- LangChain. (2024). *Agents*. https://python.langchain.com/docs/modules/agents/
- LangChain. (2024). *Memory*. https://python.langchain.com/docs/modules/memory/
- OpenAI. (2024). *Function Calling*. https://platform.openai.com/docs/guides/function-calling
- GitHub. (2024). *GitHub Models*. https://docs.github.com/en/github-models
- LangSmith. (2024). *Tracing*. https://docs.smith.langchain.com/
- BancoEstado. (2024). *Productos y Servicios*. https://www.bancoestado.cl
- Chart.js. (2024). *Documentation*. https://www.chartjs.org/docs/
- Python Software Foundation. (2024). *contextvars*. https://docs.python.org/3/library/contextvars.html
- PyCA. (2024). *Cryptography — Fernet*. https://cryptography.io/en/latest/fernet/

---

**Autores:** Luciano Garrido, Isidora Ayala  
**Licencia:** MIT — Copyright 2026
