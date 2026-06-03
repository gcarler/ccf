#!/usr/bin/env python3
"""
Migración de datos del Google Sheets "bd_ccf_052026" a la base de datos ccf_db.
Inserta: sede, personas y auth_users.
"""
import uuid
import psycopg2
from datetime import date, datetime

# Mapeo de tipo asistente -> church_role
CHURCH_ROLE_MAP = {
    "Pastor General": "Pastor General",
    "Pastor": "Pastor",
    "Líder": "Líder",
    "Servidor": "Servidor",
    "Asistente": "Asistente",
    "Miembro Bautizado": "Miembro Bautizado",
    "Visitante": "Visitante",
}

# Datos de todas las personas desde el Google Sheets
personas_data = [
    # (id_type, id_number, first_name, second_name, last_name, second_last_name,
    #  marital_status, birth_country, phone, mobile_phone, email,
    #  address, housing_type, education_level, education_status,
    #  profession, economic_sector, blood_type, medical_notes, optional_info,
    #  responsible_adult_name, responsible_adult_contact, guardian_name, guardian_contact,
    #  birthday, sex, last_group_attendance, last_meeting_attendance,
    #  membership_type, attendance_type, group_name, campus, church_join_date,
    #  church_role)

    (None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None),  # placeholder
]

conn = psycopg2.connect(
    host="localhost", dbname="ccf_db",
    user="ccf_admin", password="ccf_password_secret_123"
)
cur = conn.cursor()

# 1. Crear sede principal
sede_id = uuid.uuid4()
cur.execute("""
    INSERT INTO sedes (id, nombre, ciudad, es_activa)
    VALUES (%s, 'Sede Principal', 'Sin Información', true)
""", (str(sede_id),))
print(f"✅ Sede creada: {sede_id}")

# 2. Insertar cada persona
print("\n📋 Insertando personas...")
insert_sql = """
    INSERT INTO personas (
        id, sede_id, first_name, last_name, second_name, second_last_name,
        email, phone, mobile_phone, landline_phone, other_phone,
        id_type, id_number, marital_status, birth_country,
        address, housing_type, education_level, education_status,
        profession, economic_sector, blood_type, medical_notes, optional_info,
        responsible_adult_name, responsible_adult_contact,
        guardian_name, guardian_contact,
        birthday, sex, last_group_attendance, last_meeting_attendance,
        membership_type, attendance_type, group_name, campus, church_join_date,
        church_role, spiritual_status, estado_vital, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    )
"""

def s(value):
    """Convert 'Sin Información' and similar to None"""
    if value is None:
        return None
    v = str(value).strip()
    if v in ('', 'Sin Información', 'Sin info', 'Sin información', 'No Aplica', 'Sin Fecha', 'Sin Detalle', 'Sin dado alta', 'Sin dado baja', 'Sin fecha alta', 'Sin fecha baja', '-'):
        return None
    return v

def parse_date(value):
    v = s(value)
    if v is None:
        return None
    try:
        return date.fromisoformat(v)
    except:
        return None

def parse_sex(value):
    v = s(value)
    if v is None:
        return None
    if v.lower() in ('masculino', 'm'):
        return 'M'
    if v.lower() in ('femenino', 'f'):
        return 'F'
    return None

def map_church_role(tipo_asistente):
    return CHURCH_ROLE_MAP.get(tipo_asistente, tipo_asistente) if tipo_asistente else None

# ============================================================
# DATOS COMPLETOS (76 personas del Sheets)
# ============================================================
# Formato: [id_type, id_number, first_name, second_name, last_name, second_last_name,
#           marital_status, birth_country, phone, mobile_phone, email,
#           address, housing_type, education_level, education_status,
#           profession, economic_sector, blood_type, medical_notes, optional_info,
#           responsible_adult_name, responsible_adult_contact,
#           guardian_name, guardian_contact,
#           birthday, sex, last_group_attendance, last_meeting_attendance,
#           membership_type, attendance_type, group_name, campus, church_join_date,
#           church_role]

P = [
    # 1 - Lucas Manuel Barrio Quintero
    ["Cédula De Ciudadanía", "8854959", "Lucas", "Manuel", "Barrio", "Quintero",
     None, None, None, "3022468575", "noleescribi@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1980-10-05", "Masculino", None, "2016-01-01",
     "Servicio", "Visitante", None, None, None, "Visitante"],
    # 2 - Histar Ariza Herrera
    ["Cédula De Ciudadanía", "45593640", "Histar", None, "Ariza", "Herrera",
     "Casado Por Ambas", "Colombia", "6425126", "3017481346", "arizahistar@gmail.com",
     "Transversal 52#22-108 Edificio Bios Apto 2b", "Familiar", "Especialización", "Finalizado",
     "Bacteriólogo", "Religioso", "O+", None, "Es La Pastora Principal Y Representante Legal",
     None, None, None, None,
     "1978-11-26", "Femenino", None, "2026-05-17",
     "Servicio", "Pastor General", None, None, None, "Pastor General"],
    # 3 - Katherine Rojas Bohorquez
    ["Cédula De Ciudadanía", "1043975240", "Katherine", None, "Rojas", "Bohorquez",
     "Soltero", "Colombia", None, "3506145075", "katherine3008458623@gmail.com",
     "Rep De Chile Mza 19 Lote 19", "Propia", "Profesional Universitario", "En Curso",
     "Ingeniería De Sistemas De Información", "Tic", "O+", None, None,
     None, None, None, None,
     "2007-10-02", "Femenino", "2026-05-03", "2026-05-17",
     "Servicio", "Servidor", "CDG8", None, None, "Servidor"],
    # 4 - Elvia Julia Angulo Diaz
    ["Cédula De Ciudadanía", "1128044246", "Elvia", "Julia", "Angulo", "Diaz",
     "Casado Por Ambas", "Colombia", None, "3014756072", "elviaangulodiaz@gmail.com",
     "Urb El Gallo Transversal 52d #34-24 Edificio El Gallo 2 Apto 301", "Propia", "Profesional Universitario", "Finalizado",
     "Administrador", "Público", "O+", None, None,
     None, None, None, None,
     "1985-11-22", "Femenino", None, "2026-05-17",
     "Servicio", "Pastor", None, None, None, "Pastor"],
    # 5 - Pedro Manuel Mercado Carbal
    ["Cédula De Ciudadanía", "73213515", "Pedro", "Manuel", "Mercado", "Carbal",
     "Divorciado", "Colombia", None, "3166352490", "elpello@gmail.com",
     "Los Cerros Mz 11 Lte 786", "Familiar", "Pre-escolar", "No Concluido",
     None, None, "A+", None, None,
     None, None, None, None,
     "1971-04-15", "Masculino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 6 - Nehemias Morales Hernandez
    ["Cédula De Ciudadanía", "1047380471", "Nehemias", None, "Morales", "Hernandez",
     "Casado Por Ambas", "Colombia", None, "573005749415", "asesor.emprendimiento7@gmail.com",
     "Altos De Nuevo Bosque Mz F Lote 14", "Familiar", "Profesional Universitario", "Finalizado",
     "Administrador", "Administración", "O+", None, None,
     None, None, None, None,
     "1986-11-07", "Masculino", None, None,
     "Servicio", "Pastor", "CDG17", None, None, "Pastor"],
    # 7 - Luzkarine Palencia Ariza
    ["Cédula De Ciudadanía", "1047440669", "Luzkarine", None, "Palencia", "Ariza",
     "Casado Por Ambas", "Colombia", None, "3174882609", "luz.palencia@hotmail.com",
     "La Carolina Mza J Casa 58 2do Piso", "Familiar", "Especialización", "Finalizado",
     "Abogado", "Público", "A+", None, None,
     None, None, None, None,
     "1991-09-02", "Femenino", None, None,
     "Servicio", "Líder", None, None, None, "Líder"],
    # 8 - Solangi Marcelo Caro
    ["Cédula De Ciudadanía", "1127614645", "Solangi", None, "Marcelo", "Caro",
     "Soltero", "Venezuela", None, "573015114139", "solangimar2112@gmail.com",
     "Altos De San Isidro Mza F Lte17", "Familiar", "Técnico", "Finalizado",
     "Maestro", "Educativo", "O+", "Alérgica A Los Mariscos, Maní Y La Piña. Tpi", None,
     None, None, None, None,
     "2003-05-12", "Femenino", None, None,
     "Detonación De Fe", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 9 - Marilyn Cogollo
    ["Cédula De Ciudadanía", "45466829", "Marilyn", None, "Cogollo", None,
     None, None, None, "3186553542", "fdhrghbdfridyhr@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1965-09-19", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 10 - Clara Luz Sierra Palencia
    ["Cédula De Ciudadanía", "45765866", "Clara", "Luz", "Sierra", "Palencia",
     "Casado Por Ambas", "Colombia", None, "3161435006", "sierrapaleciaclaraluz@gmail.com",
     "Bosquecito Transversal 50 # 23 B16", "Familiar", "Enseñanza Básica - Primaria", "Finalizado",
     None, None, "O+", None, None,
     None, None, None, None,
     "1974-04-04", "Femenino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 11 - Aleyda Gomez
    ["Cédula De Ciudadanía", "21325381", "Aleyda", None, "Gomez", None,
     None, None, None, "3116608861", "ajsuiwwj@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1980-09-01", "Femenino", None, None,
     "Detonación De Fe", "Visitante", None, None, None, "Visitante"],
    # 12 - Giomar Gomez Mercado
    ["Cédula De Ciudadanía", "45486264", "Giomar", None, "Gomez", "Mercado",
     "Casado Por Ambas", "Colombia", None, "3223891602", "giomar6925@hotmail.com",
     "Altos De San Idiro Mz B Lote 6", "Propia", "Técnico", "Finalizado",
     "Maestro", "Educativo", "O+", None, None,
     None, None, None, None,
     "1969-03-25", "Femenino", None, None,
     "Casa De Gloria", "Servidor", None, None, None, "Servidor"],
    # 13 - Estefanny Torres
    [None, None, "Estefanny", None, "Torres", None,
     None, None, None, None, "625@correopordefecto.com",
     None, None, None, None, None, None, None, None, None,
     "Jorge Torre", None, None, None,
     "2009-09-17", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 14 - Abimelec Meza Ariza
    [None, None, "Abimelec", None, "Meza", "Ariza",
     None, None, None, None, "13@correopordefecto.com",
     None, None, "Bachillerato", "En Curso",
     None, None, "A+", "Ninguna", None,
     "Luis Ricardo Meza Gutierrez", "3005775435", None, None,
     "2009-10-23", "Masculino", "2025-02-04", "2026-05-17",
     "Servicio", "Servidor", "CDG1", None, None, "Servidor"],
    # 15 - Laura Stefany Anchique Pianeta
    ["Cédula De Ciudadanía", "1143412823", "Laura", "Stefany", "Anchique", "Pianeta",
     "Soltero", "Colombia", None, "3142774947", "anchike85@gmail.com",
     "Chile Mza 67 Lote 19", "Familiar", "Tecnólogo", "Finalizado",
     "Profesional En Seguridad Y Salud En El Trabajo", "Servicios", "O+", None, "Cdg15",
     None, None, None, None,
     "1999-04-11", "Femenino", None, None,
     "Casa De Gloria", "Asistente", None, None, None, "Asistente"],
    # 16 - Harold Morales Cogollo
    ["Cédula De Ciudadanía", "1143397124", "Harold", None, "Morales", "Cogollo",
     "Soltero", "Colombia", None, "573153596616", "haroldmoralescogollo@gmail.com",
     "El Carmelo Mz E Lote 5", "Propia", "Profesional Universitario", "En Curso",
     "Matemático", "Comercial", "Ab+", None, None,
     None, None, None, None,
     "1997-01-05", "Masculino", None, None,
     "Servicio", "Líder", None, None, None, "Líder"],
    # 17 - Kristell Polo Morales
    ["Cédula De Ciudadanía", "1047483067", "Kristell", None, "Polo", "Morales",
     None, None, None, "3014629836", "ajggdj@gmail.com",
     None, None, None, None, None, None, "B+", None, None,
     None, None, None, None,
     "1995-08-01", "Femenino", None, None,
     "Casa De Gloria", "Asistente", None, None, None, "Asistente"],
    # 18 - Ariel Gomez Sosa
    ["Cédula De Ciudadanía", "73101181", "Ariel", None, "Gomez", "Sosa",
     "Viudo", "Colombia", None, "3001866273", "arielgomezsosa051@gmail.com",
     "Piedra Bolivar", "Propia", "Técnico", None,
     "Soldado", None, "O+", None, None,
     None, None, None, None,
     "1961-01-14", "Masculino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 19 - Asistente Principal (sistema)
    [None, None, "Asistente", None, "Principal", None,
     None, None, None, None, "asistenteprincipal2@redil.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1970-01-01", "Masculino", None, None,
     "Casa De Gloria", "Pastor General", None, None, None, "Pastor General"],
    # 20 - Zara Abdala
    [None, None, "Zara", None, "Abdala", None,
     None, None, None, None, "657@correopordefecto.com",
     None, None, None, None, None, None, None, None, None,
     "Aleyda Gómez", "3116608861", None, None,
     "2010-12-29", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 21 - Asistente Principal (sistema)
    [None, None, "Asistente", None, "Principal", None,
     None, None, None, None, "asistenteprincipal@redil.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1970-01-01", "Femenino", None, None,
     "Casa De Gloria", "Pastor General", None, None, None, "Pastor General"],
    # 22 - Marilyn Morales Cogollo
    ["Cédula De Ciudadanía", "1143387304", "Marilyn", None, "Morales", "Cogollo",
     None, None, None, "3016351489", "hildssljkgrww@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1995-09-16", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 23 - Dina Ceballos Avila
    ["Cédula De Ciudadanía", "45542406", "Dina", None, "Ceballos", "Avila",
     None, None, None, "3002335252", "jkmfhtfh@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1982-02-02", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 24 - Gissell Romero
    [None, None, "Gissell", None, "Romero", None,
     None, None, None, None, "561@correopordefecto.com",
     None, None, None, None, None, None, None, None, None,
     "Roberto Romero", None, None, None,
     "2013-03-26", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 25 - Luis Miguel Contreras
    ["Cédula De Ciudadanía", "1043647585", "Luis", None, "Miguel", "Contreras",
     None, None, None, "3214197231", "dinatrijilloestrella@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "2005-07-24", "Masculino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 26 - Esteban Ariza Gomez
    ["Cédula De Ciudadanía", "1043971862", "Esteban", None, "Ariza", "Gomez",
     "Soltero", "Colombia", None, "3244581021", "estebanariza64@gmail.com",
     "Edificio Vida Transversal 52", "Propia", "Profesional Universitario", "En Curso",
     "Medico", "Sanitario", "O+", None, None,
     None, None, None, None,
     "2006-07-17", "Masculino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 27 - Daniela Patricia Pianeta Torres
    ["Cédula De Ciudadanía", "1043964491", "Daniela", "Patricia", "Pianeta", "Torres",
     "Soltero", "Colombia", None, "3059322573", "danielapianeta428@gmail.com",
     "Chile Sector La Conquista Mz F Lt 4", "Familiar", "Bachillerato", "En Curso",
     None, None, "O+", None, None,
     None, None, None, None,
     "2004-12-09", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 28 - Wilson David Romero Wilches
    ["Cédula De Ciudadanía", "1002245242", "Wilson", "David", "Romero", "Wilches",
     "Soltero", "Colombia", None, "3214207585", "wilsonromero321@gmail.com",
     "Altos Del Nuevo Bosque Mza F Lte 10", "Familiar", "Profesional Universitario", "En Curso",
     "Ingeniero", None, "A+", None, None,
     None, None, None, None,
     "2002-05-20", "Masculino", None, None,
     "Servicio", "Servidor", "CDG1", None, None, "Servidor"],
    # 29 - María José Cueto Canoles
    ["Cédula De Ciudadanía", "1235039395", "María", "José", "Cueto", "Canoles",
     "Casado Por Ambas", "Colombia", None, "573006305320", "mariacueto38@gmail.com",
     "Bosquesito Tranv51 23+36", "Arriendo O Alquiler", "Profesional Universitario", "Finalizado",
     "Licenciado", "Educativo", "O+", None, None,
     None, None, None, None,
     "1997-12-25", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 30 - Efren Martinez Negrete
    ["Cédula De Ciudadanía", "1128048356", "Efren", None, "Martinez", "Negrete",
     "Unión Libre", "Colombia", None, "3116558039", "notienecorreo1@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1984-12-01", "Masculino", None, None,
     "Detonación De Fe", "Visitante", None, None, None, "Visitante"],
    # 31 - Nohemy De Diego Jiménez
    ["Cédula De Ciudadanía", "45491992", "Nohemy", None, "De Diego", "Jiménez",
     "Viudo", "Colombia", "3158865572", None, "nohemy.92@hotmail.com",
     "Chile Mza 37 Lte 8", "Arriendo O Alquiler", "Profesional Universitario", "Finalizado",
     "Administrador", "Construcción", "B+", None, None,
     None, None, None, None,
     "1970-04-18", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 32 - Angela María De Diego Jiménez
    ["Cédula De Ciudadanía", "45477100", "Angela", "María", "De Diego", "Jiménez",
     "Casado Por Ambas", "Colombia", None, "3156502790", "angela.dediego68@gmail.com",
     "Urbanización Horizonte Mza 2 Lte 101 3ra Etapa", "Propia", "Técnico", "Finalizado",
     "Secretario", "Servicios", "Ab+", None, None,
     None, None, None, None,
     "1968-02-11", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 33 - Andrés Felipe Chico Martinez
    [None, None, "Andrés", "Felipe", "Chico", "Martinez",
     None, None, None, None, "527@correopordefecto.com",
     None, None, "Bachillerato", "En Curso",
     None, None, "A+", None, None,
     "Luz Nelly Chico Hernandez", "3011514225", None, None,
     "2010-08-24", "Masculino", None, None,
     "Servicio", "Asistente", None, None, None, "Asistente"],
    # 34 - Lady Diana Wilches Alfaro
    ["Cédula De Ciudadanía", "1001975062", "Lady", "Diana", "Wilches", "Alfaro",
     "Soltero", "Colombia", None, "3103884769", "ladywilches17@gmail.com",
     "Bicentenario Mz 42 Lt 32", "Familiar", "Licenciatura", "Finalizado",
     "Profesor", "Educativo", "O+", None, None,
     None, None, None, None,
     "2000-06-17", "Femenino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 35 - Joiner David Suárez Ayala
    [None, None, "Joiner", "David", "Suárez", "Ayala",
     None, None, None, None, "662@correopordefecto.com",
     None, None, None, None, None, None, None, None, None,
     "Leonalda", None, None, None,
     "2008-08-17", "Masculino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 36 - Luisa Fernanda Gonzáles Blanco
    ["Cédula De Ciudadanía", "1001979670", "Luisa", "Fernanda", "Gonzáles", "Blanco",
     "Soltero", "Colombia", None, "3242802312", "luisagonzalesblanco@gmail.com",
     "Altos De San Isidro Diag 23 #51-05", "Propia", "Profesional Universitario", "En Curso",
     None, None, "A+", None, None,
     None, None, None, None,
     "2003-10-25", "Femenino", None, None,
     "Servicio", "Asistente", None, None, None, "Asistente"],
    # 37 - Eric Baza Epalza
    ["Cédula De Ciudadanía", "9262699", "Eric", None, "Baza", "Epalza",
     "Casado Por Ambas", "Colombia", None, "3216753781", "erbaep@gmail.com",
     "Chile Sect La Conquista Mza H Lte 24", "Propia", "Bachillerato", "Finalizado",
     None, "Comercial", "O+", None, None,
     None, None, None, None,
     "1956-10-27", "Masculino", None, None,
     "Servicio", "Asistente", "C.G. 15", None, None, "Asistente"],
    # 38 - Jesus David Cueto Canoles
    ["Cédula De Ciudadanía", "1047469046", "Jesus", "David", "Cueto", "Canoles",
     "Soltero", "Colombia", None, "3156909191", "jedacu19@gmail.com",
     "Bosquecito Trv 51 #22-33", "Arriendo O Alquiler", "Profesional Universitario", "Finalizado",
     "Economista", "Financiero", "O+", None, None,
     None, None, None, None,
     "1994-10-11", "Masculino", None, None,
     "Servicio", "Servidor", "CDG17", None, None, "Servidor"],
    # 39 - Daniela Shekina Julio Gonzalez
    [None, None, "Daniela", "Shekina", "Julio", "Gonzalez",
     None, None, None, None, "789@correopordefecto.com",
     None, None, "Enseñanza Básica - Primaria", "En Curso",
     None, None, "O+", None, None,
     "Nelcy Cecilia Gonzalez Monrroy", "3042440568", None, None,
     "2015-06-04", "Femenino", None, None,
     "Servicio", "Visitante", None, None, None, "Visitante"],
    # 40 - Jenifer Paternina Mercado
    ["Cédula De Ciudadanía", "143326632", "Jenifer", None, "Paternina", "Mercado",
     None, None, None, "3223601481", "notieneporthe@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1988-07-19", "Femenino", None, None,
     "Servicio", "Visitante", None, None, None, "Visitante"],
    # 41 - Elias Sangregorio Montes
    ["Cédula De Ciudadanía", "1143401680", "Elias", None, "Sangregorio", "Montes",
     "Casado Por La Iglesia", "Colombia", None, "3154614589", "elibman3@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1997-06-14", "Masculino", None, None,
     "Casa De Gloria", "Servidor", None, None, None, "Servidor"],
    # 42 - Ana María González Blanco
    ["Cédula De Ciudadanía", "1001973658", "Ana", "Maria", "González", "Blanco",
     "Soltero", "Colombia", None, "3001674962", "anag63454@gmail.com",
     "Altos De San Isidro Diagonal 23", "Propia", "Profesional Universitario", None,
     "Profesor", None, "A+", None, None,
     None, None, None, None,
     "2001-08-26", "Femenino", None, None,
     "Casa De Gloria", "Asistente", None, None, None, "Asistente"],
    # 43 - Ronald Samuel Hernandez Rondón
    ["Cédula De Ciudadanía", "1066350998", "Ronald", "Samuel", "Hernandez", "Rondón",
     "Soltero", "Colombia", "3005583848", None, "rhronaldsamuel@gmail.com",
     "Altos Del Nuevo Bosque Mz F Lt 10 Piso 2", "Familiar", "Profesional Universitario", "En Curso",
     "Ingeniero", None, None, None, None,
     None, None, None, None,
     "2008-03-21", "Masculino", None, None,
     "Servicio", "Asistente", "CDG1", None, None, "Asistente"],
    # 44 - Breylis Tatiana Baena Fontalvo
    ["Cédula De Ciudadanía", "1002247651", "Breylis", "Tatiana", "Baena", "Fontalvo",
     "Soltero", "Colombia", "000000", "3187930568", "bbaenafontalvo@gmail.com",
     None, None, "Profesional Universitario", "Finalizado",
     "Comunicación Social", "Tic", "O+", None, None,
     None, None, None, None,
     "2000-10-13", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 45 - Melvin Jose Arrieta Pautt
    ["Cédula De Ciudadanía", "1047519100", "Melvin", "Jose", "Arrieta", "Pautt",
     "Casado Por Ambas", "Venezuela", None, "3244213304", "arrietapauttmelvinjose@gmail.com",
     "Altos De San Isidro", "Arriendo O Alquiler", "Enseñanza Media - Secundaria", "Finalizado",
     None, None, "O+", None, None,
     None, None, None, None,
     "1982-05-10", "Masculino", None, None,
     "Detonación De Fe", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 46 - Alicia Esther Romero Torres
    ["Cédula De Ciudadanía", "33149941", "Alicia", "Esther", "Romero", "Torres",
     "Viudo", "Colombia", "6056015326", None, "alpiro1001@hotmail.com",
     "Chile Mza 67 Lte 19", "Propia", "Enseñanza Básica - Primaria", None,
     None, None, "A+", None, None,
     None, None, None, None,
     "1951-04-05", "Femenino", None, None,
     "Servicio", "Miembro Bautizado", "C.G. 15", None, None, "Miembro Bautizado"],
    # 47 - Edelma Rodriguez
    ["Cédula De Ciudadanía", "22792343", "Edelma", None, "Rodriguez", None,
     None, "Colombia", None, "3178181976", "notiene15@gmail.com",
     None, None, None, None, None, None, "O+", None, None,
     None, None, None, None,
     "1957-10-31", "Femenino", None, None,
     "Detonación De Fe", "Servidor", None, None, None, "Servidor"],
    # 48 - Dayana Michel Rincón Noriega
    ["Cédula De Ciudadanía", "1085171508", "Dayana", "Michel", "Rincón", "Noriega",
     "Soltero", "Colombia", None, "573215547230", "darinco1408@gmail.com",
     "Chile Sector La Conquista", "Familiar", "Profesional Universitario", "Finalizado",
     "Educador", None, "A+", None, None,
     None, None, None, None,
     "1999-08-14", "Femenino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 49 - Nataly Cardenas
    ["Cédula De Ciudadanía", "1143398518", "Nataly", None, "Cardenas", None,
     None, None, None, "3016569092", "blhoaiksiis@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1996-12-30", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 50 - Ledys Maria Martinez Montero
    ["Cédula De Ciudadanía", "32662398", "Ledys", "Maria", "Martinez", "Montero",
     "Casado Por Ambas", "Colombia", None, "3042354152", "notienecorreo@gmail.com",
     "Barrio Chile Sect La Conquista Mz H Lt24", "Familiar", "Enseñanza Básica - Primaria", "No Concluido",
     None, None, "O+", None, None,
     None, None, None, None,
     "1958-11-26", "Femenino", None, None,
     "Servicio", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 51 - Sebastian Andres Bohorquez Murcia
    [None, None, "Sebastian", "Andres", "Bohorquez", "Murcia",
     None, None, None, None, "517@correopordefecto.com",
     None, None, "Bachillerato", "En Curso",
     None, None, None, None, None,
     "Zheris Murcia", "3332604989", None, None,
     "2009-10-01", "Masculino", None, None,
     "Casa De Gloria", "Asistente", None, None, None, "Asistente"],
    # 52 - Yessi Atencio
    ["Cédula De Ciudadanía", "1002191476", "Yessi", None, "Atencio", None,
     None, None, None, "3022097008", "notiene2170727@gmail.com",
     None, None, None, None, None, None, "O+", None, None,
     None, None, None, None,
     "2000-05-17", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 53 - Miguel Angel Barreto Morales
    ["Cédula De Ciudadanía", "1043973949", "Miguel", "Angel", "Barreto", "Morales",
     None, None, None, "3117052945", "miguelbarreto554@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     "2004-09-25", "Masculino", None, None,
     "Casa De Gloria", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 54 - Claudia Ramos Castillo
    ["Cédula De Ciudadanía", "1007154449", "Claudia", None, "Ramos", "Castillo",
     None, None, None, "3116320041", "claudiaramoscastillo1989@gmail.com",
     None, None, None, None, None, None, "O+", None, None,
     None, None, None, None,
     "1993-04-28", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 55 - Liliana Franco
    ["Cédula De Ciudadanía", "33101792", "Liliana", None, "Franco", None,
     None, None, None, "3188396972", "notiene2507@gmai.com",
     None, None, None, None, None, None, "O+", None, None,
     None, None, None, None,
     "1979-05-10", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 56 - Ana Susana Cruz De Gaitan
    ["Cédula De Ciudadanía", "413747004", "Ana", "Susana", "Cruz", "De Gaitan",
     "Casado Por La Iglesia", "Colombia", None, "3107728944", "susanacruz.300341@gmail.com",
     "Invacion Bosquesito", "Propia", "Enseñanza Básica - Primaria", "No Concluido",
     None, None, "O+", "No Manifiesta", "Paso Por La Iglesia, Entro, Le Gusto Y Decidio Congregarse Aqui",
     None, None, None, None,
     "1941-03-30", "Femenino", None, None,
     "Detonación De Fe", "Asistente", None, None, None, "Asistente"],
    # 57 - Ibeth Maria De La Rosa Luna
    ["Cédula De Ciudadanía", "64517626", "Ibeth", "Maria", "De La Rosa", "Luna",
     "Casado Por La Iglesia", "Colombia", None, "3246511056", "ivethmariadelarosaluna@gmail.com",
     "Altos Del Nuevo Bosque Mz F Lote 7 A", "Propia", "Enseñanza Media - Secundaria", "No Concluido",
     None, None, "O+", None, None,
     None, None, None, None,
     "1964-11-13", "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 58 - Fernando Daniel Ascencio Cadena
    ["Cédula De Ciudadanía", "3836931", "Fernando", "Daniel", "Ascencio", "Cadena",
     "Casado Por Ambas", "Colombia", None, "3122619952", "fercho120939@gmail.com",
     "La Carolina Mza D Lte 44 Piso 2", "Propia", "Maestria", "Finalizado",
     "Educador", "Educativo", "O+", None, None,
     None, None, None, None,
     "1981-10-17", "Masculino", None, None,
     "Servicio", "Pastor", None, None, None, "Pastor"],
    # 59 - Tayna Luz Hoyos Avila
    ["Cédula De Ciudadanía", "467879889", "Tayna", "Luz", "Hoyos", "Avila",
     None, None, None, "3009473538", "ajsjagdgj@gmail.com",
     None, None, None, None, None, None, "B+", None, None,
     None, None, None, None,
     "1980-02-28", "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 60 - William Gonzalez Martínez
    ["Cédula De Ciudadanía", "91222201", "William", None, "Gonzalez", "Martínez",
     None, None, None, "3182623390", "noselopedi123@gmail.com",
     "Conjunto Residencial Prados De San Fernando Bloque 8 Apt. 102", None, None, None, None, None, None, None, None,
     None, None, None, None,
     "1961-10-18", "Masculino", None, None,
     "Servicio", "Asistente", None, None, None, "Asistente"],
    # 61 - Brayan Israel Morillo Blanco
    [None, None, "Brayan", "Israel", "Morillo", "Blanco",
     None, None, None, None, "70@correopordefecto.com",
     None, None, "Bachillerato", "En Curso",
     None, None, "O+", None, None,
     None, None, None, None,
     "2007-08-23", "Masculino", None, None,
     "Servicio", "Servidor", "CDG8", None, None, "Servidor"],
    # 62 - Joel David Gonzales Rodriguez
    [None, None, "Joel", "David", "Gonzales", "Rodriguez",
     None, None, None, None, "jg4939100@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Masculino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 63 - Katia Elena Gomez Angulo
    [None, None, "Katia", "Elena", "Gomez", "Angulo",
     None, None, None, None, "katiagome@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, None, None, None,
     "Servicio", "Asistente", None, None, None, "Asistente"],
    # 64 - Yenile Noguera
    [None, None, "Yenile", None, "Noguera", None,
     None, None, None, None, "yenilenoguera@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, None, None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 65 - Juan David Rodríguez De La Rosa
    [None, None, "Juan", "David", "Rodríguez", "De La Rosa",
     None, None, None, None, "juandavid182020@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Masculino", None, None,
     "Casa De Gloria", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 66 - Liwis Rojano Florez
    [None, None, "Liwis", None, "Rojano", "Florez",
     None, None, None, None, "liwys84@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, None, None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 67 - Andrea Carolina Macea Sierra
    [None, None, "Andrea", "Carolina", "Macea", "Sierra",
     None, None, None, None, "andremaceas@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Femenino", None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 68 - Danna Sofia Jimenez Rojano
    [None, None, "Danna", "Sofia", "Jimenez", "Rojano",
     None, None, None, None, "169@correopordefecto.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, None, None, None,
     "Servicio", "Servidor", None, None, None, "Servidor"],
    # 69 - Norida Velaides Gulloso
    [None, None, "Norida", None, "Velaides", "Gulloso",
     None, None, None, None, "noridavelaidesgulloso@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Femenino", None, None,
     "Casa De Gloria", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 70 - Livis Velaides Gulluso
    [None, None, "Livis", None, "Velaides", "Gulluso",
     None, None, None, None, "livis2023@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, None, None, None,
     "Casa De Gloria", "Miembro Bautizado", None, None, None, "Miembro Bautizado"],
    # 71 - Yaritza Gaspar
    [None, None, "Yaritza", None, "Gaspar", None,
     None, None, None, None, "yaritzagaspar123@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 72 - Dolores Rodríguez Crismatt
    [None, None, "Dolores", None, "Rodríguez", "Crismatt",
     None, None, None, None, "dolycris@hotmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Femenino", None, None,
     "Casa De Gloria", "Servidor", None, None, None, "Servidor"],
    # 73 - Nuris Diaz
    [None, None, "Nuris", None, "Diaz", None,
     None, None, None, None, "esposadejeanamigodeedgar@gmail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Femenino", None, None,
     "Casa De Gloria", "Visitante", None, None, None, "Visitante"],
    # 74 - Jaime De Jesús Perea García
    [None, None, "Jaime", "De Jesús", "Perea", "García",
     None, None, None, None, "jaimepereagarciajaimepereagarcia@homail.com",
     None, None, None, None, None, None, None, None, None,
     None, None, None, None,
     None, "Masculino", None, None,
     "Casa De Gloria", None, None, None, None, None],
]

now = datetime.now()
count = 0
errores = []

for i, p in enumerate(P):
    try:
        pid = uuid.uuid4()
        values = (
            str(pid),
            str(sede_id),  # sede_id as string
            s(p[2]),   # first_name
            s(p[4]),   # last_name
            s(p[3]),   # second_name
            s(p[5]),   # second_last_name
            s(p[10]),  # email
            None,      # phone (deprecated)
            s(p[9]),   # mobile_phone
            s(p[8]),   # landline_phone
            None,      # other_phone
            s(p[0]),   # id_type
            s(p[1]),   # id_number
            s(p[6]),   # marital_status
            s(p[7]),   # birth_country
            s(p[11]),  # address
            s(p[12]),  # housing_type
            s(p[13]),  # education_level
            s(p[14]),  # education_status
            s(p[15]),  # profession
            s(p[16]),  # economic_sector
            s(p[17]),  # blood_type
            s(p[18]),  # medical_notes
            s(p[19]),  # optional_info
            s(p[20]),  # responsible_adult_name
            s(p[21]),  # responsible_adult_contact
            s(p[22]),  # guardian_name
            s(p[23]),  # guardian_contact
            parse_date(p[24]),  # birthday
            parse_sex(p[25]),   # sex
            parse_date(p[26]),  # last_group_attendance
            parse_date(p[27]),  # last_meeting_attendance
            s(p[28]),  # membership_type
            map_church_role(s(p[29])),  # attendance_type
            s(p[30]),  # group_name
            s(p[31]),  # campus
            parse_date(p[32]),  # church_join_date
            map_church_role(s(p[29])),  # church_role
            "Activo",  # spiritual_status
            "ACTIVO",   # estado_vital
            now,  # created_at
            now,  # updated_at
        )
        cur.execute(insert_sql, values)
        count += 1
        if count % 10 == 0:
            print(f"  → {count} personas insertadas...")
    except Exception as e:
        email = s(p[10]) or "(sin email)"
        name = f"{s(p[2]) or ''} {s(p[4]) or ''}".strip()
        errores.append(f"  ❌ Error en [{i+1}] {name} <{email}>: {e}")

conn.commit()

print(f"\n{'='*60}")
print(f"✅ MIGRACIÓN COMPLETADA: {count} personas insertadas")
print(f"❌ Errores: {len(errores)}")
for e in errores:
    print(e)

conn.close()
