#!/usr/bin/env python3
"""
Migración completa de las 768 personas del Google Sheets a la base de datos ccf_db.
"""
import csv
import uuid
import psycopg2
from datetime import datetime
import re

SEX_MAP = {"Masculino": "M", "Femenino": "F", "M": "M", "F": "F"}

conn = psycopg2.connect(
    host="localhost", dbname="ccf_db",
    user="ccf_admin", password="ccf_password_secret_123"
)
cur = conn.cursor()

cur.execute("SELECT id FROM sedes LIMIT 1")
sede_row = cur.fetchone()
sede_id = sede_row[0] if sede_row else (conn.rollback() or None)
if not sede_row:
    sede_id = uuid.uuid4()
    cur.execute("INSERT INTO sedes (id, nombre, ciudad, es_activa) VALUES (%s, 'Sede Principal', 'Sin Información', true)", (str(sede_id),))
    conn.commit()
print(f"✅ Sede: {sede_id}")

with open('/tmp/iglesia_data.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    all_rows = list(reader)

data_rows = [r for r in all_rows[2:] if len(r) > 1 and r[1].strip() and r[1] != 'Identificación']
print(f"📋 Total: {len(data_rows)}")

def cln(v):
    if v is None: return None
    v = v.strip()
    if not v or v.upper() in ('SIN INFORMACIÓN', 'SIN INFORMACION', 'N/A', '', 'SIN DATO', 'NINGUNO', 'NINGUNA', 'NO APLICA', '0'):
        return None
    return v

def pdate(v):
    v = cln(v)
    if not v: return None
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
        try: return datetime.strptime(v, fmt).date()
        except: continue
    return None

def phon(v):
    v = cln(v)
    if not v: return None
    d = re.sub(r'\D', '', v)
    return d if len(d) >= 7 else None

# Delete previously migrated 76 personas from the old incomplete migration
cur.execute("DELETE FROM personas WHERE church_role IS NOT NULL AND id_number IS NOT NULL")
conn.commit()
print("🗑️  Limpiadas personas previamente migradas")

inserted = 0
errors = 0
i = 0

for row in data_rows:
    i += 1
    try:
        while len(row) < 42:
            row.append('')
        
        p = {
            'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, f"person-{cln(row[1]) or uuid.uuid4()}")),
            'sede_id': str(sede_id),
            'id_type': cln(row[0]),
            'id_number': cln(row[1]),
            'first_name': cln(row[3]) or 'Sin Nombre',
            'second_name': cln(row[4]),
            'last_name': cln(row[5]) or 'Sin Apellido',
            'second_last_name': cln(row[6]),
            'marital_status': cln(row[7]),
            'birth_country': cln(row[8]),
            'phone': phon(row[9]) or phon(row[10]),
            'other_phone': phon(row[10]),
            'mobile_phone': phon(row[11]) or phon(row[9]),
            'email': cln(row[12]),
            'address': cln(row[13]),
            'housing_type': cln(row[14]),
            'education_level': cln(row[15]),
            'education_status': cln(row[16]),
            'profession': cln(row[17]),
            'economic_sector': cln(row[18]),
            'blood_type': cln(row[19]),
            'medical_notes': cln(row[20]),
            'optional_info': cln(row[21]),
            'responsible_adult_name': cln(row[26]),
            'responsible_adult_contact': cln(row[27]),
            'guardian_name': cln(row[28]),
            'guardian_contact': cln(row[29]),
            'birthday': pdate(row[30]),
            'sex': SEX_MAP.get(cln(row[31])),
            'last_group_attendance': pdate(row[32]),
            'last_meeting_attendance': pdate(row[33]),
            'membership_type': cln(row[34]),
            'attendance_type': cln(row[35]),
            'group_name': cln(row[36]),
            'campus': cln(row[37]),
            'church_join_date': pdate(row[38]),
            'church_role': cln(row[34]) or cln(row[35]) or 'Visitante',
        }

        cur.execute("""
            INSERT INTO personas (
                id, sede_id, first_name, second_name, last_name, second_last_name,
                id_type, id_number, email, phone, mobile_phone, other_phone,
                marital_status, birth_country, address, housing_type,
                education_level, education_status, profession, economic_sector,
                blood_type, medical_notes, optional_info,
                responsible_adult_name, responsible_adult_contact,
                guardian_name, guardian_contact,
                birthday, sex,
                last_group_attendance, last_meeting_attendance,
                membership_type, attendance_type, group_name, campus,
                church_join_date, church_role,
                created_at, updated_at
            ) VALUES (
                %(id)s, %(sede_id)s, %(first_name)s, %(second_name)s, %(last_name)s, %(second_last_name)s,
                %(id_type)s, %(id_number)s, %(email)s, %(phone)s, %(mobile_phone)s, %(other_phone)s,
                %(marital_status)s, %(birth_country)s, %(address)s, %(housing_type)s,
                %(education_level)s, %(education_status)s, %(profession)s, %(economic_sector)s,
                %(blood_type)s, %(medical_notes)s, %(optional_info)s,
                %(responsible_adult_name)s, %(responsible_adult_contact)s,
                %(guardian_name)s, %(guardian_contact)s,
                %(birthday)s, %(sex)s,
                %(last_group_attendance)s, %(last_meeting_attendance)s,
                %(membership_type)s, %(attendance_type)s, %(group_name)s, %(campus)s,
                %(church_join_date)s, %(church_role)s,
                NOW(), NOW()
            )
        """, p)

        inserted += 1
        if inserted % 100 == 0:
            conn.commit()
            print(f"  → {inserted}...")

    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ⚠ Fila {i}: {e}")
        conn.rollback()

conn.commit()
print(f"\n✅ Completado: {inserted} insertadas, {errors} errores")
cur.close()
conn.close()
