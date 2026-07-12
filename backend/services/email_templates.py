"""Templates HTML responsive para el CRM resource bank."""
from __future__ import annotations

from html import escape
from typing import Dict, Optional

from backend.services.email import _FALLBACK_BRAND, _brand_wrap


def _safe(val: Optional[str]) -> str:
    return escape(val) if val else ""


def _cta_button(text: str, url: str, brand: Dict[str, str]) -> str:
    primary = brand.get("primary", _FALLBACK_BRAND["primary"])
    return f'<table cellpadding="0" cellspacing="0" style="margin:28px 0 24px 0;"><tr><td style="background:{primary};border-radius:10px;padding:14px 36px;text-align:center;"><a href="{_safe(url)}" style="color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:2px;text-transform:uppercase;display:inline-block;">{escape(text)} &rarr;</a></td></tr></table>'


def render_welcome(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    sede = _safe(vars.get("sede", b.get("church_name", "nuestra iglesia")))
    link_grupos = _safe(vars.get("link_grupos", "#"))
    body = f"""<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;">&iexcl;{nombre}, bienvenido a la familia!</h2>
<p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">Nuevo visitante</p>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">Nos alegra de coraz&oacute;n que nos hayas visitado. En <strong style="color:{b['dark']};">{sede}</strong> creemos que Dios tiene un prop&oacute;sito para tu vida y queremos caminar juntos contigo.</p>
{_cta_button("Conocer nuestros grupos", link_grupos, b)}"""
    return _brand_wrap(body, b)


def render_birthday(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    body = f"""<div style="text-align:center;margin-bottom:28px;"><span style="font-size:48px;">&#127874;</span></div>
<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;text-align:center;">&iexcl;Feliz cumplea&ntilde;os, {nombre}!</h2>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;text-align:center;">Damos gracias a Dios por tu vida y oramos para que este nuevo a&ntilde;o est&eacute; lleno de Su gracia, paz y presencia.</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:{b['pale']};border-radius:12px;padding:24px 28px;margin:8px 0 24px 0;text-align:center;"><tr><td>
<p style="font-size:16px;color:{b['medium']};line-height:1.7;font-style:italic;margin:0 0 8px 0;">&ldquo;Porque yo s&eacute; los planes que tengo para ustedes&rdquo;</p>
<p style="font-size:13px;font-weight:700;color:{b['dark']};letter-spacing:2px;text-transform:uppercase;margin:0;">&mdash; Jerem&iacute;as 29:11</p>
</td></tr></table>"""
    return _brand_wrap(body, b)


def render_pastoral_followup(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    pastor = _safe(vars.get("pastor", "tu equipo pastoral"))
    sede = _safe(vars.get("sede", b.get("church_name", "")))
    body = f"""<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;">&iexcl;Hola {nombre}!</h2>
<p style="font-size:14px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:3px;margin:0 0 24px 0;">Acompa&ntilde;amiento pastoral</p>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">Queremos saber c&oacute;mo est&aacute;s. Tu proceso es importante para nosotros.</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border-radius:12px;padding:20px 24px;margin:0 0 20px 0;border:1px solid #bbf7d0;"><tr><td>
<p style="font-size:14px;color:#166534;line-height:1.7;margin:0;"><strong>&iquest;C&oacute;mo podemos orar por ti esta semana?</strong></p>
</td></tr></table>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0;text-align:center;">Con cari&ntilde;o,<br/><strong style="color:{b['dark']};">{pastor} &mdash; {sede}</strong></p>"""
    return _brand_wrap(body, b)


def render_pastoral_close(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    sede = _safe(vars.get("sede", b.get("church_name", "")))
    body = f"""<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;">Cerramos tu proceso de acompanhamiento</h2>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">Hola {nombre}, hemos cerrado tu proceso. <strong>Siempre puedes volver a contactarnos</strong>.</p>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0;text-align:center;">Que Dios te bendiga,<br/><strong style="color:{b['dark']};">Equipo pastoral &mdash; {sede}</strong></p>"""
    return _brand_wrap(body, b)


def render_event_invitation(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    evento = _safe(vars.get("evento", "nuestro evento"))
    fecha = _safe(vars.get("fecha", ""))
    hora = _safe(vars.get("hora", ""))
    lugar = _safe(vars.get("lugar", ""))
    link = _safe(vars.get("link", "#"))
    details = ""
    if fecha:
        details += f'<p style="margin:0 0 6px 0;"><strong style="color:{b["dark"]};">&#128197; Fecha:</strong> {fecha}</p>'
    if hora:
        details += f'<p style="margin:0 0 6px 0;"><strong style="color:{b["dark"]};">&#128336; Hora:</strong> {hora}</p>'
    if lugar:
        details += f'<p style="margin:0 0 6px 0;"><strong style="color:{b["dark"]};">&#128205; Lugar:</strong> {lugar}</p>'
    body = f"""<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;">&iexcl;{nombre}, est&aacute;s invitado!</h2>
<p style="font-size:18px;font-weight:800;color:{b['primary']};margin:0 0 20px 0;text-align:center;">{evento}</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:12px;padding:20px 24px;margin:0 0 24px 0;border:1px solid #e5e7eb;"><tr><td>{details}</td></tr></table>
{_cta_button("M&aacute;s informaci&oacute;n", link, b)}"""
    return _brand_wrap(body, b)


def render_welcome_guide(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    sede = _safe(vars.get("sede", b.get("church_name", "")))
    link_guia = _safe(vars.get("link_guia", "#"))
    body = f"""<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;">Tu gu&iacute;a de bienvenida</h2>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 20px 0;">Hola {nombre}, &iexcl;gracias por visitarnos! Encontrar&aacute;s todo lo que necesitas saber en nuestra gu&iacute;a.</p>
{_cta_button("Descargar gu&iacute;a", link_guia, b)}
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0;text-align:center;">Esperamos verte pronto,<br/><strong style="color:{b['dark']};">{sede}</strong></p>"""
    return _brand_wrap(body, b)


def render_counseling_reminder(vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    nombre = _safe(vars.get("nombre", "amigo"))
    fecha = _safe(vars.get("fecha", ""))
    hora = _safe(vars.get("hora", ""))
    pastoral_name = _safe(vars.get("pastoral_name", "tu pastor"))
    body = f"""<div style="text-align:center;margin-bottom:24px;"><span style="font-size:40px;">&#128197;</span></div>
<h2 style="font-size:22px;font-weight:800;color:{b['dark']};margin:0 0 6px 0;text-align:center;">Recordatorio de consejer&iacute;a</h2>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:12px;padding:24px 28px;margin:0 0 24px 0;border:1px solid #e5e7eb;"><tr><td>
<p style="font-size:15px;color:#374151;line-height:1.7;margin:0;">Hola <strong>{nombre}</strong>, te recordamos tu espacio de acompanhamiento:</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0 0 0;">
<tr><td style="padding:10px 0;border-bottom:1px solid #e5e7eb;"><strong style="color:{b['dark']};">&#128197; D&iacute;a:</strong> {fecha}</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #e5e7eb;"><strong style="color:{b['dark']};">&#128336; Hora:</strong> {hora}</td></tr>
<tr><td style="padding:10px 0;"><strong style="color:{b['dark']};">&#128100; Con:</strong> {pastoral_name}</td></tr>
</table></td></tr></table>
<p style="font-size:16px;color:#374151;line-height:1.7;margin:0;text-align:center;">Te esperamos,<br/><strong style="color:{b['dark']};">{pastoral_name}</strong></p>"""
    return _brand_wrap(body, b)


_RENDERERS = {
    "welcome": render_welcome,
    "birthday": render_birthday,
    "pastoral_followup": render_pastoral_followup,
    "pastoral_close": render_pastoral_close,
    "event_invitation": render_event_invitation,
    "welcome_guide": render_welcome_guide,
    "counseling_reminder": render_counseling_reminder,
}


def render_email(template_type: str, vars: Dict[str, str], brand: Optional[Dict[str, str]] = None) -> str:
    renderer = _RENDERERS.get(template_type)
    if renderer is None:
        return ""
    return renderer(vars, brand)
