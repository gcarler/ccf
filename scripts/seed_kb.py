from backend.core.database import SessionLocal
from backend import crud, schemas, models

def seed_kb():
    db = SessionLocal()
    try:
        entries = [
            {
                "title": "Doctrina de la Biblia",
                "content": "Creemos que la Biblia es la palabra de Dios, inspirada e infalible. Es nuestra única regla de fe y conducta.",
                "category": "Doctrine"
            },
            {
                "title": "Manual de Líderes de Casa de Bendición",
                "content": "Un líder de Casa de Bendición debe velar por el crecimiento espiritual de sus miembros, reportar asistencia semanalmente y fomentar la comunión.",
                "category": "Manual"
            },
            {
                "title": "Política de Privacidad de Datos",
                "content": "En CCF protegemos tus datos personales según la ley vigente. Nunca compartimos información sensible con terceros sin consentimiento.",
                "category": "Policy"
            }
        ]
        for e in entries:
            crud.create_kb_entry(db, **e)
        print("Knowledge Base seeded!")
    except Exception as e:
        print(f"Error seeding KB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_kb()
