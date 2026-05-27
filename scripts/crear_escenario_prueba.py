"""
Script de prueba: Crea ecosistema completo de evangelismo con 100 personas genericas.
Usa SQL directo para evitar los mismatches entre modelos Python y esquema BD real.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from backend.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
now = datetime.now(timezone.utc)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

with engine.connect() as conn:
    # 0. Crear estrategia "Casas de Gloria" si no existe
    log("Creando estrategia 'Casas de Gloria'...")
    existing = conn.execute(
        text("SELECT id FROM estrategias_evangelismo WHERE id = 'casas-de-gloria'")
    ).fetchone()
    if not existing:
        conn.execute(
            text("""
                INSERT INTO estrategias_evangelismo (id, nombre, categoria_id, sede_id, frecuencia, activa)
                VALUES ('casas-de-gloria', 'Casas de Gloria', 1, 1, 'SEMANAL', true)
            """)
        )
        log("  Estrategia creada OK")
    else:
        log("  Estrategia ya existe")

    # 1. Crear 100 personas genericas (IDs 1029-1128)
    log("Creando 100 personas genericas...")
    next_id = 1029
    created = 0
    for i in range(1, 101):
        pid = next_id + i - 1
        # Check if already exists
        existing = conn.execute(
            text("SELECT id FROM personas WHERE id = :pid"),
            {'pid': pid}
        ).fetchone()
        if not existing:
            nombre = f"Persona Generica {str(i).zfill(3)}"
            conn.execute(
                text("""
                    INSERT INTO personas (id, first_name, last_name, church_role, estado_vital,
                                         spiritual_status, qr_token, created_at, updated_at)
                    VALUES (:id, :fn, :ln, 'Miembro', 'ACTIVO', 'Nuevo', :qr, :ts, :ts)
                """),
                {
                    'id': pid,
                    'fn': nombre,
                    'ln': '',
                    'qr': f'TST-{str(i).zfill(3)}',
                    'ts': now
                }
            )
            created += 1
    conn.commit()
    log(f"  Creadas {created} personas nuevas (IDs 1029-1128)")

    # 2. Asignar posiciones (member_positions usa member_id:integer)
    log("Asignando posiciones...")
    created = 0
    for i in range(1, 101):
        pid = 1029 + i - 1
        pos_id = ((i - 1) % 5) + 1  # 5 positions disponibles
        existing = conn.execute(
            text("SELECT id FROM member_positions WHERE member_id = :pid AND position_id = :pos"),
            {'pid': pid, 'pos': pos_id}
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO member_positions (member_id, position_id, start_date, is_active, created_at)
                    VALUES (:pid, :pos, :sd, true, :ts)
                """),
                {'pid': pid, 'pos': pos_id, 'sd': now, 'ts': now}
            )
            created += 1
    conn.commit()
    log(f"  {created} posiciones asignadas")

    # 3. Asignar ministerios (member_ministries usa member_id:integer)
    log("Asignando ministerios...")
    roles = ['Lider', 'Co-lider', 'Anfitrion', 'Asistente', 'Lector', 'Oracion', 'Logistica', 'Musica']
    created = 0
    for i in range(1, 101):
        pid = 1029 + i - 1
        mid = ((i - 1) % 8) + 1  # 8 ministerios
        role = roles[(i - 1) % 8]
        existing = conn.execute(
            text("SELECT id FROM member_ministries WHERE member_id = :pid AND ministry_id = :mid"),
            {'pid': pid, 'mid': mid}
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO member_ministries (member_id, ministry_id, role, start_date, is_active, created_at)
                    VALUES (:pid, :mid, :role, :sd, true, :ts)
                """),
                {'pid': pid, 'mid': mid, 'role': role, 'sd': now, 'ts': now}
            )
            created += 1
    conn.commit()
    log(f"  {created} ministerios asignados")

    # 4. Crear grupos directamente en grupos_evangelismo
    log("Creando 10 grupos en grupos_evangelismo...")
    created = 0
    for i in range(1, 11):
        existing = conn.execute(
            text("SELECT id FROM grupos_evangelismo WHERE codigo = :cod"),
            {'cod': f'CG-{str(i).zfill(3)}'}
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO grupos_evangelismo
                    (estrategia_id, sede_id, codigo, nombre, ubicacion, direccion, capacidad,
                     dia_reunion, hora_reunion, activo, created_at, updated_at)
                    VALUES ('casas-de-gloria', 1, :cod, :nom, :ubi, :dir, :cap,
                           :dia, :hora, true, :ts, :ts)
                """),
                {
                    'cod': f'CG-{str(i).zfill(3)}',
                    'nom': f'Casa de Gloria {i}',
                    'ubi': f'Zona {((i-1)//3)+1}',
                    'dir': f'Direccion Grupo {i}',
                    'cap': 15,
                    'dia': str((i % 7)),
                    'hora': '19:00',
                    'ts': now
                }
            )
            created += 1
    conn.commit()
    log(f"  {created} grupos creados")

    # 5. Crear sesiones para cada grupo
    log("Creando sesiones (4 por grupo)...")
    grupos = conn.execute(text("SELECT id FROM grupos_evangelismo ORDER BY id")).fetchall()
    grupos = grupos[-10:]  # ultimos 10 (nuestros nuevos)
    ses_created = 0
    for g in grupos:
        for w in range(4):
            ses_date = now - timedelta(weeks=3 - w)
            existing = conn.execute(
                text("SELECT id FROM sesiones_grupo WHERE grupo_id = :gid AND fecha_sesion::date = :sd"),
                {'gid': g.id, 'sd': ses_date.date()}
            ).fetchone()
            if not existing:
                conn.execute(
                    text("""
                        INSERT INTO sesiones_grupo (grupo_id, fecha_sesion, estado, tema_estudio, created_at)
                        VALUES (:gid, :sd, 'REALIZADA', :top, :ts)
                    """),
                    {'gid': g.id, 'sd': ses_date, 'top': f'Sesion {w+1} - Grupo {g.id}', 'ts': now}
                )
                ses_created += 1
    conn.commit()
    log(f"  {ses_created} sesiones creadas")

    # 6. Agregar participantes a grupos (grupo_participantes requiere persona_id:uuid - skip por mismatch de tipos)
    log("NOTA: grupo_participantes requiere persona_id:uuid (incompatible con integer IDs de personas)")
    log("  Saltando asignacion de participantes por mismatch de tipos BD")
    log("  Las personas existen en BD con IDs 1029-1128")
    log("  Tienen posiciones y ministerios asignados")

    # 7. Asistencias (saltamos porque asistencias.persona_id es uuid, incompatible con integer)
    log("NOTA: asistencias.persona_id es uuid (incompatible con integer IDs)")
    log("  Saltando registro de asistencias por mismatch de tipos BD")

    # 8. Communication logs (usa member_id:integer - compatible!)
    log("Creando communication_logs de ejemplo...")
    created = 0
    for i in range(1, 11):
        pid = 1029 + i - 1
        existing = conn.execute(
            text("SELECT id FROM communication_logs WHERE member_id = :pid AND channel = 'WhatsApp'"),
            {'pid': pid}
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO communication_logs (member_id, channel, content, outcome, leader_id, created_at, updated_at)
                    VALUES (:pid, 'WhatsApp', :msg, 'sent', 1, :ts, :ts)
                """),
                {'pid': pid, 'msg': f'Bienvenido al grupo Casa de Gloria!', 'ts': now}
            )
            created += 1
    conn.commit()
    log(f"  {created} communication_logs creados")

    conn.commit()

# VERIFICACION
log("\n=== VERIFICACION ===")
with engine.connect() as conn:
    tables = [
        ('personas (nuevas 1029-1128)',
         conn.execute(text("SELECT COUNT(*) FROM personas WHERE id >= 1029 AND id <= 1128")).scalar()),
        ('estrategias_evangelismo',
         conn.execute(text("SELECT COUNT(*) FROM estrategias_evangelismo")).scalar()),
        ('grupos_evangelismo (nuevos)',
         conn.execute(text("SELECT COUNT(*) FROM grupos_evangelismo WHERE estrategia_id = 'casas-de-gloria'")).scalar()),
        ('sesiones_grupo (nuevas)',
         conn.execute(text("SELECT COUNT(*) FROM sesiones_grupo WHERE grupo_id IN (SELECT id FROM grupos_evangelismo WHERE estrategia_id = 'casas-de-gloria')")).scalar()),
        ('member_positions (nuevas)',
         conn.execute(text("SELECT COUNT(*) FROM member_positions WHERE member_id >= 1029 AND member_id <= 1128")).scalar()),
        ('member_ministries (nuevas)',
         conn.execute(text("SELECT COUNT(*) FROM member_ministries WHERE member_id >= 1029 AND member_id <= 1128")).scalar()),
        ('communication_logs (nuevos)',
         conn.execute(text("SELECT COUNT(*) FROM communication_logs WHERE member_id >= 1029 AND member_id <= 1128")).scalar()),
    ]
    for label, count in tables:
        print(f"  {label}: {count}")

log("\nCOMPLETADO: Ecosistema de prueba creado exitosamente.")
log("Personas genericas IDs: 1029-1128")
log("Estrategia: Casas de Gloria (casas-de-gloria)")
log("Grupos: CG-001 a CG-010")
log("4 sesiones por grupo = 40 sesiones total")
log("Cada persona tiene 1 posicion y 1 ministerio")
