"""
email_sender.py - Envio de reportes SMTP
========================================
Envia el resumen de la sesion del agente BancoEstado
via Gmail usando SMTP con TLS.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime


def enviar_reporte(asunto: str, cuerpo_html: str, destinatario: str = None):
    """
    Envia un correo con el reporte de la sesion.

    Args:
        asunto: Asunto del correo
        cuerpo_html: Cuerpo del correo en formato HTML
        destinatario: Correo destino (opcional, por defecto usa EMAIL_TO del .env)
    """
    remitente = os.getenv("EMAIL_FROM", "botfinanciero16@gmail.com")
    password = os.getenv("EMAIL_PASSWORD", "")
    destino_default = os.getenv("EMAIL_TO", "")
    destino = destinatario or destino_default

    if not password:
        return "[!] EMAIL_PASSWORD no configurado en .env"

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destino
    msg.set_content(
        "Este correo contiene formato HTML. "
        "Por favor usa un cliente que lo soporte."
    )
    msg.add_alternative(cuerpo_html, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(remitente, password)
            server.send_message(msg)
        return f"[OK] Reporte enviado a {destino}"
    except smtplib.SMTPAuthenticationError:
        return (
            "[!] Error de autenticacion SMTP.\n"
            "    Para Gmail necesitas una 'Contrasena de aplicacion':\n"
            "    1. https://myaccount.google.com/security\n"
            "    2. Activar verificacion en 2 pasos\n"
            "    3. Crear contrasena de aplicacion\n"
            "    4. Pegarla en EMAIL_PASSWORD en .env"
        )
    except Exception as e:
        return f"[!] Error enviando correo: {e}"


def enviar_notificacion_transaccion(tipo: str, monto: float, cuenta: str, saldo_nuevo: float,
                                     destino: str = None, rut_origen: str = None, rut_destino: str = None,
                                     cuenta_destino: str = None):
    """
    Envia un correo de notificacion por deposito o transferencia.

    Args:
        tipo: "deposito" o "transferencia"
        monto: monto de la operacion
        cuenta: tipo de cuenta origen (CuentaRUT, CuentaAhorros)
        saldo_nuevo: saldo posterior a la operacion en la cuenta origen
        destino: email destino (opcional)
        rut_origen: RUT origen (solo transferencia)
        rut_destino: RUT destino (solo transferencia)
        cuenta_destino: tipo de cuenta destino (solo transferencia)
    """
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    es_deposito = tipo == "deposito"

    if es_deposito:
        icono = "\U0001F4B0"
        asunto = f"Deposito recibido - ${monto:,.0f} - BancoEstado"
        accion = "Deposito"
        detalle = f"Se ha ingresado <strong>${monto:,.0f}</strong> a tu {cuenta}."
        cuenta_mostrada = cuenta
    else:
        icono = "\U0001F4B8"
        asunto = f"Transferencia realizada - ${monto:,.0f} - BancoEstado"
        accion = "Transferencia"
        misma_persona = rut_origen and rut_destino and rut_origen == rut_destino
        if misma_persona and cuenta_destino:
            detalle = (
                f"Se ha transferido <strong>${monto:,.0f}</strong> "
                f"desde {cuenta} a {cuenta_destino}."
            )
            cuenta_mostrada = f"{cuenta} \u2192 {cuenta_destino}"
        elif cuenta_destino and rut_destino:
            detalle = (
                f"Se ha transferido <strong>${monto:,.0f}</strong> "
                f"desde {cuenta} a {cuenta_destino} (RUT {rut_destino})."
            )
            cuenta_mostrada = f"{cuenta} \u2192 {cuenta_destino}"
        elif rut_destino:
            detalle = (
                f"Se ha transferido <strong>${monto:,.0f}</strong> "
                f"desde {cuenta} a RUT {rut_destino}."
            )
            cuenta_mostrada = cuenta
        else:
            detalle = (
                f"Se ha transferido <strong>${monto:,.0f}</strong> "
                f"desde {cuenta}."
            )
            cuenta_mostrada = cuenta

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="color-scheme" content="light">
        <style>
            @media screen and (max-width: 480px) {{
                .email-container {{ max-width: 100% !important; margin: 0 !important; }}
                .email-header {{ padding: 16px !important; border-radius: 0 !important; }}
                .email-body {{ padding: 16px !important; border-radius: 0 !important; }}
                .email-icon {{ font-size: 32px !important; }}
                .email-title {{ font-size: 18px !important; }}
                .email-detail {{ font-size: 14px !important; }}
                .email-table td {{ font-size: 13px !important; }}
                .email-footer {{ font-size: 11px !important; }}
            }}
        </style>
    </head>
    <body style="font-family:Arial,Helvetica,sans-serif;color:#333;margin:0;padding:0;background:#f5f5f5;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
        <div class="email-container" style="max-width:520px;margin:20px auto;width:100%;">
            <div class="email-header" style="background:#0066cc;color:white;padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                <div class="email-icon" style="font-size:40px;margin-bottom:8px;">{icono}</div>
                <h2 class="email-title" style="margin:0;font-size:20px;">{accion}</h2>
                <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">BancoEstado - Notificacion automatica</p>
            </div>
            <div class="email-body" style="background:white;padding:24px;border-radius:0 0 12px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                <p style="font-size:16px;margin:0 0 16px;">Hola,</p>
                <p class="email-detail" style="font-size:15px;margin:0 0 20px;line-height:1.5;">{detalle}</p>
                <div style="background:#f8f9fb;border-radius:8px;padding:16px;margin-bottom:20px;">
                    <table class="email-table" style="width:100%;border-collapse:collapse;font-size:14px;">
                        <tr>
                            <td style="padding:4px 0;color:#666;">Monto</td>
                            <td style="padding:4px 0;text-align:right;font-weight:bold;">${monto:,.0f}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 0;color:#666;">Cuenta</td>
                            <td style="padding:4px 0;text-align:right;">{cuenta_mostrada}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 0;color:#666;">Saldo actual</td>
                            <td style="padding:4px 0;text-align:right;font-weight:bold;color:#0066cc;">${saldo_nuevo:,.0f}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 0;color:#666;">Fecha</td>
                            <td style="padding:4px 0;text-align:right;">{ahora}</td>
                        </tr>
                    </table>
                </div>
                <p class="email-footer" style="font-size:12px;color:#999;margin:0;text-align:center;">
                    Este es un mensaje automatico del Asistente BancoEstado.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return enviar_reporte(asunto, cuerpo_html, destino)


def generar_reporte_html(sesion: list, beneficio: dict = None) -> str:
    """
    Genera el cuerpo HTML del reporte con todas las interacciones.

    Args:
        sesion: Lista de acciones registradas
        beneficio: Opcional, dict con la tarjeta de beneficio obtenida
    """
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    total_acciones = len(sesion)
    exitosas = sum(1 for s in sesion if s.get("exitoso", False))
    fallidas = total_acciones - exitosas

    filas = ""
    for i, s in enumerate(sesion, 1):
        estado = "✅" if s.get("exitoso", False) else "❌"
        consulta = s.get("consulta", "")
        herramienta = s.get("herramienta", "")
        resultado = str(s.get("resultado", ""))[:120]
        filas += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{i}</td>
            <td style="padding:8px;border:1px solid #ddd;">{consulta}</td>
            <td style="padding:8px;border:1px solid #ddd;">{herramienta}</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:center;">{estado}</td>
            <td style="padding:8px;border:1px solid #ddd;font-size:12px;">{resultado}</td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="color-scheme" content="light">
        <style>
            @media screen and (max-width: 480px) {{
                .report-container {{ max-width: 100% !important; margin: 0 !important; border-radius: 0 !important; border: none !important; }}
                .report-header {{ padding: 16px !important; }}
                .report-header h2 {{ font-size: 16px !important; }}
                .report-body {{ padding: 12px !important; }}
                .report-table {{ font-size: 11px !important; }}
                .report-table th, .report-table td {{ padding: 4px !important; }}
                .report-table th:nth-child(4), .report-table td:nth-child(4),
                .report-table th:nth-child(5), .report-table td:nth-child(5) {{ display: none; }}
                .report-footer {{ font-size: 10px !important; }}
            }}
        </style>
    </head>
    <body style="font-family:Arial,Helvetica,sans-serif;color:#333;margin:0;padding:0;background:#f5f5f5;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
        <div class="report-container" style="max-width:800px;margin:20px auto;border:1px solid #0066cc;border-radius:8px;overflow:hidden;background:white;width:100%;">
            <div class="report-header" style="background:#0066cc;color:white;padding:20px;text-align:center;">
                <h2 style="margin:0;">BancoEstado - Asistente Virtual</h2>
                <p style="margin:5px 0 0;font-size:14px;">Reporte de Sesion</p>
            </div>
            <div class="report-body" style="padding:20px;">
                <p><strong>Fecha:</strong> {ahora}</p>
                <p><strong>Total acciones:</strong> {total_acciones}</p>
                <p><strong>Exitosas:</strong> {exitosas} | <strong>Fallidas:</strong> {fallidas}</p>
                {"" if not beneficio else f'''
                <div style="margin:15px 0;padding:15px;background:#e8f5e9;border-left:4px solid #2e7d32;border-radius:4px;">
                    <h3 style="margin:0 0 5px;color:#2e7d32;">Beneficio Obtenido</h3>
                    <p style="margin:2px 0;"><strong>Tarjeta:</strong> {beneficio.get("nombre","")}</p>
                    <p style="margin:2px 0;"><strong>Credito maximo:</strong> ${beneficio.get("credito_maximo",0):,}</p>
                    <p style="margin:2px 0;"><strong>Descuento:</strong> {beneficio.get("descuento","")}</p>
                </div>
                '''}
                <div style="overflow-x:auto;">
                <table class="report-table" style="width:100%;border-collapse:collapse;margin-top:15px;min-width:300px;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th style="padding:8px;border:1px solid #ddd;">#</th>
                            <th style="padding:8px;border:1px solid #ddd;">Consulta</th>
                            <th style="padding:8px;border:1px solid #ddd;">Herramienta</th>
                            <th style="padding:8px;border:1px solid #ddd;width:50px;">Estado</th>
                            <th style="padding:8px;border:1px solid #ddd;">Resultado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas}
                    </tbody>
                </table>
                </div>
                <p class="report-footer" style="margin-top:20px;font-size:12px;color:#888;">
                    Generado automaticamente por el Asistente BancoEstado.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html
