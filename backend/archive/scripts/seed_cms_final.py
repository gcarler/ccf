import datetime as dt
import json
import sqlite3

# Path
SQLITE_DB = "d:/ccf/ccf_v2.db"


def seed_final_content():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    # 1. Page Contents (Legal, Support, Donation)
    page_contents = [
        # Privacy Policy
        (
            "privacy_policy",
            json.dumps(
                {
                    "title": "Pol??tica de Privacidad CCF",
                    "subtitle": "Comprometidos con la seguridad de tu informaci??n espiritual y personal.",
                    "content": "## Recopilaci??n de Informaci??n\nRecopilamos datos para fortalecer la comuni??n y el seguimiento pastoral de manera segura.\n\n## Uso de Datos\nMejora de servicios acad??micos, pastorales y de comunicaci??n directa con el miembro.",
                }
            ),
        ),
        # Terms of Service
        (
            "terms_of_service",
            json.dumps(
                {
                    "title": "T??rminos de Servicio",
                    "last_update": "12 de Marzo, 2026",
                    "content": "## 1. Aceptaci??n\nAl usar esta plataforma moderna, aceptas nuestros lineamientos de convivencia y formaci??n.\n\n## 2. Uso Responsable\nLa academia es un espacio sagrado para el crecimiento ministerial y personal.",
                }
            ),
        ),
        # Support
        (
            "support_page",
            json.dumps(
                {
                    "title": "Centro de Ayuda",
                    "description": "Estamos aqu?? para asistirte en cada paso de tu formaci??n.",
                    "categories": [
                        {
                            "title": "Soporte T??cnico",
                            "desc": "Dudas sobre acceso y contrase??as.",
                            "type": "tech",
                        },
                        {
                            "title": "Academia",
                            "desc": "Preguntas sobre certificados y cursos.",
                            "type": "academic",
                        },
                        {
                            "title": "Pastoral",
                            "desc": "L??neas de atenci??n espiritual.",
                            "type": "pastoral",
                        },
                    ],
                }
            ),
        ),
        # Donation Categories
        (
            "donation_types",
            json.dumps(
                {
                    "categories": [
                        {"id": "Diezmo", "label": "Diezmo Fiel", "icon": "Building"},
                        {
                            "id": "Ofrenda",
                            "label": "Ofrenda de Gratitud",
                            "icon": "Heart",
                        },
                        {
                            "id": "Misiones",
                            "label": "Misiones Mundiales",
                            "icon": "Globe",
                        },
                    ]
                }
            ),
        ),
        # Academy Hero
        (
            "academy_hero",
            json.dumps(
                {
                    "title": "Academia B??blica El Faro",
                    "subtitle": "Formaci??n teol??gica y ministerial de excelencia para el liderazgo del ma??ana.",
                }
            ),
        ),
        (
            "academy_welcome_sub",
            json.dumps(
                {
                    "content": "Bienvenido a tu portal de crecimiento. Aqu?? encontrar??s los cursos dise??ados para llevar tu fe al siguiente nivel."
                }
            ),
        ),
        # Onboarding
        (
            "onboarding_page",
            json.dumps(
                {
                    "steps": [
                        {
                            "id": 1,
                            "title": "Herramientas para tu fe",
                            "description": "Dise??amos un espacio digital para acompa??arte en cada paso de tu caminar cristiano.",
                            "features": [
                                {
                                    "title": "Crecimiento",
                                    "desc": "Fortalece tu esp??ritu con recursos y lecciones b??blicas.",
                                    "icon": "BookOpen",
                                },
                                {
                                    "title": "Comunidad",
                                    "desc": "Conecta con grupos de vida y eventos locales.",
                                    "icon": "Users",
                                },
                                {
                                    "title": "Prop??sito",
                                    "desc": "Encuentra y sirve seg??n el plan de Dios para ti.",
                                    "icon": "Heart",
                                },
                            ],
                        }
                    ]
                }
            ),
        ),
        # Sample Dynamic Page (Vision)
        (
            "page_vision",
            json.dumps(
                {
                    "title": "Nuestra Visi??n 2030",
                    "subtitle": "Hacia una iglesia que trasciende l??mites y transforma ciudades.",
                    "image": "https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=800",
                    "content": "Nuestra visi??n es ser un faro de esperanza para toda la regi??n del Putumayo y el mundo.\n\nCreemos en una iglesia:\n- Centrada en la presencia de Dios.\n- Comprometida con la excelencia acad??mica.\n- Radical en su amor por los perdidos.\n- Moderna en sus m??todos, eterna en su mensaje.\n\nDurante los pr??ximos a??os, nos enfocaremos en expandir nuestra presencia digital y f??sica, llevando el mensaje de Cristo a cada rinc??n del departamento.",
                    "cta": True,
                    "cta_title": "??Quieres ser parte de esta visi??n?",
                    "cta_label": "Unirse a un Grupo",
                    "cta_link": "/groups",
                }
            ),
        ),
        # Home Page refinements
        (
            "home_hero",
            json.dumps(
                {
                    "title": "Transformando Vidas a trav??s de la Palabra",
                    "subtitle": "??nete a una comunidad vibrante y moderna en busca de la presencia de Dios.",
                    "cta_primary": "Empezar Ahora",
                    "cta_secondary": "Ver Pr??dicas",
                }
            ),
        ),
        # Navbar Items
        (
            "navbar_items",
            json.dumps(
                {
                    "items": [
                        {"label": "Inicio", "href": "/"},
                        {"label": "Academia", "href": "/academy"},
                        {"label": "Pr??dicas", "href": "/sermons"},
                        {"label": "Libros", "href": "/books"},
                        {"label": "Testimonios", "href": "/testimonials"},
                        {"label": "Eventos", "href": "/events"},
                        {"label": "Grupos", "href": "/groups"},
                        {"label": "Visi??n", "href": "/p/vision"},
                    ]
                }
            ),
        ),
    ]

    # Clear existing to avoid duplicates if necessary, or use REPLACE
    for key, content in page_contents:
        cursor.execute(
            "INSERT OR REPLACE INTO page_contents (page_key, content) VALUES (?, ?)",
            (key, content),
        )

    # 2. Events (Schema check: name, description, event_type, fixed_date)
    cursor.execute("DELETE FROM events")
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    events = [
        (
            "Noche de Alabanza Prof??tica",
            "Un tiempo de adoraci??n profunda en nuestra sede central.",
            "Servicio",
            (now + dt.timedelta(days=2)).isoformat(),
        ),
        (
            "Congreso 'Fuego Cruzado'",
            "Evento especial para j??venes con invitados nacionales. ??No te lo pierdas!",
            "Congreso",
            (now + dt.timedelta(days=15)).isoformat(),
        ),
        (
            "Estudio B??blico: Fundamentos",
            "M??dulo intensivo sobre las bases de la fe cristiana para nuevos l??deres.",
            "Academia",
            (now + dt.timedelta(days=7)).isoformat(),
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO events (name, description, event_type, fixed_date)
        VALUES (?, ?, ?, ?)
    """,
        events,
    )

    # 3. Glory Houses (Groups) (Schema check: name, zone, leader_name, members_count, schedule)
    cursor.execute("DELETE FROM glory_houses")
    houses = [
        ("Casa de Paz Norte", "Zona Norte", "Familia G??mez", 12, "Jueves, 19:30"),
        ("Betel Centro", "Zona Centro", "Pastor David", 15, "Mi??rcoles, 19:00"),
        ("Renuevo Sur", "Zona Sur", "Ana Mart??nez", 8, "Viernes, 20:00"),
        ("Si??n Occidente", "Zona Occidente", "Carlos Ruiz", 10, "S??bado, 18:00"),
    ]
    cursor.executemany(
        """
        INSERT INTO glory_houses (name, zone, leader_name, members_count, schedule)
        VALUES (?, ?, ?, ?, ?)
    """,
        houses,
    )

    conn.commit()
    conn.close()
    print("???? Final CCF Content seeded 100%.")


if __name__ == "__main__":
    seed_final_content()
