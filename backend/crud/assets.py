"""Assets and maintenance logs CRUD."""
import datetime as dt
import uuid
from typing import List

from sqlalchemy.orm import Session

from backend import models


def get_assets(db: Session) -> List[models.AssetItem]:
    return db.query(models.AssetItem).all()


def create_maintenance_log(db: Session, item_id: uuid.UUID, description: str, service_date: dt.date) -> models.MaintenanceLog:
    row = models.MaintenanceLog(
        item_id=item_id,
        description=description,
        service_date=dt.datetime.combine(service_date, dt.time.min)
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
