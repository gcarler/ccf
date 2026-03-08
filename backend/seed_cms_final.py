import sqlite3
import json
import datetime as dt

# Path
SQLITE_DB = 'd:/ccf/ccf_v2.db'

def seed_final_content():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # 1. Page Contents (Legal, Support, Donation)
    page_contents = [
        # Privacy Policy
        ('privacy_policy', json.dumps({
            "title": "Política de Privacidad CCF",
            "subtitle": "Comprometidos con la seguridad de tu información espiritual y personal.",
            "content": "## Recopilación de Información\nRecopilamos datos para fortalecer la comunión y el seguimiento pastoral de manera segura.\n\n## Uso de Datos\nMejora de servicios académicos, pastorales y de comunicación directa con el miembro."
        })),
        # Terms of Service
        ('terms_of_service', json.dumps({
            "title": "Términos de Servicio",
            "last_update": "12 de Marzo, 2026",
            "content": "## 1. Aceptación\nAl usar esta plataforma moderna, aceptas nuestros lineamientos de convivencia y formación.\n\n## 2. Uso Responsable\nLa academia es un espacio sagrado para el crecimiento ministerial y personal."
        })),
        # Support
        ('support_page', json.dumps({
            "title": "Centro de Ayuda",
            "description": "Estamos aquí para asistirte en cada paso de tu formación.",
            "categories": [
                {"title": "Soporte Técnico", "desc": "Dudas sobre acceso y contraseñas.", "type": "tech"},
                {"title": "Academia", "desc": "Preguntas sobre certificados y cursos.", "type": "academic"},
                {"title": "Pastoral", "desc": "Líneas de atención espiritual.", "type": "pastoral"}
            ]
        })),
        # Donation Categories
        ('donation_types', json.dumps({
            "categories": [
                {"id": "Diezmo", "label": "Diezmo Fiel", "icon": "Building"},
                {"id": "Ofrenda", "label": "Ofrenda de Gratitud", "icon": "Heart"},
                {"id": "Misiones", "label": "Misiones Mundiales", "icon": "Globe"}
            ]
        })),
        # Academy Hero
        ('academy_hero', json.dumps({
            "title": "Academia Bíblica El Faro",
            "subtitle": "Formación teológica y ministerial de excelencia para el liderazgo del mañana."
        })),
        ('academy_welcome_sub', json.dumps({
            "content": "Bienvenido a tu portal de crecimiento. Aquí encontrarás los cursos diseñados para llevar tu fe al siguiente nivel."
        })),
        # Onboarding
        ('onboarding_page', json.dumps({
            "steps": [
                {
                    "id": 1,
                    "title": "Herramientas para tu fe",
                    "description": "Diseñamos un espacio digital para acompañarte en cada paso de tu caminar cristiano.",
                    "features": [
                        {"title": "Crecimiento", "desc": "Fortalece tu espíritu con recursos y lecciones bíblicas.", "icon": "BookOpen"},
                        {"title": "Comunidad", "desc": "Conecta con grupos de vida y eventos locales.", "icon": "Users"},
                        {"title": "Propósito", "desc": "Encuentra y sirve según el plan de Dios para ti.", "icon": "Heart"}
                    ]
                }
            ]
        })),
        # Sample Dynamic Page (Vision)
        ('page_vision', json.dumps({
            "title": "Nuestra Visión 2030",
            "subtitle": "Hacia una iglesia que trasciende límites y transforma ciudades.",
            "image": "https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=800",
            "content": "Nuestra visión es ser un faro de esperanza para toda la región del Putumayo y el mundo.\n\nCreemos en una iglesia:\n- Centrada en la presencia de Dios.\n- Comprometida con la excelencia académica.\n- Radical en su amor por los perdidos.\n- Moderna en sus métodos, eterna en su mensaje.\n\nDurante los próximos años, nos enfocaremos en expandir nuestra presencia digital y física, llevando el mensaje de Cristo a cada rincón del departamento.",
            "cta": True,
            "cta_title": "¿Quieres ser parte de esta visión?",
            "cta_label": "Unirse a un Grupo",
            "cta_link": "/groups"
        })),
        # Home Page refinements
        ('home_hero', json.dumps({
            "title": "Transformando Vidas a través de la Palabra",
            "subtitle": "Únete a una comunidad vibrante y moderna en busca de la presencia de Dios.",
            "cta_primary": "Empezar Ahora",
            "cta_secondary": "Ver Prédicas"
        })),
        # Navbar Items
        ('navbar_items', json.dumps({
            "items": [
                {"label": "Inicio", "href": "/"},
                {"label": "Academia", "href": "/academy"},
                {"label": "Prédicas", "href": "/sermons"},
                {"label": "Libros", "href": "/books"},
                {"label": "Testimonios", "href": "/testimonials"},
                {"label": "Eventos", "href": "/events"},
                {"label": "Grupos", "href": "/groups"},
                {"label": "Visión", "href": "/p/vision"}
            ]
        }))
    ]
    
    # Clear existing to avoid duplicates if necessary, or use REPLACE
    for key, content in page_contents:
        cursor.execute("INSERT OR REPLACE INTO page_contents (page_key, content) VALUES (?, ?)", (key, content))

    # 2. Events (Schema check: name, description, event_type, fixed_date)
    cursor.execute("DELETE FROM events")
    now = dt.datetime.utcnow()
    events = [
        ("Noche de Alabanza Profética", "Un tiempo de adoración profunda en nuestra sede central.", "Servicio", (now + dt.timedelta(days=2)).isoformat()),
        ("Congreso 'Fuego Cruzado'", "Evento especial para jóvenes con invitados nacionales. ¡No te lo pierdas!", "Congreso", (now + dt.timedelta(days=15)).isoformat()),
        ("Estudio Bíblico: Fundamentos", "Módulo intensivo sobre las bases de la fe cristiana para nuevos líderes.", "Academia", (now + dt.timedelta(days=7)).isoformat())
    ]
    cursor.executemany("""
        INSERT INTO events (name, description, event_type, fixed_date)
        VALUES (?, ?, ?, ?)
    """, events)

    # 3. Glory Houses (Groups) (Schema check: name, zone, leader_name, members_count, schedule)
    cursor.execute("DELETE FROM glory_houses")
    houses = [
        ("Casa de Paz Norte", "Zona Norte", "Familia Gómez", 12, "Jueves, 19:30"),
        ("Betel Centro", "Zona Centro", "Pastor David", 15, "Miércoles, 19:00"),
        ("Renuevo Sur", "Zona Sur", "Ana Martínez", 8, "Viernes, 20:00"),
        ("Sión Occidente", "Zona Occidente", "Carlos Ruiz", 10, "Sábado, 18:00")
    ]
    cursor.executemany("""
        INSERT INTO glory_houses (name, zone, leader_name, members_count, schedule)
        VALUES (?, ?, ?, ?, ?)
    """, houses)

    conn.commit()
    conn.close()
    print("🚀 Final CCF Content seeded 100%.")

if __name__ == "__main__":
    seed_final_content()
