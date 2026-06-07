from backend import crud, models, schemas


def seed_user_and_persona(db_session):
    user = models.User(
        username="cms-editor",
        email="cms-editor@example.com",
        password_hash="x",
        role="editor",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    persona = models.Persona(
        user_id=user.id,
        first_name="Editor",
        last_name="CMS",
        email=user.email,
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return user, persona


def test_page_content_versioning(db_session):
    page = models.PageContent(page_key="landing", title="Original", content="Hola")
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    crud.update_page_content(
        db_session,
        "landing",
        schemas.PageContentUpdate(title="Actualizado", content="Nuevo"),
    )

    versions = crud.get_page_content_versions(db_session, "landing")
    assert len(versions) == 1
    assert versions[0].title == "Original"


def test_increment_content_metric(db_session):
    metric = crud.increment_content_metric(db_session, "announcement", 1)
    assert metric.value == 1
    metric = crud.increment_content_metric(db_session, "announcement", 1, amount=3)
    assert metric.value == 4


def test_create_media_asset(db_session):
    asset = crud.create_media_asset(
        db_session,
        filename="image.png",
        url="/static/image.png",
        mime_type="image/png",
        size_bytes=1234,
    )
    assert asset.id is not None


def test_testimonial_accepts_explicit_author_persona_id(db_session):
    _, persona = seed_user_and_persona(db_session)

    testimonial = crud.create_testimonial(
        db_session,
        schemas.TestimonialCreate(
            content="Testimonio UUID",
            emotion="Gratitud",
            author_persona_id=str(persona.id),
        ),
    )

    assert testimonial.author_id is None
    assert testimonial.author_persona_id == persona.id
