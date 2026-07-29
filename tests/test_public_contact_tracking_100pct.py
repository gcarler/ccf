"""Tests exhaustivos y estructurales para backend/services/public_contact_tracking.py (100% Cobertura)."""

import pytest
import uuid
from backend import models
from backend.models_crm_pipeline import TipoPipelineEnum, CanalOrigenEnum, EstadoCasoEnum
from backend.services.public_contact_tracking import (
    ContactRecord,
    ContactResult,
    PublicContactTracker,
    _normalize,
    tracker,
)


class TestPublicContactTracking100Pct:

    def test_normalize_helper(self):
        assert _normalize(None) is None
        assert _normalize("") is None
        assert _normalize("   ") is None
        assert _normalize("  contacto@test.com  ") == "contacto@test.com"

    def test_record_contact_no_active_sede_raises(self, db_session):
        tracker_inst = PublicContactTracker()
        rec = ContactRecord(email="test@test.com", first_name="NoSede")
        with pytest.raises(RuntimeError, match="No active sede is configured"):
            tracker_inst.record_contact(db_session, rec)

    def test_record_contact_new_persona_creates_pipeline_and_case(self, db_session):
        sede = models.Sede(nombre="Sede Central", ciudad="Bogotá", es_activa=True)
        db_session.add(sede)
        db_session.commit()

        rec = ContactRecord(
            email="juan.perez@example.com",
            phone="3001234567",
            first_name="Juan",
            last_name="Pérez",
            source="facebook_ads",
            landing_page="https://ccf.org/bienvenida",
            campaign="Campaña2026",
            notes="Interesado en bautismo",
            extra_notes=["Referido por amigo"],
            spiritual_status="Buscador",
            church_role="Nuevo Contacto",
        )

        tracker_inst = PublicContactTracker()
        res = tracker_inst.record_contact(db_session, rec)

        assert res.persona_created is True
        assert res.case_created is True
        assert res.persona is not None
        assert res.persona.first_name == "Juan"
        assert res.persona.last_name == "Pérez"
        assert res.persona.email == "juan.perez@example.com"

        assert res.case is not None
        assert res.case.persona_id == res.persona.id
        assert res.case.sede_id == sede.id
        assert res.case.origen_canal == CanalOrigenEnum.WEB_FORM
        assert res.case.payload_web["source"] == "facebook_ads"

    def test_record_contact_existing_persona_updates_sede_and_reuses_pipeline(self, db_session):
        sede = models.Sede(nombre="Sede Norte", ciudad="Medellín", es_activa=True)
        db_session.add(sede)
        db_session.commit()

        # Existing persona without sede
        existing_p = models.Persona(
            first_name="Ana",
            last_name="Gómez",
            email="ana.gomez@example.com",
            phone="3109876543",
        )
        db_session.add(existing_p)
        db_session.commit()

        # Existing pipeline & stage
        pipe = models.PipelineCRM(
            sede_id=sede.id,
            nombre="Nuevos visitantes",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
        )
        db_session.add(pipe)
        db_session.commit()

        stage = models.EtapaPipeline(
            pipeline_id=pipe.id,
            nombre="Primer Contacto",
            orden=1,
        )
        db_session.add(stage)
        db_session.commit()

        rec = ContactRecord(
            email="ana.gomez@example.com",
            source="web_form",
            sede_id=sede.id,
        )

        res = tracker.record_contact(db_session, rec)

        assert res.persona_created is False
        assert res.persona.id == existing_p.id
        assert res.persona.sede_id == sede.id
        assert res.case.pipeline_id == pipe.id
        assert res.case.etapa_actual_id == stage.id

    def test_record_contact_empty_contact_record_defaults(self, db_session):
        sede = models.Sede(nombre="Sede Sur", ciudad="Cali", es_activa=True)
        db_session.add(sede)
        db_session.commit()

        rec = ContactRecord()  # All defaults None or empty
        res = PublicContactTracker._find_persona(db_session, None, None)
        assert res is None

        # record_contact with default values
        result = tracker.record_contact(db_session, rec)
        assert result.persona_created is True
        assert result.persona.first_name == "Visitante"
        assert result.persona.last_name == ""
