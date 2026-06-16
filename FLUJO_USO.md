# Flujo de uso — Chatbot BancoEstado

## 1. Preparación

```bash
# 1. Clonar e instalar dependencias
pip install -r requirements.txt

# 2. Configurar .env (copiar y editar)
cp .env.example .env
# Editar GITHUB_TOKEN con tu token de GitHub Models
# (opcional) EMAIL_PASSWORD para reportes por correo
```

## 2. Demo automática (30 seg)

```bash
python demo_rapida.py
```
Muestra todas las capacidades del sistema sin interacción:
- Lista las 15 herramientas
- Demuestra las 3 memorias
- Muestra planificación por criticidad
- Ejecuta decisiones adaptativas
- Ejecuta herramientas vía orquestador
- Resumen por indicador de evaluación

## 3. Consola interactiva

```bash
python agente_bancoestado.py
```

### Sin token → modo demo automático
```
BANCOESTADO - Asistente Virtual
Modo DEMO (sin LLM)
```

### Con token → modo completo con GPT-4o
```
BANCOESTADO - Asistente Virtual
Modo COMPLETO (con GPT-4o)
```

## 4. Consultas de ejemplo

```
# Consultas básicas (modo demo o completo)
Tu consulta: ¿cuánto tengo en mi CuentaRUT?
Tu consulta: quiero mi estado de cuenta
Tu consulta: simula un crédito de 2 millones a 24 meses
Tu consulta: ¿dónde quedan las sucursales?
Tu consulta: me robaron la tarjeta, bloqueala urgente

# Comandos especiales
/beneficios            → ver tarjetas Bronze, Plata, AURUM, Platino
/verificar             → revisa saldo real y dice cuál te corresponde
/actualizar_saldo      → flujo interactivo paso a paso
/actualizar_saldo CuentaRUT 5000000   → deposita directo
/memoria window        → cambia a memoria de ventana (últimas 4)
/memoria summary       → cambia a memoria con resumen
/memoria buffer        → vuelve a memoria completa
/plan quiero mi saldo  → muestra el plan sin ejecutar
/decisiones            → ejemplos de evaluación de riesgo
/reporte               → envía reporte HTML por correo
/finalizar             → termina sesión y envía reporte
```

## 5. Flujo interactivo de actualizar saldo

Al escribir por ejemplo "gané la lotería":
```
--- Detecte que necesitas actualizar tu saldo ---
  Selecciona la cuenta:
  1) CuentaRUT
  2) Cuenta de Ahorros
  Opcion [1/2]: 1
  Monto a ingresar: $150000000
  Resumen:
    Cuenta: CuentaRUT
    Monto:  $150.000.000
  Confirmar actualizacion? [s/n]: s
  [OK] Saldo actualizado exitosamente.
  Usa /verificar para revisar tus beneficios ahora.
```

## 6. Árbol de decisiones del sistema

```
Usuario escribe consulta
  │
  ├─ ¿Es comando especial? → /beneficios, /verificar, /plan, etc.
  │
  ├─ ¿Menciona actualizar saldo? → flujo interactivo
  │
  ├─ ¿Menciona beneficios/tarjetas? → sugiere /beneficios
  │
  └─ Consulta normal:
       │
       ├─ Modo DEMO:
       │   Planificador → Orquestador → Herramientas → API
       │
       └─ Modo COMPLETO:
           Planificador (urgencia?) → AgentExecutor → LLM + Herramientas → API
```

## 7. Datos de prueba

| Dato | Valor |
|------|-------|
| RUT | 12.345.678-9 |
| Nombre | Juan Pérez González |
| Saldo CuentaRUT | $120.000 |
| Saldo Ahorros | $450.000 |
| Tarjeta Débito | 4532-7890-1234-5678 |
| Tarjeta Crédito | 5123-4567-8901-2345 |
| Crédito activo | $2.500.000 (24 cuotas) |
