"""Defaults de contenido CMS v2 — single source of truth.

Antes estos defaults vivían inline en ``api/cms_v2/_shared.py`` como
strings literales dispersos en el cuerpo de ``_build_section_defaults``
(deuda técnica 🟠#4 del doc ``ESTADO_DEUDA_TECNICA_BACKEND_CMS.md``).
Centralizarlos aquí:

- los hace audatables y editables sin tocar la lógica del router;
- facilita la localización por ``site_key`` (próxima iteración:
  ``defaults_for(site_key)`` puede leer overrides por site);
- documentación canónica de qué defaults de contenido existen.

Regla contractual: estos defaults son ``fallback`` — ``_get_system_var``
ya los recibe como ``default`` y los usa SÓLO si no existe el
``SystemVariable`` correspondiente para el site. No se acopla aqui con
BD; esta capa es puramente declarativa.
"""

# ── SystemVariable defaults (used by _get_system_var) ─────────────────────────

CHURCH_NAME = "Nuestra Iglesia"
MISSION_STATEMENT = "Compartir el amor de Dios y hacer discípulos"
SERVICE_TIME = "Domingos 10:00 AM"
ADDRESS = "Ciudad, País"
MAP_EMBED_URL = ""

WELCOME_TITLE = "Bienvenidos a {church_name}"
CTA_TEXT = "Conócenos"
CTA_LINK = "/pastores"
CTA_TITLE = "Únete a nuestra comunidad"
CTA_DESCRIPTION = "Te invitamos a ser parte de nuestra familia. Todos son bienvenidos."

# ── Section: cta_banner ───────────────────────────────────────────────────────

CTA_BANNER_BUTTON_TEXT = "Visítanos"
CTA_BANNER_BUTTON_LINK = "/contacto"

# ── Section: stats ────────────────────────────────────────────────────────────

STAT_YEARS_OF_MINISTRY = "25+"
STAT_MEMBERS_LABEL = "Miembros Activos"
STAT_GROUPS_LABEL = "Grupos de Casa"

# ── Section: team ─────────────────────────────────────────────────────────────

TEAM_FALLBACK_NAME = "Pastor"
TEAM_FALLBACK_ROLE = "Pastor Principal"
TEAM_TITLE = "Nuestro Equipo Pastoral"

# ── Section: faq ──────────────────────────────────────────────────────────────

FAQ_TITLE = "Preguntas Frecuentes"
FAQ_FIRST_VISIT_ANSWER = (
    "Una comunidad cálida que te recibirá con los brazos abiertos. Ven tal como eres."
)
FAQ_GROUP_STUDY_ANSWER = (
    "Sí, tenemos grupos de casa que se reúnen durante la semana. "
    "Contáctanos para más información."
)

# ── Section: testimonials ─────────────────────────────────────────────────────

TESTIMONIALS_TITLE = "Testimonios"
TESTIMONIALS_FALLBACK_AUTHOR = "Anónimo"
TESTIMONIALS_FALLBACK_EMOTION = "Gratitud"
