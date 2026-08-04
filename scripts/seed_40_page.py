#!/usr/bin/env python3
import json
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

from backend.models import CmsPage, CmsSite, CmsSection

def seed_40_page():
    db = SessionLocal()
    try:
        # Find the main CCF site
        site = db.query(CmsSite).filter_by(site_key="ccf").first()
        if not site:
            print("Site 'ccf' not found")
            return
        
        # Check if page already exists
        page = db.query(CmsPage).filter_by(site_id=site.id, slug="40").first()
        if not page:
            page = CmsPage(
                id=uuid.uuid4(),
                site_id=site.id,
                slug="40",
                title="40 Años Iluminando Generaciones",
                status="draft",
                locale="es",
                seo_json={"title": "40 Años Iluminando Generaciones", "description": "Celebra con nosotros cuatro décadas de luz en la Comunidad Cristiana CCF."}
            )
            db.add(page)
            db.flush()
            print("Created CmsPage '40'")
        else:
            print("CmsPage '40' already exists")

        # Define the sections
        sections_data = [
            {
                "section_key": "hero",
                "type": "video_hero",
                "sort_order": 0,
                "props_json": {
                    "eyebrow": "40 ANIVERSARIO",
                    "title_lead": "Celebra con nosotros",
                    "title_accent": "cuatro décadas",
                    "title_tail": "de luz.",
                    "description": "Una historia de fe, familia y transformación. Sé parte de este hito histórico de la Comunidad Cristiana Faro.",
                    "primary_cta": "Registra tu asistencia",
                    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
                }
            },
            {
                "section_key": "agenda",
                "type": "rich_text",
                "sort_order": 1,
                "props_json": {
                    "vision_title": "Agenda de Celebración",
                    "vision_text": "Todo el mes de agosto estaremos conmemorando nuestros 40 años, pero los eventos principales se llevarán a cabo en 3 días clave. ¡Acompáñanos!\n\n**21 de Agosto:** Servicio de Milagros (7:00 PM)\n**22 de Agosto:** Conferencia para Líderes y Servidores (8:00 AM a 12:00 PM)\n**23 de Agosto:** Servicio Dominical de Aniversario (9:00 AM)",
                }
            },
            {
                "section_key": "timeline",
                "type": "timeline",
                "sort_order": 1,
                "props_json": {
                    "eyebrow": "Nuestra Historia",
                    "title": "40 Años de Fidelidad",
                    "events": [
                        {"year": "1986", "title": "El Comienzo", "description": "Un pequeño grupo de familias se reúne con una visión gigante."}
                    ]
                }
            },
            {
                "section_key": "muro-gratitud",
                "type": "contact_form",
                "sort_order": 2,
                "props_json": {
                    "eyebrow": "Muro de Gratitud",
                    "title": "¿Cómo ha transformado Dios tu vida en El Faro?",
                    "description": "Comparte tu testimonio. Tu historia es parte de nuestra historia.",
                    "name_label": "Tu nombre",
                    "message_label": "Tu testimonio",
                    "submit_label": "Enviar testimonio"
                }
            },
            {
                "section_key": "galeria",
                "type": "embed",
                "sort_order": 3,
                "props_json": {
                    "html": "<iframe src='https://photos.app.goo.gl/CTHj2bbSZsDY3pjH9' width='100%' height='600' style='border:none;'></iframe>"
                }
            }
        ]

        # Insert or update sections
        for s_data in sections_data:
            section = db.query(CmsSection).filter_by(page_id=page.id, section_key=s_data["section_key"]).first()
            if not section:
                section = CmsSection(
                    id=uuid.uuid4(),
                    page_id=page.id,
                    section_key=s_data["section_key"],
                    type=s_data["type"],
                    sort_order=s_data["sort_order"],
                    props_json=s_data["props_json"],
                    status="active"
                )
                db.add(section)
                print(f"Created CmsSection '{s_data['section_key']}'")
            else:
                section.type = s_data["type"]
                section.sort_order = s_data["sort_order"]
                section.props_json = s_data["props_json"]
                print(f"Updated CmsSection '{s_data['section_key']}'")
        
        db.commit()
        print("Done successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_40_page()
