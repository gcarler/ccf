"""Assets and maintenance logs CRUD."""
import datetime as dt
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from backend import models


# ── Assets ──────────────────────────────────────────────

def get_assets(db: Session) -> List[models.AssetItem]:
    return db.query(models.AssetItem).order_by(models.AssetItem.name.asc()).all()


def get_asset(db: Session, item_id: uuid.UUID) -> Optional[models.AssetItem]:
    return db.query(models.AssetItem).filter(models.AssetItem.id == item_id).first()


def create_asset(
    db: Session,
    name: str,
    brand: Optional[str] = None,
    serial_number: Optional[str] = None,
    purchase_price: Optional[float] = None,
    current_status: str = "Disponible",
    category: str = "Mobiliario",
) -> models.AssetItem:
    row = models.AssetItem(
        name=name,
        brand=brand,
        serial_number=serial_number,
        purchase_price=purchase_price,
        current_status=current_status,
        category=category,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_asset(
    db: Session,
    item_id: uuid.UUID,
    *,
    name: Optional[str] = None,
    brand: Optional[str] = None,
    serial_number: Optional[str] = None,
    purchase_price: Optional[float] = None,
    current_status: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[models.AssetItem]:
    row = get_asset(db, item_id)
    if not row:
        return None
    if name is not None:
        row.name = name
    if brand is not None:
        row.brand = brand
    if serial_number is not None:
        row.serial_number = serial_number
    if purchase_price is not None:
        row.purchase_price = purchase_price
    if current_status is not None:
        row.current_status = current_status
    if category is not None:
        row.category = category
    db.commit()
    db.refresh(row)
    return row


def delete_asset(db: Session, item_id: uuid.UUID) -> bool:
    row = get_asset(db, item_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Maintenance Logs ────────────────────────────────────

def get_maintenance_logs(db: Session, item_id: Optional[uuid.UUID] = None) -> List[models.MaintenanceLog]:
    query = db.query(models.MaintenanceLog)
    if item_id:
        query = query.filter(models.MaintenanceLog.item_id == item_id)
    return query.order_by(models.MaintenanceLog.service_date.desc()).all()


def create_maintenance_log(
    db: Session, item_id: uuid.UUID, description: str, service_date: dt.date, cost: float = 0.0
) -> models.MaintenanceLog:
    row = models.MaintenanceLog(
        item_id=item_id,
        description=description,
        service_date=dt.datetime.combine(service_date, dt.time.min),
        cost=cost,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
