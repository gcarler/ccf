import sys
import os
from pathlib import Path
import random
from datetime import datetime, timedelta

# Add backend directory to python path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

from backend.core.database import SessionLocal
from backend.models import (
    User, Member, Family, Course, Enrollment, CounselingSession, GloryHouse, PastoralCallLog
)
from backend.core.security import get_password_hash

# Data for randomization
NOMBRES_HOMBRES = ["Carlos", "Andrés", "Miguel", "Juan", "David", "José", "Alejandro", "Daniel", "Fernando", "Jorge", "Luis", "Felipe", "Sebastián", "Diego", "Mateo", "Santiago", "Nicolás", "Samuel", "Martín", "Tomás", "Emiliano", "Matías", "Julián", "Gabriel", "Simón", "Lucas", "Joaquín", "Jerónimo", "Maximiliano", "Thiago", "Gael", "Emmanuel", "Isaac", "Benjamín", "Camilo", "Pablo", "Esteban", "Ricardo", "Mario", "Oscar", "Víctor", "Manuel", "Javier", "Héctor", "Raúl", "Roberto", "Mauricio"]
NOMBRES_MUJERES = ["María", "Laura", "Ana", "Carmen", "Marta", "Lucía", "Paula", "Sofía", "Valeria", "Isabella", "Camila", "Mariana", "Valentina", "Victoria", "Daniela", "Gabriela", "Martina", "Juliana", "Salomé", "Antonella", "Emilia", "Luciana", "Samantha", "Sara", "Mia", "Emma", "Elena", "Luna", "Zoe", "Olivia", "Abigail", "Isadora", "Catalina", "Julieta", "Renata", "Regina", "Andrea", "Carolina", "Diana", "Gloria", "Rosa", "Silvia", "Elena", "Mónica", "Teresa", "Verónica"]
APELLIDOS = ["García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez", "Ramírez", "Cruz", "Flores", "Gómez", "Morales", "Ortiz", "Gutiérrez", "Chávez", "Ruiz", "Álvarez", "Fernández", "Jiménez", "Díaz", "Mendoza", "Castillo", "Reyes", "Aguilar", "Torres", "Vargas", "Ríos", "Castro", "Romero", "Herrera", "Medina", "Aguilar", "Méndez", "Salazar", "Rojas", "Soto", "Guzmán", "Molina", "Delgado", "Vega", "Ramos", "Navarro", "Campos", "Figueroa", "Cortés", "Paredes", "Cabrera", "Rivas"]
TEMAS_CONSEJERIA = ["Matrimonio", "Finanzas", "Crianza de Hijos", "Ansiedad y Estrés", "Depresión", "Crecimiento Espiritual", "Luto", "Adicciones", "Conflicto Familiar", "Decisión Profesional"]

def random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    if days_between_dates <= 0:
        return start_date
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def seed_mass_data():
    db = SessionLocal()
    try:
        print("Starting mass data generation for 500+ members...")

        # Find existing Pastor
        pastor = db.query(User).filter(User.role == "pastor").first()
        if not pastor:
             print("No pastor found to assign counseling sessions.")

        # Find Course
        course = db.query(Course).filter(Course.code == "DISC-A-2026").first()
        
        # Get Glory Houses
        ghouses = db.query(GloryHouse).all()

        total_members_created = 0
        total_families_created = 0
        total_users_created = 0

        # Generate ~150 Families to get around 500 Members
        for i in range(150):
            apellido_fam = random.choice(APELLIDOS)
            fam = Family(name=f"Familia {apellido_fam}")
            db.add(fam)
            db.commit()
            db.refresh(fam)
            total_families_created += 1

            # Determine family structure: 1-2 parents, 0-3 kids
            num_parents = random.choice([1, 2])
            num_kids = random.choice([0, 1, 2, 3])

            fam_members = []
            
            # Parents
            for p in range(num_parents):
                rol = "Madre" if p == 1 or num_parents == 1 and random.random() > 0.5 else "Padre"
                nombres = NOMBRES_MUJERES if rol == "Madre" else NOMBRES_HOMBRES
                
                member = Member(
                    first_name=random.choice(nombres),
                    last_name=apellido_fam,
                    phone=f"3{random.randint(100000000, 999999999)}",
                    role_in_family=rol,
                    church_role=random.choice(["Miembro", "Servidor", "Líder"]),
                    family_id=fam.id,
                    birthday=random_date(datetime(1960, 1, 1), datetime(1995, 12, 31))
                )
                db.add(member)
                fam_members.append(member)
                total_members_created += 1

            # Kids
            for k in range(num_kids):
                es_nina = random.random() > 0.5
                nombres = NOMBRES_MUJERES if es_nina else NOMBRES_HOMBRES
                
                member = Member(
                    first_name=random.choice(nombres),
                    last_name=apellido_fam,
                    phone=f"3{random.randint(100000000, 999999999)}" if random.random() > 0.5 else None,  # Kids might not have phones
                    role_in_family="Hijo" if not es_nina else "Hija",
                    church_role="Joven" if random.random() > 0.5 else "Niño",
                    family_id=fam.id,
                    birthday=random_date(datetime(1996, 1, 1), datetime(2020, 12, 31))
                )
                db.add(member)
                fam_members.append(member)
                total_members_created += 1

            db.commit()

            # For each member, decide if they get a User account, Enrollment, Counseling
            for m in fam_members:
                # Adults and Teens get Users (50% chance)
                if m.role_in_family in ["Padre", "Madre"] or (m.role_in_family in ["Hijo", "Hija"] and m.church_role == "Joven"):
                    if random.random() > 0.3: # 70% chance of user account
                        email = f"{m.first_name.lower()}.{m.last_name.lower()}{random.randint(1,999)}@ccfmock.com"
                        m.email = email
                        
                        user = User(
                            username=email,
                            email=email,
                            password_hash=get_password_hash("password123"),
                            role="estudiante" if m.church_role in ["Joven", "Miembro"] else "lider",
                            is_active=True,
                            is_email_verified=True
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
                        
                        m.user_id = user.id
                        total_users_created += 1

                        # Create Enrollment if Course exists (50% chance)
                        if course and random.random() > 0.5:
                            enroll = Enrollment(
                                user_id=user.id,
                                course_id=course.id,
                                status=random.choice(["active", "completed"]),
                                progress_percent=random.randint(0, 100)
                            )
                            db.add(enroll)

                        # Create Counseling Session (15% chance for adults/youth)
                        if pastor and random.random() > 0.85:
                            c_date = random_date(datetime(2025, 1, 1), datetime(2026, 6, 1))
                            session = CounselingSession(
                                pastor_id=pastor.id,
                                member_id=m.id,
                                scheduled_at=c_date,
                                duration_minutes=60,
                                status=random.choice(["Pendiente", "Completada", "Cancelada"]),
                                topic=random.choice(TEMAS_CONSEJERIA),
                                summary="Sesión mock generada para seguimiento." if random.random() > 0.5 else None
                            )
                            db.add(session)
            
            # Increment Glory House count (distribute families randomly)
            if ghouses and random.random() > 0.4:  # 60% chance family belongs to a glory house
                gh = random.choice(ghouses)
                gh.members_count += len(fam_members)

            db.commit()

        print("--------------------------------------------------")
        print(f"Total Families created: {total_families_created}")
        print(f"Total Members created: {total_members_created}")
        print(f"Total Users/Students created: {total_users_created}")
        print("Enrolled them in courses and assigned counseling sessions!")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"Error during mass seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_mass_data()
