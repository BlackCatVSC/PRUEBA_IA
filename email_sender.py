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
    destino_default = os.getenv("EMAIL_TO", "luc.garridos@duocuc.cl")
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
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:Arial,sans-serif;color:#333;">
        <div style="max-width:800px;margin:20px auto;border:1px solid #0066cc;border-radius:8px;overflow:hidden;">
            <div style="background:#0066cc;color:white;padding:20px;text-align:center;">
                <h2 style="margin:0;">BancoEstado - Asistente Virtual</h2>
                <p style="margin:5px 0 0;font-size:14px;">Reporte de Sesion</p>
            </div>
            <div style="padding:20px;">
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

                <table style="width:100%;border-collapse:collapse;margin-top:15px;">
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
                <p style="margin-top:20px;font-size:12px;color:#888;">
                    Generado automaticamente por el Asistente BancoEstado.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html
