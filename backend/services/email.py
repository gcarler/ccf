"""Servicio de email para verificación, password reset y notificaciones.

Usa SMTP y es configurable vía settings. En local/test escribe a stdout.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.core.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


def _build_message(to: str, subject: str, html: str, text: str = "") -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to
    msg.attach(MIMEText(text or html.replace("<", "").replace(">", ""), "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    """Envía un email vía SMTP. En local/test escribe a log en lugar de enviar.

    Returns:
        True si se envió (o se logueó), False si falló.
    """
    env = (settings.environment or "local").strip().lower()
    if env in {"local", "test", "testing", "ci"}:
        log.info("[EMAIL LOG] Subject: %s", subject)
        log.debug("[EMAIL LOG] Body: %s", html[:300])
        return True

    if not settings.smtp_host or settings.smtp_host == "localhost":
        log.warning(
            "SMTP not configured; email skipped (subject: %s)", subject
        )
        return False

    msg = _build_message(to, subject, html, text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            log.info("Email sent (subject: %s)", subject)
            return True
    except Exception as exc:
        log.error("Failed to send email (subject: %s): %s", subject, exc)
        return False


# ── Templates ─────────────────────────────────────────────────────────

# Colores corporativos
_CCF_DARK = "#001B48"
_CCF_BLUE = "#018ABD"
_CCF_MEDIUM = "#004581"
_CCF_PALE = "#DDE8F0"

_BRAND_HEADER = """\
<table width="100%" cellpadding="0" cellspacing="0" style="background:{dark};padding:48px 40px 40px 40px;position:relative;">
  <div style="position:absolute;top:-20%;right:-20%;width:140%;height:140%;pointer-events:none;background:radial-gradient(circle at 70% 30%, rgba(1,138,189,0.2) 0%, transparent 60%);"></div>
  <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
    <tr>
      <td style="border:1px solid rgba(255,255,255,0.2);border-radius:100px;padding:8px 20px;background:rgba(255,255,255,0.06);">
        <span style="color:#ffffff;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;">Ministerio Internacional</span>
      </td>
    </tr>
  </table>
  <h1 style="font-size:52px;font-weight:900;letter-spacing:-2px;line-height:0.88;color:#ffffff;margin:0 0 6px 0;">EL<br/>FARO</h1>
  <p style="font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:{blue};margin:16px 0 0 0;line-height:1.4;">Comunidad<br/>Cristiana</p>
  <div style="width:64px;height:4px;background:#ffffff;border-radius:4px;margin-top:24px;"></div>
</table>"""

_BRAND_VERSE = """\
<table width="100%" cellpadding="0" cellspacing="0" style="background:{pale};padding:32px 40px;text-align:center;">
  <tr>
    <td>
      <p style="font-size:16px;color:{medium};line-height:1.7;font-style:italic;margin:0 0 8px 0;">
        &ldquo;Mirad cu&aacute;n bueno y cu&aacute;n delicioso es<br/>
        habitar los hermanos juntos en armon&iacute;a.&rdquo;
      </p>
      <p style="font-size:13px;font-weight:700;color:{dark};letter-spacing:2px;text-transform:uppercase;margin:0;">
        &mdash; Salmos 133:1
      </p>
    </td>
  </tr>
</table>"""

_BRAND_FOOTER = """\
<table width="100%" cellpadding="0" cellspacing="0" style="background:{dark};padding:28px 40px;text-align:center;">
  <tr>
    <td>
      <p style="font-size:14px;color:rgba(255,255,255,0.7);margin:0 0 4px 0;font-weight:500;">
        Guiando a las naciones hacia la luz de la verdad.
      </p>
      <p style="font-size:11px;color:rgba(255,255,255,0.4);margin:12px 0 0 0;">
        &copy; 2026 Comunidad Cristiana El Faro &mdash; Todos los derechos reservados.
      </p>
    </td>
  </tr>
</table>"""


def _brand_wrap(html_body: str) -> str:
    """Envuelve el contenido en el layout corporativo de CCF."""
    header = _BRAND_HEADER.format(dark=_CCF_DARK, blue=_CCF_BLUE)
    verse = _BRAND_VERSE.format(pale=_CCF_PALE, medium=_CCF_MEDIUM, dark=_CCF_DARK)
    footer = _BRAND_FOOTER.format(dark=_CCF_DARK)

    return f"""\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CCF Ministerio</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,27,72,0.12);">
          {header}
          <tr><td style="padding:40px 40px 36px 40px;">
            {html_body}
          </td></tr>
          {verse}
          {footer}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_verify_email(code: str, frontend_url: str | None = None) -> tuple[str, str]:
    """Renderiza el email de verificación con diseño corporativo."""
    base = (frontend_url or settings.frontend_url).rstrip("/")
    verify_link = f"{base}/verify-email?token={code}"
    subject = "🔵 Bienvenido a El Faro — Verifica tu correo"

    body = f"""\
<h2 style="font-size:22px;font-weight:800;color:{_CCF_DARK};margin:0 0 6px 0;letter-spacing:-0.3px;">
  &iexcl;Bienvenido a la familia!
</h2>
<p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">
  Verificaci&oacute;n de cuenta
</p>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">
  Nos alegra que formes parte de <strong style="color:{_CCF_DARK};">El Faro</strong>.
  Para completar tu registro y comenzar a disfrutar de todos los recursos de nuestra plataforma,
  por favor confirma tu direcci&oacute;n de correo haciendo clic en el bot&oacute;n:
</p>
<table cellpadding="0" cellspacing="0" style="margin:28px 0 32px 0;">
  <tr>
    <td style="background:{_CCF_BLUE};border-radius:10px;padding:14px 36px;text-align:center;">
      <a href="{verify_link}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:2px;text-transform:uppercase;display:inline-block;">
        Verificar mi correo &rarr;
      </a>
    </td>
  </tr>
</table>
<p style="font-size:13px;color:#9ca3af;line-height:1.6;margin:0 0 4px 0;">
  O copia este enlace en tu navegador:
</p>
<p style="font-size:12px;color:{_CCF_BLUE};word-break:break-all;margin:0;">
  <a href="{verify_link}" style="color:{_CCF_BLUE};text-decoration:none;">{verify_link}</a>
</p>"""

    return subject, _brand_wrap(body)


def render_reset_password(
    token: str, frontend_url: str | None = None
) -> tuple[str, str]:
    """Renderiza el email de restablecimiento de contraseña con diseño corporativo."""
    base = (frontend_url or settings.frontend_url).rstrip("/")
    reset_link = f"{base}/reset-password?token={token}"
    subject = "🔐 Recuperación de contraseña — CCF Ministerio"

    body = f"""\
<h2 style="font-size:22px;font-weight:800;color:{_CCF_DARK};margin:0 0 6px 0;letter-spacing:-0.3px;">
  &iquest;Olvidaste tu contrase&ntilde;a?
</h2>
<p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">
  Restablecimiento de acceso
</p>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">
  Hemos recibido una solicitud para restablecer la contrase&ntilde;a de tu cuenta en <strong style="color:{_CCF_DARK};">El Faro</strong>.
  Si fuiste t&uacute;, haz clic en el bot&oacute;n para crear una nueva contrase&ntilde;a:
</p>
<table cellpadding="0" cellspacing="0" style="margin:28px 0 32px 0;">
  <tr>
    <td style="background:{_CCF_BLUE};border-radius:10px;padding:14px 36px;text-align:center;">
      <a href="{reset_link}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:2px;text-transform:uppercase;display:inline-block;">
        Restablecer contrase&ntilde;a &rarr;
      </a>
    </td>
  </tr>
</table>
<p style="font-size:13px;color:#9ca3af;line-height:1.6;margin:0 0 4px 0;">
  O copia este enlace en tu navegador:
</p>
<p style="font-size:12px;color:{_CCF_BLUE};word-break:break-all;margin:0;">
  <a href="{reset_link}" style="color:{_CCF_BLUE};text-decoration:none;">{reset_link}</a>
</p>
<table cellpadding="0" cellspacing="0" style="margin-top:28px;background:#fff7ed;border-radius:12px;padding:16px 20px;border:1px solid #fed7aa;">
  <tr>
    <td style="font-size:12px;color:#9a3412;line-height:1.6;">
      <strong>&#9888;&#65039; &iquest;No solicitaste esto?</strong> Ignora este mensaje.
      Tu cuenta est&aacute; segura. Este enlace expira en {settings.password_reset_expire_minutes} minutos.
    </td>
  </tr>
</table>"""

    return subject, _brand_wrap(body)
    return subject, html
