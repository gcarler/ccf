import os
import random
import sys
import uuid
from datetime import datetime, timedelta

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.management.schema import upgrade_with_optional_bootstrap


def seed_mass_data():
    print("🚀 Iniciando Operación 'Crecimiento Exponencial' (600+ registros)...")

    upgrade_with_optional_bootstrap()
    db = SessionLocal()

    # Listas para generación aleatoria
    apellidos = [
        "Rodríguez",
        "García",
        "Martínez",
        "López",
        "González",
        "Pérez",
        "Sánchez",
        "Romero",
        "Sosa",
        "Torres",
        "Ramírez",
        "Ruiz",
        "Díaz",
        "Vargas",
        "Morales",
        "Castillo",
        "Jiménez",
        "Reyes",
        "Gutiérrez",
        "Castro",
    ]
    nombres_m = [
        "Juan",
        "Carlos",
        "Ricardo",
        "Felipe",
        "Mateo",
        "Andrés",
        "Marcos",
        "David",
        "Jorge",
        "Pedro",
        "Santiago",
        "Samuel",
        "Daniel",
        "Gabriel",
        "Mateo",
        "Tomás",
        "Lucas",
        "Simón",
        "Matías",
        "Javier",
    ]
    nombres_f = [
        "Elena",
        "María",
        "Sofía",
        "Lucía",
        "Isabel",
        "Camila",
        "Valeria",
        "Mariana",
        "Paola",
        "Claudia",
        "Beatriz",
        "Raquel",
        "Marta",
        "Silvia",
        "Adriana",
        "Gloria",
        "Victoria",
        "Natalia",
        "Diana",
        "Laura",
    ]
    zonas = ["Norte", "Sur", "Este", "Oeste", "Centro", "Suburban", "Altos", "Valle"]
    roles = ["Miembro", "Líder", "Pastor de Zona", "Servidor", "Ujier", "Músico"]

    try:
        print("🧹 Limpiando base de datos para inyección masiva...")
        db.query(models.AssessmentOption).delete()
        db.query(models.AssessmentQuestion).delete()
        db.query(models.AssessmentAttempt).delete()
        db.query(models.Assessment).delete()
        db.query(models.LessonProgress).delete()
        db.query(models.Lesson).delete()
        db.query(models.Enrollment).delete()
        db.query(models.CoursePrerequisite).delete()
        db.query(models.Course).delete()
        db.query(models.EventAttendance).delete()
        db.query(models.CrmEvent).delete()
        db.query(models.CounselingTicket).delete()
        db.query(models.PrayerRequest).delete()
        db.query(models.CommunicationLog).delete()
        db.query(models.ConsolidationPipeline).delete()
        db.query(models.Member).delete()
        db.query(models.GloryHouse).delete()
        db.query(models.Family).delete()
        db.query(models.User).delete()
        db.commit()

        # 1. Crear Administrador Principal
        pwd = get_password_hash("admin123")
        admin = models.User(
            username="admin_ccf", email="admin@ccf.la", password_hash=pwd, role="admin"
        )
        db.add(admin)
        db.commit()

        # 2. Generar 200 Familias
        print("🏠 Generando 200 familias...")
        familias = []
        for i in range(200):
            apellido = random.choice(apellidos)
            if random.random() > 0.5:
                apellido += " " + random.choice(apellidos)
            fam = models.Family(name=f"Familia {apellido}")
            db.add(fam)
            familias.append(fam)
        db.commit()
        for f in familias:
            db.refresh(f)

        # 3. Generar 600 Personas
        print("👥 Generando 600 miembros...")
        miembros = []
        usuarios_creados = 0

        for i in range(600):
            es_masculino = random.random() > 0.5
            nombre = random.choice(nombres_m if es_masculino else nombres_f)
            apellido = random.choice(apellidos)
            fam = random.choice(familias)
            rol = random.choices(roles, weights=[70, 15, 5, 5, 2, 3])[0]

            email = f"{nombre.lower()}.{apellido.lower()}{i}@ccf.la"

            user_id = None
            # Crear cuenta de usuario para los primeros 100
            if usuarios_creados < 100:
                user_role = "estudiante"
                if rol == "Pastor de Zona":
                    user_role = "docente"
                if rol == "Líder":
                    user_role = "coordinador"

                u = models.User(
                    username=f"user_{i}",
                    email=email,
                    password_hash=pwd,
                    role=user_role,
                    xp=random.randint(0, 1000),
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                user_id = u.id
                usuarios_creados += 1

            m = models.Member(
                first_name=nombre,
                last_name=apellido,
                email=email,
                phone=f"555-{random.randint(1000, 9999)}",
                family_id=fam.id,
                church_role=rol,
                user_id=user_id,
            )
            db.add(m)
            miembros.append(m)

            if i % 100 == 0:
                print(f"   ... {i} personas creadas")

        db.commit()

        # 4. Generar 10 Casas de Gloria
        print("🏘️ Creando 10 Casas de Gloria...")
        nombres_casas = [
            "Bethel",
            "Sion",
            "Ebenezer",
            "Jehová Jireh",
            "Monte de los Olivos",
            "Getsemaní",
            "Peniel",
            "Salem",
            "Mizpa",
            "Beraca",
        ]
        for i in range(10):
            pastor = random.choice(
                [m for m in miembros if m.church_role in ["Líder", "Pastor de Zona"]]
            )
            gh = models.GloryHouse(
                name=f"Casa {nombres_casas[i]} - {random.choice(zonas)}",
                zone=random.choice(zonas),
                leader_name=f"{pastor.first_name} {pastor.last_name}",
                members_count=random.randint(5, 25),
                schedule="Viernes 7:30 PM",
                status="Activo",
            )
            db.add(gh)
        db.commit()

        # 5. CRM Data: Oración y Consejería
        print("🙏 Generando peticiones de oración y tickets...")
        for i in range(50):
            m = random.choice(miembros)
            pr = models.PrayerRequest(
                requester_name=f"{m.first_name} {m.last_name}",
                request_text=f"Petición masiva #{i}: Por el ministerio y la familia.",
                is_public=random.random() > 0.3,
                status=random.choice(["pending", "praying", "answered"]),
            )
            db.add(pr)

        for i in range(30):
            m = random.choice(miembros)
            ct = models.CounselingTicket(
                member_id=m.id,
                subject=f"Consulta Pastoral #{i}",
                notes="Notas de seguimiento generadas automáticamente.",
                status=random.choice(["open", "in_progress", "resolved"]),
            )
            db.add(ct)
        db.commit()

        # 6. Eventos
        print("🗓️ Creando historial de eventos...")
        for i in range(5):
            e = models.CrmEvent(
                title=f"Evento Ministerial #{i}",
                description="Descripción del evento para pruebas de carga.",
                event_date=datetime.now() + timedelta(days=i * 7),
                location="Auditorio Central",
            )
            db.add(e)
        db.commit()

        print("\n✅ ¡MISIÓN CUMPLIDA!")
        print(f"📊 Estadísticas Finales:")
        print(f"   - Usuarios: {db.query(models.User).count()}")
        print(f"   - Familias: {db.query(models.Family).count()}")
        print(f"   - Miembros: {db.query(models.Member).count()}")
        print(f"   - Casas de Gloria: {db.query(models.GloryHouse).count()}")
        print(f"   - Peticiones de Oración: {db.query(models.PrayerRequest).count()}")
        print(f"La base de datos es ahora un ecosistema vivo y denso.")

    except Exception as e:
        print(f"❌ Error crítico en seeding: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_mass_data()
