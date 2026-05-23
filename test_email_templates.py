#!/usr/bin/env python3
"""Script para probar los templates HTML de correo CCF."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── COLORES CORPORATIVOS ──
CCF_DARK = "#001B48"  # Azul profundo
CCF_MEDIUM = "#004581"  # Azul medio
CCF_BLUE = "#018ABD"  # Azul vibrante
CCF_PALE = "#DDE8F0"  # Azul pálido


def build_welcome_html(code: str, frontend_url: str = "https://elfarocc.tech") -> str:
    """Template de bienvenida / verificación de cuenta."""
    verify_link = f"{frontend_url.rstrip('/')}/verify-email?code={code}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bienvenido a CCF</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 20px;">
    <tr>
      <td align="center">
        <!-- ── CARD PRINCIPAL ── -->
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,27,72,0.12);">

          <!-- ── HEADER : Azul oscuro con gradiente radial ── -->
          <tr>
            <td style="background:{CCF_DARK};padding:48px 40px 40px 40px;position:relative;">
              <!-- Radial glow decorativo -->
              <div style="position:absolute;top:-20%;right:-20%;width:140%;height:140%;pointer-events:none;background:radial-gradient(circle at 70% 30%, rgba(1,138,189,0.2) 0%, transparent 60%);"></div>

              <!-- Badge Ministerio -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td style="border:1px solid rgba(255,255,255,0.2);border-radius:100px;padding:8px 20px;background:rgba(255,255,255,0.06);">
                    <span style="color:#ffffff;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;">Ministerio Internacional</span>
                  </td>
                </tr>
              </table>

              <!-- Logo / Marca -->
              <h1 style="font-size:52px;font-weight:900;letter-spacing:-2px;line-height:0.88;color:#ffffff;margin:0 0 6px 0;">
                EL<br/>FARO
              </h1>
              <p style="font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:{CCF_BLUE};margin:16px 0 0 0;line-height:1.4;">
                Comunidad<br/>Cristiana
              </p>
              <div style="width:64px;height:4px;background:#ffffff;border-radius:4px;margin-top:24px;"></div>
            </td>
          </tr>

          <!-- ── BODY : Contenido ── -->
          <tr>
            <td style="padding:40px 40px 36px 40px;">
              <h2 style="font-size:22px;font-weight:800;color:{CCF_DARK};margin:0 0 6px 0;letter-spacing:-0.3px;">
                ¡Bienvenido a la familia!
              </h2>
              <p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">
                Verificación de cuenta
              </p>

              <p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">
                Nos alegra que formes parte de <strong style="color:{CCF_DARK};">El Faro</strong>.
                Para completar tu registro y comenzar a disfrutar de todos los recursos de nuestra plataforma,
                por favor confirma tu dirección de correo haciendo clic en el botón:
              </p>

              <!-- Botón -->
              <table cellpadding="0" cellspacing="0" style="margin:28px 0 32px 0;">
                <tr>
                  <td style="background:{CCF_BLUE};border-radius:10px;padding:14px 36px;text-align:center;">
                    <a href="{verify_link}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:2px;text-transform:uppercase;display:inline-block;">
                      Verificar mi correo →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Link alternativo -->
              <p style="font-size:13px;color:#9ca3af;line-height:1.6;margin:0 0 4px 0;">
                O copia este enlace en tu navegador:
              </p>
              <p style="font-size:12px;color:{CCF_BLUE};word-break:break-all;margin:0;">
                <a href="{verify_link}" style="color:{CCF_BLUE};text-decoration:none;">{verify_link}</a>
              </p>
            </td>
          </tr>

          <!-- ── VERSÍCULO ── -->
          <tr>
            <td style="background:{CCF_PALE};padding:32px 40px;text-align:center;">
              <p style="font-size:16px;color:{CCF_MEDIUM};line-height:1.7;font-style:italic;margin:0 0 8px 0;">
                “Mirad cuán bueno y cuán delicioso es<br/>
                habitar los hermanos juntos en armonía.”
              </p>
              <p style="font-size:13px;font-weight:700;color:{CCF_DARK};letter-spacing:2px;text-transform:uppercase;margin:0;">
                — Salmos 133:1
              </p>
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="background:{CCF_DARK};padding:28px 40px;text-align:center;">
              <p style="font-size:14px;color:rgba(255,255,255,0.7);margin:0 0 4px 0;font-weight:500;">
                Guiando a las naciones hacia la luz de la verdad.
              </p>
              <p style="font-size:11px;color:rgba(255,255,255,0.4);margin:12px 0 0 0;">
                © 2026 Comunidad Cristiana El Faro — Todos los derechos reservados.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_recovery_html(token: str, frontend_url: str = "https://elfarocc.tech") -> str:
    """Template de recuperación de contraseña."""
    reset_link = f"{frontend_url.rstrip('/')}/reset-password?token={token}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Recuperación de Contraseña - CCF</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 20px;">
    <tr>
      <td align="center">
        <!-- ── CARD PRINCIPAL ── -->
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,27,72,0.12);">

          <!-- ── HEADER ── -->
          <tr>
            <td style="background:{CCF_DARK};padding:48px 40px 40px 40px;position:relative;">
              <div style="position:absolute;top:-20%;right:-20%;width:140%;height:140%;pointer-events:none;background:radial-gradient(circle at 70% 30%, rgba(1,138,189,0.2) 0%, transparent 60%);"></div>

              <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td style="border:1px solid rgba(255,255,255,0.2);border-radius:100px;padding:8px 20px;background:rgba(255,255,255,0.06);">
                    <span style="color:#ffffff;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;">Ministerio Internacional</span>
                  </td>
                </tr>
              </table>

              <h1 style="font-size:52px;font-weight:900;letter-spacing:-2px;line-height:0.88;color:#ffffff;margin:0 0 6px 0;">
                EL<br/>FARO
              </h1>
              <p style="font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:{CCF_BLUE};margin:16px 0 0 0;line-height:1.4;">
                Comunidad<br/>Cristiana
              </p>
              <div style="width:64px;height:4px;background:#ffffff;border-radius:4px;margin-top:24px;"></div>
            </td>
          </tr>

          <!-- ── BODY ── -->
          <tr>
            <td style="padding:40px 40px 36px 40px;">
              <h2 style="font-size:22px;font-weight:800;color:{CCF_DARK};margin:0 0 6px 0;letter-spacing:-0.3px;">
                ¿Olvidaste tu contraseña?
              </h2>
              <p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">
                Restablecimiento de acceso
              </p>

              <p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">
                Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en <strong style="color:{CCF_DARK};">El Faro</strong>.
                Si fuiste tú, haz clic en el botón para crear una nueva contraseña:
              </p>

              <!-- Botón -->
              <table cellpadding="0" cellspacing="0" style="margin:28px 0 32px 0;">
                <tr>
                  <td style="background:{CCF_BLUE};border-radius:10px;padding:14px 36px;text-align:center;">
                    <a href="{reset_link}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:2px;text-transform:uppercase;display:inline-block;">
                      Restablecer contraseña →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Link alternativo -->
              <p style="font-size:13px;color:#9ca3af;line-height:1.6;margin:0 0 4px 0;">
                O copia este enlace en tu navegador:
              </p>
              <p style="font-size:12px;color:{CCF_BLUE};word-break:break-all;margin:0;">
                <a href="{reset_link}" style="color:{CCF_BLUE};text-decoration:none;">{reset_link}</a>
              </p>

              <!-- Aviso de seguridad -->
              <table cellpadding="0" cellspacing="0" style="margin-top:28px;background:#fff7ed;border-radius:12px;padding:16px 20px;border:1px solid #fed7aa;">
                <tr>
                  <td style="font-size:12px;color:#9a3412;line-height:1.6;">
                    <strong>⚠️ No solicitaste esto?</strong> Ignora este mensaje.
                    Tu cuenta está segura. Este enlace expira en 60 minutos.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── VERSÍCULO ── -->
          <tr>
            <td style="background:{CCF_PALE};padding:32px 40px;text-align:center;">
              <p style="font-size:16px;color:{CCF_MEDIUM};line-height:1.7;font-style:italic;margin:0 0 8px 0;">
                “Mirad cuán bueno y cuán delicioso es<br/>
                habitar los hermanos juntos en armonía.”
              </p>
              <p style="font-size:13px;font-weight:700;color:{CCF_DARK};letter-spacing:2px;text-transform:uppercase;margin:0;">
                — Salmos 133:1
              </p>
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="background:{CCF_DARK};padding:28px 40px;text-align:center;">
              <p style="font-size:14px;color:rgba(255,255,255,0.7);margin:0 0 4px 0;font-weight:500;">
                Guiando a las naciones hacia la luz de la verdad.
              </p>
              <p style="font-size:11px;color:rgba(255,255,255,0.4);margin:12px 0 0 0;">
                © 2026 Comunidad Cristiana El Faro — Todos los derechos reservados.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_test_email(to: str, subject: str, html: str, text: str = ""):
    """Envía un correo de prueba usando el SMTP de Gmail."""
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = "comunicacionesministeriosfaro@gmail.com"
    smtp_password = "swnk iadn hzco stid"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"CCF Ministerio <{smtp_user}>"
    msg["To"] = to
    msg.attach(MIMEText(text or html.replace("<", "").replace(">", ""), "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"  ✅ Enviado: {subject}")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("═" * 60)
    print("  CCF — PRUEBA DE TEMPLATES DE CORREO")
    print("═" * 60)

    destino = "gscarlosernesto@gmail.com"

    # ── 1. Template de Bienvenida ──
    print("\n📧 Enviando: BIENVENIDA / VERIFICACIÓN...")
    welcome_html = build_welcome_html(code="ccf_demo_verify_code_123")
    send_test_email(
        destino, "🔵 Bienvenido a El Faro — Verifica tu correo", welcome_html
    )

    # ── 2. Template de Recuperación ──
    print("\n📧 Enviando: RECUPERACIÓN DE CONTRASEÑA...")
    recovery_html = build_recovery_html(token="ccf_demo_reset_token_456")
    send_test_email(
        destino, "🔐 Recuperación de contraseña — CCF Ministerio", recovery_html
    )

    print("\n" + "═" * 60)
    print("  ✅ Listo! Revisa la bandeja de entrada de:")
    print(f"     {destino}")
    print("═" * 60)
