# Chatbot BancoEstado - Informe del Proyecto 

## 1. Introduccion

En el contexto actual de transformación digital, las instituciones financieras enfrentan el desafío de mejorar la atención al cliente mediante soluciones eficientes, rápidas y disponibles en todo momento. En este escenario, el uso de inteligencia artificial, específicamente modelos de lenguaje (LLM), se presenta como una alternativa innovadora para automatizar la interacción con los usuarios. 

El presente proyecto tiene como objetivo el desarrollo de un chatbot inteligente orientado a la atención de clientes de BancoEstado, capaz de responder consultas frecuentes como:

- Cuentas bancarias  
- Tarjetas (bloqueo, activación)  
- Transferencias  
- Servicios digitales 

de manera clara, precisa y en tiempo real. Para ello, se integran tecnologías como GitHub Models API y LangChain, permitiendo construir un sistema conversacional con memoria, contexto y una experiencia de usuario mejorada. Por ello el ChatBot busca:

- Automatizar respuestas a preguntas frecuentes  
- Mejorar la disponibilidad del servicio (24/7)  
- Reducir tiempos de espera  
- Entregar información clara y accesible al usuario  

---

## 2. Problematica

Las instituciones financieras, como BancoEstado, enfrentan una alta demanda de consultas por parte de los usuarios, especialmente relacionadas con operaciones básicas, servicios digitales y gestión de productos bancarios. Esta situación genera una sobrecarga en los canales tradicionales de atención, como sucursales físicas, call centers y plataformas en línea.

Frente a este escenario, surge la necesidad de implementar soluciones basadas en inteligencia artificial que permitan optimizar la atención al cliente, mejorar la eficiencia operativa y ofrecer respuestas rápidas y accesibles en todo momento.

---

## 3. Implementación de la Solución

La solución fue desarrollada mediante la integración de distintas tecnologías abordadas durante el curso. Inicialmente, estas fueron implementadas en notebooks separados, para posteriormente ser unificadas en una sola estructura funcional. 
A partir de esta integración, se construyó un chatbot capaz de responder consultas de clientes de manera precisa, clara y amigable, utilizando modelos de lenguaje y herramientas especializadas para el manejo de conversaciones.

### 3.1 GitHub Models API

Se utilizó el cliente de OpenAI conectado a GitHub Models para realizar llamadas directas a modelos de lenguaje, permitiendo interactuar con el sistema de inteligencia artificial mediante una API. 

El uso de esta tecnología fue fundamental, ya que permitió integrar modelos avanzados como GPT-4o dentro de la aplicación, facilitando la generación de respuestas automáticas a partir de las consultas del usuario.

Esto permitió:
- Conectarse al modelo GPT-4o de manera segura mediante el uso de variables de entorno
- Configurar parámetros como "temperature" para controlar la creatividad de las respuestas
- Definir límites de respuesta mediante "max_tokens", optimizando el uso de recurso
- Obtener respuestas dinámicas en tiempo real desde una API externa

---

### 3.2 LangChain Model API

Se utilizó el framework LangChain como una capa de abstracción sobre el modelo de lenguaje, con el objetivo de facilitar la construcción de aplicaciones conversacionales más estructuradas y escalables.

El uso de LangChain permitió organizar de manera eficiente la interacción con el modelo, mediante el manejo de mensajes estructurados y el uso de roles (system, user, assistant), lo que contribuye a generar respuestas más coherentes y contextualizadas.

Esta herramienta facilitó:

- La creación de conversaciones "multi-turno", manteniendo el contexto entre interacciones 
- La integración de memoria conversacional para mejorar la continuidad del diálogo 
- La implementación de streaming, permitiendo respuestas en tiempo real

Esto permite construir aplicaciones más complejas de forma modular.

---

### 3.3 Streaming (Respuestas en Tiempo Real)

Se implementó la funcionalidad de streaming con el objetivo de mejorar la experiencia de usuario, permitiendo que las respuestas del modelo se generen y muestren de manera progresiva en tiempo real, en lugar de esperar a que la respuesta completa esté disponible.

Esta técnica permite simular un comportamiento más natural en el chatbot, similar al de una conversación humana, donde las respuestas se construyen de forma gradual.

Ventajas:
- Mejora la percepción de velocidad, ya que el usuario observa resultados de inmediato 
- Simula escritura en tiempo real y genera una experiencia más interactiva y dinámica
- Mantiene la atención del usuario durante la generación de la respuesta  

---

### 3.4 Memoria Conversacional

Se implementó memoria conversacional mediante el uso de InMemoryChatMessageHistory, con el objetivo de permitir que el chatbot mantenga el contexto a lo largo de múltiples interacciones con el usuario.

A diferencia de un sistema tradicional de preguntas y respuestas aisladas, la incorporación de memoria permite que el modelo recuerde mensajes anteriores, logrando una conversación más coherente, fluida y natural.

La funcionalidad permite:

- Mantener el contexto de la conversación entre distintas preguntas 
- Generar respuestas más precisas basadas en interacciones anteriores  
- Generar respuestas coherentes y simula un comportamiento más cercano a una conversación humana

Esto transforma el sistema en un chatbot más natural y no en un sistema de respuestas aisladas, capaz de adaptarse al flujo del diálogo y mejorar significativamente la experiencia del usuario.

---

## 4. Prompt Engineering (IL1.1)

Se diseñó un prompt específico para el contexto bancario, donde el modelo:

- Asume el rol de asistente de BancoEstado  
- Responde consultas sobre servicios financieros  
- Utiliza lenguaje claro y formal  
- Evita solicitar datos sensibles  

Esto permite adaptar el comportamiento del modelo al contexto organizacional.

---

## 5. Funcionalidades del Sistema 

- Chat interactivo en tiempo real  
- Respuestas con streaming  
- Memoria de conversación  
- Uso de modelo LLM (GPT-4o)  
- Contexto especializado en BancoEstado

## Diagrama del Sistema

<p align="center">
  <img src="diagrama.png" width="600">
</p>

---

## 6. Consideraciones

- El sistema no solicita datos sensibles del usuario  
- Las respuestas son informativas  
- Para operaciones críticas, se recomienda uso de canales oficiales  

---

## Autores 

- [Luciano Garrido y Isidora Ayala]