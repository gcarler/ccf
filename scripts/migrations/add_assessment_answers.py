from backend.core.database import engine, Base
from backend.models_academy import AssessmentAnswer, AssessmentAttempt # Import models to register them with Base

def migrate():
    print("Creating assessment_answers table...")
    Base.metadata.create_all(bind=engine, tables=[AssessmentAnswer.__table__])
    print("Done.")

if __name__ == "__main__":
    migrate()
