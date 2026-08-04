"""Seed: inserta las 39 sedes restantes de Comunidad Cristiana El Faro.

La sede "COMUNIDAD CRISTIANA EL FARO PRINCIPAL" ya fue creada anteriormente
y tiene las 784 personas migradas. Este script crea las 39 sedes faltantes
del listado original.

Ejecutar:  python scripts/seed_40_sedes_restantes.py
Idempotente: las sedes ya existentes por nombre exacto se saltan.
"""

import os
import uuid as _uuid
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values

# ── Listado completo de sedes (40) ──────────────────────────────────────
# La primera (PRINCIPAL) ya existe, la omitimos en el INSERT.
SEDES = [
    # (nombre, ciudad)
    ("COMUNIDAD CRISTIANA EL FARO PRINCIPAL", "Cartagena"),  # ya existe
    ("COMUNIDAD FAMILIAR CRISTIANA LA SEPTIMA", "Cartagena"),
    ("IGLESIA EMMANUEL BOQUILLA", "Cartagena"),
    ("IGLESIA EMMANUEL VILLA DE ARANJUEZ", "Cartagena"),
    ("CENTRO CRISTIANO VIDA DE LA MARIA", "Cartagena"),
    ("COMUNIDAD CRISTIANA EL FARO MARIA LA BAJA", "Maria la Baja"),
    ("COMUNIDAD CRISTIANA EL FARO BARU", "Barú"),
    ("COMUNIDAD CRISTIANA EL FARO SANTA ROSA", "Santa Rosa"),
    ("COMUNIDAD CRISTIANA EL FARO SANTA ROSA- VILLA ROSANA", "Santa Rosa"),
    ("COMUNIDAD CRISTIANA FARO DE GLORIA", "Cartagena"),
    ("FARO TIERRA FRUCTIFERA BOQUILLA", "Cartagena"),
    ("COMUNIDAD CRISTIANA EL FARO CASA DE FE POLICARPA", "Cartagena"),
    ("COMUNIDAD CRISTIANA EL FARO CASA DE FE VILLA HERMOSA", "Cartagena"),
    ("COMUNIDAD CRISTIANA EL FARO PASACABALLO", "Pasacaballo"),
    ("IGLESIA CRISTIANA PRINCIPE DEL REINO", "Cartagena"),
    ("IGLESIA CRISTIANA PRINCIPE DEL REINO SAN ISIDRO", "Cartagena"),
    ("COMUNIDAD CRISTIANA EL LEON DE LA TRIBU DE JUDA", "Cartagena"),
    ("IGLESIA CASA DE ORACION JESUCRISTO PARA LAS NACIONES", "Cartagena"),
    ("LUGAR DE REFUGIO PARA LAS NACIONES - PASACABALLOS", "Pasacaballos"),
    ("LUGAR DE REFUGIO PARA LAS NACIONES - SANTA ANA", "Santa Ana"),
    ("LUGAR DE REFUGIO PARA LAS NACIONES - BAJO DEL TIGRE", "Bajo del Tigre"),
    ("COMUNIDAD CRISTIANA EL FARO LOS DOS OLIVOS DE NUESTRO SEÑOR JESUCRISTO", "Cartagena"),
    ("COMUNIDAD CRISTIANA LOS DOS OLIVOS ARARCA", "Ararca"),
    ("COMUNIDAD CRISTIANA RIOS DE AGUA VIVA NUEVO ISRAEL", "Cartagena"),
    ("COMUNIDAD CRISTIANA FARO JESUS ES PAN DE VIDA", "Cartagena"),
    ("COMUNIDAD CRISTIANA RIOS DE AGUA VIVA", "Cartagena"),
    ("IGLESIA REFRENDA LUZ", "Cartagena"),
    ("PALABRA DE VERDAD Y VIDA EL FARO", "Cartagena"),
    ("IGLESIA AVIVANDO EL FUEGO DE CRISTO", "Cartagena"),
    ("CASA DE RESTAURACION SANTA ANA", "Santa Ana"),
    ("NACION SANTA TIERRA BOMBA", "Tierra Bomba"),
    ("COMUNIDAD CRISTIANA EL FARO CHIGORODO", "Chigorodó"),
    ("COMUNIDAD CRISTIANA EL FARO CAREPA", "Carepa"),
    ("IGLESIA CATEDRAL DE ALABANZAS. NELSON MANDELA", "Cartagena"),
    ("IGLESIA CASA DE DIOS", "Cartagena"),
    ("IGLESIA CRISTIANA ARCA DE SALVACION", "Cartagena"),
    ("IGLESIA FARO DONDE ESTA EL ESPIRITU DEL SEÑOR ALLI HAY LIBERTAD", "Cartagena"),
    ("IGLESIA CRISTIANA MONTE DE SION JESUCRISTO PERMANECE FIEL", "Cartagena"),
    ("IGLESIA JESUS DE NAZARET REY DE REYES", "Cartagena"),
    ("IGLESIA MENSAJEROS DE COMPASION", "Cartagena"),
]


def main():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("database_url")
    if not db_url:
        # Intentar leer del .env
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("database_url="):
                        db_url = line.split("=", 1)[1]
                        break

    if not db_url:
        print("ERROR: No se encontró DATABASE_URL en el entorno ni en .env")
        return 1

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Obtener sedes ya existentes para no duplicar
        cur.execute("SELECT nombre FROM sedes WHERE deleted_at IS NULL")
        existentes = {row[0] for row in cur.fetchall()}

        now = datetime.now(timezone.utc)
        nuevas = []
        omitidas = []

        for nombre, ciudad in SEDES:
            if nombre in existentes:
                omitidas.append(nombre)
                continue
            nuevas.append((str(_uuid.uuid4()), nombre, ciudad, True, now, now))

        if nuevas:
            execute_values(
                cur,
                """INSERT INTO sedes (id, nombre, ciudad, es_activa, created_at, updated_at)
                   VALUES %s""",
                nuevas,
                template="(%s, %s, %s, %s::boolean, %s, %s)",
            )
            conn.commit()
            print(f"✅ Insertadas {len(nuevas)} sedes nuevas.")
        else:
            print("ℹ️  No hay sedes nuevas para insertar.")

        if omitidas:
            print(f"ℹ️  Omitidas {len(omitidas)} sedes (ya existentes en BD):")
            for s in omitidas:
                print(f"   - {s}")

        # Mostrar resumen final
        cur.execute("SELECT id, nombre, ciudad FROM sedes WHERE deleted_at IS NULL ORDER BY nombre")
        todas = cur.fetchall()
        print(f"\n📊 Total sedes activas ahora: {len(todas)}")
        for sid, snombre, sciudad in todas:
            print(f"   • {snombre} ({sciudad})")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        return 1
    finally:
        cur.close()
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
