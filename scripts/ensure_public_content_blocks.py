"""Seed CMS-managed PageContent blocks used by public pages.

The public React components keep local fallbacks for rollback safety, but these
blocks make the current production copy and navigation editable through CMS.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


BLOCKS = {
    "faro_home_feed": {
        "title": "Home publico FARO",
        "content": {
            "eyebrow": "Nuestra esencia",
            "section_title": "Bienvenidos a Casa",
            "section_description": "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.",
            "featured_card": {
                "title": "Conocer a Jesús",
                "desc": "Descubre la base de nuestra fe a través de un viaje personal y transformador. En FARO, te acompañamos en cada paso.",
                "href": "/conocer-a-jesus",
                "cta": "Empezar el camino",
                "img": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=900&q=80",
                "alt": "Reunión de personas en comunidad",
            },
            "cards": [
                {
                    "title": "Librería",
                    "desc": "Recursos para profundizar en tu estudio bíblico.",
                    "href": "/cursos",
                    "img": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80",
                    "alt": "Libros y estudio",
                },
                {
                    "title": "Horarios",
                    "desc": "Reuniones presenciales y online cada semana.",
                    "href": "/eventos",
                    "img": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
                    "alt": "Conferencia y reunión",
                },
                {
                    "title": "Sedes",
                    "desc": "Encuéntranos en tu ciudad.",
                    "href": "/sedes",
                    "img": "https://images.unsplash.com/photo-1438032005730-c779502df39b?w=600&q=80",
                    "alt": "Lugar de reunión",
                },
            ],
        },
    },
    "faro_footer": {
        "title": "Footer publico FARO",
        "content": {
            "description": (
                "Iluminando el camino hacia una conexión profunda con lo divino "
                "a través de la comunidad y la guía espiritual. "
                "Una casa de fe abierta para toda la familia."
            ),
            "nav_links": [
                {"href": "/", "label": "Inicio"},
                {"href": "/nosotros", "label": "Sobre Nosotros"},
                {"href": "/pastores", "label": "Pastores"},
                {"href": "/eventos", "label": "Eventos"},
                {"href": "/predicas", "label": "Prédicas"},
                {"href": "/cursos", "label": "Cursos"},
            ],
            "resource_links": [
                {"href": "/conocer-a-jesus", "label": "Conocer a Jesús"},
                {"href": "/testimonios", "label": "Testimonios"},
                {"href": "/sedes", "label": "Sedes"},
                {"href": "/boletin", "label": "Boletín"},
            ],
            "social_links": [
                {"href": "https://facebook.com/comunidadfaro", "label": "Facebook", "kind": "facebook"},
                {"href": "https://instagram.com/comunidadfaro", "label": "Instagram", "kind": "instagram"},
                {"href": "https://youtube.com/comunidadfaro", "label": "YouTube", "kind": "youtube"},
            ],
            "location_label": "Cartagena, Colombia",
            "newsletter_label": "Boletín semanal",
        },
    },
    "faro_mobile_nav": {
        "title": "Navegacion movil publica FARO",
        "content": {
            "items": [
                {"href": "/", "label": "Inicio", "icon": "home"},
                {"href": "/eventos", "label": "Eventos", "icon": "calendar"},
                {"href": "/predicas", "label": "Prédicas", "icon": "play"},
                {"href": "/sedes", "label": "Sedes", "icon": "map-pin"},
                {"href": "/conocer-a-jesus", "label": "Conectar", "icon": "menu"},
            ]
        },
    },
    "faro_welcome": {
        "title": "Bienvenida publica FARO",
        "content": {
            "eyebrow": "Bienvenida",
            "title_template": "Hola, {name}.",
            "description": (
                "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía. "
                "Puedes empezar por la ruta pública de fe y crecimiento que preparamos para ti."
            ),
            "primary_cta": {"href": "/cursos", "label": "Discipulado Básico"},
            "secondary_cta": {"href": "/conocer-a-jesus", "label": "Una nueva vida con Cristo"},
            "highlights": [
                {
                    "title": "Discipulado Básico",
                    "description": "Empieza por la ruta de fundamentos para crecer con orden y acompañamiento.",
                    "href": "/cursos",
                    "cta": "Ver academia",
                    "icon": "book",
                },
                {
                    "title": "Una nueva vida con Cristo",
                    "description": "Conoce el mensaje central del evangelio en una ruta pública y clara.",
                    "href": "/conocer-a-jesus",
                    "cta": "Abrir ruta",
                    "icon": "heart",
                },
            ],
        },
    },
    "faro_privacy": {
        "title": "Política de privacidad FARO",
        "content": {
            "last_update": "12 de junio de 2026",
            "summary": (
                "Esta política describe cómo PLES SAS y la Comunidad Cristiana El Faro "
                "recopilan, usan, almacenan y protegen tus datos personales."
            ),
            "sections": [
                {"id": "responsables", "title": "1. Responsables del tratamiento"},
                {"id": "datos-recopilados", "title": "2. Datos que recopilamos"},
                {"id": "finalidades", "title": "3. Finalidades del tratamiento"},
                {"id": "bases-legales", "title": "4. Bases legales"},
                {"id": "derechos", "title": "5. Derechos del titular"},
                {"id": "procedimiento", "title": "6. Procedimiento para ejercer derechos"},
                {"id": "terceros", "title": "7. Transferencia y transmisión a terceros"},
                {"id": "cookies", "title": "8. Cookies y tecnologías similares"},
                {"id": "menores", "title": "9. Menores de edad"},
                {"id": "seguridad", "title": "10. Seguridad de la información"},
                {"id": "conservacion", "title": "11. Conservación de datos"},
                {"id": "cambios", "title": "12. Cambios a esta política"},
                {"id": "contacto", "title": "13. Canal de atención"},
            ],
        },
    },
}

MERGE_BLOCKS = {
    "faro_courses_feed": {
        "title": "Feed — Cursos",
        "content": {
            "hero_image_url": "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
            "featured_fallback_image_url": "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
            "cta_images": [
                {"src": "https://picsum.photos/seed/academia1/800/800", "alt": "Estudio"},
                {"src": "https://picsum.photos/seed/academia2/800/800", "alt": "Librería"},
            ],
        },
    },
}


def main() -> int:
    with SessionLocal() as db:
        created = 0
        updated = 0
        for page_key, payload in BLOCKS.items():
            content = json.dumps(payload["content"], ensure_ascii=False)
            row = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
            if row is None:
                row = models.PageContent(page_key=page_key, title=payload["title"], content=content)
                db.add(row)
                created += 1
            else:
                row.title = payload["title"]
                row.content = content
                updated += 1
            db.add(
                models.PageContentVersion(
                    page_key=page_key,
                    title=payload["title"],
                    content=content,
                )
            )
        for page_key, payload in MERGE_BLOCKS.items():
            row = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
            current = {}
            if row is not None:
                try:
                    current = json.loads(row.content or "{}")
                except json.JSONDecodeError:
                    current = {}
            next_content = {**current, **payload["content"]}
            content = json.dumps(next_content, ensure_ascii=False)
            if row is None:
                row = models.PageContent(page_key=page_key, title=payload["title"], content=content)
                db.add(row)
                created += 1
            else:
                row.title = row.title or payload["title"]
                row.content = content
                updated += 1
            db.add(
                models.PageContentVersion(
                    page_key=page_key,
                    title=row.title or payload["title"],
                    content=content,
                )
            )
        db.commit()
        print(f"Public content blocks ensured: {len(BLOCKS) + len(MERGE_BLOCKS)}")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
