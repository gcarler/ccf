import codecs
import re

with codecs.open("backend/models.py", "r", "utf-8") as f:
    c = f.read()

# 1. Update GloryHouse model
gh_old = """    capacity = Column(Integer, default=15)
    schedule = Column(String(100), nullable=True)
    status = Column(String(20), default="Activo")
    created_at = Column(DateTime, default=_utcnow)"""

gh_new = """    capacity = Column(Integer, default=15)
    day_of_week = Column(String(20), nullable=True) # e.g. "Lunes", "Martes"
    time = Column(String(20), nullable=True) # e.g. "19:00"
    status = Column(String(20), default="Activo")
    created_at = Column(DateTime, default=_utcnow)

class FaroSeason(Base):
    __tablename__ = "faro_seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) # e.g. "Campaña Faro 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="Activa") # Activa, Finalizada
    created_at = Column(DateTime, default=_utcnow)

class GloryHouseSession(Base):
    __tablename__ = "glory_house_sessions"
    id = Column(Integer, primary_key=True, index=True)
    glory_house_id = Column(Integer, ForeignKey("glory_houses.id"), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey("faro_seasons.id"), nullable=False, index=True)
    session_date = Column(Date, nullable=False)
    status = Column(String(20), default="Realizada") # Realizada, Cancelada
    created_at = Column(DateTime, default=_utcnow)
    
    glory_house = relationship("GloryHouse")
    season = relationship("FaroSeason")

class GloryHouseAttendance(Base):
    __tablename__ = "glory_house_attendance"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("glory_house_sessions.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    attended = Column(Boolean, default=True)
    scanned_at = Column(DateTime, default=_utcnow)
    
    session = relationship("GloryHouseSession")
    member = relationship("Member")"""

if "class FaroSeason" not in c:
    c = c.replace(gh_old, gh_new)

    # We might also need Date if not imported
    if " Date," not in c and " Date " not in c:
        c = c.replace(
            "from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, UniqueConstraint, Table",
            "from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, UniqueConstraint, Table, Date",
        )

    with codecs.open("backend/models.py", "w", "utf-8") as f:
        f.write(c)
    print("Models injected")
else:
    print("Models already exist")
