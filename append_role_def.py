
class RoleDefinition(Base):
    __tablename__ = "role_definitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    color = Column(String(100), default="text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400")
    is_leadership = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
