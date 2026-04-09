# Chatbot BancoEstado

## 1. Informe del Proyecto

El presente proyecto consiste en el desarrollo de un chatbot basado en modelos de lenguaje (LLM), orientado a la atención de clientes de BancoEstado.

La necesidad de este sistema surge debido a la alta demanda de consultas frecuentes relacionadas con servicios bancarios, tales como:

- Cuentas bancarias  
- Tarjetas (bloqueo, activación)  
- Transferencias  
- Servicios digitales  

Actualmente, estas consultas generan una carga operativa importante en los canales de atención tradicionales. Por ello, el chatbot busca:

- Automatizar respuestas a preguntas frecuentes  
- Mejorar la disponibilidad del servicio (24/7)  
- Reducir tiempos de espera  
- Entregar información clara y accesible al usuario  

---

## 2. Implementación de la Solución

La solución fue desarrollada integrando diferentes tecnologías vistas en el curso, las cuales originalmente se trabajaron en notebooks separados y posteriormente fueron unificadas en una sola celda.

### 2.1 GitHub Models API

Se utilizó el cliente de OpenAI conectado a GitHub Models para realizar llamadas directas al modelo de lenguaje.

Esto permitió:
- Conectarse al modelo GPT-4o  
- Configurar parámetros como temperatura y tokens  
- Obtener respuestas desde una API real  

---

### 2.2 LangChain Model API

Se utilizó el framework LangChain para abstraer el uso del modelo, facilitando:

- Manejo estructurado de mensajes  
- Uso de roles (system, user)  
- Integración con otras herramientas  

Esto permite construir aplicaciones más complejas de forma modular.

---

### 2.3 Streaming (Respuestas en Tiempo Real)

Se implementó streaming para mostrar las respuestas del modelo de manera progresiva.

Ventajas:
- Mejora la experiencia de usuario  
- Simula escritura en tiempo real  
- Reduce la percepción de espera  

---

### 2.4 Memoria Conversacional

Se implementó memoria mediante `InMemoryChatMessageHistory`, permitiendo:

- Recordar preguntas anteriores  
- Mantener contexto conversacional  
- Generar respuestas coherentes  

Esto transforma el sistema en un chatbot más natural y no en un sistema de respuestas aisladas.

---

## 3. Prompt Engineering (IL1.1)

Se diseñó un prompt específico para el contexto bancario, donde el modelo:

- Asume el rol de asistente de BancoEstado  
- Responde consultas sobre servicios financieros  
- Utiliza lenguaje claro y formal  
- Evita solicitar datos sensibles  

Esto permite adaptar el comportamiento del modelo al contexto organizacional.

---

## 4. Funcionalidades del Sistema 

- Chat interactivo en tiempo real  
- Respuestas con streaming  
- Memoria de conversación  
- Uso de modelo LLM (GPT-4o)  
- Contexto especializado en BancoEstado  

---

## 5. Consideraciones

- El sistema no solicita datos sensibles del usuario  
- Las respuestas son informativas  
- Para operaciones críticas, se recomienda uso de canales oficiales  

---

## Autores 

- [Luciano Garrido y Isidora Ayala]