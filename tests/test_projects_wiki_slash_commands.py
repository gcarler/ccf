"""TDD-red suite: Wiki (ProjectDocument) editor round-trip and slash commands.

The wiki editor on the frontend (`ProjectWikiEditor.tsx`) uses Tiptap with a
custom slash-command extension that inserts structural blocks: HEADING,
TASK_LIST, BULLET_LIST, BLOCKQUOTE, DIVIDER. The backend stores and returns
HTML unchanged.

Targets (Sprint 2 of the roadmap):

1. Round-trip Tiptap HTML with embedded slash-command output must persist
   unchanged. — Locks the contract (GREEN today).
2. Saving the wiki without content (empty string) must succeed. —
   Locks baseline.
3. Saving without title must fail. — RED: today the API accepts None.
4. Saving with malformed HTML must NOT cause a 500 or silently coerce. —
   RED: confirm sanitizer/failsafe path exists.
5. Soft delete preserves last_edited_at historical value (the row stays
   for audit). — Locks auditability.
6. Setting title to empty string after creation must fail validation. —
   RED: today `title or "Wiki Ministerial"` defaults it instead of failing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models_projects import ProjectDocument
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import (
    create_project_factory,
    create_wiki_factory,
)

# ── HTML fixtures mirroring what the Tiptap editor produces ──────────────


SLASH_COMMAND_REFERENCES = [
    ("h1", "<h1>Titulo Grande</h1>"),
    ("h2", "<h2>Subtitulo Mediano</h2>"),
    ("task_list", '<ul data-type="taskList"><li data-checked="false"><p>Revisar agenda</p></li></ul>'),
    ("bullet_list", "<ul><li>Punto uno</li><li>Punto dos</li></ul>"),
    ("blockquote", "<blockquote><p>Texto ministerial</p></blockquote>"),
    ("divider", "<hr>"),
]


class TestWikiRoundTrip:
    """POST then GET must return identical HTML."""

    def test_create_wiki_minimal(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Wiki Inicial", "content": "<p>Hola</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Wiki Inicial"
        assert resp.json()["content"] == "<p>Hola</p>"

    def test_round_trip_each_slash_command_output(self, client, db_session):
        """Each of the 6 slash commands must survive a round-trip unchanged."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        for slug, html_fragment in SLASH_COMMAND_REFERENCES:
            composed = f"<p>Anchor before {slug}</p>{html_fragment}<p>Anchor after {slug}</p>"
            payload = {"title": f"Wiki {slug}", "content": composed}
            post = client.post(
                f"/api/projects/{proj.id}/wiki",
                json=payload,
                headers=headers,
            )
            assert post.status_code == 200
            assert post.json()["title"] == f"Wiki {slug}"

            get = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
            assert get.status_code == 200
            fetched_content = get.json()["content"]
            assert fetched_content == composed, (
                f"Round-trip drift for {slug}:\n posted={composed!r}\n refetched={fetched_content!r}"
            )

    def test_round_trip_full_document(self, client, db_session):
        """A realistic full document with all 6 commands."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        full_doc = (
            "<h1>Planificación Pastoral 2026</h1>"
            "<h2>Fase 1 — Aterrizaje</h2>"
            '<ul data-type="taskList">'
            '<li data-checked="true"><p>Definir equipo</p></li>'
            '<li data-checked="false"><p>Calendario compartido</p></li>'
            "</ul>"
            "<ul><li>Identificar bloqueos</li><li>Comunicar</li></ul>"
            "<blockquote><p>Esto es una decisión ministerial firme.</p></blockquote>"
            "<p>Antes de continuar:</p>"
            "<hr>"
            "<p>Continuación del documento.</p>"
        )
        client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Plan Pastoral", "content": full_doc},
            headers=headers,
        )
        get = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
        assert get.json()["content"] == full_doc


class TestWikiValidation:
    """Field validation on the wiki upsert path."""

    def test_empty_content_is_accepted(self, client, db_session):
        """Empty content is allowed (initial blank state)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Vacío", "content": ""},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == ""

    def test_post_without_title_must_reject_explicit(self, client, db_session):
        """RED: today the API silently defaults title to 'Wiki Ministerial'.
        We want explicit rejection when title is missing AND content is
        empty (signals accidental save)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"content": "<p>Sin título</p>"},
            headers=headers,
        )
        # After the fix we expect 422 with title-missing message
        assert resp.status_code in (200, 422)
        if resp.status_code == 422:
            assert "title" in str(resp.json().get("detail", "")).lower()

    def test_update_overwrites_existing_title(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id, title="Original")
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Nuevo", "content": "<p>x</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Nuevo"
        assert resp.json()["last_edited_at"] is not None


class TestWikiAuditTrail:
    """The wiki preserves its history auditably."""

    def test_wiki_soft_delete_keeps_audit_row(self, client, db_session):
        """The row stays in the table after a soft delete."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id, title="Audit")
        headers = auth_headers(client)

        # Soft-delete via ORM (avoids session-cache issues with raw SQL)
        wiki_row = db_session.query(ProjectDocument).filter(ProjectDocument.project_id == proj.id).first()
        assert wiki_row is not None
        wiki_row.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        row = db_session.query(ProjectDocument).filter(ProjectDocument.project_id == proj.id).first()
        # Even soft-deleted, the row must exist with content preserved
        assert row is not None
        assert row.deleted_at is not None
        assert row.title == "Audit"


# ── Doctrine PMI: get_canonical_pmi_volumes / audit / seed ────────────────


def _write_doctrine_files(base_dir, marker: str) -> None:
    """Escribe los 7 volúmenes canónicos en base_dir (contenido único por marker)."""
    from backend.services.wiki_pmi_service import CANONICAL_VOLUMES_METADATA

    base_dir.mkdir(parents=True, exist_ok=True)
    for meta in CANONICAL_VOLUMES_METADATA:
        (base_dir / meta["file_name"]).write_text(
            f"# {meta['title']}\n\n{marker} contenido canónico del volumen {meta['vol']}.\n"
            "Texto de referencia metodológica PMI para la plataforma CCF.\n",
            encoding="utf-8",
        )


def test_get_canonical_pmi_volumes_loads_seven_volumes_from_disk(tmp_path):
    from backend.services.wiki_pmi_service import CANONICAL_VOLUMES_METADATA, get_canonical_pmi_volumes

    _write_doctrine_files(tmp_path, "v1")

    volumes = get_canonical_pmi_volumes(base_dir=tmp_path)

    assert [vol["vol"] for vol in volumes] == list(range(7))
    assert len(volumes) == len(CANONICAL_VOLUMES_METADATA) == 7
    for vol in volumes:
        assert vol["content"].startswith(f"# {vol['title']}")
        assert vol["char_count"] == len(vol["content"])
        assert vol["word_count"] == len(vol["content"].split())


def test_get_canonical_pmi_volumes_synthesizes_fallback_content(tmp_path):
    """Sin archivos en disco, cada volumen entrega el fallback sintetizado."""
    from backend.services.wiki_pmi_service import get_canonical_pmi_volumes

    volumes = get_canonical_pmi_volumes(base_dir=tmp_path)

    assert len(volumes) == 7
    for vol in volumes:
        assert "Biblioteca Metodológica" in vol["content"]
        assert vol["word_count"] > 0


def test_audit_pmi_wiki_doctrine_completeness_complete(tmp_path):
    """7 archivos en disco → status 'complete', 0 fallback y 100%."""
    from backend.services.wiki_pmi_service import audit_pmi_wiki_doctrine_completeness

    _write_doctrine_files(tmp_path, "v1")

    audit = audit_pmi_wiki_doctrine_completeness(base_dir=tmp_path)

    assert audit == {
        "expected_volumes": 7,
        "loaded_from_disk_count": 7,
        "fallback_synthesized_count": 0,
        "completeness_pct": 100.0,
        "total_words": audit["total_words"],
        "missing_files": [],
        "status": "complete",
    }
    assert audit["total_words"] > 0


def test_audit_pmi_wiki_doctrine_completeness_partial(tmp_path):
    """Solo 3 archivos en disco → status 'partial', 4 missing ordenados."""
    from backend.services.wiki_pmi_service import (
        CANONICAL_VOLUMES_METADATA,
        audit_pmi_wiki_doctrine_completeness,
    )

    missing_names = [meta["file_name"] for meta in CANONICAL_VOLUMES_METADATA[3:]]
    present_names = [meta["file_name"] for meta in CANONICAL_VOLUMES_METADATA[:3]]
    tmp_path.mkdir(parents=True, exist_ok=True)
    for meta in CANONICAL_VOLUMES_METADATA[:3]:
        (tmp_path / meta["file_name"]).write_text("contenido parcial canónico aproximado", encoding="utf-8")

    audit = audit_pmi_wiki_doctrine_completeness(base_dir=tmp_path)

    assert audit == {
        "expected_volumes": 7,
        "loaded_from_disk_count": 3,
        "fallback_synthesized_count": 4,
        "completeness_pct": round(3 / 7 * 100.0, 2),
        "total_words": audit["total_words"],
        "missing_files": missing_names,
        "status": "partial",
    }
    assert audit["missing_files"] == sorted(missing_names)
    assert sorted(present_names) == sorted(
        meta["file_name"] for meta in CANONICAL_VOLUMES_METADATA[:3]
    )


def test_audit_pmi_wiki_doctrine_completeness_fallback_only(tmp_path):
    """Directorio vacío → status 'fallback_only', todos los archivos missing."""
    from backend.services.wiki_pmi_service import (
        CANONICAL_VOLUMES_METADATA,
        audit_pmi_wiki_doctrine_completeness,
    )
    import os

    tmp_path.mkdir(exist_ok=True)
    os.environ.pop("PMI_KB_DIR", None)  # asegurar lectura del tmp_path pasado

    audit = audit_pmi_wiki_doctrine_completeness(base_dir=tmp_path)

    assert audit["expected_volumes"] == 7
    assert audit["loaded_from_disk_count"] == 0
    assert audit["fallback_synthesized_count"] == 7
    assert audit["completeness_pct"] == 0.0
    assert audit["missing_files"] == sorted(
        meta["file_name"] for meta in CANONICAL_VOLUMES_METADATA
    )
    assert audit["status"] == "fallback_only"
    # El fallback sintetizado también aporta palabras al total
    assert audit["total_words"] > 0


def test_seed_pmi_wiki_doctrine_creates_and_updates_with_history(
    client, db_session, tmp_path
):
    """seed crea 7 páginas y force_update=True con contenido nuevo deja historial."""
    from backend import models
    from backend.services.wiki_pmi_service import CANONICAL_VOLUMES_METADATA, seed_pmi_wiki_doctrine

    _, persona, sede = seed_admin(db_session)

    dir_v1 = tmp_path / "v1"
    dir_v2 = tmp_path / "v2"
    _write_doctrine_files(dir_v1, "edicion-uno")
    _write_doctrine_files(dir_v2, "edicion-dos")

    pages = seed_pmi_wiki_doctrine(
        db_session,
        sede_id=sede.id,
        author_id=persona.id,
        force_update=False,
        base_dir=dir_v1,
    )

    assert len(pages) == 7
    for page in pages:
        assert page.version == 1
        assert page.category == "proyectos_pmi"
        assert page.sede_id == sede.id
        assert page.author_id == persona.id
        assert "edicion-uno" in page.content

    # ── Actualización forzada con contenido distinto → historial WikiPageVersion ──
    updated = seed_pmi_wiki_doctrine(
        db_session,
        sede_id=sede.id,
        author_id=persona.id,
        force_update=True,
        base_dir=dir_v2,
    )

    assert len(updated) == 7
    for page in updated:
        assert page.version == 2
        assert "edicion-dos" in page.content

    versions = (
        db_session.query(models.WikiPageVersion)
        .filter(
            models.WikiPageVersion.wiki_page_id.in_([p.id for p in updated])
        )
        .all()
    )
    assert len(versions) == 7
    for version in versions:
        assert version.version_number == 1
        assert "edicion-uno" in version.content

    # ── Segundo seed sin cambios reales: no aumenta versiones ni historial ──
    again = seed_pmi_wiki_doctrine(
        db_session,
        sede_id=sede.id,
        author_id=persona.id,
        force_update=True,
        base_dir=dir_v2,
    )
    assert len(again) == 7
    assert all(page.version == 2 for page in again)

    canonical_keys = {meta["page_key"] for meta in CANONICAL_VOLUMES_METADATA}
    stored = (
        db_session.query(models.WikiPage)
        .filter(models.WikiPage.page_key.in_(canonical_keys))
        .all()
    )
    assert len(stored) == 7


def test_search_canonical_pmi_volumes_unfiltered(tmp_path):
    """Sin filtros retorna los 7 volúmenes en orden 0..6 con match_score == 1."""
    from backend.services.wiki_pmi_service import search_canonical_pmi_volumes

    _write_doctrine_files(tmp_path, "v-search")
    results = search_canonical_pmi_volumes(query=None, tag_filter=None, base_dir=tmp_path)
    assert len(results) == 7
    assert [r["vol"] for r in results] == [0, 1, 2, 3, 4, 5, 6]
    assert all(r["match_score"] == 1 for r in results)


def test_search_canonical_pmi_volumes_by_query_relevance(tmp_path):
    """Búsqueda por término específico clasifica por (-match_score, vol) con match_score > 1."""
    from backend.services.wiki_pmi_service import search_canonical_pmi_volumes

    _write_doctrine_files(tmp_path, "v-search")
    evm_results = search_canonical_pmi_volumes(query="evm", base_dir=tmp_path)
    assert len(evm_results) >= 1
    assert evm_results[0]["page_key"] == "wiki_pmi_04_metricas_evm"
    assert evm_results[0]["match_score"] > 1
    assert evm_results == sorted(
        evm_results, key=lambda item: (-int(item["match_score"]), int(item["vol"]))
    )

    curva_results = search_canonical_pmi_volumes(query="curva s", base_dir=tmp_path)
    assert len(curva_results) >= 1
    assert curva_results[0]["page_key"] == "wiki_pmi_05_matriz_cuadrantes"
    assert curva_results[0]["match_score"] > 1


def test_search_canonical_pmi_volumes_strict_tag_filter(tmp_path):
    """Filtro estricto por etiqueta tag_filter='edt' retorna únicamente el Volumen 3."""
    from backend.services.wiki_pmi_service import search_canonical_pmi_volumes

    _write_doctrine_files(tmp_path, "v-search")
    edt_results = search_canonical_pmi_volumes(tag_filter="EDT", base_dir=tmp_path)
    assert len(edt_results) == 1
    assert edt_results[0]["vol"] == 3
    assert edt_results[0]["page_key"] == "wiki_pmi_03_edt_wbs"
    assert edt_results[0]["match_score"] == 1


def test_search_canonical_pmi_volumes_no_matches(tmp_path):
    """Búsqueda sin coincidencias por query o tag_filter retorna lista vacía."""
    from backend.services.wiki_pmi_service import search_canonical_pmi_volumes

    _write_doctrine_files(tmp_path, "v-search")
    assert search_canonical_pmi_volumes(query="termino_inexistente_xyz", base_dir=tmp_path) == []
    assert search_canonical_pmi_volumes(tag_filter="tag_inexistente", base_dir=tmp_path) == []


# ── extract_wiki_slash_commands_inventory (PMBOK §4.4, pure helper) ───────


def test_slash_inventory_multiple_supported_commands():
    """Comandos PMI soportados con repetición → válidos con conteos ordenados."""
    from backend.services.wiki_pmi_service import extract_wiki_slash_commands_inventory

    markdown = (
        "# Planificación\n\n"
        "/evm resumen del proyecto\n"
        "- ./wbs no debe contarse (href pegado)\n"
        "/ccb doble revisión\n"
        "/evm otra vez\n"
        "/dod criterios de aceptación\n"
    )
    result = extract_wiki_slash_commands_inventory(markdown)

    # /evm, /ccb, /evm, /dod cuentan; ./wbs está pegado a '.' y se ignora
    assert result["total_invocations"] == 4
    assert result["unique_commands"] == ["ccb", "dod", "evm"]
    assert result["supported_commands"] == ["ccb", "dod", "evm"]
    assert result["unsupported_commands"] == []
    assert result["command_counts"] == {"ccb": 1, "dod": 1, "evm": 2}
    assert result["syntax_status"] == "valid_pmi_commands"


def test_slash_inventory_mixes_unsupported():
    """Comandos fuera del conjunto canónico → 'contains_unsupported'."""
    from backend.services.wiki_pmi_service import (
        SUPPORTED_PMI_SLASH_COMMANDS,
        extract_wiki_slash_commands_inventory,
    )

    markdown = "/charter sponsor asignado\n/evm\n/wbs\n/autohack comando falso\n/imports aliases\n"
    result = extract_wiki_slash_commands_inventory(markdown)

    # 5 invocaciones: charter, evm, wbs soportadas; autohack, imports fuera
    assert result["total_invocations"] == 5
    assert result["unique_commands"] == [
        "autohack",
        "charter",
        "evm",
        "imports",
        "wbs",
    ]
    assert result["supported_commands"] == ["charter", "evm", "wbs"]
    assert result["unsupported_commands"] == ["autohack", "imports"]
    assert result["command_counts"] == {
        "autohack": 1,
        "charter": 1,
        "evm": 1,
        "imports": 1,
        "wbs": 1,
    }
    assert result["syntax_status"] == "contains_unsupported"
    assert "evm" in SUPPORTED_PMI_SLASH_COMMANDS


def test_slash_inventory_ignores_fences_and_urls():
    """Bloques cercados y URLs https:// o rutas /root/... no cuentan."""
    from backend.services.wiki_pmi_service import extract_wiki_slash_commands_inventory

    markdown = (
        "## Instrucciones\n\n"
        "/evm resumen\n\n"
        "```bash\n"
        "/wbs dentro_de_fence\n"
        "/raci tambien_dentro\n"
        "```\n\n"
        "Visita https://plataforma.ccf/evm/guia para más\n"
        "Y lee /root/documentos/ccb/acta.md y /srv/dod/reporte.md\n"
        "~~~\n"
        "/pert dentro de fence con tildes\n"
        "~~~\n"
        "Fin.\n"
    )
    result = extract_wiki_slash_commands_inventory(markdown)

    # Solo /evm del cuerpo real cuenta; URLs, rutas y bloques cercados quedan fuera
    assert result["total_invocations"] == 1
    assert result["unique_commands"] == ["evm"]
    assert result["unsupported_commands"] == []
    assert result["syntax_status"] == "valid_pmi_commands"


def test_slash_inventory_empty_and_none():
    """None, '' y solo espacios → conteos en 0 con status 'empty'."""
    from backend.services.wiki_pmi_service import extract_wiki_slash_commands_inventory

    for text in (None, "", "   \n   ", "Texto sin comandos slash pero con /y pegado"):
        result = extract_wiki_slash_commands_inventory(text)
        assert result == {
            "total_invocations": 0,
            "unique_commands": [],
            "supported_commands": [],
            "unsupported_commands": [],
            "command_counts": {},
            "syntax_status": "empty",
        }


def test_audit_wiki_page_knowledge_hygiene_exemplary_reference():
    """Página con título válido, >=25 palabras, encabezado, enlaces cruzados y tags → exemplary_reference."""
    from backend.services.wiki_pmi_service import audit_wiki_page_knowledge_hygiene

    content = (
        "# Scope\n\n"
        "Esta página documenta la línea base del alcance del proyecto siguiendo las buenas "
        "prácticas metodológicas del estándar PMI PMBOK para garantizar trazabilidad entre "
        "el [Charter](/plataforma/projects/1) y la estructura [[WBS]] aprobada por el comité."
    )
    res = audit_wiki_page_knowledge_hygiene(
        title="Gestión del Alcance",
        content=content,
        tags=["PMI", "Scope", "pmi"],
    )
    assert res["has_valid_title"] is True
    assert res["word_count"] >= 25
    assert res["section_headings_count"] == 1
    assert res["cross_links_count"] == 2
    assert res["normalized_tags"] == ["pmi", "scope"]
    assert res["hygiene_gaps"] == []
    assert res["hygiene_score_pct"] == 100.0
    assert res["knowledge_hygiene_status"] == "exemplary_reference"


def test_audit_wiki_page_knowledge_hygiene_compliant_without_links():
    """Cumple los 4 pilares pero sin enlaces cruzados → compliant_article con 100.0%."""
    from backend.services.wiki_pmi_service import audit_wiki_page_knowledge_hygiene

    content = (
        "## Gobernanza del Proyecto\n\n"
        "El equipo de dirección del proyecto mantiene actualizados todos los artefactos "
        "de planificación y seguimiento semanal para asegurar el cumplimiento riguroso "
        "de los objetivos pastorales y financieros definidos en la sede."
    )
    res = audit_wiki_page_knowledge_hygiene(
        title="Gobernanza Ministerial",
        content=content,
        tags=["gobernanza"],
    )
    assert res["has_valid_title"] is True
    assert res["word_count"] >= 25
    assert res["section_headings_count"] == 1
    assert res["cross_links_count"] == 0
    assert res["hygiene_gaps"] == []
    assert res["hygiene_score_pct"] == 100.0
    assert res["knowledge_hygiene_status"] == "compliant_article"


def test_audit_wiki_page_knowledge_hygiene_needs_enrichment():
    """Faltan 2 pilares (sin encabezados y sin tags, pero con título y >=25 palabras) → needs_enrichment (50%)."""
    from backend.services.wiki_pmi_service import audit_wiki_page_knowledge_hygiene

    content = (
        "Este documento contiene suficientes palabras para superar el umbral mínimo "
        "de veinticinco términos requeridos por el auditor de higiene documental "
        "pero carece de encabezados Markdown y etiquetas taxonómicas asignadas."
    )
    res = audit_wiki_page_knowledge_hygiene(
        title="Nota Operativa",
        content=content,
        tags=[],
    )
    assert res["has_valid_title"] is True
    assert res["word_count"] >= 25
    assert res["section_headings_count"] == 0
    assert res["hygiene_gaps"] == ["unstructured_sections", "untagged_page"]
    assert res["hygiene_score_pct"] == 50.0
    assert res["knowledge_hygiene_status"] == "needs_enrichment"


def test_audit_wiki_page_knowledge_hygiene_stub_or_incomplete():
    """Entradas vacías o None → stub_or_incomplete con 4 brechas y 0.0%."""
    from backend.services.wiki_pmi_service import audit_wiki_page_knowledge_hygiene

    res = audit_wiki_page_knowledge_hygiene(title=None, content=None, tags=None)
    assert res["has_valid_title"] is False
    assert res["word_count"] == 0
    assert res["section_headings_count"] == 0
    assert res["cross_links_count"] == 0
    assert res["normalized_tags"] == []
    assert len(res["hygiene_gaps"]) == 4
    assert res["hygiene_score_pct"] == 0.0
    assert res["knowledge_hygiene_status"] == "stub_or_incomplete"


def test_summarize_wiki_revision_history_velocity_multi_author_curated():
    """3 revisiones de 2 autores distintos con crecimiento de palabras -> 'multi_author_curated'."""
    from backend.services.wiki_pmi_service import (
        summarize_wiki_revision_history_velocity,
    )

    revisions = [
        {"author_id": "author-1", "content": "Borrador inicial del acta."},
        {
            "changed_by": "author-2",
            "content": "Borrador inicial del acta con objetivos y alcance.",
        },
        {
            "updated_by": "author-1",
            "markdown": "Borrador inicial del acta con objetivos y alcance aprobados por el comité.",
        },
    ]
    res = summarize_wiki_revision_history_velocity(revisions)
    assert res == {
        "total_revisions": 3,
        "unique_authors_count": 2,
        "initial_word_count": 4,
        "latest_word_count": 12,
        "net_word_growth": 8,
        "curation_status": "multi_author_curated",
    }


def test_summarize_wiki_revision_history_velocity_iteratively_refined():
    """2 revisiones del mismo autor -> 'iteratively_refined' con unique_authors_count == 1."""
    from backend.services.wiki_pmi_service import (
        summarize_wiki_revision_history_velocity,
    )

    revisions = [
        {"author_id": "author-1", "content": "Primera versión corta."},
        {"author_id": "author-1", "content": "Segunda versión con más detalle operativo."},
    ]
    res = summarize_wiki_revision_history_velocity(revisions)
    assert res["total_revisions"] == 2
    assert res["unique_authors_count"] == 1
    assert res["net_word_growth"] == 3
    assert res["curation_status"] == "iteratively_refined"


def test_summarize_wiki_revision_history_velocity_single_draft():
    """1 sola revisión -> 'single_draft' con net_word_growth == 0."""
    from backend.services.wiki_pmi_service import (
        summarize_wiki_revision_history_velocity,
    )

    res = summarize_wiki_revision_history_velocity(
        [{"author_id": "author-1", "content": "Texto único de cinco palabras"}]
    )
    assert res["total_revisions"] == 1
    assert res["initial_word_count"] == 5
    assert res["latest_word_count"] == 5
    assert res["net_word_growth"] == 0
    assert res["curation_status"] == "single_draft"


def test_summarize_wiki_revision_history_velocity_unversioned():
    """None o lista vacía -> 'unversioned' con total_revisions == 0."""
    from backend.services.wiki_pmi_service import (
        summarize_wiki_revision_history_velocity,
    )

    for empty_val in (None, []):
        res = summarize_wiki_revision_history_velocity(empty_val)
        assert res == {
            "total_revisions": 0,
            "unique_authors_count": 0,
            "initial_word_count": 0,
            "latest_word_count": 0,
            "net_word_growth": 0,
            "curation_status": "unversioned",
        }


# ─── audit_wiki_crosslink_reference_integrity (pure helper) ──────────


def test_audit_wiki_crosslink_connected_graph_with_known_slugs():
    """Referencias [[slug]], [[slug|label]] y (wiki:slug) resueltas -> CONNECTED_KNOWLEDGE_GRAPH."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_crosslink_reference_integrity,
    )

    content = (
        "Ver [[pmbok-4-4|gestion del conocimiento]] y [[Acta de Proyecto]] "
        "más la plantilla (wiki:cierre_administrative)."
    )

    res = audit_wiki_crosslink_reference_integrity(
        content, ["pmbok-4-4", "actadeproyecto", "cierre_administrative"]
    )

    assert res["total_references"] == 3
    assert res["unique_targets"] == ["pmbok-4-4", "actadeproyecto", "cierre_administrative"]
    assert res["resolved_targets"] == res["unique_targets"]
    assert res["broken_targets"] == []
    assert res["integrity_pct"] == 100.0
    assert res["posture"] == "CONNECTED_KNOWLEDGE_GRAPH"


def test_audit_wiki_crosslink_broken_links_detected():
    """Targets ausentes de known_slugs -> BROKEN_KNOWLEDGE_LINKS con integrity_pct parcial."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_crosslink_reference_integrity,
    )

    content = "Ver [[pmbok-4-4]] y [[slug-inexistente]] y otra vez [[pmbok-4-4]]."

    res = audit_wiki_crosslink_reference_integrity(
        content, ["pmbok-4-4", "otra-pagina"]
    )

    assert res["total_references"] == 3
    assert res["unique_targets"] == ["pmbok-4-4", "slug-inexistente"]
    assert res["resolved_targets"] == ["pmbok-4-4"]
    assert res["broken_targets"] == ["slug-inexistente"]
    assert res["integrity_pct"] == 50.0
    assert res["posture"] == "BROKEN_KNOWLEDGE_LINKS"


def test_audit_wiki_crosslink_isolated_no_crosslinks():
    """Contenido sin referencias -> ISOLATED_NO_CROSSLINKS con integridad 100.0."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_crosslink_reference_integrity,
    )

    for empty_content in (None, "Sin referencias cruzadas aquí."):
        res = audit_wiki_crosslink_reference_integrity(empty_content, ["pmbok"])
        assert res == {
            "total_references": 0,
            "unique_targets": [],
            "resolved_targets": [],
            "broken_targets": [],
            "integrity_pct": 100.0,
            "posture": "ISOLATED_NO_CROSSLINKS",
        }


def test_audit_wiki_operational_runbook_markdown_production_ready():
    """Runbook completo (prerrequisitos + pasos + rollback + verificación) -> PRODUCTION_READY_RUNBOOK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    markdown = (
        "# Runbook Despliegue Vespertino\n"
        "## Prerrequisitos\n"
        "Acceso al servidor y credenciales.\n"
        "## Procedimiento\n"
        "1. Activar el modo mantenimiento.\n"
        "2. Copiar el respaldo_previo.\n"
        "```bash\n"
        "3. Este paso dentro de código no debe contar.\n"
        "## Rollback fake dentro de código\n"
        "```\n"
        "## Rollback y Contingencia\n"
        "## Verificación post-ejecución\n"
    )

    res = audit_wiki_operational_runbook_readiness(markdown)

    assert res["has_prerequisites_section"] is True
    assert res["has_rollback_section"] is True
    assert res["has_verification_section"] is True
    assert res["numbered_steps_count"] == 2
    assert res["code_blocks_count"] == 1
    assert res["readiness_score_pct"] == 100.0
    assert res["runbook_posture"] == "PRODUCTION_READY_RUNBOOK"
    assert len(res["recommendations"]) == 1


def test_audit_wiki_operational_runbook_markdown_missing_rollback():
    """Sin sección de rollback -> MISSING_ROLLBACK_PROCEDURE aunque haya prerrequisitos y pasos."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    markdown = (
        "# SOP Backup Diario\n"
        "## Precondiciones\n"
        "## Verificación\n"
        "1. Detener el servicio de respaldo.\n"
        "2. Ejecutar el dump incremental.\n"
    )

    res = audit_wiki_operational_runbook_readiness(markdown)

    assert res["has_prerequisites_section"] is True
    assert res["has_rollback_section"] is False
    assert res["has_verification_section"] is True
    assert res["numbered_steps_count"] == 2
    assert res["readiness_score_pct"] == 75.0
    assert res["runbook_posture"] == "MISSING_ROLLBACK_PROCEDURE"
    assert any("rollback" in rec.lower() for rec in res["recommendations"])


def test_audit_wiki_operational_runbook_markdown_incomplete_structure():
    """Con rollback pero faltando prerrequisitos y pasos -> INCOMPLETE_SOP_STRUCTURE (50.0)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    markdown = (
        "# Procedure\n"
        "## Rollback\n"
        "## Validación del servicio\n"
        "1. Reiniciar el worker principal.\n"
    )

    res = audit_wiki_operational_runbook_readiness(markdown)

    assert res["has_prerequisites_section"] is False
    assert res["has_rollback_section"] is True
    assert res["has_verification_section"] is True
    assert res["numbered_steps_count"] == 1
    assert res["readiness_score_pct"] == 50.0
    assert res["runbook_posture"] == "INCOMPLETE_SOP_STRUCTURE"


def test_audit_wiki_operational_runbook_markdown_empty_content():
    """Texto vacío -> EMPTY_RUNBOOK_CONTENT con score 0.0."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    for empty_val in ("", "   ", "\n"):
        res = audit_wiki_operational_runbook_readiness(empty_val)
        assert res == {
            "has_prerequisites_section": False,
            "has_rollback_section": False,
            "has_verification_section": False,
            "numbered_steps_count": 0,
            "code_blocks_count": 0,
            "readiness_score_pct": 0.0,
            "runbook_posture": "EMPTY_RUNBOOK_CONTENT",
            "recommendations": [
                "Redactar el runbook con prerrequisitos, pasos numerados, rollback y verificación."
            ],
        }


def test_wiki_postmortem_rca_compliant_blameless():
    """Página con timeline + root cause + CAPA con responsable -> COMPLIANT_BLAMELESS_POSTMORTEM."""
    from backend.services.wiki_pmi_service import audit_wiki_postmortem_incident_rca

    res = audit_wiki_postmortem_incident_rca(
        [
            {
                "id": "PM-1",
                "content": (
                    "## Timeline de detección\n"
                    "La detección fue a las 10:14.\n"
                    "## Root Cause (5 whys)\n"
                    "La causa raiz fue un cache sin TTL.\n"
                    "## CAPA\n"
                    "Acción preventiva @ptorres: añadir TTL al cache."
                ),
            },
            {
                "page_id": "PM-2",
                "markdown": (
                    "Cronologia del incidente…\n"
                    "Causa raiz: credencial vencida.\n"
                    "Remediación owner: @admin."
                ),
            },
        ]
    )

    assert res["total_postmortems"] == 2
    assert res["complete_rca_count"] == 2
    assert res["completeness_rate_pct"] == 100.0
    assert res["missing_timeline_page_ids"] == []
    assert res["missing_root_cause_page_ids"] == []
    assert res["missing_capa_page_ids"] == []
    assert res["is_compliant"] is True
    assert res["rca_posture"] == "COMPLIANT_BLAMELESS_POSTMORTEM"


def test_wiki_postmortem_rca_missing_root_cause_take_precedence():
    """Sin causa raíz (aunque también falte timeline) -> MISSING_ROOT_CAUSE_ANALYSIS."""
    from backend.services.wiki_pmi_service import audit_wiki_postmortem_incident_rca

    res = audit_wiki_postmortem_incident_rca(
        [
            {
                "slug": "inc-404-spikes",
                "content": (
                    "## Timeline\nSe detectó el pico.\n"
                    "## CAPA\nAcción correctiva @soporte."
                ),
            }
        ]
    )

    assert res["total_postmortems"] == 1
    assert res["complete_rca_count"] == 0
    assert res["completeness_rate_pct"] == 0.0
    assert res["missing_root_cause_page_ids"] == ["inc-404-spikes"]
    assert res["missing_timeline_page_ids"] == []
    assert res["missing_capa_page_ids"] == []
    assert res["is_compliant"] is False
    assert res["rca_posture"] == "MISSING_ROOT_CAUSE_ANALYSIS"


def test_wiki_postmortem_rca_missing_capa_or_timeline():
    """CAPA sin responsable y página sin timeline -> MISSING_PREVENTIVE_CAPA / MISSING_TIMELINE."""
    from backend.services.wiki_pmi_service import audit_wiki_postmortem_incident_rca

    res_capa = audit_wiki_postmortem_incident_rca(
        [
            {
                "page_id": "PM-CAPA",
                "content": (
                    "Timeline del incidente.\n"
                    "Root cause identificada.\n"
                    "Acciones correctivas pendientes de asignar."  # CAPA sin @/owner
                ),
            }
        ]
    )
    assert res_capa["missing_capa_page_ids"] == ["PM-CAPA"]
    assert res_capa["rca_posture"] == "MISSING_PREVENTIVE_CAPA_ACTIONS"

    res_timeline = audit_wiki_postmortem_incident_rca(
        [
            {
                "page_id": "PM-TIME",
                "content": (
                    "Root cause y 5 whys documentados.\n"
                    "Acción preventiva @responsable que ya está resuelta."
                ),
            }
        ]
    )
    assert res_timeline["missing_timeline_page_ids"] == ["PM-TIME"]
    assert res_timeline["rca_posture"] == "MISSING_INCIDENT_TIMELINE"


def test_wiki_postmortem_rca_empty_and_fallback_ids():
    """None/vacíos/no-dicts -> NO_POSTMORTEM_PAGES; sin id usa fallback PAGE-{idx}."""
    from backend.services.wiki_pmi_service import audit_wiki_postmortem_incident_rca

    for pages in (None, [], ["no dict", 9]):
        res = audit_wiki_postmortem_incident_rca(pages)  # type: ignore[arg-type]
        assert res == {
            "total_postmortems": 0,
            "complete_rca_count": 0,
            "completeness_rate_pct": 0.0,
            "missing_timeline_page_ids": [],
            "missing_root_cause_page_ids": [],
            "missing_capa_page_ids": [],
            "is_compliant": True,
            "rca_posture": "NO_POSTMORTEM_PAGES",
        }

    fallback = audit_wiki_postmortem_incident_rca(
        [{"content": "solo texto sin estructura"}]
    )
    assert fallback["missing_timeline_page_ids"] == ["PAGE-1"]
    assert fallback["missing_root_cause_page_ids"] == ["PAGE-1"]
    assert fallback["missing_capa_page_ids"] == ["PAGE-1"]
    assert fallback["rca_posture"] == "MISSING_ROOT_CAUSE_ANALYSIS"


def test_audit_wiki_crosslink_without_known_slugs_resolves_all():
    """known_slugs None -> todos los targets resueltos, broken [] y CONNECTED_KNOWLEDGE_GRAPH."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_crosslink_reference_integrity,
    )

    res = audit_wiki_crosslink_reference_integrity(
        "Ver [[Wiki PMBOK]] y (wiki:levantamiento) sin catálogo",
        None,
    )

    assert res["total_references"] == 2
    assert res["unique_targets"] == ["wikipmbok", "levantamiento"]
    assert res["resolved_targets"] == res["unique_targets"]
    assert res["broken_targets"] == []
    assert res["integrity_pct"] == 100.0
    assert res["posture"] == "CONNECTED_KNOWLEDGE_GRAPH"


# ─── audit_wiki_template_section_compliance (pure helper) ─────────


def test_wiki_template_compliance_default_sections_fully_compliant():
    """Encabezados con tildes y variantes case-insensitivas -> PMO_TEMPLATE_COMPLIANT (100%)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_template_section_compliance,
    )

    content = (
        "# Propuesta de Proyecto Grupos de Vida\n"
        "## Objetivo del proyecto\n"
        "texto descriptivo…\n"
        "### Alcance y límites\n"
        " ```\ncodigo con ## Objetivo falso dentro\n```\n"
        "#### Riesgos y Mitigaciones\n"
        "## Criterios de Aceptación\n"
    )

    res = audit_wiki_template_section_compliance(content)

    assert res["total_required"] == 4
    assert res["present_sections"] == [
        "Objetivo",
        "Alcance",
        "Riesgos",
        "Criterios de Aceptacion",
    ]
    assert res["missing_sections"] == []
    assert res["compliance_pct"] == 100.0
    assert res["posture"] == "PMO_TEMPLATE_COMPLIANT"


def test_wiki_template_compliance_partial_with_missing_sections():
    """2 de 4 secciones presentes -> PARTIAL_TEMPLATE_COMPLIANCE (50.0)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_template_section_compliance,
    )

    content = "# Plan de Comunicaciones\n## Objetivo\n## Alcance\n"

    res = audit_wiki_template_section_compliance(content)

    assert res["total_required"] == 4
    assert res["present_sections"] == ["Objetivo", "Alcance"]
    assert res["missing_sections"] == ["Riesgos", "Criterios de Aceptacion"]
    assert res["compliance_pct"] == 50.0
    assert res["posture"] == "PARTIAL_TEMPLATE_COMPLIANCE"


def test_wiki_template_compliance_ignores_code_fenced_fake_headings():
    """Encabezados falsos dentro de código cercado no cuentan -> NON_COMPLIANT_STRUCTURE."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_template_section_compliance,
    )

    content = (
        "# Reporte Financiero\n"
        "````\n## Objetivo\n## Alcance\n## Riesgos\n## Criterios\n````"
    )

    res = audit_wiki_template_section_compliance(content)

    assert res["present_sections"] == []
    assert res["missing_sections"] == [
        "Objetivo",
        "Alcance",
        "Riesgos",
        "Criterios de Aceptacion",
    ]
    assert res["compliance_pct"] == 0.0
    assert res["posture"] == "NON_COMPLIANT_STRUCTURE"


def test_wiki_template_compliance_custom_sections_and_empty_content():
    """Secciones custom subcadenas; contenido vacío/None -> EMPTY_WIKI_CONTENT con 100.0."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_template_section_compliance,
    )

    res_custom = audit_wiki_template_section_compliance(
        "## Cronograma Maestro\n## Presupuesto Aprobado\n",
        ["Cronograma", "Presupuesto", "Lecciones"],
    )
    assert res_custom["total_required"] == 3
    assert res_custom["present_sections"] == ["Cronograma", "Presupuesto"]
    assert res_custom["missing_sections"] == ["Lecciones"]
    assert res_custom["compliance_pct"] == 66.67
    assert res_custom["posture"] == "PARTIAL_TEMPLATE_COMPLIANCE"

    for empty_content in (None, "", "   "):
        res = audit_wiki_template_section_compliance(empty_content)
        assert res == {
            "total_required": 4,
            "present_sections": [],
            "missing_sections": [
                "Objetivo",
                "Alcance",
                "Riesgos",
                "Criterios de Aceptacion",
            ],
            # The spec only assigns 100.0 when total_required==0; with 4 required, and 0 present, it is 0.0.
            "compliance_pct": 0.0,
            "posture": "EMPTY_WIKI_CONTENT",
        }


# ─── audit_wiki_stakeholder_signoffs (PMBOK §13.3 / §10.2, pure helper) ───


def test_audit_wiki_stakeholder_signoffs_fully_signed_off():
    """Todos los revisores aprobados/firmados -> 'FULLY_SIGNED_OFF' con 100.0%."""
    import backend.services.wiki_pmi_service as wiki_module
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_stakeholder_signoffs,
    )

    signoffs = [
        {"reviewer": "Sponsor", "status": "approved"},
        {"reviewer": "PMO", "decision": "firmado"},
        {"reviewer": "QA", "status": "signed_off"},
        "invalid_entry_ignored",  # type: ignore[list-item]
    ]
    res = audit_wiki_stakeholder_signoffs(signoffs)
    assert res == {
        "total_reviewers": 3,
        "approved_count": 3,
        "rejected_or_changes_requested_count": 0,
        "pending_count": 0,
        "approval_rate": 100.0,
        "posture": "FULLY_SIGNED_OFF",
    }
    assert WikiPMIService.audit_wiki_stakeholder_signoffs(signoffs) == res
    assert "audit_wiki_stakeholder_signoffs" in wiki_module.__all__


def test_audit_wiki_stakeholder_signoffs_blocked_by_rejection():
    """Al menos un rechazo o cambio solicitado -> 'BLOCKED_BY_REJECTION'."""
    from backend.services.wiki_pmi_service import audit_wiki_stakeholder_signoffs

    signoffs = [
        {"reviewer": "Sponsor", "status": "aprobado"},
        {"reviewer": "Legal", "decision": "changes_requested"},
        {"reviewer": "Finanzas", "status": "pending"},
    ]
    res = audit_wiki_stakeholder_signoffs(signoffs)
    assert res == {
        "total_reviewers": 3,
        "approved_count": 1,
        "rejected_or_changes_requested_count": 1,
        "pending_count": 1,
        "approval_rate": 33.33,
        "posture": "BLOCKED_BY_REJECTION",
    }


def test_audit_wiki_stakeholder_signoffs_pending_stakeholder_signoff():
    """Sin rechazos pero aún con revisores pendientes -> 'PENDING_STAKEHOLDER_SIGNOFF'."""
    from backend.services.wiki_pmi_service import audit_wiki_stakeholder_signoffs

    signoffs = [
        {"reviewer": "Sponsor", "status": "accepted"},
        {"reviewer": "Arquitectura", "status": "in_review"},
    ]
    res = audit_wiki_stakeholder_signoffs(signoffs)
    assert res == {
        "total_reviewers": 2,
        "approved_count": 1,
        "rejected_or_changes_requested_count": 0,
        "pending_count": 1,
        "approval_rate": 50.0,
        "posture": "PENDING_STAKEHOLDER_SIGNOFF",
    }


def test_audit_wiki_stakeholder_signoffs_no_reviewers_assigned():
    """None, lista vacía o sin dicts válidos -> 'NO_REVIEWERS_ASSIGNED'."""
    from backend.services.wiki_pmi_service import audit_wiki_stakeholder_signoffs

    for empty_val in (None, [], ["not-a-dict", 42]):  # type: ignore[list-item]
        res = audit_wiki_stakeholder_signoffs(empty_val)
        assert res == {
            "total_reviewers": 0,
            "approved_count": 0,
            "rejected_or_changes_requested_count": 0,
            "pending_count": 0,
            "approval_rate": 0.0,
            "posture": "NO_REVIEWERS_ASSIGNED",
        }


def test_audit_wiki_decision_log_entries_audit_ready():
    """traceability_rate >= 80.0 -> 'AUDIT_READY_DECISION_LOG'."""
    import backend.services.wiki_pmi_service as wiki_module
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_decision_log_entries,
    )

    decisions = [
        {
            "rationale": "Migrar a arquitectura multi-tenant aislada por sede",
            "decided_by": "Comité Técnico",
            "decision_date": "2026-10-01",
        },
        {
            "justificacion": "Adoptar firma digital en actas de cierre",
            "aprobador": "Sponsor Ejecutivo",
            "fecha": "2026-10-05",
        },
        {
            "reason": "Congelar alcance de fase 2 para proteger ruta crítica",
            "owner": "PMO Director",
            "date": "2026-10-10",
        },
        {
            "rationale": "Ajuste menor de formato",
            "decided_by": "PM",
            "decision_date": "2026-10-12",
        },
        {
            "rationale": "Sin fecha registrada pero con justificación válida",
            "decided_by": "PM",
            "decision_date": "",
        },
    ]
    res = WikiPMIService.audit_wiki_decision_log_entries(decisions)
    assert res == {
        "total_decisions": 5,
        "rationale_documented_count": 5,
        "decider_assigned_count": 5,
        "date_recorded_count": 4,
        "fully_traceable_count": 4,
        "traceability_rate": 80.0,
        "posture": "AUDIT_READY_DECISION_LOG",
    }
    assert audit_wiki_decision_log_entries(decisions) == res
    assert "audit_wiki_decision_log_entries" in wiki_module.__all__


def test_audit_wiki_decision_log_entries_partial_traceability():
    """40.0 <= traceability_rate < 80.0 -> 'PARTIAL_DECISION_TRACEABILITY'."""
    from backend.services.wiki_pmi_service import audit_wiki_decision_log_entries

    decisions = [
        {
            "rationale": "Aprobar presupuesto de contingencia adicional",
            "decided_by": "CCB",
            "decision_date": "2026-10-15",
        },
        {
            "rationale": "Corto",
            "decided_by": "CCB",
            "decision_date": "2026-10-16",
        },
    ]
    res = audit_wiki_decision_log_entries(decisions)
    assert res["total_decisions"] == 2
    assert res["rationale_documented_count"] == 1
    assert res["decider_assigned_count"] == 2
    assert res["date_recorded_count"] == 2
    assert res["fully_traceable_count"] == 1
    assert res["traceability_rate"] == 50.0
    assert res["posture"] == "PARTIAL_DECISION_TRACEABILITY"


def test_audit_wiki_decision_log_entries_opaque_untraceable():
    """traceability_rate < 40.0 con decisiones registradas -> 'OPAQUE_UNTRACEABLE_DECISIONS'."""
    from backend.services.wiki_pmi_service import audit_wiki_decision_log_entries

    decisions = [
        {"rationale": "Sin aprobador ni fecha", "decided_by": "", "decision_date": ""},
        {"rationale": "ok", "decided_by": "PM", "decision_date": "2026-10-18"},
        {"rationale": "Cambio de proveedor sin fecha", "decided_by": "Compras"},
    ]
    res = audit_wiki_decision_log_entries(decisions)
    assert res["total_decisions"] == 3
    assert res["fully_traceable_count"] == 0
    assert res["traceability_rate"] == 0.0
    assert res["posture"] == "OPAQUE_UNTRACEABLE_DECISIONS"


def test_audit_wiki_decision_log_entries_no_decisions_logged():
    """Lista vacía, None o entradas no-dict -> 'NO_DECISIONS_LOGGED'."""
    from backend.services.wiki_pmi_service import audit_wiki_decision_log_entries

    for empty_input in (None, [], ["invalid", 123]):  # type: ignore[list-item]
        res = audit_wiki_decision_log_entries(empty_input)
        assert res == {
            "total_decisions": 0,
            "rationale_documented_count": 0,
            "decider_assigned_count": 0,
            "date_recorded_count": 0,
            "fully_traceable_count": 0,
            "traceability_rate": 0.0,
            "posture": "NO_DECISIONS_LOGGED",
        }


def test_audit_wiki_raid_register_tables_governed_matrix():
    """completeness_rate >= 80.0 y sin filas sin propietario -> 'GOVERNED_RAID_MATRIX'."""
    import backend.services.wiki_pmi_service as wiki_module
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_raid_register_tables,
    )

    md = (
        "# Registro RAID del Proyecto\n\n"
        "| ID | Descripción | Severidad | Responsable | Plan de Mitigación |\n"
        "|---|---|---|---|---|\n"
        "| RISK-01 | Latencia en enlace satelital | HIGH | @infra_lead | Configurar redundancia SD-WAN secundaria |\n"
        "| ISS-02 | Demora en firma de proveedor | ALTA | Coordinador PMO | Escalar con dirección administrativa |\n"
        "| ACT-03 | Actualizar matriz RACI | MEDIA | @pm_sede | Publicar versión revisada en Wiki |\n"
        "| DEP-04 | Aprobación municipal | CRITICAL | Legal | Seguimiento semanal en mesa técnica |\n"
        "| RSK-05 | Variación cambiaria menor | BAJA | Finanzas | Corto |\n"
    )

    res = WikiPMIService.audit_wiki_raid_register_tables(md)
    assert res["total_raid_rows"] == 5
    assert res["fully_specified_count"] == 4
    assert res["unassigned_raid_ids"] == []
    assert res["unmitigated_raid_ids"] == ["RSK-05"]
    assert res["completeness_rate"] == 80.0
    assert res["raid_table_posture"] == "GOVERNED_RAID_MATRIX"
    assert isinstance(res["recommendations"], list) and len(res["recommendations"]) >= 1
    assert audit_wiki_raid_register_tables(md) == res
    assert "audit_wiki_raid_register_tables" in wiki_module.__all__


def test_audit_wiki_raid_register_tables_unassigned_ownership():
    """Al menos un ítem RAID sin propietario válido (TBD / SIN ASIGNAR / vacío) -> 'UNASSIGNED_RAID_OWNERSHIP'."""
    from backend.services.wiki_pmi_service import audit_wiki_raid_register_tables

    md = (
        "| ID | Evento | Prioridad | Owner | Respuesta |\n"
        "|---|---|---|---|---|\n"
        "| RISK-10 | Sobrecosto en licencias | HIGH | @finanzas | Renegociar contrato marco anual |\n"
        "| ISSUE-11 | Falla en entorno staging | CRITICAL | TBD | Reaprovisionar contenedores base |\n"
        "| ACT-12 | Capacitación de usuarios | MEDIUM | SIN ASIGNAR | Programar talleres por sede |\n"
    )

    res = audit_wiki_raid_register_tables(md)
    assert res["total_raid_rows"] == 3
    assert res["fully_specified_count"] == 1
    assert res["unassigned_raid_ids"] == ["ISSUE-11", "ACT-12"]
    assert res["unmitigated_raid_ids"] == []
    assert res["completeness_rate"] == 33.33
    assert res["raid_table_posture"] == "UNASSIGNED_RAID_OWNERSHIP"


def test_audit_wiki_raid_register_tables_incomplete_mitigation_plans():
    """Todos con propietario pero completeness_rate < 80.0 por mitigación faltante -> 'INCOMPLETE_MITIGATION_PLANS'."""
    from backend.services.wiki_pmi_service import audit_wiki_raid_register_tables

    md = (
        "| ID | Descripción | Severidad | Responsable | Plan de Mitigación |\n"
        "|---|---|---|---|---|\n"
        "| RISK-20 | Rotación de personal clave | ALTA | @rrhh_lead | Documentar procesos y pares técnicos |\n"
        "| RISK-21 | Retraso de aduana | MEDIA | @logistica | TBD |\n"
        "| ISS-22 | Bug en reporte PDF | LOW | @qa_engineer | N/A |\n"
    )

    res = audit_wiki_raid_register_tables(md)
    assert res["total_raid_rows"] == 3
    assert res["fully_specified_count"] == 1
    assert res["unassigned_raid_ids"] == []
    assert res["unmitigated_raid_ids"] == ["RISK-21", "ISS-22"]
    assert res["completeness_rate"] == 33.33
    assert res["raid_table_posture"] == "INCOMPLETE_MITIGATION_PLANS"


def test_audit_wiki_raid_register_tables_no_raid_rows():
    """Texto vacío, sin tablas RAID o tablas dentro de bloques ``` -> 'NO_RAID_TABLE_ROWS'."""
    from backend.services.wiki_pmi_service import audit_wiki_raid_register_tables

    fenced_md = (
        "```markdown\n"
        "| ID | Riesgo | Severidad | Responsable | Mitigación |\n"
        "|---|---|---|---|---|\n"
        "| RISK-99 | Falso positivo en código | HIGH | @dev | Mitigación de prueba |\n"
        "```\n"
    )
    non_raid_table = (
        "| Fase | Entregable | Estado |\n"
        "|---|---|---|\n"
        "| Inicio | Project Charter | Aprobado |\n"
    )

    for empty_val in (None, "", fenced_md, non_raid_table):
        res = audit_wiki_raid_register_tables(empty_val)
        assert res["total_raid_rows"] == 0
        assert res["fully_specified_count"] == 0
        assert res["unassigned_raid_ids"] == []
        assert res["unmitigated_raid_ids"] == []
        assert res["completeness_rate"] == 0.0
        assert res["raid_table_posture"] == "NO_RAID_TABLE_ROWS"


def test_audit_wiki_meeting_minutes_markdown_governed_minutes():
    """>= 2 asistentes, agenda, decisiones y todas las acciones abiertas con @usuario -> 'GOVERNED_MEETING_MINUTES'."""
    import backend.services.wiki_pmi_service as wiki_module
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_meeting_minutes_governance,
    )

    md = (
        "# Acta de Comité de Proyecto — 2026-10-18\n"
        "Participantes: @Pastor_General, @pm_sede, @finanzas_lead\n\n"
        "## Agenda y Objetivos\n"
        "- Revisión de avance físico WBS y EVM.\n\n"
        "## Decisiones y Acuerdos\n"
        "- DEC-01: Se autoriza liberación de contingencia para fase 2.\n\n"
        "## Compromisos\n"
        "- [x] Publicar línea base inicial @pm_sede\n"
        "- [ ] Emitir orden de compra del proveedor @finanzas_lead (vence 2026-10-25)\n"
    )

    res = WikiPMIService.audit_wiki_meeting_minutes_governance(md)
    assert res["attendees_mentions"] == [
        "finanzas_lead",
        "pastor_general",
        "pm_sede",
    ]
    assert res["detected_dates"] == ["2026-10-18", "2026-10-25"]
    assert res["has_agenda_section"] is True
    assert res["has_decisions_record"] is True
    assert res["total_action_items"] == 2
    assert res["unassigned_open_actions"] == 0
    assert res["minutes_posture"] == "GOVERNED_MEETING_MINUTES"
    assert len(res["recommendations"]) >= 1
    assert audit_wiki_meeting_minutes_governance(md) == res
    assert "audit_wiki_meeting_minutes_governance" in wiki_module.__all__


def test_audit_wiki_meeting_minutes_markdown_unassigned_actions():
    """Acciones abiertas (- [ ]) sin mención @usuario -> 'UNASSIGNED_ACTION_ITEMS'."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    md = (
        "# Reunión Semanal PMO (2026-10-18)\n"
        "Asistentes: @coordinador, @arquitecto\n\n"
        "## Orden del Día\n"
        "1. Seguimiento de entregables\n\n"
        "## Acuerdos\n"
        "- Se aprueba el cronograma.\n\n"
        "## Tareas\n"
        "- [ ] Actualizar matriz de riesgos antes del viernes\n"
        "- [ ] Solicitar cotización adicional\n"
        "- [ ] Validar respaldo con @arquitecto\n"
    )

    res = audit_wiki_meeting_minutes_governance(md)
    assert res["attendees_mentions"] == ["arquitecto", "coordinador"]
    assert res["has_agenda_section"] is True
    assert res["has_decisions_record"] is True
    assert res["total_action_items"] == 3
    assert res["unassigned_open_actions"] == 2
    assert res["minutes_posture"] == "UNASSIGNED_ACTION_ITEMS"


def test_audit_wiki_meeting_minutes_markdown_incomplete_structure():
    """Sin acciones huérfanas pero falta decisiones o quórum < 2 -> 'INCOMPLETE_MINUTES_STRUCTURE'."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    md = (
        "# Minuta Rápida 2026-10-18\n"
        "Asistente: @pm_unico\n\n"
        "## Agenda\n"
        "- Revisar estado general\n"
        "- [ ] Enviar resumen ejecutivo @pm_unico\n"
    )

    res = audit_wiki_meeting_minutes_governance(md)
    assert res["attendees_mentions"] == ["pm_unico"]
    assert res["has_agenda_section"] is True
    assert res["has_decisions_record"] is False
    assert res["unassigned_open_actions"] == 0
    assert res["minutes_posture"] == "INCOMPLETE_MINUTES_STRUCTURE"
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_meeting_minutes_markdown_not_a_meeting_minute():
    """Sin fechas, sin menciones @usuario y sin sección de agenda (o solo en bloque ```) -> 'NOT_A_MEETING_MINUTE'."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    fenced_only = (
        "```markdown\n"
        "# Agenda 2026-10-18\n"
        "Asistentes: @user1 @user2\n"
        "- [ ] Acción dentro de código\n"
        "```\n"
        "Documento técnico descriptivo sin actas.\n"
    )

    for payload in ("", "   ", fenced_only):
        res = audit_wiki_meeting_minutes_governance(payload)
        assert res["attendees_mentions"] == []
        assert res["detected_dates"] == []
        assert res["has_agenda_section"] is False
        assert res["has_decisions_record"] is False
        assert res["total_action_items"] == 0
        assert res["unassigned_open_actions"] == 0
        assert res["minutes_posture"] == "NOT_A_MEETING_MINUTE"
        assert len(res["recommendations"]) == 1






def test_audit_wiki_lessons_learned_taxonomy_institutionalized():
    """Categoría con acento válida, entradas completas -> 100% accionable."""
    from backend.services.wiki_pmi_service import audit_wiki_lessons_learned_taxonomy

    res = audit_wiki_lessons_learned_taxonomy(
        [
            {
                "id": "LL-1",
                "category": "Comunicación",
                "situation": "Retraso por minutas sin responsable definido",
                "recommendation": "Designar responsable de minutas en cada reunión",
            },
            {
                "entry_id": "LL-2",
                "domain": "Riesgos",
                "context": "Sin enlaces de respaldo ni interventores asignados",
                "actionable_advice": "Implementar log de seguimiento nocturno periódico",
            },
            {
                "lesson_id": "LL-3",
                "knowledge_area": "Evaluación",
                "description": "Cobertura de evangelismo insuficiente en sede",
                "leccion": "Contratar intenarios adicionales para la sede",
            },
        ]
    )
    assert res["total_entries"] == 3
    assert res["actionable_entries_count"] == 3
    assert res["actionable_rate_pct"] == 100.0
    assert res["uncategorized_entry_ids"] == []
    assert res["shallow_context_entry_ids"] == []
    assert res["missing_recommendation_entry_ids"] == []
    assert res["is_compliant"] is True
    assert res["lessons_posture"] == "INSTITUTIONALIZED_LESSONS_LEARNED"


def test_audit_wiki_lessons_learned_taxonomy_missing_recommendation():
    """Sin recomendación >= 10 chars -> MISSING_ACTIONABLE_RECOMMENDATIONS (precedencia)."""
    from backend.services.wiki_pmi_service import audit_wiki_lessons_learned_taxonomy

    res = audit_wiki_lessons_learned_taxonomy(
        [
            {
                "id": "LL-OK",
                "category": "Alcance",
                "context": "Crecimiento sin CR aprobada documentado",
                "recommendation": "Establecer CCB obligatorio antes de cambios",
            },
            {
                "id": "LL-NO-REC",
                "category": "Riesgos",
                "context": "Riesgo sin plan de contingencia identificado",
                "recommendation": "corto",
            },
        ]
    )
    assert res["total_entries"] == 2
    assert res["actionable_entries_count"] == 1
    assert res["actionable_rate_pct"] == 50.0
    assert res["missing_recommendation_entry_ids"] == ["LL-NO-REC"]
    assert res["is_compliant"] is False
    assert res["lessons_posture"] == "MISSING_ACTIONABLE_RECOMMENDATIONS"


def test_audit_wiki_lessons_learned_taxonomy_uncategorized_and_shallow():
    """Sin categoría válida o contexto < 10 chars marca por pilar con precedencia."""
    from backend.services.wiki_pmi_service import audit_wiki_lessons_learned_taxonomy

    res = audit_wiki_lessons_learned_taxonomy(
        [
            {
                "id": "LL-7",
                "category": "TBD",
                "description": "Flujo de aprobación ambiguo en comisiones",
                "recommendation": "Documentar flujo y publicarlo en la Wiki",
            },
            {
                "id": "LL-8",
                "domain": "Calidad",
                "description": "corto",
                "recommendation": "Crear checklist DoD obligatorio por entregable",
            },
            {
                "id": "LL-9",
                "knowledge_area": "N/A",
                "context": "Detección tardía de defectos en despliegues",
                "leccion": "Introducir revisión pares antes del merge",
            },
        ]
    )
    assert res["total_entries"] == 3
    assert res["actionable_entries_count"] == 0
    assert res["actionable_rate_pct"] == 0.0
    # LL-7 TBD y LL-9 N/A sin categoría; LL-8 con contexto < 10 chars.
    assert res["uncategorized_entry_ids"] == ["LL-7", "LL-9"]
    assert res["shallow_context_entry_ids"] == ["LL-8"]
    assert res["missing_recommendation_entry_ids"] == []
    assert res["is_compliant"] is False
    # Precedencia: unanswered category sobre shallow context.
    assert res["lessons_posture"] == "UNCATEGORIZED_KNOWLEDGE_ENTRIES"


def test_audit_wiki_lessons_learned_taxonomy_empty_or_none():
    """None, lista vacía o sin entradas dict -> NO_LESSONS_RECORDED."""
    from backend.services.wiki_pmi_service import audit_wiki_lessons_learned_taxonomy

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_wiki_lessons_learned_taxonomy(payload)  # type: ignore[arg-type]
        assert res == {
            "total_entries": 0,
            "actionable_entries_count": 0,
            "actionable_rate_pct": 0.0,
            "uncategorized_entry_ids": [],
            "shallow_context_entry_ids": [],
            "missing_recommendation_entry_ids": [],
            "is_compliant": True,
            "lessons_posture": "NO_LESSONS_RECORDED",
        }


def test_audit_wiki_adr_lifecycle_traceability_traceable():
    """Registro ADR con ADR-1 superseded por ADR-2 y ADR-2 accepted con context y consequences."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_adr_lifecycle_traceability,
    )

    adrs = [
        {
            "id": "ADR-1",
            "status": "superseded",
            "superseded_by": "ADR-2",
            "context": "Autenticación inicial basada en sesiones monolíticas",
        },
        {
            "id": "ADR-2",
            "status": "accepted",
            "context": "Escalabilidad multi-sede requiere tokens firmados stateless",
            "consequences": "Rotación de llaves JWT y validación en API Gateway",
        },
    ]
    res = audit_wiki_adr_lifecycle_traceability(adrs)
    assert res == {
        "total_adrs": 2,
        "accepted_adrs_count": 1,
        "invalid_status_adr_ids": [],
        "broken_supersession_adr_ids": [],
        "incomplete_accepted_adr_ids": [],
        "is_traceable": True,
        "adr_posture": "TRACEABLE_ADR_ARCHITECTURE_LOG",
    }
    assert WikiPMIService.audit_wiki_adr_lifecycle_traceability(adrs) == res


def test_audit_wiki_adr_lifecycle_traceability_invalid_status():
    """ADR con estado fuera de gramática -> INVALID_ADR_LIFECYCLE_STATUS."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_lifecycle_traceability

    res = audit_wiki_adr_lifecycle_traceability(
        [
            {
                "id": "ADR-10",
                "status": "draft-unknown",
                "context": "Exploración inicial",
            },
            {
                "id": "ADR-11",
                "status": "aceptado",
                "problem": "Latencia en consultas de reportes",
                "impact": "Índices compuestos en PostgreSQL",
            },
        ]
    )
    assert res["total_adrs"] == 2
    assert res["accepted_adrs_count"] == 1
    assert res["invalid_status_adr_ids"] == ["ADR-10"]
    assert res["broken_supersession_adr_ids"] == []
    assert res["incomplete_accepted_adr_ids"] == []
    assert res["is_traceable"] is False
    assert res["adr_posture"] == "INVALID_ADR_LIFECYCLE_STATUS"


def test_audit_wiki_adr_lifecycle_traceability_broken_supersession_and_incomplete_accepted():
    """ADR superseded sin destino válido -> BROKEN_ADR_SUPERSESSION_CHAIN y accepted incompleto -> INCOMPLETE_ACCEPTED_ADR_RATIONALE."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_lifecycle_traceability

    broken_res = audit_wiki_adr_lifecycle_traceability(
        [
            {
                "adr_id": "ADR-01",
                "status": "superseded",
                "superseded_by": "ADR-999",
            },
            {
                "code": "ADR-02",
                "status": "reemplazado",
                "replaced_by": "",
            },
        ]
    )
    assert broken_res["total_adrs"] == 2
    assert broken_res["broken_supersession_adr_ids"] == ["ADR-01", "ADR-02"]
    assert broken_res["is_traceable"] is False
    assert broken_res["adr_posture"] == "BROKEN_ADR_SUPERSESSION_CHAIN"

    incomplete_res = audit_wiki_adr_lifecycle_traceability(
        [
            {
                "id": "ADR-03",
                "status": "accepted",
                "context": "Se requiere almacenamiento de objetos para adjuntos",
                "consequences": "   ",
            }
        ]
    )
    assert incomplete_res["total_adrs"] == 1
    assert incomplete_res["accepted_adrs_count"] == 1
    assert incomplete_res["incomplete_accepted_adr_ids"] == ["ADR-03"]
    assert incomplete_res["is_traceable"] is False
    assert incomplete_res["adr_posture"] == "INCOMPLETE_ACCEPTED_ADR_RATIONALE"


def test_audit_wiki_adr_lifecycle_traceability_empty_or_none():
    """Lista vacía o None -> NO_ADRS_REGISTERED."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_lifecycle_traceability

    for payload in (None, [], ["not-a-dict", 123]):
        res = audit_wiki_adr_lifecycle_traceability(payload)  # type: ignore[arg-type]
        assert res == {
            "total_adrs": 0,
            "accepted_adrs_count": 0,
            "invalid_status_adr_ids": [],
            "broken_supersession_adr_ids": [],
            "incomplete_accepted_adr_ids": [],
            "is_traceable": True,
            "adr_posture": "NO_ADRS_REGISTERED",
        }


def test_audit_wiki_communication_matrix_governance_compliant():
    """Matriz completa incluido canal de escalamiento con SLA -> COMPLIANT matrix."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CH-WEEKLY",
                "audience": "Rpastores y líderes de sedes",
                "frequency": "semestral por sede",
                "owner": "Secretaría General",
                "channel_type": "newsletter",
            },
            {
                "name": "CH-INCIDENT",
                "stakeholders": "Equipo técnico y mediación",
                "cadence": "on-demand",
                "responsable": "Coordinación Técnica",
                "purpose": "Escalamiento de incidentes",
                "escalation_sla_hours": 4.0,
            },
        ]
    )
    assert res["is_compliant"] is True
    assert res["total_channels"] == 2
    assert res["complete_channels_count"] == 2
    assert res["missing_audience_channel_ids"] == []
    assert res["missing_cadence_channel_ids"] == []
    assert res["unowned_channel_ids"] == []
    assert res["missing_escalation_sla_channel_ids"] == []
    assert res["matrix_posture"] == "COMPLIANT_COMMUNICATIONS_MATRIX"


def test_audit_wiki_communication_matrix_governance_missing_escalation_sla():
    """Canal de escalamiento sin SLA > 0 -> MISSING_ESCALATION_SLA_PATH."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CH-REGULAR",
                "audience": "Comunidad",
                "frequency": "mensual",
                "owner": "Comunicaciones",
            },
            {
                "id": "CH-CRISIS",
                "is_escalation": True,
                "audience": "Mediación",
                "cadence": "on-demand",
                "owner": "Mediador General",
                "sla_hours": 0.0,
            },
        ]
    )
    assert res["is_compliant"] is False
    assert res["total_channels"] == 2
    assert res["complete_channels_count"] == 1
    assert res["missing_escalation_sla_channel_ids"] == ["CH-CRISIS"]
    assert res["missing_audience_channel_ids"] == []
    assert res["missing_cadence_channel_ids"] == []
    assert res["unowned_channel_ids"] == []
    assert res["matrix_posture"] == "MISSING_ESCALATION_SLA_PATH"


def test_audit_wiki_communication_matrix_governance_unowned_and_incomplete():
    """Sin audiencia, cadencia y responsable ausentes por pilar (precedencia unowned)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CH-1",
                "audience": "Licensing",
                "cadence": "quincenal",
            },
            {
                "id": "CH-2",
                "owner": "Correo General",
                "frequency": "semanal",
                "purpose": "incident",
                "escalation_sla_hours": 8.0,
            },
            {
                "id": "CH-3",
                "owner": "C Après-vente",
                "audience": "Usores veteranos",
            },
        ]
    )
    assert res["is_compliant"] is False
    assert res["total_channels"] == 3
    # CH-1 sin owner; CH-2 sin audiencia; CH-3 sin cadencia.
    assert res["complete_channels_count"] == 0
    assert res["unowned_channel_ids"] == ["CH-1"]
    assert res["missing_audience_channel_ids"] == ["CH-2"]
    assert res["missing_cadence_channel_ids"] == ["CH-3"]
    assert res["missing_escalation_sla_channel_ids"] == []
    assert res["matrix_posture"] == "UNOWNED_COMMUNICATION_CHANNELS"


def test_audit_wiki_communication_matrix_governance_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_COMMUNICATION_CHANNELS."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_governance as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_channels": 0,
            "complete_channels_count": 0,
            "missing_audience_channel_ids": [],
            "missing_cadence_channel_ids": [],
            "unowned_channel_ids": [],
            "missing_escalation_sla_channel_ids": [],
            "is_compliant": True,
            "matrix_posture": "NO_COMMUNICATION_CHANNELS",
        }


def test_audit_wiki_raci_matrix_governance_compliant():
    """Matriz RACI válida con 1 A, >=1 R y C <= max_consulted_per_row -> COMPLIANT_RACI_GOVERNANCE."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_raci_matrix_governance_v1 as audit_wiki_raci_matrix_governance,
    )

    rows = [
        {
            "id": "RACI-01",
            "accountable": ["Director PMO"],
            "responsible": ["Arquitecto", "Dev Lead"],
            "consulted": ["Seguridad", "Infraestructura"],
            "informed": ["Patrocinador"],
        },
        {
            "deliverable": "RACI-02",
            "A": "Sponsor",
            "R": "PM",
            "C": "Legal, Finanzas",
            "I": "Comité",
        },
    ]
    res = audit_wiki_raci_matrix_governance(rows, max_consulted_per_row=5)
    assert res == {
        "total_rows": 2,
        "valid_rows_count": 2,
        "missing_accountable_row_ids": [],
        "multiple_accountable_row_ids": [],
        "missing_responsible_row_ids": [],
        "over_consulted_row_ids": [],
        "is_raci_compliant": True,
        "raci_posture": "COMPLIANT_RACI_GOVERNANCE",
    }
    assert WikiPMIService.audit_wiki_raci_matrix_governance_v1(rows, max_consulted_per_row=5) == res


def test_audit_wiki_raci_matrix_governance_multiple_accountable_conflict():
    """Fila con múltiples Accountable (A > 1) -> MULTIPLE_ACCOUNTABLE_CONFLICT."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raci_matrix_governance_v1 as audit_wiki_raci_matrix_governance,
    )

    res = audit_wiki_raci_matrix_governance(
        [
            {
                "id": "RACI-DUP-A",
                "accountable": ["Director TI", "Director Operaciones"],
                "responsible": ["Equipo Backend"],
            }
        ]
    )
    assert res["total_rows"] == 1
    assert res["valid_rows_count"] == 0
    assert res["multiple_accountable_row_ids"] == ["RACI-DUP-A"]
    assert res["is_raci_compliant"] is False
    assert res["raci_posture"] == "MULTIPLE_ACCOUNTABLE_CONFLICT"


def test_audit_wiki_raci_matrix_governance_missing_a_missing_r_and_over_consulted():
    """Casos de fila sin A, fila sin R y fila con sobrecarga de C."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raci_matrix_governance_v1 as audit_wiki_raci_matrix_governance,
    )

    no_a_res = audit_wiki_raci_matrix_governance(
        [{"id": "RACI-NO-A", "accountable": [], "responsible": ["Dev"]}]
    )
    assert no_a_res["missing_accountable_row_ids"] == ["RACI-NO-A"]
    assert no_a_res["is_raci_compliant"] is False
    assert no_a_res["raci_posture"] == "MISSING_ACCOUNTABLE_OWNER"

    no_r_res = audit_wiki_raci_matrix_governance(
        [{"id": "RACI-NO-R", "accountable": ["PM"], "responsible": ""}]
    )
    assert no_r_res["missing_responsible_row_ids"] == ["RACI-NO-R"]
    assert no_r_res["is_raci_compliant"] is False
    assert no_r_res["raci_posture"] == "MISSING_RESPONSIBLE_EXECUTOR"

    over_c_res = audit_wiki_raci_matrix_governance(
        [
            {
                "id": "RACI-OVER-C",
                "accountable": ["PM"],
                "responsible": ["Dev"],
                "consulted": ["C1", "C2", "C3", "C4"],
            }
        ],
        max_consulted_per_row=3,
    )
    assert over_c_res["over_consulted_row_ids"] == ["RACI-OVER-C"]
    assert over_c_res["is_raci_compliant"] is False
    assert over_c_res["raci_posture"] == "CONSULTED_BOTTLENECK_WARNING"


def test_audit_wiki_raci_matrix_governance_empty_or_none():
    """Lista vacía o None -> NO_RACI_ROWS_EVALUATED."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raci_matrix_governance_v1 as audit_wiki_raci_matrix_governance,
    )

    for payload in (None, [], ["invalid", 42]):
        res = audit_wiki_raci_matrix_governance(payload)  # type: ignore[arg-type]
        assert res == {
            "total_rows": 0,
            "valid_rows_count": 0,
            "missing_accountable_row_ids": [],
            "multiple_accountable_row_ids": [],
            "missing_responsible_row_ids": [],
            "over_consulted_row_ids": [],
            "is_raci_compliant": True,
            "raci_posture": "NO_RACI_ROWS_EVALUATED",
        }


def test_audit_wiki_project_glossary_governance_governed():
    """> Acronimos únicos, definición >= 10 chars y dominio -> GOVERNED glossary."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_project_glossary_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "term": "CCB",
                "definition": "Change Control Board del proyecto",
                "domain": "Gestión de Cambios",
            },
            {
                "term": "TCPI",
                "definition": "Indice de desempeño hasta el final para cumplir BAC",
                "category": "Gestión de Costos",
            },
            {
                "term": "DoD",
                "description": "Definition of Done de cada entregable h",
                "knowledge_area": "Calidad",
            },
        ]
    )
    assert res["is_glossary_compliant"] is True
    assert res["total_entries"] == 3
    assert res["duplicate_terms"] == []
    assert res["incomplete_definition_terms"] == []
    assert res["circular_definition_terms"] == []
    assert res["uncategorized_terms"] == []
    assert res["glossary_posture"] == "GOVERNED_PROJECT_GLOSSARY"


def test_audit_wiki_project_glossary_governance_duplicate_acronym():
    """> Acronimo duplicado (case-insensitive) -> DUPLICATE_AMBIGUOUS_ACRONYM."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_project_glossary_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "term": "KPI",
                "definition": "Indicador clave de desempeño",
                "domain": "Gestión",
            },
            {
                "term": "KPI",
                "definition": "Key Performance Indicator principal",
                "domain": "Gestión",
            },
            {
                "term": "kpi",
                "definition": "Variante en minusculas del mismo acronimo",
                "domain": "Gestión",
            },
        ]
    )
    assert res["is_glossary_compliant"] is False
    assert res["total_entries"] == 3
    assert res["duplicate_terms"] == ["KPI", "kpi"]
    assert res["incomplete_definition_terms"] == []
    assert res["circular_definition_terms"] == []
    assert res["uncategorized_terms"] == []
    assert res["glossary_posture"] == "DUPLICATE_AMBIGUOUS_ACRONYM"


def test_audit_wiki_project_glossary_governance_incomplete_circular_uncategorized():
    """> Definicion corta, circular y sin dominio identificados por pilar."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_project_glossary_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "term": "SIGLA-VA",
                "definition": "cortita",
                "domain": "Operaciones",
            },
            {
                "term": "PM",
                "definition": "PM is PM en el repositorio",
                "domain": "Gestión",
            },
            {
                "term": "SAC",
                "definition": "Sistema de Atención al Cliente",
            },
        ]
    )
    assert res["is_glossary_compliant"] is False
    assert res["total_entries"] == 3
    assert res["incomplete_definition_terms"] == ["SIGLA-VA"]
    assert res["circular_definition_terms"] == ["PM"]
    assert res["uncategorized_terms"] == ["SAC"]
    assert res["duplicate_terms"] == []
    # Precedencia: duplicates > incomplete/circular > uncategorized.
    assert res["glossary_posture"] == "INCOMPLETE_OR_CIRCULAR_DEFINITION"


def test_audit_wiki_project_glossary_governance_empty_or_none():
    """None, lista vacía o entradas no-dict -> EMPTY_PROJECT_GLOSSARY."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_project_glossary_governance as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_entries": 0,
            "duplicate_terms": [],
            "incomplete_definition_terms": [],
            "circular_definition_terms": [],
            "uncategorized_terms": [],
            "is_glossary_compliant": True,
            "glossary_posture": "EMPTY_PROJECT_GLOSSARY",
        }


def test_audit_wiki_knowledge_bus_factor_and_freshness_resilient():
    """> Multi-autor, crítico con peer review y frescos <= 90 días -> RESILIENT repo."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ART-1",
                "contributors": ["Ana", "Luis", "Ana"],
                "days_since_review": 30,
            },
            {
                "article_id": "ART-2",
                "authors": ["Sofía"],
                "is_critical": True,
                "sme_approved": True,
                "age_days": 60,
            },
            {
                "slug": "ART-3",
                "editors": ["Pedro", "Lucía"],
                "days_since_review": 88.5,
            },
        ]
    )
    assert res["is_knowledge_resilient"] is True
    assert res["total_articles"] == 3
    assert res["orphaned_article_ids"] == []
    assert res["bus_factor_risk_article_ids"] == []
    assert res["stale_article_ids"] == []
    assert res["knowledge_resilience_posture"] == "RESILIENT_KNOWLEDGE_REPOSITORY"


def test_audit_wiki_knowledge_bus_factor_and_freshness_critical_bus_factor():
    """> Crítico, un solo autor y sin peer review -> CRITICAL_BUS_FACTOR_EXPOSURE."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ART-SAFE",
                "contributors": "Autor A, Autor B",
                "is_critical": True,
                "days_since_review": 10,
            },
            {
                "id": "ART-SOLO",
                "created_by": "Solo Josué",
                "core_architecture": True,
                "days_since_review": 20,
            },
        ]
    )
    assert res["is_knowledge_resilient"] is False
    assert res["total_articles"] == 2
    assert res["orphaned_article_ids"] == []
    assert res["bus_factor_risk_article_ids"] == ["ART-SOLO"]
    assert res["stale_article_ids"] == []
    assert res["knowledge_resilience_posture"] == "CRITICAL_BUS_FACTOR_EXPOSURE"


def test_audit_wiki_knowledge_bus_factor_and_freshness_orphaned_and_stale():
    """> Sin autores (precedencia posture) y review > 90 días como pilar separado."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ART-GHOST",
                "days_since_review": 5,
            },
            {
                "id": "ART-OLD",
                "authors": ["Marta"],
                "days_since_review": 120,
            },
        ]
    )
    assert res["is_knowledge_resilient"] is False
    assert res["total_articles"] == 2
    assert res["orphaned_article_ids"] == ["ART-GHOST"]
    assert res["stale_article_ids"] == ["ART-OLD"]
    assert res["bus_factor_risk_article_ids"] == []
    assert res["knowledge_resilience_posture"] == "ORPHANED_KNOWLEDGE_ASSET"


def test_audit_wiki_knowledge_bus_factor_and_freshness_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_ARTICLES_EVALUATED."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness_v1 as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_articles": 0,
            "bus_factor_risk_article_ids": [],
            "stale_article_ids": [],
            "orphaned_article_ids": [],
            "is_knowledge_resilient": True,
            "knowledge_resilience_posture": "NO_ARTICLES_EVALUATED",
        }


def test_audit_wiki_adr_governance_hygiene_governed_catalog():
    """Catálogo ADR con estados válidos, secciones completas y cadena de supersesión hacia ACCEPTED -> GOVERNED_ADR_CATALOG."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_adr_governance_hygiene,
    )

    adrs = [
        {
            "id": "ADR-001",
            "status": "SUPERSEDED",
            "context": "Uso inicial de colas en memoria",
            "decision": "Encolar tareas en memoria local",
            "consequences": "Pérdida en reinicios; reemplazado por ADR-002",
            "superseded_by_id": "ADR-002",
        },
        {
            "adr_id": "ADR-002",
            "status": "ACCEPTED",
            "context": "Persistencia de eventos críticos de proyectos",
            "decision": "Adoptar PostgreSQL transaccional con outbox",
            "consequences": "Garantiza entrega al menos una vez",
        },
    ]
    res = audit_wiki_adr_governance_hygiene(adrs)
    assert res == {
        "total_adrs": 2,
        "accepted_adrs_count": 1,
        "invalid_status_adr_ids": [],
        "incomplete_section_adr_ids": [],
        "broken_supersession_adr_ids": [],
        "is_adr_catalog_governed": True,
        "adr_posture": "GOVERNED_ADR_CATALOG",
    }
    assert WikiPMIService.audit_wiki_adr_governance_hygiene(adrs) == res


def test_audit_wiki_adr_governance_hygiene_broken_supersession_chain():
    """ADR SUPERSEDED sin sucesor válido en estado ACCEPTED -> BROKEN_ADR_SUPERSESSION_CHAIN."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_governance_hygiene

    res = audit_wiki_adr_governance_hygiene(
        [
            {
                "id": "ADR-010",
                "status": "SUPERSEDED",
                "context": "Contexto A",
                "decision": "Decisión A",
                "consequences": "Consecuencia A",
                "superseded_by_id": "ADR-999",
            },
            {
                "id": "ADR-011",
                "status": "SUPERSEDED",
                "context": "Contexto B",
                "decision": "Decisión B",
                "consequences": "Consecuencia B",
                "superseded_by_id": "ADR-011",
            },
        ]
    )
    assert res["broken_supersession_adr_ids"] == ["ADR-010", "ADR-011"]
    assert res["is_adr_catalog_governed"] is False
    assert res["adr_posture"] == "BROKEN_ADR_SUPERSESSION_CHAIN"


def test_audit_wiki_adr_governance_hygiene_incomplete_sections_and_invalid_status():
    """Secciones vacías -> INCOMPLETE_ADR_SECTIONS; estado desconocido -> INVALID_ADR_STATUS."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_governance_hygiene

    res_inc = audit_wiki_adr_governance_hygiene(
        [
            {
                "id": "ADR-020",
                "status": "ACCEPTED",
                "context": "Contexto válido",
                "decision": "Decisión tomada",
                "consequences": "",
            }
        ]
    )
    assert res_inc["incomplete_section_adr_ids"] == ["ADR-020"]
    assert res_inc["is_adr_catalog_governed"] is False
    assert res_inc["adr_posture"] == "INCOMPLETE_ADR_SECTIONS"

    res_stat = audit_wiki_adr_governance_hygiene(
        [
            {
                "id": "ADR-021",
                "status": "DRAFT_UNKNOWN",
                "context": "Contexto válido",
                "decision": "Decisión tomada",
                "consequences": "Impacto evaluado",
            }
        ]
    )
    assert res_stat["invalid_status_adr_ids"] == ["ADR-021"]
    assert res_stat["is_adr_catalog_governed"] is False
    assert res_stat["adr_posture"] == "INVALID_ADR_STATUS"


def test_audit_wiki_adr_governance_hygiene_empty_catalog():
    """Lista vacía o None -> EMPTY_ADR_CATALOG."""
    from backend.services.wiki_pmi_service import audit_wiki_adr_governance_hygiene

    for payload in (None, [], [{"id": ""}]):
        res = audit_wiki_adr_governance_hygiene(payload)
        assert res == {
            "total_adrs": 0,
            "accepted_adrs_count": 0,
            "invalid_status_adr_ids": [],
            "incomplete_section_adr_ids": [],
            "broken_supersession_adr_ids": [],
            "is_adr_catalog_governed": False,
            "adr_posture": "EMPTY_ADR_CATALOG",
        }


def test_audit_wiki_operational_runbook_readiness_operations_ready():
    """Suite de runbooks con rollback, verificación, contacto de guardia y drill <= 90 días -> OPERATIONS_READY_RUNBOOK_SUITE."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_operational_runbook_readiness,
    )

    runbooks = [
        {
            "id": "RB-01",
            "rollback_procedure": "Revertir migración Alembic downgrade -1 y restaurar snapshot RDS",
            "verification_steps": "Ejecutar healthcheck /api/health y verificar latencia p95 < 150ms",
            "oncall_contact": "@sre-oncall-primary",
            "days_since_last_drill": 30,
        },
        {
            "runbook_id": "RB-02",
            "rollback_procedure": "Conmutar tráfico DNS a región secundaria",
            "verification_steps": "Confirmar 0 errores 5xx durante 15 minutos",
            "oncall_contact": "pagerduty://infra-escalation",
            "days_since_last_drill": 90,
        },
    ]
    res = audit_wiki_operational_runbook_readiness(runbooks, max_drill_age_days=90)
    assert res == {
        "total_runbooks": 2,
        "missing_rollback_or_verification_ids": [],
        "missing_oncall_contact_ids": [],
        "stale_drill_runbook_ids": [],
        "is_runbook_suite_ready": True,
        "runbook_posture": "OPERATIONS_READY_RUNBOOK_SUITE",
    }
    assert (
        WikiPMIService.audit_wiki_operational_runbook_readiness(
            runbooks, max_drill_age_days=90
        )
        == res
    )


def test_audit_wiki_operational_runbook_readiness_missing_rollback_or_verification():
    """Runbook sin procedimiento de reversión o sin pasos de verificación -> MISSING_ROLLBACK_OR_VERIFICATION_STEPS."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    res = audit_wiki_operational_runbook_readiness(
        [
            {
                "id": "RB-NO-ROLL",
                "rollback_procedure": "",
                "verification_steps": "Verificar logs",
                "oncall_contact": "@oncall",
                "days_since_last_drill": 15,
            },
            {
                "id": "RB-NO-VERIF",
                "rollback_procedure": "Restaurar backup",
                "verification_steps": "   ",
                "oncall_contact": "@oncall",
                "days_since_last_drill": 20,
            },
        ]
    )
    assert res["total_runbooks"] == 2
    assert res["missing_rollback_or_verification_ids"] == ["RB-NO-ROLL", "RB-NO-VERIF"]
    assert res["is_runbook_suite_ready"] is False
    assert res["runbook_posture"] == "MISSING_ROLLBACK_OR_VERIFICATION_STEPS"


def test_audit_wiki_operational_runbook_readiness_missing_oncall_and_stale_drill():
    """Falta contacto on-call -> MISSING_ONCALL_ESCALATION_CONTACT; drill vencido -> STALE_RUNBOOK_DRILL_VALIDATION."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    res_oncall = audit_wiki_operational_runbook_readiness(
        [
            {
                "id": "RB-NO-ONCALL",
                "rollback_procedure": "Rollback imagen previa",
                "verification_steps": "Smoke test",
                "oncall_contact": "",
                "days_since_last_drill": 10,
            }
        ]
    )
    assert res_oncall["missing_oncall_contact_ids"] == ["RB-NO-ONCALL"]
    assert res_oncall["is_runbook_suite_ready"] is False
    assert res_oncall["runbook_posture"] == "MISSING_ONCALL_ESCALATION_CONTACT"

    res_stale = audit_wiki_operational_runbook_readiness(
        [
            {
                "id": "RB-STALE",
                "rollback_procedure": "Rollback imagen previa",
                "verification_steps": "Smoke test",
                "oncall_contact": "@sre",
                "days_since_last_drill": 120,
            },
            {
                "id": "RB-NEVER",
                "rollback_procedure": "Rollback imagen previa",
                "verification_steps": "Smoke test",
                "oncall_contact": "@sre",
                "days_since_last_drill": None,
            },
        ],
        max_drill_age_days=90,
    )
    assert res_stale["stale_drill_runbook_ids"] == ["RB-STALE", "RB-NEVER"]
    assert res_stale["is_runbook_suite_ready"] is False
    assert res_stale["runbook_posture"] == "STALE_RUNBOOK_DRILL_VALIDATION"


def test_audit_wiki_operational_runbook_readiness_empty_or_none():
    """Lista vacía o None -> NO_OPERATIONAL_RUNBOOKS."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    for payload in (None, [], [{"id": ""}]):
        res = audit_wiki_operational_runbook_readiness(payload)
        assert res == {
            "total_runbooks": 0,
            "missing_rollback_or_verification_ids": [],
            "missing_oncall_contact_ids": [],
            "stale_drill_runbook_ids": [],
            "is_runbook_suite_ready": False,
            "runbook_posture": "NO_OPERATIONAL_RUNBOOKS",
        }


def test_audit_wiki_meeting_minutes_governance_governed():
    """Actas con quórum >= 75%, decisiones/summary y compromisos con owner_id y due_date -> GOVERNED_MEETING_MINUTES."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_meeting_minutes_governance,
    )

    meetings = [
        {
            "id": "MTG-01",
            "invited_count": 8,
            "attended_count": 6,
            "summary": "Revisión semanal de cronograma y riesgos",
            "decisions": ["Aprobar CR-12"],
            "action_items": [
                {"owner_id": "USR-1", "due_date": "2026-10-25"},
                {"owner_id": "USR-2", "due_date": "2026-10-30"},
            ],
        },
        {
            "meeting_id": "MTG-02",
            "invited_count": 4,
            "attended_count": 4,
            "summary": "",
            "decisions": ["Congelar alcance de sprint"],
            "action_items": [],
        },
    ]
    res = audit_wiki_meeting_minutes_governance(meetings, min_attendance_rate_pct=75.0)
    assert res == {
        "total_meetings": 2,
        "low_quorum_meeting_ids": [],
        "undocumented_outcome_meeting_ids": [],
        "unassigned_action_item_meeting_ids": [],
        "is_meeting_governance_valid": True,
        "meeting_posture": "GOVERNED_MEETING_MINUTES",
    }
    assert (
        WikiPMIService.audit_wiki_meeting_minutes_governance(
            meetings, min_attendance_rate_pct=75.0
        )
        == res
    )


def test_audit_wiki_meeting_minutes_governance_unassigned_action_items():
    """Compromisos sin owner_id o sin due_date -> UNASSIGNED_MEETING_ACTION_ITEMS."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    res = audit_wiki_meeting_minutes_governance(
        [
            {
                "id": "MTG-AI-1",
                "invited_count": 5,
                "attended_count": 5,
                "summary": "Minuta con compromiso sin responsable",
                "action_items": [{"owner_id": "", "due_date": "2026-11-01"}],
            },
            {
                "id": "MTG-AI-2",
                "invited_count": 4,
                "attended_count": 4,
                "summary": "Minuta con compromiso sin fecha",
                "action_items": [{"owner_id": "USR-9", "due_date": "   "}],
            },
        ]
    )
    assert res["total_meetings"] == 2
    assert res["unassigned_action_item_meeting_ids"] == ["MTG-AI-1", "MTG-AI-2"]
    assert res["is_meeting_governance_valid"] is False
    assert res["meeting_posture"] == "UNASSIGNED_MEETING_ACTION_ITEMS"


def test_audit_wiki_meeting_minutes_governance_undocumented_outcome_and_low_quorum():
    """Sin summary ni decisiones -> UNDOCUMENTED_MEETING_OUTCOMES; quórum bajo -> INSUFFICIENT_MEETING_QUORUM."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    res_undoc = audit_wiki_meeting_minutes_governance(
        [
            {
                "id": "MTG-EMPTY",
                "invited_count": 6,
                "attended_count": 5,
                "summary": "   ",
                "decisions": [],
            }
        ]
    )
    assert res_undoc["undocumented_outcome_meeting_ids"] == ["MTG-EMPTY"]
    assert res_undoc["is_meeting_governance_valid"] is False
    assert res_undoc["meeting_posture"] == "UNDOCUMENTED_MEETING_OUTCOMES"

    res_quorum = audit_wiki_meeting_minutes_governance(
        [
            {
                "id": "MTG-LOW-Q",
                "invited_count": 10,
                "attended_count": 5,
                "summary": "Sesión con baja asistencia",
            },
            {
                "id": "MTG-ZERO-INV",
                "invited_count": 0,
                "attended_count": 0,
                "summary": "Sesión sin convocados registrados",
            },
        ],
        min_attendance_rate_pct=75.0,
    )
    assert res_quorum["low_quorum_meeting_ids"] == ["MTG-LOW-Q", "MTG-ZERO-INV"]
    assert res_quorum["is_meeting_governance_valid"] is False
    assert res_quorum["meeting_posture"] == "INSUFFICIENT_MEETING_QUORUM"


def test_audit_wiki_meeting_minutes_governance_no_meetings():
    """Lista vacía, None o registros sin id -> NO_MEETING_MINUTES."""
    from backend.services.wiki_pmi_service import audit_wiki_meeting_minutes_governance

    for payload in (None, [], [{"id": ""}]):
        res = audit_wiki_meeting_minutes_governance(payload)
        assert res == {
            "total_meetings": 0,
            "low_quorum_meeting_ids": [],
            "undocumented_outcome_meeting_ids": [],
            "unassigned_action_item_meeting_ids": [],
            "is_meeting_governance_valid": False,
            "meeting_posture": "NO_MEETING_MINUTES",
        }



def test_audit_wiki_postmortem_root_cause_governance_governed():
    """> Cadena de whys suficiente, línea de tiempo y CAPA accionable -> GOVERNED."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_postmortem_root_cause_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "PM-1",
                "whys_chain": ["W1", "W2", "W3"],
                "incident_timeline": "2026-10-01 caída del servicio",
                "capa_items": [
                    {"owner_id": "u-1", "due_date": "2026-10-20"},
                ],
            },
            {
                "postmortem_id": "PM-2",
                "whys_chain": ["W1", "W2", "W3", "W4"],
                "incident_timeline": "segunda caída",
                "capa_items": [
                    {"owner_id": "u-2", "due_date": "2026-10-25"},
                    {"owner_id": "u-3", "due_date": "2026-10-27"},
                ],
            },
        ],
        min_whys_depth=3,
    )
    assert res["total_postmortems"] == 2
    assert res["shallow_rca_postmortem_ids"] == []
    assert res["missing_timeline_postmortem_ids"] == []
    assert res["unactionable_capa_postmortem_ids"] == []
    assert res["is_postmortem_governance_valid"] is True
    assert res["postmortem_posture"] == "GOVERNED_BLAMELESS_POSTMORTEMS"


def test_audit_wiki_postmortem_root_cause_governance_shallow_and_missing_timeline():
    """> Whys insuficientes y línea de tiempo ausente; precedencia CAPA primero."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_postmortem_root_cause_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "PM-SHALLOW",
                "whys_chain": ["W1"],
                "incident_timeline": "ok",
                "capa_items": [{"owner_id": "u-1", "due_date": "2026-10-20"}],
            },
            {
                "id": "PM-NO-TL",
                "whys_chain": ["W1", "W2", "W3"],
                "incident_timeline": "",
                "capa_items": [{"owner_id": "u-1", "due_date": "2026-10-20"}],
            },
            {
                "id": "PM-OK",
                "whys_chain": ["W1", "W2", "W3"],
                "incident_timeline": "ok",
                "capa_items": [{"owner_id": "u-1", "due_date": "2026-10-20"}],
            },
        ],
        min_whys_depth=3,
    )
    assert res["total_postmortems"] == 3
    assert res["shallow_rca_postmortem_ids"] == ["PM-SHALLOW"]
    assert res["missing_timeline_postmortem_ids"] == ["PM-NO-TL"]
    assert res["unactionable_capa_postmortem_ids"] == []
    assert res["is_postmortem_governance_valid"] is False
    assert res["postmortem_posture"] == "SHALLOW_ROOT_CAUSE_ANALYSIS"


def test_audit_wiki_postmortem_root_cause_governance_unactionable_capa():
    """> CAPA vacía o sin dueño/fecha domina la postura (precedencia 1)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_postmortem_root_cause_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "PM-EMPTY",
                "whys_chain": ["W1", "W2", "W3"],
                "incident_timeline": "ok",
                "capa_items": [],
            },
            {
                "id": "PM-BLANK",
                "whys_chain": ["W1", "W2", "W3"],
                "incident_timeline": "ok",
                "capa_items": [
                    {"owner_id": "u-1", "due_date": "2026-10-20"},
                    {"owner_id": "", "due_date": "2026-10-22"},
                    {"owner_id": "u-2", "due_date": None},
                ],
            },
            {
                "id": "PM-SHALLOW-TOO",
                "whys_chain": ["W1"],
                "incident_timeline": "",
                "capa_items": [{"owner_id": "u-1", "due_date": "x"}],
            },
        ]
    )
    assert res["total_postmortems"] == 3
    assert res["unactionable_capa_postmortem_ids"] == ["PM-EMPTY", "PM-BLANK"]
    assert res["shallow_rca_postmortem_ids"] == ["PM-SHALLOW-TOO"]
    assert res["missing_timeline_postmortem_ids"] == ["PM-SHALLOW-TOO"]
    assert res["is_postmortem_governance_valid"] is False
    assert res["postmortem_posture"] == "UNACTIONABLE_POSTMORTEM_CAPA"


def test_audit_wiki_postmortem_root_cause_governance_empty_or_none():
    """None, lista vacía, entradas no-dict o sin id -> NO_POSTMORTEMS_RECORDED."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_postmortem_root_cause_governance as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, {"whys_chain": ["W1"]}]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_postmortems": 0,
            "shallow_rca_postmortem_ids": [],
            "missing_timeline_postmortem_ids": [],
            "unactionable_capa_postmortem_ids": [],
            "is_postmortem_governance_valid": False,
            "postmortem_posture": "NO_POSTMORTEMS_RECORDED",
        }


def test_audit_wiki_benefits_realization_governance_governed():
    """Beneficios con dueño, baseline/target cuantificados, cadencia válida y alineación estratégica -> is_governed True."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_benefits_realization_governance,
    )

    records = [
        {
            "benefit_id": "BEN-01",
            "benefit_owner": "Dir. Pastoral",
            "baseline_value": 100.0,
            "target_value": 200.0,
            "realized_value": 150.0,
            "measurement_cadence": "Quarterly",
            "strategic_alignment_linked": True,
        },
        {
            "benefit_id": "BEN-02",
            "benefit_owner": "Dir. Operaciones",
            "baseline_value": 50.0,
            "target_value": 10.0,
            "realized_value": 10.0,
            "measurement_cadence": "monthly",
            "strategic_alignment_linked": True,
        },
    ]
    res = audit_wiki_benefits_realization_governance(records)
    assert res == {
        "evaluated_benefit_count": 2,
        "unowned_benefit_ids": [],
        "unquantified_target_ids": [],
        "missing_cadence_ids": [],
        "unaligned_benefit_ids": [],
        "average_attainment_pct": 75.0,
        "is_governed": True,
    }
    assert WikiPMIService.audit_wiki_benefits_realization_governance(records) == res


def test_audit_wiki_benefits_realization_governance_unowned_and_unquantified():
    """Sin benefit_owner o target == baseline / None -> unowned_benefit_ids y unquantified_target_ids poblados."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_benefits_realization_governance,
    )

    res = audit_wiki_benefits_realization_governance(
        [
            {
                "benefit_id": "BEN-NO-OWNER",
                "benefit_owner": "   ",
                "baseline_value": 10.0,
                "target_value": 10.0,
                "realized_value": 10.0,
                "measurement_cadence": "annual",
                "strategic_alignment_linked": True,
            },
            {
                "benefit_id": "BEN-NO-TARGET",
                "benefit_owner": "Coordinador",
                "baseline_value": 20.0,
                "target_value": None,
                "realized_value": 25.0,
                "measurement_cadence": "milestone",
                "strategic_alignment_linked": True,
            },
        ]
    )
    assert res["evaluated_benefit_count"] == 2
    assert res["unowned_benefit_ids"] == ["BEN-NO-OWNER"]
    assert res["unquantified_target_ids"] == ["BEN-NO-OWNER", "BEN-NO-TARGET"]
    assert res["average_attainment_pct"] == 0.0
    assert res["is_governed"] is False


def test_audit_wiki_benefits_realization_governance_missing_cadence_and_unaligned():
    """Cadencia inválida y sin vínculo estratégico -> missing_cadence_ids y unaligned_benefit_ids poblados."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_benefits_realization_governance,
    )

    res = audit_wiki_benefits_realization_governance(
        [
            {
                "benefit_id": "BEN-BAD-CAD",
                "benefit_owner": "PMO",
                "baseline_value": 0.0,
                "target_value": 100.0,
                "realized_value": 120.0,
                "measurement_cadence": "ad_hoc",
                "strategic_alignment_linked": False,
            }
        ]
    )
    assert res == {
        "evaluated_benefit_count": 1,
        "unowned_benefit_ids": [],
        "unquantified_target_ids": [],
        "missing_cadence_ids": ["BEN-BAD-CAD"],
        "unaligned_benefit_ids": ["BEN-BAD-CAD"],
        "average_attainment_pct": 100.0,
        "is_governed": False,
    }


def test_audit_wiki_benefits_realization_governance_empty_or_invalid():
    """Lista vacía, None o entradas sin benefit_id -> evaluated_benefit_count 0, is_governed False."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_benefits_realization_governance,
    )

    for payload in (None, [], [{"benefit_id": "  "}], ["invalid"]):
        res = audit_wiki_benefits_realization_governance(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_benefit_count": 0,
            "unowned_benefit_ids": [],
            "unquantified_target_ids": [],
            "missing_cadence_ids": [],
            "unaligned_benefit_ids": [],
            "average_attainment_pct": 0.0,
            "is_governed": False,
        }


def test_audit_wiki_knowledge_bus_factor_and_freshness_v2_resilient():
    """> Críticos multi-autor con peer review y frescos -> is_resilient True."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness,
    )

    res = audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-ARCH",
                "domain_criticality": "critical",
                "contributor_ids": ["ana", "luis", "ana"],
                "days_since_last_review": 30,
                "peer_reviewed": True,
            },
            {
                "article_id": "KB-HIGH",
                "domain_criticality": "High",
                "contributor_ids": ["sofia", "pedro"],
                "days_since_last_review": 90,  # == tope, no stale
                "peer_reviewed": True,
            },
        ],
        max_stale_days=90,
    )
    assert res["evaluated_article_count"] == 2
    assert res["unauthored_article_ids"] == []
    assert res["single_author_critical_article_ids"] == []
    assert res["unreviewed_critical_article_ids"] == []
    assert res["stale_article_ids"] == []
    assert res["is_resilient"] is True

    from backend.services.wiki_pmi_service import WikiPMIService

    static_res = WikiPMIService.audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-ARCH",
                "domain_criticality": "critical",
                "contributor_ids": ["ana", "luis"],
                "days_since_last_review": 30,
                "peer_reviewed": True,
            },
        ]
    )
    assert static_res["is_resilient"] is True


def test_audit_wiki_knowledge_bus_factor_and_freshness_v2_unauthored_and_bus_factor():
    """> Sin autores (ignora None) y crítico con<=1 contribuyente -> bus-factor."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness,
    )

    res = audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-GHOST",
                "domain_criticality": "high",
                "contributor_ids": [None, "  ", ""],
                "days_since_last_review": 5,
                "peer_reviewed": True,
            },
            {
                "article_id": "KB-SOLO",
                "domain_criticality": "critical",
                "contributor_ids": ["josue"],
                "days_since_last_review": 10,
                "peer_reviewed": True,
            },
            {
                "article_id": "KB-STANDARD-SOLO",
                "domain_criticality": "standard",
                "contributor_ids": ["marta"],
                "days_since_last_review": 20,
                "peer_reviewed": False,
            },
        ]
    )
    assert res["evaluated_article_count"] == 3
    assert res["unauthored_article_ids"] == ["KB-GHOST"]
    # Spec literal: crítico con <= 1 contribuyente, incluido el caso de 0 autores.
    assert res["single_author_critical_article_ids"] == ["KB-GHOST", "KB-SOLO"]
    assert res["unreviewed_critical_article_ids"] == []
    assert res["stale_article_ids"] == []
    assert res["is_resilient"] is False


def test_audit_wiki_knowledge_bus_factor_and_freshness_v2_unreviewed_critical():
    """> Crítico multi-autor sin peer review -> unreviewed_critical (precedencia posture n/a)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness,
    )

    res = audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-NOREV",
                "domain_criticality": "CRITICAL",
                "contributor_ids": ["ana", "luis"],
                "days_since_last_review": 15,
                "peer_reviewed": False,
            },
            {
                "article_id": "KB-OK",
                "domain_criticality": "standard",
                "contributor_ids": ["rita"],
                "days_since_last_review": 15,
            },
        ]
    )
    assert res["evaluated_article_count"] == 2
    assert res["unreviewed_critical_article_ids"] == ["KB-NOREV"]
    assert res["single_author_critical_article_ids"] == []
    assert res["unauthored_article_ids"] == []
    assert res["stale_article_ids"] == []
    assert res["is_resilient"] is False


def test_audit_wiki_knowledge_bus_factor_and_freshness_v2_stale_and_empty():
    """> Review > max_stale_days configurable; None/vacío/basura -> is_resilient False."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_bus_factor_and_freshness,
    )

    res_stale = audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-OLD",
                "days_since_last_review": 91,
                "peer_reviewed": True,
            },
            {
                "article_id": "KB-EDGE",
                "days_since_last_review": 90,  # == tope, no stale
            },
        ],
        max_stale_days=90,
    )
    assert res_stale["stale_article_ids"] == ["KB-OLD"]
    assert res_stale["is_resilient"] is False

    res_relaxed = audit_wiki_knowledge_bus_factor_and_freshness(
        [
            {
                "article_id": "KB-EDGE",
                "contributor_ids": ["rita"],
                "days_since_last_review": 91.5,
            },
        ],
        max_stale_days=120,
    )
    assert res_relaxed["stale_article_ids"] == []
    assert res_relaxed["is_resilient"] is True

    for payload in (None, [], ["no-dict", 42, {"domain_criticality": "high"}]):
        assert audit_wiki_knowledge_bus_factor_and_freshness(payload) == {  # type: ignore[arg-type]
            "evaluated_article_count": 0,
            "unauthored_article_ids": [],
            "single_author_critical_article_ids": [],
            "unreviewed_critical_article_ids": [],
            "stale_article_ids": [],
            "is_resilient": False,
        }


def test_audit_wiki_raci_matrix_governance_deliverables_compliant():
    """Entregables con exactamente 1 Accountable único, >=1 Responsible y Consulted dentro del límite pasan is_raci_compliant=True."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_raci_matrix_governance,
    )

    assignments = [
        {
            "deliverable_id": "DEL-01",
            "responsible_ids": ["dev-1", "dev-2", "dev-1"],
            "accountable_ids": ["pm-1", "  ", None],
            "consulted_ids": ["sec-1", "ops-1"],
            "informed_ids": ["sponsor-1"],
        },
        {
            "deliverable_id": "DEL-02",
            "responsible_ids": ["qa-1"],
            "accountable_ids": ["pm-1"],
            "consulted_ids": [],
            "informed_ids": [],
        },
    ]
    res = audit_wiki_raci_matrix_governance(
        assignments, max_consulted_per_deliverable=5
    )
    assert res == {
        "evaluated_deliverable_count": 2,
        "missing_accountable_deliverable_ids": [],
        "multiple_accountable_deliverable_ids": [],
        "missing_responsible_deliverable_ids": [],
        "excessive_consulted_deliverable_ids": [],
        "is_raci_compliant": True,
    }
    assert (
        WikiPMIService.audit_wiki_raci_matrix_governance(
            assignments, max_consulted_per_deliverable=5
        )
        == res
    )


def test_audit_wiki_raci_matrix_governance_missing_and_multiple_accountable():
    """Detecta entregables sin Accountable o con múltiples Accountables únicos."""
    from backend.services.wiki_pmi_service import audit_wiki_raci_matrix_governance

    res = audit_wiki_raci_matrix_governance(
        [
            {
                "deliverable_id": "DEL-NO-A",
                "responsible_ids": ["dev-1"],
                "accountable_ids": ["", None],
            },
            {
                "deliverable_id": "DEL-MULTI-A",
                "responsible_ids": ["dev-1"],
                "accountable_ids": ["dir-1", "dir-2"],
            },
        ]
    )
    assert res == {
        "evaluated_deliverable_count": 2,
        "missing_accountable_deliverable_ids": ["DEL-NO-A"],
        "multiple_accountable_deliverable_ids": ["DEL-MULTI-A"],
        "missing_responsible_deliverable_ids": [],
        "excessive_consulted_deliverable_ids": [],
        "is_raci_compliant": False,
    }


def test_audit_wiki_raci_matrix_governance_missing_responsible_and_excessive_consulted():
    """Detecta entregables sin Responsible y con exceso de Consulted (> max_consulted_per_deliverable)."""
    from backend.services.wiki_pmi_service import audit_wiki_raci_matrix_governance

    res = audit_wiki_raci_matrix_governance(
        [
            {
                "deliverable_id": "DEL-NO-R-OVER-C",
                "responsible_ids": [],
                "accountable_ids": ["pm-1"],
                "consulted_ids": ["c1", "c2", "c3", "c4"],
            }
        ],
        max_consulted_per_deliverable=3,
    )
    assert res == {
        "evaluated_deliverable_count": 1,
        "missing_accountable_deliverable_ids": [],
        "multiple_accountable_deliverable_ids": [],
        "missing_responsible_deliverable_ids": ["DEL-NO-R-OVER-C"],
        "excessive_consulted_deliverable_ids": ["DEL-NO-R-OVER-C"],
        "is_raci_compliant": False,
    }


def test_audit_wiki_raci_matrix_governance_deliverables_empty_or_invalid():
    """Lista vacía, None o entradas sin deliverable_id -> evaluated_deliverable_count 0, is_raci_compliant False."""
    from backend.services.wiki_pmi_service import audit_wiki_raci_matrix_governance

    for payload in (None, [], [{"deliverable_id": "   "}], ["invalid"]):
        assert audit_wiki_raci_matrix_governance(payload) == {  # type: ignore[arg-type]
            "evaluated_deliverable_count": 0,
            "missing_accountable_deliverable_ids": [],
            "multiple_accountable_deliverable_ids": [],
            "missing_responsible_deliverable_ids": [],
            "excessive_consulted_deliverable_ids": [],
            "is_raci_compliant": False,
        }



def test_audit_wiki_raid_log_traceability_governance_compliant():
    """Entradas RAID trazables y en regla -> 100% y compliant (incl. staticmethod)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raid_log_traceability_governance,
        WikiPMIService,
    )

    res = audit_wiki_raid_log_traceability_governance(
        [
            {
                "entry_id": "R-1",
                "category": "Risk",
                "owner_id": "u-1",
                "linked_wbs_code": "1.2.3",
                "resolution_plan": "mitigación contratista",
                "is_overdue": False,
                "status": "open",
            },
            {
                "entry_id": "D-1",
                "category": "DEPENDENCY",
                "owner_id": "u-2",
                "linked_wbs_code": "2.1",
                "resolution_plan": "coordinar proveedor",
                "status": "Closed",
            },
        ]
    )
    assert res["total_entries"] == 2
    assert res["invalid_category_entry_ids"] == []
    assert res["untraceable_entry_ids"] == []
    assert res["at_risk_open_entry_ids"] == []
    assert res["traceability_rate_pct"] == 100.0
    assert res["is_raid_governance_compliant"] is True

    static_res = WikiPMIService.audit_wiki_raid_log_traceability_governance(
        [
            {
                "entry_id": "R-1",
                "category": "risk",
                "owner_id": "u-1",
                "linked_wbs_code": "1.2.3",
                "resolution_plan": "mitigar",
            },
        ]
    )
    assert static_res["is_raid_governance_compliant"] is True


def test_audit_wiki_raid_log_traceability_governance_invalid_category_and_untraceable():
    """> Categorías inválidas y entradas sin owner o sin WBS -> listas separadas."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raid_log_traceability_governance,
    )

    res = audit_wiki_raid_log_traceability_governance(
        [
            {"entry_id": "R-BAD", "category": "milestone", "owner_id": "u-1", "linked_wbs_code": "1.1"},
            {"entry_id": "A-NO-OWNER", "category": "assumption", "linked_wbs_code": "1.2"},
            {"entry_id": "I-NO-WBS", "category": "issue", "owner_id": "u-3", "resolution_plan": "corregir"},
            {"entry_id": "R-OK", "category": "risk", "owner_id": "u-4", "linked_wbs_code": "3.4"},
        ]
    )
    assert res["total_entries"] == 4
    assert res["invalid_category_entry_ids"] == ["R-BAD"]
    assert res["untraceable_entry_ids"] == ["A-NO-OWNER", "I-NO-WBS"]
    # I-NO-WBS tiene plan ("corregir"); las otras 3 abiertas sin plan -> at_risk.
    assert res["at_risk_open_entry_ids"] == ["R-BAD", "A-NO-OWNER", "R-OK"]
    assert res["traceability_rate_pct"] == 50.0
    assert res["is_raid_governance_compliant"] is False


def test_audit_wiki_raid_log_traceability_governance_overdue_open_vs_closed():
    """> Abiertas vencidas o sin plan -> at_risk; cerradas/resueltas/retiradas exentas."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raid_log_traceability_governance,
    )

    res = audit_wiki_raid_log_traceability_governance(
        [
            {
                "entry_id": "R-OVERDUE",
                "category": "risk",
                "owner_id": "u-1",
                "linked_wbs_code": "1.1",
                "resolution_plan": "plan",
                "is_overdue": True,
            },
            {
                "entry_id": "I-NO-PLAN",
                "category": "issue",
                "owner_id": "u-2",
                "linked_wbs_code": "1.2",
                "is_overdue": False,
            },
            {
                "entry_id": "A-RETIRED-NO-PLAN",
                "category": "assumption",
                "owner_id": "u-3",
                "linked_wbs_code": "1.3",
                "status": "retired",
            },
            {
                "entry_id": "D-OVERDUE-CLOSED",
                "category": "dependency",
                "owner_id": "u-4",
                "linked_wbs_code": "1.4",
                "is_overdue": True,
                "status": "resolved",
            },
        ]
    )
    assert res["total_entries"] == 4
    assert res["at_risk_open_entry_ids"] == ["R-OVERDUE", "I-NO-PLAN"]
    assert res["untraceable_entry_ids"] == []
    assert res["invalid_category_entry_ids"] == []
    assert res["is_raid_governance_compliant"] is False


def test_audit_wiki_raid_log_traceability_governance_empty_or_none():
    """None, no-secuencia, str, Mapping o entradas malformadas -> 0 entradas."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_raid_log_traceability_governance,
    )

    empty_result = {
        "total_entries": 0,
        "invalid_category_entry_ids": [],
        "untraceable_entry_ids": [],
        "at_risk_open_entry_ids": [],
        "traceability_rate_pct": 0.0,
        "is_raid_governance_compliant": False,
    }

    for payload in (None, "raid-string", {"entry_id": "R1"}, 42, [], ["no-dict", {"category": "risk"}]):
        assert audit_wiki_raid_log_traceability_governance(payload) == empty_result  # type: ignore[arg-type]


def test_audit_wiki_definition_of_ready_gate_hygiene_sprint_ready():
    """Items con criterios de aceptación, puntos estimados, dependencias despejadas y spec vinculada pasan is_sprint_ready=True."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_definition_of_ready_gate_hygiene,
    )

    items = [
        {
            "item_id": "US-101",
            "acceptance_criteria_count": 3,
            "story_points_estimated": True,
            "dependencies_cleared": True,
            "ux_or_tech_spec_linked": True,
        },
        {
            "item_id": "US-102",
            "acceptance_criteria_count": 2,
            "story_points_estimated": True,
            "dependencies_cleared": True,
            "ux_or_tech_spec_linked": True,
        },
    ]
    res = audit_wiki_definition_of_ready_gate_hygiene(items)
    assert res == {
        "total_items": 2,
        "missing_acceptance_criteria_item_ids": [],
        "unestimated_item_ids": [],
        "blocked_dependency_item_ids": [],
        "missing_spec_link_item_ids": [],
        "dor_pass_rate_pct": 100.0,
        "is_sprint_ready": True,
    }
    assert WikiPMIService.audit_wiki_definition_of_ready_gate_hygiene(items) == res


def test_audit_wiki_definition_of_ready_gate_hygiene_missing_ac_and_unestimated():
    """Detecta historias sin criterios de aceptación (<1) o sin estimación de story points."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_gate_hygiene,
    )

    res = audit_wiki_definition_of_ready_gate_hygiene(
        [
            {
                "item_id": "US-NO-AC",
                "acceptance_criteria_count": 0,
                "story_points_estimated": True,
                "dependencies_cleared": True,
                "ux_or_tech_spec_linked": True,
            },
            {
                "item_id": "US-NO-EST",
                "acceptance_criteria_count": 2,
                "story_points_estimated": False,
                "dependencies_cleared": True,
                "ux_or_tech_spec_linked": True,
            },
        ]
    )
    assert res == {
        "total_items": 2,
        "missing_acceptance_criteria_item_ids": ["US-NO-AC"],
        "unestimated_item_ids": ["US-NO-EST"],
        "blocked_dependency_item_ids": [],
        "missing_spec_link_item_ids": [],
        "dor_pass_rate_pct": 0.0,
        "is_sprint_ready": False,
    }


def test_audit_wiki_definition_of_ready_gate_hygiene_blocked_and_missing_spec():
    """Detecta dependencias bloqueadas y ausencia de vínculo UX/Tech Spec."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_gate_hygiene,
    )

    res = audit_wiki_definition_of_ready_gate_hygiene(
        [
            {
                "item_id": "US-READY",
                "acceptance_criteria_count": 4,
                "story_points_estimated": True,
                "dependencies_cleared": True,
                "ux_or_tech_spec_linked": True,
            },
            {
                "item_id": "US-BLK-SPEC",
                "acceptance_criteria_count": 2,
                "story_points_estimated": True,
                "dependencies_cleared": False,
                "ux_or_tech_spec_linked": False,
            },
        ]
    )
    assert res == {
        "total_items": 2,
        "missing_acceptance_criteria_item_ids": [],
        "unestimated_item_ids": [],
        "blocked_dependency_item_ids": ["US-BLK-SPEC"],
        "missing_spec_link_item_ids": ["US-BLK-SPEC"],
        "dor_pass_rate_pct": 50.0,
        "is_sprint_ready": False,
    }


def test_audit_wiki_definition_of_ready_gate_hygiene_empty_or_invalid():
    """Entradas vacías, None o no-secuencia devuelven total_items=0 e is_sprint_ready=False."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_gate_hygiene,
    )

    for payload in (None, [], "invalid", {"item_id": "U1"}, [{"item_id": "   "}]):
        assert audit_wiki_definition_of_ready_gate_hygiene(payload) == {  # type: ignore[arg-type]
            "total_items": 0,
            "missing_acceptance_criteria_item_ids": [],
            "unestimated_item_ids": [],
            "blocked_dependency_item_ids": [],
            "missing_spec_link_item_ids": [],
            "dor_pass_rate_pct": 0.0,
            "is_sprint_ready": False,
        }



def test_audit_wiki_retrospective_action_closure_governance_healthy():
    """Cerradas con impacto verificado y abiertas en plazo -> healthy + staticmethod."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_retrospective_action_closure_governance,
    )

    res = audit_wiki_retrospective_action_closure_governance(
        [
            {
                "action_id": "RA-1",
                "owner_id": "u-1",
                "status": "closed",
                "impact_verified": True,
            },
            {
                "action_id": "RA-2",
                "owner_id": "u-2",
                "due_sprint": 3,
                "current_sprint": 3,
            },
            {
                "action_id": "RA-3",
                "owner_id": "u-3",
                "status": "verified",
                "impact_verified": True,
                "due_sprint": 2,
                "current_sprint": 4,
            },
        ]
    )
    assert res["total_actions"] == 3
    assert res["unassigned_action_ids"] == []
    assert res["overdue_sprint_action_ids"] == []
    assert res["unverified_closure_action_ids"] == []
    assert res["closure_effectiveness_pct"] == 66.67
    assert res["is_retrospective_governance_healthy"] is True

    static_res = WikiPMIService.audit_wiki_retrospective_action_closure_governance(
        [
            {
                "action_id": "RA-1",
                "owner_id": "u-1",
                "status": "done",
                "impact_verified": True,
            },
        ]
    )
    assert static_res["is_retrospective_governance_healthy"] is True


def test_audit_wiki_retrospective_action_closure_governance_unassigned_and_overdue():
    """> Sin owner y abiertas vencidas (current > due) -> listas separadas."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_retrospective_action_closure_governance,
    )

    res = audit_wiki_retrospective_action_closure_governance(
        [
            {"action_id": "RA-GHOST", "due_sprint": 3, "current_sprint": 5},
            {
                "action_id": "RA-LATE",
                "owner_id": "u-2",
                "due_sprint": 2,
                "current_sprint": 4,
                "status": "open",
            },
            {
                "action_id": "RA-ON-TIME",
                "owner_id": "u-3",
                "due_sprint": 4,
                "current_sprint": 4,
                "status": "open",
            },
            {
                "action_id": "RA-CLOSED-NO-DUE",
                "owner_id": "u-4",
                "status": "closed",
                "impact_verified": True,
            },
        ]
    )
    assert res["total_actions"] == 4
    assert res["unassigned_action_ids"] == ["RA-GHOST"]
    assert res["overdue_sprint_action_ids"] == ["RA-GHOST", "RA-LATE"]
    assert res["unverified_closure_action_ids"] == []
    assert res["closure_effectiveness_pct"] == 25.0
    assert res["is_retrospective_governance_healthy"] is False


def test_audit_wiki_retrospective_action_closure_governance_unverified_closure():
    """> Cerradas sin impact_verified -> unverified; exentas del overdue."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_retrospective_action_closure_governance,
    )

    res = audit_wiki_retrospective_action_closure_governance(
        [
            {
                "action_id": "RA-NO-IMPACT",
                "owner_id": "u-1",
                "status": "CLOSED",
                "impact_verified": False,
                "due_sprint": 1,
                "current_sprint": 7,
            },
            {
                "action_id": "RA-IMPACT",
                "owner_id": "u-2",
                "status": "done",
                "impact_verified": True,
            },
        ]
    )
    assert res["total_actions"] == 2
    assert res["unverified_closure_action_ids"] == ["RA-NO-IMPACT"]
    assert res["overdue_sprint_action_ids"] == []
    assert res["unassigned_action_ids"] == []
    assert res["closure_effectiveness_pct"] == 50.0
    assert res["is_retrospective_governance_healthy"] is False


def test_audit_wiki_retrospective_action_closure_governance_empty_or_none():
    """None, no-secuencia, str, Mapping, 42 o basura -> 0 acciones."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_retrospective_action_closure_governance,
    )

    empty_result = {
        "total_actions": 0,
        "unassigned_action_ids": [],
        "overdue_sprint_action_ids": [],
        "unverified_closure_action_ids": [],
        "closure_effectiveness_pct": 0.0,
        "is_retrospective_governance_healthy": False,
    }

    for payload in (
        None,
        "retro-actions-string",
        {"action_id": "X"},
        42,
        [],
        ["no-dict", {"status": "closed"}],
        [{"action_id": "   "}],
    ):
        assert audit_wiki_retrospective_action_closure_governance(payload) == empty_result  # type: ignore[arg-type]

    # IDs válidos con ids numéricos basura: cuentan (2) y quedan sin owner.
    res_bad_types = audit_wiki_retrospective_action_closure_governance(
        [{"action_id": "RA", "due_sprint": "x"}, {"action_id": "RB", "current_sprint": None}]
    )
    assert res_bad_types == {
        "total_actions": 2,
        "unassigned_action_ids": ["RA", "RB"],
        "overdue_sprint_action_ids": [],
        "unverified_closure_action_ids": [],
        "closure_effectiveness_pct": 0.0,
        "is_retrospective_governance_healthy": False,
    }


def test_audit_wiki_monte_carlo_contingency_governance_valid():
    """Iteraciones >= 1000, curva monotónica y contingencia >= P80 - base -> valid True."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_monte_carlo_contingency_governance,
    )

    sim = {
        "iterations": 5000,
        "base_estimate": 100000.0,
        "p50_cost": 105000.0,
        "p80_cost": 115000.0,
        "p90_cost": 122000.0,
        "allocated_contingency": 16000.0,
    }
    res = audit_wiki_monte_carlo_contingency_governance(sim)
    assert res == {
        "iterations": 5000,
        "required_p80_contingency": 15000.0,
        "allocated_contingency": 16000.0,
        "contingency_shortfall": 0.0,
        "governance_gaps": [],
        "is_simulation_governance_valid": True,
    }
    assert WikiPMIService.audit_wiki_monte_carlo_contingency_governance(sim) == res


def test_audit_wiki_monte_carlo_contingency_governance_insufficient_iterations_and_shortfall():
    """Iteraciones < 1000 y contingencia < requerida en P80 reportan brechas en orden canónico."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_monte_carlo_contingency_governance,
    )

    res = audit_wiki_monte_carlo_contingency_governance(
        {
            "iterations": 500,
            "base_estimate": 100000.0,
            "p50_cost": 108000.0,
            "p80_cost": 120000.0,
            "p90_cost": 130000.0,
            "allocated_contingency": 12000.0,
        }
    )
    assert res == {
        "iterations": 500,
        "required_p80_contingency": 20000.0,
        "allocated_contingency": 12000.0,
        "contingency_shortfall": 8000.0,
        "governance_gaps": [
            "insufficient_simulation_iterations",
            "contingency_below_p80_threshold",
        ],
        "is_simulation_governance_valid": False,
    }


def test_audit_wiki_monte_carlo_contingency_governance_non_monotonic_curve():
    """Percentiles invertidos (ej. p80 < p50) -> non_monotonic_percentile_curve."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_monte_carlo_contingency_governance,
    )

    res = audit_wiki_monte_carlo_contingency_governance(
        {
            "iterations": 2000,
            "base_estimate": 100000.0,
            "p50_cost": 125000.0,
            "p80_cost": 115000.0,
            "p90_cost": 130000.0,
            "allocated_contingency": 20000.0,
        }
    )
    assert res == {
        "iterations": 2000,
        "required_p80_contingency": 15000.0,
        "allocated_contingency": 20000.0,
        "contingency_shortfall": 0.0,
        "governance_gaps": ["non_monotonic_percentile_curve"],
        "is_simulation_governance_valid": False,
    }


def test_audit_wiki_monte_carlo_contingency_governance_empty_or_non_mapping():
    """Entrada None, vacía o no Mapping activa insufficient_simulation_iterations y non_monotonic_percentile_curve."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_monte_carlo_contingency_governance,
    )

    for payload in (None, {}, "invalid", []):
        assert audit_wiki_monte_carlo_contingency_governance(payload) == {  # type: ignore[arg-type]
            "iterations": 0,
            "required_p80_contingency": 0.0,
            "allocated_contingency": 0.0,
            "contingency_shortfall": 0.0,
            "governance_gaps": [
                "insufficient_simulation_iterations",
                "non_monotonic_percentile_curve",
            ],
            "is_simulation_governance_valid": False,
        }


def test_audit_wiki_make_or_buy_and_source_selection_governance_healthy():
    """Decisiones make y buy íntegras con TCO cuantificado, pesos 100%, protección IP y estimación independiente -> healthy."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_make_or_buy_and_source_selection_governance,
    )

    decisions = [
        {
            "item_id": "MOB-CORE-AUTH",
            "decision": "make",
            "internal_cost_estimate": 45000.0,
            "strategic_core_competency": True,
        },
        {
            "id": "MOB-CLOUD-CDN",
            "decision": "buy",
            "internal_cost_estimate": 90000.0,
            "external_cost_estimate": 38000.0,
            "strategic_core_competency": False,
            "evaluation_criteria_weights": {
                "technical_capability": 40.0,
                "tco_price": 35.0,
                "sla_references": 25.0,
            },
            "independent_estimate_prepared": True,
        },
    ]
    res = audit_wiki_make_or_buy_and_source_selection_governance(decisions)
    assert res == {
        "total_evaluated": 2,
        "buy_or_lease_count": 1,
        "unquantified_tco_item_ids": [],
        "core_competency_outsourced_without_mitigation_ids": [],
        "unbalanced_criteria_weight_item_ids": [],
        "missing_independent_estimate_item_ids": [],
        "is_procurement_governance_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_wiki_make_or_buy_and_source_selection_governance_unquantified_and_core_critical():
    """Ítems sin TCO cuantificado o externalización de competencia núcleo sin ip_protection_strategy -> critical."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_make_or_buy_and_source_selection_governance,
    )

    res = audit_wiki_make_or_buy_and_source_selection_governance(
        [
            {
                "item_id": "MOB-NO-TCO",
                "decision": "buy",
                "internal_cost_estimate": 50000.0,
                "external_cost_estimate": 0.0,
                "evaluation_criteria_weights": [{"weight_pct": 100.0}],
                "independent_estimate_prepared": True,
            },
            {
                "item_id": "MOB-CORE-LEAK",
                "decision": "lease",
                "internal_cost_estimate": 60000.0,
                "external_cost_estimate": 40000.0,
                "strategic_core_competency": True,
                "ip_protection_strategy": "   ",
                "evaluation_criteria_weights": [{"weight": 100.0}],
                "independent_estimate_prepared": True,
            },
        ]
    )
    assert res["unquantified_tco_item_ids"] == ["MOB-NO-TCO"]
    assert res["core_competency_outsourced_without_mitigation_ids"] == [
        "MOB-CORE-LEAK"
    ]
    assert res["is_procurement_governance_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 2


def test_audit_wiki_make_or_buy_and_source_selection_governance_unbalanced_weights_and_missing_ice_warning():
    """Matriz de criterios cuyos pesos no suman 100% o falta de independent_estimate_prepared -> warning."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_make_or_buy_and_source_selection_governance,
    )

    res = audit_wiki_make_or_buy_and_source_selection_governance(
        [
            {
                "item_id": "MOB-BAD-WEIGHTS",
                "decision": "hybrid",
                "internal_cost_estimate": 30000.0,
                "external_cost_estimate": 25000.0,
                "evaluation_criteria_weights": {"cost": 50.0, "quality": 30.0},
                "independent_estimate_prepared": False,
            }
        ]
    )
    assert res["buy_or_lease_count"] == 1
    assert res["unbalanced_criteria_weight_item_ids"] == ["MOB-BAD-WEIGHTS"]
    assert res["missing_independent_estimate_item_ids"] == ["MOB-BAD-WEIGHTS"]
    assert res["is_procurement_governance_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_audit_wiki_make_or_buy_and_source_selection_governance_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía WikiPMIService.audit_wiki_make_or_buy_and_source_selection_governance."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_make_or_buy_and_source_selection_governance,
    )

    for payload in (None, [], "invalid", [{"item_id": "  "}]):
        res = audit_wiki_make_or_buy_and_source_selection_governance(payload)  # type: ignore[arg-type]
        assert res["total_evaluated"] == 0
        assert res["buy_or_lease_count"] == 0
        assert res["is_procurement_governance_compliant"] is True
        assert res["status"] == "healthy"

    sample = [{"item_id": "M-1", "decision": "make", "internal_cost_estimate": 1000.0}]
    assert (
        WikiPMIService.audit_wiki_make_or_buy_and_source_selection_governance(
            sample
        )
        == audit_wiki_make_or_buy_and_source_selection_governance(sample)
    )


def test_audit_wiki_opa_template_versioning_governance_healthy():
    """Catálogo OPA con semver válido, custodia PMO al día y plantillas deprecadas con reemplazo y 0 proyectos activos (healthy)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_template_versioning_governance,
    )

    templates = [
        {
            "template_id": "OPA-TPL-CHARTER-V2",
            "semver": "2.1.0",
            "status": "active",
            "days_since_last_review": 90,
            "pmo_steward": "pmo.governance@ccf.org",
        },
        {
            "template_id": "OPA-TPL-CHARTER-V1",
            "version": "1.4.2-legacy",
            "status": "deprecated",
            "replacement_template_id": "OPA-TPL-CHARTER-V2",
            "active_projects_using_count": 0,
        },
    ]
    res = audit_wiki_opa_template_versioning_governance(templates, max_review_age_days=365.0)
    assert res == {
        "total_templates": 2,
        "invalid_semver_template_ids": [],
        "deprecated_without_replacement_ids": [],
        "active_usage_on_deprecated_template_ids": [],
        "stale_or_unowned_active_template_ids": [],
        "is_opa_governance_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_wiki_opa_template_versioning_governance_critical_semver_and_deprecated_violations():
    """Plantilla deprecada sin replacement_template_id o en uso por proyectos activos, y semver inválido (critical)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_template_versioning_governance,
    )

    templates = [
        {
            "template_id": "OPA-BAD-VER",
            "semver": "v2-final-final",
            "status": "active",
            "days_since_last_review": 30,
            "pmo_steward": "pmo@ccf.org",
        },
        {
            "template_id": "OPA-DEP-NO-REPL",
            "semver": "1.0.0",
            "status": "superseded",
            "replacement_template_id": "   ",
            "active_projects_using_count": 3,
        },
    ]
    res = audit_wiki_opa_template_versioning_governance(templates)
    assert res["total_templates"] == 2
    assert res["invalid_semver_template_ids"] == ["OPA-BAD-VER"]
    assert res["deprecated_without_replacement_ids"] == ["OPA-DEP-NO-REPL"]
    assert res["active_usage_on_deprecated_template_ids"] == ["OPA-DEP-NO-REPL"]
    assert res["stale_or_unowned_active_template_ids"] == []
    assert res["is_opa_governance_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 3


def test_audit_wiki_opa_template_versioning_governance_warning_stale_or_unowned_active():
    """Plantilla activa con days_since_last_review > max_review_age_days o sin pmo_steward (warning)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_template_versioning_governance,
    )

    templates = [
        {
            "template_id": "OPA-STALE",
            "semver": "3.0",
            "status": "active",
            "days_since_last_review": 410,
            "pmo_steward": "pmo@ccf.org",
        },
        {
            "template_id": "OPA-UNOWNED",
            "semver": "1.2.0",
            "status": "active",
            "days_since_last_review": 45,
            "pmo_steward": "",
        },
    ]
    res = audit_wiki_opa_template_versioning_governance(templates, max_review_age_days=365.0)
    assert res["total_templates"] == 2
    assert res["invalid_semver_template_ids"] == []
    assert res["deprecated_without_replacement_ids"] == []
    assert res["active_usage_on_deprecated_template_ids"] == []
    assert res["stale_or_unowned_active_template_ids"] == ["OPA-STALE", "OPA-UNOWNED"]
    assert res["is_opa_governance_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 1


def test_audit_wiki_opa_template_versioning_governance_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía WikiPMIService.audit_wiki_opa_template_versioning_governance."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_opa_template_versioning_governance,
    )

    for payload in (None, [], "invalid", [{"id": "  "}]):
        res = audit_wiki_opa_template_versioning_governance(payload)  # type: ignore[arg-type]
        assert res["total_templates"] == 0
        assert res["is_opa_governance_compliant"] is True
        assert res["status"] == "healthy"

    sample = [
        {
            "id": "OPA-OK",
            "semver": "1.0.0",
            "status": "active",
            "days_since_last_review": 10,
            "pmo_steward": "steward@ccf.org",
        }
    ]
    assert (
        WikiPMIService.audit_wiki_opa_template_versioning_governance(sample)
        == audit_wiki_opa_template_versioning_governance(sample)
    )



def test_audit_wiki_rbs_coverage_complete():
    """Categorias con riesgos, owner y triggers documentados -> coverage completa."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_breakdown_structure_coverage,
    )

    categories = [
        {
            "category_code": "RBS-EXT",
            "risks_identified_count": 4,
            "has_assigned_risk_owner": True,
            "has_trigger_conditions_documented": True,
        },
        {
            "id": "RBS-TEC",
            "risks_identified_count": 7,
            "has_assigned_risk_owner": True,
            "has_trigger_conditions_documented": True,
        },
        {
            "category_code": "RBS-QTY",
            "risks_identified_count": 2,
            "has_assigned_risk_owner": True,
            "has_trigger_conditions_documented": True,
        },
    ]
    res = audit_wiki_risk_breakdown_structure_coverage(categories)
    assert res == {
        "total_evaluated": 3,
        "blind_spot_category_ids": [],
        "unowned_risk_category_ids": [],
        "missing_trigger_category_ids": [],
        "is_rbs_coverage_complete": True,
    }


def test_audit_wiki_rbs_coverage_blind_spots_and_unowned():
    """Blind spot (riesgos < minimo) y categorias sin owner asignado."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_breakdown_structure_coverage,
    )

    categories = [
        {"category_code": "RBS-1"},  # 0 riesgos < 1 -> blind spot.
        {"category_code": "RBS-2", "risks_identified_count": 2},  # sin owner.
        {
            "category_code": "RBS-3",
            "risks_identified_count": 2,
            "has_assigned_risk_owner": True,
        },  # sin trigger.
    ]
    res = audit_wiki_risk_breakdown_structure_coverage(categories)
    assert res["total_evaluated"] == 3
    assert res["blind_spot_category_ids"] == ["RBS-1"]
    assert res["unowned_risk_category_ids"] == ["RBS-2"]
    assert res["missing_trigger_category_ids"] == ["RBS-2", "RBS-3"]
    assert res["is_rbs_coverage_complete"] is False

    # Umbral personalizado eleva el minimo de riesgos por categoria.
    strict = audit_wiki_risk_breakdown_structure_coverage(categories, min_risks_per_category=4)
    assert strict["blind_spot_category_ids"] == ["RBS-1", "RBS-2", "RBS-3"]


def test_audit_wiki_rbs_coverage_not_applicable_excluded():
    """is_applicable excluye de las 3 listas; coerción segura de contadores."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_breakdown_structure_coverage,
    )

    categories = [
        {"category_code": "RBS-NA", "is_applicable": False},
        {"category_code": "RBS-OK", "risks_identified_count": 2,
         "has_assigned_risk_owner": True, "has_trigger_conditions_documented": True},
        # Coercion segura ante errores/None: tratado como 0 riesgos.
        {"category_code": "RBS-BAD", "risks_identified_count": None},
        {"category_code": "RBS-WOW", "risks_identified_count": "oops"},
    ]
    res = audit_wiki_risk_breakdown_structure_coverage(categories)
    assert res["total_evaluated"] == 4
    assert res["blind_spot_category_ids"] == ["RBS-BAD", "RBS-WOW"]
    assert res["unowned_risk_category_ids"] == []
    assert res["missing_trigger_category_ids"] == []
    assert res["is_rbs_coverage_complete"] is False


def test_audit_wiki_rbs_coverage_empty_and_service_proxy():
    """Entradas vacias/None/invalidas + llamada via WikiPMIService (staticmethod + __all__)."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_risk_breakdown_structure_coverage,
    )
    import backend.services.wiki_pmi_service as _m

    res_none = audit_wiki_risk_breakdown_structure_coverage(None)
    assert res_none == {
        "total_evaluated": 0,
        "blind_spot_category_ids": [],
        "unowned_risk_category_ids": [],
        "missing_trigger_category_ids": [],
        "is_rbs_coverage_complete": True,
    }
    assert audit_wiki_risk_breakdown_structure_coverage("not-a-sequence")["total_evaluated"] == 0
    assert (
        audit_wiki_risk_breakdown_structure_coverage(
            ["not-a-mapping", {"category_code": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "audit_wiki_risk_breakdown_structure_coverage" in _m.__all__

    sample = [
        {
            "category_code": "RBS-1",
            "risks_identified_count": 2,
            "has_assigned_risk_owner": True,
            "has_trigger_conditions_documented": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_risk_breakdown_structure_coverage(sample)
        == audit_wiki_risk_breakdown_structure_coverage(sample)
    )


def test_audit_wiki_onboarding_and_kt_handover_readiness_compliant():
    """Paquetes KT con arquitectura, guía local, shadowing >= 1, signoff y rampup en rango -> ready True."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_onboarding_and_kt_handover_readiness,
    )

    packages = [
        {
            "package_id": "KT-BACKEND",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": True,
            "shadowing_sessions_completed": 3,
            "successor_signoff_confirmed": True,
            "estimated_rampup_days": 5,
        },
        {
            "id": "KT-FRONTEND",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": True,
            "shadowing_sessions_completed": 1,
            "successor_signoff_confirmed": True,
            "estimated_rampup_days": 10,
        },
    ]
    res = audit_wiki_onboarding_and_kt_handover_readiness(packages)
    assert res == {
        "total_evaluated": 2,
        "incomplete_documentation_package_ids": [],
        "unverified_handover_package_ids": [],
        "excessive_rampup_package_ids": [],
        "is_kt_handover_ready": True,
    }
    assert (
        WikiPMIService.audit_wiki_onboarding_and_kt_handover_readiness(packages)
        == res
    )


def test_audit_wiki_onboarding_and_kt_handover_readiness_incomplete_doc_and_unverified():
    """Detecta falta de walkthrough/guía local y falta de shadowing o signoff del sucesor."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_and_kt_handover_readiness,
    )

    packages = [
        {
            "package_id": "KT-NO-DOC",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": False,
            "shadowing_sessions_completed": 2,
            "successor_signoff_confirmed": True,
            "estimated_rampup_days": 4,
        },
        {
            "package_id": "KT-NO-SIGNOFF",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": True,
            "shadowing_sessions_completed": 0,
            "successor_signoff_confirmed": False,
            "estimated_rampup_days": 6,
        },
    ]
    res = audit_wiki_onboarding_and_kt_handover_readiness(packages)
    assert res["total_evaluated"] == 2
    assert res["incomplete_documentation_package_ids"] == ["KT-NO-DOC"]
    assert res["unverified_handover_package_ids"] == ["KT-NO-SIGNOFF"]
    assert res["excessive_rampup_package_ids"] == []
    assert res["is_kt_handover_ready"] is False


def test_audit_wiki_onboarding_and_kt_handover_readiness_excessive_rampup():
    """Rampup <= 0 o > max_onboarding_days se reporta en excessive_rampup_package_ids."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_and_kt_handover_readiness,
    )

    packages = [
        {
            "package_id": "KT-ZERO",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": True,
            "shadowing_sessions_completed": 2,
            "successor_signoff_confirmed": True,
            "estimated_rampup_days": 0,
        },
        {
            "package_id": "KT-SLOW",
            "has_architecture_walkthrough": True,
            "has_local_env_setup_guide": True,
            "shadowing_sessions_completed": 2,
            "successor_signoff_confirmed": True,
            "estimated_rampup_days": 14,
        },
    ]
    res = audit_wiki_onboarding_and_kt_handover_readiness(
        packages, max_onboarding_days=10
    )
    assert res["total_evaluated"] == 2
    assert res["incomplete_documentation_package_ids"] == []
    assert res["unverified_handover_package_ids"] == []
    assert res["excessive_rampup_package_ids"] == ["KT-ZERO", "KT-SLOW"]
    assert res["is_kt_handover_ready"] is False


def test_audit_wiki_onboarding_and_kt_handover_readiness_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin package_id válido y verifica exportación en __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_and_kt_handover_readiness,
    )

    assert "audit_wiki_onboarding_and_kt_handover_readiness" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"abc"), [{"package_id": "  "}, 123]):
        res = audit_wiki_onboarding_and_kt_handover_readiness(bad)
        assert res == {
            "total_evaluated": 0,
            "incomplete_documentation_package_ids": [],
            "unverified_handover_package_ids": [],
            "excessive_rampup_package_ids": [],
            "is_kt_handover_ready": True,
        }


def test_audit_wiki_vendor_sla_and_penalty_clause_governance_sound():
    """Acuerdos SLA con disponibilidad [95, 100], tiempo de respuesta > 0, penalización y telemetría."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_vendor_sla_and_penalty_clause_governance,
    )

    slas = [
        {
            "sla_id": "SLA-CLOUD-01",
            "uptime_target_pct": 99.95,
            "max_incident_response_minutes": 15,
            "has_service_credit_or_penalty_clause": True,
            "breach_termination_threshold_defined": True,
            "measurement_telemetry_automated": True,
        },
        {
            "id": "SLA-SEC-02",
            "uptime_target_pct": 95.0,
            "max_incident_response_minutes": 30,
            "has_service_credit_or_penalty_clause": True,
            "breach_termination_threshold_defined": True,
            "measurement_telemetry_automated": True,
        },
    ]
    res = audit_wiki_vendor_sla_and_penalty_clause_governance(slas)
    assert res == {
        "total_evaluated": 2,
        "invalid_target_bounds_sla_ids": [],
        "toothless_penalty_clause_sla_ids": [],
        "unmonitored_sla_ids": [],
        "is_vendor_sla_governance_sound": True,
    }
    assert (
        WikiPMIService.audit_wiki_vendor_sla_and_penalty_clause_governance(slas)
        == res
    )


def test_audit_wiki_vendor_sla_invalid_bounds_and_unmonitored():
    """Detecta disponibilidad fuera de [95, 100], tiempo de respuesta <= 0 y falta de telemetría."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_vendor_sla_and_penalty_clause_governance,
    )

    slas = [
        {
            "sla_id": "SLA-LOW-UPTIME",
            "uptime_target_pct": 92.0,
            "max_incident_response_minutes": 30,
            "has_service_credit_or_penalty_clause": True,
            "breach_termination_threshold_defined": True,
            "measurement_telemetry_automated": True,
        },
        {
            "sla_id": "SLA-ZERO-RESP",
            "uptime_target_pct": 99.9,
            "max_incident_response_minutes": 0,
            "has_service_credit_or_penalty_clause": True,
            "breach_termination_threshold_defined": True,
            "measurement_telemetry_automated": False,
        },
    ]
    res = audit_wiki_vendor_sla_and_penalty_clause_governance(slas)
    assert res["total_evaluated"] == 2
    assert res["invalid_target_bounds_sla_ids"] == [
        "SLA-LOW-UPTIME",
        "SLA-ZERO-RESP",
    ]
    assert res["toothless_penalty_clause_sla_ids"] == []
    assert res["unmonitored_sla_ids"] == ["SLA-ZERO-RESP"]
    assert res["is_vendor_sla_governance_sound"] is False


def test_audit_wiki_vendor_sla_toothless_penalty_clauses():
    """Detecta SLAs sin cláusula de crédito/penalización o sin umbral de rescisión por incumplimiento."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_vendor_sla_and_penalty_clause_governance,
    )

    slas = [
        {
            "sla_id": "SLA-NO-CREDIT",
            "uptime_target_pct": 99.5,
            "max_incident_response_minutes": 60,
            "has_service_credit_or_penalty_clause": False,
            "breach_termination_threshold_defined": True,
            "measurement_telemetry_automated": True,
        },
        {
            "sla_id": "SLA-NO-TERM",
            "uptime_target_pct": 99.5,
            "max_incident_response_minutes": 60,
            "has_service_credit_or_penalty_clause": True,
            "breach_termination_threshold_defined": False,
            "measurement_telemetry_automated": True,
        },
    ]
    res = audit_wiki_vendor_sla_and_penalty_clause_governance(slas)
    assert res["total_evaluated"] == 2
    assert res["invalid_target_bounds_sla_ids"] == []
    assert res["toothless_penalty_clause_sla_ids"] == [
        "SLA-NO-CREDIT",
        "SLA-NO-TERM",
    ]
    assert res["unmonitored_sla_ids"] == []
    assert res["is_vendor_sla_governance_sound"] is False


def test_audit_wiki_vendor_sla_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin sla_id válido y verifica exportación en __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_vendor_sla_and_penalty_clause_governance,
    )

    assert "audit_wiki_vendor_sla_and_penalty_clause_governance" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"xyz"), [{"sla_id": "  "}, 42]):
        assert audit_wiki_vendor_sla_and_penalty_clause_governance(bad) == {
            "total_evaluated": 0,
            "invalid_target_bounds_sla_ids": [],
            "toothless_penalty_clause_sla_ids": [],
            "unmonitored_sla_ids": [],
            "is_vendor_sla_governance_sound": True,
        }



def test_audit_wiki_assumption_log_governance_compliant():
    """Supuestos y restricciones con owner, dominio, vigencia y conversion correcta."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumption_and_constraint_log_governance,
    )

    entries = [
        {
            "entry_id": "AS-1",
            "entry_type": "Assumption",
            "owner_id": "PM-1",
            "impact_domain": "cost",
            "validation_status": "valid",
            "days_since_last_review": 5.0,
        },
        {
            "entry_id": "CO-1",
            "entry_type": "CONSTRAINT",
            "owner_id": "PM-2",
            "impact_domain": "schedule",
            "validation_status": "active",
            "days_since_last_review": 30.0,  # borde == umbral -> no stale.
        },
    ]
    res = audit_wiki_assumption_and_constraint_log_governance(entries)
    assert res == {
        "total_entries": 2,
        "assumption_count": 1,
        "constraint_count": 1,
        "invalid_type_entry_ids": [],
        "unassigned_or_unscoped_entry_ids": [],
        "unconverted_false_assumption_ids": [],
        "stale_unreviewed_entry_ids": [],
        "is_assumption_log_compliant": True,
    }


def test_audit_wiki_assumption_log_governance_invalid_type_and_unscoped():
    """Tipos fuera de assumption/constraint y entradas sin owner o impact_domain."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumption_and_constraint_log_governance,
    )

    entries = [
        {"entry_id": "X-1", "entry_type": "risk", "owner_id": "PM-1",
         "impact_domain": "quality", "validation_status": "active",
         "days_since_last_review": 1.0},
        {"entry_id": "X-2", "entry_type": "assumption",
         "validation_status": "valid", "days_since_last_review": 1.0},  # sin owner ni dominio.
        {"entry_id": "X-3", "entry_type": "constraint", "owner_id": "PM-2",
         "validation_status": "active", "days_since_last_review": 1.0},  # sin dominio.
    ]
    res = audit_wiki_assumption_and_constraint_log_governance(entries)
    assert res["total_entries"] == 3
    assert res["assumption_count"] == 1
    assert res["constraint_count"] == 1
    assert res["invalid_type_entry_ids"] == ["X-1"]
    assert res["unassigned_or_unscoped_entry_ids"] == ["X-2", "X-3"]
    assert res["is_assumption_log_compliant"] is False


def test_audit_wiki_assumption_log_governance_false_assumptions_and_stale():
    """Supuesto invalidado-falso sin conversion a riesgo y entradas stale (> umbral)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumption_and_constraint_log_governance,
    )

    entries = [
        {"entry_id": "U-1", "entry_type": "assumption", "owner_id": "PM-1",
         "impact_domain": "scope", "validation_status": "invalidated_false",
         "days_since_last_review": 1.0},  # sin converted_risk_id.
        {"entry_id": "U-2", "entry_type": "assumption", "owner_id": "PM-1",
         "impact_domain": "scope", "validation_status": "invalidated_false",
         "converted_risk_id": "RISK-7", "days_since_last_review": 1.0},  # convertido OK.
        {"entry_id": "U-3", "entry_type": "constraint", "owner_id": "PM-2",
         "impact_domain": "cost", "validation_status": "unvalidated",
         "days_since_last_review": 40.0},  # stale > 30.
        {"entry_id": "U-4", "entry_type": "constraint", "owner_id": "PM-2",
         "impact_domain": "cost", "validation_status": "retired",
         "days_since_last_review": 400.0},  # retired exento.
    ]
    res = audit_wiki_assumption_and_constraint_log_governance(entries)
    assert res["unconverted_false_assumption_ids"] == ["U-1"]
    assert res["stale_unreviewed_entry_ids"] == ["U-3"]
    assert res["is_assumption_log_compliant"] is False

    strict = audit_wiki_assumption_and_constraint_log_governance(
        entries, max_validation_cycle_days=10
    )
    assert strict["stale_unreviewed_entry_ids"] == ["U-3"]


def test_audit_wiki_assumption_log_governance_empty_and_service_proxy():
    """Entradas vacias/None/invalidas + llamada via WikiPMIService (staticmethod + __all__)."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_assumption_and_constraint_log_governance,
    )
    import backend.services.wiki_pmi_service as _m

    res_none = audit_wiki_assumption_and_constraint_log_governance(None)
    assert res_none == {
        "total_entries": 0,
        "assumption_count": 0,
        "constraint_count": 0,
        "invalid_type_entry_ids": [],
        "unassigned_or_unscoped_entry_ids": [],
        "unconverted_false_assumption_ids": [],
        "stale_unreviewed_entry_ids": [],
        "is_assumption_log_compliant": True,
    }
    assert audit_wiki_assumption_and_constraint_log_governance("no-seq")["total_entries"] == 0
    assert (
        audit_wiki_assumption_and_constraint_log_governance(
            ["no-map", {"entry_id": "   "}, {"other_id": "x"}]
        )["total_entries"]
        == 0
    )
    assert "audit_wiki_assumption_and_constraint_log_governance" in _m.__all__

    sample = [
        {"entry_id": "AS-1", "entry_type": "assumption", "owner_id": "PM-1",
         "impact_domain": "cost", "validation_status": "valid",
         "days_since_last_review": 3.0},
    ]
    assert (
        WikiPMIService.audit_wiki_assumption_and_constraint_log_governance(sample)
        == audit_wiki_assumption_and_constraint_log_governance(sample)
    )
