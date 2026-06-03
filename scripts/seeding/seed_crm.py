import asyncio
from datetime import datetime

from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_crm():
    db = SessionLocal()
    try:
        # Create some grupos if none exist
        existing_grupos = db.query(models.GrupoEvangelismo).first()
        if not existing_grupos:
            grupos_data = [
                models.GrupoEvangelismo(
                    name="Casa de Bendición Faro Norte",
                    zone="Norte",
                    leader_name="Pedro Martínez",
                    day_of_week="Jueves",
                    start_time="7:00 PM",
                    address="Calle 100 #45-12",
                    status="Activo",
                ),
                models.GrupoEvangelismo(
                    name="Centro Vida Central",
                    zone="Centro",
                    leader_name="Marta Lucía",
                    day_of_week="Martes",
                    start_time="6:30 PM",
                    address="Carrera 15 #32-10",
                    status="Activo",
                ),
                models.GrupoEvangelismo(
                    name="Jóvenes CCF Sur",
                    zone="Sur",
                    leader_name="Andrés Felipe",
                    day_of_week="Sábado",
                    start_time="4:00 PM",
                    address="Calle 45 Sur #12-34",
                    status="Activo",
                ),
            ]
            for grupo in grupos_data:
                db.add(grupo)
            db.commit()
            print("Grupos seeded!")

        # Create some Members if none exist
        existing_members = crud.get_members(db)
        if len(existing_members) < 5:
            members_data = [
                schemas.MemberCreate(
                    first_name="Juan",
                    last_name="Pérez",
                    email="juan.perez@email.com",
                    phone="+57 300 111 2233",
                    church_role="member",
                    status="Activo",
                ),
                schemas.MemberCreate(
                    first_name="María",
                    last_name="García",
                    email="maria.garcia@email.com",
                    phone="+57 300 222 3344",
                    church_role="member",
                    status="Seguimiento",
                ),
                schemas.MemberCreate(
                    first_name="Carlos",
                    last_name="Rodríguez",
                    email="carlos.rod@email.com",
                    phone="+57 300 333 4455",
                    church_role="member",
                    status="Activo",
                ),
                schemas.MemberCreate(
                    first_name="Elena",
                    last_name="Gómez",
                    email="elena.gomez@email.com",
                    phone="+57 300 444 5566",
                    church_role="member",
                    status="Inactivo",
                ),
            ]
            for m in members_data:
                crud.create_member(db, m)
            print("Members seeded!")

    except Exception as e:
        print(f"Error seeding CRM: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_crm()
