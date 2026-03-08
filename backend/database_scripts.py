from sqlalchemy import text
from sqlalchemy.orm import Session

def create_stored_procedures(db: Session):
    """
    Creates the required Stored Procedures for CCF Platform.
    """
    
    # SP for calculating student status based on course completion and prerequisites
    sp_calculate_student_status = """
    CREATE OR REPLACE FUNCTION sp_calculate_student_status(p_user_id INTEGER)
    RETURNS TABLE (
        course_id INTEGER,
        course_title VARCHAR,
        total_lessons INTEGER,
        completed_lessons INTEGER,
        progress_percentage FLOAT,
        is_approved BOOLEAN
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT 
            c.id, 
            c.title,
            (SELECT COUNT(*) FROM lessons l WHERE l.course_id = c.id)::INTEGER as total_lessons,
            (SELECT COUNT(*) FROM assessment_attempts aa 
             JOIN enrollments e2 ON aa.enrollment_id = e2.id 
             WHERE e2.user_id = p_user_id AND e2.course_id = c.id AND aa.passed = True)::INTEGER as completed_lessons,
            e.progress_percent,
            e.approved
        FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.user_id = p_user_id;
    END;
    $$ LANGUAGE plpgsql;
    """

    # SP for generating a community impact report
    sp_generate_community_report = """
    CREATE OR REPLACE FUNCTION sp_generate_community_report()
    RETURNS TABLE (
        category TEXT,
        total_count BIGINT,
        description TEXT
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT 'Families'::TEXT, COUNT(*)::BIGINT, 'Total de familias registradas'::TEXT FROM families
        UNION ALL
        SELECT 'Members'::TEXT, COUNT(*)::BIGINT, 'Total de miembros activos'::TEXT FROM members
        UNION ALL
        SELECT 'Glory Houses'::TEXT, COUNT(*)::BIGINT, 'Total de Casas de Gloria activas'::TEXT FROM glory_houses
        UNION ALL
        SELECT 'Volunteers'::TEXT, COUNT(*)::BIGINT, 'Total de servidores en el equipo'::TEXT FROM volunteers;
    END;
    $$ LANGUAGE plpgsql;
    """

    # Execute the SP creation
    try:
        db.execute(text(sp_calculate_student_status))
        db.execute(text(sp_generate_community_report))
        db.commit()
        print("Stored Procedures created successfully.")
    except Exception as e:
        print(f"Skipping Stored Procedure creation (likely non-Postgres DB): {e}")
        db.rollback()
