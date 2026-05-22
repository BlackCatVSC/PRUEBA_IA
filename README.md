# Chatbot BancoEstado - Informe del Proyecto 

## 1. Introducción

En el contexto actual de transformación digital, las instituciones financieras enfrentan el desafío de mejorar la atención al cliente mediante soluciones eficientes, rápidas y disponibles en todo momento. En este escenario, el uso de inteligencia artificial, específicamente modelos de lenguaje (LLM), se presenta como una alternativa innovadora para automatizar la interacción con los usuarios.

El presente proyecto tiene como objetivo el desarrollo de un chatbot inteligente orientado a la atención de clientes de BancoEstado, capaz de responder consultas frecuentes relacionadas con:

- Creación de cuentas bancarias (CuentaRUT, cuenta de ahorro, cuenta vista)
- Bloqueo y gestión de tarjetas
- Transferencias bancarias
- Uso de servicios digitales

El sistema busca entregar respuestas claras, seguras y en tiempo real, mejorando la experiencia del usuario y optimizando los canales de atención.

Para ello, se integran tecnologías como GitHub Models API, LangChain, técnicas de Prompt Engineering y arquitectura RAG, permitiendo construir un sistema conversacional con memoria, contexto y alta precisión.

---

## 2. Problemática

Las instituciones financieras presentan una alta demanda de consultas por parte de los usuarios, lo que genera sobrecarga en canales tradicionales como sucursales, call centers y plataformas digitales.

Esto provoca:
- Tiempos de espera elevados
- Saturación de los canales de atención
- Baja eficiencia en la resolución de consultas simples

Frente a esta problemática, surge la necesidad de implementar soluciones basadas en inteligencia artificial que permitan automatizar respuestas, mejorar la disponibilidad del servicio y optimizar la experiencia del usuario.

---

## 3. Implementación de la Solución

La solución fue desarrollada integrando distintas tecnologías abordadas durante el curso, inicialmente en notebooks separados, y posteriormente unificadas en una sola arquitectura funcional.

El sistema final corresponde a un chatbot inteligente capaz de mantener conversaciones, recordar contexto y responder consultas utilizando información relevante.

---

### 3.1 GitHub Models API

Se utilizó la API de GitHub Models para conectarse a modelos de lenguaje avanzados como GPT-4o.

Esto permitió:
- Generar respuestas dinámicas en tiempo real
- Configurar parámetros como temperatura y tokens
- Integrar inteligencia artificial mediante API

---

### 3.2 LangChain Model API

LangChain fue utilizado como framework para estructurar la interacción con el modelo, permitiendo:

- Manejo de mensajes estructurados (system, user, assistant)
- Conversaciones multi-turno
- Integración de memoria conversacional
- Arquitectura modular y escalable

---

### 3.3 Streaming (Respuestas en Tiempo Real)

Se implementó streaming para mostrar respuestas progresivas, mejorando la experiencia del usuario.

Ventajas:
- Mayor percepción de velocidad
- Simulación de escritura en tiempo real
- Interacción más natural

---

### 3.4 Memoria Conversacional

Se utilizó InMemoryChatMessageHistory para mantener el contexto de la conversación.

Esto permite:
- Recordar interacciones previas
- Responder de manera coherente
- Simular una conversación real

---

## 4. Prompt Engineering

Se aplicaron técnicas de:

- Zero-shot prompting (definición de rol y comportamiento)
- Few-shot prompting (ejemplos guiados)

El prompt incluye:
- Rol del asistente
- Formato estructurado de respuesta
- Restricciones de seguridad
- Uso de contexto y memoria

Esto mejora significativamente la calidad de las respuestas.

---

## 5. Funcionalidades del Sistema

- Chat interactivo en tiempo real  
- Respuestas con streaming  
- Memoria conversacional  
- Uso de modelo GPT-4o  
- Contexto especializado en BancoEstado  
- Recuperación de información mediante RAG  

---

## Diagrama del Sistema

<p align="center">
  <img src="Diagrama.png" width="600">
</p>

---

## 6. Implementación de RAG (Retrieval-Augmented Generation)

Se implementó la técnica RAG con el objetivo de mejorar la precisión del chatbot y evitar la generación de respuestas incorrectas.

RAG permite que el modelo:
1. Recupere información relevante desde una base de conocimiento
2. Genere respuestas basadas en ese contexto

El flujo es:

Usuario → Embedding → FAISS → Recuperación → Respuesta

Esto permite entregar respuestas más confiables y basadas en información real.

---

## 7. Base Vectorial y Embeddings

Se utilizó FAISS como base de datos vectorial para almacenar embeddings generados a partir de los textos.

Proceso:
- División de textos (chunking)
- Conversión a embeddings
- Almacenamiento en FAISS
- Búsqueda por similitud semántica

Esto permite que el sistema entienda el significado de las preguntas, no solo palabras exactas.

---

## 8. Memoria Híbrida

El sistema implementa una memoria híbrida compuesta por:

- Memoria estructurada (historial)
- Memoria vectorial (FAISS)
- Resumen conversacional (summary)

Esto permite:
- Mantener coherencia
- Reducir uso de tokens
- Mejorar contexto en respuestas

---

## 9. Evaluación del Sistema RAG

Se evaluó el chatbot utilizando tres métricas:

- Faithfulness (fidelidad)
- Relevancia
- Context Precision

Resultados:

- Faithfulness: 0.60  
- Relevancia: 0.80  
- Context Precision: 0.90  

Interpretación:

- Excelente recuperación de contexto (RAG funciona correctamente)
- Buena capacidad de respuesta
- Presencia de algunas alucinaciones

---

## 10. Análisis de Resultados

Los resultados muestran que:

- El sistema recupera correctamente información relevante
- Las respuestas son en su mayoría adecuadas
- Existen casos donde el modelo genera información no presente en el contexto

Esto indica que el principal desafío es mejorar la fidelidad del modelo.

---

## 11. Consideraciones

- El sistema no solicita datos sensibles  
- Las respuestas son informativas  
- Se recomienda el uso de canales oficiales  
- Se identificaron limitaciones en el uso combinado de few-shot y memoria  

---

## 12. Conclusión

El chatbot desarrollado integra tecnologías modernas de inteligencia artificial como RAG, embeddings, bases vectoriales y memoria híbrida, logrando un sistema conversacional avanzado.

El sistema demuestra un alto nivel de precisión en la recuperación de información y una buena calidad de respuesta, aunque aún presenta desafíos relacionados con la fidelidad del modelo.

En conclusión, el proyecto logra cumplir los objetivos propuestos, ofreciendo una solución eficiente, escalable y alineada con las necesidades actuales de atención al cliente en el ámbito financiero.

---

## Autores 

- Luciano Garrido  
- Isidora Ayala
