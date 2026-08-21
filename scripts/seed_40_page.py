#!/usr/bin/env python3
"""Seed/refresh the public /aniversario40 landing page (CMS).

Control de calidad (2026-08-21):
- ``seo_json`` usa el contrato vigente ``meta_title``/``meta_description``/
  ``meta_image`` (igual que la home). Antes guardaba ``title``/``description``,
  claves que ni el builder ni el render público leen → la página no tenía
  meta description.
- Todas las secciones validan sus ``props_json`` con ``validate_section_props``
  antes de persistir (la misma capa que usa el API del CMS). El seed anterior
  escribía directo a BD con props fuera de schema (p. ej. ``video_hero`` con
  claves de ``hero``, ``rich_text`` con ``vision_*``, ``timeline`` con
  ``events``); cualquier edición posterior desde el builder habría descartado
  esas claves (``extra="ignore"``) y roto la sección.
- Si la página ya está publicada, refresca el snapshot de la versión publicada
  (lo que realmente sirve el endpoint público) e invalida la caché.
"""
import sys
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

try:
    from backend.database import SessionLocal
except ImportError:
    from backend.core.database import SessionLocal

from backend.core.cache_v2 import invalidate_cached_public, invalidate_cached_public_pattern
from backend.crud.cms.pages import _build_page_snapshot
from backend.models import CmsPage, CmsPageVersion, CmsSection, CmsSite, CrmEvent
from backend.schemas.cms_v2_sections import validate_section_props

PAGE_SLUG = "aniversario40"


def _validate_props(section_key: str, section_type: str, props: dict) -> dict:
    """Valida contra el schema backend; reporta claves descartadas (drift)."""
    validated = validate_section_props(section_type, props)
    dropped = set(props) - set(validated)
    if dropped:
        print(f"  ⚠ {section_key} ({section_type}): claves fuera de schema descartadas: {sorted(dropped)}")
    return validated


def seed_40_page():
    db = SessionLocal()
    try:
        # Find the main CCF site
        site = db.query(CmsSite).filter_by(site_key="ccf").first()
        if not site:
            print("Site 'ccf' not found")
            return

        seo_json = {
            "meta_title": "40 Años Iluminando Generaciones — CCF",
            "meta_description": (
                "Celebra con nosotros cuatro décadas de luz en la Comunidad Cristiana Faro. "
                "Agenda del aniversario, nuestra historia y un muro de gratitud. ¡Acompáñanos!"
            ),
            "meta_image": "/aniversario40/gallery-01.jpg",
        }

        # Check if page already exists
        page = db.query(CmsPage).filter_by(site_id=site.id, slug=PAGE_SLUG).first()
        if not page:
            page = CmsPage(
                id=uuid.uuid4(),
                site_id=site.id,
                slug=PAGE_SLUG,
                title="40 Años Iluminando Generaciones",
                status="draft",
                locale="es",
                seo_json=seo_json,
            )
            db.add(page)
            db.flush()
            print("Created CmsPage '40'")
        else:
            # Refresh SEO + título incluso si la página ya existía.
            page.title = "40 Años Iluminando Generaciones"
            page.seo_json = seo_json
            print("CmsPage '40' already exists (SEO/título actualizados)")

        # CTA de registro: se conecta al evento real del aniversario (reserva
        # con QR, lista de espera y formulario dinámico). Si el evento no
        # existe (DB nueva), cae a /eventos.
        mass_event = (
            db.query(CrmEvent)
            .filter(
                CrmEvent.name == "Aniversario 40 Años CCF",
                CrmEvent.deleted_at.is_(None),
            )
            .first()
        )
        register_href = f"/public/events/{mass_event.id}/register" if mass_event else "/eventos"

        # Define the sections
        sections_data = [
            {
                "section_key": "hero",
                "type": "video_hero",
                "sort_order": 0,
                "props_json": {
                    "title": "Celebra con nosotros cuatro décadas de luz.",
                    "body": "Una historia de fe, familia y transformación. Sé parte de este hito histórico de la Comunidad Cristiana Faro.",
                    "cta_label": "Registra tu asistencia",
                    "cta_href": register_href,
                    "video_url": "/aniversario40/video-aniversario40.mp4",
                    "full_bleed": True,
                },
            },
            {
                "section_key": "agenda",
                # Antes usaba ``vision_title``/``vision_text`` (claves de
                # ``about``) que ``rich_text`` no lee → panel vacío. Además el
                # markdown ``**...**`` se habría mostrado literal (el renderer
                # usa ``whitespace-pre-line``, no parsea markdown).
                "type": "rich_text",
                "sort_order": 1,
                "props_json": {
                    "title": "Agenda de Celebración",
                    "body": (
                        "Todo el mes de agosto estaremos conmemorando nuestros 40 años, "
                        "pero los eventos principales se llevarán a cabo en 3 días clave. ¡Acompáñanos!\n\n"
                        "21 de Agosto: Servicio de Milagros (7:00 PM)\n"
                        "22 de Agosto: Conferencia para Líderes y Servidores (8:00 AM a 12:00 PM)\n"
                        "23 de Agosto: Servicio Dominical de Aniversario (9:00 AM)"
                    ),
                    "cta_label": "Ver todos los eventos",
                    "cta_href": "/eventos",
                    "full_bleed": True,
                },
            },
            {
                "section_key": "timeline",
                # Antes usaba ``events`` con ``description``; el contrato de
                # ``timeline`` es ``items`` con ``year/title/body``.
                "type": "timeline",
                "sort_order": 2,
                "props_json": {
                    "title": "40 Años de Fidelidad",
                    "full_bleed": True,
                    "items": [
                        {
                            "year": "1986",
                            "title": "El Comienzo",
                            "body": "Un pequeño grupo de familias se reúne con una visión gigante.",
                        },
                        {
                            "year": "90s",
                            "title": "La semilla de los fundadores",
                            "body": "La Pastora Martina Herrera y su esposo Alejandro Ariza Torres siembran con fe, oración y perseverancia las bases espirituales de esta casa. (Año exacto por confirmar desde el CMS)",
                        },
                        {
                            "year": "2000s",
                            "title": "Una casa que crece",
                            "body": "Los pastores Luis Ricardo Meza e Histar Ariza dedican más de dos décadas a edificar una iglesia que sea verdaderamente una casa para cada persona. (Década por confirmar desde el CMS)",
                        },
                        {
                            "year": "2010s",
                            "title": "Madrugones y familias",
                            "body": "Los servicios de madrugón reúnen a generaciones. Nuevas familias se bautizan, se casan y crecen en la vida en comunidad. (Año por confirmar desde el CMS)",
                        },
                        {
                            "year": "Hoy",
                            "title": "Una red que ilumina",
                            "body": "Más de 500 familias y una red de cerca de 40 sedes de la Comunidad Cristiana El Faro en la región Caribe.",
                        },
                        {
                            "year": "2026",
                            "title": "40 Aniversario",
                            "body": "Cuatro décadas iluminando generaciones. Celebramos este hito con gratitud y esperanza.",
                        },
                    ],
                },
            },
            {
                "section_key": "muro-gratitud",
                # Antes incluía ``eyebrow``/``description``, claves que el
                # schema de ``contact_form`` descarta (se habrían borrado al
                # editar desde el builder). ``subtitle`` es el contrato.
                "type": "contact_form",
                "sort_order": 4,
                "props_json": {
                    "title": "¿Cómo ha transformado Dios tu vida en El Faro?",
                    "full_bleed": True,
                    "split_layout": True,
                    "subtitle": "Comparte tu testimonio. Tu historia es parte de nuestra historia.",
                    "name_label": "Tu nombre",
                    "name_placeholder": "Tu nombre",
                    "email_label": "Correo electrónico",
                    "email_placeholder": "tu@email.com (opcional)",
                    "phone_label": "WhatsApp",
                    "phone_placeholder": "+57 300...",
                    "message_label": "Tu testimonio",
                    "message_placeholder": "Cuéntanos cómo Dios ha transformado tu vida...",
                    "submit_label": "Enviar testimonio",
                    "success_message": "¡Gracias por compartir tu testimonio! Tu historia es parte de nuestra historia.",
                    "action_url": "/public/contact",
                    "reset_label": "Enviar otro testimonio",
                },
            },
            {
                "section_key": "galeria",
                "type": "gallery_masonry",
                "sort_order": 3,
                "props_json": {
                    "title": "Galería histórica",
                    "body": "Momentos que forman parte de nuestra historia. Recorre estas memorias y visita el álbum completo para ver más fotografías.",
                    "layout": "carousel",
                    "autoplay": False,
                    "full_bleed": True,
                    "album_url": "https://photos.app.goo.gl/BN3sDiXAt6aP6tLX8",
                    "album_label": "Ver más fotos en Google Fotos",
                    "images": [
                        {
                            "url": f"/aniversario40/gallery-{index:02d}.jpg",
                            "alt": f"Memoria histórica de CCF {index}",
                            "caption": "Aniversario 40 años CCF",
                        }
                        for index in range(1, 21)
                    ],
                },
            },
        ]

        # Insert or update sections
        for s_data in sections_data:
            section = db.query(CmsSection).filter_by(page_id=page.id, section_key=s_data["section_key"]).first()
            props = _validate_props(s_data["section_key"], s_data["type"], s_data["props_json"])
            if not section:
                section = CmsSection(
                    id=uuid.uuid4(),
                    page_id=page.id,
                    section_key=s_data["section_key"],
                    type=s_data["type"],
                    sort_order=s_data["sort_order"],
                    props_json=props,
                    status="active",
                )
                db.add(section)
                print(f"Created CmsSection '{s_data['section_key']}'")
            else:
                section.type = s_data["type"]
                section.sort_order = s_data["sort_order"]
                section.props_json = props
                print(f"Updated CmsSection '{s_data['section_key']}'")

        db.commit()

        # Si la página está publicada, refresca el snapshot de la versión
        # publicada (lo que sirve el endpoint público) e invalida la caché.
        if page.status == "published" and page.published_version_id:
            version = (
                db.query(CmsPageVersion).filter_by(id=page.published_version_id).first()
            )
            if version:
                version.snapshot_json = _build_page_snapshot(db, page)
                db.commit()
                invalidate_cached_public("public_page", site_key="ccf", slug=PAGE_SLUG)
                invalidate_cached_public_pattern("public_pages_list")
                print("Snapshot público actualizado y caché invalidada.")
            else:
                print("⚠ publicada sin versión publicada; re-publica la página.")
        else:
            print("La página no está publicada; usa el flujo de publicación del CMS.")

        print("Done successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_40_page()
