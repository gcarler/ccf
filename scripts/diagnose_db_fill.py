
import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models
from backend.core.database import SessionLocal

def check_empty_tables():
    db = SessionLocal()
    print("🔍 Diagnosticando tablas vacías (Lista Real)...")
    
    model_classes = [
        models.Role, models.Level, models.User, models.Badge, models.UserBadge,
        models.UserUIPreference, models.Course, models.CoursePrerequisite,
        models.Lesson, models.LessonProgress, models.Assessment, 
        models.AssessmentQuestion, models.AssessmentOption, models.AssessmentAttempt,
        models.Resource, models.AssignmentSubmission, models.FormalActa,
        models.ForumThread, models.ForumComment, models.Family, models.GloryHouse,
        models.Enrollment, models.ConsolidationPipeline, models.ChatMessage,
        models.CrmEvent, models.EventAttendance, models.CounselingTicket,
        models.PrayerRequest, models.Ministry, models.Member,
        models.Project, models.ProjectTask, models.TaskSupply, models.InventoryItem,
        models.AgentInsight, models.RefreshToken, models.AgentTask,
        models.AdminAuditLog, models.PastoralCallLog, models.PageContent,
        models.PageContentVersion, models.ContentMetric, models.MediaAsset,
        models.Notification, models.CommunicationLog, models.Certificate
    ]
    
    empty_tables = []
    for model in model_classes:
        try:
            count = db.query(model).count()
            print(f"📊 {model.__tablename__}: {count} filas")
            if count == 0:
                empty_tables.append(model)
        except Exception as e:
            print(f"❌ Error al leer {model.__tablename__}: {e}")
            
    print("\n--- RESULTADO FINAL ---")
    if not empty_tables:
        print("✅ ¡Perfecto! Ninguna tabla está vacía.")
    else:
        print(f"⚠️ Se encontraron {len(empty_tables)} tablas vacías.")
        for table in empty_tables:
            print(f"   - {table.__tablename__}")
            
    db.close()
    return empty_tables

if __name__ == "__main__":
    check_empty_tables()
