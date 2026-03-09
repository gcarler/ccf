import pathlib
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend import crud
from backend import models
from backend import schemas
from backend.auth import normalize_role, require_active_user, require_admin, require_staff_or_admin
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.uploads import sanitize_filename, save_upload


router = APIRouter()
settings = get_settings()


@router.get("/announcements", response_model=List[schemas.Announcement])
def get_announcements(db: Session = Depends(get_db)):
    return crud.get_announcements(db)


@router.post("/admin/announcements", response_model=schemas.Announcement)
def create_announcement(
    announcement: schemas.AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_announcement(db=db, announcement=announcement)
    record_admin_action(
        db,
        current_user,
        action="create_announcement",
        resource_type="announcement",
        resource_id=str(created.id),
        metadata={"title": created.title},
    )
    return created


@router.delete("/admin/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    if crud.delete_announcement(db, announcement_id):
        record_admin_action(
            db,
            current_user,
            action="delete_announcement",
            resource_type="announcement",
            resource_id=str(announcement_id),
        )
        return {"detail": "Announcement deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")


@router.get("/sermons", response_model=List[schemas.Sermon])
def get_sermons(db: Session = Depends(get_db)):
    return crud.get_sermons(db)


@router.post("/admin/sermons", response_model=schemas.Sermon)
def create_sermon(
    sermon: schemas.SermonCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_sermon(db=db, sermon=sermon)
    record_admin_action(
        db,
        current_user,
        action="create_sermon",
        resource_type="sermon",
        resource_id=str(created.id),
        metadata={"title": created.title},
    )
    return created


@router.delete("/admin/sermons/{sermon_id}")
def delete_sermon(
    sermon_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    if crud.delete_sermon(db, sermon_id):
        record_admin_action(
            db,
            current_user,
            action="delete_sermon",
            resource_type="sermon",
            resource_id=str(sermon_id),
        )
        return {"detail": "Sermon deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sermon not found")


@router.get("/books", response_model=List[schemas.Book])
def get_books(db: Session = Depends(get_db)):
    return crud.get_books(db)


@router.post("/admin/books", response_model=schemas.Book)
def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_book(db=db, book=book)
    record_admin_action(
        db,
        current_user,
        action="create_book",
        resource_type="book",
        resource_id=str(created.id),
        metadata={"title": created.title},
    )
    return created


@router.delete("/admin/books/{book_id}")
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    if crud.delete_book(db, book_id):
        record_admin_action(
            db,
            current_user,
            action="delete_book",
            resource_type="book",
            resource_id=str(book_id),
        )
        return {"detail": "Book deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


@router.get("/content/{page_key}", response_model=schemas.PageContent)
def get_page_content(page_key: str, db: Session = Depends(get_db)):
    content = crud.get_page_content(db, page_key)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page content not found")
    return content


@router.patch("/admin/content/{page_key}", response_model=schemas.PageContent)
def update_page_content(
    page_key: str,
    content: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    updated = crud.update_page_content(db=db, page_key=page_key, content=content)
    record_admin_action(
        db,
        current_user,
        action="update_page_content",
        resource_type="page_content",
        resource_id=page_key,
        metadata=content.model_dump(exclude_unset=True),
    )
    return updated


@router.get("/content/{page_key}/versions", response_model=List[schemas.PageContentVersion])
def get_page_versions(
    page_key: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_page_content_versions(db, page_key=page_key, limit=limit)


@router.post("/testimonials", response_model=schemas.Testimonial)
def create_testimonial(
    testimonial: schemas.TestimonialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    user_id = int(getattr(current_user, "id", 0))
    if normalize_role(str(current_user.role)) != "admin" and user_id != testimonial.author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only post your own testimonial")
    return crud.create_testimonial(db=db, testimonial=testimonial)


@router.get("/testimonials", response_model=List[schemas.Testimonial])
def read_testimonials(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_testimonials(db, skip=skip, limit=limit, approved_only=True)


@router.get("/admin/testimonials", response_model=List[schemas.Testimonial])
def read_all_testimonials(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_testimonials(db, skip=skip, limit=limit, approved_only=False)


@router.patch("/admin/testimonials/{testimonial_id}", response_model=schemas.Testimonial)
def update_testimonial_status(
    testimonial_id: int,
    testimonial: schemas.TestimonialUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    db_testimonial = crud.update_testimonial(db, testimonial_id=testimonial_id, testimonial=testimonial)
    if db_testimonial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Testimonial not found")
    record_admin_action(
        db,
        current_user,
        action="update_testimonial",
        resource_type="testimonial",
        resource_id=str(testimonial_id),
        metadata=testimonial.model_dump(exclude_unset=True),
    )
    return db_testimonial


@router.post("/admin/uploads", response_model=schemas.MediaAsset)
async def upload_media_asset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    filename = sanitize_filename(file.filename or "asset")
    unique_name = f"media_{uuid.uuid4().hex}_{filename}"
    try:
        contents = await file.read()
        save_upload(contents, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    asset = crud.create_media_asset(
        db,
        filename=filename,
        url=f"/static/{unique_name}",
        mime_type=file.content_type,
        size_bytes=len(contents),
    )
    record_admin_action(
        db,
        current_user,
        action="upload_media_asset",
        resource_type="media_asset",
        resource_id=str(asset.id),
        metadata={"filename": filename, "mime_type": file.content_type},
    )
    return asset


@router.post(
    "/analytics/{content_type}/{content_id}/events",
    response_model=schemas.ContentMetric,
)
def track_content_metric(
    content_type: str,
    content_id: int,
    payload: schemas.ContentMetricIncrement,
    db: Session = Depends(get_db),
):
    return crud.increment_content_metric(
        db,
        content_type=content_type,
        content_id=content_id,
        metric_type=payload.metric_type,
        amount=payload.amount,
    )
