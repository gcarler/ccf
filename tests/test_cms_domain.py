import uuid

from backend import crud, models, schemas


def seed_user_and_persona(db_session):
    from tests.conftest import seed_admin
    user, persona, sede = seed_admin(db_session, email="cms-editor@example.com")
    return user, persona


def _seed_site(db_session):
    """Create a minimal CmsSite for v2 page tests."""
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=f"test_{uuid.uuid4().hex[:6]}",
        name="Test Site",
        base_path="/test",
        is_active=True,
    )
    db_session.add(site)
    db_session.flush()
    return site


def test_cms_page_versioning(db_session):
    """CMS v2 page versioning: create page → update → snapshot version."""
    from backend.crud.cms import create_cms_page_version
    from backend.schemas.cms import CmsPageCreate, CmsPageUpdate

    site = _seed_site(db_session)
    page = crud.create_cms_page(
        db_session, site.id,
        CmsPageCreate(slug="landing", title="Original", status="draft"),
        user_id=None,
    )
    assert page is not None

    # Update the page title
    updated = crud.update_cms_page(
        db_session, page, CmsPageUpdate(title="Actualizado"), user_id=None,
    )
    assert updated.title == "Actualizado"

    # Create a version snapshot
    version = create_cms_page_version(db_session, page, user_id=None)
    assert version is not None
    assert version.page_id == page.id

    versions, total = crud.list_cms_page_versions(db_session, page.id)
    assert total >= 1
    assert len(versions) >= 1


def test_create_cms_media_item(db_session):
    """CMS v2 media creation replaces legacy create_media_asset."""
    user, persona = seed_user_and_persona(db_session)
    item = crud.create_cms_media_item(
        db_session,
        url="/static/image.png",
        alt_text="Test image",
        section="gallery",
        tags=[],
        created_by=persona.id,
        filename="image.png",
        mime_type="image/png",
        file_size=1234,
        actor_user_id=user.id,
    )
    assert item.id is not None


def test_testimonial_accepts_explicit_author_persona_id(db_session):
    user, persona = seed_user_and_persona(db_session)

    testimonial = crud.create_testimonial(
        db_session,
        schemas.TestimonialCreate(
            content="Testimonio UUID",
            emotion="Gratitud",
            author_persona_id=str(persona.id),
        ),
        actor_user_id=user.id,
    )

    assert testimonial.author_persona_id == persona.id
