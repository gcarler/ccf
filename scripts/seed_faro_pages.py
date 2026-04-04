import os
import sys
import json
from sqlalchemy.orm import Session

# Add the root project directory to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal
from backend.models import PageContent

def seed_faro_pages():
    print("Iniciando Seed de Páginas Públicas de FARO...")
    db: Session = SessionLocal()

    faro_blocks = [
        {
            "key": "faro_home_hero",
            "title": "Inicio hero",
            "content": json.dumps({
                "eyebrow": "UNA COMUNIDAD QUE ILUMINA",
                "title_lead": "Somos El Faro,",
                "title_accent": "Tu Refugio",
                "title_tail": "Y Tu Guía.",
                "description": "Somos un faro de luz que ilumina y guía con amor, que salva vidas y restaura el alma; un puerto seguro que acompaña a cada persona a reencontrarse con su propósito en Dios. Bienvenido a casa.",
                "primary_cta": "Conocer a Jesús",
                "secondary_cta": "Ver Prédicas"
            })
        },
        {
            "key": "faro_discover_hero",
            "title": "Conocer a Jesus hero",
            "content": json.dumps({
                "eyebrow": "EL PRIMER PASO DE TU VIAJE",
                "title_lead": "La luz que ",
                "title_accent": "Salva ",
                "title_tail": "Vidas.",
                "description": "No estás aquí por accidente. Si estás cansado o buscas respuestas, este es el puerto seguro para ti. Descubre el descanso y la libertad que Jesús tiene para ofrecerte hoy.",
                "cta": "Quiero hablar con alguien"
            })
        },
        {
            "key": "faro_about_hero",
            "title": "Nosotros hero",
            "content": json.dumps({
                "eyebrow": "NUESTRA VERDADERA IDENTIDAD",
                "title_lead": "Un Hospital ",
                "title_accent": "Para el Alma",
                "description": "Creemos en la conexión espiritual, en amar incondicionalmente y en restaurar vidas. No somos solo un edificio, somos una familia que te acompaña en todo momento."
            })
        },
        {
            "key": "faro_testimonios_hero",
            "title": "Testimonios hero",
            "content": json.dumps({
                "eyebrow": "LA LUZ EN ACCIÓN",
                "title_lead": "Historias de ",
                "title_accent": "Verdadera Sanidad",
                "description": "No somos perfectos, somos personas reales transformadas por un amor radical y abundante. Lee cómo la gracia nos alcanzó."
            })
        },
        {
            "key": "faro_events_hero",
            "title": "Eventos hero",
            "content": json.dumps({
                "eyebrow": "ENCUENTROS DE CONEXIÓN",
                "title": "Momentos para Crecer",
                "description": "Sumérgete en nuestra comunidad. Descubre reuniones presenciales y online, células y actividades diseñadas para tu crecimiento espiritual integral."
            })
        },
        {
            "key": "faro_sermons_hero",
            "title": "Predicas hero",
            "content": json.dumps({
                "eyebrow": "ESCUCHA ACTIVA",
                "title_lead": "Sabiduría y ",
                "title_accent": "Esperanza",
                "description": "Mensajes claros, coherentes e inspirados para alimentar tu alma y darte herramientas prácticas cada semana."
            })
        },
        {
            "key": "faro_courses_hero",
            "title": "Cursos hero",
            "content": json.dumps({
                "eyebrow": "FORMACIÓN ESPIRITUAL",
                "title_lead": "Crece en tu ",
                "title_accent": "Fundamento",
                "description": "Explora nuestra Academia y librería. Cursos dinámicos para conocer mejor la Biblia y afianzar tu identidad con fundamentos sólidos."
            })
        },
        {
            "key": "faro_locations_hero",
            "title": "Sedes hero",
            "content": json.dumps({
                "eyebrow": "MÁXIMA ACCESIBILIDAD",
                "title": "Cerca de Ti",
                "search_placeholder": "Busca tu refugio más cercano..."
            })
        }
    ]

    try:
        inserted = 0
        updated = 0
        for block in faro_blocks:
            existing = db.query(PageContent).filter(PageContent.page_key == block["key"]).first()
            if existing:
                existing.content = block["content"]
                updated += 1
            else:
                new_page = PageContent(
                    page_key=block["key"],
                    title=block["title"],
                    content=block["content"]
                )
                db.add(new_page)
                inserted += 1
        
        db.commit()
        print(f"✅ ¡Seed completado con éxito! {inserted} nuevos bloques insertados, {updated} actualizados.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_faro_pages()
