import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_exams():
    db = SessionLocal()
    try:
        # 1. Create a Course if none exists
        course = db.query(models.Course).first()
        if not course:
            course = models.Course(
                code="FUND1",
                title="Fundamentos de la Fe I",
                description="Curso introductorio a la doctrina cristiana.",
                modality="non-formal",
                is_published=True,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            print(f"Created course: {course.title}")

        # 2. Create an Assessment for the course
        assessment = schemas.AssessmentCreate(
            course_id=course.id,
            title="Examen Final - Fundamentos I",
            description="Demuestra lo aprendido en este primer nivel.",
            max_score=100,
            passing_score=70,
        )
        db_assessment = models.Assessment(**assessment.model_dump())
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        print(f"Created assessment: {db_assessment.title}")

        # 3. Add Questions
        q1 = crud.create_assessment_question(
            db,
            schemas.AssessmentQuestionCreate(
                assessment_id=db_assessment.id,
                question_text="¿Quién es el autor de la Biblia?",
                question_type="multiple_choice",
                points=50,
                order_index=1,
            ),
        )
        crud.create_question_option(
            db,
            schemas.QuestionOptionCreate(
                question_id=q1.id,
                option_text="Dios a través de hombres inspirados",
                is_correct=True,
            ),
        )
        crud.create_question_option(
            db,
            schemas.QuestionOptionCreate(
                question_id=q1.id,
                option_text="Un grupo de historiadores griegos",
                is_correct=False,
            ),
        )

        q2 = crud.create_assessment_question(
            db,
            schemas.AssessmentQuestionCreate(
                assessment_id=db_assessment.id,
                question_text="La salvación es por obras.",
                question_type="true_false",
                points=50,
                order_index=2,
            ),
        )
        crud.create_question_option(
            db,
            schemas.QuestionOptionCreate(
                question_id=q2.id, option_text="Verdadero", is_correct=False
            ),
        )
        crud.create_question_option(
            db,
            schemas.QuestionOptionCreate(
                question_id=q2.id, option_text="Falso", is_correct=True
            ),
        )

        print("Exams and questions seeded successfully!")

    except Exception as e:
        print(f"Error seeding exams: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_exams()
