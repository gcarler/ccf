from backend.core.database import SessionLocal
from backend import crud, schemas, models

def seed_support():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == 1).first()
        if user:
            tickets = [
                schemas.SupportTicketCreate(
                    user_id=user.id,
                    subject="Problema con acceso a curso",
                    description="No puedo ver las lecciones de Fundamentos I.",
                    priority="alta",
                    category="Tecnico"
                ),
                schemas.SupportTicketCreate(
                    user_id=user.id,
                    subject="Duda sobre donaciones",
                    description="¿Cómo puedo descargar mi certificado de donación?",
                    priority="media",
                    category="Financiero"
                ),
                schemas.SupportTicketCreate(
                    user_id=user.id,
                    subject="Petición de Oración",
                    description="Pido oración por mi familia en este tiempo difícil.",
                    priority="media",
                    category="Pastoral"
                )
            ]
            for t in tickets:
                crud.create_support_ticket(db, t)
            print("Support tickets seeded!")
        else:
            print("User 1 not found.")
    except Exception as e:
        print(f"Error seeding support: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_support()
