import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
import os
import sys

from sqlalchemy.orm import Session

# Add the root project directory to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal
from backend.models import PageContent


def seed_ccf_pages():
    print("Iniciando Seed de Páginas Públicas de FARO (Actualización de Feeds)...")
    db: Session = SessionLocal()

    ccf_blocks = [
        {
            "key": "ccf_home_hero",
            "title": "Inicio hero",
            "content": json.dumps(
                {
                    "eyebrow": "UNA COMUNIDAD QUE ILUMINA",
                    "title_lead": "Somos El Faro,",
                    "title_accent": "Tu Refugio",
                    "title_tail": "Y Tu Guía.",
                    "description": "Somos un ccf de luz que ilumina y guía con amor, que salva vidas y restaura el alma; un puerto seguro que acompaña a cada persona a reencontrarse con su propósito en Dios. Bienvenido a casa.",
                    "primary_cta": "Conocer a Jesús",
                    "secondary_cta": "Ver Prédicas",
                }
            ),
        },
        {
            "key": "ccf_discover_hero",
            "title": "Conocer a Jesus hero",
            "content": json.dumps(
                {
                    "eyebrow": "EL PRIMER PASO DE TU VIAJE",
                    "title_lead": "La luz que ",
                    "title_accent": "Salva ",
                    "title_tail": "Vidas.",
                    "description": "No estás aquí por accidente. Si estás cansado o buscas respuestas, este es el puerto seguro para ti. Descubre el descanso y la libertad que Jesús tiene para ofrecerte hoy.",
                    "cta": "Quiero hablar con alguien",
                }
            ),
        },
        {
            "key": "ccf_about_hero",
            "title": "Nosotros hero",
            "content": json.dumps(
                {
                    "eyebrow": "NUESTRA VERDADERA IDENTIDAD",
                    "title_lead": "Un Hospital ",
                    "title_accent": "Para el Alma",
                    "description": "Creemos en la conexión espiritual, en amar incondicionalmente y en restaurar vidas. No somos solo un edificio, somos una familia que te acompaña en todo momento.",
                }
            ),
        },
        {
            "key": "ccf_testimonios_hero",
            "title": "Testimonios hero",
            "content": json.dumps(
                {
                    "eyebrow": "LA LUZ EN ACCIÓN",
                    "title_lead": "Historias de ",
                    "title_accent": "Verdadera Sanidad",
                    "description": "No somos perfectos, somos personas reales transformadas por un amor radical y abundante. Lee cómo la gracia nos alcanzó.",
                }
            ),
        },
        {
            "key": "ccf_events_hero",
            "title": "Eventos hero",
            "content": json.dumps(
                {
                    "eyebrow": "ENCUENTROS DE CONEXIÓN",
                    "title": "Momentos para Crecer",
                    "description": "Sumérgete en nuestra comunidad. Descubre reuniones presenciales y online, células y actividades diseñadas para tu crecimiento espiritual integral.",
                }
            ),
        },
        {
            "key": "ccf_sermons_hero",
            "title": "Predicas hero",
            "content": json.dumps(
                {
                    "eyebrow": "ESCUCHA ACTIVA",
                    "title_lead": "Sabiduría y ",
                    "title_accent": "Esperanza",
                    "description": "Mensajes claros, coherentes e inspirados para alimentar tu alma y darte herramientas prácticas cada semana.",
                }
            ),
        },
        {
            "key": "ccf_courses_hero",
            "title": "Cursos hero",
            "content": json.dumps(
                {
                    "eyebrow": "FORMACIÓN ESPIRITUAL",
                    "title_lead": "Crece en tu ",
                    "title_accent": "Fundamento",
                    "description": "Explora nuestra Academia y librería. Cursos dinámicos para conocer mejor la Biblia y afianzar tu identidad con fundamentos sólidos.",
                }
            ),
        },
        {
            "key": "ccf_locations_hero",
            "title": "Sedes hero",
            "content": json.dumps(
                {
                    "eyebrow": "MÁXIMA ACCESIBILIDAD",
                    "title": "Cerca de Ti",
                    "search_placeholder": "Busca tu refugio más cercano...",
                }
            ),
        },
        # --- NEW FEEDS ---
        {
            "key": "ccf_testimonials_feed",
            "title": "Testimonios Feed",
            "content": json.dumps(
                [
                    {
                        "id": 1,
                        "content": "Mi matrimonio estaba destruído y aquí encontré el apoyo pastoral que nos enseñó a perdonar. Fue un verdadero hospital para nuestra familia.",
                        "emotion": "Sanidad Restaurada",
                        "author": {"username": "Andrés & Valeria"},
                        "featured": True,
                    },
                    {
                        "id": 2,
                        "content": "Llegué buscando respuestas. La gracia sin condenas que predican me dio esperanza real y paz sobre mi futuro.",
                        "emotion": "Descanso",
                        "author": {"username": "Camila G."},
                    },
                    {
                        "id": 3,
                        "content": "Llevaba mucho tiempo sintiendo soledad. En FARO hallé una comunidad que me cuidó y donde hoy también sirvo a otros.",
                        "emotion": "Compañerismo Genuino",
                        "author": {"username": "Esteban R."},
                    },
                    {
                        "id": 4,
                        "content": "Las enseñanzas de la Academia y cada sermón tienen un impacto práctico increíble. Hoy sé cuál es mi propósito.",
                        "emotion": "Propósito Descubierto",
                        "author": {"username": "Luisa F."},
                    },
                ]
            ),
        },
        {
            "key": "ccf_public_events",
            "title": "Eventos Feed",
            "content": json.dumps(
                [
                    {
                        "title": "Noche de Iluminación: Adoración",
                        "date": "24 DE AGOSTO, 2026",
                        "location": "Auditorio Sede Central",
                        "excerpt": "Una experiencia inmersiva de adoración donde la presencia de Dios es palpable.",
                        "category": "Especiales",
                        "featured": True,
                        "img": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&q=80",
                    },
                    {
                        "title": "Jornada de Liderazgo",
                        "date": "10 DE SEPTIEMBRE, 2026",
                        "location": "Sede Norte",
                        "excerpt": "Herramientas de servicio y excelencia para pastores, líderes de célula y voluntarios.",
                        "category": "Conferencias",
                        "featured": False,
                        "img": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=600&q=80",
                    },
                    {
                        "title": "Reunión de Crecimiento",
                        "date": "CADA MIÉRCOLES",
                        "location": "Vía Zoom",
                        "excerpt": "Profundidad teológica en grupos pequeños.",
                        "category": "Grupos de Conexión",
                        "featured": False,
                        "img": "https://images.unsplash.com/photo-1447690709975-318628b14c57?w=600&q=80",
                    },
                ]
            ),
        },
        {
            "key": "ccf_sermons_feed",
            "title": "Prédicas Feed",
            "content": json.dumps(
                [
                    {
                        "title": "Renacer: Luz en la oscuridad",
                        "speaker": "Pr. David Mendoza",
                        "duration": "45 min",
                        "series": "Temporada de Cosecha",
                        "thumbnail": "https://images.unsplash.com/photo-1542614482-eb06198f3b14?w=800&q=80",
                        "category": "Fe",
                        "featured": True,
                    },
                    {
                        "title": "La Paz que sobrepasa todo entendimiento",
                        "speaker": "Pr. Sara Mendoza",
                        "duration": "32 min",
                        "series": "Salud Emocional",
                        "thumbnail": "https://images.unsplash.com/photo-1483808161634-29aa1b1ecfc9?w=800&q=80",
                        "category": "Sanidad",
                    },
                    {
                        "title": "Una Comunidad Auténtica",
                        "speaker": "Ps. Jóvenes",
                        "duration": "28 min",
                        "series": "Identidad FARO",
                        "thumbnail": "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=800&q=80",
                        "category": "Relaciones",
                    },
                ]
            ),
        },
        {
            "key": "ccf_courses_feed",
            "title": "Cursos Feed",
            "content": json.dumps(
                [
                    {
                        "title": "Fundamentos de la Fe",
                        "lessons": 12,
                        "modality": "Virtual",
                        "excerpt": "Descubre los pilares de la fe cristiana y cómo aplicarlos en tu vida diaria.",
                        "image": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=500&q=80",
                    },
                    {
                        "title": "Liderazgo y Servicio",
                        "lessons": 8,
                        "modality": "Presencial",
                        "excerpt": "Aprende a servir con pasión y excelencia dentro del ecosistema de la iglesia.",
                        "image": "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=500&q=80",
                    },
                ]
            ),
        },
        {
            "key": "ccf_locations_feed",
            "title": "Sedes Feed",
            "content": json.dumps(
                [
                    {
                        "name": "Sede Central (Faro Principal)",
                        "address": "Av. Esperanza 124, Centro Financiero",
                        "services": ["Domingos 9 AM y 11 AM", "Lunes 7 PM"],
                        "pastor": "David & Sara Mendoza",
                        "phone": "+57 320 000 0000",
                    },
                    {
                        "name": "Campus Norte",
                        "address": "Calle 170 #54-12, Sector Universitario",
                        "services": ["Sábados 6 PM (Jóvenes)", "Domingos 10 AM"],
                        "pastor": "Sebastián Vargas",
                        "phone": "+57 310 111 2222",
                    },
                ]
            ),
        },
    ]

    try:
        inserted = 0
        updated = 0
        for block in ccf_blocks:
            existing = (
                db.query(PageContent)
                .filter(PageContent.page_key == block["key"])
                .first()
            )
            if existing:
                existing.content = block["content"]
                updated += 1
            else:
                new_page = PageContent(
                    page_key=block["key"],
                    title=block["title"],
                    content=block["content"],
                )
                db.add(new_page)
                inserted += 1

        db.commit()
        print(
            f"✅ ¡Seed completado con éxito! {inserted} nuevos bloques insertados, {updated} actualizados."
        )
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el seed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_ccf_pages()
