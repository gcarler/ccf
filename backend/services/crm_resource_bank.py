"""Banco de recursos del CRM — catálogo de plantillas y categorías predefinidas.

Este módulo mantiene un catálogo *estático* de plantillas orientadas a iglesia.
No inserta nada en la base de datos hasta que un usuario elige "Usar plantilla";
asi cada sede puede personalizar sus propias copias sin forzar datos globales.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SystemTemplate:
    """Plantilla predefinida del banco de recursos."""

    categoria: str
    titulo: str
    canal: str
    contenido_texto: str
    variables_requeridas: List[str] = field(default_factory=list)
    asunto: Optional[str] = None
    descripcion: Optional[str] = None
    contenido_html: Optional[str] = None
    html_template_type: Optional[str] = None


@dataclass(frozen=True)
class SystemCategory:
    """Categoría predefinida del banco de recursos."""

    nombre: str
    descripcion: str
    color_ui_hex: str


# ── Categorías del banco de recursos ──────────────────────────────────────────

SYSTEM_CATEGORIES: List[SystemCategory] = [
    SystemCategory(
        nombre="Bienvenida y Conexión",
        descripcion="Mensajes para nuevos visitantes y seguimiento de primeros pasos.",
        color_ui_hex="#3B82F6",
    ),
    SystemCategory(
        nombre="Acompañamiento y Cuidado",
        descripcion="Seguimiento pastoral, consejería y re-conexión de personas ausentes.",
        color_ui_hex="#10B981",
    ),
    SystemCategory(
        nombre="Fechas Especiales",
        descripcion="Cumpleaños, aniversarios de servicio y festividades importantes.",
        color_ui_hex="#F59E0B",
    ),
    SystemCategory(
        nombre="Recordatorios y Avisos",
        descripcion="Citas pastorales, reuniones de ministerio y anuncios rápidos.",
        color_ui_hex="#EF4444",
    ),
    SystemCategory(
        nombre="Respuestas Rápidas (FAQ)",
        descripcion="Horarios, ubicación, ofrendas y mensajes fuera de horario.",
        color_ui_hex="#8B5CF6",
    ),
    SystemCategory(
        nombre="Redes Sociales",
        descripcion="Textos para comentarios, mensajes privados y atención en redes.",
        color_ui_hex="#EC4899",
    ),
    SystemCategory(
        nombre="Biblioteca de Contenidos",
        descripcion="Guiones, enlaces útiles y materiales listos para compartir.",
        color_ui_hex="#14B8A6",
    ),
    SystemCategory(
        nombre="Automatización y Etiquetas",
        descripcion="Reglas de asignación, etiquetas y flujos automáticos.",
        color_ui_hex="#6366F1",
    ),
]


# ── Plantillas del banco de recursos ──────────────────────────────────────────

SYSTEM_TEMPLATES: List[SystemTemplate] = [
    # ── Bienvenida y Conexión ────────────────────────────────────────────────
    SystemTemplate(
        categoria="Bienvenida y Conexión",
        titulo="Bienvenida a nuevo visitante",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, ¡qué alegría que nos acompañaras! En {{sede}} creemos que Dios tiene un propósito para tu vida y queremos caminar juntos contigo.

Si tienes alguna petición de oración o duda, escríbenos. Estamos para servirte.

Bendiciones,
Equipo pastoral de {{sede}}""",
        variables_requeridas=["nombre", "sede"],
    ),
    SystemTemplate(
        categoria="Bienvenida y Conexión",
        titulo="Bienvenida a nuevo visitante (Email HTML)",
        canal="EMAIL",
        asunto="¡{{nombre}}, bienvenido a la familia! 🏠",
        contenido_texto="""Hola {{nombre}},

Nos alegra de corazón que nos hayas visitado. En {{sede}} creemos que Dios tiene un propósito para tu vida.

Tu siguiente paso ideal es unirte a un grupo en casa: {{link_grupos}}

Que el Señor te bendiga,
{{sede}}""",
        contenido_html="__RENDER__:welcome",
        html_template_type="welcome",
        variables_requeridas=["nombre", "sede", "link_grupos"],
    ),
    SystemTemplate(
        categoria="Bienvenida y Conexión",
        titulo="Seguimiento después de la primera visita",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, esperamos que hayas sido bendecido en tu visita. ¿Tienes alguna pregunta sobre nuestra iglesia o alguna petición de oración? Estamos para servirte.""",
        variables_requeridas=["nombre"],
    ),

    # ── Acompañamiento y Cuidado ─────────────────────────────────────────────
    SystemTemplate(
        categoria="Acompañamiento y Cuidado",
        titulo="Re-conexión por ausencia prolongada",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, ¡te hemos extrañado! Queríamos saludarte y recordarte que eres parte valiosa de nuestra familia. Si hay algo en lo que el equipo pastoral pueda orar o apoyarte, aquí estamos.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Acompañamiento y Cuidado",
        titulo="Seguimiento pastoral",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, queremos saber cómo vas. ¿Cómo podemos orar por ti esta semana? Tu proceso de acompañamiento pastoral es importante para nosotros.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Acompañamiento y Cuidado",
        titulo="Seguimiento pastoral (Email HTML)",
        canal="EMAIL",
        asunto="Hola {{nombre}}, ¿cómo podemos orar por ti?",
        contenido_texto="""Hola {{nombre}},

Queremos saber cómo estás. Tu proceso es importante para nosotros y estamos aquí para apoyarte.

¿Cómo podemos orar por ti esta semana? Responde a este mensaje.

Con cariño,
{{pastor}} — {{sede}}""",
        contenido_html="__RENDER__:pastoral_followup",
        html_template_type="pastoral_followup",
        variables_requeridas=["nombre", "pastor", "sede"],
    ),
    SystemTemplate(
        categoria="Acompañamiento y Cuidado",
        titulo="Cierre de proceso pastoral (Email HTML)",
        canal="EMAIL",
        asunto="Cerramos tu proceso de acompañamiento, {{nombre}}",
        contenido_texto="""Hola {{nombre}},

Hemos cerrado tu proceso de acompañamiento pastoral. Siempre puedes volver a contactarnos.

Dios te bendiga,
Equipo pastoral — {{sede}}""",
        contenido_html="__RENDER__:pastoral_close",
        html_template_type="pastoral_close",
        variables_requeridas=["nombre", "sede"],
    ),

    # ── Fechas Especiales ──────────────────────────────────────────────────
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Felicitación de cumpleaños",
        canal="WHATSAPP",
        contenido_texto="""¡Feliz cumpleaños {{nombre}}! 🥳 Damos gracias a Dios por tu vida y oramos para que Su gracia te sorprenda en este nuevo año.

"Porque yo sé los planes que tengo para ti" — Jeremías 29:11

Un abrazo fraterno de parte de tus pastores.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Felicitación de cumpleaños (Email HTML)",
        canal="EMAIL",
        asunto="¡Feliz cumpleaños, {{nombre}}! 🎂",
        contenido_texto="""¡Feliz cumpleaños {{nombre}}!

Damos gracias a Dios por tu vida. Oramos para que este nuevo año esté lleno de Su gracia, paz y presencia.

"Porque yo sé los planes que tengo para ti" — Jeremías 29:11

Un abrazo fraterno,
Tus pastores""",
        contenido_html="__RENDER__:birthday",
        html_template_type="birthday",
        variables_requeridas=["nombre", "sede"],
    ),
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Aniversario de servicio o matrimonio",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, hoy celebramos contigo este aniversario. Que el Señor siga fortaleciendo tu hogar y tu servicio. ¡Felicidades! 🎉""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Saludo navideño",
        canal="WHATSAPP",
        contenido_texto="""¡Feliz Navidad {{nombre}}! Que el nacimiento de Jesús renueve tu esperanza y tu fe. Te deseamos una Navidad llena de bendiciones junto a los tuyos.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Saludo de año nuevo",
        canal="WHATSAPP",
        contenido_texto="""¡Feliz año nuevo, {{nombre}}! Oramos para que este año esté lleno de propósito, paz y presencia de Dios. Te esperamos en nuestras reuniones.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Fechas Especiales",
        titulo="Día del padre / madre",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, en este día especial queremos honrarte y agradecer a Dios por tu vida. Que el Señor te siga llenando de sabiduría y amor. ¡Feliz día!""",
        variables_requeridas=["nombre"],
    ),

    # ── Recordatorios y Avisos ─────────────────────────────────────────────
    SystemTemplate(
        categoria="Recordatorios y Avisos",
        titulo="Recordatorio de consejería (SMS)",
        canal="SMS",
        contenido_texto="""CCF: Hola {{nombre}}, te recordamos tu espacio de acompañamiento pastoral el {{fecha}} a las {{hora}}. Confirma respondiendo a este mensaje.""",
        variables_requeridas=["nombre", "fecha", "hora"],
    ),
    SystemTemplate(
        categoria="Recordatorios y Avisos",
        titulo="Recordatorio de consejería (Email HTML)",
        canal="EMAIL",
        asunto="Recordatorio: tu consejería pastoral — {{fecha}}",
        contenido_texto="""Hola {{nombre}},

Te recordamos tu espacio de acompañamiento pastoral:
- Día: {{fecha}}
- Hora: {{hora}}
- Con: {{pastoral_name}}

Si no puedes asistir, por favor confirma para reprogramar.

Te esperamos,
{{pastoral_name}}""",
        contenido_html="__RENDER__:counseling_reminder",
        html_template_type="counseling_reminder",
        variables_requeridas=["nombre", "fecha", "hora", "pastoral_name"],
    ),
    SystemTemplate(
        categoria="Recordatorios y Avisos",
        titulo="Confirmación de reunión de ministerio",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, te confirmamos la reunión de {{ministerio}} el día {{fecha}} a las {{hora}} en {{lugar}}. ¡Te esperamos!""",
        variables_requeridas=["nombre", "ministerio", "fecha", "hora", "lugar"],
    ),
    SystemTemplate(
        categoria="Recordatorios y Avisos",
        titulo="Aviso de evento especial",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, te invitamos a "{{evento}}" el día {{fecha}} a las {{hora}}. ¡No te lo pierdas! Más info: {{link}}""",
        variables_requeridas=["nombre", "evento", "fecha", "hora", "link"],
    ),
    SystemTemplate(
        categoria="Recordatorios y Avisos",
        titulo="Invitación a evento (Email HTML)",
        canal="EMAIL",
        asunto="¡{{nombre}}, estás invitado a {{evento}}!",
        contenido_texto="""Hola {{nombre}},

Estás invitado a {{evento}}.
Fecha: {{fecha}}
Hora: {{hora}}
Lugar: {{lugar}}

Más información: {{link}}

¡Te esperamos!""",
        contenido_html="__RENDER__:event_invitation",
        html_template_type="event_invitation",
        variables_requeridas=["nombre", "evento", "fecha", "hora", "lugar", "link"],
    ),

    # ── Respuestas Rápidas (FAQ) ─────────────────────────────────────────────
    SystemTemplate(
        categoria="Respuestas Rápidas (FAQ)",
        titulo="Horarios de reunión",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, nuestros servicios son los {{dias}} a las {{hora}}. Nos ubicamos en {{direccion}}. ¡Será un gusto verte!""",
        variables_requeridas=["nombre", "dias", "hora", "direccion"],
    ),
    SystemTemplate(
        categoria="Respuestas Rápidas (FAQ)",
        titulo="Fuera de horario de atención",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, la paz de Dios. En este momento el equipo está fuera de horario. Déjanos tu mensaje y te responderemos pronto. Si es una emergencia pastoral, contacta al {{telefono_ayuda}}.""",
        variables_requeridas=["nombre", "telefono_ayuda"],
    ),
    SystemTemplate(
        categoria="Respuestas Rápidas (FAQ)",
        titulo="Ubicación de la iglesia",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, nos ubicamos en {{direccion}}. Puedes ver la ubicación aquí: {{link_maps}}. ¡Te esperamos!""",
        variables_requeridas=["nombre", "direccion", "link_maps"],
    ),
    SystemTemplate(
        categoria="Respuestas Rápidas (FAQ)",
        titulo="Información de ofrendas y donaciones",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, puedes realizar tu ofrenda a través de {{metodo}}. Si necesitas más detalles, escríbenos. ¡Dios bendiga tu generosidad!""",
        variables_requeridas=["nombre", "metodo"],
    ),

    # ── Redes Sociales ───────────────────────────────────────────────────────
    SystemTemplate(
        categoria="Redes Sociales",
        titulo="Respuesta a comentario de agradecimiento",
        canal="WHATSAPP",
        contenido_texto="""¡Gracias por tu comentario, {{nombre}}! Nos alegra saber que fuiste bendecido. Si necesitas oración o acompañamiento, escríbenos por interno.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Redes Sociales",
        titulo="Invitación a mensaje privado",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, gracias por tu interés. Nos encantaría conocerte más. ¿Podemos hablar por interno? Escríbenos y con gusto te atenderemos.""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Redes Sociales",
        titulo="Respuesta a queja o reclamo",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, lamentamos escuchar eso. Queremos atenderte con empatía. Por favor, escríbenos por interno con tus datos para que nuestro equipo pastoral se comunique contigo.""",
        variables_requeridas=["nombre"],
    ),

    # ── Biblioteca de Contenidos ─────────────────────────────────────────────
    SystemTemplate(
        categoria="Biblioteca de Contenidos",
        titulo="Guía de bienvenida para nuevos (Email HTML)",
        canal="EMAIL",
        asunto="Tu guía de bienvenida, {{nombre}}",
        contenido_texto="""Hola {{nombre}},

Te compartimos nuestra guía de bienvenida con los próximos pasos para conectarte: {{link_guia}}

Esperamos verte pronto,
{{sede}}""",
        contenido_html="__RENDER__:welcome_guide",
        html_template_type="welcome_guide",
        variables_requeridas=["nombre", "link_guia", "sede"],
    ),
    SystemTemplate(
        categoria="Biblioteca de Contenidos",
        titulo="Enlace a devotional o estudio",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, te compartimos el devotional de esta semana: {{link}}. Esperamos sea de bendición para tu vida.""",
        variables_requeridas=["nombre", "link"],
    ),
    SystemTemplate(
        categoria="Biblioteca de Contenidos",
        titulo="Guion de llamada de seguimiento",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, soy {{pastor}} de {{sede}}. Quería saludarte y saber cómo estás. ¿Hay algo por lo que podamos orar? ¿Tienes alguna duda sobre la iglesia?""",
        variables_requeridas=["nombre", "pastor", "sede"],
    ),

    # ── Automatización y Etiquetas ──────────────────────────────────────────
    SystemTemplate(
        categoria="Automatización y Etiquetas",
        titulo="Asignación automática a nuevo visitante",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, bienvenido a nuestra iglesia. Un líder de nuevos visitantes se pondrá en contacto contigo pronto. ¡Dios te bendiga!""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Automatización y Etiquetas",
        titulo="Mensaje a personas interesadas en grupo",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, vemos que estás interesado en unirte a un grupo en casa. Tenemos varios horarios disponibles. ¿Te gustaría que te enviemos más información?""",
        variables_requeridas=["nombre"],
    ),
    SystemTemplate(
        categoria="Automatización y Etiquetas",
        titulo="Mensaje a voluntarios activos",
        canal="WHATSAPP",
        contenido_texto="""Hola {{nombre}}, gracias por tu servicio en {{ministerio}}. Te recordamos la próxima reunión de equipo el {{fecha}} a las {{hora}}. ¡Tu labor es muy valiosa!""",
        variables_requeridas=["nombre", "ministerio", "fecha", "hora"],
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_system_categories() -> List[Dict]:
    """Devuelve las categorías del sistema en formato serializable."""
    return [
        {
            "nombre": cat.nombre,
            "descripcion": cat.descripcion,
            "color_ui_hex": cat.color_ui_hex,
        }
        for cat in SYSTEM_CATEGORIES
    ]


def get_system_templates() -> List[Dict]:
    """Devuelve las plantillas del sistema en formato serializable."""
    return [
        {
            "id": system_template_id(tpl),
            "categoria": tpl.categoria,
            "titulo": tpl.titulo,
            "canal": tpl.canal,
            "asunto": tpl.asunto,
            "contenido_texto": tpl.contenido_texto,
            "contenido_html": tpl.contenido_html,
            "html_template_type": tpl.html_template_type,
            "variables_requeridas": tpl.variables_requeridas,
            "descripcion": tpl.descripcion,
        }
        for tpl in SYSTEM_TEMPLATES
    ]


def find_system_category(nombre: str) -> Optional[SystemCategory]:
    for cat in SYSTEM_CATEGORIES:
        if cat.nombre == nombre:
            return cat
    return None


def system_template_id(template: SystemTemplate) -> str:
    """Build a stable public identifier without exposing catalog contents as input."""
    value = unicodedata.normalize("NFKD", f"{template.categoria}-{template.titulo}")
    ascii_value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def find_system_template(template_id: str) -> Optional[SystemTemplate]:
    return next(
        (template for template in SYSTEM_TEMPLATES if system_template_id(template) == template_id),
        None,
    )


def find_system_templates_by_category(categoria: str) -> List[SystemTemplate]:
    return [tpl for tpl in SYSTEM_TEMPLATES if tpl.categoria == categoria]
