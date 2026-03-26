from fastapi import APIRouter, Depends

from backend import models, crud
from backend.analytics import queries
from backend.auth import require_admin
from backend.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return crud.get_analytics_summary(db)


@router.get("/events/summary")
def event_summary(days: int = 7, current_user: models.User = Depends(require_admin)):
    return queries.get_event_summary(days)


@router.get("/events/course-performance")
def course_performance(limit: int = 10, current_user: models.User = Depends(require_admin)):
    return queries.get_course_performance(limit)


@router.get("/events/raw")
def raw_events(limit: int = 50, current_user: models.User = Depends(require_admin)):
    return queries.list_raw_events(limit)
