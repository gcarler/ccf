"""Seed all modules for dashboard demo — single atomic transaction."""
import os, sys, random, uuid
from datetime import datetime, timedelta, timezone

os.environ['ENVIRONMENT'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite:////root/ccf/ccf_final.db'
sys.path.insert(0, '/root/ccf')
from sqlalchemy import text
from backend.core.database import engine

conn = engine.connect()
random.seed(42)
now = datetime.now(timezone.utc)

def rd(db=0, df=0):
    if df > 0: return now + timedelta(days=random.randint(1, df), hours=random.randint(0, 23))
    return now - timedelta(days=random.randint(1, db+1), hours=random.randint(0, 23))

print("=== SEED ===")

# 1. Personas (INTEGER pk)
pids = []
firsts = ["María","José","Luis","Ana","Carlos","Laura","Pedro","Sofía","Andrés","Valentina",
          "Diego","Camila","Jorge","Isabella","Miguel","Gabriela","David","Fernanda","Santiago","Luciana",
          "Óscar","Natalia","Héctor","Verónica","Raúl","Patricia","Felipe","Daniela","Cristian","Mónica"]
lasts = ["García","Rodríguez","Martínez","López","González","Pérez","Ramírez","Torres","Flores","Reyes"]
for i in range(30):
    pid = conn.execute(text("""
        INSERT INTO personas (first_name, last_name, email, phone, sede_id, created_at)
        VALUES (:fn,:ln,:em,:ph,1,:cr)
    """), {"fn":firsts[i],"ln":lasts[i%10],"em":f"{firsts[i].lower()}.{lasts[i%10].lower()}@email.com",
           "ph":f"300{random.randint(1000000,9999999)}","cr":rd(180)}).lastrowid
    pids.append(pid)

# 2. Users
for i in range(1,21):
    conn.execute(text("INSERT OR IGNORE INTO users(username,email,password_hash,role,is_active,created_at) VALUES(:u,:e,'x',:r,1,:c)"),
                 {"u":f"user{i}","e":f"user{i}@ccf.com","r":random.choice(["admin","pastor","leader","member","member"]),"c":rd(180)})

# 3. CampaignSeason
conn.execute(text("INSERT OR IGNORE INTO campaign_seasons(id,name) VALUES(1,'Temp 2026-1')"))

# 4. EvangelismStrategies (INTEGER pk)
for sid in range(1,4):
    conn.execute(text("INSERT OR IGNORE INTO evangelism_strategies(id,name,description,sede_id,status,created_at) VALUES(:id,:n,:d,1,'active',:c)"),
                 {"id":sid,"n":random.choice(["Cosecha","Multiplicación","Avance"]),"d":"Estrategia activa","c":rd(90)})

# 5. CellGroups with geo
zones=[("Chapinero",4.6453,-74.0635),("Usaquén",4.6950,-74.0300),("Suba",4.7450,-74.0850),
       ("Engativá",4.7050,-74.1150),("Kennedy",4.6250,-74.1450),("Fontibón",4.6750,-74.1450),
       ("Bosa",4.6050,-74.1950),("San Cristóbal",4.5650,-74.1150),("Usme",4.5150,-74.1250),
       ("Ciudad Bolívar",4.5550,-74.1650),("Teusaquillo",4.6350,-74.0850),("Barrios Unidos",4.6650,-74.0650)]
gids=[]
for zn,lat,lng in zones:
    gid=conn.execute(text("""
        INSERT INTO cell_groups(name,zone,latitude,longitude,capacity,day_of_week,start_time,status,
            sede_id,evangelism_strategy_id,leader_persona_id,created_at,updated_at)
        VALUES(:n,:z,:lat,:lng,:cap,:dow,:t,'active',1,:es,:lid,:c,:c)
    """),{"n":zn,"z":zn,"lat":round(lat+random.uniform(-.015,.015),6),"lng":round(lng+random.uniform(-.015,.015),6),
          "cap":random.randint(10,25),"dow":random.choice(["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]),
          "t":f"{random.randint(16,20)}:00","es":random.randint(1,3),"lid":random.choice(pids),"c":rd(120)}).lastrowid
    gids.append(gid)

# 6. CellGroupMembers
for gid in gids:
    for pid in random.sample(pids, random.randint(4,9)):
        conn.execute(text("INSERT OR IGNORE INTO cell_group_members(cell_group_id,persona_id,role,activo,fecha_ingreso) VALUES(:g,:p,:r,1,:f)"),
                     {"g":gid,"p":pid,"r":random.choice(["MIEMBRO","MIEMBRO","MIEMBRO","MIEMBRO","LIDER","COLIDER"]),"f":rd(90)})

# 7. Sessions + Attendance (10 weeks)
for gid in gids:
    mpids=[r[0] for r in conn.execute(text("SELECT persona_id FROM cell_group_members WHERE cell_group_id=:g AND activo=1"),{"g":gid}).all()]
    for w in range(10):
        sd=(now-timedelta(weeks=9-w,days=random.randint(0,2))).strftime("%Y-%m-%d")
        conn.execute(text("INSERT INTO cell_group_sessions(cell_group_id,season_id,session_date,status,topic,created_at) VALUES(:g,1,:sd,'REALIZADA',:t,:c)"),
                     {"g":gid,"sd":sd,"t":random.choice(["La fe","El amor","Oración","Frutos","Gracia"]),"c":sd})
        sid=conn.execute(text("SELECT id FROM cell_group_sessions WHERE cell_group_id=:g AND session_date=:sd"),{"g":gid,"sd":sd}).scalar()
        if sid and mpids:
            for pid in mpids:
                att=random.random()>.2
                conn.execute(text("INSERT INTO cell_group_attendance(session_id,persona_id,attended,estado,absence_reason_detail) VALUES(:s,:p,:a,:e,:d)"),
                             {"s":sid,"p":pid,"a":1 if att else 0,"e":"ASISTIO" if att else "FALTO",
                              "d":"" if att else random.choice(["Enfermedad","Viaje","Trabajo","Ocupación familiar","No informó"])})

# 8. ConsolidationCases (UUID pk)
for _ in range(20):
    stage=random.choice(["new","contacted","meeting","followup","won","closed"])
    conn.execute(text("""
        INSERT INTO consolidation_cases(id,persona_id,stage,status,source,last_contact_at,next_contact_at,created_at,updated_at)
        VALUES(:cid,:pid,:st,:sta,:src,:lc,:nc,:cr,:up)
    """),{"cid":str(uuid.uuid4()),"pid":str(uuid.uuid4()),"st":stage,
          "sta":"active" if stage not in ("won","closed") else "closed",
          "src":random.choice(["WEB_FORM","EVANGELISMO","ASISTENCIA_SERVICIO"]),
          "lc":rd(15),"nc":rd(0,5) if stage not in ("won","closed") else None,
          "cr":rd(60),"up":rd(7)})

# 9. Courses
cids=[]
for i,t in enumerate(["Fundamentos de la Fe","Vida en el Espíritu","Discipulado Avanzado","Liderazgo Cristiano","Matrimonio y Familia","Ministerio Práctico"],1):
    cid=conn.execute(text("INSERT INTO courses(code,title,description,modality,is_published,duration_hours,created_at) VALUES(:c,:t,:d,:m,1,:dur,:cr)"),
                    {"c":f"C{i:03d}","t":t,"d":"Formación ministerial","m":random.choice(["PRESENCIAL","VIRTUAL"]),
                     "dur":random.randint(10,40),"cr":rd(120)}).lastrowid
    cids.append(cid)

# 10. Enrollments
for uid in range(1,21):
    p=random.randint(0,100)
    conn.execute(text("INSERT OR IGNORE INTO enrollments(user_id,course_id,status,progress_percent,certificate_issued,created_at) VALUES(:u,:c,:s,:p,:cert,:cr)"),
                {"u":uid,"c":random.choice(cids),"s":"active" if p<100 else "completed","p":p,"cert":1 if p>=90 else 0,"cr":rd(90)})

# 11. Donations
for _ in range(30):
    conn.execute(text("INSERT INTO donations(persona_id,amount,donation_type,status,donor_name,donor_email,created_at) VALUES(:p,:a,:t,'completed',:n,:e,:c)"),
                {"p":random.choice(pids),"a":round(random.uniform(10000,500000),0),
                 "t":random.choice(["Diezmo","Ofrenda","Ofrenda","Donación","Especial"]),
                 "n":"Donante","e":f"donor{random.randint(1,100)}@email.com","c":rd(180)})

# 12. AgendaEvents
for _ in range(8):
    s=rd(0,30)
    conn.execute(text("INSERT INTO agenda_events(title,description,start_at,end_at,location,created_at) VALUES(:t,:d,:s,:e,:l,:c)"),
                {"t":random.choice(["Culto General","Estudio Bíblico","Reunión Líderes","Escuela Dominical","Ayuno y Oración","Taller Matrimonios"]),
                 "d":"Evento programado","s":s,"e":s+timedelta(hours=random.randint(1,3)),
                 "l":random.choice(["Salón Principal","Salón Juvenil","Auditorio"]),"c":rd(60)})

# 13. Projects + Tasks
for _ in range(4):
    pj=conn.execute(text("INSERT INTO projects(title,description,status,created_at,updated_at) VALUES(:t,:d,:s,:c,:c)"),
                   {"t":random.choice(["Remodelación","Campaña Evangelística","Escuela de Líderes","Ayuda Social"]),
                    "d":"Proyecto ministerial","s":random.choice(["active","active","active","completed"]),"c":rd(120)}).lastrowid
    for _ in range(5):
        conn.execute(text("INSERT INTO project_tasks(project_id,title,status,assignee_id,due_date,created_at,updated_at) VALUES(:p,:t,:s,:a,:d,:c,:c)"),
                    {"p":pj,"t":random.choice(["Diseñar plan","Reunir equipo","Comprar materiales","Coordinar horarios","Difundir evento"]),
                     "s":random.choice(["pending","in_progress","completed","completed"]),"a":random.randint(1,10),
                     "d":rd(0,20),"c":rd(60)})

# 14. RefreshTokens
conn.execute(text("INSERT OR IGNORE INTO refresh_tokens(user_id,token,revoked,expires_at,created_at) VALUES(1,'t1',0,:e,:c),(2,'t2',0,:e,:c)"),
            {"e":now+timedelta(days=30),"c":now})

conn.commit()
conn.close()

# Verify
from backend.core.database import engine as eng
c=eng.connect()
for t in ['personas','cell_groups','cell_group_members','cell_group_sessions','cell_group_attendance',
          'consolidation_cases','courses','enrollments','donations','agenda_events','projects','project_tasks',
          'users','refresh_tokens','evangelism_strategies']:
    n=c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
    print(f"  {t}: {n}")
c.close()
print("\n✅ All seed data complete!")
