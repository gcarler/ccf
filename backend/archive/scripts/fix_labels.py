import json
import os

from backend.core.database import SessionLocal
from backend.models_projects import ProjectTask

db = SessionLocal()
tasks = db.query(ProjectTask).all()
for t in tasks:
    if t.labels and not isinstance(t.labels, list):
        print(f"Task {t.id} has invalid labels: {t.labels} (type: {type(t.labels)})")
        if isinstance(t.labels, str):
            try:
                parsed = json.loads(t.labels)
                if isinstance(parsed, list):
                    t.labels = parsed
                else:
                    t.labels = [t.labels]
            except:
                t.labels = [t.labels]
        else:
            t.labels = []

    # Let's also check attachments
    if t.attachments and not isinstance(t.attachments, list):
         print(f"Task {t.id} has invalid attachments: {t.attachments} (type: {type(t.attachments)})")
         t.attachments = []
         
db.commit()
print("Fixed tasks.")
db.close()
