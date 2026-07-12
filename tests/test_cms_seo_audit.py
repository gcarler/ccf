"""SEO Audit endpoint tests — CCF CMS (faro global).

Verifies:
  - 404 for unknown site.
  - 403 for users sin CMS_EDITOR_ROLES.
  - Empty site → score 0, sin findings.
  - Página publicada perfecta → score 100, sin findings.
  - Cada check aislado devuelve su hallazgo + resta puntos correctos.
  - Imagen con media_id sin alt → image_missing_alt error.
  - image_url sin alt → image_url_missing_alt error.
  - min_score filtra correctamente.
  - status filtra correctamente.
  - Helpers puros (group_sections_by_page, build_media_alt_lookup) funcionan.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models

# Gate 6 anti-drift: SeoAudit helpers (incluyendo constantes de peso) viven
# en ``_shared.py`` desde el merge de ``seo_audit.py``. Los tests consumen
# la API pública de ese módulo directamente.
from backend.api._cms_helpers._shared import (
    META_DESC_WEIGHT,
    TITLE_LEN_WEIGHT,
    audit_pages,
    build_media_alt_lookup,
    collect_section_media_ids,
    group_sections_by_page,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

GOOD_DESC = (
    "Una descripción pastoral bien redactada con suficiente contexto y palabras clave relevantes para SEO moderno."
)
GOOD_TITLE = "Encuentro Pastoral de Avivamiento Semanal"
GOOD_OG = "https://cdn.example.com/og.png"


def _seed_site(db, key="ccf", name="CCF Test", base_path="/"):
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key=key,
        name=name,
        base_path=base_path,
        is_active=True,
    )
    db.add(site)
    db.flush()
    return site


def _seed_sede(db):
    """Crea una Sede válida (NOT NULL en cms_media_items)."""
    sede = models.Sede(
        id=_uuid.uuid4(),
        nombre="Sede Audit Test",
        ciudad="Bogota",
        es_activa=True,
    )
    db.add(sede)
    db.flush()
    return sede


def _make_page(
    db,
    site_id,
    *,
    slug,
    title,
    status="published",
    seo=None,
    sections=(),
):
    page = models.CmsPage(
        id=_uuid.uuid4(),
        site_id=site_id,
        slug=slug,
        title=title,
        status=status,
        seo_json=seo or {},
    )
    db.add(page)
    db.flush()
    for idx, (sec_type, props) in enumerate(sections):
        db.add(
            models.CmsSection(
                id=_uuid.uuid4(),
                page_id=page.id,
                section_key=f"sec-{slug}-{idx}",
                type=sec_type,
                props_json=props,
                sort_order=idx,
                is_visible=True,
                status="active",
            )
        )
    db.flush()
    return page


# ── Fixtures / sanity ────────────────────────────────────────────────────


def test_audit_empty_site_returns_zero(client, db_session):
    seed_admin(db_session, email="seo-empty@example.com")
    _seed_site(db_session)
    headers = auth_headers(client, email="seo-empty@example.com")
    resp = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["site_key"] == "ccf"
    assert body["aggregate"]["total_pages"] == 0
    assert body["aggregate"]["average_score"] == 0
    assert body["aggregate"]["pages_with_errors"] == 0
    assert body["aggregate"]["critical_issues"] == 0
    assert body["pages"] == []


def test_readiness_empty_site_flags_publication_contract_gaps(client, db_session):
    seed_admin(db_session, email="ready-empty@example.com")
    _seed_site(db_session)
    db_session.commit()
    headers = auth_headers(client, email="ready-empty@example.com")

    resp = client.get("/api/cms/v2/sites/ccf/readiness", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["site_key"] == "ccf"
    assert body["score"] < 100
    codes = {issue["code"] for issue in body["issues"]}
    assert "no_published_pages" in codes
    assert "no_active_theme" in codes
    assert any(cap["key"] == "pages" for cap in body["capabilities"])
    assert any(metric["key"] == "published_pages" for metric in body["metrics"])


def test_readiness_complete_site_scores_ready(client, db_session):
    seed_admin(db_session, email="ready-good@example.com")
    site = _seed_site(db_session)
    page = _make_page(
        db_session,
        site.id,
        slug="home",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=[("rich_text", {"body": " ".join(["contenido pastoral"] * 40)})],
    )
    version = models.CmsPageVersion(
        id=_uuid.uuid4(),
        page_id=page.id,
        version_number=1,
        snapshot_json={"page": {"slug": page.slug}, "sections": []},
    )
    db_session.add(version)
    db_session.flush()
    page.published_version_id = version.id
    theme = models.CmsTheme(
        id=_uuid.uuid4(),
        site_id=site.id,
        name="Tema activo",
        tokens_json={"primary": "#2563eb"},
        is_active=True,
        status="active",
    )
    menu = models.CmsMenu(
        id=_uuid.uuid4(),
        site_id=site.id,
        menu_key="main",
        name="Principal",
        is_active=True,
    )
    db_session.add_all([theme, menu])
    db_session.flush()
    db_session.add(
        models.CmsMenuItem(
            id=_uuid.uuid4(),
            menu_id=menu.id,
            label="Inicio",
            href="/",
            sort_order=0,
        )
    )
    db_session.commit()
    headers = auth_headers(client, email="ready-good@example.com")

    resp = client.get("/api/cms/v2/sites/ccf/readiness", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] == 100
    assert body["issues"] == []
    statuses = {cap["key"]: cap["status"] for cap in body["capabilities"]}
    assert statuses["pages"] == "ready"
    assert statuses["themes"] == "ready"
    assert statuses["menus"] == "ready"


def test_audit_unknown_site_returns_404(client, db_session):
    seed_admin(db_session, email="seo-nofound@example.com")
    headers = auth_headers(client, email="seo-nofound@example.com")
    resp = client.get(
        "/api/cms/v2/site_unknown/seo-audit".replace("site_unknown", "no-existe"),
        headers=headers,
    )
    assert resp.status_code == 404, resp.text


def test_audit_perfect_published_page_scores_100(client, db_session):
    seed_admin(db_session, email="seo-good@example.com")
    site = _seed_site(db_session)
    rich_text_body = " ".join(["contenido pastoral rico para SEO"] * 30)
    _make_page(
        db_session,
        site.id,
        slug="sobre-nosotros",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=[
            (
                "hero",
                {
                    "title": "Bienvenidos a nuestra iglesia",
                    "subtitle": "Un llamado al servicio y la comunidad",
                    "image_url": "https://cdn.example.com/hero.png",
                    "alt": "Familia congregada en el templo",
                },
            ),
            (
                "rich_text",
                {"body": rich_text_body},
            ),
        ],
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-good@example.com")
    resp = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["aggregate"]["average_score"] == 100
    assert body["aggregate"]["total_pages"] == 1
    assert body["pages"][0]["score"] == 100
    assert body["pages"][0]["findings"] == []


# ── Per-check isolation ──────────────────────────────────────────────────


def test_audit_flags_missing_meta_description(client, db_session):
    seed_admin(db_session, email="seo-nometa@example.com")
    site = _seed_site(db_session)
    body_text_a = " ".join(["párrafo pastoral con detalle suficiente"] * 30)
    body_text_b = " ".join(["segunda sección pastoral completa"] * 30)
    _make_page(
        db_session,
        site.id,
        slug="sin-meta",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_image": GOOD_OG},
        sections=[
            ("rich_text", {"body": body_text_a}),
            ("rich_text", {"body": body_text_b}),
        ],
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-nometa@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page = body["pages"][0]
    codes = {f["code"]: f for f in page["findings"]}
    assert "meta_description_missing" in codes
    assert codes["meta_description_missing"]["impact_points"] == META_DESC_WEIGHT
    # Sin otras penalidades (meta aislado): ninguna más debería aparecer.
    assert page["score"] == 100 - META_DESC_WEIGHT


def test_audit_flags_short_title(client, db_session):
    seed_admin(db_session, email="seo-short-title@example.com")
    site = _seed_site(db_session)
    _make_page(
        db_session,
        site.id,
        slug="cortito",
        title="X",
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=[("rich_text", {"body": " ".join(["t"] * 30)})],
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-short-title@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page = body["pages"][0]
    assert any(
        f["code"] == "title_length_out_of_range" and f["impact_points"] == TITLE_LEN_WEIGHT for f in page["findings"]
    )


def test_audit_flags_noindex_on_published(client, db_session):
    seed_admin(db_session, email="seo-noindex@example.com")
    site = _seed_site(db_session)
    _make_page(
        db_session,
        site.id,
        slug="privada",
        title=GOOD_TITLE,
        status="published",
        seo={
            "meta_description": GOOD_DESC,
            "meta_image": GOOD_OG,
            "robots_meta": "noindex, nofollow",
        },
        sections=[("rich_text", {"body": " ".join(["x"] * 30)})],
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-noindex@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page = body["pages"][0]
    codes = {f["code"] for f in page["findings"]}
    assert "noindex_on_published" in codes


def test_audit_flags_no_visible_sections(client, db_session):
    seed_admin(db_session, email="seo-emptybody@example.com")
    site = _seed_site(db_session)
    _make_page(
        db_session,
        site.id,
        slug="sin-cuerpo",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=(),
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-emptybody@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page = body["pages"][0]
    codes = {f["code"] for f in page["findings"]}
    assert "no_visible_sections" in codes


def test_audit_flags_missing_alt_on_referenced_image(client, db_session):
    seed_admin(db_session, email="seo-alt-client@example.com")
    site = _seed_site(db_session)
    sede = _seed_sede(db_session)
    creator = models.Persona(
        id=_uuid.uuid4(),
        first_name="Creador",
        last_name="Seo",
        email=f"creator-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede.id,
    )
    db_session.add(creator)
    db_session.flush()

    image_section_id = _uuid.uuid4()
    page_id = _uuid.uuid4()

    media = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/hero.png",
        section="hero",
        alt_text=None,  # missing alt on purpose
        created_by_persona_id=creator.id,
        sede_id=sede.id,  # NOT NULL en cms_media_items
    )
    db_session.add(media)
    db_session.flush()

    body_text = " ".join(["párrafo pastoral aquí"] * 30)

    page = models.CmsPage(
        id=page_id,
        site_id=site.id,
        slug="galeria",
        title=GOOD_TITLE,
        status="published",
        seo_json={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
    )
    db_session.add(page)
    db_session.flush()
    db_session.add(
        models.CmsSection(
            id=image_section_id,
            page_id=page_id,
            section_key="hero-1",
            type="hero",
            props_json={"media_id": str(media.id)},
            sort_order=0,
            is_visible=True,
            status="active",
        )
    )
    db_session.add(
        models.CmsSection(
            id=_uuid.uuid4(),
            page_id=page_id,
            section_key="body-1",
            type="rich_text",
            props_json={"body": body_text},
            sort_order=1,
            is_visible=True,
            status="active",
        )
    )
    db_session.flush()
    db_session.commit()

    headers = auth_headers(client, email="seo-alt-client@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page_audit = body["pages"][0]
    codes = {f["code"] for f in page_audit["findings"]}
    assert "image_missing_alt" in codes

    finding = next(f for f in page_audit["findings"] if f["code"] == "image_missing_alt")
    assert finding["section_id"] == str(image_section_id)


def test_audit_flags_missing_alt_for_image_url(client, db_session):
    seed_admin(db_session, email="seo-alt-url@example.com")
    site = _seed_site(db_session)
    section_id = _uuid.uuid4()
    page = models.CmsPage(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="sin-alt-url",
        title=GOOD_TITLE,
        status="published",
        seo_json={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
    )
    db_session.add(page)
    db_session.flush()
    db_session.add(
        models.CmsSection(
            id=section_id,
            page_id=page.id,
            section_key="hero-1",
            type="hero",
            props_json={"image_url": "https://cdn.example.com/x.png"},
            sort_order=0,
            is_visible=True,
            status="active",
        )
    )
    db_session.commit()

    headers = auth_headers(client, email="seo-alt-url@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers).json()
    page_audit = body["pages"][0]
    finding = next(f for f in page_audit["findings"] if f["code"] == "image_url_missing_alt")
    assert finding["section_id"] == str(section_id)


# ── Filters ─────────────────────────────────────────────────────────────


def test_audit_min_score_filter_excludes_low_pages(client, db_session):
    seed_admin(db_session, email="seo-filter@example.com")
    site = _seed_site(db_session)
    _make_page(
        db_session,
        site.id,
        slug="buena",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=[("rich_text", {"body": " ".join(["t"] * 30)})],
    )
    _make_page(
        db_session,
        site.id,
        slug="mala",
        title="X",
        status="published",
        seo={"robots_meta": "noindex, nofollow"},
        sections=(),
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-filter@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit?min_score=80", headers=headers).json()
    slugs = [p["slug"] for p in body["pages"]]
    assert "buena" in slugs
    assert "mala" not in slugs


def test_audit_blocks_non_editor_role(client, db_session):
    """Un usuario con rol de plataforma sin permisos editoriales recibe 403.

    Contrato: el endpoint requiere CMS_EDITOR_ROLES (admin,
    coordinador, docente, pastor). Un LECTOR no debe poder auditar.
    Cubre la rama de ``_assert_role`` dentro de ``seo_audit``.
    """
    seed_admin(db_session, email="seo-actor@example.com")
    _seed_site(db_session)
    seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="seo-lector@example.com",
        password="testpass123",
    )
    headers = auth_headers(client, email="seo-lector@example.com")
    resp = client.get("/api/cms/v2/sites/ccf/seo-audit", headers=headers)
    assert (
        resp.status_code == 403
    ), f"Leak: LECTOR pudo llamar al audit endpoint (status {resp.status_code}): {resp.text}"


def test_audit_status_filter_excludes_draft(client, db_session):
    seed_admin(db_session, email="seo-status@example.com")
    site = _seed_site(db_session)
    _make_page(db_session, site.id, slug="draft-one", title=GOOD_TITLE, status="draft")
    _make_page(
        db_session,
        site.id,
        slug="published-one",
        title=GOOD_TITLE,
        status="published",
        seo={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
        sections=[("rich_text", {"body": " ".join(["t"] * 30)})],
    )
    db_session.commit()
    headers = auth_headers(client, email="seo-status@example.com")
    body = client.get("/api/cms/v2/sites/ccf/seo-audit?status=published", headers=headers).json()
    slugs = [p["slug"] for p in body["pages"]]
    assert slugs == ["published-one"]


# ── Pure-helper unit tests (no HTTP) ─────────────────────────────────────


def test_helper_group_sections_by_page_groups_correctly(db_session):
    page_a = models.CmsPage(id=_uuid.uuid4(), site_id=_uuid.uuid4(), slug="a", title="A", status="published")
    page_b = models.CmsPage(id=_uuid.uuid4(), site_id=_uuid.uuid4(), slug="b", title="B", status="published")
    db_session.add_all([page_a, page_b])
    db_session.flush()

    sec_aa = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page_a.id,
        section_key="s",
        type="rich_text",
        props_json={"body": "hola"},
        sort_order=0,
        is_visible=True,
    )
    sec_ba = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page_b.id,
        section_key="s",
        type="rich_text",
        props_json={"body": "hola"},
        sort_order=0,
        is_visible=True,
    )
    db_session.add_all([sec_aa, sec_ba])
    db_session.flush()

    grouped = group_sections_by_page([sec_aa, sec_ba])
    assert grouped[page_a.id] == [sec_aa]
    assert grouped[page_b.id] == [sec_ba]


def test_helper_collect_media_ids_detects_referenced(db_session):
    page = models.CmsPage(id=_uuid.uuid4(), site_id=_uuid.uuid4(), slug="a", title="A", status="published")
    media_a = _uuid.uuid4()
    media_b = _uuid.uuid4()
    sec_1 = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page.id,
        section_key="a",
        type="hero",
        props_json={"media_id": str(media_a), "image_alt": ""},
        sort_order=0,
        is_visible=True,
    )
    sec_2 = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page.id,
        section_key="b",
        type="cards",
        props_json={"media_ids": [str(media_b), "not-a-uuid"]},
        sort_order=1,
        is_visible=True,
    )
    db_session.add_all([page, sec_1, sec_2])
    db_session.flush()
    ids = collect_section_media_ids([sec_1, sec_2])
    assert ids == {str(media_a), str(media_b)}


def test_helper_collect_media_ids_filters_invalid_uuids():
    """Los IDs no-UUID se descartan silenciosamente."""
    fake_section = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=_uuid.uuid4(),
        section_key="x",
        type="hero",
        props_json={"media_id": "esto-no-es-uuid"},
        sort_order=0,
        is_visible=True,
    )
    assert collect_section_media_ids([fake_section]) == set()


def test_helper_build_media_alt_lookup_returns_none_when_alternative_is_missing(db_session):
    sede = _seed_sede(db_session)
    creator = models.Persona(
        id=_uuid.uuid4(),
        first_name="C",
        last_name="Alt",
        email=f"c-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede.id,
    )
    db_session.add(creator)
    db_session.flush()
    media_id = _uuid.uuid4()
    db_session.add(
        models.CmsMediaItem(
            id=media_id,
            url="https://x/y.png",
            section="hero",
            alt_text=None,
            created_by_persona_id=creator.id,
            sede_id=sede.id,
        )
    )
    db_session.flush()
    lookup = build_media_alt_lookup(db_session, [str(media_id)])
    assert lookup == {str(media_id): None}


def test_helper_audit_pages_returns_aggregate_correctly(db_session):
    site = _seed_site(db_session)
    page_published = models.CmsPage(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="x",
        title=GOOD_TITLE,
        status="published",
        seo_json={"meta_description": GOOD_DESC, "meta_image": GOOD_OG},
    )
    page_draft = models.CmsPage(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="y",
        title="X",
        status="draft",
        seo_json={},
    )
    db_session.add_all([page_published, page_draft])
    db_session.flush()
    # Published: 2 secciones visibles con suficiente texto para evitar TODOS
    # los findings (no_visible_sections, thin_content_sections, thin_content_text).
    rich_body_a = " ".join(["contenido pastoral con densidad suficiente"] * 30)
    rich_body_b = " ".join(["segunda sección pastoral con cuerpo suficiente"] * 30)
    sections_rows = [
        models.CmsSection(
            id=_uuid.uuid4(),
            page_id=page_published.id,
            section_key="body-1",
            type="rich_text",
            props_json={"body": rich_body_a},
            sort_order=0,
            is_visible=True,
            status="active",
        ),
        models.CmsSection(
            id=_uuid.uuid4(),
            page_id=page_published.id,
            section_key="body-2",
            type="rich_text",
            props_json={"body": rich_body_b},
            sort_order=1,
            is_visible=True,
            status="active",
        ),
    ]
    db_session.add_all(sections_rows)
    db_session.flush()
    grouped = group_sections_by_page(sections_rows)
    audits, aggregate = audit_pages(
        [page_published, page_draft],
        grouped,
        {},
    )
    assert aggregate.total_pages == 2
    # Published page: full bonus. Draft: penalized for short title and missing meta
    assert any(a.slug == "x" and a.score == 100 for a in audits)
    assert any(a.slug == "y" and a.score < 100 for a in audits)
