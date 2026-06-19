# Agente BancoEstado — Documentación Técnica (IL2.1–IL3.3)

**Asignatura:** ISY0101 — Optativo Ingeniería de Soluciones con IA  
**Evaluación Parcial N°2 y RA3**  
**Autores:** Luciano Garrido, Isidora Ayala

---

## Tabla de Contenidos

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [IL2.1 — Herramientas y Framework (IE1, IE2)](#2-il21--herramientas-y-framework-ie1-ie2)
3. [IL2.2 — Memoria y Contexto (IE3, IE4)](#3-il22--memoria-y-contexto-ie3-ie4)
4. [IL2.3 — Planificación y Decisiones (IE5, IE6)](#4-il23--planificación-y-decisiones-ie5-ie6)
5. [IL2.4 — Documentación Técnica (IE7–IE10)](#5-il24--documentación-técnica-ie7ie10)
6. [IL3.3 — Seguridad y Ética en Agentes de IA](#6-il33--seguridad-y-ética-en-agentes-de-ia)
7. [Comandos del Sistema](#7-comandos-del-sistema)
8. [Evidencias por Indicador de Evaluación](#8-evidencias-por-indicador-de-evaluación)
9. [Referencias](#9-referencias)

---

## 1. Arquitectura del Sistema

### Diagrama de Orquestación (IE7)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USUARIO                                       │
│  ┌──────────────────────┐   ┌──────────────────────────────────┐   │
│  │   CLI (consola)      │   │   Web (Flask + HTML/CSS/JS)      │   │
│  │ agente_bancoestado.py│   │   app.py + templates/ + static/  │   │
│  └──────────┬───────────┘   └────────────────┬─────────────────┘   │
└─────────────┼────────────────────────────────┼──────────────────────┘
              │                                │
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CAPAS DE SEGURIDAD (seguridad.py)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐│
│  │ Rate     │→│ Sanitiza-│→│ Filtro   │→│ Clasif.  │→│ Val.  ││
│  │ Limiter  │ │ dor      │ │ Etico    │ │ Semantico│ │Salida ││
│  │(ventana) │ │(regex)   │ │(4 categ)│ │(LLM,mult)│ │(PII)  ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────┘│
│   Capa 1        Capa 2-4       Capa 3        Capa 5       Capa 6   │
│   Normalización Unicode confusables (small caps, cyrillic, greek)   │
│   Leetspeak decoding, zero-width removal, bypass character collapse  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PLANIFICADOR Y ORQUESTADOR (planificador.py)            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Planificador: clasificación (14 intenciones), criticidad,    │   │
│  │ urgencia, pasos jerárquicos con dependencias                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Orquestador: ejecución multi-paso, args automáticos,          │   │
│  │ extracción de montos desde NLP, evaluación de riesgo          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AGENTE LANGSCHAIN (GPT-4o via GitHub Models)            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ AgentExecutor + TOOL_LIST (16 herramientas @tool)            │   │
│  │ Memoria: Buffer / Window (k=4) / Summary                      │   │
│  │ ContextVar para RUT thread-safe por request                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│           BANCOESTADO API + CIFRADO (bancoestado_api.py)             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 13 endpoints bancarios simulados                              │   │
│  │ Cifrado en reposo: Fernet (AES-128-CBC)                       │   │
│  │ Migración transparente texto plano → cifrado                  │   │
│  │ Clave almacenada en memoria/clave.key (gitignored)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                EMAIL + FRONTEND RESPONSIVE                            │
│  ┌────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ email_sender.py        │  │ templates/index.html + static/     │  │
│  │ • Notificaciones       │  │ • Tailwind CSS responsive          │  │
│  │ • Reporte de sesión    │  │ • Mobile-first breakpoints         │  │
│  │ • Bienvenida login     │  │ • Sidebar con scroll               │  │
│  │ • Responsive (media Q) │  │ • Visitor/User state management    │  │
│  └────────────────────────┘  └────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Flujo de una consulta típica (Web)

1. Usuario ingresa texto en el chat web
2. `POST /chat` → validación de seguridad (6 capas: rate limit → sanitización → inyección → ético → semántico → PII output)
3. `set_rut_actual()` establece RUT thread-safe via ContextVar
4. Si modo demo: `procesar_demo()` → planificador → orquestador → herramientas
5. Si modo LLM: `AgentExecutor.invoke()` → GPT-4o con herramientas + memoria
6. Validación de salida (PII leakage check)
7. Respuesta al frontend
8. Cada acción se registra en sesión con timestamp

### Flujo de una consulta típica (CLI)

1. Usuario ingresa texto en la consola
2. `loop_principal()` recibe la entrada
3. Si es comando especial (`/beneficios`, `/verificar`, etc.), se maneja directo
4. Si el planificador detecta `actualizar_saldo`, se ejecuta flujo interactivo
5. Si menciona "beneficio"/"tarjeta", se sugiere comando sin ir al LLM
6. En modo demo: `procesar_consulta_modo_demo()` → planificador → orquestador → herramientas
7. En modo completo: `procesar_consulta_llm()` → `AgentExecutor` con memoria + herramientas
8. Al finalizar, se envía reporte HTML por correo

### Justificación de Componentes (IE8)

| Componente | Justificación |
|---|---|
| **LangChain (`@tool`, `AgentExecutor`)** | Framework probado para agentes con function calling. Permite escalar agregando nuevas herramientas sin modificar la arquitectura. |
| **Planificador propio** | Evita depender del LLM para tareas simples (modo demo). Clasifica por palabras clave, ordena por criticidad y resuelve dependencias. |
| **API simulada** | El sistema real de BancoEstado está cerrado y maneja datos sensibles. Una simulación permite demostrar todas las funcionalidades sin riesgos de seguridad. |
| **Memorias LangChain** | Tres estrategias (Buffer, Window, Summary) cubren distintos escenarios de uso: conversaciones largas, cortas o con resumen automático. |
| **6 capas de seguridad** | Defensa en profundidad: regex estructural (gratuito, 0ms) + clasificación semántica LLM multilingüe (deep defense). 133 tests de jailbreak con 100% efectividad. |
| **Cifrado Fernet** | AES-128-CBC para datos en reposo. Protege PII de clientes simulados contra accesos no autorizados al sistema de archivos. |
| **ContextVar** | Aislamiento thread-safe del RUT por request. Evita condiciones de carrera en entorno multi-hilo de Flask. |
| **SMTP Gmail** | Protocolo estándar para reportes. La contraseña de aplicación garantiza seguridad sin requerir un servidor de correo dedicado. |
| **Frontend responsive** | Tailwind CSS con breakpoints sm/md. Sidebar con scroll, modales adaptativos, quick-chips con truncado. Compatible con mobile y desktop. |

---

## 2. IL2.1 — Herramientas y Framework (IE1, IE2)

### Framework: LangChain

Se eligió LangChain sobre CrewAI porque CrewAI es incompatible con Python 3.14.5 (entorno del usuario). LangChain ofrece:

- `@tool` para definir herramientas con descripciones que el LLM entiende
- `AgentExecutor` para el ciclo ReAct (Thought → Action → Observation)
- `ChatOpenAI` compatible con GitHub Models API (GPT-4o)
- Tres tipos de memoria conversacional

### Las 16 herramientas (IE1)

Todas en `herramientas_bancoestado.py`, decoradas con `@tool`. Usan `get_rut_actual()` via ContextVar para acceso thread-safe al RUT:

| Herramienta | Parámetros | Descripción |
|---|---|---|
| `consultar_saldo` | tipo_cuenta | Saldo disponible de CuentaRUT o Ahorros |
| `consultar_estado_cuenta` | tipo_cuenta | Estado completo con movimientos |
| `crear_cuenta_rut` | — | Crea nueva CuentaRUT |
| `crear_cuenta_ahorros` | deposito_inicial | Crea cuenta de ahorros |
| `bloquear_tarjeta` | numero_tarjeta, motivo | Bloqueo por pérdida/robo |
| `desbloquear_tarjeta` | numero_tarjeta | Desbloqueo de tarjeta |
| `simular_credito` | monto, plazo_meses | Simulación con cuotas e intereses |
| `solicitar_credito` | monto, plazo_meses | Solicitud formal (con validaciones) |
| `consultar_creditos` | — | Lista créditos activos |
| `transferir` | tipo_origen, tipo_destino, monto, rut_destino? | Transferencia entre cuentas (rut_destino opcional) |
| `simular_ahorro` | monto_mensual, plazo_meses | Proyección de ahorro |
| `listar_sucursales` | — | Sucursales con dirección y horario |
| `consultar_productos` | — | Productos bancarios disponibles |
| `actualizar_saldo` | tipo_cuenta, monto | Depósito externo (solo montos positivos) |
| `buscar_wikipedia` | query | Consultas generales |
| `obtener_fecha_hora` | — | Fecha y hora actual |

### Configuración del LLM

```python
llm = ChatOpenAI(model="gpt-4o", temperature=0)
# Endpoint: https://models.inference.ai.azure.com
# Token: GITHUB_TOKEN del .env
```

Si falla la conexión (rate limit, sin token), el sistema cae automáticamente a modo demo usando solo el planificador.

---

## 3. IL2.2 — Memoria y Contexto (IE3, IE4)

### Estrategias de Memoria

Tres implementaciones intercambiables en tiempo de ejecución con el comando `/memoria`:

```
/memoria buffer      → ConversationBufferMemory (historial completo)
/memoria window      → ConversationBufferWindowMemory (últimas 4)
/memoria summary     → ConversationSummaryMemory (resumen automático)
```

| Estrategia | Ventaja | Desventaja |
|---|---|---|
| **Buffer** | Contexto completo, sin pérdida de información | Alto consumo de tokens en conversaciones largas |
| **Window (k=4)** | Bajo consumo de tokens, ideal para consultas cortas | Pierde contexto de interacciones anteriores |
| **Summary** | Compresión inteligente, retiene lo importante | Depende del LLM para generar el resumen |

### Recuperación de Contexto (IE4)

El prompt del sistema incluye:

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente virtual de BancoEstado... Usa el historial de chat..."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
```

El `chat_history` se mantiene automáticamente según la memoria activa, permitiendo al LLM recordar interacciones previas y mantener coherencia.

---

## 4. IL2.3 — Planificación y Decisiones (IE5, IE6)

### Planificador Jerárquico

`Planificador` en `planificador.py`:

1. **Clasificación**: 14 categorías de intención detectadas por subcadena
2. **Ordenamiento**: Por criticidad (alta → media → baja) y prioridad numérica
3. **Detección de urgencia**: Si hay intenciones de criticidad "alta" (bloqueo de tarjeta)
4. **Generación de pasos**: Cada herramienta única se agrega como paso, con dependencias

### Orquestador Multi-paso

`Orquestador` ejecuta los pasos secuencialmente:

- **Argumentos automáticos**: Inspecciona `inspect.signature` de cada herramienta y provee defaults. Usa `api_bee.rut` para RUT destino en transferencias entre cuentas propias.
- **Extracción de montos desde NLP**: Detecta "150 millones" → 150000000, "10 mil" → 10000
- **Manejo de errores**: Cada paso reporta éxito/fallo individualmente

### Toma de Decisiones Adaptativa (IE6)

#### Evaluación de Transferencia

```python
def evaluar_riesgo_transferencia(monto, saldo_disponible):
    relacion = monto / saldo_disponible
    if relacion > 1.0:   → RECHAZAR (saldo insuficiente)
    if relacion > 0.7:   → REQUIERE VALIDACIÓN (>70% del saldo)
    if relacion > 0.3:   → ADVERTIR (monto considerable)
    else:                → APROBAR (parámetros normales)
```

#### Evaluación de Crédito

```python
def evaluar_credito(monto, ingresos=800000):
    cuota_estimada = monto * 0.05
    relacion = cuota_estimada / ingresos
    if relacion > 0.4:   → RECHAZAR (cuota >40% de ingresos)
    if relacion > 0.25:  → REVISAR (25-40%, evaluar con cuidado)
    else:                → RECOMENDAR (viable)
```

---

## 5. IL2.4 — Documentación Técnica (IE7–IE10)

### Diagrama de Orquestación (IE7)

Incluido en la sección 1. Muestra la arquitectura completa con capas de seguridad, planificador, agente LangChain, API bancaria, cifrado, email y frontend.

### Justificación de Componentes (IE8)

Ver tabla en sección 1. Cada componente se justifica según compatibilidad, seguridad, escalabilidad y estándares.

### Evidencias y Lenguaje Técnico (IE9, IE10)

Este README constituye el informe técnico. Incluye diagrama de arquitectura, tablas comparativas, fragmentos de código y evidencias por cada indicador.

---

## 6. IL3.3 — Seguridad y Ética en Agentes de IA

### Arquitectura de Defensa en Profundidad (6 capas)

Implementado en `herramientas/seguridad.py` — `OrquestadorSeguridad`:

```
ENTRADA
  │
  ├─ CAPA 1: Rate Limiter (ventana deslizante, 30 req/60s por IP/sesión)
  │         • Bloquea por exceso de solicitudes → código RATE_LIMIT
  │
  ├─ CAPA 2: Sanitización Estructural
  │         • NFKD normalization (tildes, diacríticos)
  │         • Zero-width character removal (\u200B, \u200C, \u200D, \uFEFF)
  │         • Unicode confusables normalization (small caps, fullwidth, cyrillic, greek homoglyphs)
  │         • Leetspeak decoding (4→a, 3→e, 1→i, 0→o, etc.)
  │         • Caracteres especiales (ø→o, ł→l, đ→d, þ→th, ß→ss)
  │         • Bypass character collapse (i-g-n-o-r-a→ignora, hack****ear→hackear)
  │         • Punto simple preservado (os.system no se rompe)
  │
  ├─ CAPA 3: Detección de Inyección (24 patrones regex ES+EN)
  │         • Prompt injection: ignora instrucciones, olvida indicaciones, eres un ai
  │         • Code injection: eval(, exec(, __import__(, os.system, subprocess
  │         • English: ignore instructions, forget restrictions, act as if, DAN
  │         • Credential extraction: dame tu contraseña, reveal your password
  │
  ├─ CAPA 4: Filtro Ético (4 categorías, español)
  │         • Violencia: matar, bomba, asesinato, atentado, arma
  │         • Contenido ilegal: hackear, phishing, estafa, fraude, clonar tarjeta
  │         • Manipulación: ignora.*instruccion, olvida.*indicacion, actua como si
  │         • Prompt leak: system prompt, instrucciones de sistema, reglas de seguridad
  │
  ├─ CAPA 5: Clasificación Semántica Multilingüe (LLM) [opcional]
  │         • Analiza intención semántica en cualquier idioma
  │         • Categoriza: inyeccion, etico, prompt_leak
  │         • Degradación elegante: si no hay LLM, se omite sin bloquear
  │
  └─ CAPA 6: Validación de Salida (PII leakage)
            • Detecta RUT, email, teléfono, tarjeta en respuestas del LLM
            • Sanitiza con marcadores: [RUT_REDACTADO], [EMAIL_REDACTADO]
            • Límite de longitud: 10,000 caracteres
```

### Cifrado en Reposo (Fernet AES-128-CBC)

`memoria/datos_clientes.json` se almacena cifrado en disco mediante `cryptography.fernet`:

```python
# Clave generada automáticamente en primer uso
clave = Fernet.generate_key()          # memoria/clave.key (gitignored)
cipher = Fernet(clave)
datos_cifrados = cipher.encrypt(json_data.encode())
```

- **Migración transparente**: Si el archivo existe en texto plano, se carga y se re-cifra automáticamente
- **Archivos protegidos**: `*.db`, `*.sqlite`, `memoria/clave.key`, `memoria/datos_clientes.json` en `.gitignore`
- **Credenciales**: `.env` en `.gitignore`, `.env.example` como plantilla sin secretos

### Métricas de Seguridad

Endpoint `GET /api/security/metrics` + comando `/seguridad`:

| Métrica | Descripción |
|---|---|
| `total_validaciones` | Total de mensajes procesados |
| `bloqueados_inyeccion` | Bloqueos por patrón de inyección |
| `bloqueados_etico` | Bloqueos por filtro ético |
| `bloqueados_rate_limit` | Bloqueos por exceso de solicitudes |
| `bloqueados_semantico` | Bloqueos por clasificación semántica multilingüe |
| `pii_detectados_input` | PII detectada en mensajes de entrada |
| `pii_detectados_output` | PII detectada en respuestas del LLM |

### Testing de Seguridad

`test_jailbreak.py` — 133 tests en 18 categorías con **100% efectividad**:

| Sección | Tests | Descripción |
|---|---|---|
| Inyección de prompts | 20 | Patrones directos español + inglés |
| Filtro ético | 12 | Violencia, ilegal, manipulación |
| Jailbreak clásicos | 8 | DAN, override, re-inyección |
| Bypass encoding | 6 | Tildes, small caps, fullwidth, cyrillic |
| Leetspeak | 14 | Caracteres ofuscados con números/símbolos |
| Zero-width / invisible Unicode | 3 | ZWS, ZWJ, BOM |
| Caracteres especiales | 3 | Guiones, asteriscos, puntos |
| Multi-lenguaje (EN) | 9 | Patrones de ataque en inglés |
| Prompt leaking | 8 | Extracción de system prompt |
| Re-inyección | 6 | Context override, reset de fábrica |
| Inyección de código/SQL | 8 | SQLi, XSS, SSTI, path traversal |
| Rate limiter | 2 | Activación y reinicio |
| Validador de salida | 5 | PII leakage en respuestas |
| Detector PII | 5 | RUT, email, teléfono, tarjeta |
| Orquestador | 5 | Flujo completo 5 capas |
| Multilingüe (7 idiomas) | 11 | FR, DE, IT, PT, ZH, AR, HI |
| Clasificador semántico | 12 | Mock LLM multilingüe |
| Orquestador 6 capas | 7 | Flujo completo con capa semántica |

---

## 7. Comandos del Sistema

### CLI (`agente_bancoestado.py`)

| Comando | Descripción |
|---|---|
| `/beneficios` | Muestra las 4 tarjetas (Bronze, Plata, AURUM, Platino) |
| `/verificar` | Consulta saldo real y muestra qué tarjeta calificas |
| `/actualizar_saldo <tipo> <monto>` | Actualiza saldo directamente |
| `/memoria buffer\|window\|summary` | Cambia estrategia de memoria |
| `/plan <consulta>` | Muestra el plan sin ejecutar |
| `/decisiones` | Ejemplos de toma de decisiones adaptativa |
| `/seguridad` o `/security` | Métricas de seguridad en tiempo real |
| `/reporte` | Envía reporte manualmente |
| `/finalizar` | Termina sesión y envía reporte |

### Web (`app.py`)

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Interfaz web del chatbot |
| `/chat` | POST | Procesa mensaje con seguridad + LLM/demo |
| `/api/register` | POST | Registro de nuevo usuario |
| `/api/login` | POST | Inicio de sesión |
| `/api/cuentas` | GET | Consulta saldos (requiere RUT) |
| `/api/security/metrics` | GET | Métricas de seguridad |
| `/health` | GET | Estado del servidor |

### Tarjetas de Beneficios

| Tarjeta | Saldo Requerido | Crédito Máximo | Descuento |
|---|---|---|---|
| Bronze | $5.000.000 | $500.000 | 5% |
| Plata | $10.000.000 | $1.000.000 | 10% |
| AURUM | $20.000.000 | $3.000.000 | 15% |
| Platino | $100.000.000 | $10.000.000 | 25% |

---

## 8. Evidencias por Indicador de Evaluación

### IE1 — Configura herramientas del agente (10%)

**Evidencia:** `herramientas_bancoestado.py` contiene 16 herramientas decoradas con `@tool`. Cada una con descripción, parámetros tipados y acceso thread-safe al RUT via ContextVar.

**Archivo:** `herramientas_bancoestado.py:28-148`

### IE2 — Integra frameworks escalables (10%)

**Evidencia:** LangChain con `ChatOpenAI`, `AgentExecutor`, `@tool` y `ChatPromptTemplate`. Tres tipos de memoria intercambiables. Arquitectura modular.

**Archivos:** `agente_bancoestado.py:37-148`, `app.py:19-78`

### IE3 — Memoria de contenido para flujos prolongados (10%)

**Evidencia:** `ConversationBufferMemory`, `ConversationBufferWindowMemory`, `ConversationSummaryMemory`. Cambiables en runtime.

**Archivo:** `agente_bancoestado.py:83-100`

### IE4 — Recuperación de contexto semántico (10%)

**Evidencia:** Prompt usa `{chat_history}` como placeholder. Memorias mantienen historial de mensajes.

**Archivo:** `agente_bancoestado.py:106-126`, `app.py:61-66`

### IE5 — Planificación de tareas según prioridades (10%)

**Evidencia:** `Planificador` clasifica por palabras clave, ordena por criticidad y genera pasos con dependencias.

**Archivo:** `planificador.py:20-169`

### IE6 — Decisiones adaptativas según condiciones (10%)

**Evidencia:** `evaluar_riesgo_transferencia()` y `evaluar_credito()`. Flujo interactivo con confirmación.

**Archivo:** `planificador.py:175-201`, `agente_bancoestado.py:288-322`

### IE7 — Diagrama de orquestación y README (10%)

**Evidencia:** Diagrama ASCII completo con capas de seguridad, planificador, agente, API, cifrado, email y frontend.

### IE8 — Justificación de componentes (10%)

**Evidencia:** Tabla de justificación con argumentos de compatibilidad, seguridad, escalabilidad y estándares.

### IE9 — Informe técnico con diagramas y flujos (10%)

**Evidencia:** Este README constituye el informe completo con diagramas, flujos y ejemplos de código.

### IE10 — Lenguaje técnico con evidencias (10%)

**Evidencia:** Todo el informe usa terminología técnica. Cada afirmación respaldada con referencias a archivos y líneas.

### RA3/IL3.3 — Seguridad y Ética (adicional)

**Evidencia:** `herramientas/seguridad.py` — 6 capas de defensa en profundidad con `OrquestadorSeguridad`. `test_jailbreak.py` — 133 tests con 100% efectividad. Cifrado Fernet en `bancoestado_api.py`. Clasificación semántica multilingüe via LLM.

**Archivos:** `seguridad.py`, `test_jailbreak.py`, `bancoestado_api.py:30-80`, `app.py:34`

---

## 9. Referencias

- LangChain. (2024). *Agents*. https://python.langchain.com/docs/modules/agents/
- LangChain. (2024). *Memory*. https://python.langchain.com/docs/modules/memory/
- OpenAI. (2024). *Function Calling*. https://platform.openai.com/docs/guides/function-calling
- GitHub. (2024). *GitHub Models*. https://docs.github.com/en/github-models
- BancoEstado. (2024). *Productos y Servicios*. https://www.bancoestado.cl
- Python Software Foundation. (2024). *contextvars — Context Variables*. https://docs.python.org/3/library/contextvars.html
- Python Software Foundation. (2024). *inspect — Inspect live objects*. https://docs.python.org/3/library/inspect.html
- PyCA. (2024). *Cryptography — Fernet*. https://cryptography.io/en/latest/fernet/
- Google. (2024). *SMTP Gmail*. https://support.google.com/a/answer/176600
- Tailwind CSS. (2024). *Responsive Design*. https://tailwindcss.com/docs/responsive-design
