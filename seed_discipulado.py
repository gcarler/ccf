import sys, os
sys.path.insert(0, '/root/ccf')
from backend.core.database import SessionLocal
import backend.models
from backend.models_academy_core import Course, Lesson
from sqlalchemy import text

def seed_discipulado():
    with SessionLocal() as db:
        SEDE_ID = db.execute(text("SELECT id FROM sedes LIMIT 1")).scalar()
        if not SEDE_ID:
            print("No sede found")
            return
            
        course = db.query(Course).filter(Course.slug == "discipulado-basico-ccf").first()
        if not course:
            course = Course(slug="discipulado-basico-ccf", sede_id=SEDE_ID)
            db.add(course)
            
        course.code = "CCF-DIS-01"
        course.title = "Discipulado Básico CCF"
        course.tag = "Crecimiento"
        course.modality = "Presencial & Online"
        course.duration_hours = 12
        course.instructor_name = "Pastor Luis Ricardo Meza Gutiérrez"
        course.image_url = "/api/static/cms/external/c419851873dba088a55c2de83974af71.jpg"
        course.excerpt = "Fundamentos de la fe cristiana, el poder del Espíritu Santo y la vida en comunidad."
        course.description = "Un curso esencial para cimentar tu fe en los principios bíblicos del Evangelio. A través de 12 sesiones fundamentales, exploraremos desde el arrepentimiento y la salvación por gracia, hasta el bautismo en agua y la llenura del Espíritu Santo. En CCF, creemos en el poder transformador de Dios para hoy, edificando creyentes firmes en la Palabra y activos en la obra del Reino, lejos de tradiciones vacías y siempre guiados por el Espíritu."
        course.cta_text = "Comenzar Discipulado"
        
        lecciones_data = [
            ("La Salvación por Gracia", "video", 45, "Entendiendo que somos salvos por la fe en Jesucristo mediante el arrepentimiento genuino y no por nuestras obras."),
            ("La Autoridad de la Biblia", "texto", 30, "La Biblia como nuestra única y suficiente regla infalible de fe y conducta, inspirada por Dios."),
            ("La Naturaleza de Dios", "video", 40, "Comprendiendo a Dios como Padre, Hijo y Espíritu Santo: un solo Dios verdadero."),
            ("La Persona de Jesucristo", "video", 45, "Su nacimiento virginal, vida sin pecado, muerte vicaria, resurrección corporal y exaltación."),
            ("El Bautismo en Agua", "video", 40, "El significado bíblico del bautismo por inmersión como un paso esencial de obediencia y testimonio público."),
            ("El Bautismo en el Espíritu Santo", "video", 50, "La promesa del Padre para cada creyente hoy, dotándonos de poder para ser testigos eficaces."),
            ("Los Dones del Espíritu", "texto", 35, "Cómo el Espíritu Santo reparte dones espirituales a la Iglesia para su edificación y para el ministerio."),
            ("La Oración y el Ayuno", "texto", 30, "El valor de las disciplinas espirituales diarias para fortalecer nuestro espíritu y buscar el rostro de Dios."),
            ("La Sanidad Divina", "video", 40, "Creemos que la sanidad divina es una promesa en la expiación de Cristo y es un privilegio de todos los creyentes."),
            ("Mayordomía y Generosidad", "texto", 30, "Honrar a Dios con nuestros recursos, tiempo y talentos a través de diezmos y ofrendas."),
            ("La Familia y la Iglesia Local", "video", 45, "Por qué nos congregamos, servimos y amamos la iglesia local (CCF) como el cuerpo de Cristo."),
            ("La Segunda Venida de Cristo", "video", 45, "Nuestra esperanza bienaventurada: el retorno inminente, personal y visible del Señor Jesucristo.")
        ]
        
        course.syllabus = [ltitle for ltitle, _, _, _ in lecciones_data]
        
        db.commit()
        db.refresh(course)
        
        # Eliminar lecciones anteriores si existen
        db.query(Lesson).filter(Lesson.course_id == course.id).delete()
        
        for i, (ltitle, ltype, ldur, ldesc) in enumerate(lecciones_data, 1):
            lesson = Lesson(
                course_id=course.id,
                title=ltitle,
                content_type=ltype,
                duration_minutes=ldur,
                content=ldesc,
                order_index=i
            )
            db.add(lesson)
            
        db.commit()
        print(f"Course '{course.title}' seeded successfully with 12 lessons.")

if __name__ == "__main__":
    seed_discipulado()
