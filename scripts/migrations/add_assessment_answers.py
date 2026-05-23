from backend.core.database import Base, engine
from backend.models_academy import (  # Import models to register them with Base
    AssessmentAnswer,
    AssessmentAttempt,
)


def migrate():
    print("Creating assessment_answers table...")
    Base.metadata.create_all(bind=engine, tables=[AssessmentAnswer.__table__])
    print("Done.")


if __name__ == "__main__":
    migrate()
