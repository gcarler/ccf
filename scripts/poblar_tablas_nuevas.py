"""
Script: Poblar tablas nuevas del ecosistema de evangelismo.
Paso 2: Despues de crear_escenario_prueba.py (100 personas, grupos viejos, sesiones viejas).

Puebla:
- evangelism_strategies (nueva)
- cell_groups (nuevo)
- cell_group_members (nuevo)
- cell_group_sessions (nuevo)
- cell_group_attendance (nuevo)
- grupo_participantes (viejo - pendiente)
- asistencias (viejo - pendiente)
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from backend.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
now = datetime.now(timezone.utc)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# IDs de personas genericas: 1029-1128
PERSONA_IDS = list(range(1029, 1129))

with engine.connect() as conn:
    # ── VERIFICAR DATOS EXISTENTES ──
    log("Verificando datos existentes...")
    estrategia_vieja = conn.execute(
        text("SELECT id FROM estrategias_evangelismo WHERE id = 'casas-de-gloria'")
    ).fetchone()
    if not estrategia_vieja:
        log("ERROR: Estrategia 'casas-de-gloria' no existe. Ejecuta crear_escenario_prueba.py primero.")
        exit(1)
    log("  Estrategia OK: casas-de-gloria")

    grupos_viejos = conn.execute(
        text("SELECT id, codigo FROM grupos_evangelismo WHERE estrategia_id = 'casas-de-gloria' ORDER BY id")
    ).fetchall()
    grupos_viejos = grupos_viejos[-10:]  # Solo nuestros 10 grupos
    log(f"  {len(grupos_viejos)} grupos viejos encontrados")

    sesiones_viejas = conn.execute(
        text("SELECT id, grupo_id FROM sesiones_grupo WHERE grupo_id IN ({}) ORDER BY id".format(
            ','.join(str(g.id) for g in grupos_viejos)
        ))
    ).fetchall()
    log(f"  {len(sesiones_viejas)} sesiones viejas encontradas")

    # ── 1. EVANGELISM STRATEGIES ──
    log("\n1. Creando estrategia en evangelism_strategies...")
    existing = conn.execute(
        text("SELECT id FROM evangelism_strategies WHERE codigo = 'CDG-001'")
    ).fetchone()
    if not existing:
        conn.execute(
            text("""
                INSERT INTO evangelism_strategies (name, codigo, description, typology, recurrence,
                    sede_id, categoria_id, activa, status, created_at, updated_at)
                VALUES ('Casas de Gloria', 'CDG-001', 'Estrategia de Casas de Gloria - prueba 100 personas',
                    'relacional', 'SEMANAL', 1, 1, true, 'active', :ts, :ts)
            """),
            {'ts': now}
        )
        conn.commit()
        log("  Creada OK")
    else:
        log("  Ya existe")

    # Obtener el ID numerico de la nueva estrategia
    nueva_estrategia = conn.execute(
        text("SELECT id FROM evangelism_strategies WHERE codigo = 'CDG-001'")
    ).fetchone()
    strat_id = nueva_estrategia.id
    log(f"  Estrategia ID: {strat_id}")

    # ── 2. CELL GROUPS ──
    log("\n2. Creando grupos en cell_groups...")
    cell_groups_created = 0
    cell_group_map = {}  # group index → cell_group_id

    for i, gv in enumerate(grupos_viejos, 1):
        existing = conn.execute(
            text("SELECT id FROM cell_groups WHERE code = :cod"),
            {'cod': f'CG-{str(i).zfill(3)}'}
        ).fetchone()
        if not existing:
            # Elegir lideres de nuestras personas genericas
            leader_id = PERSONA_IDS[(i - 1) % 100]
            assistant_id = PERSONA_IDS[(i + 10) % 100]
            host_id = PERSONA_IDS[(i + 20) % 100]
            dias = ['Domingo','Lunes','Martes','Miercoles','Jueves','Viernes','Sabado']
            result = conn.execute(
                text("""
                    INSERT INTO cell_groups (code, name, zone, address, capacity,
                        day_of_week, start_time, status, sede_id,
                        evangelism_strategy_id,
                        leader_persona_id, assistant_persona_id, host_persona_id,
                        leader_name, members_count, created_at, updated_at)
                    VALUES (:cod, :nom, :zone, :addr, :cap,
                        :dia, '19:00', 'Activo', 1,
                        'casas-de-gloria',
                        :lid, :asid, :hid,
                        :lname, 10, :ts, :ts)
                    RETURNING id
                """),
                {
                    'cod': f'CG-{str(i).zfill(3)}',
                    'nom': f'Casa de Gloria {i}',
                    'zone': f'Zona {((i-1)//3)+1}',
                    'addr': f'Direccion Grupo {i}',
                    'cap': 15,
                    'dia': dias[i % 7],
                    'lid': leader_id,
                    'asid': assistant_id,
                    'hid': host_id,
                    'lname': f'Persona Generica {str(leader_id - 1028).zfill(3)}',
                    'ts': now
                }
            )
            new_id = result.fetchone()[0]
            cell_group_map[i] = new_id
            cell_groups_created += 1
        else:
            cell_group_map[i] = existing.id
    conn.commit()
    log(f"  {cell_groups_created} cell_groups creados, total: {len(cell_group_map)}")

    # ── 3. CELL GROUP MEMBERS ──
    log("\n3. Asignando miembros a cell_group_members...")
    created = 0
    roles_cycle = ['LIDER', 'COLIDER', 'ANFITRION', 'ASISTENTE', 'INVITADO']
    for i, pid in enumerate(PERSONA_IDS):
        cg_idx = (i // 10) + 1  # 10 personas por grupo
        if cg_idx not in cell_group_map:
            continue
        cg_id = cell_group_map[cg_idx]
        existing = conn.execute(
            text("SELECT id FROM cell_group_members WHERE cell_group_id = :cg AND persona_id = :pid"),
            {'cg': cg_id, 'pid': pid}
        ).fetchone()
        if not existing:
            role = roles_cycle[i % len(roles_cycle)]
            conn.execute(
                text("""
                    INSERT INTO cell_group_members (cell_group_id, persona_id, role, fecha_ingreso, activo)
                    VALUES (:cg, :pid, :role, :ts, true)
                """),
                {'cg': cg_id, 'pid': pid, 'role': role, 'ts': now}
            )
            created += 1
    conn.commit()
    log(f"  {created} miembros asignados a cell_groups")

    # ── 4. CELL GROUP SESSIONS ──
    log("\n4. Creando sesiones en cell_group_sessions...")
    created = 0
    for cg_idx, cg_id in cell_group_map.items():
        for w in range(4):
            ses_date = now - timedelta(weeks=3 - w)
            existing = conn.execute(
                text("SELECT id FROM cell_group_sessions WHERE cell_group_id = :cg AND session_date = :sd"),
                {'cg': cg_id, 'sd': ses_date.date()}
            ).fetchone()
            if not existing:
                conn.execute(
                    text("""
                        INSERT INTO cell_group_sessions
                            (cell_group_id, season_id, session_date, status, topic, offering_amount,
                             report_notes, created_at)
                        VALUES (:cg, 1, :sd, 'Realizada', :top, :off,
                            'Sesion reportada - prueba', :ts)
                    """),
                    {
                        'cg': cg_id,
                        'sd': ses_date,
                        'top': f'Sesion {w+1} - Grupo {cg_idx}',
                        'off': 15000 + (cg_idx * 1000),
                        'ts': now
                    }
                )
                created += 1
    conn.commit()
    log(f"  {created} sesiones creadas en cell_group_sessions")

    # Obtener los IDs de las sesiones nuevas
    cell_session_map = {}  # (cg_idx, week) → session_id
    for cg_idx, cg_id in cell_group_map.items():
        sesiones = conn.execute(
            text("""
                SELECT id, session_date FROM cell_group_sessions
                WHERE cell_group_id = :cg
                ORDER BY session_date ASC
            """),
            {'cg': cg_id}
        ).fetchall()
        for i, ses in enumerate(sesiones):
            cell_session_map[(cg_idx, i)] = ses.id

    # ── 5. CELL GROUP ATTENDANCE ──
    log("\n5. Registrando asistencias en cell_group_attendance...")
    created = 0
    for (cg_idx, week), session_id in cell_session_map.items():
        # 10 personas por grupo
        base_idx = (cg_idx - 1) * 10
        group_pids = PERSONA_IDS[base_idx:base_idx + 10]
        for pid in group_pids:
            existing = conn.execute(
                text("SELECT id FROM cell_group_attendance WHERE session_id = :sid AND persona_id = :pid"),
                {'sid': session_id, 'pid': pid}
            ).fetchone()
            if not existing:
                # Simular: 80% asiste, 15% falta, 5% excusa
                mod = hash(f"{session_id}-{pid}") % 100
                if mod < 80:
                    estado = 'ASISTIO'
                    attended = True
                    first_time = False
                elif mod < 95:
                    estado = 'FALTO'
                    attended = False
                    first_time = False
                else:
                    estado = 'EXCUSA'
                    attended = False
                    first_time = False

                conn.execute(
                    text("""
                        INSERT INTO cell_group_attendance
                            (session_id, persona_id, attended, status, estado,
                             es_primera_vez, requiere_seguimiento)
                        VALUES (:sid, :pid, :att, :st, :est,
                            false, false)
                    """),
                    {
                        'sid': session_id,
                        'pid': pid,
                        'att': attended,
                        'st': 'present' if attended else 'absent',
                        'est': estado,
                    }
                )
                created += 1
    conn.commit()
    log(f"  {created} registros de asistencia creados")

    # ── 6. GRUPO_PARTICIPANTES (tabla vieja) ──
    log("\n6. Asignando participantes a grupos viejos (grupo_participantes)...")
    created = 0
    for i, pid in enumerate(PERSONA_IDS):
        gv = grupos_viejos[i // 10]
        gv_id = gv.id
        existing = conn.execute(
            text("SELECT id FROM grupo_participantes WHERE grupo_id = :gid AND persona_id = :pid"),
            {'gid': gv_id, 'pid': pid}
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO grupo_participantes (grupo_id, persona_id, rol_base, fecha_ingreso, activo)
                    VALUES (:gid, :pid, 'asistente', :ts, true)
                """),
                {'gid': gv_id, 'pid': pid, 'ts': now}
            )
            created += 1
    conn.commit()
    log(f"  {created} participantes asignados a grupos viejos")

    # ── 7. ASISTENCIAS (tabla vieja) ──
    log("\n7. Registrando asistencias en tabla vieja (asistencias)...")
    created = 0
    for ses in sesiones_viejas:
        grupo_viejo = next(g for g in grupos_viejos if g.id == ses.grupo_id)
        grupo_idx = grupos_viejos.index(grupo_viejo)
        base_idx = grupo_idx * 10
        group_pids = PERSONA_IDS[base_idx:base_idx + 10]
        for pid in group_pids:
            existing = conn.execute(
                text("SELECT id FROM asistencias WHERE sesion_id = :sid AND persona_id = :pid"),
                {'sid': ses.id, 'pid': pid}
            ).fetchone()
            if not existing:
                mod = hash(f"old-{ses.id}-{pid}") % 100
                estado = 'ASISTIO' if mod < 80 else ('FALTO' if mod < 95 else 'EXCUSA')
                conn.execute(
                    text("""
                        INSERT INTO asistencias (sesion_id, persona_id, estado, es_primera_vez, requiere_seguimiento)
                        VALUES (:sid, :pid, :est, false, false)
                    """),
                    {'sid': ses.id, 'pid': pid, 'est': estado}
                )
                created += 1
    conn.commit()
    log(f"  {created} asistencias registradas en tabla vieja")

    # ── VERIFICACION ──
    log("\n=== VERIFICACION ===")
    checks = [
        ('evangelism_strategies', "SELECT COUNT(*) FROM evangelism_strategies"),
        ('cell_groups', "SELECT COUNT(*) FROM cell_groups"),
        ('cell_group_members', "SELECT COUNT(*) FROM cell_group_members"),
        ('cell_group_sessions', "SELECT COUNT(*) FROM cell_group_sessions"),
        ('cell_group_attendance', "SELECT COUNT(*) FROM cell_group_attendance"),
        ('grupo_participantes', "SELECT COUNT(*) FROM grupo_participantes WHERE persona_id >= 1029 AND persona_id <= 1128"),
        ('asistencias', "SELECT COUNT(*) FROM asistencias WHERE persona_id >= 1029 AND persona_id <= 1128"),
    ]
    for label, query in checks:
        count = conn.execute(text(query)).scalar()
        log(f"  {label}: {count}")

log("\nCOMPLETADO! Todas las tablas nuevas pobladas exitosamente.")
log("Ahora reinicia el backend: pm2 restart ccf-backend-staging")
