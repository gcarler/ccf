import json
import sqlite3

db_path = "d:/ccf/ccf_v2.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


def ensure_tables():
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        content TEXT NOT NULL,
        image_url VARCHAR,
        category VARCHAR DEFAULT 'General' NOT NULL,
        is_active BOOLEAN DEFAULT 1 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS sermons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        description TEXT,
        preacher VARCHAR NOT NULL,
        video_url VARCHAR,
        audio_url VARCHAR,
        thumbnail_url VARCHAR,
        duration VARCHAR,
        date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        views INTEGER DEFAULT 0 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        description TEXT,
        author VARCHAR NOT NULL,
        cover_image_url VARCHAR,
        download_url VARCHAR,
        is_published BOOLEAN DEFAULT 1 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS testimonials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        emotion VARCHAR,
        is_approved BOOLEAN DEFAULT 0 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY(author_id) REFERENCES users(id)
    );
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS page_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_key VARCHAR UNIQUE NOT NULL,
        title VARCHAR,
        content TEXT,
        image_url VARCHAR,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    )
    conn.commit()


ALLOWED_TABLES = {"announcements", "sermons", "books", "testimonials", "page_contents"}


def clean_tables():
    for table in sorted(ALLOWED_TABLES):
        cursor.execute(f'DELETE FROM "{table}"')
    conn.commit()


def seed_announcements():
    announcements = [
        (
            "Nueva Serie: Caminando en la Luz",
            "??nete a nosotros este domingo para el inicio de nuestra nueva serie de ense??anzas sobre la Primera Ep??stola de Juan.",
            "https://images.unsplash.com/photo-1438032005730-c779502df39b?auto=format&fit=crop&q=80",
            "Serie Dominical",
        ),
        (
            "Retiro de J??venes: Sin Filtro",
            "Inscripciones abiertas para nuestro pr??ximo retiro anual de j??venes en la monta??a. Cupos limitados.",
            "https://images.unsplash.com/photo-1523580494863-6f3031224c94?auto=format&fit=crop&q=80",
            "Eventos",
        ),
        (
            "Inscripciones Academia Faro 2026",
            "Ya puedes inscribirte en los niveles 1 a 4 de nuestra formaci??n teol??gica ministerial.",
            "https://images.unsplash.com/photo-1541339907198-e08756edd811?auto=format&fit=crop&q=80",
            "Academia",
        ),
    ]
    cursor.executemany(
        "INSERT INTO announcements (title, content, image_url, category) VALUES (?, ?, ?, ?)",
        announcements,
    )
    conn.commit()


def seed_sermons():
    sermons = [
        (
            "??C??mo vencer el miedo?",
            "Una ense??anza poderosa sobre la confianza en Dios en tiempos de incertidumbre.",
            "Pr. Juan Delgado",
            "https://www.youtube.com/watch?v=Nn_E_8y62_g",
            "42:15",
            "https://img.youtube.com/vi/Nn_E_8y62_g/maxresdefault.jpg",
        ),
        (
            "El poder de tu testimonio",
            "Descubre c??mo tu historia personal puede impactar la vida de otros para el Reino.",
            "Ps. Carlos M??ndez",
            "https://www.youtube.com/watch?v=R9K1Xp2uG5g",
            "38:40",
            "https://img.youtube.com/vi/R9K1Xp2uG5g/maxresdefault.jpg",
        ),
        (
            "Caminando en fe",
            "No por vista, sino por fe. C??mo dar pasos firmes cuando el camino es incierto.",
            "Ps. Roberto Silva",
            "https://www.youtube.com/watch?v=V-X-NnXvW6s",
            "45:10",
            "https://img.youtube.com/vi/V-X-NnXvW6s/maxresdefault.jpg",
        ),
    ]
    cursor.executemany(
        "INSERT INTO sermons (title, description, preacher, video_url, duration, thumbnail_url) VALUES (?, ?, ?, ?, ?, ?)",
        sermons,
    )
    conn.commit()


def seed_books():
    books = [
        (
            "Vida con Prop??sito",
            "Un viaje espiritual de 40 d??as para descubrir por qu?? est??s aqu??.",
            "Rick Warren",
            "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80",
            "#",
        ),
        (
            "El Regreso del Hijo Pr??digo",
            "Meditaciones sobre el hogar, el regreso y el abrazo del Padre.",
            "Henri Nouwen",
            "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?auto=format&fit=crop&q=80",
            "#",
        ),
        (
            "Fundamentos Teol??gicos",
            "Bases s??lidas para el creyente moderno.",
            "J.I. Packer",
            "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&q=80",
            "#",
        ),
    ]
    cursor.executemany(
        "INSERT INTO books (title, description, author, cover_image_url, download_url) VALUES (?, ?, ?, ?, ?)",
        books,
    )
    conn.commit()


def seed_testimonials():
    testimonials = [
        (
            1,
            "Desde que llegu?? a CC El Faro, mi familia ha encontrado un prop??sito real. La comunidad nos abraz?? en nuestro momento m??s dif??cil.",
            "Agradecimiento",
        ),
        (
            1,
            "Literalmente vi la mano de Dios sanando mi cuerpo despu??s de una oraci??n un??nime en mi Faro en Casa.",
            "Sanidad",
        ),
        (
            1,
            "La Academia Faro me dio las herramientas teol??gicas que necesitaba para servir con excelencia en el ministerio de alabanza.",
            "Crecimiento",
        ),
    ]
    cursor.executemany(
        "INSERT INTO testimonials (author_id, content, emotion, is_approved) VALUES (?, ?, ?, 1)",
        testimonials,
    )
    conn.commit()


def seed_page_contents():
    contents = [
        # Home
        (
            "home_hero",
            "Servicio de Adoraci??n Dominical",
            "??nete a nuestra transmisi??n en vivo y experimenta la presencia de Dios desde donde est??s.",
            "https://images.unsplash.com/photo-1438032005730-c779502df39b?auto=format&fit=crop&q=80",
        ),
        (
            "home_academy_card",
            "Academia Faro",
            "Formaci??n teol??gica y ministerial profunda para el liderazgo del siglo XXI.",
            None,
        ),
        (
            "home_giving_card",
            "Ofrendar",
            "Tu generosidad permite que el mensaje de esperanza llegue a m??s corazones.",
            None,
        ),
        (
            "home_community_card",
            "Comunidad",
            "Encuentra tu lugar en un Faro en Casa y crece junto a otros creyentes.",
            None,
        ),
        (
            "home_prayer_banner",
            "Peticiones de Oraci??n",
            "??Podemos orar por ti hoy? Env??anos tu petici??n y nos uniremos en fe por tu milagro.",
            None,
        ),
        (
            "home_impact_stats",
            "Impacto Ministerial",
            json.dumps({"courses": 15, "impact": "2.8k", "churches": 4}),
            None,
        ),
        # Academy
        (
            "academy_hero",
            "Contin??a tu Formaci??n",
            "Explora nuestro cat??logo de cursos dise??ados para equiparte en tu caminar con Cristo.",
            None,
        ),
        (
            "academy_welcome_sub",
            "Portal Estudiantil",
            "Nos alegra tenerte de vuelta. Tu crecimiento espiritual es nuestra prioridad.",
            None,
        ),
        # Sermons Page
        (
            "sermons_hero",
            "Mensajes y Ense??anzas",
            "Busca y encuentra la palabra que Dios tiene para ti en nuestra biblioteca de pr??dicas.",
            None,
        ),
        # Books Page
        (
            "books_hero",
            "Biblioteca Digital",
            "Recursos seleccionados para profundizar en tu estudio b??blico y crecimiento personal.",
            None,
        ),
        # Testimonials
        (
            "testimonials_hero",
            "Muro de Testimonios",
            "Historias reales de transformaci??n, sanidad y el obrar de Dios en nuestra comunidad.",
            None,
        ),
        # Footer
        (
            "footer_info",
            "CC El Faro",
            "Un faro de esperanza en la ciudad. Transformando vidas a trav??s del Evangelio de Jesucristo.",
            None,
        ),
    ]
    cursor.executemany(
        "INSERT INTO page_contents (page_key, title, content, image_url) VALUES (?, ?, ?, ?)",
        contents,
    )
    conn.commit()


if __name__ == "__main__":
    print(
        "Forcing table creation and seeding ALL website content (including sub-pages)..."
    )
    ensure_tables()
    clean_tables()
    seed_announcements()
    seed_sermons()
    seed_books()
    seed_testimonials()
    seed_page_contents()
    conn.close()
    print("Full CMS seeding completed successfully.")
