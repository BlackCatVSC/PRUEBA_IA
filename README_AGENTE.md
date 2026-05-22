# Agente BancoEstado — Documentación Técnica (IL2.1–IL2.4)

**Asignatura:** ISY0101 — Optativo Ingeniería de Soluciones con IA  
**Evaluación Parcial N°2** — Ponderación: 35%  
**Autores:** Luciano Garrido, Isidora Ayala

---

## Tabla de Contenidos

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [IL2.1 — Herramientas y Framework (IE1, IE2)](#2-il21--herramientas-y-framework-ie1-ie2)
3. [IL2.2 — Memoria y Contexto (IE3, IE4)](#3-il22--memoria-y-contexto-ie3-ie4)
4. [IL2.3 — Planificación y Decisiones (IE5, IE6)](#4-il23--planificación-y-decisiones-ie5-ie6)
5. [IL2.4 — Documentación Técnica (IE7–IE10)](#5-il24--documentación-técnica-ie7ie10)
6. [Comandos del Sistema](#6-comandos-del-sistema)
7. [Evidencias por Indicador de Evaluación](#7-evidencias-por-indicador-de-evaluación)
8. [Referencias](#8-referencias)

---

## 1. Arquitectura del Sistema

### Diagrama de Orquestación (IE7)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USUARIO (consola)                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     agente_bancoestado.py                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Loop Principal (input → procesar → responder)                │  │
│  │  • Detección de comandos especiales                           │  │
│  │  • Detección de intenciones (planificador preview)            │  │
│  │  • Enrutamiento: modo demo → planificador, modo LLM → GPT-4o │  │
│  │  • Tracking de sesión (lista `sesion`)                        │  │
│  │  • Envío de reporte al finalizar                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────┬────────────────────────────────┬─────────────────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│   planificador.py        │   │  herramientas_bancoestado.py │
│  ┌────────────────────┐  │   │  ┌─────────────────────────┐ │
│  │ Planificador       │  │   │  │ 15 × @tool (LangChain)  │ │
│  │ • Clasificación    │  │   │  │ • consultar_saldo       │ │
│  │ • Criticidad       │  │   │  │ • consultar_estado_cta  │ │
│  │ • Urgencia         │  │   │  │ • crear_cuenta_rut      │ │
│  │ • Pasos+deps       │  │   │  │ • crear_cuenta_ahorros  │ │
│  └────────────────────┘  │   │  │ • bloquear/desbloquear  │ │
│  ┌────────────────────┐  │   │  │ • simular/solicitar_cred│ │
│  │ Orquestador        │  │   │  │ • transferir            │ │
│  │ • Ejecución multi- │  │   │  │ • simular_ahorro        │ │
│  │   paso             │  │   │  │ • listar_sucursales     │ │
│  │ • Args automáticos │  │   │  │ • consultar_productos   │ │
│  │ • Extracción de    │  │   │  │ • actualizar_saldo      │ │
│  │   montos desde NLP │  │   │  │ • buscar_wikipedia      │ │
│  │ • Evaluación riesgo│  │   │  │ • obtener_fecha_hora    │ │
│  └────────────────────┘  │   │  └─────────────────────────┘ │
└──────────────────────────┘   └──────────────────────────────┘
           │                                │
           └────────────┬───────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      bancoestado_api.py                             │
│  • Simulación backend bancario (13 endpoints)                      │
│  • Cliente: RUT 12.345.678-9, saldos, tarjetas, créditos           │
│  • Validaciones, reglas de negocio, datos de prueba                 │
└─────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      email_sender.py                                │
│  • generar_reporte_html(sesion, beneficio) → HTML                  │
│  • enviar_reporte() → SMTP Gmail (TLS 587)                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Flujo de una consulta típica

1. Usuario ingresa texto en la consola
2. `loop_principal()` recibe la entrada
3. Si es comando especial (`/beneficios`, `/verificar`, etc.), se maneja directo
4. Si el planificador detecta `actualizar_saldo`, se ejecuta flujo interactivo
5. Si menciona "beneficio"/"tarjeta", se sugiere comando sin ir al LLM
6. En modo demo: `procesar_consulta_modo_demo()` → planificador → orquestador → herramientas
7. En modo completo: `procesar_consulta_llm()` → `AgentExecutor` con memoria + herramientas
8. Cada acción se registra en `sesion` con timestamp
9. Al finalizar, se envía reporte HTML por correo

### Justificación de Componentes (IE8)

| Componente | Justificación |
|---|---|
| **LangChain (`@tool`, `AgentExecutor`)** | Framework probado para agentes con function calling. Permite escalar agregando nuevas herramientas sin modificar la arquitectura. |
| **Planificador propio** | Evita depender del LLM para tareas simples (modo demo). Clasifica por palabras clave, ordena por criticidad y resuelve dependencias. |
| **API simulada** | El sistema real de BancoEstado está cerrado y maneja datos sensibles. Una simulación permite demostrar todas las funcionalidades sin riesgos de seguridad. |
| **Memorias LangChain** | Tres estrategias (Buffer, Window, Summary) cubren distintos escenarios de uso: conversaciones largas, cortas o con resumen automático. |
| **SMTP Gmail** | Protocolo estándar para reportes. La contraseña de aplicación garantiza seguridad sin requerir un servidor de correo dedicado. |
| **Flujo interactivo** | Para operaciones sensibles (actualizar saldo), se pide confirmación al usuario, evitando ejecuciones accidentales. |

---

## 2. IL2.1 — Herramientas y Framework (IE1, IE2)

### Framework: LangChain

Se eligió LangChain sobre CrewAI porque CrewAI es incompatible con Python 3.14.5 (entorno del usuario). LangChain ofrece:

- `@tool` para definir herramientas con descripciones que el LLM entiende
- `AgentExecutor` para el ciclo ReAct (Thought → Action → Observation)
- `ChatOpenAI` compatible con GitHub Models API (GPT-4o)
- Tres tipos de memoria conversacional

### Las 15 herramientas (IE1)

Todas en `herramientas_bancoestado.py`, decoradas con `@tool`:

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
| `transferir` | tipo_origen, rut_destino, tipo_destino, monto | Transferencia entre cuentas |
| `simular_ahorro` | monto_mensual, plazo_meses | Proyección de ahorro |
| `listar_sucursales` | — | Sucursales con dirección y horario |
| `consultar_productos` | — | Productos bancarios disponibles |
| `actualizar_saldo` | tipo_cuenta, monto | Depositar/actualizar saldo |
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

Ejemplo de plan para "Me robaron la tarjeta":

```
Plan de 1 paso(s):
  [URGENTE] 1. Ejecutar bloquear_tarjeta
[!] Se detectaron acciones urgentes - priorizando ejecucion
```

### Orquestador Multi-paso

`Orquestador` ejecuta los pasos secuencialmente. Características:

- **Argumentos automáticos**: Inspecciona `inspect.signature` de cada herramienta y provee defaults
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

#### Flujo Interactivo de Actualización de Saldo

Cuando el usuario menciona lotería, herencia, depósito, etc., el sistema activa un flujo interactivo:

1. Pregunta: ¿CuentaRUT o CuentaAhorros?
2. Pregunta: ¿Monto a ingresar?
3. Muestra resumen y pide confirmación
4. Ejecuta y sugiere `/verificar` para beneficios

---

## 5. IL2.4 — Documentación Técnica (IE7–IE10)

### Diagrama de Orquestación (IE7)

Incluido en la sección 1 de este documento. Muestra todos los componentes del sistema, sus relaciones y el flujo de datos.

### Justificación de Componentes (IE8)

Ver tabla en sección 1. Cada componente se justifica según:
- Compatibilidad con el entorno (Python 3.14.5)
- Requerimientos del problema (banco real cerrado → simulación)
- Estándares de la industria (LangChain, SMTP)
- Experiencia de usuario (flujo interactivo con confirmación)

### Evidencias y Lenguaje Técnico (IE9, IE10)

Este README constituye el informe técnico. Incluye:
- Diagrama de arquitectura
- Tablas comparativas de componentes
- Fragmentos de código relevantes
- Justificaciones basadas en restricciones técnicas reales
- Evidencias por cada indicador de evaluación (sección 7)

---

## 6. Comandos del Sistema

| Comando | Descripción |
|---|---|
| `/beneficios` | Muestra las 4 tarjetas (Bronze, Plata, AURUM, Platino) |
| `/verificar` | Consulta saldo real y muestra qué tarjeta calificas |
| `/actualizar_saldo <tipo> <monto>` | Actualiza saldo directamente |
| `/memoria buffer\|window\|summary` | Cambia estrategia de memoria |
| `/plan <consulta>` | Muestra el plan sin ejecutar |
| `/decisiones` | Ejemplos de toma de decisiones adaptativa |
| `/reporte` | Envía reporte manualmente |
| `/finalizar` | Termina sesión y envía reporte |

### Tarjetas de Beneficios

| Tarjeta | Saldo Requerido | Crédito Máximo | Descuento |
|---|---|---|---|
| Bronze | $5.000.000 | $500.000 | 5% |
| Plata | $10.000.000 | $1.000.000 | 10% |
| AURUM | $20.000.000 | $3.000.000 | 15% |
| Platino | $100.000.000 | $10.000.000 | 25% |

---

## 7. Evidencias por Indicador de Evaluación

### IE1 — Configura herramientas del agente (10%)

**Evidencia:** `herramientas_bancoestado.py` contiene 15 herramientas decoradas con `@tool`. Cada herramienta tiene descripción y parámetros tipados. Se ejecutan autónomamente vía `AgentExecutor` (LLM) o `Orquestador` (demo).

**Archivo:** `herramientas_bancoestado.py:16-133`

### IE2 — Integra frameworks escalables (10%)

**Evidencia:** LangChain con `ChatOpenAI`, `AgentExecutor`, `@tool` y `ChatPromptTemplate`. Tres tipos de memoria intercambiables. Arquitectura modular que permite agregar herramientas sin modificar el núcleo.

**Archivos:** `agente_bancoestado.py:37-148`

### IE3 — Memoria de contenido para flujos prolongados (10%)

**Evidencia:** `ConversationBufferMemory`, `ConversationBufferWindowMemory`, `ConversationSummaryMemory` implementadas. Cambiables en runtime con `/memoria`.

**Archivo:** `agente_bancoestado.py:83-100`

### IE4 — Recuperación de contexto semántico (10%)

**Evidencia:** El prompt usa `{chat_history}` como placeholder. Las memorias mantienen el historial de mensajes. El planificador analiza la consulta completa antes de decidir acciones.

**Archivo:** `agente_bancoestado.py:106-120`

### IE5 — Planificación de tareas según prioridades (10%)

**Evidencia:** `Planificador` clasifica por palabras clave, ordena por criticidad (alta > media > baja) y genera pasos con dependencias. Detección de urgencia.

**Archivo:** `planificador.py:20-169`

### IE6 — Decisiones adaptativas según condiciones (10%)

**Evidencia:** `evaluar_riesgo_transferencia()` y `evaluar_credito()` ajustan decisiones según monto, saldo e ingresos. Flujo interactivo con confirmación para operaciones sensibles.

**Archivo:** `planificador.py:175-201`, `agente_bancoestado.py:288-322`

### IE7 — Diagrama de orquestación y README (10%)

**Evidencia:** Este documento incluye diagrama ASCII de la arquitectura completa (sección 1) y describe cada componente.

**Archivo:** `README_AGENTE.md` (este documento)

### IE8 — Justificación de componentes (10%)

**Evidencia:** Tabla de justificación en sección 1 con argumentos de compatibilidad, seguridad, escalabilidad y estándares.

### IE9 — Informe técnico con diagramas y flujos (10%)

**Evidencia:** Este README constituye el informe. Incluye diagrama de orquestación, flujo de consulta típico, tablas comparativas y ejemplos de código.

### IE10 — Lenguaje técnico con evidencias (10%)

**Evidencia:** Todo el informe usa terminología técnica (AgentExecutor, function calling, ConversationBufferMemory, criticidad, orquestación multi-paso). Cada afirmación se respalda con referencias a archivos y líneas de código.

---

## 8. Referencias

- LangChain. (2024). *Agents*. https://python.langchain.com/docs/modules/agents/
- LangChain. (2024). *Memory*. https://python.langchain.com/docs/modules/memory/
- OpenAI. (2024). *Function Calling*. https://platform.openai.com/docs/guides/function-calling
- GitHub. (2024). *GitHub Models*. https://docs.github.com/en/github-models
- BancoEstado. (2024). *Productos y Servicios*. https://www.bancoestado.cl
- Python Software Foundation. (2024). *inspect — Inspect live objects*. https://docs.python.org/3/library/inspect.html
- Google. (2024). *SMTP Gmail*. https://support.google.com/a/answer/176600
