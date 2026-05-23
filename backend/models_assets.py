from backend.models_shared import *
from backend.models_shared import _utcnow


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    stock = Column(Integer, default=0)
    status = Column(String(20), default="ok")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class AssetItem(Base):
    __tablename__ = "assets_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    brand = Column(String(100))
    serial_number = Column(String(100), unique=True)
    purchase_price = Column(Float)
    current_status = Column(String(50), default="Disponible")
    category = Column(String(100), default="Mobiliario")
    created_at = Column(DateTime, default=_utcnow)


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("assets_items.id"))
    service_date = Column(DateTime, default=_utcnow)
    description = Column(Text)
    cost = Column(Float, default=0.0)

    asset = relationship("AssetItem")
