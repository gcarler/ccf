from backend.database import engine, SessionLocal
from backend.models import Base, RoleDefinition

Base.metadata.create_all(bind=engine)

db = SessionLocal()

ROLES = [
    {'name': 'Todos', 'color': 'text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400', 'is_leadership': False},
    {'name': 'Apóstol', 'color': 'text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400', 'is_leadership': True},
    {'name': 'Profeta', 'color': 'text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 dark:text-indigo-400', 'is_leadership': True},
    {'name': 'Evangelista', 'color': 'text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400', 'is_leadership': True},
    {'name': 'Pastor', 'color': 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400', 'is_leadership': True},
    {'name': 'Maestro', 'color': 'text-teal-600 bg-teal-50 dark:bg-teal-900/20 dark:text-teal-400', 'is_leadership': True},
    {'name': 'Ministro de Culto', 'color': 'text-rose-600 bg-rose-50 dark:bg-rose-900/20 dark:text-rose-400', 'is_leadership': True},
    {'name': 'Líder', 'color': 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400', 'is_leadership': True},
    {'name': 'Servidor', 'color': 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-400', 'is_leadership': False},
    {'name': 'Miembro Bautizado', 'color': 'text-sky-600 bg-sky-50 dark:bg-sky-900/20 dark:text-sky-400', 'is_leadership': False},
    {'name': 'Asistente', 'color': 'text-violet-600 bg-violet-50 dark:bg-violet-900/20 dark:text-violet-400', 'is_leadership': False},
    {'name': 'Visitante Servicios', 'color': 'text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400', 'is_leadership': False},
    {'name': 'Visitante Faro en Casa', 'color': 'text-cyan-600 bg-cyan-50 dark:bg-cyan-900/20 dark:text-cyan-400', 'is_leadership': False},
    {'name': 'Visitante Online', 'color': 'text-fuchsia-600 bg-fuchsia-50 dark:bg-fuchsia-900/20 dark:text-fuchsia-400', 'is_leadership': False},
]

for r in ROLES:
    exists = db.query(RoleDefinition).filter_by(name=r['name']).first()
    if not exists:
        db.add(RoleDefinition(**r))

db.commit()
print("Roles seeded!")
db.close()
