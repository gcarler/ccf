import datetime as dt

from backend.core.database import SessionLocal
from backend.models import (Assessment, AssessmentOption, AssessmentQuestion,
                            Course, Lesson)


def seed_assessments():
    db = SessionLocal()
    try:
        # Find the quiz lesson for Disc-1
        lesson = (
            db.query(Lesson)
            .join(Course)
            .filter(Course.code == "DISC-1", Lesson.content_type == "quiz")
            .first()
        )

        if not lesson:
            print(
                "❌ Quiz lesson for DISC-1 not found. Run seed_academy_full.py first."
            )
            return

        # 1. Create Assessment for this lesson
        # Check if already exists
        existing = (
            db.query(Assessment).filter(Assessment.lesson_id == lesson.id).first()
        )
        if existing:
            print("ℹ️ Assessment already exists. Skipping.")
            return

        assessment = Assessment(
            title="Examen Final: Fundamentos de la Fe",
            lesson_id=lesson.id,
            min_score=70.0,
        )
        db.add(assessment)
        db.flush()

        # 2. Add Questions
        q1 = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text="¿Cuál es la base de nuestra salvación?",
            question_type="single_choice",
            points=50,
        )
        db.add(q1)
        db.flush()

        # Options for Q1
        db.add(
            AssessmentOption(
                question_id=q1.id, option_text="Nuestras buenas obras", is_correct=False
            )
        )
        db.add(
            AssessmentOption(
                question_id=q1.id,
                option_text="La gracia de Dios mediante la fe",
                is_correct=True,
            )
        )
        db.add(
            AssessmentOption(
                question_id=q1.id,
                option_text="Asistir todos los domingos",
                is_correct=False,
            )
        )

        q2 = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text="¿Qué representa el bautismo en agua?",
            question_type="single_choice",
            points=50,
        )
        db.add(q2)
        db.flush()

        # Options for Q2
        db.add(
            AssessmentOption(
                question_id=q2.id,
                option_text="Un rito de paso social",
                is_correct=False,
            )
        )
        db.add(
            AssessmentOption(
                question_id=q2.id,
                option_text="Identificación pública con la muerte y resurrección de Cristo",
                is_correct=True,
            )
        )
        db.add(
            AssessmentOption(
                question_id=q2.id,
                option_text="Un requisito para ser líder",
                is_correct=False,
            )
        )

        db.commit()
        print(f"✅ Assessment for '{lesson.title}' seeded successfully.")

    except Exception as e:
        print(f"❌ Error seeding assessments: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_assessments()
