import codecs

with codecs.open('backend/models.py', 'r', 'utf-8') as f:
    c = f.read()

faro_season_old = """class FaroSeason(Base):
    __tablename__ = "faro_seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) # e.g. "Campaña Faro 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="Activa") # Activa, Finalizada
    created_at = Column(DateTime, default=_utcnow)"""

faro_season_new = """class FaroSeason(Base):
    __tablename__ = "faro_seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) # e.g. "Campaña Faro 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    periodicity = Column(String(20), default="SEMANAL") # SEMANAL, MENSUAL
    status = Column(String(20), default="Activa") # Activa, Finalizada
    created_at = Column(DateTime, default=_utcnow)"""

if "periodicity =" not in faro_season_old and "periodicity =" not in c[c.find('class FaroSeason'):c.find('class GloryHouseSession')]:
    c = c.replace(faro_season_old, faro_season_new)
    with codecs.open('backend/models.py', 'w', 'utf-8') as f:
        f.write(c)
    print("Periodicity added to FaroSeason")
else:
    print("Periodicity already exists")
