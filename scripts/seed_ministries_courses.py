
import sys
import os
import random
from datetime import datetime, timedelta

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models, schemas, crud
from backend.core.database import SessionLocal, engine, Base

def seed_ministries_and_courses():
    print("🎭 Iniciando Semilla de Ministerios y Cursos Reales...")
    
    # Asegurar tablas creadas
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Limpieza previa para evitar duplicados
        print("🧹 Limpiando datos previos de ministerios y cursos...")
        db.execute(models.member_ministries.delete())
        db.query(models.Ministry).delete()
        db.query(models.Enrollment).delete()
        db.query(models.Lesson).delete()
        db.query(models.CoursePrerequisite).delete()
        db.query(models.Course).delete()
        db.commit()

        # Obtener miembros existentes
        miembros = db.query(models.Member).all()
        usuarios = db.query(models.User).filter(models.User.role == "estudiante").all()
        
        if not miembros:
            print("❌ No hay miembros en la base de datos. Ejecuta seed_mass_data_v2.py primero.")
            return

        # 1. CREAR MINISTERIOS
        print("🏛️ Creando Ministerios...")
        nombres_ministerios = [
            ("Alabanza y Adoración", "Encargados de la música y liturgia."),
            ("Ministerio de Jóvenes", "Formación y eventos para la nueva generación."),
            ("Ministerio Infantil (Kids)", "Educación bíblica para niños."),
            ("Ujieres y Protocolo", "Servicio de bienvenida y orden."),
            ("Intercesión", "Equipo dedicado a la oración constante."),
            ("Medios y Tecnología", "Sonido, video y redes sociales."),
            ("Misiones y Evangelismo", "Impacto social y alcance exterior.")
        ]
        
        ministerios_db = []
        for nombre, desc in nombres_ministerios:
            # Asignar un líder aleatorio que sea "Líder" o "Pastor"
            lider = random.choice([m for m in miembros if m.church_role in ["Líder", "Pastor de Zona", "Servidor"]])
            minis = models.Ministry(name=nombre, description=desc, leader_id=lider.id)
            db.add(minis)
            ministerios_db.append(minis)
        db.commit()

        # Asignar miembros aleatorios a ministerios (aprox 15 personas por ministerio)
        print("🔗 Asignando personas a los ministerios...")
        for m_db in ministerios_db:
            equipo = random.sample(miembros, random.randint(10, 25))
            m_db.members.extend(equipo)
        db.commit()

        # 2. CREAR CURSOS REALES
        print("📚 Creando Cursos Académicos...")
        cursos_data = [
            ("LIDER-100", "Escuela de Líderes Nivel 1", "Formación básica para el servicio ministerial."),
            ("BIBLIA-200", "Panorama del Antiguo Testamento", "Estudio profundo de los libros históricos y proféticos."),
            ("VIDA-050", "Vida Nueva en Cristo", "Curso de discipulado para recién convertidos."),
            ("TEOL-300", "Doctrina de la Salvación", "Estudio teológico sistemático sobre la Soteriología.")
        ]
        
        cursos_db = []
        for code, title, desc in cursos_data:
            c = models.Course(code=code, title=title, description=desc, modality="formal", is_published=True)
            db.add(c)
            cursos_db.append(c)
        db.commit()
        for c in cursos_db: db.refresh(c)

        # 3. CREAR LECCIONES PARA LOS CURSOS
        print("📖 Añadiendo lecciones...")
        for curso in cursos_db:
            for i in range(1, 6):
                lesson = models.Lesson(
                    course_id=curso.id,
                    title=f"Lección {i}: {curso.title} - Parte {i}",
                    content=f"Contenido educativo detallado para la lección {i} del curso {curso.title}.",
                    order_index=i,
                    duration_minutes=45
                )
                db.add(lesson)
        db.commit()

        # 4. INSCRIBIR ESTUDIANTES Y GENERAR PROGRESO
        print(f"🎓 Inscribiendo estudiantes con progreso real (Población: {len(usuarios)})...")
        sample_size = min(len(usuarios), 150)
        estudiantes_seleccionados = random.sample(usuarios, sample_size)
        
        for user in estudiantes_seleccionados:
            # Inscribir en 1 o 2 cursos aleatorios
            cursos_inscritos = random.sample(cursos_db, random.randint(1, 2))
            for curso in cursos_inscritos:
                enrollment = models.Enrollment(
                    user_id=user.id,
                    course_id=curso.id,
                    status=random.choice(["active", "completed"]),
                    progress_percent=random.randint(10, 100)
                )
                if enrollment.progress_percent == 100:
                    enrollment.status = "completed"
                    enrollment.approved = True
                
                db.add(enrollment)
        db.commit()

        print("\n✅ ¡FINALIZADO!")
        print(f"📊 Resumen Académico/Ministerial:")
        print(f"   - Ministerios Activos: {len(nombres_ministerios)}")
        print(f"   - Cursos Disponibles: {len(cursos_data)}")
        print(f"   - Lecciones Creadas: {db.query(models.Lesson).count()}")
        print(f"   - Inscripciones con Progreso: {db.query(models.Enrollment).count()}")
        print("Los ministerios y la academia ahora tienen vida real.")

    except Exception as e:
        print(f"❌ Error en semilla avanzada: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_ministries_and_courses()
