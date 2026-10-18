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


def test_audit_wiki_operational_runbook_readiness_production_ready():
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


def test_audit_wiki_operational_runbook_readiness_missing_rollback():
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


def test_audit_wiki_operational_runbook_readiness_incomplete_structure():
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


def test_audit_wiki_operational_runbook_readiness_empty_content():
    """None o texto vacío -> EMPTY_RUNBOOK_CONTENT con score 0.0."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_readiness,
    )

    for empty_val in (None, "", "   "):
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


def test_audit_wiki_meeting_minutes_governance_governed_minutes():
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


def test_audit_wiki_meeting_minutes_governance_unassigned_actions():
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


def test_audit_wiki_meeting_minutes_governance_incomplete_structure():
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


def test_audit_wiki_meeting_minutes_governance_not_a_meeting_minute():
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

    for payload in (None, "", fenced_only):
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
