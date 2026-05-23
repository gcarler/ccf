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

    # SP for summarizing project portfolio health
    sp_project_portfolio_summary = """
    CREATE OR REPLACE FUNCTION sp_project_portfolio_summary()
    RETURNS TABLE (
        project_status TEXT,
        total_projects BIGINT,
        total_tasks BIGINT,
        completed_tasks BIGINT,
        completion_ratio FLOAT
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT
            p.status::TEXT,
            COUNT(DISTINCT p.id)::BIGINT AS total_projects,
            COUNT(t.id)::BIGINT AS total_tasks,
            COUNT(CASE WHEN t.status = 'done' THEN 1 END)::BIGINT AS completed_tasks,
            CASE
                WHEN COUNT(t.id) = 0 THEN 0::FLOAT
                ELSE (COUNT(CASE WHEN t.status = 'done' THEN 1 END)::FLOAT / COUNT(t.id)::FLOAT)
            END AS completion_ratio
        FROM projects p
        LEFT JOIN project_tasks t ON t.project_id = p.id
        GROUP BY p.status;
    END;
    $$ LANGUAGE plpgsql;
    """

    # SP for summarizing workload by assignee
    sp_project_workload_summary = """
    CREATE OR REPLACE FUNCTION sp_project_workload_summary()
    RETURNS TABLE (
        assignee_id INTEGER,
        open_tasks BIGINT,
        in_review BIGINT,
        overdue_tasks BIGINT
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT
            t.assignee_id,
            COUNT(CASE WHEN t.status <> 'done' THEN 1 END)::BIGINT AS open_tasks,
            COUNT(CASE WHEN t.status = 'review' THEN 1 END)::BIGINT AS in_review,
            COUNT(CASE WHEN t.due_date IS NOT NULL AND t.due_date < NOW() AND t.status <> 'done' THEN 1 END)::BIGINT AS overdue_tasks
        FROM project_tasks t
        GROUP BY t.assignee_id;
    END;
    $$ LANGUAGE plpgsql;
    """

    # Execute the SP creation
    try:
        db.execute(text(sp_calculate_student_status))
        db.execute(text(sp_generate_community_report))
        db.execute(text(sp_project_portfolio_summary))
        db.execute(text(sp_project_workload_summary))
        db.commit()
        print("Stored Procedures created successfully.")
    except Exception as e:
        print(f"Skipping Stored Procedure creation (likely non-Postgres DB): {e}")
        db.rollback()
