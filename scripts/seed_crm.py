import asyncio
from backend.core.database import SessionLocal
from backend import crud, schemas, models
from datetime import datetime

def seed_crm():
    db = SessionLocal()
    try:
        # Create some Glory Houses if none exist
        existing_houses = crud.get_glory_houses(db)
        if not existing_houses:
            houses_data = [
                schemas.GloryHouseCreate(
                    name="Casa de Bendición Faro Norte",
                    zone="Norte",
                    leader_name="Pedro Martínez",
                    schedule="Jueves 7:00 PM",
                    address="Calle 100 #45-12",
                    is_active=True
                ),
                schemas.GloryHouseCreate(
                    name="Centro Vida Central",
                    zone="Centro",
                    leader_name="Marta Lucía",
                    schedule="Martes 6:30 PM",
                    address="Carrera 15 #32-10",
                    is_active=True
                ),
                schemas.GloryHouseCreate(
                    name="Jóvenes CCF Sur",
                    zone="Sur",
                    leader_name="Andrés Felipe",
                    schedule="Sábado 4:00 PM",
                    address="Calle 45 Sur #12-34",
                    is_active=True
                )
            ]
            for h in houses_data:
                crud.create_glory_house(db, h)
            print("Glory Houses seeded!")

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
                    status="Activo"
                ),
                schemas.MemberCreate(
                    first_name="María",
                    last_name="García",
                    email="maria.garcia@email.com",
                    phone="+57 300 222 3344",
                    church_role="member",
                    status="Seguimiento"
                ),
                schemas.MemberCreate(
                    first_name="Carlos",
                    last_name="Rodríguez",
                    email="carlos.rod@email.com",
                    phone="+57 300 333 4455",
                    church_role="member",
                    status="Activo"
                ),
                schemas.MemberCreate(
                    first_name="Elena",
                    last_name="Gómez",
                    email="elena.gomez@email.com",
                    phone="+57 300 444 5566",
                    church_role="member",
                    status="Inactivo"
                )
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
