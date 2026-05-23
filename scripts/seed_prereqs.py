from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_prereqs():
    db = SessionLocal()
    try:
        # 1. Ensure we have two courses
        c1 = db.query(models.Course).filter(models.Course.code == "FUND1").first()
        if not c1:
            c1 = models.Course(
                code="FUND1",
                title="Fundamentos I",
                modality="formal",
                is_published=True,
            )
            db.add(c1)
            db.commit()
            db.refresh(c1)

        c2 = db.query(models.Course).filter(models.Course.code == "FUND2").first()
        if not c2:
            c2 = models.Course(
                code="FUND2",
                title="Fundamentos II",
                modality="formal",
                is_published=True,
            )
            db.add(c2)
            db.commit()
            db.refresh(c2)

        # 2. Add prerequisite: FUND2 needs FUND1
        exists = (
            db.query(models.CoursePrerequisite)
            .filter(
                models.CoursePrerequisite.course_id == c2.id,
                models.CoursePrerequisite.prerequisite_course_id == c1.id,
            )
            .first()
        )

        if not exists:
            prereq = models.CoursePrerequisite(
                course_id=c2.id, prerequisite_course_id=c1.id
            )
            db.add(prereq)
            db.commit()
            print(f"Prerequisite added: {c2.title} now requires {c1.title}")
        else:
            print("Prerequisite already exists.")

    except Exception as e:
        print(f"Error seeding prereqs: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_prereqs()
