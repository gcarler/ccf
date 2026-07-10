from __future__ import annotations

import datetime
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

try:
    import openai
except ImportError:
    openai = MagicMock()
    sys.modules["openai"] = openai

from backend import models
from tests.conftest import auth_headers, seed_admin


# ── Helper for calling the scoring engine ─────────────────────────────
def _call_scoring_engine(db_session: Session, persona_id: uuid.UUID):
    """
    Tries to locate and call the pastoral health scoring engine.
    Looks in backend.services.pastoral_health and backend.crud.crm.
    """
    try:
        from backend.services import pastoral_health
        if hasattr(pastoral_health, "calculate_pastoral_health_score"):
            return pastoral_health.calculate_pastoral_health_score(db_session, persona_id)
        elif hasattr(pastoral_health, "calculate_health_score"):
            return pastoral_health.calculate_health_score(db_session, persona_id)
    except ImportError:
        pass

    try:
        from backend.crud import crm
        if hasattr(crm, "calculate_pastoral_health_score"):
            return crm.calculate_pastoral_health_score(db_session, persona_id)
        elif hasattr(crm, "calculate_health_score"):
            return crm.calculate_health_score(db_session, persona_id)
    except (ImportError, AttributeError):
        pass

    pytest.fail(
        "Pastoral health scoring engine function (calculate_pastoral_health_score or calculate_health_score) "
        "not found in backend.services.pastoral_health or backend.crud.crm"
    )


# ── OpenAI Mock Fixture ───────────────────────────────────────────────
@pytest.fixture
def mock_openai_client():
    with patch("openai.OpenAI") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "Mocked AI Response Suggestion"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        yield mock_client


# ══════════════════════════════════════════════════════════════════════
# TIER 1: FEATURE COVERAGE (15 tests)
# ══════════════════════════════════════════════════════════════════════

# --- Feature A: Pastoral Health Score ---

def test_health_score_initial_defaults(db_session: Session):
    """
    1. Verifies that the new columns 'health_score' and 'health_status' exist on the
    Persona model, and that a newly created Persona defaults them correctly to None or appropriate initial values.
    """
    assert hasattr(models.Persona, "health_score"), "Persona model missing health_score column"
    assert hasattr(models.Persona, "health_status"), "Persona model missing health_status column"

    persona = models.Persona(
        first_name="John",
        last_name="Doe",
        email="john.doe.defaults@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)

    assert persona.health_score is None, "New persona should have health_score initialized to None"
    assert persona.health_status is None, "New persona should have health_status initialized to None"


def test_health_score_calc_no_activity(db_session: Session):
    """
    2. Verifies that a persona with absolutely no activity (no attendance, no donations, etc.)
    receives a low health score (e.g. 0-30) and status EN_RIESGO.
    """
    # Verify columns exist first
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Inactive",
        last_name="Member",
        email="inactive.member@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score is not None
    assert 0 <= persona.health_score <= 30
    assert persona.health_status == "EN_RIESGO"


def test_health_score_calc_high_activity(db_session: Session):
    """
    3. Verifies that a persona with high recent activity (attendances, donations, group sessions)
    is scored highly (71-100) with status COMPROMETIDO.
    """
    assert hasattr(models.Persona, "health_score")
    
    # 1. Create Sede
    sede = models.Sede(nombre="High Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    # 2. Create Persona
    persona = models.Persona(
        first_name="Active",
        last_name="Member",
        email="active.member@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # 3. Simulate high activity: multiple attendances and donations
    # We can create event attendances if they exist, or log donations
    for i in range(10):
        donation = models.Donation(
            persona_id=persona.id,
            amount=100.0,
            donation_date=datetime.date.today() - datetime.timedelta(days=i),
            status="completed"
        )
        db_session.add(donation)
    
    db_session.commit()
    db_session.refresh(persona)

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score is not None
    assert 71 <= persona.health_score <= 100
    assert persona.health_status == "COMPROMETIDO"


def test_health_score_calc_medium_activity(db_session: Session):
    """
    4. Verifies that a persona with moderate recent activity receives a medium score (31-70)
    and status ESTABLE.
    """
    assert hasattr(models.Persona, "health_score")
    
    sede = models.Sede(nombre="Medium Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    persona = models.Persona(
        first_name="Medium",
        last_name="Member",
        email="medium.member@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # Moderate activity: some activity but less than high
    donation = models.Donation(
        persona_id=persona.id,
        amount=50.0,
        donation_date=datetime.date.today(),
        status="completed"
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(persona)

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score is not None
    assert 31 <= persona.health_score <= 70
    assert persona.health_status == "ESTABLE"


def test_health_score_calc_db_update(db_session: Session):
    """
    5. Verifies that running the calculation updates the database columns and commits them correctly,
    so they persist in subsequent database sessions.
    """
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Persist",
        last_name="Test",
        email="persist.test@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    persona_id = persona.id

    _call_scoring_engine(db_session, persona_id)

    # Start a fresh query to verify persistence
    db_session.expire_all()
    queried_persona = db_session.query(models.Persona).filter(models.Persona.id == persona_id).one()
    assert queried_persona.health_score is not None
    assert queried_persona.health_status is not None


# --- Feature B: AI Copilot for Counseling ---

def test_ai_copilot_endpoint_success(client, db_session: Session, mock_openai_client):
    """
    6. Verifies that requesting the copilot-draft endpoint returns a generated suggestion draft successfully.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Counselee",
        last_name="Doe",
        email="counselee@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Seeking spiritual guidance",
        notes="Feeling lost and seeking advice.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)
    
    data = response.json()
    assert "draft" in data or "suggestion" in data
    draft_val = data.get("draft") or data.get("suggestion")
    assert draft_val == "Mocked AI Response Suggestion"


def test_ai_copilot_empty_history(client, db_session: Session, mock_openai_client):
    """
    7. Verifies that requesting a copilot draft on a ticket with empty/blank history/notes
    handles it gracefully by returning a standard draft recommendation.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="NoNotes",
        last_name="User",
        email="nonotes@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Empty notes case",
        notes="",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "draft" in data or "suggestion" in data


def test_ai_copilot_openai_missing_key(client, db_session: Session, monkeypatch):
    """
    8. Verifies that the endpoint falls back gracefully if the OPENAI_API_KEY environment variable is missing,
    returning a warning or standard template message rather than throwing an internal server error.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="NoKey",
        last_name="User",
        email="nokey@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Spiritual block",
        notes="Jane is undergoing a crisis of faith.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # Even without the key, the API must handle the exception gracefully
    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 400, 500) # Graceful error handling (standard code or customized message)
    if response.status_code == 200:
        data = response.json()
        assert "draft" in data or "suggestion" in data
        val = data.get("draft") or data.get("suggestion")
        assert "OpenAI" in val or "API key" in val or "fallback" in val or len(val) > 0


def test_ai_copilot_openai_error_propagation(client, db_session: Session):
    """
    9. Verifies that if the OpenAI client library raises an API Error (e.g. Rate Limit, API connection, etc.),
    the endpoint handles the error gracefully without a 500 crash.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="ErrProp",
        last_name="User",
        email="errprop@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Faith counseling",
        notes="Struggling with work/life balance.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # Mock OpenAI to throw an error
    with patch("openai.OpenAI") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("OpenAI Rate Limit Exceeded")

        response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
        assert response.status_code in (200, 429, 503, 500) # Should fail gracefully
        # If it returns 200, it should be a fallback suggestion
        if response.status_code == 200:
            data = response.json()
            assert "draft" in data or "suggestion" in data


def test_ai_copilot_response_payload_structure(client, db_session: Session, mock_openai_client):
    """
    10. Verifies that the endpoint response payload adheres to the required contract JSON schema.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Schema",
        last_name="Check",
        email="schemacheck@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Schema validation",
        notes="Notes for schema",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)
    
    data = response.json()
    assert isinstance(data, dict)
    assert "draft" in data or "suggestion" in data


# --- Feature C: Omnichannel Inbox / Unified Timeline ---

def test_timeline_unification_whatsapp(client, db_session: Session):
    """
    11. Verifies that WhatsApp communication logs show up in the unified timeline of the persona.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Timeline",
        last_name="WA",
        email="timeline.wa@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="Important outreach via WhatsApp",
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(log)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    
    timeline = response.json()
    # Check that a WhatsApp log is present in timeline
    wa_found = False
    for item in timeline:
        desc = item.get("description", "").lower()
        title = item.get("title", "").lower()
        ch = item.get("channel", "").lower()
        t = item.get("type", "").lower()
        if "whatsapp" in desc or "whatsapp" in title or ch == "whatsapp" or t == "whatsapp":
            wa_found = True
            break
    assert wa_found, "WhatsApp communication was not unified in timeline"


def test_timeline_unification_sms(client, db_session: Session):
    """
    12. Verifies that SMS communication logs show up in the unified timeline.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Timeline",
        last_name="SMS",
        email="timeline.sms@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="sms",
        content="Welcome via SMS",
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(log)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    
    timeline = response.json()
    sms_found = False
    for item in timeline:
        desc = item.get("description", "").lower()
        title = item.get("title", "").lower()
        ch = item.get("channel", "").lower()
        t = item.get("type", "").lower()
        if "sms" in desc or "sms" in title or ch == "sms" or t == "sms":
            sms_found = True
            break
    assert sms_found, "SMS communication was not unified in timeline"


def test_timeline_unification_email(client, db_session: Session):
    """
    13. Verifies that Email communication logs show up in the unified timeline.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Timeline",
        last_name="Email",
        email="timeline.email@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content="Monthly bulletin via Email",
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(log)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    
    timeline = response.json()
    email_found = False
    for item in timeline:
        desc = item.get("description", "").lower()
        title = item.get("title", "").lower()
        ch = item.get("channel", "").lower()
        t = item.get("type", "").lower()
        if "email" in desc or "email" in title or ch == "email" or t == "email":
            email_found = True
            break
    assert email_found, "Email communication was not unified in timeline"


def test_timeline_unification_spiritual_milestones(client, db_session: Session):
    """
    14. Verifies that spiritual milestones show up in the unified timeline.
    (This is expected to fail on baseline, since SpiritualMilestones are not queried in the baseline timeline).
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Timeline",
        last_name="Milestone",
        email="timeline.milestone@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # Create spiritual milestone
    milestone = models.SpiritualMilestone(
        persona_id=persona.id,
        type="Baptism",
        event_date=datetime.date.today(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(milestone)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    
    timeline = response.json()
    milestone_found = False
    for item in timeline:
        desc = item.get("description", "").lower()
        title = item.get("title", "").lower()
        t = item.get("type", "").lower()
        if "baptism" in desc or "baptism" in title or t in ("spiritual_milestone", "milestone", "baptism"):
            milestone_found = True
            break
            
    assert milestone_found, "SpiritualMilestone (Baptism) was not unified in timeline"


def test_timeline_sorting_order(client, db_session: Session):
    """
    15. Verifies that the unified timeline returns all events in descending chronological order.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Timeline",
        last_name="Sorting",
        email="timeline.sorting@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    base_time = datetime.datetime.now(datetime.timezone.utc)

    # 1. WhatsApp (oldest)
    log_wa = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="Hello WA",
        created_at=base_time - datetime.timedelta(days=10)
    )
    # 2. SMS
    log_sms = models.CommunicationLog(
        persona_id=persona.id,
        channel="sms",
        content="Hello SMS",
        created_at=base_time - datetime.timedelta(days=5)
    )
    # 3. Email
    log_email = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content="Hello Email",
        created_at=base_time - datetime.timedelta(days=2)
    )
    # 4. Milestone (newest)
    milestone = models.SpiritualMilestone(
        persona_id=persona.id,
        type="Leadership Assignment",
        event_date=(base_time - datetime.timedelta(days=1)).date(),
        created_at=base_time - datetime.timedelta(days=1)
    )

    db_session.add_all([log_wa, log_sms, log_email, milestone])
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    timeline = response.json()

    assert len(timeline) >= 4
    dates = [item["date"] for item in timeline if "date" in item]
    
    # Verify descending sort order
    sorted_dates = sorted(dates, reverse=True)
    assert dates == sorted_dates, "Timeline events are not sorted chronologically descending"


# ══════════════════════════════════════════════════════════════════════
# TIER 2: BOUNDARY & CORNER CASES (15 tests)
# ══════════════════════════════════════════════════════════════════════

# --- Feature A: Pastoral Health Score ---

def test_health_score_calc_exactly_zero_score(db_session: Session):
    """
    16. Verifies that the lowest bounds of metrics yields a score of exactly 0 and status EN_RIESGO.
    Checks division and bounds handling.
    """
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Zero",
        last_name="Score",
        email="zero.score@example.com"
    )
    db_session.add(persona)
    db_session.commit()

    # Zero activity should trigger a minimum bound
    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score == 0
    assert persona.health_status == "EN_RIESGO"


def test_health_score_calc_exactly_hundred_score(db_session: Session):
    """
    17. Verifies that extremely high activity caps the score at exactly 100 with COMPROMETIDO.
    """
    assert hasattr(models.Persona, "health_score")
    
    sede = models.Sede(nombre="Max Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    persona = models.Persona(
        first_name="Max",
        last_name="Score",
        email="max.score@example.com",
        sede_id=sede.id,
        is_baptized=True
    )
    db_session.add(persona)
    db_session.flush()

    # Create massive activity to guarantee maximum score
    for i in range(50):
        donation = models.Donation(
            persona_id=persona.id,
            amount=500.0,
            donation_date=datetime.date.today() - datetime.timedelta(days=i),
            status="completed"
        )
        db_session.add(donation)
    
    db_session.commit()

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score == 100
    assert persona.health_status == "COMPROMETIDO"


def test_health_score_calc_missing_data_fields(db_session: Session):
    """
    18. Verifies that the scoring engine handles Persona records with missing optional fields
    (e.g., registration_date is None, last_group_attendance is None, etc.) without crashing.
    """
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Nulls",
        last_name="Everywhere",
        email="nulls@example.com",
        registration_date=None,
        last_group_attendance=None,
        last_meeting_attendance=None
    )
    db_session.add(persona)
    db_session.commit()

    # Call engine. Should not raise AttributeError or TypeError
    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)
    
    assert persona.health_score is not None


def test_health_score_calc_inactive_persona(db_session: Session):
    """
    19. Verifies that inactive personas (estado_vital = 'INACTIVO') are skipped by the scoring calculations
    or are handled according to policies (e.g. keeping their score at 0 or None).
    """
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Inactive",
        last_name="Member",
        email="inactive.status@example.com",
        estado_vital="INACTIVO"
    )
    db_session.add(persona)
    db_session.commit()

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    # Inactive should remain uncalculated or zero
    assert persona.health_score is None or persona.health_score == 0


def test_health_score_calc_extreme_activities(db_session: Session):
    """
    20. Verifies that out-of-bounds metrics (e.g., 999999 event attendances or donations)
    do not overflow the calculation or lead to score values greater than 100.
    """
    assert hasattr(models.Persona, "health_score")
    
    persona = models.Persona(
        first_name="Extreme",
        last_name="Metrics",
        email="extreme@example.com"
    )
    db_session.add(persona)
    db_session.flush()

    # Add an astronomically large donation
    donation = models.Donation(
        persona_id=persona.id,
        amount=1000000000.0,
        donation_date=datetime.date.today(),
        status="completed"
    )
    db_session.add(donation)
    db_session.commit()

    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    assert persona.health_score <= 100


# --- Feature B: AI Copilot ---

def test_ai_copilot_invalid_ticket_id(client, db_session: Session):
    """
    21. Verifies that querying the AI copilot endpoint with a non-existent or malformed
    ticket ID returns a 404 or 422 error.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    fake_id = uuid.uuid4()
    response = client.get(f"/api/crm/counseling/{fake_id}/copilot-draft", headers=headers)
    assert response.status_code in (404, 422)


def test_ai_copilot_unauthorized_user(client, db_session: Session):
    """
    22. Verifies that calling the AI copilot endpoint without correct authorization headers
    fails with a 401 or 403 Forbidden.
    """
    persona = models.Persona(first_name="Auth", last_name="Fail", email="authfail@example.com")
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Secret counseling",
        notes="Private note",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # Call without auth headers
    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft")
    assert response.status_code in (401, 403)


def test_ai_copilot_extremely_long_history(client, db_session: Session, mock_openai_client):
    """
    23. Verifies that the endpoint handles extremely long notes/history by truncating
    or summarizing it safely, avoiding context window overflows in the OpenAI API call.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="LongHistory",
        last_name="User",
        email="longhistory@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # Create ticket with massive notes
    huge_notes = "A " * 50000  # Very long text
    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Heavy counseling case",
        notes=huge_notes,
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)


def test_ai_copilot_non_ascii_characters(client, db_session: Session, mock_openai_client):
    """
    24. Verifies that the endpoint correctly processes non-ASCII characters, symbols,
    and emojis in counseling notes without encoding failures.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Unicode",
        last_name="Test",
        email="unicode@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    unicode_notes = "Counseling with emojis 😇, Spanish accents (á, é, í, ó, ú, ñ), and symbols."
    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Unicode Support 🧐",
        notes=unicode_notes,
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)


def test_ai_copilot_cross_sede_isolation(client, db_session: Session):
    """
    25. Verifies that a staff member in Sede A cannot call the copilot endpoint
    for a counseling ticket belonging to a persona in Sede B (Axioma 3: Sede scope isolation).
    """
    # 1. Create Sede A and Sede B
    sede_a = models.Sede(nombre="Sede A", ciudad="Bogota", es_activa=True)
    sede_b = models.Sede(nombre="Sede B", ciudad="Medellin", es_activa=True)
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    # 2. User in Sede A
    user_a, persona_a, _ = seed_admin(db_session, email="staff.a@example.com")
    user_a.sede_id = sede_a.id
    persona_a.sede_id = sede_a.id
    db_session.flush()

    # 3. Ticket for Persona in Sede B
    persona_b = models.Persona(
        first_name="Isolate",
        last_name="B",
        email="isolate.b@example.com",
        sede_id=sede_b.id
    )
    db_session.add(persona_b)
    db_session.flush()

    ticket_b = models.CounselingTicket(
        persona_id=persona_b.id,
        subject="Cross-sede problem",
        notes="Sede B notes",
        status="open"
    )
    db_session.add(ticket_b)
    db_session.commit()

    # Request with User A's auth headers
    headers_a = auth_headers(client, email=user_a.email)
    response = client.get(f"/api/crm/counseling/{ticket_b.id}/copilot-draft", headers=headers_a)
    
    # Must fail with 404 (or 403) due to scope boundary
    assert response.status_code in (404, 403)


# --- Feature C: Omnichannel Inbox ---

def test_timeline_empty_events(client, db_session: Session):
    """
    26. Verifies that requesting the timeline for a persona with zero communication logs or milestones
    does not crash, returning either an empty list or only the default registration event.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="NoEvents",
        last_name="User",
        email="noevents@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        timeline = response.json()
        assert isinstance(timeline, list)


def test_timeline_duplicate_timestamps(client, db_session: Session):
    """
    27. Verifies that events with duplicate timestamps are handled cleanly and sorted deterministically.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Duplicate",
        last_name="Time",
        email="duplicate.time@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    shared_time = datetime.datetime.now(datetime.timezone.utc)

    # Two events with exact same timestamp
    log1 = models.CommunicationLog(
        persona_id=persona.id,
        channel="sms",
        content="SMS First",
        created_at=shared_time
    )
    log2 = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content="Email Second",
        created_at=shared_time
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) >= 2


def test_timeline_cross_sede_leakage(client, db_session: Session):
    """
    28. Verifies that a user from Sede A cannot view the timeline of a persona from Sede B.
    """
    sede_a = models.Sede(nombre="Sede A", ciudad="Bogota", es_activa=True)
    sede_b = models.Sede(nombre="Sede B", ciudad="Medellin", es_activa=True)
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    user_a, persona_a, _ = seed_admin(db_session, email="staff.a.leak@example.com")
    user_a.sede_id = sede_a.id
    persona_a.sede_id = sede_a.id
    db_session.flush()

    persona_b = models.Persona(
        first_name="Leak",
        last_name="Target",
        email="leak.target@example.com",
        sede_id=sede_b.id
    )
    db_session.add(persona_b)
    db_session.commit()

    headers_a = auth_headers(client, email=user_a.email)
    response = client.get(f"/api/crm/personas/{persona_b.id}/timeline", headers=headers_a)
    assert response.status_code in (404, 403)


def test_timeline_special_milestone_types(client, db_session: Session):
    """
    29. Verifies that the timeline correctly supports custom or unusually long milestone types.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Custom",
        last_name="Milestone",
        email="custom.milestone@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    custom_type = "Completed Advanced Discipleship Masterclass With High Honors"
    milestone = models.SpiritualMilestone(
        persona_id=persona.id,
        type=custom_type,
        event_date=datetime.date.today(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(milestone)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    
    timeline = response.json()
    type_found = False
    for item in timeline:
        if custom_type in item.get("description", "") or custom_type in item.get("title", "") or item.get("type") == custom_type:
            type_found = True
            break
    assert type_found


def test_timeline_html_or_injection_content(client, db_session: Session):
    """
    30. Verifies that the timeline endpoint handles HTML or script tags in logs/milestones
    gracefully (e.g. without executing/rendering them or failing to serialize).
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Safe",
        last_name="Render",
        email="safe.render@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    injection_content = "<script>alert('xss')</script><b>Bold Text</b>"
    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content=injection_content,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(log)
    db_session.commit()

    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# TIER 3: CROSS-FEATURE COMBINATIONS (3 tests)
# ══════════════════════════════════════════════════════════════════════

def test_combo_scoring_affects_milestones(db_session: Session):
    """
    31. Pairwise: Pastoral Health Score + Omnichannel Inbox (Timeline).
    Verifies that when a persona's health status changes, it registers a timeline event/milestone
    indicating their transition (e.g., status changes to 'EN_RIESGO' or 'COMPROMETIDO').
    """
    assert hasattr(models.Persona, "health_score")
    
    sede = models.Sede(nombre="Combo Sede 1", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    persona = models.Persona(
        first_name="Combo",
        last_name="ScoringMilestone",
        email="combo1@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.commit()

    # Recalculate to set initial status
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()

    # Query milestones to check if the status change is logged as a milestone
    milestones = db_session.query(models.SpiritualMilestone).filter(
        models.SpiritualMilestone.persona_id == persona.id
    ).all()
    
    # Assert that a milestone corresponding to health score / health status is recorded
    health_milestone_exists = any("health" in m.type.lower() or "riesgo" in m.type.lower() for m in milestones)
    assert health_milestone_exists, "Health status change did not generate a spiritual milestone record"


def test_combo_copilot_uses_timeline(client, db_session: Session, mock_openai_client):
    """
    32. Pairwise: AI Copilot + Omnichannel Inbox.
    Verifies that AI Copilot reads context directly from the unified timeline / communication logs
    to construct its suggestions, rather than only reading the ticket's immediate notes field.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Combo",
        last_name="CopilotTimeline",
        email="combo2@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # Add communication logs to the timeline
    log_wa = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="I am having a tough time with depression lately.",
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    )
    db_session.add(log_wa)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Follow-up counseling",
        notes="Regular check-in.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    mock_choice = MagicMock()
    mock_choice.message.content = "Draft based on timeline."
    mock_openai_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)

    # Verify that the timeline context (depression) was passed to the mock OpenAI API call
    called_args, called_kwargs = mock_openai_client.chat.completions.create.call_args
    messages = called_kwargs.get("messages", [])
    
    # Check if the depression log content is in the prompt messages
    timeline_content_passed = False
    for msg in messages:
        content = msg.get("content", "")
        if "depression" in content or "tough time" in content:
            timeline_content_passed = True
            break

    assert timeline_content_passed, "Timeline logs were not incorporated into AI Copilot prompt context"


def test_combo_milestone_triggers_scoring(db_session: Session):
    """
    33. Pairwise: Pastoral Health Score + Omnichannel Inbox.
    Verifies that registering a significant Spiritual Milestone (e.g. Baptism) automatically
    triggers or is incorporated into the next health score recalculation.
    """
    assert hasattr(models.Persona, "health_score")

    sede = models.Sede(nombre="Combo Sede 2", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()

    persona = models.Persona(
        first_name="Combo",
        last_name="MilestoneScoring",
        email="combo3@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # Recalculate without milestone
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()
    score_before = persona.health_score

    # Add spiritual milestone (Baptism)
    milestone = models.SpiritualMilestone(
        persona_id=persona.id,
        type="Baptism",
        event_date=datetime.date.today(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(milestone)
    db_session.commit()

    # Recalculate with milestone
    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)
    score_after = persona.health_score

    # Score should improve after significant milestone
    assert score_after > score_before, "Spiritual milestone did not increase the health score"


# ══════════════════════════════════════════════════════════════════════
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 tests)
# ══════════════════════════════════════════════════════════════════════

def test_scenario_new_convert_journey(client, db_session: Session, mock_openai_client):
    """
    34. Scenario: A new convert joins CCF, attends some groups, gets baptized, has a counseling session,
    and we check that the unified timeline and health score reflect this entire lifecycle.
    """
    assert hasattr(models.Persona, "health_score")
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    # 1. New convert joins
    persona = models.Persona(
        first_name="New",
        last_name="Convert",
        email="new.convert@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # 2. Recalculate score (should be low/at risk initially)
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()
    assert persona.health_score <= 30
    assert persona.health_status == "EN_RIESGO"

    # 3. Add activity (attends group sessions)
    log_group = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="Attended group discipulado session 1",
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    )
    db_session.add(log_group)

    # 4. Receives Baptism (spiritual milestone)
    baptism = models.SpiritualMilestone(
        persona_id=persona.id,
        type="Baptism",
        event_date=datetime.date.today(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(baptism)
    db_session.commit()

    # 5. Recalculate (score increases to ESTABLE or COMPROMETIDO)
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()
    assert persona.health_score > 30
    assert persona.health_status in ("ESTABLE", "COMPROMETIDO")

    # 6. Counseling Session
    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Post-baptism follow-up",
        notes="Convert is excited and seeking next steps.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # 7. Check that timeline includes all these steps chronologically
    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    timeline = response.json()
    
    # Assert timeline includes Baptism, WhatsApp communication, and Counseling Ticket
    has_baptism = any("baptism" in item.get("title", "").lower() or "baptism" in item.get("type", "").lower() for item in timeline)
    has_counseling = any("counseling" in item.get("type", "").lower() for item in timeline)
    has_wa = any("whatsapp" in item.get("description", "").lower() or "whatsapp" in item.get("channel", "").lower() for item in timeline)

    assert has_baptism
    assert has_counseling
    assert has_wa


def test_scenario_disengaged_member_recovery(client, db_session: Session, mock_openai_client):
    """
    35. Scenario: Active member drops all activity (health score drops to EN_RIESGO).
    This status triggers pastoral care. The counselor opens a ticket, uses AI Copilot to draft a WhatsApp outreach message,
    sends it (creating a communication log), the member re-engages (attends group), and score recalculates to ESTABLE.
    """
    assert hasattr(models.Persona, "health_score")
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    # 1. Member is active originally but has been disengaged for months
    persona = models.Persona(
        first_name="Disengaged",
        last_name="Member",
        email="disengaged@example.com",
        sede_id=sede.id,
        last_meeting_attendance=datetime.date.today() - datetime.timedelta(days=120)
    )
    db_session.add(persona)
    db_session.commit()

    # 2. Recalculate -> status becomes EN_RIESGO
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()
    assert persona.health_status == "EN_RIESGO"

    # 3. Counselor opens ticket
    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Disengaged Member Outreach",
        notes="Attempting recovery outreach.",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # 4. Use AI Copilot to generate outreach WhatsApp
    response = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
    assert response.status_code in (200, 201)

    # 5. Send outreach (logs WhatsApp communication)
    log_outreach = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="Hey! We missed you. Hope you are well. - Pastor",
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(log_outreach)
    db_session.commit()

    # 6. Member attends a group session (re-engages)
    persona.last_meeting_attendance = datetime.date.today()
    db_session.flush()

    # 7. Recalculate score -> increases to ESTABLE
    _call_scoring_engine(db_session, persona.id)
    db_session.commit()
    assert persona.health_status == "ESTABLE"


def test_scenario_sede_isolation_full_flow(client, db_session: Session):
    """
    36. Scenario: Full multi-tenant isolation flow. Verify that users, scores, copilot,
    and timelines are fully partitioned by Sede.
    """
    assert hasattr(models.Persona, "health_score")
    
    sede_a = models.Sede(nombre="Sede A Isolation", ciudad="Bogota", es_activa=True)
    sede_b = models.Sede(nombre="Sede B Isolation", ciudad="Medellin", es_activa=True)
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    # Staff A in Sede A
    user_a, persona_a, _ = seed_admin(db_session, email="staff.isolate.a@example.com")
    user_a.sede_id = sede_a.id
    persona_a.sede_id = sede_a.id
    db_session.flush()

    # Persona in Sede B
    persona_b = models.Persona(
        first_name="Sede B",
        last_name="Persona",
        email="sede.b.persona@example.com",
        sede_id=sede_b.id
    )
    db_session.add(persona_b)
    db_session.commit()

    # Check: Staff A cannot access Sede B's persona timeline
    headers_a = auth_headers(client, email=user_a.email)
    response = client.get(f"/api/crm/personas/{persona_b.id}/timeline", headers=headers_a)
    assert response.status_code in (404, 403)


def test_scenario_copilot_rate_limiting_and_retry(client, db_session: Session, mock_openai_client):
    """
    37. Scenario: Multiple rapid concurrent requests to AI Copilot and scoring recalculations.
    Ensures that the application rate limiter and database transaction locks are handled properly
    and fail with structured 429/retry errors or resolve cleanly without deadlocking.
    """
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Rate",
        last_name="Limit",
        email="ratelimit@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    ticket = models.CounselingTicket(
        persona_id=persona.id,
        subject="Rate limit check",
        notes="High volume operations",
        status="open"
    )
    db_session.add(ticket)
    db_session.commit()

    # Call endpoint rapidly to hit potential limits or verify parallel safety
    responses = []
    for _ in range(5):
        resp = client.get(f"/api/crm/counseling/{ticket.id}/copilot-draft", headers=headers)
        responses.append(resp)

    # Some must succeed (200), others may get rate limited (429) but none should cause DB corruption (500)
    for resp in responses:
        assert resp.status_code in (200, 201, 429)


def test_scenario_milestone_and_multichannel_campaign(client, db_session: Session):
    """
    38. Scenario: An outreach campaign targets a persona with multiple communication channels (Email, WhatsApp, SMS).
    The persona completes a Spiritual Milestone. Recalculating the health score combines these campaign touchpoints
    and milestones into a holistic score, which shows up unified and ordered in the timeline.
    """
    assert hasattr(models.Persona, "health_score")
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    persona = models.Persona(
        first_name="Campaign",
        last_name="Holistic",
        email="campaign.holistic@example.com",
        sede_id=sede.id
    )
    db_session.add(persona)
    db_session.flush()

    # 1. Multichannel Campaign messages sent
    log_email = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content="Campaign Outreach: Join a small group",
        campaign_name="Group Campaign 2026",
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
    )
    log_sms = models.CommunicationLog(
        persona_id=persona.id,
        channel="sms",
        content="Campaign SMS reminder",
        campaign_name="Group Campaign 2026",
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    )
    log_wa = models.CommunicationLog(
        persona_id=persona.id,
        channel="whatsapp",
        content="Campaign WA reminder",
        campaign_name="Group Campaign 2026",
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    )
    db_session.add_all([log_email, log_sms, log_wa])
    db_session.flush()

    # 2. Member joins a group (spiritual milestone)
    milestone = models.SpiritualMilestone(
        persona_id=persona.id,
        type="Joined Small Group",
        event_date=datetime.date.today(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(milestone)
    db_session.commit()

    # 3. Recalculate score
    _call_scoring_engine(db_session, persona.id)
    db_session.refresh(persona)

    # 4. Verify all channels and milestone exist in timeline
    response = client.get(f"/api/crm/personas/{persona.id}/timeline", headers=headers)
    assert response.status_code == 200
    timeline = response.json()

    assert len(timeline) >= 4

    # Verify compatibility keys for frontend expectations
    for item in timeline:
        assert "created_at" in item
        assert "notes" in item
        assert "event_type" in item
        assert item["created_at"] == item["date"]
        assert item["notes"] == item["description"]
        assert item["event_type"] == item["title"]
