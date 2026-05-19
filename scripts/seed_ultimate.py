import os
import random
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.management.schema import reset_database_for_local_bootstrap


def seed_ultimate():
    print("Iniciando inyeccion maestra de diversidad...")

    reset_database_for_local_bootstrap()
    db = SessionLocal()

    try:
        print("Creando roles base...")
        roles_db = [
            models.Role(name="admin", permissions={"all": True}),
            models.Role(name="docente", permissions={"academy": True}),
            models.Role(name="coordinador", permissions={"crm": True}),
            models.Role(name="estudiante", permissions={"academy": "read"}),
        ]
        db.add_all(roles_db)
        db.commit()

        pwd = get_password_hash("admin123")

        def create_ministerial_user(first, last, email, role_name, username):
            user = models.User(username=username, email=email, password_hash=pwd, role="admin", xp=10000)
            db.add(user)
            db.commit()
            db.refresh(user)
            member = models.Member(
                first_name=first,
                last_name=last,
                email=email,
                church_role=role_name,
                is_baptized=True,
                spiritual_status="Servidor",
                user_id=user.id,
            )
            db.add(member)
            db.commit()
            return member

        pastor_luis = create_ministerial_user(
            "LUIS RICARDO", "MEZA GUTIERREZ", "luis.meza@ccf.la", "Pastor Principal", "luis_meza"
        )
        pastora_histar = create_ministerial_user(
            "HISTAR", "ARIZA HERRERA", "histar.ariza@ccf.la", "Pastora Principal", "histar_ariza"
        )
        pastor_alex = create_ministerial_user(
            "ALEX", "CABARCAS", "alex.cabarcas@ccf.la", "Pastor", "alex_cabarcas"
        )
        pastora_elivia = create_ministerial_user(
            "ELIVIA", "ANGULO", "elivia.angulo@ccf.la", "Pastora", "elivia_angulo"
        )
        pastor_camilo = create_ministerial_user(
            "CAMILO", "PAJARO", "camilo.pajaro@ccf.la", "Pastor", "camilo_pajaro"
        )
        pastora_alba = create_ministerial_user(
            "ALBA", "ESTRADA", "alba.estrada@ccf.la", "Pastora", "alba_estrada"
        )
        pastor_nehemias = create_ministerial_user(
            "NEHEMIAS", "HERNANDEZ", "nehemias.hernandez@ccf.la", "Pastor", "nehemias_h"
        )
        pastor_fernando = create_ministerial_user(
            "FERNANDO", "HERNANDEZ", "fernando.hernandez@ccf.la", "Pastor", "fernando_h"
        )

        print("Generando familias y miembros...")
        apellidos = ["Rodriguez", "Garcia", "Martinez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Castro", "Mendoza", "Vargas"]
        nombres = ["Juan", "Elena", "Carlos", "Sofia", "Ricardo", "Maria", "Mateo", "Lucia", "Andres", "Valeria"]
        oficios = ["Profeta", "Maestro", "Evangelista", "Servidor", "Miembro", "Diacono"]
        pesos_oficios = [2, 5, 3, 20, 60, 10]
        estados_espirituales = ["Nuevo", "Creyente", "Discipulo", "Servidor"]

        miembros_lista = [
            pastor_luis,
            pastora_histar,
            pastor_alex,
            pastora_elivia,
            pastor_camilo,
            pastora_alba,
            pastor_nehemias,
            pastor_fernando,
        ]

        familias_lista = []
        for i in range(200):
            fam = models.Family(name=f"Familia {random.choice(apellidos)} {i}")
            db.add(fam)
            familias_lista.append(fam)
        db.commit()

        for i in range(600):
            user_id = None
            email = f"persona{i}@ccf.la"
            rol_iglesia = random.choices(oficios, weights=pesos_oficios)[0]
            baptized = random.random() > 0.3
            spiritual = random.choice(estados_espirituales)

            if i < 100:
                user = models.User(
                    username=f"user{i}",
                    email=email,
                    password_hash=pwd,
                    role="estudiante",
                    xp=random.randint(0, 500),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                user_id = user.id

            member = models.Member(
                first_name=random.choice(nombres),
                last_name=random.choice(apellidos),
                email=email,
                family_id=random.choice(familias_lista).id,
                church_role=rol_iglesia,
                is_baptized=baptized,
                spiritual_status=spiritual,
                user_id=user_id,
            )
            db.add(member)
            miembros_lista.append(member)
        db.commit()

        print("Creando cursos y distribuyendo estudiantes...")
        course_one = models.Course(code="FUND-1", title="Fundamentos de la Fe", modality="formal")
        course_two = models.Course(code="MAESTRIA-1", title="Formacion de Maestros", modality="formal")
        db.add_all([course_one, course_two])
        db.commit()
        db.refresh(course_one)
        db.refresh(course_two)

        lesson = models.Lesson(course_id=course_one.id, title="La Gracia", content="Contenido...", order_index=1)
        db.add(lesson)
        db.commit()

        usuarios_est = db.query(models.User).filter(models.User.role == "estudiante").all()
        for idx, user in enumerate(usuarios_est):
            if idx < 40:
                db.add(
                    models.Enrollment(
                        user_id=user.id,
                        course_id=course_one.id,
                        status="active",
                        progress_percent=random.randint(10, 90),
                    )
                )
            elif idx < 50:
                db.add(
                    models.Enrollment(
                        user_id=user.id,
                        course_id=course_two.id,
                        status="completed",
                        approved=True,
                        progress_percent=100,
                    )
                )
        db.commit()

        db.add(models.Ministry(name="Ensenanza", description="Cuerpo de Maestros", leader_id=miembros_lista[0].id))
        db.add(models.Ministry(name="Profetico", description="Cuerpo de Profetas", leader_id=miembros_lista[1].id))
        db.add(models.CrmEvent(title="Gran Bautismo", event_date=datetime.now() + timedelta(days=15), location="Sede Central"))
        db.commit()

        print("Operacion completada.")
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_ultimate()
