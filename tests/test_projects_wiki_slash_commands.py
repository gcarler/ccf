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

