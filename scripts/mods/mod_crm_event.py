with open("backend/models.py", "r", encoding="utf-8") as f:
    c = f.read()

old_str = '    status = Column(String(20), default="SCHEDULED", index=True)\n    created_at = Column(DateTime, default=_utcnow, index=True)'
new_str = '    status = Column(String(20), default="SCHEDULED", index=True)\n    target_audience = Column(String(50), default="ALL")\n    target_role_id = Column(Integer, ForeignKey("role_definitions.id"), nullable=True)\n    created_at = Column(DateTime, default=_utcnow, index=True)'

c = c.replace(old_str, new_str)

with open("backend/models.py", "w", encoding="utf-8") as f:
    f.write(c)
print("Done!")
