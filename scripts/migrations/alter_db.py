import os

from sqlalchemy import text

from backend.core.database import engine


def alter_db():
    try:
        with engine.begin() as conn:
            try:
                conn.execute(
                    text("ALTER TABLE project_tasks ADD COLUMN parent_id INTEGER;")
                )
                print("Added parent_id")
            except Exception as e:
                print(f"Skipped parent_id: {e}")

            try:
                conn.execute(
                    text(
                        "ALTER TABLE project_tasks ADD COLUMN order_index INTEGER DEFAULT 0;"
                    )
                )
                print("Added order_index")
            except Exception as e:
                print(f"Skipped order_index: {e}")

            try:
                conn.execute(
                    text(
                        "ALTER TABLE enrollments ADD COLUMN access_window_end DATETIME;"
                    )
                )
                print("Added access_window_end to enrollments")
            except Exception as e:
                print(f"Skipped access_window_end: {e}")

            try:
                # Manual create table since SQLAlchemy already knows it
                conn.execute(
                    text(
                        """
                    CREATE TABLE academy_activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type VARCHAR(50) NOT NULL,
                        course_id INTEGER,
                        user_id INTEGER,
                        modality VARCHAR(20),
                        value DECIMAL(10, 2) DEFAULT 1.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(course_id) REFERENCES courses(id),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                """
                    )
                )
                print("Created academy_activity_logs table")
            except Exception as e:
                print(f"Skipped academy_activity_logs creation: {e}")

            try:
                conn.execute(
                    text(
                        """
                    CREATE TABLE course_attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        enrollment_id INTEGER NOT NULL,
                        session_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'present',
                        recorded_by_id INTEGER,
                        FOREIGN KEY(enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
                        FOREIGN KEY(recorded_by_id) REFERENCES users(id)
                    )
                """
                    )
                )
                print("Created course_attendance table")
            except Exception as e:
                print(f"Skipped course_attendance creation: {e}")
    except Exception as e:
        print(f"Error connecting to db: {e}")


if __name__ == "__main__":
    alter_db()
