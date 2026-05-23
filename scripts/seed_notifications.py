from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_notifications():
    db = SessionLocal()
    try:
        # Find user with id 1
        user = db.query(models.User).filter(models.User.id == 1).first()
        if user:
            notifications = [
                schemas.NotificationCreate(
                    user_id=user.id,
                    title="Nueva mención",
                    content="Juan te mencionó en 'Diseño UI Proyectos'",
                    notif_type="mention",
                    link_url="/projects",
                ),
                schemas.NotificationCreate(
                    user_id=user.id,
                    title="Tarea completada",
                    content="La tarea 'Migración DB' ha sido finalizada por Alex.",
                    notif_type="task",
                    link_url="/projects",
                ),
                schemas.NotificationCreate(
                    user_id=user.id,
                    title="Actualización de Sistema",
                    content="Nueva versión 4.2 disponible con mejoras en CRM.",
                    notif_type="system",
                ),
            ]
            for n in notifications:
                crud.create_notification(db, n)
            print("Notifications seeded for user 1!")
        else:
            print("User 1 not found.")
    except Exception as e:
        print(f"Error seeding notifications: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_notifications()
