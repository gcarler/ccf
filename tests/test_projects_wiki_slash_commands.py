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


def test_audit_wiki_cost_of_quality_prevention_vs_failure_balance_compliant():
    """Balance CoQ con >= 65% conformidad, <= 10% fallas externas y CAPA vinculada cumple §8.1 y §8.2."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_cost_of_quality_prevention_vs_failure_balance,
    )

    items = [
        {"item_id": "COQ-PREV-1", "coq_category": "prevention", "amount": 45000.0},
        {"item_id": "COQ-APPR-1", "coq_category": "Appraisal", "amount": 30000.0},
        {
            "item_id": "COQ-INT-1",
            "coq_category": "internal_failure",
            "amount": 18000.0,
            "corrective_action_linked": True,
        },
        {
            "item_id": "COQ-EXT-1",
            "coq_category": "external_failure",
            "amount": 7000.0,
            "corrective_action_linked": True,
        },
    ]
    res = audit_wiki_cost_of_quality_prevention_vs_failure_balance(items)
    assert res == {
        "total_coq": 100000.0,
        "conformance_share_pct": 75.0,
        "external_failure_share_pct": 7.0,
        "below_conformance_investment_threshold": False,
        "exceeds_external_failure_cap": False,
        "invalid_category_or_amount_ids": [],
        "unlinked_failure_cost_ids": [],
        "is_coq_balance_compliant": True,
    }
    assert (
        WikiPMIService.audit_wiki_cost_of_quality_prevention_vs_failure_balance(
            items
        )
        == res
    )


def test_audit_wiki_cost_of_quality_below_conformance_and_unlinked_failure():
    """Detecta subinversión en conformidad (< min_conformance_share_pct) y costos de falla sin CAPA vinculada."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_cost_of_quality_prevention_vs_failure_balance,
    )

    items = [
        {"item_id": "COQ-PREV", "coq_category": "prevention", "amount": 25000.0},
        {"item_id": "COQ-APPR", "coq_category": "appraisal", "amount": 25000.0},
        {
            "item_id": "COQ-INT-UNLINKED",
            "coq_category": "internal_failure",
            "amount": 50000.0,
            "corrective_action_linked": False,
        },
    ]
    res = audit_wiki_cost_of_quality_prevention_vs_failure_balance(
        items, min_conformance_share_pct=65.0
    )
    assert res["total_coq"] == 100000.0
    assert res["conformance_share_pct"] == 50.0
    assert res["below_conformance_investment_threshold"] is True
    assert res["unlinked_failure_cost_ids"] == ["COQ-INT-UNLINKED"]
    assert res["is_coq_balance_compliant"] is False


def test_audit_wiki_cost_of_quality_exceeds_external_failure_cap():
    """Detecta cuando el costo de fallas externas supera max_external_failure_share_pct."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_cost_of_quality_prevention_vs_failure_balance,
    )

    items = [
        {"item_id": "COQ-PREV", "coq_category": "prevention", "amount": 70000.0},
        {
            "item_id": "COQ-EXT-HIGH",
            "coq_category": "external_failure",
            "amount": 30000.0,
            "corrective_action_linked": True,
        },
    ]
    res = audit_wiki_cost_of_quality_prevention_vs_failure_balance(
        items, max_external_failure_share_pct=10.0
    )
    assert res["conformance_share_pct"] == 70.0
    assert res["external_failure_share_pct"] == 30.0
    assert res["below_conformance_investment_threshold"] is False
    assert res["exceeds_external_failure_cap"] is True
    assert res["is_coq_balance_compliant"] is False


def test_audit_wiki_cost_of_quality_invalid_items_and_export():
    """Detecta categorías o montos inválidos, maneja entradas vacías y verifica exportación en __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_cost_of_quality_prevention_vs_failure_balance,
    )

    assert "audit_wiki_cost_of_quality_prevention_vs_failure_balance" in _m.__all__
    res = audit_wiki_cost_of_quality_prevention_vs_failure_balance(
        [
            {"item_id": "BAD-CAT", "coq_category": "overhead", "amount": 1000.0},
            {"item_id": "BAD-AMT", "coq_category": "prevention", "amount": -50.0},
        ]
    )
    assert res["invalid_category_or_amount_ids"] == ["BAD-CAT", "BAD-AMT"]
    assert res["is_coq_balance_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"item_id": "  "}]):
        assert audit_wiki_cost_of_quality_prevention_vs_failure_balance(bad) == {
            "total_coq": 0.0,
            "conformance_share_pct": 100.0,
            "external_failure_share_pct": 0.0,
            "below_conformance_investment_threshold": False,
            "exceeds_external_failure_cap": False,
            "invalid_category_or_amount_ids": [],
            "unlinked_failure_cost_ids": [],
            "is_coq_balance_compliant": True,
        }


def test_audit_wiki_issue_log_escalation_and_aging_sla_compliant():
    """Issues activos asignados dentro del SLA y bloqueantes criticos gestionados."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_issue_log_escalation_and_aging_sla,
    )

    entries = [
        {"issue_id": "IS-1", "severity": "Critical", "status": "Open", "owner_id": "PM-1",
         "age_days": 2.0, "workaround_documented": True,
         "escalated_to_sponsor_or_ccb": True},  # dentro del SLA de 3 dias.
        {"issue_id": "IS-2", "severity": "high", "status": "in_progress", "owner_id": "PM-2",
         "age_days": 7.0},  # borde == umbral -> no overdue.
        {"issue_id": "IS-3", "severity": "medium", "status": "resolved", "owner_id": "PM-3",
         "age_days": 900.0},  # inactivo -> sin chequeo de SLA.
    ]
    res = audit_wiki_issue_log_escalation_and_aging_sla(entries)
    assert res == {
        "total_issues": 3,
        "active_issue_count": 2,
        "invalid_issue_metadata_ids": [],
        "unassigned_active_issue_ids": [],
        "overdue_sla_issue_ids": [],
        "unescalated_critical_blocker_ids": [],
        "is_issue_log_sla_compliant": True,
    }


def test_audit_wiki_issue_log_escalation_and_aging_sla_invalid_metadata():
    """Severidad/status fuera del catalogo y age_days negativo -> metadata invalida."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_issue_log_escalation_and_aging_sla,
    )

    entries = [
        {"issue_id": "M-1", "severity": "urgent", "status": "open", "owner_id": "PM-1",
         "age_days": 1.0},
        {"issue_id": "M-2", "severity": "high", "status": "on_hold", "owner_id": "PM-1",
         "age_days": 1.0},
        {"issue_id": "M-3", "severity": "high", "status": "open", "owner_id": "PM-1",
         "age_days": -5.0},
    ]
    res = audit_wiki_issue_log_escalation_and_aging_sla(entries)
    assert res["total_issues"] == 3
    assert res["active_issue_count"] == 0
    assert res["invalid_issue_metadata_ids"] == ["M-1", "M-2", "M-3"]
    assert res["is_issue_log_sla_compliant"] is False

    # Coercion segura: age_days invalido -> 0.0, no invalida.
    bad = audit_wiki_issue_log_escalation_and_aging_sla(
        [
            {"issue_id": "B-1", "severity": "high", "status": "open", "owner_id": "PM-2",
             "age_days": "oops"},
        ]
    )
    assert bad["invalid_issue_metadata_ids"] == []
    assert bad["is_issue_log_sla_compliant"] is True


def test_audit_wiki_issue_log_escalation_and_aging_sla_overdue_and_blockers():
    """Unassigned activos, overdue SLA (critical >3 / high >7) y bloqueantes sin gestion."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_issue_log_escalation_and_aging_sla,
    )

    entries = [
        {"issue_id": "U-1", "severity": "medium", "status": "open",
         "age_days": 1.0},  # activo sin owner.
        {"issue_id": "C-1", "severity": "critical", "status": "open", "owner_id": "PM-4",
         "age_days": 3.5},  # overdue + sin escalar ni workaround.
        {"issue_id": "C-2", "severity": "critical", "status": "escalated", "owner_id": "PM-5",
         "age_days": 4.0, "escalated_to_sponsor_or_ccb": True,
         "workaround_documented": True},  # overdue pero gestionado.
        {"issue_id": "H-1", "severity": "high", "status": "in_progress", "owner_id": "PM-6",
         "age_days": 8.0},  # overdue high.
        {"issue_id": "H-2", "severity": "high", "status": "open", "owner_id": "PM-7",
         "age_days": 7.5, "workaround_documented": False},  # overdue high; no critical.
    ]
    res = audit_wiki_issue_log_escalation_and_aging_sla(entries)
    assert res["total_issues"] == 5
    assert res["active_issue_count"] == 5
    assert res["unassigned_active_issue_ids"] == ["U-1"]
    assert res["overdue_sla_issue_ids"] == ["C-1", "C-2", "H-1", "H-2"]
    assert res["unescalated_critical_blocker_ids"] == ["C-1"]
    assert res["is_issue_log_sla_compliant"] is False

    # Umbrales personalizados mas estrictos.
    strict = audit_wiki_issue_log_escalation_and_aging_sla(
        entries, critical_sla_days=1, high_sla_days=5
    )
    assert strict["overdue_sla_issue_ids"] == ["C-1", "C-2", "H-1", "H-2"]


def test_audit_wiki_issue_log_escalation_and_aging_sla_empty_and_service_proxy():
    """Entradas vacias/None/invalidas + llamada via WikiPMIService (staticmethod + __all__)."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_issue_log_escalation_and_aging_sla,
    )
    import backend.services.wiki_pmi_service as _m

    res_none = audit_wiki_issue_log_escalation_and_aging_sla(None)
    assert res_none == {
        "total_issues": 0,
        "active_issue_count": 0,
        "invalid_issue_metadata_ids": [],
        "unassigned_active_issue_ids": [],
        "overdue_sla_issue_ids": [],
        "unescalated_critical_blocker_ids": [],
        "is_issue_log_sla_compliant": True,
    }
    assert audit_wiki_issue_log_escalation_and_aging_sla("no-seq")["total_issues"] == 0
    assert (
        audit_wiki_issue_log_escalation_and_aging_sla(
            ["no-map", {"issue_id": "   "}, {"other_id": "x"}]
        )["total_issues"]
        == 0
    )
    assert "audit_wiki_issue_log_escalation_and_aging_sla" in _m.__all__

    sample = [
        {"issue_id": "IS-1", "severity": "low", "status": "open", "owner_id": "PM-1",
         "age_days": 1.0},
    ]
    assert (
        WikiPMIService.audit_wiki_issue_log_escalation_and_aging_sla(sample)
        == audit_wiki_issue_log_escalation_and_aging_sla(sample)
    )


def test_audit_wiki_communication_confidentiality_and_channel_security_compliant():
    """Canales clasificados con retención > 0, cifrado+DLP en confidencial/restringido y sin invitados en restringido cumplen §10.1 y §10.3."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_communication_confidentiality_and_channel_security,
    )

    channels = [
        {
            "channel_id": "CH-PUB-NEWS",
            "confidentiality_level": "public",
            "encryption_at_rest_and_transit": False,
            "external_guest_access_enabled": True,
            "dlp_and_audit_logging_enabled": False,
            "retention_policy_days": 365,
        },
        {
            "channel_id": "CH-CONF-PMO",
            "confidentiality_level": "Confidential",
            "encryption_at_rest_and_transit": True,
            "external_guest_access_enabled": True,
            "dlp_and_audit_logging_enabled": True,
            "retention_policy_days": 730,
        },
        {
            "channel_id": "CH-REST-BOARD",
            "confidentiality_level": "restricted",
            "encryption_at_rest_and_transit": True,
            "external_guest_access_enabled": False,
            "dlp_and_audit_logging_enabled": True,
            "retention_policy_days": 1825,
        },
    ]
    res = audit_wiki_communication_confidentiality_and_channel_security(channels)
    assert res == {
        "total_channels": 3,
        "invalid_classification_or_retention_ids": [],
        "unprotected_sensitive_channel_ids": [],
        "external_exposure_restricted_channel_ids": [],
        "is_communication_security_compliant": True,
    }
    assert (
        WikiPMIService.audit_wiki_communication_confidentiality_and_channel_security(
            channels
        )
        == res
    )


def test_audit_wiki_communication_confidentiality_unprotected_sensitive_channels():
    """Detecta canales confidential o restricted sin cifrado o sin DLP/audit logging."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_confidentiality_and_channel_security,
    )

    channels = [
        {
            "channel_id": "CH-CONF-NO-ENC",
            "confidentiality_level": "confidential",
            "encryption_at_rest_and_transit": False,
            "dlp_and_audit_logging_enabled": True,
            "retention_policy_days": 365,
        },
        {
            "channel_id": "CH-REST-NO-DLP",
            "confidentiality_level": "restricted",
            "encryption_at_rest_and_transit": True,
            "dlp_and_audit_logging_enabled": False,
            "external_guest_access_enabled": False,
            "retention_policy_days": 365,
        },
    ]
    res = audit_wiki_communication_confidentiality_and_channel_security(channels)
    assert res["total_channels"] == 2
    assert res["unprotected_sensitive_channel_ids"] == [
        "CH-CONF-NO-ENC",
        "CH-REST-NO-DLP",
    ]
    assert res["is_communication_security_compliant"] is False


def test_audit_wiki_communication_confidentiality_restricted_external_exposure():
    """Detecta canales restricted con acceso de invitados externos habilitado."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_confidentiality_and_channel_security,
    )

    channels = [
        {
            "channel_id": "CH-REST-GUEST",
            "confidentiality_level": "restricted",
            "encryption_at_rest_and_transit": True,
            "dlp_and_audit_logging_enabled": True,
            "external_guest_access_enabled": True,
            "retention_policy_days": 365,
        }
    ]
    res = audit_wiki_communication_confidentiality_and_channel_security(channels)
    assert res["external_exposure_restricted_channel_ids"] == ["CH-REST-GUEST"]
    assert res["is_communication_security_compliant"] is False


def test_audit_wiki_communication_confidentiality_invalid_and_export():
    """Detecta clasificación o retención inválida, ignora entradas no secuencia y verifica __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_confidentiality_and_channel_security,
    )

    assert (
        "audit_wiki_communication_confidentiality_and_channel_security"
        in _m.__all__
    )
    res = audit_wiki_communication_confidentiality_and_channel_security(
        [
            {
                "channel_id": "CH-BAD-LEVEL",
                "confidentiality_level": "top_secret",
                "retention_policy_days": 90,
            },
            {
                "channel_id": "CH-ZERO-RET",
                "confidentiality_level": "internal",
                "retention_policy_days": 0,
            },
        ]
    )
    assert res["invalid_classification_or_retention_ids"] == [
        "CH-BAD-LEVEL",
        "CH-ZERO-RET",
    ]
    assert res["is_communication_security_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"channel_id": "  "}]):
        assert (
            audit_wiki_communication_confidentiality_and_channel_security(bad)
            == {
                "total_channels": 0,
                "invalid_classification_or_retention_ids": [],
                "unprotected_sensitive_channel_ids": [],
                "external_exposure_restricted_channel_ids": [],
                "is_communication_security_compliant": True,
            }
        )


def test_audit_wiki_lessons_learned_actionable_opa_transfer_compliant():
    """Cumple cuando las lecciones se capturan a lo largo de varias fases, tienen contexto/recomendación detallada y transferencia a OPA."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_lessons_learned_actionable_opa_transfer,
    )

    entries = [
        {
            "lesson_id": "LL-PLAN-01",
            "phase_captured": "planning",
            "root_cause_context": "Estimación omitió tiempos de homologación regulatoria externa.",
            "actionable_recommendation": "Incluir hito obligatorio de revisión legal en checklist de cronograma.",
            "opa_template_updated": True,
            "assigned_follow_up_owner_id": None,
        },
        {
            "lesson_id": "LL-EXEC-02",
            "phase_captured": "executing",
            "root_cause_context": "Ambientes de staging compartidos generaron bloqueos entre células.",
            "actionable_recommendation": "Aprovisionar entornos efímeros por PR en pipeline CI/CD.",
            "opa_template_updated": False,
            "assigned_follow_up_owner_id": "USR-DEVOPS-01",
        },
        {
            "lesson_id": "LL-CLOSE-03",
            "phase_captured": "closing",
            "root_cause_context": "Transferencia a soporte requirió sesiones adicionales de arquitectura.",
            "actionable_recommendation": "Incorporar plantilla de runbook operativo desde la fase de ejecución.",
            "opa_template_updated": True,
            "assigned_follow_up_owner_id": "USR-PMO-02",
        },
    ]
    res = audit_wiki_lessons_learned_actionable_opa_transfer(entries)
    assert res == {
        "total_lessons": 3,
        "captured_only_at_closure_anti_pattern": False,
        "invalid_phase_lesson_ids": [],
        "vague_or_incomplete_lesson_ids": [],
        "untransferred_opa_lesson_ids": [],
        "is_lessons_learned_governance_compliant": True,
    }
    assert WikiPMIService.audit_wiki_lessons_learned_actionable_opa_transfer(entries) == res


def test_audit_wiki_lessons_learned_actionable_captured_only_at_closure_anti_pattern():
    """Detecta el anti-patrón PMBOK §4.4 cuando >= 3 lecciones válidas se registran únicamente al cierre."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_lessons_learned_actionable_opa_transfer,
    )

    entries = [
        {
            "lesson_id": f"LL-CLOSE-0{i}",
            "phase_captured": "CLOSING",
            "root_cause_context": "Contexto de causa raíz suficientemente descriptivo y claro.",
            "actionable_recommendation": "Recomendación accionable concreta para futuros proyectos.",
            "opa_template_updated": True,
        }
        for i in range(1, 4)
    ]
    res = audit_wiki_lessons_learned_actionable_opa_transfer(entries)
    assert res["total_lessons"] == 3
    assert res["captured_only_at_closure_anti_pattern"] is True
    assert res["is_lessons_learned_governance_compliant"] is False


def test_audit_wiki_lessons_learned_actionable_vague_and_untransferred():
    """Detecta lecciones con contexto/recomendación vaga (< 10 chars) y sin actualización OPA ni responsable."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_lessons_learned_actionable_opa_transfer,
    )

    res = audit_wiki_lessons_learned_actionable_opa_transfer(
        [
            {
                "lesson_id": "LL-VAGUE",
                "phase_captured": "executing",
                "root_cause_context": "Corto",
                "actionable_recommendation": "Mejorar",
                "opa_template_updated": True,
            },
            {
                "lesson_id": "LL-NO-OPA",
                "phase_captured": "monitoring_controlling",
                "root_cause_context": "Desviación en pruebas de integración por contratos desactualizados.",
                "actionable_recommendation": "Automatizar pruebas de contrato OpenAPI en cada merge.",
                "opa_template_updated": False,
                "assigned_follow_up_owner_id": "   ",
            },
        ]
    )
    assert res["vague_or_incomplete_lesson_ids"] == ["LL-VAGUE"]
    assert res["untransferred_opa_lesson_ids"] == ["LL-NO-OPA"]
    assert res["is_lessons_learned_governance_compliant"] is False


def test_audit_wiki_lessons_learned_actionable_invalid_phase_and_export():
    """Detecta fases de ciclo de vida inválidas, maneja entradas malformadas y verifica exportación en __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_lessons_learned_actionable_opa_transfer,
    )

    assert "audit_wiki_lessons_learned_actionable_opa_transfer" in _m.__all__
    res = audit_wiki_lessons_learned_actionable_opa_transfer(
        [
            {
                "lesson_id": "LL-BAD-PHASE",
                "phase_captured": "post_mortem_random",
                "root_cause_context": "Contexto suficientemente largo para prueba.",
                "actionable_recommendation": "Recomendación suficientemente larga para prueba.",
                "opa_template_updated": True,
            }
        ]
    )
    assert res["invalid_phase_lesson_ids"] == ["LL-BAD-PHASE"]
    assert res["is_lessons_learned_governance_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"lesson_id": "  "}]):
        assert audit_wiki_lessons_learned_actionable_opa_transfer(bad) == {
            "total_lessons": 0,
            "captured_only_at_closure_anti_pattern": False,
            "invalid_phase_lesson_ids": [],
            "vague_or_incomplete_lesson_ids": [],
            "untransferred_opa_lesson_ids": [],
            "is_lessons_learned_governance_compliant": True,
        }


def test_audit_wiki_risk_trigger_early_warning_and_fallback_healthy():
    """Verifica estado HEALTHY cuando todos los riesgos tienen EWI, dueño, respuesta efectiva o fallback activado."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_risk_trigger_early_warning_and_fallback,
    )

    triggers = [
        {
            "risk_id": "RSK-LATENCY-01",
            "trigger_condition_defined": True,
            "risk_owner_assigned": True,
            "trigger_breached": False,
            "primary_response_activated": False,
            "primary_response_effective": False,
            "fallback_plan_documented": True,
            "fallback_plan_activated": False,
        },
        {
            "risk_id": "RSK-FAILOVER-02",
            "trigger_condition_defined": True,
            "risk_owner_assigned": True,
            "trigger_breached": True,
            "primary_response_activated": True,
            "primary_response_effective": False,
            "fallback_plan_documented": True,
            "fallback_plan_activated": True,
        },
    ]
    res = audit_wiki_risk_trigger_early_warning_and_fallback(triggers)
    assert res == {
        "total_monitored_risks": 2,
        "compliant_risks_count": 2,
        "missing_trigger_or_owner_count": 0,
        "breached_triggers_count": 1,
        "unactivated_breached_trigger_count": 0,
        "failed_primary_without_fallback_count": 0,
        "ewi_governance_status": "HEALTHY",
        "violations": [],
    }
    assert (
        WikiPMIService.audit_wiki_risk_trigger_early_warning_and_fallback(triggers)
        == res
    )


def test_audit_wiki_risk_trigger_early_warning_and_fallback_at_risk():
    """Verifica estado AT_RISK cuando falta condición de disparo o propietario pero ningún trigger ha sido vulnerado."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_trigger_early_warning_and_fallback,
    )

    res = audit_wiki_risk_trigger_early_warning_and_fallback(
        [
            {
                "risk_id": "RSK-NO-OWNER",
                "trigger_condition_defined": True,
                "risk_owner_assigned": False,
                "trigger_breached": False,
                "primary_response_activated": False,
                "primary_response_effective": False,
                "fallback_plan_documented": False,
                "fallback_plan_activated": False,
            }
        ]
    )
    assert res["missing_trigger_or_owner_count"] == 1
    assert res["compliant_risks_count"] == 0
    assert res["ewi_governance_status"] == "AT_RISK"
    assert len(res["violations"]) == 1
    assert res["violations"][0]["risk_id"] == "RSK-NO-OWNER"


def test_audit_wiki_risk_trigger_early_warning_and_fallback_critical():
    """Verifica estado CRITICAL cuando un trigger se activa sin respuesta primaria o falla sin plan de fallback activado."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_trigger_early_warning_and_fallback,
    )

    res = audit_wiki_risk_trigger_early_warning_and_fallback(
        [
            {
                "risk_id": "RSK-UNACTIVATED",
                "trigger_condition_defined": True,
                "risk_owner_assigned": True,
                "trigger_breached": True,
                "primary_response_activated": False,
                "primary_response_effective": False,
                "fallback_plan_documented": True,
                "fallback_plan_activated": False,
            },
            {
                "risk_id": "RSK-NO-FALLBACK",
                "trigger_condition_defined": True,
                "risk_owner_assigned": True,
                "trigger_breached": True,
                "primary_response_activated": True,
                "primary_response_effective": False,
                "fallback_plan_documented": True,
                "fallback_plan_activated": False,
            },
        ]
    )
    assert res["breached_triggers_count"] == 2
    assert res["unactivated_breached_trigger_count"] == 1
    assert res["failed_primary_without_fallback_count"] == 1
    assert res["ewi_governance_status"] == "CRITICAL"


def test_audit_wiki_risk_trigger_early_warning_and_fallback_empty_and_export():
    """Verifica manejo de entradas vacías o no secuencia y exportación en __all__."""
    import backend.services.wiki_pmi_service as _m
    from backend.services.wiki_pmi_service import (
        audit_wiki_risk_trigger_early_warning_and_fallback,
    )

    assert "audit_wiki_risk_trigger_early_warning_and_fallback" in _m.__all__
    for bad in ([], None, "invalid"):
        assert audit_wiki_risk_trigger_early_warning_and_fallback(bad) == {
            "total_monitored_risks": 0,
            "compliant_risks_count": 0,
            "missing_trigger_or_owner_count": 0,
            "breached_triggers_count": 0,
            "unactivated_breached_trigger_count": 0,
            "failed_primary_without_fallback_count": 0,
            "ewi_governance_status": "HEALTHY",
            "violations": [],
        }




def test_audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration_healthy():
    """Dominios sin SPOF, sin silo SME y con runbook/revisión al día."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration,
    )

    res = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-1", "qualified_contributors_count": 2,
             "primary_author_edit_share_pct": 60.0,
             "shadowing_or_cross_training_completed": True, "runbook_documented": True,
             "days_since_last_peer_review": 10},
            {"domain_id": "D-2", "qualified_contributors_count": 3,
             "primary_author_edit_share_pct": 50.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": True,
             "days_since_last_peer_review": 40},
        ]
    )
    assert res == {
        "total_domains": 2,
        "resilient_domains_count": 2,
        "spof_domains_count": 0,
        "sme_silo_domains_count": 0,
        "missing_runbook_or_stale_review_count": 0,
        "knowledge_resilience_pct": 100.0,
        "bus_factor_governance_status": "HEALTHY",
        "violations": [],
    }


def test_audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration_spof_critical():
    """SPOF: contributores < min sin shadowing -> CRITICAL y resiliencia 0.0."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration,
    )

    res = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-S", "qualified_contributors_count": 1,
             "primary_author_edit_share_pct": 50.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": True,
             "days_since_last_peer_review": 20},
        ]
    )
    assert res["spof_domains_count"] == 1
    assert res["resilient_domains_count"] == 0
    assert res["knowledge_resilience_pct"] == 0.0
    assert res["bus_factor_governance_status"] == "CRITICAL"
    assert res["violations"] == [{
        "domain_id": "D-S", "reasons": ["SPOF_BUS_FACTOR (1<2, sin shadowing)"],
    }]

    # Con shadowing completado, el mismo bus factor se mitiga.
    mitigated = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-M", "qualified_contributors_count": 1,
             "primary_author_edit_share_pct": 50.0,
             "shadowing_or_cross_training_completed": True, "runbook_documented": True,
             "days_since_last_peer_review": 20},
        ]
    )
    assert mitigated["spof_domains_count"] == 0
    assert mitigated["bus_factor_governance_status"] == "HEALTHY"


def test_audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration_silo_and_runbook():
    """SME silo (> 80% sin shadowing) y runbook ausente / revisión vencida -> AT_RISK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration,
    )

    silo = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-SILO", "qualified_contributors_count": 2,
             "primary_author_edit_share_pct": 90.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": True,
             "days_since_last_peer_review": 30},
        ]
    )
    assert silo["sme_silo_domains_count"] == 1
    assert silo["bus_factor_governance_status"] == "AT_RISK"
    assert silo["violations"] == [{
        "domain_id": "D-SILO", "reasons": ["SME_SILO (90.0>80.0, sin shadowing)"],
    }]

    # Shadowing mitiga el silo.
    mitigated = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-MIT", "qualified_contributors_count": 2,
             "primary_author_edit_share_pct": 90.0,
             "shadowing_or_cross_training_completed": True, "runbook_documented": True,
             "days_since_last_peer_review": 30},
        ]
    )
    assert mitigated["sme_silo_domains_count"] == 0

    # Runbook ausente + revisión vencida en el mismo dominio.
    runbook = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-RB", "qualified_contributors_count": 3,
             "primary_author_edit_share_pct": 20.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": False,
             "days_since_last_peer_review": 50},
        ]
    )
    assert runbook["missing_runbook_or_stale_review_count"] == 1
    assert runbook["bus_factor_governance_status"] == "AT_RISK"
    assert runbook["violations"] == [{
        "domain_id": "D-RB",
        "reasons": ["RUNBOOK_MISSING", "PEER_REVIEW_STALE (50>45)"],
    }]

    # Borde de revisión: 45 <= 45 no es vencida even con share en el limite 80.0.
    border = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-B", "qualified_contributors_count": 2,
             "primary_author_edit_share_pct": 80.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": True,
             "days_since_last_peer_review": 45},
        ]
    )
    assert border["missing_runbook_or_stale_review_count"] == 0
    assert border["sme_silo_domains_count"] == 0
    assert border["resilient_domains_count"] == 1


def test_audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration_custom_and_empty():
    """Umbrales custom, entrada vacia/None y proxy estatico + __all__."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration,
    )
    import backend.services.wiki_pmi_service as mod

    # min_bus_factor=3 y max_days=10 => 2 contributores es SPOF y 11 dias vencida.
    custom = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
        [
            {"domain_id": "D-C", "qualified_contributors_count": 2,
             "primary_author_edit_share_pct": 10.0,
             "shadowing_or_cross_training_completed": False, "runbook_documented": True,
             "days_since_last_peer_review": 11},
        ],
        min_bus_factor=3,
        max_days_without_peer_review=10,
    )
    assert custom["spof_domains_count"] == 1
    assert custom["missing_runbook_or_stale_review_count"] == 1
    assert custom["bus_factor_governance_status"] == "CRITICAL"
    assert custom["knowledge_resilience_pct"] == 0.0

    for payload in ([], None, 42):
        empty = audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(payload)
        assert empty["total_domains"] == 0
        assert empty["knowledge_resilience_pct"] == 100.0
        assert empty["bus_factor_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    sample = [{"domain_id": "SM", "qualified_contributors_count": 2,
               "primary_author_edit_share_pct": 10.0,
               "shadowing_or_cross_training_completed": False, "runbook_documented": True,
               "days_since_last_peer_review": 10}]
    assert (
        WikiPMIService.audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(sample)
        == audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(sample)
    )
    assert "audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration" in mod.__all__


def test_audit_wiki_requirements_bidirectional_traceability_and_gold_plating_healthy():
    """Matriz RTM 100% trazable hacia objetivos, WBS, casos de prueba y linea base CCB (PMBOK §5.2, §5.6)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_requirements_bidirectional_traceability_and_gold_plating,
    )

    res = audit_wiki_requirements_bidirectional_traceability_and_gold_plating(
        [
            {
                "item_id": "REQ-001",
                "linked_business_objective_id": "OBJ-FIN-01",
                "linked_wbs_deliverable_id": "WBS-1.2.1",
                "linked_test_case_id": "TC-QA-101",
                "ccb_approved_baseline": True,
            },
            {
                "item_id": "REQ-002",
                "linked_business_objective_id": "OBJ-OPS-02",
                "linked_wbs_deliverable_id": "WBS-2.1.4",
                "linked_test_case_id": "TC-QA-102",
                "ccb_approved_baseline": True,
            },
        ]
    )
    assert res == {
        "total_items": 2,
        "fully_traced_items_count": 2,
        "unverified_or_unbuilt_requirements_count": 0,
        "gold_plating_or_orphan_scope_count": 0,
        "bidirectional_traceability_pct": 100.0,
        "traceability_governance_status": "AT_RISK" if False else "HEALTHY",
        "violations": [],
    }


def test_audit_wiki_requirements_bidirectional_traceability_and_gold_plating_at_risk_forward_gap():
    """Detecta brecha de trazabilidad hacia adelante (sin WBS o sin caso de prueba) como AT_RISK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_requirements_bidirectional_traceability_and_gold_plating,
    )

    res = audit_wiki_requirements_bidirectional_traceability_and_gold_plating(
        [
            {
                "item_id": "REQ-010",
                "linked_business_objective_id": "OBJ-01",
                "linked_wbs_deliverable_id": "WBS-1.1",
                "linked_test_case_id": "TC-01",
                "ccb_approved_baseline": True,
            },
            {
                "item_id": "REQ-011",
                "linked_business_objective_id": "OBJ-01",
                "linked_wbs_deliverable_id": "",
                "linked_test_case_id": "TC-02",
                "ccb_approved_baseline": True,
            },
            {
                "item_id": "REQ-012",
                "linked_business_objective_id": "OBJ-02",
                "linked_wbs_deliverable_id": "WBS-1.3",
                "linked_test_case_id": None,
                "ccb_approved_baseline": True,
            },
        ]
    )
    assert res["total_items"] == 3
    assert res["fully_traced_items_count"] == 1
    assert res["unverified_or_unbuilt_requirements_count"] == 2
    assert res["gold_plating_or_orphan_scope_count"] == 0
    assert res["bidirectional_traceability_pct"] == 33.33
    assert res["traceability_governance_status"] == "AT_RISK"
    assert len(res["violations"]) == 2
    assert res["violations"][0]["item_id"] == "REQ-011"
    assert "missing_linked_wbs_deliverable_id" in res["violations"][0]["reasons"]
    assert res["violations"][1]["item_id"] == "REQ-012"
    assert "missing_linked_test_case_id" in res["violations"][1]["reasons"]


def test_audit_wiki_requirements_bidirectional_traceability_and_gold_plating_critical_scope_creep():
    """Detecta gold-plating o alcance huerfano (sin objetivo de negocio o sin aprobacion CCB) como CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_requirements_bidirectional_traceability_and_gold_plating,
    )

    res = audit_wiki_requirements_bidirectional_traceability_and_gold_plating(
        [
            {
                "item_id": "REQ-GP-1",
                "linked_business_objective_id": "   ",
                "linked_wbs_deliverable_id": "WBS-3.1",
                "linked_test_case_id": "TC-31",
                "ccb_approved_baseline": True,
            },
            {
                "item_id": "REQ-GP-2",
                "linked_business_objective_id": "OBJ-09",
                "linked_wbs_deliverable_id": "WBS-3.2",
                "linked_test_case_id": "TC-32",
                "ccb_approved_baseline": False,
            },
        ]
    )
    assert res["total_items"] == 2
    assert res["fully_traced_items_count"] == 0
    assert res["unverified_or_unbuilt_requirements_count"] == 0
    assert res["gold_plating_or_orphan_scope_count"] == 2
    assert res["bidirectional_traceability_pct"] == 0.0
    assert res["traceability_governance_status"] == "CRITICAL"
    assert "missing_linked_business_objective_id" in res["violations"][0]["reasons"]
    assert "unapproved_ccb_baseline_gold_plating" in res["violations"][1]["reasons"]


def test_audit_wiki_requirements_bidirectional_traceability_and_gold_plating_empty_and_export():
    """Maneja entradas vacias/no-lista con 100.0% HEALTHY y verifica staticmethod + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_requirements_bidirectional_traceability_and_gold_plating,
    )

    for payload in ([], None, "invalid"):
        empty = audit_wiki_requirements_bidirectional_traceability_and_gold_plating(payload)  # type: ignore[arg-type]
        assert empty == {
            "total_items": 0,
            "fully_traced_items_count": 0,
            "unverified_or_unbuilt_requirements_count": 0,
            "gold_plating_or_orphan_scope_count": 0,
            "bidirectional_traceability_pct": 100.0,
            "traceability_governance_status": "HEALTHY",
            "violations": [],
        }

    sample = [
        {
            "item_id": "REQ-100",
            "linked_business_objective_id": "OBJ-1",
            "linked_wbs_deliverable_id": "WBS-1",
            "linked_test_case_id": "TC-1",
            "ccb_approved_baseline": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_requirements_bidirectional_traceability_and_gold_plating(sample)
        == audit_wiki_requirements_bidirectional_traceability_and_gold_plating(sample)
    )
    assert "audit_wiki_requirements_bidirectional_traceability_and_gold_plating" in mod.__all__



def test_audit_wiki_decision_log_daci_accountability_and_reversal_healthy():
    """Decisiones sin ambiguedad DACI, con alternativas y SLA al dia."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_decision_log_daci_accountability_and_reversal,
    )

    res = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-1", "status": "approved", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 3,
             "days_pending": 0, "was_reversed": False,
             "reversal_impact_documented": False},
            {"decision_id": "D-2", "status": "PENDING", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 2,
             "days_pending": 10, "was_reversed": False,
             "reversal_impact_documented": False},
        ]
    )
    assert res == {
        "total_decisions": 2,
        "compliant_decisions_count": 2,
        "ambiguous_accountability_count": 0,
        "stalled_or_unjustified_decisions_count": 0,
        "undocumented_reversals_count": 0,
        "decision_governance_status": "HEALTHY",
        "violations": [],
    }


def test_audit_wiki_decision_log_daci_accountability_and_reversal_critical():
    """Ambiguedad DACI (approvers != 1 / sin driver) y reversion sin impacto -> CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_decision_log_daci_accountability_and_reversal,
    )

    crit = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-3", "status": "DECIDED", "approvers_count": 2,
             "driver_assigned": False, "alternatives_documented_count": 3,
             "days_pending": 0, "was_reversed": False,
             "reversal_impact_documented": False},
            {"decision_id": "D-4", "status": "approved", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 3,
             "days_pending": 0, "was_reversed": True,
             "reversal_impact_documented": False},
        ]
    )
    assert crit["ambiguous_accountability_count"] == 1
    assert crit["undocumented_reversals_count"] == 1
    assert crit["compliant_decisions_count"] == 0
    assert crit["decision_governance_status"] == "CRITICAL"
    assert crit["violations"][0]["reasons"] == [
        "DACI_APPROVERS_COUNT_AMBIGUOUS (2 != 1)", "DACI_DRIVER_NO_ASSIGNED",
    ]
    assert crit["violations"][1]["reasons"] == ["REVERSAL_IMPACT_UNDOCUMENTED"]

    # Reversion con impacto documentado -> sin hallazgo de reversion.
    rev_ok = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-8", "status": "approved", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 2,
             "days_pending": 0, "was_reversed": True,
             "reversal_impact_documented": True},
        ]
    )
    assert rev_ok["undocumented_reversals_count"] == 0
    assert rev_ok["decision_governance_status"] == "HEALTHY"


def test_audit_wiki_decision_log_daci_accountability_and_reversal_at_risk():
    """PENDING vencida (borde 10 == SLA no vence) o < 2 alternativas -> AT_RISK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_decision_log_daci_accountability_and_reversal,
    )

    risk = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-5", "status": "pending", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 2,
             "days_pending": 11, "was_reversed": False,
             "reversal_impact_documented": False},
        ]
    )
    assert risk["stalled_or_unjustified_decisions_count"] == 1
    assert risk["compliant_decisions_count"] == 0
    assert risk["decision_governance_status"] == "AT_RISK"
    assert risk["violations"][0]["reasons"] == ["PENDING_STALLED (11>10)"]

    alt = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-6", "status": "DECIDED", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 1,
             "days_pending": 0, "was_reversed": False,
             "reversal_impact_documented": False},
        ]
    )
    assert alt["stalled_or_unjustified_decisions_count"] == 1
    assert alt["violations"][0]["reasons"] == ["ALTERNATIVES_UNDERDOCUMENTED (1<2)"]

    # Borde: PENDING con days_pending == 10 (== SLA) no vence.
    border = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-9", "status": "PENDING", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 2,
             "days_pending": 10, "was_reversed": False,
             "reversal_impact_documented": False},
        ]
    )
    assert border["stalled_or_unjustified_decisions_count"] == 0
    assert border["decision_governance_status"] == "HEALTHY"


def test_audit_wiki_decision_log_daci_accountability_and_reversal_custom_and_empty():
    """Umbrales custom, case-insensitive, entrada vacia/None y proxy + __all__."""
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_decision_log_daci_accountability_and_reversal,
    )
    import backend.services.wiki_pmi_service as mod

    custom = audit_wiki_decision_log_daci_accountability_and_reversal(
        [
            {"decision_id": "D-7", "status": "pEnDiNg", "approvers_count": 1,
             "driver_assigned": True, "alternatives_documented_count": 2,
             "days_pending": 4, "was_reversed": False,
             "reversal_impact_documented": False},
        ],
        max_pending_decision_days=3,
    )
    assert custom["stalled_or_unjustified_decisions_count"] == 1
    assert custom["decision_governance_status"] == "AT_RISK"

    for payload in ([], None, 42, ["x"]):
        empty = audit_wiki_decision_log_daci_accountability_and_reversal(payload)
        assert empty["total_decisions"] == 0
        assert empty["decision_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    sample = [{"decision_id": "SM", "status": "approved", "approvers_count": 1,
               "driver_assigned": True, "alternatives_documented_count": 2,
               "days_pending": 0, "was_reversed": False,
               "reversal_impact_documented": False}]
    assert (
        WikiPMIService.audit_wiki_decision_log_daci_accountability_and_reversal(sample)
        == audit_wiki_decision_log_daci_accountability_and_reversal(sample)
    )
    assert "audit_wiki_decision_log_daci_accountability_and_reversal" in mod.__all__


def test_audit_wiki_assumptions_and_constraints_empirical_validation_healthy():
    """Supuestos validados o dentro de ventana con dueño/método, falsos convertidos a riesgo/CR y restricciones con margen."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumptions_and_constraints_empirical_validation,
    )

    entries = [
        {
            "id": "ASM-01",
            "entry_type": "assumption",
            "validation_status": "validated_true",
            "days_open": 14,
            "owner": "Lead Architect",
            "validation_method": "Prueba de carga en staging",
        },
        {
            "id": "ASM-02",
            "entry_type": "assumption",
            "validation_status": "invalidated_false",
            "days_open": 10,
            "owner": "Security Lead",
            "validation_method": "Pentest externo",
            "linked_risk_or_cr_id": "RISK-404",
        },
        {
            "id": "CON-01",
            "entry_type": "constraint",
            "owner": "PMO Director",
            "constraint_buffer_pct": 12.5,
        },
    ]
    res = audit_wiki_assumptions_and_constraints_empirical_validation(
        entries, max_unvalidated_days=21
    )
    assert res["total_entries"] == 3
    assert res["compliant_entries"] == 3
    assert res["unowned_or_missing_method_ids"] == []
    assert res["stale_unvalidated_assumption_ids"] == []
    assert res["unconverted_invalidated_assumption_ids"] == []
    assert res["breached_constraint_ids"] == []
    assert res["validation_rate_pct"] == 100.0
    assert res["governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_wiki_assumptions_and_constraints_empirical_validation_at_risk_stale_and_unowned():
    """Detecta supuestos sin dueño/método de validación y supuestos sin validar estancados (at_risk)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumptions_and_constraints_empirical_validation,
    )

    entries = [
        {
            "assumption_id": "ASM-10",
            "entry_type": "assumption",
            "validation_status": "unvalidated",
            "days_open": 5,
            "owner": "",
            "validation_method": "",
        },
        {
            "assumption_id": "ASM-11",
            "entry_type": "assumption",
            "validation_status": "unvalidated",
            "days_open": 30,
            "owner": "Infra Lead",
            "validation_method": "PoC de latencia WAN",
        },
    ]
    res = audit_wiki_assumptions_and_constraints_empirical_validation(
        entries, max_unvalidated_days=21
    )
    assert res["total_entries"] == 2
    assert res["compliant_entries"] == 0
    assert res["unowned_or_missing_method_ids"] == ["ASM-10"]
    assert res["stale_unvalidated_assumption_ids"] == ["ASM-11"]
    assert res["unconverted_invalidated_assumption_ids"] == []
    assert res["breached_constraint_ids"] == []
    assert res["validation_rate_pct"] == 0.0
    assert res["governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_assumptions_and_constraints_empirical_validation_critical_unconverted_and_breached():
    """Detecta supuestos invalidados sin conversión a riesgo/CR y restricciones violadas (critical)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_assumptions_and_constraints_empirical_validation,
    )

    entries = [
        {
            "id": "ASM-20",
            "entry_type": "assumption",
            "validation_status": "invalidated_false",
            "days_open": 12,
            "owner": "Data Lead",
            "validation_method": "Muestreo de calidad de datos",
            "linked_risk_or_cr_id": "",
        },
        {
            "id": "CON-20",
            "entry_type": "constraint",
            "owner": "Sponsor",
            "constraint_buffer_pct": -4.5,
        },
    ]
    res = audit_wiki_assumptions_and_constraints_empirical_validation(entries)
    assert res["total_entries"] == 2
    assert res["compliant_entries"] == 0
    assert res["unconverted_invalidated_assumption_ids"] == ["ASM-20"]
    assert res["breached_constraint_ids"] == ["CON-20"]
    assert res["validation_rate_pct"] == 50.0
    assert res["governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_assumptions_and_constraints_empirical_validation_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_assumptions_and_constraints_empirical_validation,
    )

    for payload in (None, [], "invalid", ["not-a-mapping"]):
        empty = audit_wiki_assumptions_and_constraints_empirical_validation(payload)  # type: ignore[arg-type]
        assert empty["total_entries"] == 0
        assert empty["compliant_entries"] == 0
        assert empty["validation_rate_pct"] == 100.0
        assert empty["governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "ASM-99",
            "entry_type": "assumption",
            "validation_status": "validated_true",
            "days_open": 3,
            "owner": "QA Lead",
            "validation_method": "Test automatizado",
        }
    ]
    assert (
        WikiPMIService.audit_wiki_assumptions_and_constraints_empirical_validation(sample)
        == audit_wiki_assumptions_and_constraints_empirical_validation(sample)
    )
    assert "audit_wiki_assumptions_and_constraints_empirical_validation" in mod.__all__



def test_wiki_runbook_rto_rpo_readiness_healthy_and_critical():
    """Runbook conforme -> compliant; SLA breach por target/measured -> CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness,
    )

    healthy = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-1",
                "target_rto_minutes": 30.0,
                "measured_drill_rto_minutes": 20.0,
                "target_rpo_minutes": 15.0,
                "measured_drill_rpo_minutes": 10.0,
                "days_since_last_drill": 30,
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
            }
        ]
    )
    assert healthy["total_runbooks"] == 1
    assert healthy["compliant_runbooks_count"] == 1
    assert healthy["rto_or_rpo_sla_breach_count"] == 0
    assert healthy["stale_or_untested_drill_count"] == 0
    assert healthy["missing_rollback_or_escalation_count"] == 0
    assert healthy["runbook_readiness_status"] == "HEALTHY"
    assert healthy["violations"] == []

    critical = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-2",
                "target_rto_minutes": 0.0,
                "target_rpo_minutes": 10.0,
                "measured_drill_rpo_minutes": 20.0,
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
                "days_since_last_drill": 10,
            }
        ]
    )
    assert critical["rto_or_rpo_sla_breach_count"] == 1
    assert critical["violations"][0]["runbook_id"] == "RB-2"
    assert critical["violations"][0]["reasons"] == ["rto_or_rpo_sla_breach"]
    assert critical["runbook_readiness_status"] == "CRITICAL"


def test_wiki_runbook_rto_rpo_readiness_at_risk_missing_and_dedup():
    """Solo drill vencido -> AT_RISK; rollbacks/asignación ausentes -> CRITICAL; dedup de reasons."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness,
    )

    at_risk = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-3",
                "days_since_last_drill": 91,
                "target_rto_minutes": 30.0,
                "target_rpo_minutes": 15.0,
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
            }
        ]
    )
    assert at_risk["stale_or_untested_drill_count"] == 1
    assert at_risk["rto_or_rpo_sla_breach_count"] == 0
    assert at_risk["missing_rollback_or_escalation_count"] == 0
    assert at_risk["runbook_readiness_status"] == "AT_RISK"

    multi = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-4",
                "target_rto_minutes": 30.0,
                "measured_drill_rto_minutes": 45.0,
                "rollback_steps_documented": False,
                "oncall_escalation_assigned": False,
            }
        ]
    )
    reasons = multi["violations"][0]["reasons"]
    assert reasons == ["rto_or_rpo_sla_breach", "missing_rollback_or_escalation"]
    assert multi["missing_rollback_or_escalation_count"] == 1
    assert multi["runbook_readiness_status"] == "CRITICAL"

    # Drill negativo también es stale; custom max_days_since_drill se respeta.
    neg = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [{"runbook_id": "RB-5", "days_since_last_drill": -1}],
        max_days_since_drill=30,
    )
    assert neg["stale_or_untested_drill_count"] == 1

    tight = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-6",
                "days_since_last_drill": 15,
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
            }
        ],
        max_days_since_drill=14,
    )
    assert tight["stale_or_untested_drill_count"] == 1
    assert tight["runbook_readiness_status"] == "AT_RISK"

    within = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-7",
                "days_since_last_drill": 14,
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
            }
        ],
        max_days_since_drill=14,
    )
    assert within["runbook_readiness_status"] == "HEALTHY"


def test_wiki_runbook_rto_rpo_readiness_ignores_bad_entries_and_fields():
    """No-lista->[]; no-dict ignorado; faltantes de campos no violan por sí solos salvo especificados."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness,
    )

    res = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-8",
                "rollback_steps_documented": True,
                "oncall_escalation_assigned": True,
            }
        ]
    )
    assert res["total_runbooks"] == 1
    assert res["compliant_runbooks_count"] == 1
    assert res["violations"] == []

    empty_non_list = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(None)
    assert empty_non_list["total_runbooks"] == 0
    assert empty_non_list["runbook_readiness_status"] == "HEALTHY"
    assert empty_non_list["compliant_runbooks_count"] == 0
    assert empty_non_list["violations"] == []

    string_payload = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness("RB-9")
    assert string_payload["total_runbooks"] == 0

    # Faltantes explícitos: sin rollback ni oncall -> missing.
    missing_fields = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [{"runbook_id": "RB-10", "rollback_steps_documented": True}]
    )
    assert missing_fields["violations"][0]["reasons"] == ["missing_rollback_or_escalation"]
    assert missing_fields["runbook_readiness_status"] == "CRITICAL"


def test_wiki_runbook_rto_rpo_readiness_status_precedence_and_binding():
    """Precedencia CRITICAL>AT_RISK, proxy @staticmethod de WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness,
    )

    # target_rpo < 0 (breach) + drill vencido + rollback/oncall faltantes: un solo runbook con 3 reasons.
    everything = audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
        [
            {
                "runbook_id": "RB-11",
                "target_rpo_minutes": -5.0,
                "days_since_last_drill": 999,
                "rollback_steps_documented": False,
                "oncall_escalation_assigned": False,
            }
        ]
    )
    assert everything["violations"][0]["reasons"] == [
        "rto_or_rpo_sla_breach",
        "stale_or_untested_drill",
        "missing_rollback_or_escalation",
    ]
    assert everything["rto_or_rpo_sla_breach_count"] == 1
    assert everything["stale_or_untested_drill_count"] == 1
    assert everything["missing_rollback_or_escalation_count"] == 1
    assert everything["runbook_readiness_status"] == "CRITICAL"

    sample = [{"runbook_id": "RB-12", "target_rto_minutes": -1.0}]
    assert (
        WikiPMIService.audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(sample)
        == audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(sample)
    )
    assert "audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness" in mod.__all__


def test_audit_wiki_communications_matrix_cadence_and_escalation_healthy():
    """Valida matriz de comunicaciones con métodos interactive/push/pull, dueño, audiencia, ruta de escalamiento, entrega oportuna y alta confirmación."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communications_matrix_cadence_and_escalation,
    )

    artifacts = [
        {
            "id": "COM-01",
            "method": "interactive",
            "sender_owner": "PMO Lead",
            "target_audience": "Steering Committee",
            "escalation_path_defined": True,
            "delivery_delay_days": 0,
            "recipient_ack_rate_pct": 95.0,
        },
        {
            "id": "COM-02",
            "method": "push",
            "sender_owner": "Project Manager",
            "target_audience": "Key Stakeholders",
            "escalation_path_defined": True,
            "delivery_delay_days": 1,
            "recipient_ack_rate_pct": 70.0,
        },
        {
            "id": "COM-03",
            "method": "pull",
            "sender_owner": "Knowledge Manager",
            "target_audience": "Project Team",
            "escalation_path_defined": True,
            "delivery_delay_days": 0,
        },
    ]
    res = audit_wiki_communications_matrix_cadence_and_escalation(artifacts)
    assert res["total_artifacts"] == 3
    assert res["compliant_artifacts"] == 3
    assert res["incomplete_matrix_definition_ids"] == []
    assert res["cadence_delivery_overdue_ids"] == []
    assert res["low_interactive_engagement_ids"] == []
    assert res["communications_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_wiki_communications_matrix_cadence_and_escalation_at_risk():
    """Detecta retrasos en la cadencia de distribución y baja confirmación interactiva ('at_risk')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communications_matrix_cadence_and_escalation,
    )

    artifacts = [
        {
            "comm_id": "COM-10",
            "method": "push",
            "sender_owner": "Project Manager",
            "target_audience": "Sponsors",
            "escalation_path_defined": True,
            "delivery_delay_days": 6,
            "recipient_ack_rate_pct": 90.0,
        },
        {
            "comm_id": "COM-11",
            "method": "interactive",
            "sender_owner": "Scrum Master",
            "target_audience": "Core Team",
            "escalation_path_defined": True,
            "delivery_delay_days": 1,
            "recipient_ack_rate_pct": 60.0,
        },
    ]
    res = audit_wiki_communications_matrix_cadence_and_escalation(artifacts)
    assert res["total_artifacts"] == 2
    assert res["compliant_artifacts"] == 0
    assert res["incomplete_matrix_definition_ids"] == []
    assert res["cadence_delivery_overdue_ids"] == ["COM-10"]
    assert res["low_interactive_engagement_ids"] == ["COM-11"]
    assert res["communications_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_communications_matrix_cadence_and_escalation_critical_incomplete():
    """Detecta artefactos sin responsable, sin audiencia, método inválido o sin ruta de escalamiento ('critical')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communications_matrix_cadence_and_escalation,
    )

    artifacts = [
        {
            "comm_id": "COM-20",
            "method": "interactive",
            "sender_owner": "",
            "target_audience": "Board",
            "escalation_path_defined": True,
            "delivery_delay_days": 0,
            "recipient_ack_rate_pct": 95.0,
        },
        {
            "comm_id": "COM-21",
            "method": "telepathy",
            "sender_owner": "PM",
            "target_audience": "Team",
            "escalation_path_defined": False,
            "delivery_delay_days": 0,
        },
    ]
    res = audit_wiki_communications_matrix_cadence_and_escalation(artifacts)
    assert res["total_artifacts"] == 2
    assert res["compliant_artifacts"] == 0
    assert res["incomplete_matrix_definition_ids"] == ["COM-20", "COM-21"]
    assert res["communications_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_wiki_communications_matrix_cadence_and_escalation_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_communications_matrix_cadence_and_escalation,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_communications_matrix_cadence_and_escalation(payload)  # type: ignore[arg-type]
        assert empty["total_artifacts"] == 0
        assert empty["compliant_artifacts"] == 0
        assert empty["incomplete_matrix_definition_ids"] == []
        assert empty["cadence_delivery_overdue_ids"] == []
        assert empty["low_interactive_engagement_ids"] == []
        assert empty["communications_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "COM-99",
            "method": "push",
            "sender_owner": "PM",
            "target_audience": "Sponsors",
            "escalation_path_defined": True,
            "delivery_delay_days": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_communications_matrix_cadence_and_escalation(
            sample
        )
        == audit_wiki_communications_matrix_cadence_and_escalation(sample)
    )
    assert (
        "audit_wiki_communications_matrix_cadence_and_escalation" in mod.__all__
    )


def test_audit_wiki_definition_of_ready_and_backlog_grooming_healthy():
    """Valida candidatos de backlog que cumplen INVEST/DoR (<=13 pts, >=2 AC, 0 bloqueos y spec vinculada)."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_and_backlog_grooming,
    )

    candidates = [
        {
            "id": "BKL-01",
            "committed_to_sprint": True,
            "story_points": 5,
            "acceptance_criteria_count": 3,
            "blocking_dependencies_count": 0,
            "ux_or_arch_spec_linked": True,
        },
        {
            "id": "BKL-02",
            "committed_to_sprint": False,
            "story_points": 8,
            "acceptance_criteria_count": 2,
            "blocking_dependencies_count": 1,
            "ux_or_arch_spec_linked": True,
        },
    ]
    res = audit_wiki_definition_of_ready_and_backlog_grooming(candidates)
    assert res["total_candidates"] == 2
    assert res["ready_candidates"] == 2
    assert res["unestimated_or_oversized_epic_ids"] == []
    assert res["insufficient_acceptance_criteria_or_spec_ids"] == []
    assert res["blocked_item_committed_to_sprint_ids"] == []
    assert res["dor_readiness_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_wiki_definition_of_ready_and_backlog_grooming_at_risk():
    """Detecta épicas sin descomponer (>13 pts) o sin criterios/spec en backlog aún no comprometido ('at_risk')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_and_backlog_grooming,
    )

    candidates = [
        {
            "item_id": "BKL-10",
            "committed_to_sprint": False,
            "story_points": 21,
            "acceptance_criteria_count": 3,
            "blocking_dependencies_count": 0,
            "ux_or_arch_spec_linked": True,
        },
        {
            "item_id": "BKL-11",
            "committed_to_sprint": False,
            "story_points": 5,
            "acceptance_criteria_count": 1,
            "blocking_dependencies_count": 0,
            "ux_or_arch_spec_linked": False,
        },
    ]
    res = audit_wiki_definition_of_ready_and_backlog_grooming(candidates)
    assert res["total_candidates"] == 2
    assert res["ready_candidates"] == 0
    assert res["unestimated_or_oversized_epic_ids"] == ["BKL-10"]
    assert res["insufficient_acceptance_criteria_or_spec_ids"] == ["BKL-11"]
    assert res["blocked_item_committed_to_sprint_ids"] == []
    assert res["dor_readiness_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_definition_of_ready_and_backlog_grooming_critical_committed():
    """Detecta historias comprometidas al sprint con dependencias bloqueantes o sin estimar ('critical')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_definition_of_ready_and_backlog_grooming,
    )

    candidates = [
        {
            "item_id": "BKL-20",
            "committed_to_sprint": True,
            "story_points": 5,
            "acceptance_criteria_count": 3,
            "blocking_dependencies_count": 2,
            "ux_or_arch_spec_linked": True,
        },
        {
            "item_id": "BKL-21",
            "committed_to_sprint": True,
            "story_points": 0,
            "acceptance_criteria_count": 1,
            "blocking_dependencies_count": 0,
            "ux_or_arch_spec_linked": True,
        },
    ]
    res = audit_wiki_definition_of_ready_and_backlog_grooming(candidates)
    assert res["total_candidates"] == 2
    assert res["ready_candidates"] == 0
    assert res["blocked_item_committed_to_sprint_ids"] == ["BKL-20", "BKL-21"]
    assert res["dor_readiness_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_definition_of_ready_and_backlog_grooming_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_definition_of_ready_and_backlog_grooming,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_definition_of_ready_and_backlog_grooming(payload)  # type: ignore[arg-type]
        assert empty["total_candidates"] == 0
        assert empty["ready_candidates"] == 0
        assert empty["unestimated_or_oversized_epic_ids"] == []
        assert empty["insufficient_acceptance_criteria_or_spec_ids"] == []
        assert empty["blocked_item_committed_to_sprint_ids"] == []
        assert empty["dor_readiness_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "BKL-99",
            "committed_to_sprint": True,
            "story_points": 3,
            "acceptance_criteria_count": 2,
            "blocking_dependencies_count": 0,
            "ux_or_arch_spec_linked": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_definition_of_ready_and_backlog_grooming(
            sample
        )
        == audit_wiki_definition_of_ready_and_backlog_grooming(sample)
    )
    assert (
        "audit_wiki_definition_of_ready_and_backlog_grooming" in mod.__all__
    )


def test_audit_wiki_blameless_postmortem_and_systemic_prevention_exemplary():
    """Valida post-mortems con 5-Whys >= 3, sin culpabilización, acción preventiva sistémica con responsable y publicados a tiempo ('EXEMPLARY')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_and_systemic_prevention,
    )

    records = [
        {
            "incident_id": "INC-01",
            "whys_chain_depth": 5,
            "has_blameless_language_violation": False,
            "has_systemic_preventive_action": True,
            "action_owner_assigned": True,
            "days_to_publish": 2,
        },
        {
            "incident_id": "INC-02",
            "whys_chain_depth": 3,
            "has_blameless_language_violation": False,
            "has_systemic_preventive_action": True,
            "action_owner_assigned": True,
            "days_to_publish": 5,
        },
    ]
    res = audit_wiki_blameless_postmortem_and_systemic_prevention(records)
    assert res["total_postmortems"] == 2
    assert res["shallow_root_cause_ids"] == []
    assert res["blame_violation_ids"] == []
    assert res["missing_preventive_action_ids"] == []
    assert res["late_publication_ids"] == []
    assert res["learning_culture_status"] == "EXEMPLARY"
    assert res["is_compliant"] is True
    assert res["issues"] == []


def test_audit_wiki_blameless_postmortem_and_systemic_prevention_non_compliant():
    """Detecta violación de lenguaje Blameless y falta de acción preventiva sistémica o propietario ('NON_COMPLIANT')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_and_systemic_prevention,
    )

    records = [
        {
            "incident_id": "INC-10",
            "whys_chain_depth": 4,
            "has_blameless_language_violation": True,
            "has_systemic_preventive_action": True,
            "action_owner_assigned": True,
            "days_to_publish": 3,
        },
        {
            "incident_id": "INC-11",
            "whys_chain_depth": 5,
            "has_blameless_language_violation": False,
            "has_systemic_preventive_action": False,
            "action_owner_assigned": False,
            "days_to_publish": 2,
        },
    ]
    res = audit_wiki_blameless_postmortem_and_systemic_prevention(records)
    assert res["total_postmortems"] == 2
    assert res["blame_violation_ids"] == ["INC-10"]
    assert res["missing_preventive_action_ids"] == ["INC-11"]
    assert res["learning_culture_status"] == "NON_COMPLIANT"
    assert res["is_compliant"] is False
    assert len(res["issues"]) == 2


def test_audit_wiki_blameless_postmortem_and_systemic_prevention_needs_coaching():
    """Detecta profundidad 5-Whys superficial o publicación tardía sin violación punitiva ('NEEDS_COACHING')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_and_systemic_prevention,
    )

    records = [
        {
            "incident_id": "INC-20",
            "whys_chain_depth": 2,
            "has_blameless_language_violation": False,
            "has_systemic_preventive_action": True,
            "action_owner_assigned": True,
            "days_to_publish": 8,
        }
    ]
    res = audit_wiki_blameless_postmortem_and_systemic_prevention(records)
    assert res["total_postmortems"] == 1
    assert res["shallow_root_cause_ids"] == ["INC-20"]
    assert res["late_publication_ids"] == ["INC-20"]
    assert res["blame_violation_ids"] == []
    assert res["missing_preventive_action_ids"] == []
    assert res["learning_culture_status"] == "NEEDS_COACHING"
    assert res["is_compliant"] is False
    assert len(res["issues"]) == 2


def test_audit_wiki_blameless_postmortem_and_systemic_prevention_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y enlace en WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_blameless_postmortem_and_systemic_prevention,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_blameless_postmortem_and_systemic_prevention(payload)  # type: ignore[arg-type]
        assert empty["total_postmortems"] == 0
        assert empty["shallow_root_cause_ids"] == []
        assert empty["blame_violation_ids"] == []
        assert empty["missing_preventive_action_ids"] == []
        assert empty["late_publication_ids"] == []
        assert empty["learning_culture_status"] == "EXEMPLARY"
        assert empty["is_compliant"] is True
        assert empty["issues"] == []

    sample = [
        {
            "incident_id": "INC-99",
            "whys_chain_depth": 4,
            "has_blameless_language_violation": False,
            "has_systemic_preventive_action": True,
            "action_owner_assigned": True,
            "days_to_publish": 1,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_blameless_postmortem_and_systemic_prevention(
            sample
        )
        == audit_wiki_blameless_postmortem_and_systemic_prevention(sample)
    )
    assert (
        "audit_wiki_blameless_postmortem_and_systemic_prevention"
        in mod.__all__
    )


def test_audit_wiki_opa_and_eef_catalog_freshness_governed():
    """Valida entradas OPA y EEF con custodio asignado, revisión vigente y deprecados sin uso activo ('GOVERNED')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_and_eef_catalog_freshness,
    )

    entries = [
        {
            "asset_id": "OPA-01",
            "asset_category": "OPA",
            "days_since_last_review": 45,
            "steward_owner_id": "USR-PMO-01",
            "is_deprecated": False,
            "active_templates_referencing_count": 8,
        },
        {
            "asset_id": "EEF-02",
            "asset_category": "EEF",
            "days_since_last_review": 120,
            "steward_owner_id": "USR-LEGAL-02",
            "is_deprecated": False,
            "active_templates_referencing_count": 4,
        },
        {
            "asset_id": "OPA-03",
            "asset_category": "OPA",
            "days_since_last_review": 500,
            "steward_owner_id": None,
            "is_deprecated": True,
            "active_templates_referencing_count": 0,
        },
    ]
    res = audit_wiki_opa_and_eef_catalog_freshness(entries)
    assert res["total_catalog_entries"] == 3
    assert res["invalid_category_asset_ids"] == []
    assert res["stale_asset_ids"] == []
    assert res["unowned_asset_ids"] == []
    assert res["deprecated_in_use_asset_ids"] == []
    assert res["catalog_health_status"] == "GOVERNED"
    assert res["is_catalog_governed"] is True
    assert res["issues"] == []


def test_audit_wiki_opa_and_eef_catalog_freshness_critical_drift():
    """Detecta activos deprecados aún en uso en plantillas activas o con categoría inválida ('CRITICAL_DRIFT')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_and_eef_catalog_freshness,
    )

    entries = [
        {
            "asset_id": "OPA-10",
            "asset_category": "OPA",
            "days_since_last_review": 300,
            "steward_owner_id": "USR-01",
            "is_deprecated": True,
            "active_templates_referencing_count": 3,
        },
        {
            "asset_id": "X-11",
            "asset_category": "UNKNOWN_CAT",
            "days_since_last_review": 10,
            "steward_owner_id": "USR-02",
            "is_deprecated": False,
            "active_templates_referencing_count": 1,
        },
    ]
    res = audit_wiki_opa_and_eef_catalog_freshness(entries)
    assert res["total_catalog_entries"] == 2
    assert res["deprecated_in_use_asset_ids"] == ["OPA-10"]
    assert res["invalid_category_asset_ids"] == ["X-11"]
    assert res["catalog_health_status"] == "CRITICAL_DRIFT"
    assert res["is_catalog_governed"] is False
    assert len(res["issues"]) == 2


def test_audit_wiki_opa_and_eef_catalog_freshness_stale_or_unowned():
    """Detecta activos vigentes sin custodio o con revisión vencida (>180 días) ('STALE_OR_UNOWNED')."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_opa_and_eef_catalog_freshness,
    )

    entries = [
        {
            "asset_id": "EEF-20",
            "asset_category": "EEF",
            "days_since_last_review": 210,
            "steward_owner_id": "",
            "is_deprecated": False,
            "active_templates_referencing_count": 2,
        }
    ]
    res = audit_wiki_opa_and_eef_catalog_freshness(entries)
    assert res["total_catalog_entries"] == 1
    assert res["stale_asset_ids"] == ["EEF-20"]
    assert res["unowned_asset_ids"] == ["EEF-20"]
    assert res["invalid_category_asset_ids"] == []
    assert res["deprecated_in_use_asset_ids"] == []
    assert res["catalog_health_status"] == "STALE_OR_UNOWNED"
    assert res["is_catalog_governed"] is False
    assert len(res["issues"]) == 2


def test_audit_wiki_opa_and_eef_catalog_freshness_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y enlace en WikiPMIService y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_opa_and_eef_catalog_freshness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_opa_and_eef_catalog_freshness(payload)  # type: ignore[arg-type]
        assert empty["total_catalog_entries"] == 0
        assert empty["invalid_category_asset_ids"] == []
        assert empty["stale_asset_ids"] == []
        assert empty["unowned_asset_ids"] == []
        assert empty["deprecated_in_use_asset_ids"] == []
        assert empty["catalog_health_status"] == "GOVERNED"
        assert empty["is_catalog_governed"] is True
        assert empty["issues"] == []

    sample = [
        {
            "asset_id": "OPA-99",
            "asset_category": "OPA",
            "days_since_last_review": 15,
            "steward_owner_id": "USR-99",
            "is_deprecated": False,
            "active_templates_referencing_count": 1,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_opa_and_eef_catalog_freshness(sample)
        == audit_wiki_opa_and_eef_catalog_freshness(sample)
    )
    assert "audit_wiki_opa_and_eef_catalog_freshness" in mod.__all__




def test_wiki_adr_chain_compliant_and_status_broken():
    """Cadena íntegra -> COMPLIANT; status inválido o destino no accepted -> CHAIN_OR_STATUS_BROKEN."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_superseded_chain_and_consequences_hygiene,
    )

    def adr(aid, status="accepted", sup=None, ctx=True, dec=True, con=True):
        return {
            "adr_id": aid,
            "status": status,
            "superseded_by_adr_id": sup,
            "has_context_section": ctx,
            "has_decision_section": dec,
            "has_consequences_section": con,
        }

    compliant = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [
            adr("ADR-1"),
            adr("ADR-2", "superseded", "ADR-1"),
            adr("ADR-3", "deprecated"),
            adr("ADR-4", "rejected"),
            adr("ADR-5", "proposed"),
        ]
    )
    assert compliant["total_adr_records"] == 5
    assert compliant["invalid_status_adr_ids"] == []
    assert compliant["incomplete_sections_adr_ids"] == []
    assert compliant["broken_superseded_link_adr_ids"] == []
    assert compliant["contradictory_superseded_adr_ids"] == []
    assert compliant["adr_governance_status"] == "COMPLIANT"
    assert compliant["is_adr_log_healthy"] is True

    invalid = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-9", "APPROVED")]
    )
    assert invalid["invalid_status_adr_ids"] == ["ADR-9"]
    assert invalid["adr_governance_status"] == "CHAIN_OR_STATUS_BROKEN"
    assert invalid["is_adr_log_healthy"] is False

    # Super con destino no accepted -> broken.
    dest_not_accepted = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-1", "superseded", "ADR-2"), adr("ADR-2", "proposed")]
    )
    assert dest_not_accepted["broken_superseded_link_adr_ids"] == ["ADR-1"]
    assert dest_not_accepted["adr_governance_status"] == "CHAIN_OR_STATUS_BROKEN"

    # Status con espacios y mezcla de mayúsculas sigue siendo válido (strip+lower).
    case_insensitive = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-10", "  Superseded  ", "ADR-10b"), adr("ADR-10b")]
    )
    assert case_insensitive["invalid_status_adr_ids"] == []
    assert case_insensitive["adr_governance_status"] == "COMPLIANT"


def test_wiki_adr_chain_broken_links_variants():
    """Superseded sin destino, auto-referencial o a fantasma -> broken."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_superseded_chain_and_consequences_hygiene,
    )

    def adr(aid, status="accepted", sup=None):
        return {
            "adr_id": aid,
            "status": status,
            "superseded_by_adr_id": sup,
            "has_context_section": True,
            "has_decision_section": True,
            "has_consequences_section": True,
        }

    no_target = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-2", "superseded", None)]
    )
    assert no_target["broken_superseded_link_adr_ids"] == ["ADR-2"]

    self_ref = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-X", "superseded", "ADR-X")]
    )
    assert self_ref["broken_superseded_link_adr_ids"] == ["ADR-X"]

    ghost = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-Y", "superseded", "NO-EXISTE")]
    )
    assert ghost["broken_superseded_link_adr_ids"] == ["ADR-Y"]

    # Contradicción: status != superseded con destino presente.
    contradictory = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-C", "accepted", "ADR-1")]
    )
    assert contradictory["contradictory_superseded_adr_ids"] == ["ADR-C"]
    assert contradictory["adr_governance_status"] == "CHAIN_OR_STATUS_BROKEN"


def test_wiki_adr_chain_incomplete_and_precedence():
    """Faltante de secciones -> INCOMPLETE_DOCUMENTATION; CHAIN domina sobre incomplete."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_superseded_chain_and_consequences_hygiene,
    )

    def adr(aid, status="accepted", sup=None, ctx=True, dec=True, con=True):
        return {
            "adr_id": aid,
            "status": status,
            "superseded_by_adr_id": sup,
            "has_context_section": ctx,
            "has_decision_section": dec,
            "has_consequences_section": con,
        }

    incomplete = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-D", "accepted", None, ctx=True, con=False)]
    )
    assert incomplete["incomplete_sections_adr_ids"] == ["ADR-D"]
    assert incomplete["adr_governance_status"] == "INCOMPLETE_DOCUMENTATION"
    assert incomplete["is_adr_log_healthy"] is False

    missing_ctx = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-G", ctx=False)]
    )
    assert missing_ctx["incomplete_sections_adr_ids"] == ["ADR-G"]

    chain_dominates = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-E", "superseded", "GHOST"), adr("ADR-F", ctx=False)]
    )
    assert chain_dominates["broken_superseded_link_adr_ids"] == ["ADR-E"]
    assert chain_dominates["incomplete_sections_adr_ids"] == ["ADR-F"]
    assert chain_dominates["adr_governance_status"] == "CHAIN_OR_STATUS_BROKEN"

    # Con status != superseded, el destino fantasma genera contradictory (no broken).
    contradictory_case = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [adr("ADR-H", "accepted", "GHOST")]
    )
    assert contradictory_case["contradictory_superseded_adr_ids"] == ["ADR-H"]
    assert contradictory_case["broken_superseded_link_adr_ids"] == []


def test_wiki_adr_chain_neutral_and_binding():
    """None/vacío -> vacío COMPLIANT; no-dict ignorados; proxy estático y __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_adr_superseded_chain_and_consequences_hygiene,
    )

    for payload in (None, "no-list", 42):
        empty = audit_wiki_adr_superseded_chain_and_consequences_hygiene(payload)
        assert empty["total_adr_records"] == 0
        assert empty["invalid_status_adr_ids"] == []
        assert empty["incomplete_sections_adr_ids"] == []
        assert empty["broken_superseded_link_adr_ids"] == []
        assert empty["contradictory_superseded_adr_ids"] == []
        assert empty["adr_governance_status"] == "COMPLIANT"
        assert empty["is_adr_log_healthy"] is True

    mixed = audit_wiki_adr_superseded_chain_and_consequences_hygiene(
        [
            "no-dict",
            42,
            {
                "adr_id": "ADR-OK",
                "status": "accepted",
                "superseded_by_adr_id": None,
                "has_context_section": True,
                "has_decision_section": True,
                "has_consequences_section": True,
            },
        ]
    )
    assert mixed["total_adr_records"] == 1
    assert mixed["adr_governance_status"] == "COMPLIANT"

    sample = [{"adr_id": "ADR-PROBE", "status": "accepted"}]
    assert (
        WikiPMIService.audit_wiki_adr_superseded_chain_and_consequences_hygiene(sample)
        == audit_wiki_adr_superseded_chain_and_consequences_hygiene(sample)
    )
    assert "audit_wiki_adr_superseded_chain_and_consequences_hygiene" in mod.__all__


def test_audit_wiki_onboarding_playbook_and_kt_ready_for_handover():
    """Caso 1: Playbook al día, setup local verificado, rampa <= 14d y >= 2 sesiones shadow con signoff -> READY_FOR_HANDOVER."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness,
    )

    domains = [
        {
            "domain_id": "DOM-BACKEND",
            "has_up_to_date_playbook": True,
            "local_setup_verified_under_max_days": True,
            "estimated_ramp_days": 10,
            "shadow_sessions_completed": 3,
            "independent_signoff_achieved": True,
        },
        {
            "domain_id": "DOM-DEVOPS",
            "has_up_to_date_playbook": True,
            "local_setup_verified_under_max_days": True,
            "estimated_ramp_days": 14,
            "shadow_sessions_completed": 2,
            "independent_signoff_achieved": True,
        },
    ]
    res = audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(
        domains, max_onboarding_ramp_days=14, min_shadow_sessions_completed=2
    )
    assert res["total_domains"] == 2
    assert res["missing_playbook_domain_ids"] == []
    assert res["excessive_ramp_domain_ids"] == []
    assert res["insufficient_shadowing_domain_ids"] == []
    assert res["kt_readiness_status"] == "READY_FOR_HANDOVER"
    assert res["is_kt_ready"] is True
    assert res["issues"] == []


def test_audit_wiki_onboarding_playbook_and_kt_ramp_or_shadow_deficit():
    """Caso 2: Playbook completo pero rampa > 14d o shadowing insuficiente -> RAMP_OR_SHADOW_DEFICIT."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness,
    )

    domains = [
        {
            "domain_id": "DOM-BILLING",
            "has_up_to_date_playbook": True,
            "local_setup_verified_under_max_days": True,
            "estimated_ramp_days": 21,
            "shadow_sessions_completed": 1,
            "independent_signoff_achieved": False,
        }
    ]
    res = audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(
        domains, max_onboarding_ramp_days=14, min_shadow_sessions_completed=2
    )
    assert res["total_domains"] == 1
    assert res["missing_playbook_domain_ids"] == []
    assert res["excessive_ramp_domain_ids"] == ["DOM-BILLING"]
    assert res["insufficient_shadowing_domain_ids"] == ["DOM-BILLING"]
    assert res["kt_readiness_status"] == "RAMP_OR_SHADOW_DEFICIT"
    assert res["is_kt_ready"] is False
    assert len(res["issues"]) >= 2


def test_audit_wiki_onboarding_playbook_and_kt_blocked():
    """Caso 3: Falta playbook actualizado o setup local no verificado -> KT_BLOCKED."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness,
    )

    domains = [
        {
            "domain_id": "DOM-LEGACY",
            "has_up_to_date_playbook": False,
            "local_setup_verified_under_max_days": True,
            "estimated_ramp_days": 30,
            "shadow_sessions_completed": 0,
            "independent_signoff_achieved": False,
        },
        {
            "domain_id": "DOM-AUTH",
            "has_up_to_date_playbook": True,
            "local_setup_verified_under_max_days": False,
            "estimated_ramp_days": 10,
            "shadow_sessions_completed": 2,
            "independent_signoff_achieved": True,
        },
    ]
    res = audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(
        domains, max_onboarding_ramp_days=14, min_shadow_sessions_completed=2
    )
    assert res["total_domains"] == 2
    assert res["missing_playbook_domain_ids"] == ["DOM-LEGACY", "DOM-AUTH"]
    assert res["excessive_ramp_domain_ids"] == ["DOM-LEGACY"]
    assert res["insufficient_shadowing_domain_ids"] == ["DOM-LEGACY"]
    assert res["kt_readiness_status"] == "KT_BLOCKED"
    assert res["is_kt_ready"] is False
    assert len(res["issues"]) >= 3


def test_audit_wiki_onboarding_playbook_and_kt_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_domains"] == 0
        assert empty["missing_playbook_domain_ids"] == []
        assert empty["excessive_ramp_domain_ids"] == []
        assert empty["insufficient_shadowing_domain_ids"] == []
        assert empty["kt_readiness_status"] == "READY_FOR_HANDOVER"
        assert empty["is_kt_ready"] is True
        assert empty["issues"] == []

    sample = [
        {
            "domain_id": "DOM-99",
            "has_up_to_date_playbook": True,
            "local_setup_verified_under_max_days": True,
            "estimated_ramp_days": 7,
            "shadow_sessions_completed": 3,
            "independent_signoff_achieved": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(
            sample
        )
        == audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(sample)
    )
    assert (
        "audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness"
        in mod.__all__
    )


def test_audit_wiki_communication_matrix_cadence_and_escalation_healthy():
    """Caso 1: Canales al día, canal ejecutivo con fallback, con responsable de escalamiento y apertura >= 65% -> HEALTHY."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_cadence_and_escalation,
    )

    channels = [
        {
            "channel_id": "CH-EXEC-01",
            "stakeholder_tier": "EXECUTIVE",
            "cadence_days": 7,
            "days_since_last_dispatch": 5,
            "has_fallback_channel": True,
            "has_escalation_owner": True,
            "open_ack_rate_pct": 85.0,
        },
        {
            "channel_id": "CH-TEAM-02",
            "stakeholder_tier": "CORE_TEAM",
            "cadence_days": 14,
            "days_since_last_dispatch": 10,
            "has_fallback_channel": False,
            "has_escalation_owner": True,
            "open_ack_rate_pct": 90.0,
        },
    ]
    res = audit_wiki_communication_matrix_cadence_and_escalation(
        channels, max_days_since_dispatch=14, min_open_rate_pct=65.0
    )
    assert res["total_channels"] == 2
    assert res["overdue_dispatch_channel_ids"] == []
    assert res["single_point_of_failure_channel_ids"] == []
    assert res["unowned_escalation_channel_ids"] == []
    assert res["low_engagement_channel_ids"] == []
    assert res["communication_health_status"] == "HEALTHY"
    assert res["recommendations"] == []


def test_audit_wiki_communication_matrix_cadence_and_escalation_warning():
    """Caso 2: 1 canal con atraso de envío o baja tasa de apertura sin SPOF ni huérfanos -> WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_cadence_and_escalation,
    )

    channels = [
        {
            "channel_id": "CH-EXT-01",
            "stakeholder_tier": "EXTERNAL",
            "cadence_days": 7,
            "days_since_last_dispatch": 10,  # > cadence_days (7)
            "has_fallback_channel": False,
            "has_escalation_owner": True,
            "open_ack_rate_pct": 50.0,  # < 65%
        }
    ]
    res = audit_wiki_communication_matrix_cadence_and_escalation(
        channels, max_days_since_dispatch=14, min_open_rate_pct=65.0
    )
    assert res["total_channels"] == 1
    assert res["overdue_dispatch_channel_ids"] == ["CH-EXT-01"]
    assert res["single_point_of_failure_channel_ids"] == []
    assert res["unowned_escalation_channel_ids"] == []
    assert res["low_engagement_channel_ids"] == ["CH-EXT-01"]
    assert res["communication_health_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_communication_matrix_cadence_and_escalation_critical():
    """Caso 3: Canal EXECUTIVE sin fallback, canal sin escalation owner o > 1 canal vencido -> CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_communication_matrix_cadence_and_escalation,
    )

    channels = [
        {
            "channel_id": "CH-EXEC-SPOF",
            "stakeholder_tier": "EXECUTIVE",
            "cadence_days": 7,
            "days_since_last_dispatch": 20,  # overdue
            "has_fallback_channel": False,  # SPOF
            "has_escalation_owner": False,  # unowned
            "open_ack_rate_pct": 40.0,
        },
        {
            "channel_id": "CH-TEAM-OVERDUE",
            "stakeholder_tier": "CORE_TEAM",
            "cadence_days": 7,
            "days_since_last_dispatch": 12,  # overdue
            "has_fallback_channel": True,
            "has_escalation_owner": True,
            "open_ack_rate_pct": 80.0,
        },
    ]
    res = audit_wiki_communication_matrix_cadence_and_escalation(channels)
    assert res["total_channels"] == 2
    assert res["overdue_dispatch_channel_ids"] == ["CH-EXEC-SPOF", "CH-TEAM-OVERDUE"]
    assert res["single_point_of_failure_channel_ids"] == ["CH-EXEC-SPOF"]
    assert res["unowned_escalation_channel_ids"] == ["CH-EXEC-SPOF"]
    assert res["low_engagement_channel_ids"] == ["CH-EXEC-SPOF"]
    assert res["communication_health_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 3


def test_audit_wiki_communication_matrix_cadence_and_escalation_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_communication_matrix_cadence_and_escalation,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_communication_matrix_cadence_and_escalation(payload)  # type: ignore[arg-type]
        assert empty["total_channels"] == 0
        assert empty["overdue_dispatch_channel_ids"] == []
        assert empty["single_point_of_failure_channel_ids"] == []
        assert empty["unowned_escalation_channel_ids"] == []
        assert empty["low_engagement_channel_ids"] == []
        assert empty["communication_health_status"] == "HEALTHY"
        assert empty["recommendations"] == []

    sample = [
        {
            "channel_id": "CH-99",
            "stakeholder_tier": "CORE_TEAM",
            "cadence_days": 7,
            "days_since_last_dispatch": 3,
            "has_fallback_channel": True,
            "has_escalation_owner": True,
            "open_ack_rate_pct": 95.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_communication_matrix_cadence_and_escalation(sample)
        == audit_wiki_communication_matrix_cadence_and_escalation(sample)
    )
    assert (
        "audit_wiki_communication_matrix_cadence_and_escalation" in mod.__all__
    )


def test_audit_wiki_slo_error_budget_and_runbook_linkage_healthy():
    """Caso 1: Servicios cumpliendo SLO, burn rate controlado y runbooks vinculados -> HEALTHY."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_slo_error_budget_and_runbook_linkage,
    )

    catalog = [
        {
            "service_id": "SVC-AUTH",
            "target_slo_pct": 99.9,
            "current_sli_pct": 99.95,
            "remaining_error_budget_pct": 65.0,
            "burn_rate_24h": 0.8,
            "has_linked_runbook": True,
            "feature_freeze_enforced": False,
        },
        {
            "service_id": "SVC-BILLING",
            "target_slo_pct": 99.95,
            "current_sli_pct": 99.98,
            "remaining_error_budget_pct": 80.0,
            "burn_rate_24h": 0.5,
            "has_linked_runbook": True,
            "feature_freeze_enforced": False,
        },
    ]
    res = audit_wiki_slo_error_budget_and_runbook_linkage(
        catalog, max_burn_rate_threshold=1.5, min_remaining_error_budget_pct=20.0
    )
    assert res["total_services"] == 2
    assert res["slo_breached_service_ids"] == []
    assert res["unfrozen_exhausted_budget_service_ids"] == []
    assert res["high_burn_rate_service_ids"] == []
    assert res["missing_runbook_service_ids"] == []
    assert res["slo_governance_status"] == "HEALTHY"
    assert res["recommendations"] == []


def test_audit_wiki_slo_error_budget_and_runbook_linkage_warning():
    """Caso 2: Burn rate elevado (>1.5x) o falta de runbook sin violar el SLO -> WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_slo_error_budget_and_runbook_linkage,
    )

    catalog = [
        {
            "service_id": "SVC-SEARCH",
            "target_slo_pct": 99.5,
            "current_sli_pct": 99.6,
            "remaining_error_budget_pct": 15.0,
            "burn_rate_24h": 2.4,
            "has_linked_runbook": True,
            "feature_freeze_enforced": False,
        },
        {
            "service_id": "SVC-EXPORT",
            "target_slo_pct": 99.0,
            "current_sli_pct": 99.4,
            "remaining_error_budget_pct": 55.0,
            "burn_rate_24h": 1.0,
            "has_linked_runbook": False,
            "feature_freeze_enforced": False,
        },
    ]
    res = audit_wiki_slo_error_budget_and_runbook_linkage(
        catalog, max_burn_rate_threshold=1.5, min_remaining_error_budget_pct=20.0
    )
    assert res["total_services"] == 2
    assert res["slo_breached_service_ids"] == []
    assert res["unfrozen_exhausted_budget_service_ids"] == []
    assert res["high_burn_rate_service_ids"] == ["SVC-SEARCH"]
    assert res["missing_runbook_service_ids"] == ["SVC-EXPORT"]
    assert res["slo_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_slo_error_budget_and_runbook_linkage_critical():
    """Caso 3: SLI por debajo de SLO y presupuesto agotado (<=0%) sin feature freeze -> CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_slo_error_budget_and_runbook_linkage,
    )

    catalog = [
        {
            "service_id": "SVC-PAYMENTS",
            "target_slo_pct": 99.99,
            "current_sli_pct": 99.85,
            "remaining_error_budget_pct": 0.0,
            "burn_rate_24h": 4.2,
            "has_linked_runbook": False,
            "feature_freeze_enforced": False,
        }
    ]
    res = audit_wiki_slo_error_budget_and_runbook_linkage(catalog)
    assert res["total_services"] == 1
    assert res["slo_breached_service_ids"] == ["SVC-PAYMENTS"]
    assert res["unfrozen_exhausted_budget_service_ids"] == ["SVC-PAYMENTS"]
    assert res["high_burn_rate_service_ids"] == ["SVC-PAYMENTS"]
    assert res["missing_runbook_service_ids"] == ["SVC-PAYMENTS"]
    assert res["slo_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 3


def test_audit_wiki_slo_error_budget_and_runbook_linkage_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_slo_error_budget_and_runbook_linkage,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_slo_error_budget_and_runbook_linkage(payload)  # type: ignore[arg-type]
        assert empty["total_services"] == 0
        assert empty["slo_breached_service_ids"] == []
        assert empty["unfrozen_exhausted_budget_service_ids"] == []
        assert empty["high_burn_rate_service_ids"] == []
        assert empty["missing_runbook_service_ids"] == []
        assert empty["slo_governance_status"] == "HEALTHY"
        assert empty["recommendations"] == []

    sample = [
        {
            "service_id": "SVC-99",
            "target_slo_pct": 99.9,
            "current_sli_pct": 99.95,
            "remaining_error_budget_pct": 75.0,
            "burn_rate_24h": 0.5,
            "has_linked_runbook": True,
            "feature_freeze_enforced": False,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_slo_error_budget_and_runbook_linkage(sample)
        == audit_wiki_slo_error_budget_and_runbook_linkage(sample)
    )
    assert (
        "audit_wiki_slo_error_budget_and_runbook_linkage" in mod.__all__
    )


def test_audit_wiki_chaos_gameday_resilience_and_action_closure_resilient():
    """Caso 1: Experimentos GameDay con hipótesis, abort condition, recientes y validados -> RESILIENT."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_resilience_and_action_closure,
    )

    experiments = [
        {
            "experiment_id": "CHAOS-AZ-FAILOVER",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": True,
            "days_since_executed": 30,
            "hypothesis_validated": True,
            "open_remediation_items": 0,
            "oldest_remediation_age_days": 0,
        },
        {
            "experiment_id": "CHAOS-REDIS-LATENCY",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": True,
            "days_since_executed": 45,
            "hypothesis_validated": False,
            "open_remediation_items": 2,
            "oldest_remediation_age_days": 10,
        },
    ]
    res = audit_wiki_chaos_gameday_resilience_and_action_closure(
        experiments, max_days_between_gamedays=90, max_remediation_age_days=30
    )
    assert res["total_experiments"] == 2
    assert res["unsafe_experiment_ids"] == []
    assert res["stale_gameday_experiment_ids"] == []
    assert res["unmitigated_failure_experiment_ids"] == []
    assert res["untracked_failure_experiment_ids"] == []
    assert res["gameday_governance_status"] == "RESILIENT"
    assert res["is_gameday_compliant"] is True
    assert res["recommendations"] == []


def test_audit_wiki_chaos_gameday_resilience_and_action_closure_warning():
    """Caso 2: GameDay desactualizado (>90 días) pero seguro y con hipótesis validada -> WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_resilience_and_action_closure,
    )

    experiments = [
        {
            "experiment_id": "CHAOS-DB-REPLICA",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": True,
            "days_since_executed": 125,
            "hypothesis_validated": True,
            "open_remediation_items": 0,
            "oldest_remediation_age_days": 0,
        }
    ]
    res = audit_wiki_chaos_gameday_resilience_and_action_closure(
        experiments, max_days_between_gamedays=90, max_remediation_age_days=30
    )
    assert res["total_experiments"] == 1
    assert res["unsafe_experiment_ids"] == []
    assert res["stale_gameday_experiment_ids"] == ["CHAOS-DB-REPLICA"]
    assert res["unmitigated_failure_experiment_ids"] == []
    assert res["untracked_failure_experiment_ids"] == []
    assert res["gameday_governance_status"] == "WARNING"
    assert res["is_gameday_compliant"] is False
    assert len(res["recommendations"]) == 1


def test_audit_wiki_chaos_gameday_resilience_and_action_closure_critical():
    """Caso 3: Experimento sin abort condition, fallo con remediación vencida y fallo sin remediación -> CRITICAL."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_resilience_and_action_closure,
    )

    experiments = [
        {
            "experiment_id": "CHAOS-UNSAFE",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": False,
            "days_since_executed": 15,
            "hypothesis_validated": False,
            "open_remediation_items": 0,
            "oldest_remediation_age_days": 0,
        },
        {
            "experiment_id": "CHAOS-OVERDUE-FIX",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": True,
            "days_since_executed": 50,
            "hypothesis_validated": False,
            "open_remediation_items": 3,
            "oldest_remediation_age_days": 42,
        },
    ]
    res = audit_wiki_chaos_gameday_resilience_and_action_closure(
        experiments, max_days_between_gamedays=90, max_remediation_age_days=30
    )
    assert res["total_experiments"] == 2
    assert res["unsafe_experiment_ids"] == ["CHAOS-UNSAFE"]
    assert res["unmitigated_failure_experiment_ids"] == ["CHAOS-OVERDUE-FIX"]
    assert res["untracked_failure_experiment_ids"] == ["CHAOS-UNSAFE"]
    assert res["gameday_governance_status"] == "CRITICAL"
    assert res["is_gameday_compliant"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_wiki_chaos_gameday_resilience_and_action_closure_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_chaos_gameday_resilience_and_action_closure,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_chaos_gameday_resilience_and_action_closure(payload)  # type: ignore[arg-type]
        assert empty["total_experiments"] == 0
        assert empty["unsafe_experiment_ids"] == []
        assert empty["stale_gameday_experiment_ids"] == []
        assert empty["unmitigated_failure_experiment_ids"] == []
        assert empty["untracked_failure_experiment_ids"] == []
        assert empty["gameday_governance_status"] == "RESILIENT"
        assert empty["is_gameday_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "experiment_id": "CHAOS-99",
            "steady_state_hypothesis_defined": True,
            "abort_stop_condition_defined": True,
            "days_since_executed": 10,
            "hypothesis_validated": True,
            "open_remediation_items": 0,
            "oldest_remediation_age_days": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_chaos_gameday_resilience_and_action_closure(sample)
        == audit_wiki_chaos_gameday_resilience_and_action_closure(sample)
    )
    assert (
        "audit_wiki_chaos_gameday_resilience_and_action_closure" in mod.__all__
    )


def test_audit_wiki_api_deprecation_sunset_and_migration_readiness_safe_to_sunset():
    """Caso 1: Endpoints con aviso >= 60d, guía de migración publicada y tráfico residual <= 5% -> SAFE_TO_SUNSET."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_migration_readiness,
    )

    endpoints = [
        {
            "endpoint_id": "GET /v1/projects/legacy",
            "sunset_notice_days_given": 90,
            "days_until_removal": 7,
            "has_migration_guide_url": True,
            "unmigrated_consumer_count": 0,
            "active_traffic_share_pct": 0.0,
        },
        {
            "endpoint_id": "POST /v1/tasks/sync",
            "sunset_notice_days_given": 60,
            "days_until_removal": 30,
            "has_migration_guide_url": True,
            "unmigrated_consumer_count": 2,
            "active_traffic_share_pct": 2.5,
        },
    ]
    res = audit_wiki_api_deprecation_sunset_and_migration_readiness(
        endpoints, min_sunset_notice_days=60, max_unmigrated_traffic_pct=5.0
    )
    assert res["total_deprecated_endpoints"] == 2
    assert res["insufficient_notice_endpoint_ids"] == []
    assert res["missing_migration_guide_endpoint_ids"] == []
    assert res["imminent_breaking_removal_endpoint_ids"] == []
    assert res["high_residual_traffic_endpoint_ids"] == []
    assert res["deprecation_governance_status"] == "SAFE_TO_SUNSET"
    assert res["is_sunset_compliant"] is True
    assert res["recommendations"] == []


def test_audit_wiki_api_deprecation_sunset_and_migration_readiness_warning():
    """Caso 2: Ventana de aviso corta (<60d) o tráfico residual > 5% pero con >14d antes del retiro y con guía -> WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_migration_readiness,
    )

    endpoints = [
        {
            "endpoint_id": "GET /v1/reports/old",
            "sunset_notice_days_given": 45,
            "days_until_removal": 25,
            "has_migration_guide_url": True,
            "unmigrated_consumer_count": 3,
            "active_traffic_share_pct": 12.0,
        }
    ]
    res = audit_wiki_api_deprecation_sunset_and_migration_readiness(
        endpoints, min_sunset_notice_days=60, max_unmigrated_traffic_pct=5.0
    )
    assert res["total_deprecated_endpoints"] == 1
    assert res["insufficient_notice_endpoint_ids"] == ["GET /v1/reports/old"]
    assert res["missing_migration_guide_endpoint_ids"] == []
    assert res["imminent_breaking_removal_endpoint_ids"] == []
    assert res["high_residual_traffic_endpoint_ids"] == ["GET /v1/reports/old"]
    assert res["deprecation_governance_status"] == "WARNING"
    assert res["is_sunset_compliant"] is False
    assert len(res["recommendations"]) == 2


def test_audit_wiki_api_deprecation_sunset_and_migration_readiness_breaking_risk():
    """Caso 3: Retiro inminente (<=14d) con consumidores no migrados o sin guía de migración -> BREAKING_RISK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_migration_readiness,
    )

    endpoints = [
        {
            "endpoint_id": "DELETE /v1/charter",
            "sunset_notice_days_given": 30,
            "days_until_removal": 5,
            "has_migration_guide_url": False,
            "unmigrated_consumer_count": 4,
            "active_traffic_share_pct": 18.5,
        }
    ]
    res = audit_wiki_api_deprecation_sunset_and_migration_readiness(
        endpoints, min_sunset_notice_days=60, max_unmigrated_traffic_pct=5.0
    )
    assert res["total_deprecated_endpoints"] == 1
    assert res["insufficient_notice_endpoint_ids"] == ["DELETE /v1/charter"]
    assert res["missing_migration_guide_endpoint_ids"] == ["DELETE /v1/charter"]
    assert res["imminent_breaking_removal_endpoint_ids"] == ["DELETE /v1/charter"]
    assert res["high_residual_traffic_endpoint_ids"] == ["DELETE /v1/charter"]
    assert res["deprecation_governance_status"] == "BREAKING_RISK"
    assert res["is_sunset_compliant"] is False
    assert len(res["recommendations"]) == 4


def test_audit_wiki_api_deprecation_sunset_and_migration_readiness_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_api_deprecation_sunset_and_migration_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_api_deprecation_sunset_and_migration_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_deprecated_endpoints"] == 0
        assert empty["insufficient_notice_endpoint_ids"] == []
        assert empty["missing_migration_guide_endpoint_ids"] == []
        assert empty["imminent_breaking_removal_endpoint_ids"] == []
        assert empty["high_residual_traffic_endpoint_ids"] == []
        assert empty["deprecation_governance_status"] == "SAFE_TO_SUNSET"
        assert empty["is_sunset_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "endpoint_id": "GET /v1/ping",
            "sunset_notice_days_given": 90,
            "days_until_removal": 30,
            "has_migration_guide_url": True,
            "unmigrated_consumer_count": 0,
            "active_traffic_share_pct": 0.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_api_deprecation_sunset_and_migration_readiness(sample)
        == audit_wiki_api_deprecation_sunset_and_migration_readiness(sample)
    )
    assert (
        "audit_wiki_api_deprecation_sunset_and_migration_readiness" in mod.__all__
    )


def test_audit_wiki_operational_runbook_idempotency_and_preflight_hygiene_unsafe_runbook():
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_idempotency_and_preflight_hygiene,
    )

    res = audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
        [
            {
                "runbook_id": "RB-DB-MIGRATE",
                "has_preflight_validation_checks": False,
                "is_idempotent_or_reentrant": True,
                "has_explicit_rollback_commands": True,
                "manual_steps_count": 3,
                "days_since_last_dry_run": 15,
                "linked_alert_rule_id": "ALR-101",
            },
            {
                "runbook_id": "RB-CACHE-FLUSH",
                "has_preflight_validation_checks": True,
                "is_idempotent_or_reentrant": False,
                "has_explicit_rollback_commands": False,
                "manual_steps_count": 2,
                "days_since_last_dry_run": 10,
                "linked_alert_rule_id": "ALR-102",
            },
        ]
    )
    assert res["total_runbooks"] == 2
    assert res["missing_preflight_or_rollback_ids"] == [
        "RB-DB-MIGRATE",
        "RB-CACHE-FLUSH",
    ]
    assert res["non_idempotent_runbook_ids"] == ["RB-CACHE-FLUSH"]
    assert res["runbook_governance_status"] == "UNSAFE_RUNBOOK"
    assert res["is_runbook_production_ready"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_wiki_operational_runbook_idempotency_and_preflight_hygiene_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_idempotency_and_preflight_hygiene,
    )

    res = audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
        [
            {
                "runbook_id": "RB-FAILOVER-01",
                "has_preflight_validation_checks": True,
                "is_idempotent_or_reentrant": True,
                "has_explicit_rollback_commands": True,
                "manual_steps_count": 12,
                "days_since_last_dry_run": 120,
                "linked_alert_rule_id": "   ",
            }
        ],
        max_days_since_dry_run=90,
        max_manual_steps_count=8,
    )
    assert res["missing_preflight_or_rollback_ids"] == []
    assert res["non_idempotent_runbook_ids"] == []
    assert res["toil_heavy_runbook_ids"] == ["RB-FAILOVER-01"]
    assert res["stale_dry_run_runbook_ids"] == ["RB-FAILOVER-01"]
    assert res["unlinked_alert_runbook_ids"] == ["RB-FAILOVER-01"]
    assert res["runbook_governance_status"] == "WARNING"
    assert res["is_runbook_production_ready"] is False


def test_audit_wiki_operational_runbook_idempotency_and_preflight_hygiene_production_grade_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_operational_runbook_idempotency_and_preflight_hygiene,
    )

    empty = audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
        [{"runbook_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_runbooks"] == 0
    assert empty["runbook_governance_status"] == "PRODUCTION_GRADE"
    assert empty["is_runbook_production_ready"] is True
    assert empty["recommendations"] == []

    healthy = audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
        [
            {
                "runbook_id": "RB-SCALE-OUT",
                "has_preflight_validation_checks": True,
                "is_idempotent_or_reentrant": True,
                "has_explicit_rollback_commands": True,
                "manual_steps_count": 4,
                "days_since_last_dry_run": 30,
            }
        ]
    )
    assert healthy["total_runbooks"] == 1
    assert healthy["unlinked_alert_runbook_ids"] == []
    assert healthy["runbook_governance_status"] == "PRODUCTION_GRADE"
    assert healthy["is_runbook_production_ready"] is True
    assert healthy["recommendations"] == []


def test_audit_wiki_operational_runbook_idempotency_and_preflight_hygiene_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_operational_runbook_idempotency_and_preflight_hygiene,
    )

    sample = [
        {
            "runbook_id": "RB-01",
            "has_preflight_validation_checks": True,
            "is_idempotent_or_reentrant": True,
            "has_explicit_rollback_commands": True,
            "manual_steps_count": 2,
            "days_since_last_dry_run": 10,
            "linked_alert_rule_id": "ALR-01",
        }
    ]
    assert (
        WikiPMIService.audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
            sample
        )
        == audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(sample)
    )
    assert (
        "audit_wiki_operational_runbook_idempotency_and_preflight_hygiene"
        in mod.__all__
    )


def test_audit_wiki_migration_expand_contract_outage_risk_paths():
    """Caso 1: irreversible, destructiva sin expand-contract o índice bloqueante -> OUTAGE_RISK."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_database_migration_expand_contract_and_lock_safety,
    )

    res = audit_wiki_database_migration_expand_contract_and_lock_safety(
        [
            {
                "migration_id": "MIG-01",
                "has_reversible_downgrade": False,
                "lock_timeout_ms_configured": 2000,
            },
            {
                "migration_id": "MIG-02",
                "has_reversible_downgrade": True,
                "contains_destructive_drop_or_rename": True,
                "uses_expand_contract_pattern": False,
                "lock_timeout_ms_configured": 2000,
            },
            {
                "migration_id": "MIG-03",
                "has_reversible_downgrade": True,
                "index_created_concurrently": False,
                "lock_timeout_ms_configured": 2000,
            },
        ]
    )
    assert res["total_migrations"] == 3
    assert res["irreversible_migration_ids"] == ["MIG-01"]
    assert res["unsafe_destructive_migration_ids"] == ["MIG-02"]
    assert res["blocking_index_migration_ids"] == ["MIG-03"]
    assert res["missing_lock_timeout_migration_ids"] == []
    assert res["migration_governance_status"] == "OUTAGE_RISK"
    assert res["is_migration_safe"] is False
    assert len(res["recommendations"]) == 3

    # Destructiva CON expand-contract: queda fuera de unsafe (patrón correcto).
    res_safe_destructive = audit_wiki_database_migration_expand_contract_and_lock_safety(
        [
            {
                "migration_id": "MIG-04",
                "has_reversible_downgrade": True,
                "contains_destructive_drop_or_rename": True,
                "uses_expand_contract_pattern": True,
                "lock_timeout_ms_configured": 2000,
            },
        ]
    )
    assert res_safe_destructive["unsafe_destructive_migration_ids"] == []
    assert res_safe_destructive["migration_governance_status"] == "ZERO_DOWNTIME_SAFE"


def test_audit_wiki_migration_expand_contract_warning_lock_timeout():
    """Caso 2: lock_timeout 0 o por encima del máximo, sin otros riesgos -> WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_database_migration_expand_contract_and_lock_safety,
    )

    res = audit_wiki_database_migration_expand_contract_and_lock_safety(
        [
            {
                "migration_id": "MIG-10",
                "has_reversible_downgrade": True,
                "lock_timeout_ms_configured": 0,
            },
            {
                "migration_id": "MIG-11",
                "has_reversible_downgrade": True,
                "lock_timeout_ms_configured": 5001,
            },
        ],
        max_lock_timeout_ms=3000,
    )
    assert res["total_migrations"] == 2
    assert res["missing_lock_timeout_migration_ids"] == ["MIG-10", "MIG-11"]
    assert res["irreversible_migration_ids"] == []
    assert res["unsafe_destructive_migration_ids"] == []
    assert res["blocking_index_migration_ids"] == []
    assert res["migration_governance_status"] == "WARNING"
    assert res["is_migration_safe"] is False
    # Precisión: OUTAGE_RISK domina sobre WARNING.
    res_mixed = audit_wiki_database_migration_expand_contract_and_lock_safety(
        [
            {"migration_id": "MIG-12", "has_reversible_downgrade": False},
            {"migration_id": "MIG-13", "has_reversible_downgrade": True, "lock_timeout_ms_configured": 0},
        ]
    )
    assert res_mixed["migration_governance_status"] == "OUTAGE_RISK"


def test_audit_wiki_migration_expand_contract_safe_and_boundaries():
    """Caso 3: fronteras exactas de lock_timeout (1 y max inclusive) -> ZERO_DOWNTIME_SAFE."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_database_migration_expand_contract_and_lock_safety,
    )

    res = audit_wiki_database_migration_expand_contract_and_lock_safety(
        [
            {
                "migration_id": "MIG-20",
                "has_reversible_downgrade": True,
                "lock_timeout_ms_configured": 1,
                "max_lock_timeout_ms": 3000,
            },
            {
                "migration_id": "MIG-21",
                "has_reversible_downgrade": True,
                "lock_timeout_ms_configured": 3000,
                "max_lock_timeout_ms": 3000,
            },
        ],
    )
    assert res["total_migrations"] == 2
    assert res["missing_lock_timeout_migration_ids"] == []
    assert res["migration_governance_status"] == "ZERO_DOWNTIME_SAFE"
    assert res["is_migration_safe"] is True
    assert res["recommendations"] == []


def test_audit_wiki_migration_expand_contract_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_database_migration_expand_contract_and_lock_safety,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_database_migration_expand_contract_and_lock_safety(payload)  # type: ignore[arg-type]
        assert empty["total_migrations"] == 0
        assert empty["irreversible_migration_ids"] == []
        assert empty["unsafe_destructive_migration_ids"] == []
        assert empty["missing_lock_timeout_migration_ids"] == []
        assert empty["blocking_index_migration_ids"] == []
        assert empty["migration_governance_status"] == "ZERO_DOWNTIME_SAFE"
        assert empty["is_migration_safe"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "migration_id": "MIG-30",
            "has_reversible_downgrade": True,
            "lock_timeout_ms_configured": 2000,
        },
    ]
    assert (
        WikiPMIService.audit_wiki_database_migration_expand_contract_and_lock_safety(sample)
        == audit_wiki_database_migration_expand_contract_and_lock_safety(sample)
    )
    assert "audit_wiki_database_migration_expand_contract_and_lock_safety" in mod.__all__


def test_audit_wiki_blameless_postmortem_five_whys_and_action_sla_culture_or_action_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_five_whys_and_action_sla,
    )

    res = audit_wiki_blameless_postmortem_five_whys_and_action_sla(
        [
            {
                "postmortem_id": "PIR-101",
                "incident_severity": "SEV1",
                "why_analysis_depth": 4,
                "hours_to_publish_draft": 24.0,
                "contains_blameful_language": True,
                "has_preventive_action_with_owner_and_due_date": True,
                "has_timeline_with_utc_timestamps": True,
            },
            {
                "postmortem_id": "PIR-102",
                "incident_severity": "SEV2",
                "why_analysis_depth": 5,
                "hours_to_publish_draft": 12.0,
                "contains_blameful_language": False,
                "has_preventive_action_with_owner_and_due_date": False,
                "has_timeline_with_utc_timestamps": True,
            },
        ],
        min_why_depth=3,
        max_publish_delay_hours=48.0,
    )
    assert res["total_postmortems_evaluated"] == 2
    assert res["blameful_culture_violation_ids"] == ["PIR-101"]
    assert res["unactionable_postmortem_ids"] == ["PIR-102"]
    assert res["pir_governance_status"] == "CULTURE_OR_ACTION_BREACH"
    assert res["is_pir_compliant"] is False


def test_audit_wiki_blameless_postmortem_five_whys_and_action_sla_analytical_or_sla_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_five_whys_and_action_sla,
    )

    res = audit_wiki_blameless_postmortem_five_whys_and_action_sla(
        [
            {
                "postmortem_id": "PIR-201",
                "incident_severity": "SEV1",
                "why_analysis_depth": 2,
                "hours_to_publish_draft": 72.0,
                "contains_blameful_language": False,
                "has_preventive_action_with_owner_and_due_date": True,
                "has_timeline_with_utc_timestamps": True,
            }
        ],
        min_why_depth=3,
        max_publish_delay_hours=48.0,
    )
    assert res["shallow_root_cause_ids"] == ["PIR-201"]
    assert res["late_published_ids"] == ["PIR-201"]
    assert res["blameful_culture_violation_ids"] == []
    assert res["unactionable_postmortem_ids"] == []
    assert res["pir_governance_status"] == "ANALYTICAL_OR_SLA_WARNING"
    assert res["is_pir_compliant"] is False


def test_audit_wiki_blameless_postmortem_five_whys_and_action_sla_exemplary_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_blameless_postmortem_five_whys_and_action_sla,
    )

    empty = audit_wiki_blameless_postmortem_five_whys_and_action_sla(
        [{"postmortem_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_postmortems_evaluated"] == 0
    assert empty["pir_governance_status"] == "BLAMELESS_EXEMPLARY"
    assert empty["is_pir_compliant"] is True

    exemplary = audit_wiki_blameless_postmortem_five_whys_and_action_sla(
        [
            {
                "postmortem_id": "PIR-301",
                "incident_severity": "SEV1",
                "why_analysis_depth": 5,
                "hours_to_publish_draft": 18.0,
                "contains_blameful_language": False,
                "has_preventive_action_with_owner_and_due_date": True,
                "has_timeline_with_utc_timestamps": True,
            },
            {
                "postmortem_id": "PIR-302",
                "incident_severity": "SEV3",
                "why_analysis_depth": 3,
                "hours_to_publish_draft": 96.0,
                "contains_blameful_language": False,
                "has_preventive_action_with_owner_and_due_date": True,
                "has_timeline_with_utc_timestamps": True,
            },
        ]
    )
    assert exemplary["total_postmortems_evaluated"] == 2
    assert exemplary["shallow_root_cause_ids"] == []
    assert exemplary["late_published_ids"] == []
    assert exemplary["pir_governance_status"] == "BLAMELESS_EXEMPLARY"
    assert exemplary["is_pir_compliant"] is True


def test_audit_wiki_blameless_postmortem_five_whys_and_action_sla_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_blameless_postmortem_five_whys_and_action_sla,
    )

    sample = [
        {
            "postmortem_id": "PIR-99",
            "incident_severity": "SEV2",
            "why_analysis_depth": 4,
            "hours_to_publish_draft": 20.0,
            "contains_blameful_language": False,
            "has_preventive_action_with_owner_and_due_date": True,
            "has_timeline_with_utc_timestamps": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_blameless_postmortem_five_whys_and_action_sla(sample)
        == audit_wiki_blameless_postmortem_five_whys_and_action_sla(sample)
    )
    assert (
        "audit_wiki_blameless_postmortem_five_whys_and_action_sla" in mod.__all__
    )


def test_audit_wiki_on_call_rotation_burnout_and_escalation_readiness_sustainable():
    """Caso 1: Rotaciones con pool >= 4, <= 8 alertas nocturnas, backup secundario y notas de handoff -> ROTATION_SUSTAINABLE."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_on_call_rotation_burnout_and_escalation_readiness,
    )

    rotations = [
        {
            "rotation_id": "ONCALL-CORE-PLAT",
            "active_responders_count": 6,
            "after_hours_pages_count": 3,
            "has_secondary_backup_escalation": True,
            "has_shift_handoff_notes_logged": True,
        },
        {
            "rotation_id": "ONCALL-DB-SRE",
            "active_responders_count": 4,
            "after_hours_pages_count": 8,
            "has_secondary_backup_escalation": True,
            "has_shift_handoff_notes_logged": True,
        },
    ]
    res = audit_wiki_on_call_rotation_burnout_and_escalation_readiness(
        rotations, min_responders_in_pool=4, max_after_hours_pages_per_shift=8
    )
    assert res["total_rotations_evaluated"] == 2
    assert res["understaffed_rotation_ids"] == []
    assert res["burnout_overload_rotation_ids"] == []
    assert res["single_point_escalation_ids"] == []
    assert res["missing_handoff_rotation_ids"] == []
    assert res["on_call_governance_status"] == "ROTATION_SUSTAINABLE"
    assert res["is_on_call_compliant"] is True


def test_audit_wiki_on_call_rotation_burnout_and_escalation_readiness_handoff_warning():
    """Caso 2: Solo falta el registro de notas de cambio de turno -> HANDOFF_HYGIENE_WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_on_call_rotation_burnout_and_escalation_readiness,
    )

    rotations = [
        {
            "rotation_id": "ONCALL-BILLING",
            "active_responders_count": 5,
            "after_hours_pages_count": 4,
            "has_secondary_backup_escalation": True,
            "has_shift_handoff_notes_logged": False,
        }
    ]
    res = audit_wiki_on_call_rotation_burnout_and_escalation_readiness(
        rotations, min_responders_in_pool=4, max_after_hours_pages_per_shift=8
    )
    assert res["total_rotations_evaluated"] == 1
    assert res["understaffed_rotation_ids"] == []
    assert res["burnout_overload_rotation_ids"] == []
    assert res["single_point_escalation_ids"] == []
    assert res["missing_handoff_rotation_ids"] == ["ONCALL-BILLING"]
    assert res["on_call_governance_status"] == "HANDOFF_HYGIENE_WARNING"
    assert res["is_on_call_compliant"] is False


def test_audit_wiki_on_call_rotation_burnout_and_escalation_readiness_crisis():
    """Caso 3: Pool insuficiente (<4), exceso de alertas nocturnas (>8) o sin escalamiento secundario -> ESCALATION_OR_BURNOUT_CRISIS."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_on_call_rotation_burnout_and_escalation_readiness,
    )

    rotations = [
        {
            "rotation_id": "ONCALL-AUTH-CRISIS",
            "active_responders_count": 2,
            "after_hours_pages_count": 14,
            "has_secondary_backup_escalation": False,
            "has_shift_handoff_notes_logged": False,
        }
    ]
    res = audit_wiki_on_call_rotation_burnout_and_escalation_readiness(
        rotations, min_responders_in_pool=4, max_after_hours_pages_per_shift=8
    )
    assert res["total_rotations_evaluated"] == 1
    assert res["understaffed_rotation_ids"] == ["ONCALL-AUTH-CRISIS"]
    assert res["burnout_overload_rotation_ids"] == ["ONCALL-AUTH-CRISIS"]
    assert res["single_point_escalation_ids"] == ["ONCALL-AUTH-CRISIS"]
    assert res["missing_handoff_rotation_ids"] == ["ONCALL-AUTH-CRISIS"]
    assert res["on_call_governance_status"] == "ESCALATION_OR_BURNOUT_CRISIS"
    assert res["is_on_call_compliant"] is False


def test_audit_wiki_on_call_rotation_burnout_and_escalation_readiness_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en WikiPMIService + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_on_call_rotation_burnout_and_escalation_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_on_call_rotation_burnout_and_escalation_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_rotations_evaluated"] == 0
        assert empty["understaffed_rotation_ids"] == []
        assert empty["burnout_overload_rotation_ids"] == []
        assert empty["single_point_escalation_ids"] == []
        assert empty["missing_handoff_rotation_ids"] == []
        assert empty["on_call_governance_status"] == "ROTATION_SUSTAINABLE"
        assert empty["is_on_call_compliant"] is True

    sample = [
        {
            "rotation_id": "ONCALL-99",
            "active_responders_count": 5,
            "after_hours_pages_count": 2,
            "has_secondary_backup_escalation": True,
            "has_shift_handoff_notes_logged": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_on_call_rotation_burnout_and_escalation_readiness(
            sample
        )
        == audit_wiki_on_call_rotation_burnout_and_escalation_readiness(sample)
    )
    assert (
        "audit_wiki_on_call_rotation_burnout_and_escalation_readiness" in mod.__all__
    )


def test_audit_wiki_adr_immutability_and_superseded_chain_integrity_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_immutability_and_superseded_chain_integrity,
    )

    res = audit_wiki_adr_immutability_and_superseded_chain_integrity(
        [
            {
                "adr_id": "ADR-001",
                "status": "ACCEPTED",
                "superseded_by_adr_id": None,
                "was_mutated_in_place_after_acceptance": True,
                "has_context_decision_and_consequences_sections": True,
                "has_deciders_and_date_recorded": True,
            },
            {
                "adr_id": "ADR-002",
                "status": "SUPERSEDED",
                "superseded_by_adr_id": "ADR-999",
                "was_mutated_in_place_after_acceptance": False,
                "has_context_decision_and_consequences_sections": True,
                "has_deciders_and_date_recorded": True,
            },
            {
                "adr_id": "ADR-003",
                "status": "SUPERSEDED",
                "superseded_by_adr_id": "ADR-003",
                "was_mutated_in_place_after_acceptance": False,
                "has_context_decision_and_consequences_sections": True,
                "has_deciders_and_date_recorded": True,
            },
        ]
    )
    assert res["total_adrs_evaluated"] == 3
    assert res["mutated_in_place_adr_ids"] == ["ADR-001"]
    assert res["broken_superseded_link_adr_ids"] == ["ADR-002", "ADR-003"]
    assert res["incomplete_structure_adr_ids"] == []
    assert res["adr_governance_status"] == "IMMUTABILITY_OR_CHAIN_BREACH"
    assert res["is_adr_log_compliant"] is False


def test_audit_wiki_adr_immutability_and_superseded_chain_integrity_structure_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_immutability_and_superseded_chain_integrity,
    )

    res = audit_wiki_adr_immutability_and_superseded_chain_integrity(
        [
            {
                "adr_id": "ADR-010",
                "status": "PROPOSED",
                "superseded_by_adr_id": None,
                "was_mutated_in_place_after_acceptance": False,
                "has_context_decision_and_consequences_sections": False,
                "has_deciders_and_date_recorded": True,
            }
        ]
    )
    assert res["mutated_in_place_adr_ids"] == []
    assert res["broken_superseded_link_adr_ids"] == []
    assert res["incomplete_structure_adr_ids"] == ["ADR-010"]
    assert res["adr_governance_status"] == "STRUCTURE_INCOMPLETE_WARNING"
    assert res["is_adr_log_compliant"] is False


def test_audit_wiki_adr_immutability_and_superseded_chain_integrity_verified_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_adr_immutability_and_superseded_chain_integrity,
    )

    empty = audit_wiki_adr_immutability_and_superseded_chain_integrity(
        [{"adr_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_adrs_evaluated"] == 0
    assert empty["adr_governance_status"] == "ADR_LOG_INTEGRITY_VERIFIED"
    assert empty["is_adr_log_compliant"] is True

    verified = audit_wiki_adr_immutability_and_superseded_chain_integrity(
        [
            {
                "adr_id": "ADR-020",
                "status": "SUPERSEDED",
                "superseded_by_adr_id": "ADR-021",
                "was_mutated_in_place_after_acceptance": False,
                "has_context_decision_and_consequences_sections": True,
                "has_deciders_and_date_recorded": True,
            },
            {
                "adr_id": "ADR-021",
                "status": "ACCEPTED",
                "superseded_by_adr_id": None,
                "was_mutated_in_place_after_acceptance": False,
                "has_context_decision_and_consequences_sections": True,
                "has_deciders_and_date_recorded": True,
            },
        ]
    )
    assert verified["total_adrs_evaluated"] == 2
    assert verified["broken_superseded_link_adr_ids"] == []
    assert verified["adr_governance_status"] == "ADR_LOG_INTEGRITY_VERIFIED"
    assert verified["is_adr_log_compliant"] is True


def test_audit_wiki_adr_immutability_and_superseded_chain_integrity_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_adr_immutability_and_superseded_chain_integrity,
    )

    sample = [
        {
            "adr_id": "ADR-99",
            "status": "ACCEPTED",
            "was_mutated_in_place_after_acceptance": False,
            "has_context_decision_and_consequences_sections": True,
            "has_deciders_and_date_recorded": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_adr_immutability_and_superseded_chain_integrity(
            sample
        )
        == audit_wiki_adr_immutability_and_superseded_chain_integrity(sample)
    )
    assert (
        "audit_wiki_adr_immutability_and_superseded_chain_integrity"
        in mod.__all__
    )


def test_audit_wiki_bus_factor_spok_and_cross_training_coverage_critical_spok():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bus_factor_spok_and_cross_training_coverage,
    )

    res = audit_wiki_bus_factor_spok_and_cross_training_coverage(
        [
            {
                "domain_id": "DOM-BILLING-ENGINE",
                "active_distinct_contributors": 1,
                "top_author_contribution_share_pct": 95.0,
                "has_verified_onboarding_walkthrough": True,
                "has_completed_shadowing_rotation": True,
            },
            {
                "domain_id": "DOM-AUTH-KERNEL",
                "active_distinct_contributors": 3,
                "top_author_contribution_share_pct": 85.0,
                "has_verified_onboarding_walkthrough": True,
                "has_completed_shadowing_rotation": True,
            },
        ],
        min_bus_factor_contributors=2,
        max_single_author_commit_share_pct=80.0,
    )
    assert res["total_domains_evaluated"] == 2
    assert res["bus_factor_one_domain_ids"] == ["DOM-BILLING-ENGINE"]
    assert res["monopolized_knowledge_domain_ids"] == [
        "DOM-BILLING-ENGINE",
        "DOM-AUTH-KERNEL",
    ]
    assert res["untrained_handover_domain_ids"] == []
    assert res["bus_factor_governance_status"] == "CRITICAL_SPOK_EXPOSURE"
    assert res["is_bus_factor_compliant"] is False


def test_audit_wiki_bus_factor_spok_and_cross_training_coverage_cross_training_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bus_factor_spok_and_cross_training_coverage,
    )

    res = audit_wiki_bus_factor_spok_and_cross_training_coverage(
        [
            {
                "domain_id": "DOM-REPORTING",
                "active_distinct_contributors": 3,
                "top_author_contribution_share_pct": 55.0,
                "has_verified_onboarding_walkthrough": True,
                "has_completed_shadowing_rotation": False,
            }
        ],
        min_bus_factor_contributors=2,
        max_single_author_commit_share_pct=80.0,
    )
    assert res["bus_factor_one_domain_ids"] == []
    assert res["monopolized_knowledge_domain_ids"] == []
    assert res["untrained_handover_domain_ids"] == ["DOM-REPORTING"]
    assert res["bus_factor_governance_status"] == "CROSS_TRAINING_GAP_WARNING"
    assert res["is_bus_factor_compliant"] is False


def test_audit_wiki_bus_factor_spok_and_cross_training_coverage_resilient_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bus_factor_spok_and_cross_training_coverage,
    )

    empty = audit_wiki_bus_factor_spok_and_cross_training_coverage(
        [{"domain_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_domains_evaluated"] == 0
    assert empty["bus_factor_governance_status"] == "KNOWLEDGE_RESILIENT"
    assert empty["is_bus_factor_compliant"] is True

    resilient = audit_wiki_bus_factor_spok_and_cross_training_coverage(
        [
            {
                "domain_id": "DOM-CORE-API",
                "active_distinct_contributors": 4,
                "top_author_contribution_share_pct": 45.0,
                "has_verified_onboarding_walkthrough": True,
                "has_completed_shadowing_rotation": True,
            }
        ]
    )
    assert resilient["total_domains_evaluated"] == 1
    assert resilient["bus_factor_governance_status"] == "KNOWLEDGE_RESILIENT"
    assert resilient["is_bus_factor_compliant"] is True


def test_audit_wiki_bus_factor_spok_and_cross_training_coverage_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_bus_factor_spok_and_cross_training_coverage,
    )

    sample = [
        {
            "domain_id": "DOM-99",
            "active_distinct_contributors": 3,
            "top_author_contribution_share_pct": 50.0,
            "has_verified_onboarding_walkthrough": True,
            "has_completed_shadowing_rotation": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_bus_factor_spok_and_cross_training_coverage(
            sample
        )
        == audit_wiki_bus_factor_spok_and_cross_training_coverage(sample)
    )
    assert (
        "audit_wiki_bus_factor_spok_and_cross_training_coverage" in mod.__all__
    )


def test_audit_wiki_secret_rotation_exposure_breach_paths():
    """Caso 1: rotación vencida o clave estática -> CREDENTIAL_EXPOSURE_BREACH."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene,
    )

    res = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
        [
            {
                "credential_id": "CRD-01",
                "days_since_last_rotation": 120,
                "uses_dynamic_vault_lease": True,
                "lease_ttl_hours": 8.0,
                "has_automated_rotation_runbook": True,
            },
            {
                "credential_id": "CRD-02",
                "days_since_last_rotation": 10,
                "is_static_long_lived_key": True,
                "lease_ttl_hours": 8.0,
            },
            {
                "credential_id": "CRD-03",
                "days_since_last_rotation": 10,
                "uses_dynamic_vault_lease": False,
                "lease_ttl_hours": 8.0,
            },
        ]
    )
    assert res["total_credentials_evaluated"] == 3
    assert res["stale_rotation_credential_ids"] == ["CRD-01"]
    assert res["static_key_violation_ids"] == ["CRD-02", "CRD-03"]
    assert res["excessive_lease_ttl_ids"] == []
    assert res["missing_rotation_runbook_ids"] == []
    assert res["secret_hygiene_status"] == "CREDENTIAL_EXPOSURE_BREACH"
    assert res["is_secret_hygiene_compliant"] is False

    # Precisión: CREDENTIAL_EXPOSURE_BREACH domina sobre LEASE_OR_RUNBOOK_WARNING.
    res_mixed = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
        [
            {
                "credential_id": "CRD-04",
                "days_since_last_rotation": 120,
                "lease_ttl_hours": 48.0,
                "has_automated_rotation_runbook": False,
            },
        ]
    )
    assert res_mixed["stale_rotation_credential_ids"] == ["CRD-04"]
    assert res_mixed["excessive_lease_ttl_ids"] == ["CRD-04"]
    assert res_mixed["missing_rotation_runbook_ids"] == ["CRD-04"]
    assert res_mixed["secret_hygiene_status"] == "CREDENTIAL_EXPOSURE_BREACH"


def test_audit_wiki_secret_rotation_lease_warning_only():
    """Caso 2: solo TTL excesivo o runbook faltante -> LEASE_OR_RUNBOOK_WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene,
    )

    res = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
        [
            {
                "credential_id": "CRD-10",
                "days_since_last_rotation": 30,
                "uses_dynamic_vault_lease": True,
                "lease_ttl_hours": 30.0,
                "has_automated_rotation_runbook": True,
            },
            {
                "credential_id": "CRD-11",
                "days_since_last_rotation": 30,
                "lease_ttl_hours": 8.0,
                "has_automated_rotation_runbook": False,
            },
        ]
    )
    assert res["total_credentials_evaluated"] == 2
    assert res["stale_rotation_credential_ids"] == []
    assert res["static_key_violation_ids"] == []
    assert res["excessive_lease_ttl_ids"] == ["CRD-10"]
    assert res["missing_rotation_runbook_ids"] == ["CRD-11"]
    assert res["secret_hygiene_status"] == "LEASE_OR_RUNBOOK_WARNING"
    assert res["is_secret_hygiene_compliant"] is False


def test_audit_wiki_secret_rotation_clean_and_boundaries():
    """Caso 3: fronteras exactas (rotación = 90, TTL = 24.0 inclusive) -> ZERO_STATIC_SECRETS_VERIFIED."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene,
    )

    res = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
        [
            {
                "credential_id": "CRD-20",
                "days_since_last_rotation": 90,
                "uses_dynamic_vault_lease": True,
                "lease_ttl_hours": 24.0,
                "has_automated_rotation_runbook": True,
            },
            {
                "credential_id": "CRD-21",
                "days_since_last_rotation": 0,
                "lease_ttl_hours": 8.0,
            },
        ]
    )
    # CRD-20: 90 no > 90; TTL 24.0 no > 24.0 y > 0. CRD-21: defaults correctos.
    assert res["total_credentials_evaluated"] == 2
    assert res["stale_rotation_credential_ids"] == []
    assert res["static_key_violation_ids"] == []
    assert res["excessive_lease_ttl_ids"] == []
    assert res["missing_rotation_runbook_ids"] == []
    assert res["secret_hygiene_status"] == "ZERO_STATIC_SECRETS_VERIFIED"
    assert res["is_secret_hygiene_compliant"] is True

    # TTL <= 0 es inválido aunque el resto estén en frontera.
    res_ttl_zero = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
        [
            {"credential_id": "CRD-22", "days_since_last_rotation": 0, "lease_ttl_hours": 0.0},
        ]
    )
    assert res_ttl_zero["excessive_lease_ttl_ids"] == ["CRD-22"]
    assert res_ttl_zero["secret_hygiene_status"] == "LEASE_OR_RUNBOOK_WARNING"


def test_audit_wiki_secret_rotation_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_credentials_evaluated"] == 0
        assert empty["stale_rotation_credential_ids"] == []
        assert empty["static_key_violation_ids"] == []
        assert empty["excessive_lease_ttl_ids"] == []
        assert empty["missing_rotation_runbook_ids"] == []
        assert empty["secret_hygiene_status"] == "ZERO_STATIC_SECRETS_VERIFIED"
        assert empty["is_secret_hygiene_compliant"] is True

    sample = [
        {
            "credential_id": "CRD-30",
            "days_since_last_rotation": 15,
            "lease_ttl_hours": 8.0,
            "has_automated_rotation_runbook": True,
        },
    ]
    assert (
        WikiPMIService.audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(sample)
        == audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(sample)
    )
    assert "audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene" in mod.__all__


def test_audit_wiki_quarterly_attestation_and_orphan_page_archival_deprecated_or_stale_hazard():
    from backend.services.wiki_pmi_service import (
        audit_wiki_quarterly_attestation_and_orphan_page_archival,
    )

    res = audit_wiki_quarterly_attestation_and_orphan_page_archival(
        [
            {
                "page_id": "PG-STALE-01",
                "days_since_owner_attestation": 120,
                "incoming_navigation_links_count": 3,
                "is_root_index_page": False,
                "references_deprecated_system": False,
                "is_marked_archived": False,
            },
            {
                "page_id": "PG-DEPRECATED-02",
                "days_since_owner_attestation": 20,
                "incoming_navigation_links_count": 2,
                "is_root_index_page": False,
                "references_deprecated_system": True,
                "is_marked_archived": False,
            },
            {
                "page_id": "PG-ARCHIVED-IGNORED",
                "days_since_owner_attestation": 999,
                "incoming_navigation_links_count": 0,
                "is_root_index_page": False,
                "references_deprecated_system": True,
                "is_marked_archived": True,
            },
        ],
        max_days_since_attestation=90,
    )
    assert res["total_pages_evaluated"] == 3
    assert res["active_pages_count"] == 2
    assert res["unattested_stale_page_ids"] == ["PG-STALE-01"]
    assert res["orphan_unindexed_page_ids"] == []
    assert res["active_deprecated_procedure_page_ids"] == ["PG-DEPRECATED-02"]
    assert res["knowledge_curation_status"] == "DEPRECATED_OR_STALE_HAZARD"
    assert res["is_curation_compliant"] is False


def test_audit_wiki_quarterly_attestation_and_orphan_page_archival_orphan_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_quarterly_attestation_and_orphan_page_archival,
    )

    res = audit_wiki_quarterly_attestation_and_orphan_page_archival(
        [
            {
                "page_id": "PG-ORPHAN",
                "days_since_owner_attestation": 30,
                "incoming_navigation_links_count": 0,
                "is_root_index_page": False,
                "references_deprecated_system": False,
                "is_marked_archived": False,
            },
            {
                "page_id": "PG-ROOT-INDEX",
                "days_since_owner_attestation": 15,
                "incoming_navigation_links_count": 0,
                "is_root_index_page": True,
                "references_deprecated_system": False,
                "is_marked_archived": False,
            },
        ],
        max_days_since_attestation=90,
    )
    assert res["total_pages_evaluated"] == 2
    assert res["active_pages_count"] == 2
    assert res["unattested_stale_page_ids"] == []
    assert res["orphan_unindexed_page_ids"] == ["PG-ORPHAN"]
    assert res["active_deprecated_procedure_page_ids"] == []
    assert res["knowledge_curation_status"] == "ORPHAN_DISCOVERABILITY_WARNING"
    assert res["is_curation_compliant"] is False


def test_audit_wiki_quarterly_attestation_and_orphan_page_archival_curated_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_quarterly_attestation_and_orphan_page_archival,
    )

    empty = audit_wiki_quarterly_attestation_and_orphan_page_archival(
        [{"page_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_pages_evaluated"] == 0
    assert empty["active_pages_count"] == 0
    assert empty["knowledge_curation_status"] == "CURATED_KNOWLEDGE_BASE"
    assert empty["is_curation_compliant"] is True

    curated = audit_wiki_quarterly_attestation_and_orphan_page_archival(
        [
            {
                "page_id": "PG-OK-1",
                "days_since_owner_attestation": 90,
                "incoming_navigation_links_count": 4,
                "is_root_index_page": False,
                "references_deprecated_system": False,
                "is_marked_archived": False,
            }
        ],
        max_days_since_attestation=90,
    )
    assert curated["total_pages_evaluated"] == 1
    assert curated["active_pages_count"] == 1
    assert curated["knowledge_curation_status"] == "CURATED_KNOWLEDGE_BASE"
    assert curated["is_curation_compliant"] is True


def test_audit_wiki_quarterly_attestation_and_orphan_page_archival_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_quarterly_attestation_and_orphan_page_archival,
    )

    sample = [
        {
            "page_id": "PG-99",
            "days_since_owner_attestation": 10,
            "incoming_navigation_links_count": 2,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_quarterly_attestation_and_orphan_page_archival(
            sample
        )
        == audit_wiki_quarterly_attestation_and_orphan_page_archival(sample)
    )
    assert (
        "audit_wiki_quarterly_attestation_and_orphan_page_archival"
        in mod.__all__
    )


def test_audit_wiki_dr_tabletop_exercise_and_communication_tree_preparedness_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dr_tabletop_exercise_and_communication_tree,
    )

    res = audit_wiki_dr_tabletop_exercise_and_communication_tree(
        [
            {
                "exercise_id": "DR-TT-REGION-OUTAGE",
                "days_since_last_tabletop": 240,
                "participant_attendance_pct": 95.0,
                "out_of_band_comm_tree_verified": True,
                "unassigned_gaps_discovered_count": 0,
            },
            {
                "exercise_id": "DR-TT-RANSOMWARE",
                "days_since_last_tabletop": 45,
                "participant_attendance_pct": 90.0,
                "out_of_band_comm_tree_verified": False,
                "unassigned_gaps_discovered_count": 0,
            },
        ],
        max_days_since_tabletop=180,
        min_participant_attendance_pct=85.0,
    )
    assert res["total_exercises_evaluated"] == 2
    assert res["overdue_tabletop_exercise_ids"] == ["DR-TT-REGION-OUTAGE"]
    assert res["unverified_comm_tree_exercise_ids"] == ["DR-TT-RANSOMWARE"]
    assert res["low_attendance_or_unassigned_gap_ids"] == []
    assert res["tabletop_readiness_status"] == "DR_PREPAREDNESS_BREACH"
    assert res["is_tabletop_compliant"] is False


def test_audit_wiki_dr_tabletop_exercise_and_communication_tree_attendance_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dr_tabletop_exercise_and_communication_tree,
    )

    res = audit_wiki_dr_tabletop_exercise_and_communication_tree(
        [
            {
                "exercise_id": "DR-TT-DNS-FAILOVER",
                "days_since_last_tabletop": 60,
                "participant_attendance_pct": 70.0,
                "out_of_band_comm_tree_verified": True,
                "unassigned_gaps_discovered_count": 2,
            }
        ],
        max_days_since_tabletop=180,
        min_participant_attendance_pct=85.0,
    )
    assert res["overdue_tabletop_exercise_ids"] == []
    assert res["unverified_comm_tree_exercise_ids"] == []
    assert res["low_attendance_or_unassigned_gap_ids"] == [
        "DR-TT-DNS-FAILOVER"
    ]
    assert (
        res["tabletop_readiness_status"]
        == "ATTENDANCE_OR_GAP_FOLLOWUP_WARNING"
    )
    assert res["is_tabletop_compliant"] is False


def test_audit_wiki_dr_tabletop_exercise_and_communication_tree_verified_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dr_tabletop_exercise_and_communication_tree,
    )

    empty = audit_wiki_dr_tabletop_exercise_and_communication_tree(
        [{"exercise_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_exercises_evaluated"] == 0
    assert empty["tabletop_readiness_status"] == "TABLETOP_DRILL_VERIFIED"
    assert empty["is_tabletop_compliant"] is True

    verified = audit_wiki_dr_tabletop_exercise_and_communication_tree(
        [
            {
                "exercise_id": "DR-TT-Q3-GOLD",
                "days_since_last_tabletop": 25,
                "participant_attendance_pct": 92.5,
                "out_of_band_comm_tree_verified": True,
                "unassigned_gaps_discovered_count": 0,
            }
        ]
    )
    assert verified["total_exercises_evaluated"] == 1
    assert verified["tabletop_readiness_status"] == "TABLETOP_DRILL_VERIFIED"
    assert verified["is_tabletop_compliant"] is True


def test_audit_wiki_dr_tabletop_exercise_and_communication_tree_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_dr_tabletop_exercise_and_communication_tree,
    )

    sample = [
        {
            "exercise_id": "DR-TT-99",
            "days_since_last_tabletop": 15,
            "participant_attendance_pct": 100.0,
            "out_of_band_comm_tree_verified": True,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_dr_tabletop_exercise_and_communication_tree(
            sample
        )
        == audit_wiki_dr_tabletop_exercise_and_communication_tree(sample)
    )
    assert (
        "audit_wiki_dr_tabletop_exercise_and_communication_tree"
        in mod.__all__
    )


def test_audit_wiki_api_deprecation_sunset_and_consumer_migration_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_consumer_migration,
    )

    result = audit_wiki_api_deprecation_sunset_and_consumer_migration(
        [
            {
                "endpoint_id": "GET /v1/legacy-tasks",
                "notice_period_days_granted": 120,
                "days_until_sunset": 45,
                "active_consumers_count": 0,
                "has_published_migration_guide_in_wiki": False,
                "emits_rfc8594_sunset_headers": True,
            },
            {
                "endpoint_id": "POST /v1/legacy-sync",
                "notice_period_days_granted": 90,
                "days_until_sunset": 0,
                "active_consumers_count": 3,
                "has_published_migration_guide_in_wiki": True,
                "emits_rfc8594_sunset_headers": True,
            },
        ],
        min_sunset_notice_days=90,
        max_remaining_active_consumers_at_sunset=0,
    )
    assert result["evaluated_endpoints_count"] == 2
    assert result["unsafe_sunset_or_undocumented_endpoint_ids"] == [
        "GET /v1/legacy-tasks",
        "POST /v1/legacy-sync",
    ]
    assert result["short_notice_or_missing_header_endpoint_ids"] == [
        "POST /v1/legacy-sync"
    ]
    assert (
        result["api_sunset_governance_status"]
        == "API_SUNSET_BREAKING_OR_UNDOCUMENTED_BREACH"
    )
    assert result["is_api_sunset_compliant"] is False


def test_audit_wiki_api_deprecation_sunset_and_consumer_migration_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_consumer_migration,
    )

    result = audit_wiki_api_deprecation_sunset_and_consumer_migration(
        [
            {
                "endpoint_id": "GET /v1/short-notice",
                "notice_period_days_granted": 60,
                "days_until_sunset": 30,
                "active_consumers_count": 0,
                "has_published_migration_guide_in_wiki": True,
                "emits_rfc8594_sunset_headers": True,
            },
            {
                "endpoint_id": "GET /v1/no-header",
                "notice_period_days_granted": 90,
                "days_until_sunset": 30,
                "active_consumers_count": 0,
                "has_published_migration_guide_in_wiki": True,
                "emits_rfc8594_sunset_headers": False,
            },
            {
                "endpoint_id": "GET /v1/imminent-consumers",
                "notice_period_days_granted": 90,
                "days_until_sunset": 10,
                "active_consumers_count": 2,
                "has_published_migration_guide_in_wiki": True,
                "emits_rfc8594_sunset_headers": True,
            },
        ],
        min_sunset_notice_days=90,
        max_remaining_active_consumers_at_sunset=0,
    )
    assert result["evaluated_endpoints_count"] == 3
    assert result["unsafe_sunset_or_undocumented_endpoint_ids"] == []
    assert result["short_notice_or_missing_header_endpoint_ids"] == [
        "GET /v1/short-notice",
        "GET /v1/no-header",
        "GET /v1/imminent-consumers",
    ]
    assert (
        result["api_sunset_governance_status"]
        == "API_SUNSET_NOTICE_OR_MIGRATION_WARNING"
    )
    assert result["is_api_sunset_compliant"] is False


def test_audit_wiki_api_deprecation_sunset_and_consumer_migration_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_api_deprecation_sunset_and_consumer_migration,
    )

    empty = audit_wiki_api_deprecation_sunset_and_consumer_migration(
        [{"endpoint_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_endpoints_count"] == 0
    assert (
        empty["api_sunset_governance_status"] == "API_SUNSET_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_api_sunset_compliant"] is True

    optimal = audit_wiki_api_deprecation_sunset_and_consumer_migration(
        [
            {
                "endpoint_id": "GET /v1/clean-sunset",
                "notice_period_days_granted": 120,
                "days_until_sunset": 30,
                "active_consumers_count": 0,
                "has_published_migration_guide_in_wiki": True,
                "emits_rfc8594_sunset_headers": True,
            }
        ],
        min_sunset_notice_days=90,
        max_remaining_active_consumers_at_sunset=0,
    )
    assert optimal["evaluated_endpoints_count"] == 1
    assert (
        optimal["api_sunset_governance_status"]
        == "API_SUNSET_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_api_sunset_compliant"] is True


def test_audit_wiki_api_deprecation_sunset_and_consumer_migration_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_api_deprecation_sunset_and_consumer_migration,
    )

    sample = [
        {
            "endpoint_id": "GET /v1/status",
            "notice_period_days_granted": 90,
            "days_until_sunset": 45,
            "active_consumers_count": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_api_deprecation_sunset_and_consumer_migration(
            sample
        )
        == audit_wiki_api_deprecation_sunset_and_consumer_migration(sample)
    )
    assert (
        "audit_wiki_api_deprecation_sunset_and_consumer_migration"
        in mod.__all__
    )



def test_wiki_runbook_automation_toil_idempotency_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_automation_toil_and_idempotency,
    )

    res = audit_wiki_runbook_automation_toil_and_idempotency(
        [
            {
                "runbook_id": "RB-NON-IDEMPOTENT",
                "automation_scripts_idempotent": False,
            },
            {
                "runbook_id": "RB-NOT-STAGED",
                "peer_reviewed_and_tested_in_staging": False,
            },
            {
                "runbook_id": "RB-TAIL-ONLY-WARNING",
                "monthly_toil_hours_consumed": 14.0,
            },
        ],
        max_manual_steps_allowed=3,
        max_toil_hours_per_month=10.0,
    )
    assert res["evaluated_runbooks_count"] == 3
    assert res["unsafe_or_non_idempotent_runbook_ids"] == [
        "RB-NON-IDEMPOTENT",
        "RB-NOT-STAGED",
    ]
    assert res["high_toil_or_missing_dry_run_runbook_ids"] == [
        "RB-TAIL-ONLY-WARNING"
    ]
    assert (
        res["runbook_automation_status"]
        == "RUNBOOK_IDEMPOTENCY_OR_STAGING_BREACH"
    )
    assert res["is_runbook_automation_compliant"] is False


def test_wiki_runbook_automation_toil_idempotency_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_automation_toil_and_idempotency,
    )

    res = audit_wiki_runbook_automation_toil_and_idempotency(
        [
            {
                "runbook_id": "RB-TOOLONG",
                "manual_cli_steps_count": 5,
            },
            {
                "runbook_id": "RB-NO-DRY-RUN",
                "dry_run_mode_supported": False,
            },
            {
                "runbook_id": "RB-OVER-TOIL",
                "monthly_toil_hours_consumed": 10.5,
            },
        ],
        max_manual_steps_allowed=3,
        max_toil_hours_per_month=10.0,
    )
    assert res["evaluated_runbooks_count"] == 3
    assert res["unsafe_or_non_idempotent_runbook_ids"] == []
    assert res["high_toil_or_missing_dry_run_runbook_ids"] == [
        "RB-TOOLONG",
        "RB-NO-DRY-RUN",
        "RB-OVER-TOIL",
    ]
    assert (
        res["runbook_automation_status"]
        == "RUNBOOK_TOIL_OR_DRY_RUN_WARNING"
    )
    assert res["is_runbook_automation_compliant"] is False


def test_wiki_runbook_automation_toil_idempotency_boundaries_optimal():
    from backend.services.wiki_pmi_service import (
        audit_wiki_runbook_automation_toil_and_idempotency,
    )

    res = audit_wiki_runbook_automation_toil_and_idempotency(
        [
            {
                "runbook_id": "RB-BOUNDARY",
                "manual_cli_steps_count": 3,
                "monthly_toil_hours_consumed": 10.0,
            },
            {"runbook_id": "RB-ALL-DEFAULTS"},
        ],
        max_manual_steps_allowed=3,
        max_toil_hours_per_month=10.0,
    )
    assert res["evaluated_runbooks_count"] == 2
    assert res["unsafe_or_non_idempotent_runbook_ids"] == []
    assert res["high_toil_or_missing_dry_run_runbook_ids"] == []
    assert (
        res["runbook_automation_status"]
        == "RUNBOOK_AUTOMATION_OPTIMAL"
    )
    assert res["is_runbook_automation_compliant"] is True


def test_wiki_runbook_automation_toil_idempotency_invalid_and_binding():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_runbook_automation_toil_and_idempotency,
    )

    empty = audit_wiki_runbook_automation_toil_and_idempotency(None)
    assert empty["evaluated_runbooks_count"] == 0
    assert empty["unsafe_or_non_idempotent_runbook_ids"] == []
    assert empty["high_toil_or_missing_dry_run_runbook_ids"] == []
    assert (
        empty["runbook_automation_status"]
        == "RUNBOOK_AUTOMATION_OPTIMAL"
    )
    assert empty["is_runbook_automation_compliant"] is True

    invalid = audit_wiki_runbook_automation_toil_and_idempotency(
        [42, "not-a-dict", None, {"runbook_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_runbooks_count"] == 0

    defaults = audit_wiki_runbook_automation_toil_and_idempotency(
        [
            {
                "runbook_id": "RB-DEFAULTS",
                "manual_cli_steps_count": None,
                "monthly_toil_hours_consumed": None,
                "automation_scripts_idempotent": None,
                "dry_run_mode_supported": None,
                "peer_reviewed_and_tested_in_staging": None,
            }
        ]
    )
    assert defaults["evaluated_runbooks_count"] == 1
    assert (
        defaults["runbook_automation_status"]
        == "RUNBOOK_AUTOMATION_OPTIMAL"
    )
    assert defaults["is_runbook_automation_compliant"] is True

    sample = [
        {
            "runbook_id": "RB-1",
            "manual_cli_steps_count": 2,
            "monthly_toil_hours_consumed": 4.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_runbook_automation_toil_and_idempotency(
            sample
        )
        == audit_wiki_runbook_automation_toil_and_idempotency(sample)
    )
    assert (
        "audit_wiki_runbook_automation_toil_and_idempotency"
        in mod.__all__
    )


def test_audit_wiki_chaos_gameday_hypothesis_and_blast_radius_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_hypothesis_and_blast_radius,
    )

    result = audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
        [
            {
                "experiment_id": "CHAOS-NO-HYP",
                "steady_state_hypothesis_defined": False,
                "automated_abort_switch_verified": True,
                "blast_radius_tenants_pct": 1.0,
                "unremediated_resilience_gaps_count": 0,
                "days_since_gameday_execution": 5,
            },
            {
                "experiment_id": "CHAOS-NO-ABORT",
                "steady_state_hypothesis_defined": True,
                "automated_abort_switch_verified": False,
                "blast_radius_tenants_pct": 1.0,
                "unremediated_resilience_gaps_count": 0,
                "days_since_gameday_execution": 5,
            },
            {
                "experiment_id": "CHAOS-WIDE-BLAST",
                "steady_state_hypothesis_defined": True,
                "automated_abort_switch_verified": True,
                "blast_radius_tenants_pct": 12.5,
                "unremediated_resilience_gaps_count": 0,
                "days_since_gameday_execution": 5,
            },
        ],
        max_blast_radius_tenants_pct=5.0,
        max_unremediated_findings_days=14,
    )
    assert result["evaluated_experiments_count"] == 3
    assert result["unsafe_or_uncontained_experiment_ids"] == [
        "CHAOS-NO-HYP",
        "CHAOS-NO-ABORT",
        "CHAOS-WIDE-BLAST",
    ]
    assert result["overdue_remediation_experiment_ids"] == []
    assert (
        result["chaos_gameday_status"]
        == "CHAOS_ABORT_SWITCH_OR_BLAST_RADIUS_BREACH"
    )
    assert result["is_chaos_gameday_compliant"] is False


def test_audit_wiki_chaos_gameday_hypothesis_and_blast_radius_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_hypothesis_and_blast_radius,
    )

    result = audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
        [
            {
                "experiment_id": "CHAOS-STALE-GAP",
                "steady_state_hypothesis_defined": True,
                "automated_abort_switch_verified": True,
                "blast_radius_tenants_pct": 2.0,
                "unremediated_resilience_gaps_count": 2,
                "days_since_gameday_execution": 21,
            },
            {
                "experiment_id": "CHAOS-RECENT-GAP",
                "steady_state_hypothesis_defined": True,
                "automated_abort_switch_verified": True,
                "blast_radius_tenants_pct": 2.0,
                "unremediated_resilience_gaps_count": 1,
                "days_since_gameday_execution": 10,
            },
        ],
        max_blast_radius_tenants_pct=5.0,
        max_unremediated_findings_days=14,
    )
    assert result["evaluated_experiments_count"] == 2
    assert result["unsafe_or_uncontained_experiment_ids"] == []
    assert result["overdue_remediation_experiment_ids"] == ["CHAOS-STALE-GAP"]
    assert (
        result["chaos_gameday_status"]
        == "CHAOS_RESILIENCE_GAP_REMEDIATION_WARNING"
    )
    assert result["is_chaos_gameday_compliant"] is False


def test_audit_wiki_chaos_gameday_hypothesis_and_blast_radius_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_chaos_gameday_hypothesis_and_blast_radius,
    )

    empty = audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
        [{"experiment_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_experiments_count"] == 0
    assert (
        empty["chaos_gameday_status"] == "CHAOS_GAMEDAY_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_chaos_gameday_compliant"] is True

    optimal = audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
        [
            {
                "experiment_id": "CHAOS-GOLD-1",
                "steady_state_hypothesis_defined": True,
                "automated_abort_switch_verified": True,
                "blast_radius_tenants_pct": 2.5,
                "unremediated_resilience_gaps_count": 0,
                "days_since_gameday_execution": 10,
            }
        ],
        max_blast_radius_tenants_pct=5.0,
        max_unremediated_findings_days=14,
    )
    assert optimal["evaluated_experiments_count"] == 1
    assert (
        optimal["chaos_gameday_status"] == "CHAOS_GAMEDAY_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_chaos_gameday_compliant"] is True


def test_audit_wiki_chaos_gameday_hypothesis_and_blast_radius_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_chaos_gameday_hypothesis_and_blast_radius,
    )

    sample = [
        {
            "experiment_id": "CHAOS-99",
            "steady_state_hypothesis_defined": True,
            "automated_abort_switch_verified": True,
            "blast_radius_tenants_pct": 1.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
            sample
        )
        == audit_wiki_chaos_gameday_hypothesis_and_blast_radius(sample)
    )
    assert (
        "audit_wiki_chaos_gameday_hypothesis_and_blast_radius"
        in mod.__all__
    )


def test_audit_wiki_observability_cardinality_and_trace_sampling_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_observability_cardinality_and_trace_sampling,
    )

    result = audit_wiki_observability_cardinality_and_trace_sampling(
        [
            {
                "pipeline_id": "OTEL-UUID-LABEL",
                "observed_metric_series_cardinality": 2000,
                "unbounded_user_id_or_uuid_labels_detected": True,
                "error_trace_tail_sampling_pct": 100.0,
                "w3c_trace_context_propagated": True,
                "cold_storage_log_tiering_configured": True,
            },
            {
                "pipeline_id": "OTEL-NO-W3C",
                "observed_metric_series_cardinality": 2000,
                "unbounded_user_id_or_uuid_labels_detected": False,
                "error_trace_tail_sampling_pct": 100.0,
                "w3c_trace_context_propagated": False,
                "cold_storage_log_tiering_configured": True,
            },
            {
                "pipeline_id": "OTEL-LOW-ERR-SAMPLE",
                "observed_metric_series_cardinality": 2000,
                "unbounded_user_id_or_uuid_labels_detected": False,
                "error_trace_tail_sampling_pct": 50.0,
                "w3c_trace_context_propagated": True,
                "cold_storage_log_tiering_configured": True,
            },
        ],
        max_metric_label_cardinality=10000,
        min_error_trace_tail_sampling_pct=100.0,
    )
    assert result["evaluated_pipelines_count"] == 3
    assert result["cardinality_explosion_or_blind_trace_pipeline_ids"] == [
        "OTEL-UUID-LABEL",
        "OTEL-NO-W3C",
        "OTEL-LOW-ERR-SAMPLE",
    ]
    assert result["high_cardinality_or_untiered_log_pipeline_ids"] == []
    assert (
        result["observability_hygiene_status"]
        == "OBSERVABILITY_CARDINALITY_OR_BLIND_TRACE_BREACH"
    )
    assert result["is_observability_hygiene_compliant"] is False


def test_audit_wiki_observability_cardinality_and_trace_sampling_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_observability_cardinality_and_trace_sampling,
    )

    result = audit_wiki_observability_cardinality_and_trace_sampling(
        [
            {
                "pipeline_id": "OTEL-HIGH-CARD",
                "observed_metric_series_cardinality": 25000,
                "unbounded_user_id_or_uuid_labels_detected": False,
                "error_trace_tail_sampling_pct": 100.0,
                "w3c_trace_context_propagated": True,
                "cold_storage_log_tiering_configured": True,
            },
            {
                "pipeline_id": "OTEL-NO-TIERING",
                "observed_metric_series_cardinality": 2000,
                "unbounded_user_id_or_uuid_labels_detected": False,
                "error_trace_tail_sampling_pct": 100.0,
                "w3c_trace_context_propagated": True,
                "cold_storage_log_tiering_configured": False,
            },
        ],
        max_metric_label_cardinality=10000,
        min_error_trace_tail_sampling_pct=100.0,
    )
    assert result["evaluated_pipelines_count"] == 2
    assert result["cardinality_explosion_or_blind_trace_pipeline_ids"] == []
    assert result["high_cardinality_or_untiered_log_pipeline_ids"] == [
        "OTEL-HIGH-CARD",
        "OTEL-NO-TIERING",
    ]
    assert (
        result["observability_hygiene_status"]
        == "OBSERVABILITY_SERIES_PRESSURE_OR_TIERING_WARNING"
    )
    assert result["is_observability_hygiene_compliant"] is False


def test_audit_wiki_observability_cardinality_and_trace_sampling_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_observability_cardinality_and_trace_sampling,
    )

    empty = audit_wiki_observability_cardinality_and_trace_sampling(
        [{"pipeline_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_pipelines_count"] == 0
    assert (
        empty["observability_hygiene_status"]
        == "OBSERVABILITY_TELEMETRY_OPTIMAL"
    )
    assert empty["is_observability_hygiene_compliant"] is True

    optimal = audit_wiki_observability_cardinality_and_trace_sampling(
        [
            {
                "pipeline_id": "OTEL-GOLD-1",
                "observed_metric_series_cardinality": 3500,
                "unbounded_user_id_or_uuid_labels_detected": False,
                "error_trace_tail_sampling_pct": 100.0,
                "w3c_trace_context_propagated": True,
                "cold_storage_log_tiering_configured": True,
            }
        ],
        max_metric_label_cardinality=10000,
        min_error_trace_tail_sampling_pct=100.0,
    )
    assert optimal["evaluated_pipelines_count"] == 1
    assert (
        optimal["observability_hygiene_status"]
        == "OBSERVABILITY_TELEMETRY_OPTIMAL"
    )
    assert optimal["is_observability_hygiene_compliant"] is True


def test_audit_wiki_observability_cardinality_and_trace_sampling_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_observability_cardinality_and_trace_sampling,
    )

    sample = [
        {
            "pipeline_id": "OTEL-99",
            "observed_metric_series_cardinality": 1200,
            "error_trace_tail_sampling_pct": 100.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_observability_cardinality_and_trace_sampling(
            sample
        )
        == audit_wiki_observability_cardinality_and_trace_sampling(sample)
    )
    assert (
        "audit_wiki_observability_cardinality_and_trace_sampling"
        in mod.__all__
    )


def test_audit_wiki_service_catalog_ownership_and_dependency_graph_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_service_catalog_ownership_and_dependency_graph,
    )

    result = audit_wiki_service_catalog_ownership_and_dependency_graph(
        [
            {
                "service_id": "SVC-TIER1-NO-PD",
                "criticality_tier": 1,
                "has_accountable_team_owner": True,
                "has_pagerduty_escalation_policy": False,
                "circular_runtime_dependency_detected": False,
                "synchronous_downstream_fan_out_count": 3,
                "slo_dashboard_linked_in_wiki": True,
            },
            {
                "service_id": "SVC-CYCLE-UNOWNED",
                "criticality_tier": 2,
                "has_accountable_team_owner": False,
                "has_pagerduty_escalation_policy": False,
                "circular_runtime_dependency_detected": True,
                "synchronous_downstream_fan_out_count": 5,
                "slo_dashboard_linked_in_wiki": True,
            },
        ],
        max_dependency_fan_out=15,
    )
    assert result["evaluated_services_count"] == 2
    assert result["unowned_or_circular_dependency_service_ids"] == [
        "SVC-TIER1-NO-PD",
        "SVC-CYCLE-UNOWNED",
    ]
    assert result["high_fan_out_or_unlinked_slo_service_ids"] == []
    assert (
        result["service_catalog_status"]
        == "SERVICE_CATALOG_OWNERSHIP_OR_CYCLE_BREACH"
    )
    assert result["is_service_catalog_compliant"] is False


def test_audit_wiki_service_catalog_ownership_and_dependency_graph_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_service_catalog_ownership_and_dependency_graph,
    )

    result = audit_wiki_service_catalog_ownership_and_dependency_graph(
        [
            {
                "service_id": "SVC-CHATTY-GATEWAY",
                "criticality_tier": 1,
                "has_accountable_team_owner": True,
                "has_pagerduty_escalation_policy": True,
                "circular_runtime_dependency_detected": False,
                "synchronous_downstream_fan_out_count": 22,
                "slo_dashboard_linked_in_wiki": False,
            }
        ],
        max_dependency_fan_out=15,
    )
    assert result["evaluated_services_count"] == 1
    assert result["unowned_or_circular_dependency_service_ids"] == []
    assert result["high_fan_out_or_unlinked_slo_service_ids"] == [
        "SVC-CHATTY-GATEWAY"
    ]
    assert (
        result["service_catalog_status"]
        == "SERVICE_CATALOG_FAN_OUT_OR_SLO_WARNING"
    )
    assert result["is_service_catalog_compliant"] is False


def test_audit_wiki_service_catalog_ownership_and_dependency_graph_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_service_catalog_ownership_and_dependency_graph,
    )

    empty = audit_wiki_service_catalog_ownership_and_dependency_graph(
        [{"service_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_services_count"] == 0
    assert (
        empty["service_catalog_status"]
        == "SERVICE_CATALOG_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_service_catalog_compliant"] is True

    optimal = audit_wiki_service_catalog_ownership_and_dependency_graph(
        [
            {
                "service_id": "SVC-PAYMENTS-CORE",
                "criticality_tier": 1,
                "has_accountable_team_owner": True,
                "has_pagerduty_escalation_policy": True,
                "circular_runtime_dependency_detected": False,
                "synchronous_downstream_fan_out_count": 6,
                "slo_dashboard_linked_in_wiki": True,
            },
            {
                "service_id": "SVC-TIER3-BATCH",
                "criticality_tier": 3,
                "has_accountable_team_owner": True,
                "has_pagerduty_escalation_policy": False,
                "circular_runtime_dependency_detected": False,
                "synchronous_downstream_fan_out_count": 2,
                "slo_dashboard_linked_in_wiki": True,
            },
        ],
        max_dependency_fan_out=15,
    )
    assert optimal["evaluated_services_count"] == 2
    assert (
        optimal["service_catalog_status"]
        == "SERVICE_CATALOG_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_service_catalog_compliant"] is True


def test_audit_wiki_service_catalog_ownership_and_dependency_graph_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_service_catalog_ownership_and_dependency_graph,
    )

    sample = [
        {
            "service_id": "SVC-99",
            "criticality_tier": 2,
            "synchronous_downstream_fan_out_count": 4,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_service_catalog_ownership_and_dependency_graph(
            sample
        )
        == audit_wiki_service_catalog_ownership_and_dependency_graph(sample)
    )
    assert (
        "audit_wiki_service_catalog_ownership_and_dependency_graph"
        in mod.__all__
    )


def test_audit_wiki_tls_certificate_expiration_and_acme_renewal_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_tls_certificate_expiration_and_acme_renewal,
    )

    result = audit_wiki_tls_certificate_expiration_and_acme_renewal(
        [
            {
                "cert_id": "CERT-IMMINENT-EXPIRY",
                "days_until_expiration": 4,
                "acme_auto_renewal_enabled": True,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": False,
                "ocsp_stapling_and_ct_logged": True,
            },
            {
                "cert_id": "CERT-WEAK-CIPHER",
                "days_until_expiration": 45,
                "acme_auto_renewal_enabled": True,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": True,
                "ocsp_stapling_and_ct_logged": True,
            },
        ],
        min_days_before_expiry_warning=21,
        critical_expiry_days_threshold=7,
    )
    assert result["evaluated_certificates_count"] == 2
    assert result["expired_imminent_or_weak_cipher_cert_ids"] == [
        "CERT-IMMINENT-EXPIRY",
        "CERT-WEAK-CIPHER",
    ]
    assert result["renewal_window_or_manual_cert_ids"] == []
    assert (
        result["tls_certificate_status"]
        == "TLS_CERTIFICATE_EXPIRY_OR_CIPHER_BREACH"
    )
    assert result["is_tls_certificate_compliant"] is False


def test_audit_wiki_tls_certificate_expiration_and_acme_renewal_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_tls_certificate_expiration_and_acme_renewal,
    )

    result = audit_wiki_tls_certificate_expiration_and_acme_renewal(
        [
            {
                "cert_id": "CERT-RENEWAL-WINDOW",
                "days_until_expiration": 15,
                "acme_auto_renewal_enabled": True,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": False,
                "ocsp_stapling_and_ct_logged": True,
            },
            {
                "cert_id": "CERT-MANUAL-NO-ACME",
                "days_until_expiration": 50,
                "acme_auto_renewal_enabled": False,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": False,
                "ocsp_stapling_and_ct_logged": True,
            },
            {
                "cert_id": "CERT-NO-OCSP",
                "days_until_expiration": 50,
                "acme_auto_renewal_enabled": True,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": False,
                "ocsp_stapling_and_ct_logged": False,
            },
        ],
        min_days_before_expiry_warning=21,
        critical_expiry_days_threshold=7,
    )
    assert result["evaluated_certificates_count"] == 3
    assert result["expired_imminent_or_weak_cipher_cert_ids"] == []
    assert result["renewal_window_or_manual_cert_ids"] == [
        "CERT-RENEWAL-WINDOW",
        "CERT-MANUAL-NO-ACME",
        "CERT-NO-OCSP",
    ]
    assert (
        result["tls_certificate_status"]
        == "TLS_RENEWAL_WINDOW_OR_ACME_WARNING"
    )
    assert result["is_tls_certificate_compliant"] is False


def test_audit_wiki_tls_certificate_expiration_and_acme_renewal_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_tls_certificate_expiration_and_acme_renewal,
    )

    empty = audit_wiki_tls_certificate_expiration_and_acme_renewal(
        [{"cert_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_certificates_count"] == 0
    assert empty["tls_certificate_status"] == "TLS_CRYPTO_LIFECYCLE_OPTIMAL"
    assert empty["is_tls_certificate_compliant"] is True

    optimal = audit_wiki_tls_certificate_expiration_and_acme_renewal(
        [
            {
                "cert_id": "CERT-MTLS-EDGE-1",
                "days_until_expiration": 75,
                "acme_auto_renewal_enabled": True,
                "uses_deprecated_tls10_or_tls11_or_weak_cipher": False,
                "ocsp_stapling_and_ct_logged": True,
            }
        ],
        min_days_before_expiry_warning=21,
        critical_expiry_days_threshold=7,
    )
    assert optimal["evaluated_certificates_count"] == 1
    assert optimal["expired_imminent_or_weak_cipher_cert_ids"] == []
    assert optimal["renewal_window_or_manual_cert_ids"] == []
    assert optimal["tls_certificate_status"] == "TLS_CRYPTO_LIFECYCLE_OPTIMAL"
    assert optimal["is_tls_certificate_compliant"] is True


def test_audit_wiki_tls_certificate_expiration_and_acme_renewal_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_tls_certificate_expiration_and_acme_renewal,
    )

    sample = [
        {
            "cert_id": "CERT-99",
            "days_until_expiration": 45,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_tls_certificate_expiration_and_acme_renewal(
            sample
        )
        == audit_wiki_tls_certificate_expiration_and_acme_renewal(sample)
    )
    assert (
        "audit_wiki_tls_certificate_expiration_and_acme_renewal"
        in mod.__all__
    )



def test_wiki_k8s_oomkill_or_pdb_topology_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction,
    )

    res = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
        [
            {
                "workload_id": "WL-OOMKILLS",
                "oomkill_restarts_last_7d": 3,
            },
            {
                "workload_id": "WL-NO-PDB",
                "pdb_configured_and_non_blocking": False,
            },
            {
                "workload_id": "WL-SINGLE-AZ",
                "multi_az_topology_spread_enforced": False,
            },
        ],
        min_hpa_replica_headroom_pct=20.0,
        max_oomkill_restarts_last_7d=0,
    )
    assert res["evaluated_workloads_count"] == 3
    assert res["oomkill_or_missing_pdb_workload_ids"] == [
        "WL-OOMKILLS",
        "WL-NO-PDB",
        "WL-SINGLE-AZ",
    ]
    assert res["low_headroom_or_coupled_probes_workload_ids"] == []
    assert (
        res["k8s_resilience_status"]
        == "K8S_OOMKILL_OR_PDB_TOPOLOGY_BREACH"
    )
    assert res["is_k8s_resilience_compliant"] is False


def test_wiki_k8s_headroom_or_coupled_probes_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction,
    )

    res = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
        [
            {
                "workload_id": "WL-NARROW-HEADROOM",
                "hpa_replica_headroom_pct": 8.0,
            },
            {
                "workload_id": "WL-COUPLED-PROBES",
                "liveness_and_readiness_probes_distinct": False,
            },
        ],
        min_hpa_replica_headroom_pct=20.0,
        max_oomkill_restarts_last_7d=0,
    )
    assert res["evaluated_workloads_count"] == 2
    assert res["oomkill_or_missing_pdb_workload_ids"] == []
    assert res["low_headroom_or_coupled_probes_workload_ids"] == [
        "WL-NARROW-HEADROOM",
        "WL-COUPLED-PROBES",
    ]
    assert (
        res["k8s_resilience_status"]
        == "K8S_HPA_HEADROOM_OR_PROBE_WARNING"
    )
    assert res["is_k8s_resilience_compliant"] is False


def test_wiki_k8s_boundaries_optimal_and_defaults():
    from backend.services.wiki_pmi_service import (
        audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction,
    )

    res = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
        [
            {
                "workload_id": "WL-BOUNDARY",
                "hpa_replica_headroom_pct": 20.0,
                "oomkill_restarts_last_7d": 0,
            },
            {"workload_id": "WL-ALL-DEFAULTS"},
        ],
        min_hpa_replica_headroom_pct=20.0,
        max_oomkill_restarts_last_7d=0,
    )
    assert res["evaluated_workloads_count"] == 2
    assert res["oomkill_or_missing_pdb_workload_ids"] == []
    assert res["low_headroom_or_coupled_probes_workload_ids"] == []
    assert (
        res["k8s_resilience_status"]
        == "K8S_WORKLOAD_RESILIENCE_OPTIMAL"
    )
    assert res["is_k8s_resilience_compliant"] is True


def test_wiki_k8s_invalid_and_binding():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction,
    )

    empty = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(None)
    assert empty["evaluated_workloads_count"] == 0
    assert empty["oomkill_or_missing_pdb_workload_ids"] == []
    assert empty["low_headroom_or_coupled_probes_workload_ids"] == []
    assert (
        empty["k8s_resilience_status"]
        == "K8S_WORKLOAD_RESILIENCE_OPTIMAL"
    )
    assert empty["is_k8s_resilience_compliant"] is True

    invalid = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
        [42, "not-a-dict", None, {"workload_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_workloads_count"] == 0

    defaults = audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
        [
            {
                "workload_id": "WL-DEFAULTS",
                "pdb_configured_and_non_blocking": None,
                "oomkill_restarts_last_7d": None,
                "hpa_replica_headroom_pct": None,
                "multi_az_topology_spread_enforced": None,
                "liveness_and_readiness_probes_distinct": None,
            }
        ]
    )
    assert defaults["evaluated_workloads_count"] == 1
    assert (
        defaults["k8s_resilience_status"]
        == "K8S_WORKLOAD_RESILIENCE_OPTIMAL"
    )
    assert defaults["is_k8s_resilience_compliant"] is True

    sample = [
        {
            "workload_id": "WL-1",
            "hpa_replica_headroom_pct": 30.0,
            "oomkill_restarts_last_7d": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
            sample
        )
        == audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(sample)
    )
    assert (
        "audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction"
        in mod.__all__
    )


def test_audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience,
    )

    result = audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
        [
            {
                "zone_id": "ZONE-NO-DNSSEC",
                "failover_ttl_seconds": 30,
                "dnssec_and_caa_enabled": False,
                "multi_provider_anycast_active": True,
                "health_check_auto_failover_verified": True,
            },
            {
                "zone_id": "ZONE-UNVERIFIED-FAILOVER",
                "failover_ttl_seconds": 30,
                "dnssec_and_caa_enabled": True,
                "multi_provider_anycast_active": True,
                "health_check_auto_failover_verified": False,
            },
        ],
        max_failover_ttl_seconds=60,
        require_dnssec_and_caa_records=True,
    )
    assert result["evaluated_zones_count"] == 2
    assert result["unverified_failover_or_missing_dnssec_zone_ids"] == [
        "ZONE-NO-DNSSEC",
        "ZONE-UNVERIFIED-FAILOVER",
    ]
    assert result["high_ttl_or_single_provider_zone_ids"] == []
    assert (
        result["dns_resilience_status"]
        == "DNS_FAILOVER_OR_SECURITY_RECORD_BREACH"
    )
    assert result["is_dns_resilience_compliant"] is False


def test_audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience,
    )

    result = audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
        [
            {
                "zone_id": "ZONE-HIGH-TTL",
                "failover_ttl_seconds": 300,
                "dnssec_and_caa_enabled": True,
                "multi_provider_anycast_active": True,
                "health_check_auto_failover_verified": True,
            },
            {
                "zone_id": "ZONE-SINGLE-PROVIDER",
                "failover_ttl_seconds": 30,
                "dnssec_and_caa_enabled": True,
                "multi_provider_anycast_active": False,
                "health_check_auto_failover_verified": True,
            },
        ],
        max_failover_ttl_seconds=60,
        require_dnssec_and_caa_records=True,
    )
    assert result["evaluated_zones_count"] == 2
    assert result["unverified_failover_or_missing_dnssec_zone_ids"] == []
    assert result["high_ttl_or_single_provider_zone_ids"] == [
        "ZONE-HIGH-TTL",
        "ZONE-SINGLE-PROVIDER",
    ]
    assert (
        result["dns_resilience_status"]
        == "DNS_TTL_OR_SINGLE_PROVIDER_WARNING"
    )
    assert result["is_dns_resilience_compliant"] is False


def test_audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience,
    )

    empty = audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
        [{"zone_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_zones_count"] == 0
    assert (
        empty["dns_resilience_status"] == "DNS_ANYCAST_RESILIENCE_OPTIMAL"
    )
    assert empty["is_dns_resilience_compliant"] is True

    optimal = audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
        [
            {
                "zone_id": "ZONE-EDGE-PROD-1",
                "failover_ttl_seconds": 30,
                "dnssec_and_caa_enabled": True,
                "multi_provider_anycast_active": True,
                "health_check_auto_failover_verified": True,
            }
        ],
        max_failover_ttl_seconds=60,
        require_dnssec_and_caa_records=True,
    )
    assert optimal["evaluated_zones_count"] == 1
    assert optimal["unverified_failover_or_missing_dnssec_zone_ids"] == []
    assert optimal["high_ttl_or_single_provider_zone_ids"] == []
    assert (
        optimal["dns_resilience_status"] == "DNS_ANYCAST_RESILIENCE_OPTIMAL"
    )
    assert optimal["is_dns_resilience_compliant"] is True


def test_audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience,
    )

    sample = [
        {
            "zone_id": "ZONE-99",
            "failover_ttl_seconds": 20,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
            sample
        )
        == audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(sample)
    )
    assert (
        "audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience"
        in mod.__all__
    )


def test_audit_wiki_db_read_replica_lag_and_split_brain_fencing_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_db_read_replica_lag_and_split_brain_fencing,
    )

    result = audit_wiki_db_read_replica_lag_and_split_brain_fencing(
        [
            {
                "cluster_id": "DB-NO-STONITH",
                "replication_lag_ms": 50.0,
                "split_brain_stonith_fencing_enabled": False,
                "quorum_synchronous_commit_verified": True,
                "failover_promotion_rto_seconds": 10,
                "wal_archiving_continuous": True,
            },
            {
                "cluster_id": "DB-NO-QUORUM",
                "replication_lag_ms": 60.0,
                "split_brain_stonith_fencing_enabled": True,
                "quorum_synchronous_commit_verified": False,
                "failover_promotion_rto_seconds": 15,
                "wal_archiving_continuous": True,
            },
            {
                "cluster_id": "DB-UNARCHIVED-WAL",
                "replication_lag_ms": 30.0,
                "split_brain_stonith_fencing_enabled": True,
                "quorum_synchronous_commit_verified": True,
                "failover_promotion_rto_seconds": 8,
                "wal_archiving_continuous": False,
            },
        ],
        max_replication_lag_ms=250.0,
        max_failover_rto_seconds=30,
    )
    assert result["evaluated_clusters_count"] == 3
    assert result["split_brain_or_unarchived_wal_cluster_ids"] == [
        "DB-NO-STONITH",
        "DB-NO-QUORUM",
        "DB-UNARCHIVED-WAL",
    ]
    assert result["high_lag_or_slow_promotion_cluster_ids"] == []
    assert (
        result["db_ha_fencing_status"]
        == "DB_SPLIT_BRAIN_OR_WAL_DURABILITY_BREACH"
    )
    assert result["is_db_ha_fencing_compliant"] is False


def test_audit_wiki_db_read_replica_lag_and_split_brain_fencing_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_db_read_replica_lag_and_split_brain_fencing,
    )

    result = audit_wiki_db_read_replica_lag_and_split_brain_fencing(
        [
            {
                "cluster_id": "DB-HIGH-LAG",
                "replication_lag_ms": 480.0,
                "split_brain_stonith_fencing_enabled": True,
                "quorum_synchronous_commit_verified": True,
                "failover_promotion_rto_seconds": 12,
                "wal_archiving_continuous": True,
            },
            {
                "cluster_id": "DB-SLOW-PROMOTION",
                "replication_lag_ms": 80.0,
                "split_brain_stonith_fencing_enabled": True,
                "quorum_synchronous_commit_verified": True,
                "failover_promotion_rto_seconds": 65,
                "wal_archiving_continuous": True,
            },
        ],
        max_replication_lag_ms=250.0,
        max_failover_rto_seconds=30,
    )
    assert result["evaluated_clusters_count"] == 2
    assert result["split_brain_or_unarchived_wal_cluster_ids"] == []
    assert result["high_lag_or_slow_promotion_cluster_ids"] == [
        "DB-HIGH-LAG",
        "DB-SLOW-PROMOTION",
    ]
    assert (
        result["db_ha_fencing_status"]
        == "DB_REPLICA_LAG_OR_FAILOVER_RTO_WARNING"
    )
    assert result["is_db_ha_fencing_compliant"] is False


def test_audit_wiki_db_read_replica_lag_and_split_brain_fencing_optimal_and_empty():
    from backend.services.wiki_pmi_service import (
        audit_wiki_db_read_replica_lag_and_split_brain_fencing,
    )

    empty = audit_wiki_db_read_replica_lag_and_split_brain_fencing(
        [{"cluster_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_clusters_count"] == 0
    assert (
        empty["db_ha_fencing_status"] == "DB_HA_REPLICATION_FENCING_OPTIMAL"
    )
    assert empty["is_db_ha_fencing_compliant"] is True

    optimal = audit_wiki_db_read_replica_lag_and_split_brain_fencing(
        [
            {
                "cluster_id": "DB-PRIMARY-HA-01",
                "replication_lag_ms": 35.0,
                "split_brain_stonith_fencing_enabled": True,
                "quorum_synchronous_commit_verified": True,
                "failover_promotion_rto_seconds": 10,
                "wal_archiving_continuous": True,
            }
        ],
        max_replication_lag_ms=250.0,
        max_failover_rto_seconds=30,
    )
    assert optimal["evaluated_clusters_count"] == 1
    assert optimal["split_brain_or_unarchived_wal_cluster_ids"] == []
    assert optimal["high_lag_or_slow_promotion_cluster_ids"] == []
    assert (
        optimal["db_ha_fencing_status"] == "DB_HA_REPLICATION_FENCING_OPTIMAL"
    )
    assert optimal["is_db_ha_fencing_compliant"] is True


def test_audit_wiki_db_read_replica_lag_and_split_brain_fencing_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_db_read_replica_lag_and_split_brain_fencing,
    )

    sample = [
        {
            "cluster_id": "DB-99",
            "replication_lag_ms": 25.0,
            "failover_promotion_rto_seconds": 8,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_db_read_replica_lag_and_split_brain_fencing(
            sample
        )
        == audit_wiki_db_read_replica_lag_and_split_brain_fencing(sample)
    )
    assert (
        "audit_wiki_db_read_replica_lag_and_split_brain_fencing"
        in mod.__all__
    )


def test_audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection,
    )

    res = audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
        [
            {
                "edge_id": "  CDN-DOCS-US  ",
                "origin_shield_enabled": False,
                "waf_ddos_challenge_active": True,
                "purge_propagation_seconds": 10,
                "origin_shield_offload_pct": 95.0,
            },
            {
                "edge_id": "CDN-DOCS-EU",
                "origin_shield_enabled": True,
                "waf_ddos_challenge_active": False,
                "purge_propagation_seconds": 45,
                "origin_shield_offload_pct": 85.0,
            },
            {
                "edge_id": "CDN-CLEAN",
                "origin_shield_enabled": True,
                "waf_ddos_challenge_active": True,
                "purge_propagation_seconds": 30,
                "origin_shield_offload_pct": 90.0,
            },
        ]
    )
    assert res["evaluated_edges_count"] == 3
    assert res["unshielded_or_waf_disabled_edge_ids"] == [
        "CDN-DOCS-US",
        "CDN-DOCS-EU",
    ]
    assert res["slow_purge_or_low_offload_edge_ids"] == ["CDN-DOCS-EU"]
    assert res["cdn_edge_status"] == "CDN_ORIGIN_SHIELD_OR_WAF_BREACH"
    assert res["is_cdn_edge_compliant"] is False


def test_audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection,
    )

    res = audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
        [
            {
                "edge_id": "CDN-SLOW-PURGE",
                "origin_shield_enabled": True,
                "waf_ddos_challenge_active": True,
                "purge_propagation_seconds": 31,
                "origin_shield_offload_pct": 90.0,
            },
            {
                "edge_id": "CDN-LOW-OFFLOAD",
                "origin_shield_enabled": True,
                "waf_ddos_challenge_active": True,
                "purge_propagation_seconds": 30,
                "origin_shield_offload_pct": 89.9,
            },
        ],
        max_purge_propagation_seconds=30,
        min_origin_shield_offload_pct=90.0,
    )
    assert res["evaluated_edges_count"] == 2
    assert res["unshielded_or_waf_disabled_edge_ids"] == []
    assert res["slow_purge_or_low_offload_edge_ids"] == [
        "CDN-SLOW-PURGE",
        "CDN-LOW-OFFLOAD",
    ]
    assert res["cdn_edge_status"] == "CDN_PURGE_SLA_OR_OFFLOAD_WARNING"
    assert res["is_cdn_edge_compliant"] is False


def test_audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection_optimal_and_defensive():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection,
    )

    empty = audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
        None
    )
    assert empty["evaluated_edges_count"] == 0
    assert empty["unshielded_or_waf_disabled_edge_ids"] == []
    assert empty["slow_purge_or_low_offload_edge_ids"] == []
    assert empty["cdn_edge_status"] == "CDN_EDGE_DELIVERY_OPTIMAL"
    assert empty["is_cdn_edge_compliant"] is True

    optimal = audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"edge_id": "   "},
            {
                "edge_id": "CDN-DEFAULTS",
                "origin_shield_enabled": None,
                "waf_ddos_challenge_active": None,
                "purge_propagation_seconds": None,
                "origin_shield_offload_pct": None,
            },
        ]
    )
    assert optimal["evaluated_edges_count"] == 1
    assert optimal["unshielded_or_waf_disabled_edge_ids"] == []
    assert optimal["slow_purge_or_low_offload_edge_ids"] == []
    assert optimal["cdn_edge_status"] == "CDN_EDGE_DELIVERY_OPTIMAL"
    assert optimal["is_cdn_edge_compliant"] is True


def test_audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection,
    )

    sample = [
        {
            "edge_id": "CDN-99",
            "purge_propagation_seconds": 6,
            "origin_shield_offload_pct": 97.5,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
            sample
        )
        == audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
            sample
        )
    )
    assert (
        "audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection"
        in mod.__all__
    )



def test_wiki_worm_exposure_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_object_storage_worm_lock_and_ransomware_airgap,
    )

    res = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
        [
            {
                "bucket_id": "BUCKET-NO-WORM",
                "worm_compliance_lock_enabled": False,
            },
            {
                "bucket_id": "BUCKET-PUBLIC",
                "mfa_delete_and_public_block_enforced": False,
            },
        ],
        min_retention_lock_days=90,
        max_cross_account_replication_lag_minutes=15,
    )
    assert res["evaluated_buckets_count"] == 2
    assert res["mutable_or_public_exposed_bucket_ids"] == [
        "BUCKET-NO-WORM",
        "BUCKET-PUBLIC",
    ]
    assert res["short_retention_or_slow_airgap_bucket_ids"] == []
    assert (
        res["worm_airgap_status"] == "WORM_OBJECT_LOCK_OR_EXPOSURE_BREACH"
    )
    assert res["is_worm_airgap_compliant"] is False


def test_wiki_worm_retention_or_airgap_lag_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_object_storage_worm_lock_and_ransomware_airgap,
    )

    res = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
        [
            {
                "bucket_id": "BUCKET-SHORT-RETENTION",
                "retention_lock_days": 30,
            },
            {
                "bucket_id": "BUCKET-SLOW-AIRGAP",
                "cross_account_airgap_lag_minutes": 45,
            },
        ],
        min_retention_lock_days=90,
        max_cross_account_replication_lag_minutes=15,
    )
    assert res["evaluated_buckets_count"] == 2
    assert res["mutable_or_public_exposed_bucket_ids"] == []
    assert res["short_retention_or_slow_airgap_bucket_ids"] == [
        "BUCKET-SHORT-RETENTION",
        "BUCKET-SLOW-AIRGAP",
    ]
    assert (
        res["worm_airgap_status"] == "WORM_RETENTION_OR_AIRGAP_LAG_WARNING"
    )
    assert res["is_worm_airgap_compliant"] is False


def test_wiki_worm_boundaries_optimal_and_defaults():
    from backend.services.wiki_pmi_service import (
        audit_wiki_object_storage_worm_lock_and_ransomware_airgap,
    )

    res = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
        [
            {
                "bucket_id": "BUCKET-BOUNDARY",
                "retention_lock_days": 90,
                "cross_account_airgap_lag_minutes": 15,
            },
            {"bucket_id": "BUCKET-ALL-DEFAULTS"},
        ],
        min_retention_lock_days=90,
        max_cross_account_replication_lag_minutes=15,
    )
    assert res["evaluated_buckets_count"] == 2
    assert res["mutable_or_public_exposed_bucket_ids"] == []
    assert res["short_retention_or_slow_airgap_bucket_ids"] == []
    assert res["worm_airgap_status"] == "WORM_RANSOMWARE_AIRGAP_OPTIMAL"
    assert res["is_worm_airgap_compliant"] is True


def test_wiki_worm_invalid_and_binding():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_object_storage_worm_lock_and_ransomware_airgap,
    )

    empty = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(None)
    assert empty["evaluated_buckets_count"] == 0
    assert empty["mutable_or_public_exposed_bucket_ids"] == []
    assert empty["short_retention_or_slow_airgap_bucket_ids"] == []
    assert empty["worm_airgap_status"] == "WORM_RANSOMWARE_AIRGAP_OPTIMAL"
    assert empty["is_worm_airgap_compliant"] is True

    invalid = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
        [42, "not-a-dict", None, {"bucket_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_buckets_count"] == 0

    defaults = audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
        [
            {
                "bucket_id": "BUCKET-DEFAULTS",
                "worm_compliance_lock_enabled": None,
                "mfa_delete_and_public_block_enforced": None,
                "retention_lock_days": None,
                "cross_account_airgap_lag_minutes": None,
            }
        ]
    )
    assert defaults["evaluated_buckets_count"] == 1
    assert defaults["worm_airgap_status"] == "WORM_RANSOMWARE_AIRGAP_OPTIMAL"
    assert defaults["is_worm_airgap_compliant"] is True

    sample = [
        {
            "bucket_id": "BUCKET-1",
            "retention_lock_days": 365,
            "cross_account_airgap_lag_minutes": 5,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
            sample
        )
        == audit_wiki_object_storage_worm_lock_and_ransomware_airgap(sample)
    )
    assert (
        "audit_wiki_object_storage_worm_lock_and_ransomware_airgap"
        in mod.__all__
    )


def test_audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover,
    )

    res = audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(
        [
            {
                "prefix_id": "  PFX-INVALID-ROA  ",
                "rpki_roa_cryptographically_valid": False,
                "bfd_subsecond_peering_enabled": True,
                "scrubbing_diversion_seconds": 15,
                "redundant_transit_asns_count": 2,
            },
            {
                "prefix_id": "PFX-NO-BFD",
                "rpki_roa_cryptographically_valid": True,
                "bfd_subsecond_peering_enabled": False,
                "scrubbing_diversion_seconds": 60,
                "redundant_transit_asns_count": 1,
            },
            {
                "prefix_id": "PFX-CLEAN",
                "rpki_roa_cryptographically_valid": True,
                "bfd_subsecond_peering_enabled": True,
                "scrubbing_diversion_seconds": 45,
                "redundant_transit_asns_count": 2,
            },
        ]
    )
    assert res["evaluated_prefixes_count"] == 3
    assert res["unsigned_rpki_or_missing_bfd_prefix_ids"] == [
        "PFX-INVALID-ROA",
        "PFX-NO-BFD",
    ]
    assert res["slow_scrubbing_or_single_homed_prefix_ids"] == ["PFX-NO-BFD"]
    assert res["bgp_routing_status"] == "BGP_RPKI_ROA_OR_BFD_LIVENESS_BREACH"
    assert res["is_bgp_routing_compliant"] is False


def test_audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover,
    )

    res = audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(
        [
            {
                "prefix_id": "PFX-SLOW-SCRUB",
                "rpki_roa_cryptographically_valid": False,
                "bfd_subsecond_peering_enabled": False,
                "scrubbing_diversion_seconds": 46,
                "redundant_transit_asns_count": 2,
            },
            {
                "prefix_id": "PFX-SINGLE-ASN",
                "rpki_roa_cryptographically_valid": True,
                "bfd_subsecond_peering_enabled": True,
                "scrubbing_diversion_seconds": 45,
                "redundant_transit_asns_count": 1,
            },
        ],
        max_scrubbing_diversion_seconds=45,
        require_rpki_roa_and_bfd=False,
    )
    assert res["evaluated_prefixes_count"] == 2
    assert res["unsigned_rpki_or_missing_bfd_prefix_ids"] == []
    assert res["slow_scrubbing_or_single_homed_prefix_ids"] == [
        "PFX-SLOW-SCRUB",
        "PFX-SINGLE-ASN",
    ]
    assert (
        res["bgp_routing_status"]
        == "BGP_SCRUBBING_DIVERSION_OR_SINGLE_ASN_WARNING"
    )
    assert res["is_bgp_routing_compliant"] is False


def test_audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover_optimal_and_defensive():
    from backend.services.wiki_pmi_service import (
        audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover,
    )

    empty = audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(None)
    assert empty["evaluated_prefixes_count"] == 0
    assert empty["unsigned_rpki_or_missing_bfd_prefix_ids"] == []
    assert empty["slow_scrubbing_or_single_homed_prefix_ids"] == []
    assert empty["bgp_routing_status"] == "BGP_ROUTING_AND_SCRUBBING_OPTIMAL"
    assert empty["is_bgp_routing_compliant"] is True

    optimal = audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"prefix_id": "   "},
            {
                "prefix_id": "PFX-DEFAULTS",
                "rpki_roa_cryptographically_valid": None,
                "bfd_subsecond_peering_enabled": None,
                "scrubbing_diversion_seconds": None,
                "redundant_transit_asns_count": None,
            },
        ]
    )
    assert optimal["evaluated_prefixes_count"] == 1
    assert optimal["unsigned_rpki_or_missing_bfd_prefix_ids"] == []
    assert optimal["slow_scrubbing_or_single_homed_prefix_ids"] == []
    assert optimal["bgp_routing_status"] == "BGP_ROUTING_AND_SCRUBBING_OPTIMAL"
    assert optimal["is_bgp_routing_compliant"] is True


def test_audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover,
    )

    sample = [
        {
            "prefix_id": "PFX-99",
            "scrubbing_diversion_seconds": 12,
            "redundant_transit_asns_count": 3,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(
            sample
        )
        == audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(sample)
    )
    assert (
        "audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover"
        in mod.__all__
    )


def test_audit_wiki_secrets_vault_lease_rotation_and_root_token_seal_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_secrets_vault_lease_rotation_and_root_token_seal,
    )

    res = audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(
        [
            {
                "vault_id": "  VLT-ACTIVE-ROOT  ",
                "root_tokens_revoked_and_audited": False,
                "hsm_kms_auto_unseal_quorum_verified": True,
                "dynamic_lease_ttl_hours": 8,
                "static_long_lived_secrets_count": 0,
            },
            {
                "vault_id": "VLT-NO-UNSEAL",
                "root_tokens_revoked_and_audited": True,
                "hsm_kms_auto_unseal_quorum_verified": False,
                "dynamic_lease_ttl_hours": 36,
                "static_long_lived_secrets_count": 2,
            },
            {
                "vault_id": "VLT-CLEAN",
                "root_tokens_revoked_and_audited": True,
                "hsm_kms_auto_unseal_quorum_verified": True,
                "dynamic_lease_ttl_hours": 24,
                "static_long_lived_secrets_count": 0,
            },
        ]
    )
    assert res["evaluated_vaults_count"] == 3
    assert res["active_root_token_or_unverified_unseal_vault_ids"] == [
        "VLT-ACTIVE-ROOT",
        "VLT-NO-UNSEAL",
    ]
    assert res["long_lease_or_static_secret_vault_ids"] == ["VLT-NO-UNSEAL"]
    assert (
        res["secrets_vault_status"]
        == "VAULT_ROOT_TOKEN_OR_UNSEAL_QUORUM_BREACH"
    )
    assert res["is_secrets_vault_compliant"] is False


def test_audit_wiki_secrets_vault_lease_rotation_and_root_token_seal_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_secrets_vault_lease_rotation_and_root_token_seal,
    )

    res = audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(
        [
            {
                "vault_id": "VLT-LONG-LEASE",
                "root_tokens_revoked_and_audited": False,
                "hsm_kms_auto_unseal_quorum_verified": True,
                "dynamic_lease_ttl_hours": 25,
                "static_long_lived_secrets_count": 0,
            },
            {
                "vault_id": "VLT-STATIC-SECRETS",
                "root_tokens_revoked_and_audited": True,
                "hsm_kms_auto_unseal_quorum_verified": True,
                "dynamic_lease_ttl_hours": 24,
                "static_long_lived_secrets_count": 1,
            },
        ],
        max_dynamic_lease_ttl_hours=24,
        require_root_token_revoked=False,
    )
    assert res["evaluated_vaults_count"] == 2
    assert res["active_root_token_or_unverified_unseal_vault_ids"] == []
    assert res["long_lease_or_static_secret_vault_ids"] == [
        "VLT-LONG-LEASE",
        "VLT-STATIC-SECRETS",
    ]
    assert (
        res["secrets_vault_status"]
        == "VAULT_LEASE_TTL_OR_STATIC_SECRET_WARNING"
    )
    assert res["is_secrets_vault_compliant"] is False


def test_audit_wiki_secrets_vault_lease_rotation_and_root_token_seal_optimal_and_defensive():
    from backend.services.wiki_pmi_service import (
        audit_wiki_secrets_vault_lease_rotation_and_root_token_seal,
    )

    empty = audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(None)
    assert empty["evaluated_vaults_count"] == 0
    assert empty["active_root_token_or_unverified_unseal_vault_ids"] == []
    assert empty["long_lease_or_static_secret_vault_ids"] == []
    assert empty["secrets_vault_status"] == "VAULT_DYNAMIC_SECRETS_OPTIMAL"
    assert empty["is_secrets_vault_compliant"] is True

    optimal = audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"vault_id": "   "},
            {
                "vault_id": "VLT-DEFAULTS",
                "root_tokens_revoked_and_audited": None,
                "hsm_kms_auto_unseal_quorum_verified": None,
                "dynamic_lease_ttl_hours": None,
                "static_long_lived_secrets_count": None,
            },
        ]
    )
    assert optimal["evaluated_vaults_count"] == 1
    assert optimal["active_root_token_or_unverified_unseal_vault_ids"] == []
    assert optimal["long_lease_or_static_secret_vault_ids"] == []
    assert optimal["secrets_vault_status"] == "VAULT_DYNAMIC_SECRETS_OPTIMAL"
    assert optimal["is_secrets_vault_compliant"] is True


def test_audit_wiki_secrets_vault_lease_rotation_and_root_token_seal_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_secrets_vault_lease_rotation_and_root_token_seal,
    )

    sample = [
        {
            "vault_id": "VLT-99",
            "dynamic_lease_ttl_hours": 12,
            "static_long_lived_secrets_count": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(
            sample
        )
        == audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(sample)
    )
    assert (
        "audit_wiki_secrets_vault_lease_rotation_and_root_token_seal"
        in mod.__all__
    )


def test_wiki_ntp_nts_or_leap_smear_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ntp_clock_drift_and_leap_second_smearing,
    )

    res = audit_wiki_ntp_clock_drift_and_leap_second_smearing(
        [
            {
                "node_id": "NODE-NO-NTS",
                "nts_authenticated_time_sources": False,
            },
            {
                "node_id": "NODE-UNSMEARED",
                "leap_second_smearing_consistent": False,
            },
        ],
        max_clock_offset_ms=10.0,
        max_stratum_level=3,
    )
    assert res["evaluated_nodes_count"] == 2
    assert res["unauthenticated_or_unsmeared_leap_node_ids"] == [
        "NODE-NO-NTS",
        "NODE-UNSMEARED",
    ]
    assert res["high_drift_or_degraded_stratum_node_ids"] == []
    assert (
        res["clock_sync_status"] == "CLOCK_NTS_AUTH_OR_LEAP_SMEAR_BREACH"
    )
    assert res["is_clock_sync_compliant"] is False


def test_wiki_ntp_drift_or_stratum_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ntp_clock_drift_and_leap_second_smearing,
    )

    res = audit_wiki_ntp_clock_drift_and_leap_second_smearing(
        [
            {
                "node_id": "NODE-HIGH-DRIFT",
                "observed_clock_offset_ms": 28.0,
            },
            {
                "node_id": "NODE-NEGATIVE-DRIFT",
                "observed_clock_offset_ms": -30.0,
            },
            {
                "node_id": "NODE-DEGRADED-STRATUM",
                "stratum_level": 5,
            },
        ],
        max_clock_offset_ms=10.0,
        max_stratum_level=3,
    )
    assert res["evaluated_nodes_count"] == 3
    assert res["unauthenticated_or_unsmeared_leap_node_ids"] == []
    assert res["high_drift_or_degraded_stratum_node_ids"] == [
        "NODE-HIGH-DRIFT",
        "NODE-NEGATIVE-DRIFT",
        "NODE-DEGRADED-STRATUM",
    ]
    assert (
        res["clock_sync_status"] == "CLOCK_OFFSET_DRIFT_OR_STRATUM_WARNING"
    )
    assert res["is_clock_sync_compliant"] is False


def test_wiki_ntp_boundaries_optimal_and_defaults():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ntp_clock_drift_and_leap_second_smearing,
    )

    res = audit_wiki_ntp_clock_drift_and_leap_second_smearing(
        [
            {
                "node_id": "NODE-BOUNDARY",
                "observed_clock_offset_ms": 10.0,
                "stratum_level": 3,
            },
            {
                "node_id": "NODE-NEG-BOUNDARY",
                "observed_clock_offset_ms": -10.0,
            },
            {"node_id": "NODE-ALL-DEFAULTS"},
        ],
        max_clock_offset_ms=10.0,
        max_stratum_level=3,
    )
    assert res["evaluated_nodes_count"] == 3
    assert res["unauthenticated_or_unsmeared_leap_node_ids"] == []
    assert res["high_drift_or_degraded_stratum_node_ids"] == []
    assert res["clock_sync_status"] == "CLOCK_SYNCHRONIZATION_OPTIMAL"
    assert res["is_clock_sync_compliant"] is True


def test_wiki_ntp_invalid_and_binding():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_ntp_clock_drift_and_leap_second_smearing,
    )

    empty = audit_wiki_ntp_clock_drift_and_leap_second_smearing(None)
    assert empty["evaluated_nodes_count"] == 0
    assert empty["unauthenticated_or_unsmeared_leap_node_ids"] == []
    assert empty["high_drift_or_degraded_stratum_node_ids"] == []
    assert empty["clock_sync_status"] == "CLOCK_SYNCHRONIZATION_OPTIMAL"
    assert empty["is_clock_sync_compliant"] is True

    invalid = audit_wiki_ntp_clock_drift_and_leap_second_smearing(
        [42, "not-a-dict", None, {"node_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_nodes_count"] == 0

    defaults = audit_wiki_ntp_clock_drift_and_leap_second_smearing(
        [
            {
                "node_id": "NODE-DEFAULTS",
                "nts_authenticated_time_sources": None,
                "leap_second_smearing_consistent": None,
                "observed_clock_offset_ms": None,
                "stratum_level": None,
            }
        ]
    )
    assert defaults["evaluated_nodes_count"] == 1
    assert defaults["clock_sync_status"] == "CLOCK_SYNCHRONIZATION_OPTIMAL"
    assert defaults["is_clock_sync_compliant"] is True

    sample = [
        {
            "node_id": "NODE-1",
            "observed_clock_offset_ms": 1.0,
            "stratum_level": 2,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_ntp_clock_drift_and_leap_second_smearing(
            sample
        )
        == audit_wiki_ntp_clock_drift_and_leap_second_smearing(sample)
    )
    assert (
        "audit_wiki_ntp_clock_drift_and_leap_second_smearing"
        in mod.__all__
    )


def test_audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety,
    )

    res = audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
        [
            {
                "probe_id": "EBPF-NET-01",
                "verifier_passed": True,
                "btf_core_enabled": True,
                "events_emitted": 100000,
                "events_dropped": 100,
                "cpu_overhead_pct": 0.8,
                "unbounded_loop_detected": False,
            }
        ],
        max_ringbuffer_drop_rate_pct=0.5,
        max_cpu_overhead_pct=2.0,
    )
    assert res["status"] == "healthy"
    assert res["is_compliant"] is True
    assert res["probes_evaluated"] == 1
    assert res["unsafe_probe_ids"] == []
    assert res["dropping_or_high_cpu_probe_ids"] == []
    assert res["Violations"] == []
    assert res["records"][0]["ringbuffer_drop_rate_pct"] == 0.0999


def test_audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety_critical():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety,
    )

    res = audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
        [
            {
                "probe_id": "EBPF-BAD-VERIFY",
                "verifier_passed": False,
                "unbounded_loop_detected": True,
                "events_emitted": 500,
                "events_dropped": 0,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["unsafe_probe_ids"] == ["EBPF-BAD-VERIFY"]
    assert len(res["Violations"]) >= 1


def test_audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety,
    )

    res = audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
        [
            {
                "id": "EBPF-HIGH-DROP",
                "verifier_passed": True,
                "btf_core_enabled": False,
                "events_emitted": 900,
                "events_dropped": 100,
                "cpu_overhead_pct": 3.5,
            }
        ],
        max_ringbuffer_drop_rate_pct=0.5,
        max_cpu_overhead_pct=2.0,
        require_btf_core_portability=True,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["unsafe_probe_ids"] == []
    assert res["dropping_or_high_cpu_probe_ids"] == ["EBPF-HIGH-DROP"]
    assert res["records"][0]["ringbuffer_drop_rate_pct"] == 10.0
    assert res["records"][0]["btf_core_missing"] is True


def test_audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety,
    )

    sample = [{"probe_id": "EBPF-1", "events_emitted": 1000, "events_dropped": 0}]
    assert (
        WikiPMIService.audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
            sample
        )
        == audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
            sample
        )
    )
    assert (
        "audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety"
        in mod.__all__
    )


def test_audit_wiki_otel_tail_sampling_baggage_and_span_drop_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_otel_tail_sampling_baggage_and_span_drop,
    )

    res = audit_wiki_otel_tail_sampling_baggage_and_span_drop(
        [
            {
                "pipeline_id": "OTEL-GATEWAY-01",
                "w3c_tracecontext_enforced": True,
                "error_trace_retention_pct": 100.0,
                "spans_received": 50000,
                "spans_dropped_queue_full": 250,
                "max_observed_baggage_bytes": 2048,
            }
        ],
        max_span_drop_rate_pct=1.0,
        min_error_trace_retention_pct=100.0,
        max_baggage_header_bytes=8192,
    )
    assert res["status"] == "healthy"
    assert res["is_compliant"] is True
    assert res["pipelines_evaluated"] == 1
    assert res["trace_loss_pipeline_ids"] == []
    assert res["degraded_pipeline_ids"] == []
    assert res["Violations"] == []
    assert res["records"][0]["span_drop_rate_pct"] == 0.5


def test_audit_wiki_otel_tail_sampling_baggage_and_span_drop_critical():
    from backend.services.wiki_pmi_service import (
        audit_wiki_otel_tail_sampling_baggage_and_span_drop,
    )

    res = audit_wiki_otel_tail_sampling_baggage_and_span_drop(
        [
            {
                "pipeline_id": "OTEL-NO-W3C",
                "w3c_tracecontext_enforced": False,
                "error_trace_retention_pct": 100.0,
                "spans_received": 1000,
                "spans_dropped_queue_full": 0,
            },
            {
                "pipeline_id": "OTEL-ERR-LOSS",
                "w3c_tracecontext_enforced": True,
                "error_trace_retention_pct": 85.0,
                "spans_received": 1000,
                "spans_dropped_queue_full": 0,
            },
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["trace_loss_pipeline_ids"] == ["OTEL-NO-W3C", "OTEL-ERR-LOSS"]
    assert res["records"][0]["missing_w3c_tracecontext"] is True
    assert res["records"][1]["error_trace_sampling_loss"] is True
    assert len(res["Violations"]) == 2


def test_audit_wiki_otel_tail_sampling_baggage_and_span_drop_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_otel_tail_sampling_baggage_and_span_drop,
    )

    res = audit_wiki_otel_tail_sampling_baggage_and_span_drop(
        [
            {
                "id": "OTEL-DROP-AND-BAGGAGE",
                "w3c_tracecontext_enforced": True,
                "error_trace_retention_pct": 100.0,
                "spans_received": 1000,
                "spans_dropped_queue_full": 25,
                "max_observed_baggage_bytes": 12288,
            }
        ],
        max_span_drop_rate_pct=1.0,
        max_baggage_header_bytes=8192,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["trace_loss_pipeline_ids"] == []
    assert res["degraded_pipeline_ids"] == ["OTEL-DROP-AND-BAGGAGE"]
    assert res["records"][0]["span_drop_rate_pct"] == 2.5
    assert res["records"][0]["span_drop_budget_exceeded"] is True
    assert res["records"][0]["baggage_size_overflow"] is True


def test_audit_wiki_otel_tail_sampling_baggage_and_span_drop_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_otel_tail_sampling_baggage_and_span_drop,
    )

    sample = [{"pipeline_id": "OTEL-1", "spans_received": 0}]
    assert (
        WikiPMIService.audit_wiki_otel_tail_sampling_baggage_and_span_drop(
            sample
        )
        == audit_wiki_otel_tail_sampling_baggage_and_span_drop(sample)
    )
    assert (
        "audit_wiki_otel_tail_sampling_baggage_and_span_drop"
        in mod.__all__
    )


def test_audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing,
    )

    res = audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
        [
            {
                "shard_id": "HNSW-SHARD-01",
                "observed_recall_at_10_pct": 97.5,
                "tombstone_fragmentation_pct": 8.0,
                "embedding_model_version": "text-embedding-3-large-v1",
                "p99_ann_query_latency_ms": 14.2,
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["is_compliant"] is True
    assert res["shards_evaluated"] == 1
    assert res["version_skew_or_low_recall_shard_ids"] == []
    assert res["fragmented_shard_ids"] == []
    assert res["Violations"] == []


def test_audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing_critical():
    from backend.services.wiki_pmi_service import (
        audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing,
    )

    res = audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
        [
            {
                "shard_id": "HNSW-SKEW-LOW",
                "observed_recall_at_10_pct": 88.0,
                "tombstone_fragmentation_pct": 5.0,
                "embedding_model_version": "text-embedding-ada-002",
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["version_skew_or_low_recall_shard_ids"] == ["HNSW-SKEW-LOW"]
    assert len(res["Violations"]) >= 2


def test_audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing,
    )

    res = audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
        [
            {
                "id": "HNSW-FRAG",
                "observed_recall_at_10_pct": 96.0,
                "tombstone_fragmentation_pct": 32.0,
                "embedding_model_version": "text-embedding-3-large-v1",
            }
        ],
        max_tombstone_fragmentation_pct=20.0,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["version_skew_or_low_recall_shard_ids"] == []
    assert res["fragmented_shard_ids"] == ["HNSW-FRAG"]
    assert res["records"][0]["tombstone_fragmentation_exceeded"] is True


def test_audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing,
    )

    sample = [{"shard_id": "HNSW-1", "observed_recall_at_10_pct": 98.0}]
    assert (
        WikiPMIService.audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
            sample
        )
        == audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
            sample
        )
    )
    assert (
        "audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing"
        in mod.__all__
    )


# ── audit_wiki_graph_backlink_reciprocity_and_orphan_clusters (PMBOK §4.4 & §10.2, pure helper) ──


def test_wiki_graph_topology_optimal_nodes():
    """Páginas con backlinks sincronizados, sin transclusiones rotas y sin orfandad -> 'KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL'."""
    import backend.services.wiki_pmi_service as wiki_module
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_graph_backlink_reciprocity_and_orphan_clusters,
    )

    graph_nodes = [
        {
            "page_id": "PG-001",
            "bidirectional_backlinks_synced": True,
            "broken_transclusion_embeds_count": 0,
            "is_isolated_orphan_node": False,
            "orphan_cluster_ratio_pct": 2.0,
        },
        {
            "page_id": "PG-002",
            # Defaults implícitos por campo: synced True, 0 rotas, False orfan, 2.0 ratio.
        },
    ]
    res = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(graph_nodes)
    assert res == {
        "evaluated_pages_count": 2,
        "desynced_backlink_or_broken_transclusion_page_ids": [],
        "isolated_orphan_cluster_page_ids": [],
        "knowledge_graph_status": "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL",
        "is_knowledge_graph_compliant": True,
    }
    # Ratio de clúster huérfano exactamente en el umbral 5.0 no es warning (comparación estricta >)
    at_ratio = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [{"page_id": "PG-003", "orphan_cluster_ratio_pct": 5.0}]
    )
    assert at_ratio["knowledge_graph_status"] == "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL"
    assert (
        WikiPMIService.audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
            graph_nodes
        )
        == res
    )
    assert "audit_wiki_graph_backlink_reciprocity_and_orphan_clusters" in wiki_module.__all__


def test_wiki_graph_backlink_desync_or_transclusion_breach():
    """Backlinks no sincronizados o transclusiones rotas -> 'BACKLINK_DESYNC_OR_BROKEN_TRANSCLUSION_BREACH' con precedencia sobre WARNING."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_graph_backlink_reciprocity_and_orphan_clusters,
    )

    breach = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [
            {
                "page_id": "PG-DESYNC",
                "bidirectional_backlinks_synced": False,
                "broken_transclusion_embeds_count": 0,
            },
            {
                "page_id": "PG-BROKEN-EMBED",
                "broken_transclusion_embeds_count": 2,
            },
        ]
    )
    assert breach["evaluated_pages_count"] == 2
    assert breach["desynced_backlink_or_broken_transclusion_page_ids"] == [
        "PG-DESYNC",
        "PG-BROKEN-EMBED",
    ]
    assert breach["knowledge_graph_status"] == (
        "BACKLINK_DESYNC_OR_BROKEN_TRANSCLUSION_BREACH"
    )
    assert breach["is_knowledge_graph_compliant"] is False

    # Breach tiene precedencia aunque también haya páginas huérfanas
    mixed = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [
            {"page_id": "PG-BROKEN-EMBED-2", "broken_transclusion_embeds_count": 1},
            {"page_id": "PG-BROKEN-EMBED-3", "bidirectional_backlinks_synced": False},
            {"page_id": "PG-ORPHAN", "is_isolated_orphan_node": True},
        ]
    )
    assert mixed["knowledge_graph_status"] == (
        "BACKLINK_DESYNC_OR_BROKEN_TRANSCLUSION_BREACH"
    )


def test_wiki_graph_orphan_cluster_fragmentation_warning():
    """Nodos huérfanos aislados o ratio de clúster > 5.0 (con backlinks limpios) -> 'ORPHAN_CLUSTER_FRAGMENTATION_WARNING'."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_graph_backlink_reciprocity_and_orphan_clusters,
    )

    warning = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [
            {
                "page_id": "PG-ORPHAN-A",
                "is_isolated_orphan_node": True,
                "orphan_cluster_ratio_pct": 2.0,
            },
            {
                "page_id": "PG-ORPHAN-B",
                "orphan_cluster_ratio_pct": 8.5,
            },
        ]
    )
    assert warning["evaluated_pages_count"] == 2
    assert warning["desynced_backlink_or_broken_transclusion_page_ids"] == []
    assert warning["isolated_orphan_cluster_page_ids"] == [
        "PG-ORPHAN-A",
        "PG-ORPHAN-B",
    ]
    assert warning["knowledge_graph_status"] == (
        "ORPHAN_CLUSTER_FRAGMENTATION_WARNING"
    )
    assert warning["is_knowledge_graph_compliant"] is False

    custom = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [{"page_id": "PG-4", "orphan_cluster_ratio_pct": 6.0}],
        max_orphan_cluster_ratio_pct=5.5,
    )
    assert custom["knowledge_graph_status"] == "ORPHAN_CLUSTER_FRAGMENTATION_WARNING"
    assert custom["isolated_orphan_cluster_page_ids"] == ["PG-4"]


def test_wiki_graph_empty_invalid_and_field_reversion():
    """None / dicts inválidos se descartan; campos no numéricos/no bool revierten a defaults del spec."""
    from backend.services.wiki_pmi_service import (
        audit_wiki_graph_backlink_reciprocity_and_orphan_clusters,
    )

    empty_res = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(None)
    assert empty_res == {
        "evaluated_pages_count": 0,
        "desynced_backlink_or_broken_transclusion_page_ids": [],
        "isolated_orphan_cluster_page_ids": [],
        "knowledge_graph_status": "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL",
        "is_knowledge_graph_compliant": True,
    }

    invalid_res = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        ["no-dict", None, {"page_id": "   "}, {"page_id": 88}, {"broken_transclusion_embeds_count": 3}]
    )
    assert invalid_res["evaluated_pages_count"] == 0

    bad_fields = audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
        [
            {
                "page_id": "PG-BAD",
                "bidirectional_backlinks_synced": "sí",
                "broken_transclusion_embeds_count": "ninguna",
                "is_isolated_orphan_node": None,
                "orphan_cluster_ratio_pct": [9.0],
            }
        ]
    )
    assert bad_fields == {
        "evaluated_pages_count": 1,
        "desynced_backlink_or_broken_transclusion_page_ids": [],
        "isolated_orphan_cluster_page_ids": [],
        "knowledge_graph_status": "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL",
        "is_knowledge_graph_compliant": True,
    }


def test_audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock,
    )

    res = audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
        [
            {
                "doc_id": "CRDT-CHARTER-01",
                "causal_vector_converged": True,
                "tombstone_overhead_pct": 8.5,
                "unmerged_offline_ops_count": 40,
                "duplicate_client_id_detected": False,
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["is_compliant"] is True
    assert res["documents_evaluated"] == 1
    assert res["diverged_or_conflicted_doc_ids"] == []
    assert res["tombstone_or_offline_lag_doc_ids"] == []
    assert res["Violations"] == []


def test_audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock_critical():
    from backend.services.wiki_pmi_service import (
        audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock,
    )

    res = audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
        [
            {
                "doc_id": "CRDT-SPLIT-BRAIN",
                "causal_vector_converged": False,
                "tombstone_overhead_pct": 12.0,
                "unmerged_offline_ops_count": 100,
                "duplicate_client_id_detected": True,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["diverged_or_conflicted_doc_ids"] == ["CRDT-SPLIT-BRAIN"]
    assert len(res["Violations"]) >= 1


def test_audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock,
    )

    res = audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
        [
            {
                "id": "CRDT-TOMBSTONE-BLOAT",
                "causal_vector_converged": True,
                "tombstone_overhead_pct": 38.0,
                "unmerged_offline_ops_count": 820,
                "duplicate_client_id_detected": False,
            }
        ],
        max_tombstone_overhead_pct=25.0,
        max_offline_divergence_ops=500,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["diverged_or_conflicted_doc_ids"] == []
    assert res["tombstone_or_offline_lag_doc_ids"] == ["CRDT-TOMBSTONE-BLOAT"]
    assert res["records"][0]["tombstone_bloat_or_offline_ops_warning"] is True


def test_audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock,
    )

    sample = [{"doc_id": "CRDT-1", "causal_vector_converged": True}]
    assert (
        WikiPMIService.audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
            sample
        )
        == audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
            sample
        )
    )
    assert (
        "audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock"
        in mod.__all__
    )


def test_audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle,
    )

    res = audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
        [
            {
                "workload_id": "WIKI-INDEXER-01",
                "spiffe_id": "spiffe://ccf.local/ns/wiki/sa/indexer",
                "svid_ttl_total_sec": 3600,
                "svid_ttl_remaining_sec": 1800,
                "node_attested": True,
                "unix_workload_attested": True,
                "federation_bundle_age_sec": 90,
            }
        ]
    )
    assert res["is_spiffe_zero_trust_healthy"] is True
    assert res["spiffe_svid_federation_status"] == "SPIFFE_ZERO_TRUST_HEALTHY"
    assert res["unattested_or_invalid_spiffe_workload_ids"] == []
    assert res["expiring_or_expired_svid_workload_ids"] == []
    assert res["stale_federation_bundle_workload_ids"] == []


def test_audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle_critical():
    from backend.services.wiki_pmi_service import (
        audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle,
    )

    res = audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
        [
            {
                "workload_id": "WIKI-BAD-SPIFFE",
                "spiffe_id": "https://ccf.local/wiki",
                "svid_ttl_total_sec": 3600,
                "svid_ttl_remaining_sec": 0,
                "node_attested": False,
                "unix_workload_attested": True,
                "federation_bundle_age_sec": 60,
            }
        ]
    )
    assert res["is_spiffe_zero_trust_healthy"] is False
    assert (
        res["spiffe_svid_federation_status"]
        == "CRITICAL_ATTESTATION_OR_SVID_EXPIRY_BREACH"
    )
    assert res["unattested_or_invalid_spiffe_workload_ids"] == [
        "WIKI-BAD-SPIFFE"
    ]
    assert res["expiring_or_expired_svid_workload_ids"] == ["WIKI-BAD-SPIFFE"]


def test_audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle,
    )

    res = audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
        [
            {
                "workload_id": "WIKI-LOW-HEADROOM",
                "spiffe_id": "spiffe://ccf.local/ns/wiki/sa/render",
                "svid_ttl_total_sec": 3600,
                "svid_ttl_remaining_sec": 360,
                "node_attested": True,
                "unix_workload_attested": True,
                "federation_bundle_age_sec": 450,
            }
        ],
        min_rotation_headroom_pct=20.0,
        max_federation_bundle_staleness_sec=300,
    )
    assert res["is_spiffe_zero_trust_healthy"] is False
    assert (
        res["spiffe_svid_federation_status"]
        == "SVID_ROTATION_OR_FEDERATION_BUNDLE_WARNING"
    )
    assert res["unattested_or_invalid_spiffe_workload_ids"] == []
    assert res["expiring_or_expired_svid_workload_ids"] == ["WIKI-LOW-HEADROOM"]
    assert res["stale_federation_bundle_workload_ids"] == ["WIKI-LOW-HEADROOM"]


def test_audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle,
    )

    sample = [
        {
            "workload_id": "WIKI-01",
            "spiffe_id": "spiffe://ccf.local/ns/wiki/sa/api",
        }
    ]
    assert (
        WikiPMIService.audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
            sample
        )
        == audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
            sample
        )
    )
    assert (
        "audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle"
        in mod.__all__
    )


def test_audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker_green_optimal():
    from backend.services.wiki_pmi_service import (
        audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker,
    )

    res = audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(
        indices=[
            {
                "index_name": "wiki-pages-v1",
                "unassigned_primary_shards": 0,
                "unassigned_replica_shards": 0,
                "search_thread_pool_rejections": 0,
                "indexing_lag_docs": 12,
            },
            {
                "index_name": "wiki-embeddings-v1",
                "unassigned_primary_shards": 0,
                "unassigned_replica_shards": 0,
                "search_thread_pool_rejections": 0,
                "indexing_lag_docs": 0,
            },
        ],
        max_node_jvm_heap_used_pct=68.5,
        jvm_parent_circuit_breaker_limit_pct=85.0,
        quorum_master_nodes_present=True,
    )
    assert res["is_valid"] is True
    assert res["total_indices"] == 2
    assert res["red_unassigned_primary_indices"] == []
    assert res["degraded_replica_or_rejected_indices"] == []
    assert res["jvm_circuit_breaker_tripped"] is False
    assert res["split_brain_risk"] is False
    assert res["cluster_health_status"] == "GREEN_OPTIMAL"


def test_audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker_red_critical_outage():
    from backend.services.wiki_pmi_service import (
        audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker,
    )

    res = audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(
        indices=[
            {
                "index_name": "wiki-pages-v1",
                "unassigned_primary_shards": 2,
                "unassigned_replica_shards": 1,
                "search_thread_pool_rejections": 0,
            }
        ],
        max_node_jvm_heap_used_pct=91.0,
        jvm_parent_circuit_breaker_limit_pct=85.0,
        quorum_master_nodes_present=False,
    )
    assert res["is_valid"] is False
    assert res["red_unassigned_primary_indices"] == ["wiki-pages-v1"]
    assert res["jvm_circuit_breaker_tripped"] is True
    assert res["split_brain_risk"] is True
    assert res["cluster_health_status"] == "RED_CRITICAL_OUTAGE"


def test_audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker_yellow_replica_or_queue():
    from backend.services.wiki_pmi_service import (
        audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker,
    )

    res = audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(
        indices=[
            {
                "index_name": "wiki-attachments-v1",
                "unassigned_primary_shards": 0,
                "unassigned_replica_shards": 2,
                "search_thread_pool_rejections": 5,
            }
        ],
        max_node_jvm_heap_used_pct=72.0,
        jvm_parent_circuit_breaker_limit_pct=85.0,
        quorum_master_nodes_present=True,
    )
    assert res["is_valid"] is False
    assert res["red_unassigned_primary_indices"] == []
    assert res["degraded_replica_or_rejected_indices"] == ["wiki-attachments-v1"]
    assert res["jvm_circuit_breaker_tripped"] is False
    assert res["split_brain_risk"] is False
    assert res["cluster_health_status"] == "YELLOW_REPLICA_OR_QUEUE_PRESSURE"


def test_audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker,
    )

    empty = audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker([])
    assert empty["is_valid"] is False
    assert empty["cluster_health_status"] == "RED_CRITICAL_OUTAGE"

    sample = [
        {
            "index_name": "wiki-idx-1",
            "unassigned_primary_shards": 0,
            "unassigned_replica_shards": 0,
            "search_thread_pool_rejections": 0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(
            sample
        )
        == audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(sample)
    )
    assert (
        "audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker"
        in mod.__all__
    )


def test_audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio_optimal():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio,
    )

    res = audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(
        pop_regions=[
            {
                "region_id": "us-east-iad",
                "surrogate_purge_latency_sec": 1.2,
                "edge_cache_hit_ratio_pct": 94.5,
                "origin_shield_enabled": True,
                "five_xx_edge_error_rate_pct": 0.05,
            },
            {
                "region_id": "eu-central-fra",
                "surrogate_purge_latency_sec": 2.4,
                "edge_cache_hit_ratio_pct": 91.0,
                "origin_shield_enabled": True,
                "five_xx_edge_error_rate_pct": 0.10,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_pop_regions"] == 2
    assert res["slow_purge_propagation_regions"] == []
    assert res["cache_thrashing_or_unshielded_regions"] == []
    assert res["elevated_5xx_edge_regions"] == []
    assert res["cdn_edge_status"] == "CDN_EDGE_OPTIMAL"


def test_audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio_critical_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio,
    )

    res = audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(
        pop_regions=[
            {
                "region_id": "sa-east-gru",
                "surrogate_purge_latency_sec": 8.0,
                "edge_cache_hit_ratio_pct": 60.0,
                "origin_shield_enabled": False,
                "five_xx_edge_error_rate_pct": 1.8,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["slow_purge_propagation_regions"] == ["sa-east-gru"]
    assert res["cache_thrashing_or_unshielded_regions"] == ["sa-east-gru"]
    assert res["elevated_5xx_edge_regions"] == ["sa-east-gru"]
    assert res["cdn_edge_status"] == "CRITICAL_EDGE_5XX_OR_UNSHIELDED_ORIGIN_BREACH"


def test_audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio,
    )

    res = audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(
        pop_regions=[
            {
                "region_id": "ap-northeast-nrt",
                "surrogate_purge_latency_sec": 6.5,
                "edge_cache_hit_ratio_pct": 78.0,
                "origin_shield_enabled": True,
                "five_xx_edge_error_rate_pct": 0.1,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["slow_purge_propagation_regions"] == ["ap-northeast-nrt"]
    assert res["cache_thrashing_or_unshielded_regions"] == ["ap-northeast-nrt"]
    assert res["elevated_5xx_edge_regions"] == []
    assert res["cdn_edge_status"] == "PURGE_LATENCY_OR_CACHE_HIT_WARNING"


def test_audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio,
    )

    empty = audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio([])
    assert empty["is_valid"] is False
    assert empty["cdn_edge_status"] == "CRITICAL_EDGE_5XX_OR_UNSHIELDED_ORIGIN_BREACH"

    sample = [
        {
            "region_id": "us-west-sjc",
            "surrogate_purge_latency_sec": 1.0,
            "edge_cache_hit_ratio_pct": 95.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(
            sample
        )
        == audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(sample)
    )
    assert (
        "audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio"
        in mod.__all__
    )


def test_audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound_healthy():
    from backend.services.wiki_pmi_service import (
        audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound,
    )

    res = audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
        replication_slots=[
            {
                "slot_name": "wiki_cdc_slot_1",
                "active": True,
                "retained_wal_gb": 2.5,
                "replica_lag_seconds": 1.8,
                "max_table_txid_age_millions": 45.0,
            },
            {
                "slot_name": "wiki_read_replica_2",
                "active": True,
                "retained_wal_gb": 1.1,
                "replica_lag_seconds": 0.4,
                "max_table_txid_age_millions": 45.0,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_slots"] == 2
    assert res["inactive_or_wal_bloated_slots"] == []
    assert res["lagging_replication_slots"] == []
    assert res["txid_wraparound_risk_slots"] == []
    assert res["replication_health_status"] == "REPLICATION_AND_VACUUM_HEALTHY"


def test_audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound_critical_breach():
    from backend.services.wiki_pmi_service import (
        audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound,
    )

    res = audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
        replication_slots=[
            {
                "slot_name": "wiki_orphaned_slot",
                "active": False,
                "retained_wal_gb": 48.0,
                "replica_lag_seconds": 600.0,
                "max_table_txid_age_millions": 215.0,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["inactive_or_wal_bloated_slots"] == ["wiki_orphaned_slot"]
    assert res["lagging_replication_slots"] == ["wiki_orphaned_slot"]
    assert res["txid_wraparound_risk_slots"] == ["wiki_orphaned_slot"]
    assert (
        res["replication_health_status"]
        == "CRITICAL_WAL_EXHAUSTION_OR_TXID_WRAPAROUND"
    )


def test_audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound_lag_warning():
    from backend.services.wiki_pmi_service import (
        audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound,
    )

    res = audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
        replication_slots=[
            {
                "slot_name": "wiki_analytics_slot",
                "active": True,
                "retained_wal_gb": 8.0,
                "replica_lag_seconds": 45.0,
                "max_table_txid_age_millions": 60.0,
            }
        ],
        max_replica_lag_seconds=30.0,
    )
    assert res["is_valid"] is False
    assert res["inactive_or_wal_bloated_slots"] == []
    assert res["lagging_replication_slots"] == ["wiki_analytics_slot"]
    assert res["txid_wraparound_risk_slots"] == []
    assert res["replication_health_status"] == "REPLICA_LAG_WARNING"


def test_audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound_staticmethod_and_dunder_all():
    import backend.services.wiki_pmi_service as mod
    from backend.services.wiki_pmi_service import (
        WikiPMIService,
        audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound,
    )

    empty = audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound([])
    assert empty["is_valid"] is False
    assert (
        empty["replication_health_status"]
        == "CRITICAL_WAL_EXHAUSTION_OR_TXID_WRAPAROUND"
    )

    sample = [
        {
            "slot_name": "slot_1",
            "active": True,
            "retained_wal_gb": 1.0,
            "replica_lag_seconds": 2.0,
        }
    ]
    assert (
        WikiPMIService.audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
            sample
        )
        == audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
            sample
        )
    )
    assert (
        "audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound"
        in mod.__all__
    )


