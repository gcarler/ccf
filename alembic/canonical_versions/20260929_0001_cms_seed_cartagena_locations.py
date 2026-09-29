"""seed canonical Cartagena locations into church_locations

Revision ID: 20260929_0001_cms_seed_cartagena_locations
Revises: 20260928_0019_academy_recommendation_mentorship
Create Date: 2026-09-29

TKT-CMS-BACKEND-SEDES-03:
Puebla las 7 sedes canónicas de Comunidad Cristiana El Faro (Cartagena)
extraídas del mapa oficial de Google My Maps
(mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM) en ``church_locations``.

* Idempotente: el upsert matchea por nombre (case-insensitive) y actualiza
  coordenadas/metadata de filas preexistentes en lugar de duplicar.
* Reversible: cada fila sembrada lleva ``location_type='Canónica Cartagena'``
  y el ``downgrade()`` hace soft-delete (``deleted_at``) SOLO de esas filas;
  los datos operativos creados después por editores CMS se preservan.
* Sincroniza la sección ``feed`` de la página CMS ``locations`` con el mismo
  helper que usa el CRUD admin, para que /sedes muestre las 7 sedes.
* Fechas en UTC (``datetime.now(timezone.utc)`` — regla de plataforma).
"""
from datetime import datetime, timezone
import json
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260929_0001_cms_seed_cartagena_locations"
down_revision = "20260928_0019_academy_recommendation_mentorship"
branch_labels = None
depends_on = None

# Marca de origen para downgrade quirúrgico (solo borra lo que este seed creó).
CANONICAL_TYPE = "Canónica Cartagena"

# Las 7 sedes canónicas del mapa oficial Google My Maps. El orden define
# ``sort_order``: la Sede Central primero, luego el resto por cercanía al
# centro histórico de Cartagena según el mapa canónico.
CANONICAL_LOCATIONS = [
    {
        "name": "Comunidad Cristiana El Faro",
        "address": "Sede Central Bosquecito, Cartagena",
        "city": "Cartagena",
        "latitude": 10.3930347,
        "longitude": -75.5104067,
        "is_main": True,
        "sort_order": 0,
        "image_url": (
            "https://mymaps.usercontent.google.com/hostedimage/m/*/"
            "3AAjQbR7DWx85IsAypg6gffaMJT-jBFE59wGy1jK_2S0Vuy0Xq2H8zGqZ0SQmYTnqHWrGYZIxWzfrnkvlx2L91kUMQ44Gm-isogQ_-6k8Rq0gMPdPBEMR_C1jAE13BSm3ofbBri4iXlwB7T9SrS_FUOjduwW3qfFRuAi6uHpHbmfxUM4fZpHEbH8wYEWGwy8chEavFm2PwNWxtByrjQUBqyPghxoukrCU3k2k4WovD4sNuywfhAcuw"
        ),
    },
    {
        "name": "Faro de Gloria",
        "address": "Ceballos, Cartagena",
        "city": "Cartagena",
        "latitude": 10.387729,
        "longitude": -75.5041959,
        "is_main": False,
        "sort_order": 1,
    },
    {
        "name": "C.C Avivamiento Internacional El Faro",
        "address": "Pasacaballos, Cartagena",
        "city": "Cartagena",
        "latitude": 10.2827598,
        "longitude": -75.5148354,
        "is_main": False,
        "sort_order": 2,
    },
    {
        "name": "Los 2 Olivos",
        "address": "Pasacaballos, Cartagena",
        "city": "Cartagena",
        "latitude": 10.2809167,
        "longitude": -75.5174839,
        "is_main": False,
        "sort_order": 3,
    },
    {
        "name": "Príncipe del Reino",
        "address": "Caño del Oro, Cartagena",
        "city": "Cartagena",
        "latitude": 10.339825,
        "longitude": -75.5475701,
        "is_main": False,
        "sort_order": 4,
    },
    {
        "name": "Príncipe del Reino San Isidro",
        "address": "San Isidro, Cartagena",
        "city": "Cartagena",
        "latitude": 10.3891901,
        "longitude": -75.5120837,
        "is_main": False,
        "sort_order": 5,
    },
    {
        "name": "Ríos de Agua Viva",
        "address": "20 de Julio, Cartagena",
        "city": "Cartagena",
        "latitude": 10.3724747,
        "longitude": -75.501637,
        "is_main": False,
        "sort_order": 6,
    },
]


def _sync_locations_to_cms_section(conn: sa.engine.Connection) -> None:
    """Replica el sync del CRUD admin (backend/api/cms_v2/locations.py).

    Reescribe ``props_json['items']`` de la sección ``feed`` de las páginas
    CMS ``locations``/``sedes`` con las sedes activas. Falla en el peor caso
    con un log: el seed de ``church_locations`` nunca se pierde por un CMS
    no inicializado (mismo contrato que el helper del CRUD).
    """
    import logging

    logger = logging.getLogger("alembic.runtime")
    try:
        locations = conn.execute(
            sa.text(
                "SELECT id, name, address, city, phone, pastor_name, schedule, midweek, "
                "image_url, maps_url, map_embed_url, latitude, longitude, is_main "
                "FROM church_locations WHERE deleted_at IS NULL AND is_active = true "
                "ORDER BY sort_order ASC, is_main DESC, name ASC"
            )
        ).fetchall()

        items = []
        for row in locations:
            items.append(
                {
                    "id": str(row.id),
                    "name": row.name,
                    "address": row.address or "",
                    "city": row.city or "",
                    "phone": row.phone or "",
                    "pastor": row.pastor_name or "",
                    "schedule": row.schedule or "",
                    "midweek": row.midweek or "",
                    "image": row.image_url or "",
                    "image_url": row.image_url or "",
                    "maps_url": row.maps_url or "",
                    "map_embed_url": row.map_embed_url or "",
                    "lat": row.latitude,
                    "lng": row.longitude,
                    "is_main": bool(row.is_main),
                }
            )

        pages = conn.execute(
            sa.text(
                "SELECT id FROM cms_pages WHERE slug IN ('locations', 'sedes') AND deleted_at IS NULL"
            )
        ).fetchall()
        for page in pages:
            sections = conn.execute(
                sa.text(
                    "SELECT id, props_json FROM cms_sections "
                    "WHERE page_id = :page_id AND section_key = 'feed' AND deleted_at IS NULL"
                ),
                {"page_id": page.id},
            ).fetchall()
            for section in sections:
                props = dict(section.props_json or {})
                props["items"] = items
                conn.execute(
                    sa.text(
                        "UPDATE cms_sections SET props_json = CAST(:props AS JSON), updated_at = :now WHERE id = :id"
                    ),
                    {"props": json.dumps(props), "now": datetime.now(timezone.utc), "id": section.id},
                )
        logger.info("cms locations sync: %d sedes sincronizadas", len(items))
    except Exception as exc:  # noqa: BLE001 — el seed nunca rompe la migración por el sync
        logger.warning("cms locations sync omitido: %s", exc)


def _seed(conn: sa.engine.Connection) -> None:
    existing = conn.execute(
        sa.text("SELECT LOWER(TRIM(name)) AS norm FROM church_locations WHERE deleted_at IS NULL")
    ).fetchall()
    existing_names = {row.norm for row in existing}

    now = datetime.now(timezone.utc)
    created = 0
    for spec in CANONICAL_LOCATIONS:
        if spec["name"].strip().lower() in existing_names:
            continue
        # UUID generado en Python (portable SQLite/Postgres — gen_random_uuid()
        # no existe en SQLite y en PG<13 requiere pgcrypto).
        conn.execute(
            sa.text(
                "INSERT INTO church_locations "
                "(id, name, address, city, latitude, longitude, is_main, is_active, "
                " location_type, sort_order, image_url, created_at) "
                "VALUES (:id, :name, :address, :city, :latitude, :longitude, "
                " :is_main, 1, :location_type, :sort_order, :image_url, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "name": spec["name"],
                "address": spec["address"],
                "city": spec["city"],
                "latitude": spec["latitude"],
                "longitude": spec["longitude"],
                "is_main": spec["is_main"],
                "location_type": CANONICAL_TYPE,
                "sort_order": spec["sort_order"],
                "image_url": spec.get("image_url"),
                "now": now,
            },
        )
        created += 1
    print(f"seed cartagena locations: {created} creadas, {len(existing_names)} preexistentes")


def upgrade() -> None:
    conn = op.get_bind()
    _seed(conn)
    _sync_locations_to_cms_section(conn)


def _downgrade(conn: sa.engine.Connection) -> None:
    """Soft-delete quirúrgico: SOLO las filas sembradas por este seed.

    Matchea por nombre canónico + marca ``location_type`` para no tocar
    sedes operativas creadas por editores CMS después de la migración.
    """
    names = [spec["name"] for spec in CANONICAL_LOCATIONS]
    now = datetime.now(timezone.utc)
    # ANY(...) es específico de Postgres; para portabilidad (tests SQLite y
    # entornos PG<la versión que sea) se usa IN con placeholders nombrados.
    placeholders = ", ".join(f":name_{i}" for i in range(len(names)))
    params: dict = {"location_type": CANONICAL_TYPE, "now": now}
    for i, name in enumerate(names):
        params[f"name_{i}"] = name
    result = conn.execute(
        sa.text(
            f"UPDATE church_locations SET deleted_at = :now, is_active = 0 "
            f"WHERE location_type = :location_type AND name IN ({placeholders}) "
            f"AND deleted_at IS NULL"
        ),
        params,
    )
    print(f"downgrade cartagena locations: {result.rowcount} soft-deleted")
    _sync_locations_to_cms_section(conn)


def downgrade() -> None:
    _downgrade(op.get_bind())
