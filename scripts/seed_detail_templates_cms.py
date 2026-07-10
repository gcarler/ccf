#!/usr/bin/env python3
"""Seed CMS detail-template sections for testimonials, courses, and pastors.

Adds or updates a ``detail_template`` section (type ``rich_text``) on the
English-slug CMS pages. The section's ``props_json`` contains the default
Spanish labels and static copy currently used by the frontend detail pages.
The script is idempotent: it upserts the section and publishes a new version
of each page.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models as models  # noqa: E402

try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

DETAIL_TEMPLATE_PROPS: dict[str, dict[str, Any]] = {
    "testimonials": {
        "footer_label": "Historia de impacto",
        "prayer_action_label": "Pedir oración",
        "share_action_label": "Compartir historia",
        "share_toast_success": "Enlace copiado al portapapeles",
        "share_toast_error": "No pudimos copiar el enlace",
        "prayer_success_title": "Petición recibida",
        "prayer_success_description": (
            "Tu solicitud de oración ha sido enviada a nuestro equipo de consolidación. "
            "No se publica en la página — es confidencial."
        ),
        "prayer_success_close": "Cerrar",
        "prayer_form_badge": "Oración confidencial",
        "prayer_form_title": "¿Este testimonio tocó tu corazón?",
        "prayer_form_description": (
            "Si deseas que oremos por ti, déjanos tu petición. Llega directo a nuestro "
            "equipo pastoral, sin publicarse en el sitio."
        ),
        "prayer_name_placeholder": "Tu nombre",
        "prayer_request_placeholder": "Cuéntanos tu petición de oración...",
        "prayer_submit_label": "Enviar al equipo pastoral",
    },
    "courses": {
        "about_title": "Acerca de este programa",
        "instructor_label": "Instructor Principal",
        "syllabus_title": "Temario del Curso",
        "enroll_button_default": "Inscribirme al Curso",
        "enrolled_label": "Inscrito",
        "share_toast_success": "Enlace copiado",
        "enroll_drawer_title": "Inscribirme en {title}",
        "enroll_drawer_description": "Déjanos tus datos para crear tu acceso al curso.",
        "enroll_name_label": "Nombre completo",
        "enroll_email_label": "Email",
        "enroll_phone_label": "WhatsApp (opcional)",
        "enroll_cancel_label": "Cancelar",
        "enroll_submit_label": "Inscribirme",
        "enroll_submitting_label": "Inscribiendo...",
        "enroll_success_toast": 'Inscrito en "{title}". Revisa tu correo.',
        "enroll_error_toast": "No se pudo completar la inscripción. Intenta de nuevo.",
    },
    "pastors": {
        "badge_label": "Liderazgo Pastoral",
        "role_fallback": "Pastor",
        "quote_subtitle": "Filosofía de vida",
        "tags": ["Pastor", "Líder", "Consejero"],
        "motto_label": "Versículo Lema",
        "story_title": "Su Historia",
        "story_subtitle": "Testimonio de vida y ministerio",
        "cta_eyebrow": "Comunidad de Fe",
        "cta_description": "¿Deseas conectar con el Pastor {first_name} o saber más sobre su ministerio?",
        "cta_primary_label": "Conocer al equipo",
        "cta_secondary_label": "Nuestras sedes",
    },
}


def _snapshot(page: models.CmsPage, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
            "locale": page.locale,
        },
        "sections": [
            {
                "section_key": s["key"],
                "type": s["type"],
                "props_json": s["props"],
                "sort_order": s["sort"],
                "is_visible": True,
                "status": "active",
            }
            for s in sections
        ],
    }


def main() -> int:
    db = SessionLocal()
    try:
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
        if site is None:
            site = db.query(models.CmsSite).filter_by(site_key="ccf").first()
        if site is None:
            raise RuntimeError("No active CmsSite found")

        updated = 0
        published = 0

        for slug, props in DETAIL_TEMPLATE_PROPS.items():
            page = (
                db.query(models.CmsPage)
                .filter_by(site_id=site.id, slug=slug)
                .first()
            )
            if page is None:
                print(f"Skip {slug}: CMS page not found")
                continue

            # Gather existing sections to preserve them in the new version.
            existing_sections = (
                db.query(models.CmsSection)
                .filter_by(page_id=page.id)
                .order_by(models.CmsSection.sort_order)
                .all()
            )

            section_specs: list[dict[str, Any]] = []
            detail_inserted = False
            for idx, sec in enumerate(existing_sections):
                if sec.section_key == "detail_template":
                    # Replace the existing detail_template section.
                    section_specs.append(
                        {
                            "key": "detail_template",
                            "type": "rich_text",
                            "props": props,
                            "sort": idx,
                        }
                    )
                    detail_inserted = True
                else:
                    section_specs.append(
                        {
                            "key": sec.section_key,
                            "type": sec.type,
                            "props": sec.props_json or {},
                            "sort": idx,
                        }
                    )

            if not detail_inserted:
                section_specs.append(
                    {
                        "key": "detail_template",
                        "type": "rich_text",
                        "props": props,
                        "sort": len(section_specs),
                    }
                )

            # Replace all sections on the page.
            db.query(models.CmsSection).filter_by(page_id=page.id).delete()
            db.commit()

            for spec in section_specs:
                section = models.CmsSection(
                    page_id=page.id,
                    section_key=spec["key"],
                    type=spec["type"],
                    props_json=spec["props"],
                    sort_order=spec["sort"],
                    is_visible=True,
                    status="active",
                )
                db.add(section)
            db.commit()

            # Publish a new version.
            max_version = (
                db.query(models.CmsPageVersion)
                .filter_by(page_id=page.id)
                .order_by(models.CmsPageVersion.version_number.desc())
                .first()
            )
            next_version = (max_version.version_number + 1) if max_version else 1

            version = models.CmsPageVersion(
                page_id=page.id,
                version_number=next_version,
                snapshot_json=_snapshot(page, section_specs),
                notes="Seed detail_template section",
            )
            db.add(version)
            db.commit()
            db.refresh(version)

            page.published_version_id = version.id
            page.status = "published"
            db.add(page)
            db.commit()

            updated += 1
            published += 1
            print(f"Updated {slug}: detail_template section, published version {next_version}")

        print(f"\nDone: {updated} pages updated, {published} versions published")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
