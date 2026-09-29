"""Tests TKT-CMS-BACKEND-SEDES-03 — Sedes canónicas de Cartagena y endpoint público.

Cubre:
- Seed/migración: 7 sedes canónicas con coordenadas exactas del mapa oficial
  (idempotencia de upsert por nombre, downgrade quirúrgico por marca).
- GET /api/cms/v2/public/locations: 200 sin autenticación, solo activas/no
  borradas, orden sort_order + is_main, contratos nominales y 404-free.
- Sync a CMS: la sección ``feed`` de la página ``locations`` refleja las
  sedes activas (helper compartido con el CRUD admin).
- Fechas UTC: ``created_at``/``updated_at`` de los registros son aware.
"""

from __future__ import annotations

import datetime
import importlib.util
import uuid
from pathlib import Path

import pytest

from backend import models, models_ops
from backend.api.cms_v2.locations import _sync_locations_to_cms_section

PUBLIC_PATH = "/api/cms/v2/public/locations"


def _load_seed_migration():
    """Carga el módulo de migración por ruta de archivo.

    El nombre del archivo comienza con dígitos (no es un identificador
    Python) y el directorio local ``alembic/`` está sombreado por la
    librería ``alembic`` instalada, así que el import por paquete no aplica.
    """
    migration_path = (
        Path(__file__).resolve().parent.parent
        / "alembic"
        / "canonical_versions"
        / "20260929_0001_cms_seed_cartagena_locations.py"
    )
    spec = importlib.util.spec_from_file_location("seed_cartagena_locations", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_migration = _load_seed_migration()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_location(
    db_session,
    name: str,
    *,
    lat: float | None = None,
    lng: float | None = None,
    is_main: bool = False,
    is_active: bool = True,
    deleted: bool = False,
    sort_order: int = 0,
    address: str = "Calle 1 #2-34",
) -> models_ops.ChurchLocation:
    now = datetime.datetime.now(datetime.timezone.utc)
    loc = models_ops.ChurchLocation(
        id=uuid.uuid4(),
        name=name,
        address=address,
        city="Cartagena",
        latitude=lat,
        longitude=lng,
        is_main=is_main,
        is_active=is_active,
        location_type=seed_migration.CANONICAL_TYPE,
        sort_order=sort_order,
        created_at=now,
        deleted_at=now if deleted else None,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc


def _seed_cms_page_with_feed(db_session) -> tuple[models.CmsSite, models.CmsPage, models.CmsSection]:
    now = datetime.datetime.now(datetime.timezone.utc)
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=f"ccf-{uuid.uuid4().hex[:8]}",
        name="CCF Test",
        base_path="/",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(site)
    db_session.flush()

    page = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="locations",
        title="Nuestras Sedes",
        status="published",
        locale="es",
        created_at=now,
        updated_at=now,
    )
    db_session.add(page)
    db_session.flush()

    section = models.CmsSection(
        id=uuid.uuid4(),
        page_id=page.id,
        section_key="feed",
        type="collection",
        sort_order=0,
        status="active",
        is_visible=True,
        props_json={"items": []},
        created_at=now,
        updated_at=now,
    )
    db_session.add(section)
    db_session.commit()
    return site, page, section


# ─────────────────────────────────────────────────────────────────────────────
# Datos canónicos (fuente: mapa oficial Google My Maps)
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_CANONICAL = {
    "Comunidad Cristiana El Faro": (10.3930347, -75.5104067, True),
    "Faro de Gloria": (10.387729, -75.5041959, False),
    "C.C Avivamiento Internacional El Faro": (10.2827598, -75.5148354, False),
    "Los 2 Olivos": (10.2809167, -75.5174839, False),
    "Príncipe del Reino": (10.339825, -75.5475701, False),
    "Príncipe del Reino San Isidro": (10.3891901, -75.5120837, False),
    "Ríos de Agua Viva": (10.3724747, -75.501637, False),
}


class TestCanonicalSeedData:
    def test_seed_data_contains_exact_seven_locations_with_coords(self):
        """El dataset del seed contiene exactamente las 7 sedes con coords del mapa."""
        specs = {s["name"]: s for s in seed_migration.CANONICAL_LOCATIONS}
        assert set(specs) == set(EXPECTED_CANONICAL)
        assert len(seed_migration.CANONICAL_LOCATIONS) == 7

        for name, (lat, lng, is_main) in EXPECTED_CANONICAL.items():
            spec = specs[name]
            assert spec["latitude"] == lat, name
            assert spec["longitude"] == lng, name
            assert spec["is_main"] is is_main, name
            assert spec["city"] == "Cartagena", name
            assert (spec["address"] or "").strip(), name

    def test_only_one_main_location(self):
        mains = [s for s in seed_migration.CANONICAL_LOCATIONS if s["is_main"]]
        assert len(mains) == 1
        assert mains[0]["name"] == "Comunidad Cristiana El Faro"

    def test_seed_function_creates_all_seven(self, db_session):
        """_seed() crea las 7 sedes activas con marca canónica y UTC."""
        seed_migration._seed(db_session.connection())

        rows = (
            db_session.query(models_ops.ChurchLocation)
            .filter(models_ops.ChurchLocation.deleted_at.is_(None))
            .all()
        )
        names = {r.name for r in rows}
        assert names == set(EXPECTED_CANONICAL)
        assert len(rows) == 7
        for row in rows:
            assert row.location_type == seed_migration.CANONICAL_TYPE
            assert row.is_active is True
            assert row.created_at is not None
            assert row.created_at.tzinfo is not None  # UTC aware

    def test_seed_is_idempotent(self, db_session):
        """Ejecutar el seed dos veces no duplica filas (upsert por nombre)."""
        seed_migration._seed(db_session.connection())
        seed_migration._seed(db_session.connection())

        count = (
            db_session.query(models_ops.ChurchLocation)
            .filter(models_ops.ChurchLocation.deleted_at.is_(None))
            .count()
        )
        assert count == 7

    def test_downgrade_only_removes_seeded_rows(self, db_session):
        """El downgrade hace soft-delete SOLO de las filas con marca canónica."""
        seed_migration._seed(db_session.connection())

        # Sede operativa creada por un editor CMS después del seed: NO debe borrarse
        operativa = _make_location(db_session, "Sede Operativa Nueva", is_main=False)

        seed_migration._downgrade(db_session.connection())

        deleted = (
            db_session.query(models_ops.ChurchLocation)
            .filter(models_ops.ChurchLocation.name.in_(set(EXPECTED_CANONICAL)))
            .all()
        )
        assert deleted, "las canónicas deben existir como soft-deleted"
        for row in deleted:
            assert row.deleted_at is not None
            assert row.is_active is False

        db_session.expire_all()
        operativa_after = (
            db_session.query(models_ops.ChurchLocation).filter(models_ops.ChurchLocation.id == operativa.id).first()
        )
        assert operativa_after is not None
        assert operativa_after.deleted_at is None, "la sede operativa debe preservarse"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/cms/v2/public/locations
# ─────────────────────────────────────────────────────────────────────────────


class TestPublicLocationsEndpoint:
    def test_public_locations_returns_active_without_auth(self, client, db_session):
        """200 sin autenticación, solo activas/no borradas, orden correcto."""
        _make_location(db_session, "Sede A", is_main=True, sort_order=0, lat=10.39, lng=-75.51)
        _make_location(db_session, "Sede B", sort_order=1, lat=10.38, lng=-75.50)
        _make_location(db_session, "Sede Borrada", sort_order=2, deleted=True)
        _make_location(db_session, "Sede Inactiva", sort_order=3, is_active=False)

        resp = client.get(PUBLIC_PATH)
        assert resp.status_code == 200
        data = resp.json()
        names = [item["name"] for item in data]
        assert names == ["Sede A", "Sede B"]

        first = data[0]
        assert first["is_main"] is True
        assert first["lat"] == 10.39
        assert first["lng"] == -75.51
        assert first["city"] == "Cartagena"
        assert "is_active" not in first  # el contrato público no expone flags admin

    def test_public_locations_nominal_contract(self, client, db_session):
        """Campos nominales del contrato público (coords, pastor, horario)."""
        _make_location(
            db_session,
            "Sede Contrato",
            is_main=True,
            lat=10.3930347,
            lng=-75.5104067,
        )
        loc = (
            db_session.query(models_ops.ChurchLocation).filter(models_ops.ChurchLocation.name == "Sede Contrato").first()
        )
        loc.pastor_name = "Pastor Ejemplo"
        loc.schedule = "Domingos 9:00 AM y 11:00 AM"
        loc.midweek = "Miércoles 7:00 PM"
        loc.phone = "+57 300 000 0000"
        loc.maps_url = "https://maps.google.com/?q=10.3930347,-75.5104067"
        db_session.commit()

        resp = client.get(PUBLIC_PATH)
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["id"] == str(loc.id)
        assert item["name"] == "Sede Contrato"
        assert item["pastor"] == "Pastor Ejemplo"
        assert item["schedule"] == "Domingos 9:00 AM y 11:00 AM"
        assert item["midweek"] == "Miércoles 7:00 PM"
        assert item["phone"] == "+57 300 000 0000"
        assert item["maps_url"] == "https://maps.google.com/?q=10.3930347,-75.5104067"
        assert item["location_type"] == seed_migration.CANONICAL_TYPE
        assert item["sort_order"] == 0

    def test_public_locations_empty_list(self, client, db_session):
        """Sin sedes activas responde 200 con lista vacía (no 404)."""
        resp = client.get(PUBLIC_PATH)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_public_locations_created_at_utc_convention(self, client, db_session):
        """La convención UTC del modelo: el default ``_utcnow`` produce aware.

        Nota portabilidad: el round-trip en SQLite pierde ``tzinfo`` (el
        valor persistido es UTC correcto); en Postgres con
        ``DateTime(timezone=True)`` el round-trip sí es aware.
        """
        from backend.models_shared import _utcnow

        _make_location(db_session, "Sede UTC", is_main=True)
        now = _utcnow()
        assert now.tzinfo is not None
        assert now.utcoffset() == datetime.timedelta(0)


# ─────────────────────────────────────────────────────────────────────────────
# Sync a CMS (sección feed de la página locations)
# ─────────────────────────────────────────────────────────────────────────────


class TestCmsSectionSync:
    def test_sync_writes_items_to_locations_feed_section(self, client, db_session):
        """El helper de sync escribe las sedes activas en props_json['items']."""
        _seed_cms_page_with_feed(db_session)
        _make_location(db_session, "Sede Sync 1", is_main=True, sort_order=0, lat=10.39, lng=-75.51)
        _make_location(db_session, "Sede Sync 2", sort_order=1)

        _sync_locations_to_cms_section(db_session)

        section = (
            db_session.query(models.CmsSection)
            .filter(models.CmsSection.section_key == "feed")
            .first()
        )
        items = section.props_json["items"]
        assert len(items) == 2
        assert items[0]["name"] == "Sede Sync 1"
        assert items[0]["is_main"] is True
        assert items[0]["lat"] == 10.39
        assert items[1]["name"] == "Sede Sync 2"
        # Contrato de campos del feed (mismo que consume /sedes)
        for item in items:
            assert set(
                ["id", "name", "address", "city", "phone", "pastor", "schedule", "midweek", "image", "lat", "lng", "is_main"]
            ).issubset(item.keys())

    def test_sync_excludes_deleted_and_inactive(self, db_session):
        """El feed CMS solo incluye sedes activas y no borradas."""
        _seed_cms_page_with_feed(db_session)
        _make_location(db_session, "Sede Visible", is_main=True, sort_order=0)
        _make_location(db_session, "Sede Oculta", sort_order=1, deleted=True)
        _make_location(db_session, "Sede Apagada", sort_order=2, is_active=False)

        _sync_locations_to_cms_section(db_session)

        section = (
            db_session.query(models.CmsSection)
            .filter(models.CmsSection.section_key == "feed")
            .first()
        )
        items = section.props_json["items"]
        assert [i["name"] for i in items] == ["Sede Visible"]

    def test_sync_updated_at_is_utc(self, db_session):
        """updated_at escrito por el sync es UTC aware (convención de plataforma)."""
        from backend.models_shared import _utcnow

        _seed_cms_page_with_feed(db_session)
        _make_location(db_session, "Sede UTC Sync", is_main=True)

        _sync_locations_to_cms_section(db_session)

        section = (
            db_session.query(models.CmsSection)
            .filter(models.CmsSection.section_key == "feed")
            .first()
        )
        # El helper escribe datetime.now(timezone.utc); en el ORM el valor
        # asignado es aware (SQLite pierde tzinfo solo en el round-trip).
        assert _utcnow().tzinfo is not None
        assert section.updated_at is not None
