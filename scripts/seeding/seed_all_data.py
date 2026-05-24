import os
import random
import sys
from datetime import date, datetime, timedelta

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash

# Spanish names for seed generation
FIRST_NAMES_MALE = [
    "Juan",
    "Carlos",
    "José",
    "Luis",
    "Fernando",
    "Francisco",
    "Pedro",
    "Jorge",
    "Miguel",
    "Javier",
    "Alejandro",
    "Manuel",
    "Roberto",
    "Raúl",
    "Diego",
    "David",
    "Daniel",
    "Alberto",
    "Andrés",
    "Mario",
    "Santiago",
    "Gabriel",
    "Hugo",
    "Sebastián",
    "Mateo",
    "Nicolás",
    "Samuel",
    "Ángel",
    "Tomás",
    "Ricardo",
    "Pablo",
    "Eduardo",
    "Héctor",
    "Sergio",
    "Rafael",
    "Antonio",
    "Marcos",
    "Adrian",
    "Iván",
    "Gustavo",
    "César",
    "Rubén",
    "Víctor",
    "Leonardo",
    "Martín",
    "Gonzalo",
    "Joaquín",
    "Mauricio",
    "Rodrigo",
    "Esteban",
]

FIRST_NAMES_FEMALE = [
    "María",
    "Ana",
    "Luisa",
    "Carmen",
    "Isabel",
    "Teresa",
    "Francisca",
    "Elena",
    "Marta",
    "Laura",
    "Cristina",
    "Silvia",
    "Patricia",
    "Andrea",
    "Mónica",
    "Claudia",
    "Sandra",
    "Alicia",
    "Beatriz",
    "Gloria",
    "Sofía",
    "Camila",
    "Valentina",
    "Isabella",
    "Gabriela",
    "Daniela",
    "Mariana",
    "Paula",
    "Natalia",
    "Clara",
    "Valeria",
    "Jimena",
    "Lucía",
    "Sara",
    "Liliana",
    "Diana",
    "Adriana",
    "Sonia",
    "Olga",
    "Cecilia",
    "Rosa",
    "Juana",
    "Luz",
    "Ángela",
    "Julia",
    "Victoria",
    "Carolina",
    "Estela",
    "Paola",
    "Diana",
]

LAST_NAMES = [
    "González",
    "Rodríguez",
    "Gómez",
    "Fernández",
    "López",
    "Díaz",
    "Martínez",
    "Pérez",
    "García",
    "Sánchez",
    "Romero",
    "Sosa",
    "Álvarez",
    "Torres",
    "Ruiz",
    "Ramírez",
    "Flores",
    "Acosta",
    "Benítez",
    "Medina",
    "Herrera",
    "Aguirre",
    "Gutiérrez",
    "Castro",
    "Molina",
    "Silva",
    "Ortiz",
    "Delgado",
    "Mendoza",
    "Salazar",
    "Rojas",
    "Guerrero",
    "Paredes",
    "Ramos",
    "Suárez",
    "Morales",
    "Ortega",
    "Castillo",
    "Vargas",
    "Guzmán",
    "Méndez",
    "Núñez",
    "Cabrera",
    "Domínguez",
    "Herrera",
    "Blanco",
    "Jiménez",
    "Marín",
    "Cruz",
    "Ortiz",
]

ZONES = ["Zona Norte", "Zona Sur", "Zona Centro", "Zona Este", "Zona Oeste"]
DAYS_OF_WEEK = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]
TIME_SLOTS = [
    ("19:00", "20:30"),
    ("19:30", "21:00"),
    ("20:00", "21:30"),
    ("18:30", "20:00"),
]

TALENTS = [
    "Música (Guitarra)",
    "Música (Teclado)",
    "Canto",
    "Tecnología y Redes",
    "Cocina y Repostería",
    "Enseñanza",
    "Administración",
    "Diseño Gráfico",
    "Logística y Protocolo",
    "Fotografía",
    "Manualidades",
    "Primeros Auxilios",
    "Sonido y Multimedia",
]

SPIRITUAL_GIFTS = [
    "Liderazgo",
    "Misericordia",
    "Sabiduría",
    "Profecía",
    "Enseñanza",
    "Fe",
    "Servicio",
    "Evangelismo",
    "Administración",
    "Exhortación",
    "Dar con liberalidad",
    "Pastoreo",
]

COUNSELING_SUBJECTS = [
    "Crisis de pareja y comunicación",
    "Orientación vocacional para jóvenes",
    "Fortalecimiento espiritual y dudas",
    "Proceso de duelo familiar",
    "Superación de adicciones y malos hábitos",
    "Sanidad interior y perdón",
    "Manejo de ansiedad y estrés",
    "Finanzas familiares y principios bíblicos",
    "Restauración de relaciones padres-hijos",
]

COUNSELING_NOTES = [
    "Se brindaron pautas de comunicación asertiva y compromiso mutuo.",
    "El miembro se muestra receptivo y comprometido a continuar el proceso académico.",
    "Se oró por fortaleza espiritual y se sugirió lectura de pasajes específicos.",
    "Se acompaña en el proceso de aceptación y consuelo espiritual.",
    "Presenta avances significativos y mantiene una red de apoyo activa.",
    "Se trabajó en el perdón y la liberación de resentimientos del pasado.",
    "Se recomendaron hábitos saludables y descanso guiado en fe.",
    "Se elaboró un plan de presupuesto y ahorro basado en mayordomía.",
    "Se establecieron acuerdos de respeto y tiempo de calidad familiar.",
]


def seed_database():
    db = SessionLocal()
    try:
        print("Starting Database Seed...")

        # 1. Clean existing records in dependency order
        print("Cleaning old data...")
        db.query(models.GloryHouseAttendance).delete()
        db.query(models.GloryHouseSession).delete()
        db.query(models.FaroSeason).delete()
        db.query(models.GloryHouseMember).delete()
        db.query(models.GloryHouse).delete()
        db.query(models.CounselingTicket).delete()
        db.query(models.Enrollment).delete()
        db.query(models.Course).delete()
        db.query(models.MemberPosition).delete()
        db.query(models.Position).delete()
        db.query(models.Member).delete()
        db.query(models.Family).delete()

        # Keep the admin user, delete other users (except admin)
        db.query(models.User).filter(models.User.username != "admin").delete()

        db.query(models.Level).delete()
        db.query(models.Role).delete()
        db.commit()

        # 2. Seed Levels
        print("Creating levels...")
        levels = []
        for i in range(1, 6):
            lvl = models.Level(
                title=f"Nivel {i}", min_xp=(i - 1) * 1000, icon_key=f"level_{i}"
            )
            db.add(lvl)
            levels.append(lvl)
        db.commit()

        # 3. Seed Roles
        print("Creating roles...")
        roles_list = ["admin", "pastor", "coordinador", "lider", "estudiante"]
        roles_dict = {}
        for role_name in roles_list:
            role_obj = models.Role(name=role_name, permissions={"access": [role_name]})
            db.add(role_obj)
            roles_dict[role_name] = role_obj
        db.commit()

        # Update admin user to have Level 1 and role admin
        admin_user = (
            db.query(models.User).filter(models.User.username == "admin").first()
        )
        if admin_user:
            admin_user.current_level_id = levels[0].id
            admin_user.role_id = roles_dict["admin"].role_id
            db.commit()

        # Create a Pastor User
        pastor_user = models.User(
            username="pastor.juan",
            email="pastor.juan@ccf.com",
            password_hash=get_password_hash("password123"),
            role="pastor",
            role_id=roles_dict["pastor"].role_id,
            current_level_id=levels[0].id,
            is_active=True,
            is_email_verified=True,
        )
        db.add(pastor_user)
        db.commit()

        # 4. Seed Families
        print("Creating families...")
        families = []
        for i in range(1, 131):
            ln1 = random.choice(LAST_NAMES)
            ln2 = random.choice(LAST_NAMES)
            fam_name = f"Familia {ln1} {ln2}"
            zone = random.choice(ZONES)
            address = f"Calle {random.randint(1, 100)} # {random.randint(1, 99)} - {random.randint(1, 99)}, {zone}"
            family = models.Family(name=fam_name, address=address)
            db.add(family)
            families.append(family)
        db.commit()

        # 5. Seed Members
        print("Creating 500 members...")
        members = []
        # Spiritual Status Distribution
        # 10% Servidor, 25% Discípulo, 40% Creyente, 25% Nuevo
        status_weights = (
            ["Servidor"] * 10 + ["Discípulo"] * 25 + ["Creyente"] * 40 + ["Nuevo"] * 25
        )

        # Roles list to assign based on status
        servidor_roles = ["Servidor", "Líder", "Colíder", "Anfitrión"]

        for idx in range(1, 501):
            family = random.choice(families)
            # Extrapolate last name from family name
            fam_last_names = family.name.replace("Familia ", "")

            gender = random.choice(["Male", "Female"])
            if gender == "Male":
                first_name = random.choice(FIRST_NAMES_MALE)
            else:
                first_name = random.choice(FIRST_NAMES_FEMALE)

            last_name = f"{fam_last_names.split()[0]} {random.choice(LAST_NAMES)}"

            email_local = f"{first_name.lower()}.{last_name.split()[0].lower()}{idx}"
            # Clean email local part from accents
            email_local = (
                email_local.replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
                .replace("ñ", "n")
            )
            email = f"{email_local}@example.com"
            phone = f"3{random.randint(0,9)}{random.randint(0,9)} {random.randint(100, 999)} {random.randint(1000, 9999)}"

            spiritual_status = random.choice(status_weights)

            if spiritual_status == "Servidor":
                church_role = random.choice(servidor_roles)
                is_baptized = True
            elif spiritual_status == "Discípulo":
                church_role = "Miembro"
                is_baptized = True
            elif spiritual_status == "Creyente":
                church_role = "Miembro"
                is_baptized = random.choice([True, False])
            else:
                church_role = "Miembro"
                is_baptized = False

            talents_list = random.sample(TALENTS, random.randint(1, 3))
            gifts_list = random.sample(SPIRITUAL_GIFTS, random.randint(1, 3))

            # Demographic representation in notes
            age = random.randint(8, 80)
            if age < 18:
                pastoral_notes = f"Hijo/a menor de edad. Edad: {age} años."
            elif age < 30:
                pastoral_notes = (
                    f"Joven soltero/a. Edad: {age} años. Interesado en misiones."
                )
            elif age < 60:
                pastoral_notes = (
                    f"Adulto. Edad: {age} años. Integrante activo de su hogar."
                )
            else:
                pastoral_notes = (
                    f"Adulto mayor. Edad: {age} años. Aporta sabiduría al grupo."
                )

            member = models.Member(
                family_id=family.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                church_role=church_role,
                is_baptized=is_baptized,
                spiritual_status=spiritual_status,
                talents=", ".join(talents_list),
                spiritual_gifts=", ".join(gifts_list),
                pastoral_notes=pastoral_notes,
            )
            db.add(member)
            members.append(member)

        db.commit()

        # Link pastor_user to a member profile
        pastor_member = members[0]
        pastor_member.church_role = "Pastor"
        pastor_member.spiritual_status = "Servidor"
        pastor_member.user_id = pastor_user.id
        db.commit()

        # 6. Create User Accounts for ~300 members (Servidores, Discípulos and some Creyentes)
        print("Creating student users...")
        students_count = 0
        for m in members:
            # Skip if already has user or is pastor
            if m.user_id is not None:
                continue

            if m.spiritual_status in ["Servidor", "Discípulo"] or (
                m.spiritual_status == "Creyente" and random.random() < 0.5
            ):
                username_base = (
                    f"{m.first_name.lower()}.{m.last_name.split()[0].lower()}"
                )
                username_base = (
                    username_base.replace("á", "a")
                    .replace("é", "e")
                    .replace("í", "i")
                    .replace("ó", "o")
                    .replace("ú", "u")
                    .replace("ñ", "n")
                )
                username = f"{username_base}_{m.id}"

                user_obj = models.User(
                    username=username,
                    email=m.email,
                    password_hash=get_password_hash("password123"),
                    role="estudiante",
                    role_id=roles_dict["estudiante"].role_id,
                    current_level_id=levels[0].id,
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(user_obj)
                db.commit()

                m.user_id = user_obj.id
                students_count += 1
        db.commit()
        print(f"Created {students_count} student user accounts linked to members.")

        # 7. Seed Glory Houses
        print("Creating Glory Houses...")
        glory_houses = []

        # Pick potential leaders (Servidores with Líder role, or just Servidores)
        leaders_pool = [m for m in members if m.spiritual_status == "Servidor"]
        if not leaders_pool:
            leaders_pool = members[:50]

        random.shuffle(leaders_pool)

        house_names = [
            "Faro Bethel",
            "Faro Peniel",
            "Faro Ebenezer",
            "Faro Getsemaní",
            "Faro Sinaí",
            "Faro Hermón",
            "Faro Jordán",
            "Faro Sión",
            "Faro Siloé",
            "Faro Betania",
            "Faro Galilea",
            "Faro Capernaum",
            "Faro Emaús",
            "Faro Salem",
            "Faro Filadelfia",
            "Faro Antioquía",
            "Faro Éfeso",
            "Faro Esmirna",
            "Faro Pérgamo",
            "Faro Tiatira",
            "Faro Sardis",
            "Faro Laodicea",
            "Faro de Luz",
            "Faro de Esperanza",
            "Faro de Fe",
        ]

        for i, name in enumerate(house_names):
            code = (
                f"FARO-{str(i+1).padStart(3, '0')}"
                if hasattr(str, "padStart")
                else f"FARO-{str(i+1).zfill(3)}"
            )
            zone = random.choice(ZONES)

            # Select Leader, Assistant, Host
            leader = leaders_pool[i % len(leaders_pool)]
            assistant = leaders_pool[(i + 1) % len(leaders_pool)]
            host = leaders_pool[(i + 2) % len(leaders_pool)]

            # Ensure different members
            if leader.id == assistant.id:
                assistant = members[
                    (m.id for m in members if m.id != leader.id).__next__()
                ]
            if host.id == leader.id or host.id == assistant.id:
                host = members[
                    (
                        m.id for m in members if m.id not in [leader.id, assistant.id]
                    ).__next__()
                ]

            leader.church_role = "Líder"
            assistant.church_role = "Colíder"
            host.church_role = "Anfitrión"

            time_slot = random.choice(TIME_SLOTS)
            status = "Activo"
            if i == 22:
                status = "Inactivo"
            elif i == 24:
                status = "Suspendido"

            capacity = random.choice([12, 15, 20, 25])

            # Coordinates around Bogota/CCF area for realism
            lat = 4.6097 + random.uniform(-0.05, 0.05)
            lng = -74.0817 + random.uniform(-0.05, 0.05)

            house = models.GloryHouse(
                code=code,
                name=name,
                zone=zone,
                address=f"Carrera {random.randint(1, 50)} # {random.randint(1, 99)} - {random.randint(1, 99)}, {zone}",
                latitude=lat,
                longitude=lng,
                leader_name=f"{leader.first_name} {leader.last_name}",
                leader_id=leader.id,
                assistant_id=assistant.id,
                host_id=host.id,
                capacity=capacity,
                day_of_week=random.choice(DAYS_OF_WEEK),
                start_time=time_slot[0],
                end_time=time_slot[1],
                status=status,
                members_count=0,
            )
            db.add(house)
            glory_houses.append(house)
        db.commit()

        # 8. Assign members to Glory Houses
        print("Assigning members to houses...")
        # Get all members who are not leaders/assistants/hosts of any house
        core_roles_ids = set()
        for h in glory_houses:
            if h.leader_id:
                core_roles_ids.add(h.leader_id)
            if h.assistant_id:
                core_roles_ids.add(h.assistant_id)
            if h.host_id:
                core_roles_ids.add(h.host_id)

        assignable_members = [m for m in members if m.id not in core_roles_ids]
        random.shuffle(assignable_members)

        member_idx = 0
        for h in glory_houses:
            # Assign between 8 and 18 members per house
            num_to_assign = min(
                random.randint(8, 18), len(assignable_members) - member_idx
            )
            if num_to_assign <= 0:
                break

            for _ in range(num_to_assign):
                m = assignable_members[member_idx]
                gh_member = models.GloryHouseMember(
                    glory_house_id=h.id, member_id=m.id, role="asistente"
                )
                db.add(gh_member)
                member_idx += 1

            h.members_count = num_to_assign

        db.commit()
        print("Glory Houses assignment completed.")

        # 9. Seed Courses
        print("Creating courses...")
        courses_data = [
            (
                "ACAD-001",
                "Fundamentos de la Fe",
                "Estudio de las verdades fundamentales del evangelio y la doctrina cristiana básica.",
                "presencial",
                True,
                20,
            ),
            (
                "ACAD-002",
                "Discipulado I: Vida Cristiana",
                "Principios prácticos para el crecimiento diario, oración, lectura de la palabra y testimonio.",
                "virtual",
                True,
                30,
            ),
            (
                "ACAD-003",
                "Discipulado II: Carácter Cristiano",
                "Desarrollo del carácter a través de la obediencia, mayordomía y vida comunitaria.",
                "virtual",
                True,
                30,
            ),
            (
                "ACAD-004",
                "Liderazgo Ministerial",
                "Capacitación avanzada para servir en los diferentes ministerios de la iglesia y guiar a otros.",
                "presencial",
                True,
                40,
            ),
            (
                "ACAD-005",
                "Consejería Familiar",
                "Herramientas bíblicas y psicológicas para orientar a familias en crisis y restaurar relaciones.",
                "presencial",
                True,
                35,
            ),
            (
                "ACAD-006",
                "Teología Práctica",
                "Profundización doctrinal aplicada a los desafíos contemporáneos de la iglesia hoy.",
                "virtual",
                True,
                45,
            ),
        ]

        courses = []
        for code, title, desc, modality, published, hours in courses_data:
            course = models.Course(
                code=code,
                title=title,
                description=desc,
                modality=modality,
                is_published=published,
                is_self_paced=True,
                duration_hours=hours,
                cohort_name="Cohorte 2026",
                instructor_name="Pastor Principal / Coordinador Académico",
            )
            db.add(course)
            courses.append(course)
        db.commit()

        # 10. Seed Enrollments
        print("Creating enrollments...")
        users_pool = (
            db.query(models.User).filter(models.User.role == "estudiante").all()
        )

        enrollments_count = 0
        for u in users_pool:
            # Enroll user in 1 to 3 random courses
            num_courses = random.randint(1, 3)
            selected_courses = random.sample(courses, num_courses)

            for c in selected_courses:
                status = random.choice(["active", "completed", "dropped"])
                if status == "completed":
                    progress = 100
                    approved = True
                elif status == "active":
                    progress = random.randint(10, 95)
                    approved = False
                else:
                    progress = random.randint(0, 45)
                    approved = False

                enrollment = models.Enrollment(
                    user_id=u.id,
                    course_id=c.id,
                    status=status,
                    progress_percent=progress,
                    approved=approved,
                    certificate_issued=approved,
                    certificate_code=f"CERT-{c.code}-{u.id}" if approved else None,
                )
                db.add(enrollment)
                enrollments_count += 1
        db.commit()
        print(f"Created {enrollments_count} course enrollments.")

        # 11. Seed Counseling Tickets
        print("Creating counseling tickets...")
        # Select members to receive counseling
        counseling_pool = random.sample(members, 70)
        for idx, m in enumerate(counseling_pool):
            subject = random.choice(COUNSELING_SUBJECTS)
            notes_text = f"Detalle de la solicitud: {subject}. " + random.choice(
                COUNSELING_NOTES
            )
            status = random.choice(["open", "in_progress", "resolved"])
            priority = random.choice(["URGENT", "HIGH", "NORMAL"])

            # Sentiment score matching the status/subject
            sentiment = random.uniform(-0.8, 0.4)
            if sentiment < -0.2:
                label = "NEGATIVE"
            elif sentiment < 0.2:
                label = "NEUTRAL"
            else:
                label = "POSITIVE"

            ticket = models.CounselingTicket(
                member_id=m.id,
                pastor_id=pastor_user.id,
                subject=subject,
                notes=notes_text,
                status=status,
                priority_level=priority,
                sentiment_score=round(sentiment, 2),
                sentiment_label=label,
                created_at=datetime.now() - timedelta(days=random.randint(1, 60)),
            )
            db.add(ticket)
        db.commit()
        print("Counseling tickets created.")

        # 12. Seed Faro Seasons, Sessions & Attendance
        print("Creating Faro seasons, sessions, and attendance...")
        season = models.FaroSeason(
            name="Campaña Faro en Casa 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            periodicity="SEMANAL",
            status="Activa",
        )
        db.add(season)
        db.commit()

        # Generate sessions for the past 4 weeks
        today_date = date.today()
        session_dates = [today_date - timedelta(weeks=w) for w in range(1, 5)]

        topics = [
            "El poder de la oración colectiva",
            "La importancia del perdón en la familia",
            "Mayordomía cristiana y generosidad",
            "Caminando por fe y no por vista",
        ]

        attendance_records_count = 0
        for h in glory_houses:
            # Skip inactive/suspended houses for sessions
            if h.status != "Activo":
                continue

            # Get members assigned to this house
            gh_members = (
                db.query(models.GloryHouseMember)
                .filter(models.GloryHouseMember.glory_house_id == h.id)
                .all()
            )
            if not gh_members:
                continue

            for s_idx, s_date in enumerate(session_dates):
                # Create session
                session = models.GloryHouseSession(
                    glory_house_id=h.id,
                    season_id=season.id,
                    session_date=s_date,
                    status="Realizada",
                    topic=topics[s_idx % len(topics)],
                    offering_amount=random.randint(5, 50) * 1000,  # 5,000 to 50,000 COP
                )
                db.add(session)
                db.commit()

                # Create attendance for each member
                for ghm in gh_members:
                    attended = random.random() < 0.85  # 85% attendance rate
                    reason = None
                    detail = None
                    if not attended:
                        reason = random.choice(["Trabajo", "Salud", "Viaje", "Otros"])
                        detail = f"No pudo asistir por motivos de {reason.lower()}."

                    attendance = models.GloryHouseAttendance(
                        session_id=session.id,
                        member_id=ghm.member_id,
                        attended=attended,
                        absence_reason=reason,
                        absence_reason_detail=detail,
                        scanned_at=datetime.combine(s_date, datetime.min.time())
                        + timedelta(hours=19, minutes=random.randint(0, 20)),
                    )
                    db.add(attendance)
                    attendance_records_count += 1

        db.commit()
        print(
            f"Created weekly sessions and {attendance_records_count} attendance records."
        )
        print("Database Seeding Completed Successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
