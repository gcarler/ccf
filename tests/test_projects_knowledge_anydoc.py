"""Pruebas unitarias para la Fase 5: Integración del Banco de Conocimiento PMI y Motor AnyDoc.

Cubre:
1. Servicio de conversión documental AnyDoc (anydoc_service.py).
2. Compendio canónico de 7 volúmenes de doctrina PMI (wiki_pmi_service.py).
3. Indexador de doctrina PMI y enriquecimiento de proyectos con EVM en AgentKnowledgeBase (knowledge_base.py).
4. Endpoints de conversión documental y compendio en API Projects (api/projects.py).
5. Endpoints de doctrina canónica en API Wiki (api/wiki.py).
"""

from __future__ import annotations

import base64
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.datastructures import Headers

from backend import models, schemas
from backend.services.anydoc_service import (
    AnyDocConversionError,
    convert_bytes_to_markdown,
    detect_document_format,
    is_anydoc_available,
)
from backend.services.knowledge_base import KnowledgeIndexer
from backend.services.wiki_pmi_service import (
    CANONICAL_VOLUMES_METADATA,
    get_canonical_pmi_volumes,
    load_volume_markdown_content,
    seed_pmi_wiki_doctrine,
)

# ────────────────────────────────────────────────────────────
# 1. PRUEBAS DEL SERVICIO ANYDOC
# ────────────────────────────────────────────────────────────


def test_anydoc_engine_availability():
    """Verifica que el motor AnyDoc se encuentre disponible en el entorno."""
    assert is_anydoc_available() is True


def test_detect_document_format_variants():
    """Verifica la detección de formatos mediante extensión, pista o alias."""
    assert detect_document_format(filename="reporte.csv") == "csv"
    assert detect_document_format(filename="analisis.xlsx") == "xlsx"
    assert detect_document_format(filename="datos.xls") == "xlsx"
    assert detect_document_format(filename="propuesta.docx") == "docx"
    assert detect_document_format(filename="documento.docm") == "docx"
    assert detect_document_format(filename="presentacion.pptx") == "pptx"
    assert detect_document_format(filename="guia.pdf") == "pdf"
    assert detect_document_format(filename="notas.md") == "md"
    assert detect_document_format(filename="archivo.txt") == "txt"
    assert detect_document_format(format_hint="csv") == "csv"
    assert detect_document_format(format_hint=".docx") == "docx"
    assert detect_document_format(filename="desconocido.xyz") == "unknown"


def test_convert_csv_to_markdown_table():
    """Valida la conversión de CSV a tablas GitHub-Flavored Markdown con AnyDoc."""
    csv_bytes = b"Fase,Presupuesto,Responsable\nIniciacion,25000,Pastor General\nPlanificacion,45000,Director Proyectos\n"
    res = convert_bytes_to_markdown(data=csv_bytes, filename="presupuesto.csv")

    assert res["success"] is True
    assert res["format"] == "csv"
    assert res["filename"] == "presupuesto.csv"
    assert res["engine"] == "anydoc_v0.2.4"
    assert "| Fase | Presupuesto | Responsable |" in res["markdown"]
    assert "| Iniciacion | 25000 | Pastor General |" in res["markdown"]
    assert res["word_count"] > 0
    assert res["char_count"] > 0
    assert res["processing_time_ms"] >= 0


def test_convert_markdown_and_plain_text():
    """Valida el procesamiento directo de archivos Markdown y texto plano."""
    md_content = b"# Plan de Implementacion PMI\n\n- Entregable 1: EDT Completa\n- Entregable 2: Curva S"
    res = convert_bytes_to_markdown(data=md_content, filename="plan.md")

    assert res["success"] is True
    assert res["format"] == "md"
    assert res["engine"] == "native_text"
    assert "# Plan de Implementacion PMI" in res["markdown"]
    assert res["char_count"] == len(md_content.decode("utf-8"))


def test_convert_empty_bytes():
    """Valida que bytes vacíos retornen resultado exitoso con markdown vacío."""
    res = convert_bytes_to_markdown(data=b"", filename="vacio.docx")
    assert res["success"] is True
    assert res["markdown"] == ""
    assert res["char_count"] == 0
    assert res["word_count"] == 0


def test_convert_unsupported_format_raises_error():
    """Verifica que formatos binarios arbitrarios no soportados eleven AnyDocConversionError."""
    fake_binary = b"\x00\x01\x02\x03\x04\x05"
    with pytest.raises(AnyDocConversionError) as exc_info:
        convert_bytes_to_markdown(data=fake_binary, filename="binario.desconocido", format_hint="xyz_unsupported")
    assert exc_info.value.code in ("UNSUPPORTED_FORMAT", "CONVERT_ERROR", "MALFORMED_DOCUMENT")


# ────────────────────────────────────────────────────────────
# 2. PRUEBAS DEL COMPENDIO CANÓNICO PMI (7 VOLÚMENES)
# ────────────────────────────────────────────────────────────


def test_canonical_pmi_volumes_loading():
    """Valida que los 7 volúmenes canónicos del compendio PMI se carguen con contenido íntegro."""
    assert len(CANONICAL_VOLUMES_METADATA) == 7

    volumes = get_canonical_pmi_volumes()
    assert len(volumes) == 7

    # Verificar mapeo de volúmenes 0 al 6
    vol_indices = [v["vol"] for v in volumes]
    assert vol_indices == [0, 1, 2, 3, 4, 5, 6]

    # Verificar Volumen 0: Compendio Maestro
    vol0 = volumes[0]
    assert vol0["page_key"] == "wiki_pmi_00_indice_maestro"
    assert "Compendio Maestro" in vol0["title"]
    assert vol0["char_count"] > 1000
    assert "Project Management Institute" in vol0["content"]

    # Verificar Volumen 3: EDT / WBS
    vol3 = volumes[3]
    assert vol3["page_key"] == "wiki_pmi_03_edt_wbs"
    assert "Regla del 100%" in vol3["summary"]
    assert "wbs" in vol3["tags"] or "edt" in vol3["tags"]
    assert vol3["char_count"] > 1000

    # Verificar Volumen 4: EVM
    vol4 = volumes[4]
    assert vol4["page_key"] == "wiki_pmi_04_metricas_evm"
    assert "BAC" in vol4["summary"]
    assert "CPI" in vol4["summary"]
    assert "SPI" in vol4["summary"]
    assert vol4["char_count"] > 1000

    # Verificar Volumen 5: Matriz 4 Cuadrantes
    vol5 = volumes[5]
    assert vol5["page_key"] == "wiki_pmi_05_matriz_cuadrantes"
    assert "Regla 15%" in vol5["summary"] or "4 Cuadrantes" in vol5["summary"]


def test_load_volume_markdown_content_fallback():
    """Valida el texto de contingencia cuando un archivo no existe físicamente."""
    content = load_volume_markdown_content("archivo_inexistente.md")
    assert "Biblioteca Metodológica" in content


def test_seed_pmi_wiki_doctrine():
    """Valida la siembra de los 7 volúmenes en la tabla wiki_pages."""
    db = MagicMock()
    db.query().filter().first.return_value = None  # Simula páginas nuevas

    sede_id = uuid.uuid4()
    author_id = uuid.uuid4()

    seeded = seed_pmi_wiki_doctrine(db, sede_id=sede_id, author_id=author_id, force_update=False)

    assert len(seeded) == 7
    assert db.add.call_count == 7
    assert db.commit.call_count == 1

    for page in seeded:
        assert page.category == "proyectos_pmi"
        assert page.sede_id == sede_id
        assert page.author_id == author_id
        assert page.version == 1
        assert page.page_key.startswith("wiki_pmi_")


# ────────────────────────────────────────────────────────────
# 3. PRUEBAS DEL INDEXADOR DE KNOWLEDGE BASE (EVM & PMI)
# ────────────────────────────────────────────────────────────


def test_knowledge_indexer_pmi_doctrine():
    """Valida la indexación de la doctrina PMI en AgentKnowledgeBase."""
    db = MagicMock()
    indexer = KnowledgeIndexer(db)

    with patch.object(indexer, "_upsert_kb") as mock_upsert:
        count = indexer._index_pmi_doctrine(agent_id=None)
        assert count == 7
        assert mock_upsert.call_count == 7
        first_call = mock_upsert.call_args_list[0][1]
        assert first_call["category"] == "pmi_doctrine"
        assert first_call["source_module"] == "projects"
        assert first_call["relevance_score"] == 1.0


def test_knowledge_indexer_projects_evm_enrichment():
    """Valida que los proyectos indexados en KB contengan métricas EVM y cuadrantes de salud."""
    db = MagicMock()

    proj_id = uuid.uuid4()
    mock_project = MagicMock(spec=models.Project)
    mock_project.id = proj_id
    mock_project.title = "Catedral Sede Norte"
    mock_project.description = "Construcción y adecuación integral"
    mock_project.status = "active"
    mock_project.owner_id = uuid.uuid4()
    mock_project.sede_id = uuid.uuid4()

    db.query().filter().all.return_value = [mock_project]

    indexer = KnowledgeIndexer(db)

    # Simular cálculo de EVM en el servicio
    mock_evm = MagicMock()
    mock_evm.bac = 100000.0
    mock_evm.pv = 50000.0
    mock_evm.ev = 55000.0
    mock_evm.ac = 48000.0
    mock_evm.cv = 7000.0
    mock_evm.sv = 5000.0
    mock_evm.cpi = 1.15
    mock_evm.spi = 1.10
    mock_evm.progreso_real_pct = 55.0
    mock_evm.progreso_planificado_pct = 50.0

    mock_quad = MagicMock()
    mock_quad.name = "Zona Óptima"
    mock_quad.status.value = "optimal"
    mock_quad.description = "Bajo presupuesto y adelantado en cronograma."

    with (
        patch("backend.services.project_evm_service.calculate_project_evm", return_value=mock_evm),
        patch("backend.services.project_evm_service.calculate_cpi_spi_quadrant", return_value=mock_quad),
        patch.object(indexer, "_upsert_kb") as mock_upsert,
    ):
        count = indexer._index_projects(agent_id=None)
        assert count == 1
        assert mock_upsert.call_count == 1

        call_kwargs = mock_upsert.call_args[1]
        assert call_kwargs["title"] == "Proyecto: Catedral Sede Norte"
        assert "Salud EVM" in call_kwargs["content"]
        assert "1.15" in call_kwargs["content"]
        assert "1.10" in call_kwargs["content"]
        assert "Zona Óptima" in call_kwargs["content"]
        assert "CPI: 1.15" in call_kwargs["summary"]
        assert "Zona Óptima" in call_kwargs["summary"]


def test_rebuild_all_includes_pmi_doctrine():
    """Valida que KnowledgeIndexer.rebuild_all() incluya 'pmi_doctrine' en su diccionario de resultados."""
    db = MagicMock()
    indexer = KnowledgeIndexer(db)

    with (
        patch.object(indexer, "_index_courses", return_value=3),
        patch.object(indexer, "_index_evangelism", return_value=2),
        patch.object(indexer, "_index_projects", return_value=5),
        patch.object(indexer, "_index_pmi_doctrine", return_value=7),
        patch.object(indexer, "_index_persona_stats", return_value=1),
        patch.object(indexer, "_index_system_vars", return_value=4),
    ):
        stats = indexer.rebuild_all()
        assert stats["pmi_doctrine"] == 7
        assert stats["projects"] == 5


# ────────────────────────────────────────────────────────────
# 4. PRUEBAS DE ENDPOINTS DE LA API (PROJECTS & WIKI)
# ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_api_convert_document_json_payload():
    """Valida el endpoint POST /convert-document con payload JSON base64."""
    from backend.api.projects import convert_document_endpoint

    csv_data = b"Codigo,Tarea,Avance\nT-1,Diseno,100\nT-2,Desarrollo,50\n"
    b64 = base64.b64encode(csv_data).decode("utf-8")

    request = MagicMock()
    request.headers = Headers({"content-type": "application/json"})

    async def mock_json():
        return {
            "filename": "tareas.csv",
            "content_base64": b64,
            "format_hint": "csv",
        }

    request.json = mock_json

    user = MagicMock(spec=models.User)

    res = await convert_document_endpoint(
        request=request,
        file=None,
        format_hint=None,
        ocr="reject",
        current_user=user,
    )

    assert isinstance(res, schemas.DocumentConversionResponse)
    assert res.success is True
    assert res.format == "csv"
    assert "| Codigo | Tarea | Avance |" in res.markdown


@pytest.mark.anyio
async def test_api_convert_document_empty_raises_400():
    """Valida que POST /convert-document eleve 400 si no se envían datos."""
    from backend.api.projects import convert_document_endpoint

    request = MagicMock()
    request.headers = Headers({"content-type": "application/json"})

    async def mock_json():
        return {}

    request.json = mock_json

    user = MagicMock(spec=models.User)

    with pytest.raises(HTTPException) as exc_info:
        await convert_document_endpoint(
            request=request,
            file=None,
            format_hint=None,
            ocr="reject",
            current_user=user,
        )
    assert exc_info.value.status_code == 400


def test_api_pmi_doctrine_compendium():
    """Valida el endpoint GET /pmi-doctrine."""
    from backend.api.projects import get_pmi_doctrine_compendium

    db = MagicMock()
    db.query().filter().count.return_value = 7
    user = MagicMock(spec=models.User)

    with patch("backend.api.projects.get_user_sede_id", return_value=uuid.uuid4()):
        res = get_pmi_doctrine_compendium(
            include_content=True,
            db=db,
            current_user=user,
        )

        assert isinstance(res, schemas.PMIDoctrineIndexResponse)
        assert res.total_volumes == 7
        assert len(res.volumes) == 7
        assert res.volumes[0].vol == 0
        assert res.volumes[0].content is not None


@pytest.mark.anyio
async def test_api_convert_and_publish_project_wiki():
    """Valida el endpoint POST /{project_id}/documents/convert-and-publish a la Wiki del Proyecto."""
    from backend.api.projects import convert_and_publish_document

    project_uuid = uuid.uuid4()
    project_id_str = str(project_uuid)
    sede_uuid = uuid.uuid4()

    db = MagicMock()
    db_project = MagicMock(spec=models.Project)
    db_project.id = project_uuid
    db_project.title = "Construcción Templo"
    db_project.sede_id = sede_uuid

    request = MagicMock()
    request.headers = Headers({"content-type": "application/json"})

    csv_data = b"Entregable,Responsable\nEDT,Ingeniero\nCurva S,Analista\n"
    b64 = base64.b64encode(csv_data).decode("utf-8")

    async def mock_json():
        return {
            "filename": "entregables.csv",
            "content_base64": b64,
            "target_type": "project_wiki",
            "title": "Entregables del Proyecto",
        }

    request.json = mock_json
    user = MagicMock(spec=models.User)
    user.id = uuid.uuid4()

    with (
        patch("backend.api.projects.get_user_sede_id", return_value=sede_uuid),
        patch("backend.api.projects._ensure_project", return_value=db_project),
        patch("backend.api.projects.get_user_persona_id", return_value=uuid.uuid4()),
        patch("backend.crud.get_project_wiki", return_value=None),
        patch("backend.api.projects._log_project_activity"),
    ):
        res = await convert_and_publish_document(
            project_id=project_id_str,
            request=request,
            file=None,
            target_type="project_wiki",
            title=None,
            category="proyectos",
            db=db,
            current_user=user,
        )

        assert isinstance(res, schemas.ConvertAndPublishWikiResponse)
        assert res.published_to == "project_wiki"
        assert res.title == "Entregables del Proyecto"
        assert res.conversion.format == "csv"
        assert "| Entregable | Responsable |" in res.conversion.markdown
        assert db.add.called
        assert db.commit.called


# ────────────────────────────────────────────────────────────
# 6. AUDITOR DE DENSIDAD ESTRUCTURAL DEL MARKDOWN
# ────────────────────────────────────────────────────────────


def test_audit_converted_markdown_structure_structured_document():
    """Encabezados ATX, filas de tabla y viñetas → 'structured' con conteos exactos."""
    from backend.services.anydoc_service import audit_converted_markdown_structure

    conversion = {
        "markdown": (
            "# Plan EVM\n"
            "## Batería de Indicadores\n"
            "#### Detalle CPI\n"
            "\n"
            "| Fase | Presupuesto |\n"
            "| Iniciacion | 25000 |\n"
            "\n"
            "- Entregable EDT\n"
            "* Curva S\n"
            "  - Viñeta con indentación\n"
        )
    }

    audit = audit_converted_markdown_structure(conversion)

    assert audit == {
        "is_non_empty": True,
        "heading_count": 3,
        "table_row_count": 2,
        "bullet_item_count": 3,
        "structural_density_status": "structured",
    }


def test_audit_converted_markdown_structure_with_csv_table_conversion():
    """Integración: una tabla CSV convertida por convert_bytes_to_markdown es 'structured'."""
    from backend.services.anydoc_service import audit_converted_markdown_structure

    csv_bytes = b"Fase,Presupuesto,Responsable\nIniciacion,25000,Pastor General\nPlanificacion,45000,Director\n"
    conversion = convert_bytes_to_markdown(data=csv_bytes, filename="presupuesto.csv")

    # Prechequeo del contrato de conversión ya cubierto arriba
    assert conversion["success"] is True

    audit = audit_converted_markdown_structure(conversion)

    assert audit["is_non_empty"] is True
    # Header + separador GFM (|---|---|---|) + 2 filas de datos = 4 líneas con tuberías
    assert audit["table_row_count"] == 4
    assert audit["heading_count"] == 0
    assert audit["bullet_item_count"] == 0
    assert audit["structural_density_status"] == "structured"


def test_audit_converted_markdown_structure_plain_prose():
    """Texto corrido sin encabezados/tablas/viñetas → 'plain_prose'."""
    from backend.services.anydoc_service import audit_converted_markdown_structure

    conversion = {
        "markdown": (
            "El proyecto avanza según lo planificado.\n"
            "La próxima hito revisa la curva S.\n"
            "No hay desviaciones relevantes.\n"
        )
    }

    audit = audit_converted_markdown_structure(conversion)

    assert audit == {
        "is_non_empty": True,
        "heading_count": 0,
        "table_row_count": 0,
        "bullet_item_count": 0,
        "structural_density_status": "plain_prose",
    }


def test_audit_converted_markdown_structure_empty_and_none():
    """None, {} y markdown vacío/whitespace → 'empty' sin estructuras."""
    from backend.services.anydoc_service import audit_converted_markdown_structure

    for result in (None, {}, {"markdown": ""}, {"markdown": "   \n  "}):
        audit = audit_converted_markdown_structure(result)
        assert audit == {
            "is_non_empty": False,
            "heading_count": 0,
            "table_row_count": 0,
            "bullet_item_count": 0,
            "structural_density_status": "empty",
        }


def test_audit_rejects_inline_hashtag_as_heading():
    """'#tag' sin espacio ni doble numeral no es un encabezado ATX."""
    from backend.services.anydoc_service import audit_converted_markdown_structure

    audit = audit_converted_markdown_structure({"markdown": "#tag de proyecto\nMás texto corrido.\n"})

    assert audit["is_non_empty"] is True
    assert audit["heading_count"] == 0
    assert audit["structural_density_status"] == "plain_prose"


def test_estimate_document_reading_metrics_empty_or_none():
    """Entrada vacía o None retorna word_count=0, 'empty' y estimated_reading_minutes=0.0."""
    from backend.services.anydoc_service import estimate_document_reading_metrics

    for empty_val in (None, "", "   \n  ", {}, {"markdown": ""}):
        res = estimate_document_reading_metrics(empty_val)
        assert res["word_count"] == 0
        assert res["estimated_reading_minutes"] == 0.0
        assert res["artifact_depth_tier"] == "empty"
        assert res["words_per_minute"] == 200


def test_estimate_document_reading_metrics_brief_note():
    """Nota breve (< 150 palabras) soporta tanto str como dict de convert_bytes_to_markdown."""
    from backend.services.anydoc_service import (
        convert_bytes_to_markdown,
        estimate_document_reading_metrics,
    )

    text_note = " ".join(["entregable"] * 50)
    res_str = estimate_document_reading_metrics(text_note, words_per_minute=200)
    assert res_str == {
        "word_count": 50,
        "char_count": len(text_note),
        "words_per_minute": 200,
        "estimated_reading_minutes": 0.25,
        "artifact_depth_tier": "brief_note",
    }

    conv_result = convert_bytes_to_markdown(b"# Acta Breve\n\nReunion de seguimiento PMI con 10 palabras clave.", "acta.md")
    res_dict = estimate_document_reading_metrics(conv_result)
    assert 1 <= res_dict["word_count"] < 150
    assert res_dict["artifact_depth_tier"] == "brief_note"
    assert res_dict["estimated_reading_minutes"] > 0.0


def test_estimate_document_reading_metrics_standard_artifact():
    """Artefacto estándar (150..999 palabras) clasifica como 'standard_artifact'."""
    from backend.services.anydoc_service import estimate_document_reading_metrics

    standard_text = " ".join(["alcance"] * 300)
    res = estimate_document_reading_metrics(standard_text, words_per_minute=200)
    assert res == {
        "word_count": 300,
        "char_count": len(standard_text),
        "words_per_minute": 200,
        "estimated_reading_minutes": 1.5,
        "artifact_depth_tier": "standard_artifact",
    }


def test_estimate_document_reading_metrics_comprehensive_manual_and_wpm_floor():
    """Manual comprehensivo (>= 1000 palabras) y piso de seguridad wpm >= 50."""
    from backend.services.anydoc_service import estimate_document_reading_metrics

    manual_text = " ".join(["gobernanza"] * 1200)
    res = estimate_document_reading_metrics({"markdown": manual_text}, words_per_minute=10)
    assert res == {
        "word_count": 1200,
        "char_count": len(manual_text),
        "words_per_minute": 50,
        "estimated_reading_minutes": 24.0,
        "artifact_depth_tier": "comprehensive_manual",
    }


def test_extract_markdown_governance_markers_pending_actions():
    """Mezcla de acciones abiertas/cerradas, DECISIÓN: y [RIESGO] -> 'pending_actions'."""
    from backend.services.anydoc_service import extract_markdown_governance_markers

    md = (
        "# Acta de Comité\n"
        "- [x] Validar presupuesto inicial\n"
        "- [ ] Firmar acta de constitución\n"
        "* [ ] Notificar a interesados\n"
        "DECISIÓN: Se aprueba reserva de contingencia del 10%\n"
        "[RIESGO] Posible retraso en proveedor externo\n"
    )
    res = extract_markdown_governance_markers(md)
    assert res == {
        "open_action_items_count": 2,
        "completed_action_items_count": 1,
        "total_action_items": 3,
        "action_completion_pct": 33.33,
        "decision_markers_count": 1,
        "risk_markers_count": 1,
        "governance_traceability_status": "pending_actions",
    }


def test_extract_markdown_governance_markers_actions_closed():
    """Todos los ítems de acción completados (- [x] y * [X]) -> 'actions_closed' y 100.0%."""
    from backend.services.anydoc_service import extract_markdown_governance_markers

    md = (
        "- [x] Entregar plan de gestión\n"
        "* [X] Publicar matriz RACI\n"
    )
    res = extract_markdown_governance_markers(md)
    assert res == {
        "open_action_items_count": 0,
        "completed_action_items_count": 2,
        "total_action_items": 2,
        "action_completion_pct": 100.0,
        "decision_markers_count": 0,
        "risk_markers_count": 0,
        "governance_traceability_status": "actions_closed",
    }


def test_extract_markdown_governance_markers_decisions_only_dict_input():
    """Entrada dict con ACUERDO: y BLOQUEO: sin checkboxes -> 'decisions_recorded'."""
    from backend.services.anydoc_service import extract_markdown_governance_markers

    res = extract_markdown_governance_markers(
        {"markdown": "ACUERDO: Aprobar línea base\nBLOQUEO: Falta firma"}
    )
    assert res == {
        "open_action_items_count": 0,
        "completed_action_items_count": 0,
        "total_action_items": 0,
        "action_completion_pct": 0.0,
        "decision_markers_count": 1,
        "risk_markers_count": 1,
        "governance_traceability_status": "decisions_recorded",
    }


def test_extract_markdown_governance_markers_empty_or_no_markers():
    """Texto sin marcadores o None -> 'no_markers' y 0.0%."""
    from backend.services.anydoc_service import extract_markdown_governance_markers

    for val in (None, "", "Texto informativo sin acciones ni acuerdos.", {}):
        res = extract_markdown_governance_markers(val)
        assert res == {
            "open_action_items_count": 0,
            "completed_action_items_count": 0,
            "total_action_items": 0,
            "action_completion_pct": 0.0,
            "decision_markers_count": 0,
            "risk_markers_count": 0,
            "governance_traceability_status": "no_markers",
        }


# ── summarize_markdown_tables_schema (PMBOK §4.4, pure helper) ───────────


def test_tables_schema_single_table_with_data_rows():
    """Una tabla con filas de datos → 'single_table_summary' con conteos exactos."""
    from backend.services.anydoc_service import summarize_markdown_tables_schema

    markdown = (
        "| Fase | Presupuesto | Responsable |\n"
        "|---|---|---|\n"
        "| Iniciacion | 25000 | Pastor General |\n"
        "| Planificacion | 45000 | Director |\n"
        "| Ejecucion | 30000 | Coordinador |\n"
    )
    result = summarize_markdown_tables_schema(markdown)

    assert result == {
        "tables_count": 1,
        "total_data_rows": 3,
        "max_columns_count": 3,
        "distinct_column_headers": ["fase", "presupuesto", "responsable"],
        "tabular_richness_status": "single_table_summary",
    }


def test_tables_schema_multi_table_dedup_headers():
    """Dos tablas con cabeceras solapadas → 'multi_table_dataset' y dedup en minúsculas."""
    from backend.services.anydoc_service import summarize_markdown_tables_schema

    markdown = (
        "| Fase | Presupuesto |\n"
        "| --- | --- |\n"
        "| Iniciacion | 100 |\n"
        "| Cierre | 200 |\n"
        "\n"
        "Texto intermedio.\n"
        "\n"
        "| FASE | Responsable |\n"
        "|-|-|\n"
        "| Cierre | Auditor |\n"
    )
    result = summarize_markdown_tables_schema(markdown)

    assert result == {
        "tables_count": 2,
        "total_data_rows": 3,
        "max_columns_count": 2,
        "distinct_column_headers": ["fase", "presupuesto", "responsable"],
        "tabular_richness_status": "multi_table_dataset",
    }


def test_tables_schema_headers_only_no_data_rows():
    """Tablas solo con cabecera + separador sin filas → 'empty_headers_only'."""
    from backend.services.anydoc_service import summarize_markdown_tables_schema

    markdown = (
        "| Riesgo | Impacto |\n"
        "| --- | --- |\n"
        "Prose sin tablas adjuntas.\n"
        "| KPI | Meta |\n"
        "| :-: | --- |\n"
    )
    result = summarize_markdown_tables_schema(markdown)

    assert result["tables_count"] == 2
    assert result["total_data_rows"] == 0
    assert result["tabular_richness_status"] == "empty_headers_only"
    assert result["distinct_column_headers"] == ["impacto", "kpi", "meta", "riesgo"]


def test_tables_schema_no_tables_and_none():
    """Texto sin tablas, None, dict vacío y inválido → 'no_tables' en todo cero."""
    from backend.services.anydoc_service import summarize_markdown_tables_schema

    prose = "Solo texto corrido\nsin ninguna tabla.\n| incompleta\n"
    for source in (None, {}, "nope", prose):
        result = summarize_markdown_tables_schema(source)
        assert result == {
            "tables_count": 0,
            "total_data_rows": 0,
            "max_columns_count": 0,
            "distinct_column_headers": [],
            "tabular_richness_status": "no_tables",
        }


# ── summarize_markdown_code_blocks (PMBOK §4.4, pure helper) ──────────────


def test_summarize_markdown_code_blocks_well_typed_snippets():
    """Bloques con python y sql cerrados -> 'well_typed_snippets' con lenguajes ordenados."""
    from backend.services.anydoc_service import summarize_markdown_code_blocks

    md = (
        "# Especificación Técnica\n\n"
        "```python\n"
        "def calc_evm(bac, pct):\n"
        "    return bac * pct\n"
        "```\n\n"
        "```SQL\n"
        "SELECT id, title FROM projects;\n"
        "```\n"
    )
    res = summarize_markdown_code_blocks(md)
    assert res == {
        "code_blocks_count": 2,
        "total_code_lines": 3,
        "languages": ["python", "sql"],
        "untagged_blocks_count": 0,
        "unclosed_fences_count": 0,
        "technical_spec_status": "well_typed_snippets",
    }


def test_summarize_markdown_code_blocks_mixed_untagged_snippets():
    """1 bloque con json y 1 bloque sin etiqueta -> 'mixed_untagged_snippets'."""
    from backend.services.anydoc_service import summarize_markdown_code_blocks

    md = (
        "```json\n"
        '{"status": "ok"}\n'
        "```\n\n"
        "```\n"
        "raw log line 1\n"
        "raw log line 2\n"
        "```\n"
    )
    res = summarize_markdown_code_blocks({"markdown": md})
    assert res == {
        "code_blocks_count": 2,
        "total_code_lines": 3,
        "languages": ["json"],
        "untagged_blocks_count": 1,
        "unclosed_fences_count": 0,
        "technical_spec_status": "mixed_untagged_snippets",
    }


def test_summarize_markdown_code_blocks_malformed_unclosed_fence():
    """Bloque abierto sin cerrar al final -> 'malformed_unclosed_fence' con unclosed_fences_count == 1."""
    from backend.services.anydoc_service import summarize_markdown_code_blocks

    md = (
        "```python\n"
        "x = 1\n"
        "```\n"
        "```bash\n"
        "echo 'unclosed'\n"
    )
    res = summarize_markdown_code_blocks(md)
    assert res["code_blocks_count"] == 1
    assert res["unclosed_fences_count"] == 1
    assert res["technical_spec_status"] == "malformed_unclosed_fence"


def test_summarize_markdown_code_blocks_prose_only_or_none():
    """Texto sin bloques o None -> 'prose_only' con code_blocks_count == 0."""
    from backend.services.anydoc_service import summarize_markdown_code_blocks

    for val in (None, "", "Texto de gobernanza sin código.", {}):
        res = summarize_markdown_code_blocks(val)
        assert res == {
            "code_blocks_count": 0,
            "total_code_lines": 0,
            "languages": [],
            "untagged_blocks_count": 0,
            "unclosed_fences_count": 0,
            "technical_spec_status": "prose_only",
        }


# ── extract_markdown_action_checklists (PMBOK §10.2 / §4.4, pure helper) ───


def test_extract_markdown_action_checklists_all_actions_completed():
    """Todos los ítems en [x]/[X] fuera de bloques de código -> 'ALL_ACTIONS_COMPLETED' (100.0%)."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import (
        AnyDocService,
        extract_markdown_action_checklists,
    )

    md = (
        "# Acta de Cierre\n"
        "- [x] Aprobar acta con @sponsor\n"
        "* [X] Publicar línea base (Responsable: PMO)\n"
        "```markdown\n"
        "- [ ] Este ítem dentro de código debe ignorarse\n"
        "```\n"
    )
    res = extract_markdown_action_checklists(md)
    assert res == {
        "total_items": 2,
        "completed_items": 2,
        "pending_items": 0,
        "assigned_pending_items": 0,
        "completion_rate": 100.0,
        "posture": "ALL_ACTIONS_COMPLETED",
    }
    assert AnyDocService.extract_markdown_action_checklists({"markdown": md}) == res
    assert "extract_markdown_action_checklists" in anydoc_module.__all__


def test_extract_markdown_action_checklists_accountable_pending_actions():
    """Ítems pendientes con mención @usuario o Owner:/Responsable: -> 'ACCOUNTABLE_PENDING_ACTIONS'."""
    from backend.services.anydoc_service import extract_markdown_action_checklists

    md = (
        "- [x] Hito 1 cerrado\n"
        "- [ ] Revisar presupuesto con @carlos.ruiz\n"
        "+ [ ] Actualizar matriz RACI (Responsable: Ana Gómez)\n"
        "* [ ] Validar entregable (Owner: qa-team)\n"
    )
    res = extract_markdown_action_checklists(md)
    assert res == {
        "total_items": 4,
        "completed_items": 1,
        "pending_items": 3,
        "assigned_pending_items": 3,
        "completion_rate": 25.0,
        "posture": "ACCOUNTABLE_PENDING_ACTIONS",
    }


def test_extract_markdown_action_checklists_unassigned_pending_actions():
    """Al menos un ítem pendiente sin responsable asignado -> 'UNASSIGNED_PENDING_ACTIONS'."""
    from backend.services.anydoc_service import extract_markdown_action_checklists

    md = (
        "- [x] Definir alcance\n"
        "- [ ] Ajustar cronograma con @pmo_lead\n"
        "- [ ] Tarea huérfana sin propietario\n"
    )
    res = extract_markdown_action_checklists({"markdown": md})
    assert res == {
        "total_items": 3,
        "completed_items": 1,
        "pending_items": 2,
        "assigned_pending_items": 1,
        "completion_rate": 33.33,
        "posture": "UNASSIGNED_PENDING_ACTIONS",
    }


def test_extract_markdown_action_checklists_no_checklist_items():
    """None, texto sin checkboxes o solo checkboxes dentro de bloques ``` -> 'NO_CHECKLIST_ITEMS'."""
    from backend.services.anydoc_service import extract_markdown_action_checklists

    fenced_only = "```md\n- [ ] Falso positivo en bloque\n- [x] Otro en bloque\n```\n"
    for val in (None, "", "Texto normal\n- Viñeta simple sin checkbox", {}, fenced_only):
        res = extract_markdown_action_checklists(val)
        assert res == {
            "total_items": 0,
            "completed_items": 0,
            "pending_items": 0,
            "assigned_pending_items": 0,
            "completion_rate": 0.0,
            "posture": "NO_CHECKLIST_ITEMS",
        }


# ── audit_markdown_reference_citations (PMBOK §10.2 / §4.4, pure helper) ───


def test_audit_markdown_reference_citations_verified_hygiene():
    """Enlaces HTTPS seguros y anclas/rutas internas válidas -> 'VERIFIED_CITATION_HYGIENE' (100.0%)."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_reference_citations,
    )

    md = (
        "# Referencias del Proyecto\n"
        "- [Guía PMBOK](https://www.pmi.org/pmbok-guide)\n"
        "- [Panel de Proyecto](/plataforma/proyectos)\n"
        "- [Sección Alcance](#alcance)\n"
    )
    res = audit_markdown_reference_citations(md)
    assert res == {
        "total_links": 3,
        "https_secure_links": 1,
        "insecure_http_links": 0,
        "internal_or_anchor_links": 2,
        "empty_or_placeholder_links": 0,
        "citation_hygiene_pct": 100.0,
        "posture": "VERIFIED_CITATION_HYGIENE",
    }
    assert AnyDocService.audit_markdown_reference_citations({"markdown": md}) == res
    assert "audit_markdown_reference_citations" in anydoc_module.__all__


def test_audit_markdown_reference_citations_malformed_or_insecure():
    """Enlaces http:// inseguros o placeholders (TODO, #, vacío) -> 'MALFORMED_OR_INSECURE_CITATIONS'."""
    from backend.services.anydoc_service import audit_markdown_reference_citations

    md = (
        "- [Repositorio Oficial](https://github.com/org/repo)\n"
        "- [Sitio Legacy](http://legacy.example.com/doc)\n"
        "- [Pendiente](TODO)\n"
        "- [   ](https://valid.org)\n"
    )
    res = audit_markdown_reference_citations(md)
    assert res == {
        "total_links": 4,
        "https_secure_links": 2,
        "insecure_http_links": 1,
        "internal_or_anchor_links": 0,
        "empty_or_placeholder_links": 2,
        "citation_hygiene_pct": 25.0,
        "posture": "MALFORMED_OR_INSECURE_CITATIONS",
    }


def test_audit_markdown_reference_citations_ignores_images_and_code_blocks():
    """Ignora imágenes ![alt](url) y enlaces dentro de bloques ```."""
    from backend.services.anydoc_service import audit_markdown_reference_citations

    md = (
        "![Diagrama WBS](http://insecure-image-ignored.com/wbs.png)\n"
        "```markdown\n"
        "[Enlace en código](http://insecure-in-code.com)\n"
        "[Placeholder en código](TBD)\n"
        "```\n"
        "Ver [Acta Firmada](https://ccf.org/charter.pdf).\n"
    )
    res = audit_markdown_reference_citations(md)
    assert res == {
        "total_links": 1,
        "https_secure_links": 1,
        "insecure_http_links": 0,
        "internal_or_anchor_links": 0,
        "empty_or_placeholder_links": 0,
        "citation_hygiene_pct": 100.0,
        "posture": "VERIFIED_CITATION_HYGIENE",
    }


def test_audit_markdown_reference_citations_no_citations():
    """None, texto sin enlaces o solo imágenes -> 'NO_CITATIONS' con hygiene 100.0%."""
    from backend.services.anydoc_service import audit_markdown_reference_citations

    for val in (None, "", "Texto plano sin citas.", {}, "![Logo](https://ccf.org/logo.png)"):
        res = audit_markdown_reference_citations(val)
        assert res == {
            "total_links": 0,
            "https_secure_links": 0,
            "insecure_http_links": 0,
            "internal_or_anchor_links": 0,
            "empty_or_placeholder_links": 0,
            "citation_hygiene_pct": 100.0,
            "posture": "NO_CITATIONS",
        }


# ─── audit_markdown_frontmatter_metadata (pure helper) ────────────


def test_frontmatter_governed_document_header():
    """Título + autor + versión completos -> GOVERNED_DOCUMENT_HEADER (100.0) con claves ordenadas."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_metadata

    markdown = (
        "---\n"
        "Título: Plan de Gestión de Riesgos\n"
        'owner: "Oficina de Proyectos"\n'
        'version: "1.0"\n'
        "updated_at: 2026-10-18\n"
        "---\n"
        "\n# Encabezado\n"
    )

    res = audit_markdown_frontmatter_metadata(markdown)

    assert res["has_frontmatter"] is True
    assert res["present_keys"] == ["owner", "título", "updated_at", "version"]
    assert res["has_title"] is True
    assert res["has_owner"] is True
    assert res["has_version_or_date"] is True
    assert res["completeness_score"] == 100.0
    assert res["posture"] == "GOVERNED_DOCUMENT_HEADER"


def test_frontmatter_partial_via_conversion_dict_and_aliases():
    """Dict de conversión (clave 'markdown'), aliases título/versión con acentos -> PARTIAL_FRONTMATTER."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_metadata

    conversion_result = {
        "markdown": (
            "---\n"
            "título: Acta de Constitución\n"
            "versión: 2\n"
            "tags: pmi\n"
            "---\n"
        )
    }

    res = audit_markdown_frontmatter_metadata(conversion_result)

    assert res["has_frontmatter"] is True
    assert res["present_keys"] == ["tags", "título", "versión"]
    assert res["has_title"] is True
    assert res["has_owner"] is False
    assert res["has_version_or_date"] is True
    assert res["completeness_score"] == 66.67
    assert res["posture"] == "PARTIAL_FRONTMATTER"


def test_frontmatter_missing_block_and_uncontrolled():
    """Sin delimitadores -> NO_FRONTMATTER; delimitadores sin claves útiles -> EMPTY_OR_UNCONTROLLED."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_metadata

    for val in (None, "", "# Doc sin frontmatter\n", "sin delimitadores --- en el medio"):
        res = audit_markdown_frontmatter_metadata(val)
        assert res["has_frontmatter"] is False
        assert res["present_keys"] == []
        assert res["completeness_score"] == 0.0
        assert res["posture"] == "NO_FRONTMATTER"

    empty_keys = audit_markdown_frontmatter_metadata(
        "---\ndescription \nstatus:\nautor:   \n---\n"
    )
    assert empty_keys["has_frontmatter"] is True
    assert empty_keys["present_keys"] == []
    assert empty_keys["completeness_score"] == 0.0
    assert empty_keys["posture"] == "EMPTY_OR_UNCONTROLLED_FRONTMATTER"


def test_frontmatter_unclosed_block_is_ignored_and_blank_prefix_tolerated():
    """'---' sin cierre no es frontmatter; líneas en blanco previas se toleran; valores con comillas se limpian."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_metadata

    unclosed = audit_markdown_frontmatter_metadata("---\ntitle: Song\n# Cuerpo\n")
    assert unclosed["has_frontmatter"] is False
    assert unclosed["posture"] == "NO_FRONTMATTER"

    prefixed = audit_markdown_frontmatter_metadata(
        "\n\n---\n\nTitulo: \'Sesiones de Formación\'\n   # comentario\n---\n# Cuerpo\n"
    )
    assert prefixed["has_frontmatter"] is True
    assert prefixed["present_keys"] == ["titulo"]
    assert prefixed["has_title"] is True
    assert prefixed["has_owner"] is False
    assert prefixed["completeness_score"] == 33.33
    assert prefixed["posture"] == "PARTIAL_FRONTMATTER"


def test_extract_markdown_admonition_callouts_high_risk():
    """Presencia de WARNING o CAUTION -> 'HIGH_RISK_CAUTION_HIGHLIGHTED'."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import (
        AnyDocService,
        extract_markdown_admonition_callouts,
    )

    md = (
        "# Plan de Despliegue\n"
        "> [!WARNING]\n"
        "> Impacto potencial en base de datos transaccional.\n\n"
        "  > [!caution]\n"
        "  > Requiere respaldo previo.\n\n"
        "> [!NOTE]\n"
        "> Ventana de mantenimiento programada.\n"
    )
    res = AnyDocService.extract_markdown_admonition_callouts(md)
    assert res == {
        "total_callouts": 3,
        "critical_alerts_count": 2,
        "governance_notices_count": 0,
        "informational_count": 1,
        "counts_by_kind": {"WARNING": 1, "CAUTION": 1, "NOTE": 1},
        "posture": "HIGH_RISK_CAUTION_HIGHLIGHTED",
    }
    assert extract_markdown_admonition_callouts({"markdown": md}) == res
    assert "extract_markdown_admonition_callouts" in anydoc_module.__all__


def test_extract_markdown_admonition_callouts_governance_emphasis():
    """Sin alertas críticas pero con IMPORTANT -> 'GOVERNANCE_EMPHASIS_PRESENT'."""
    from backend.services.anydoc_service import extract_markdown_admonition_callouts

    md = (
        "> [!IMPORTANT]\n"
        "> Todo cambio de línea base requiere aprobación del CCB.\n\n"
        "> [!tip]\n"
        "> Adjuntar análisis de impacto EVM.\n"
    )
    res = extract_markdown_admonition_callouts(md)
    assert res["total_callouts"] == 2
    assert res["critical_alerts_count"] == 0
    assert res["governance_notices_count"] == 1
    assert res["informational_count"] == 1
    assert res["counts_by_kind"] == {"IMPORTANT": 1, "TIP": 1}
    assert res["posture"] == "GOVERNANCE_EMPHASIS_PRESENT"


def test_extract_markdown_admonition_callouts_informational_only():
    """Solo NOTE o TIP -> 'INFORMATIONAL_GUIDANCE_ONLY'."""
    from backend.services.anydoc_service import extract_markdown_admonition_callouts

    md = "> [!NOTE]\n> Nota 1\n\n> [!TIP]\n> Consejo 1\n> [!note]\n> Nota 2\n"
    res = extract_markdown_admonition_callouts(md)
    assert res["total_callouts"] == 3
    assert res["critical_alerts_count"] == 0
    assert res["governance_notices_count"] == 0
    assert res["informational_count"] == 3
    assert res["counts_by_kind"] == {"NOTE": 2, "TIP": 1}
    assert res["posture"] == "INFORMATIONAL_GUIDANCE_ONLY"


def test_extract_markdown_admonition_callouts_none_and_fenced_ignored():
    """Sin alertas fuera de bloques ``` -> 'NO_CALLOUT_ALERTS'."""
    from backend.services.anydoc_service import extract_markdown_admonition_callouts

    md_fenced = (
        "```markdown\n"
        "> [!CAUTION]\n"
        "> Ejemplo dentro de bloque de código ignorado\n"
        "```\n"
    )
    for val in (None, "", {"markdown": ""}, md_fenced):
        res = extract_markdown_admonition_callouts(val)
        assert res == {
            "total_callouts": 0,
            "critical_alerts_count": 0,
            "governance_notices_count": 0,
            "informational_count": 0,
            "counts_by_kind": {},
            "posture": "NO_CALLOUT_ALERTS",
        }


def test_extract_markdown_glossary_definitions_governed_domain_glossary():
    """Definiciones completas y sin duplicados -> 'GOVERNED_DOMAIN_GLOSSARY'."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import (
        AnyDocService,
        extract_markdown_glossary_definitions,
    )

    md = (
        "# Glosario del Proyecto\n\n"
        "- **EVM**: Earned Value Management para control integrado de alcance, cronograma y costos.\n"
        "* **CCB** — Comité de Control de Cambios responsable de aprobar o rechazar solicitudes.\n"
        "**WBS**: Work Breakdown Structure jerárquica orientada a entregables verificables.\n"
        "- **Línea Base de Costos** - Presupuesto autorizado distribuido en el tiempo (BAC).\n"
    )
    res = AnyDocService.extract_markdown_glossary_definitions(md)
    assert res["total_definitions"] == 4
    assert res["acronym_count"] == 3
    assert [e["term"] for e in res["entries"]] == [
        "EVM",
        "CCB",
        "WBS",
        "Línea Base de Costos",
    ]
    assert [e["is_acronym"] for e in res["entries"]] == [True, True, True, False]
    assert res["duplicate_terms"] == []
    assert res["shallow_definitions"] == []
    assert res["glossary_posture"] == "GOVERNED_DOMAIN_GLOSSARY"
    assert extract_markdown_glossary_definitions({"markdown": md}) == res
    assert "extract_markdown_glossary_definitions" in anydoc_module.__all__


def test_extract_markdown_glossary_definitions_duplicate_term_conflicts():
    """Términos repetidos (case-insensitive) -> 'DUPLICATE_TERM_CONFLICTS'."""
    from backend.services.anydoc_service import extract_markdown_glossary_definitions

    md = (
        "- **EVM**: Earned Value Management estándar PMBOK sección 7.4.\n"
        "- **evm**: Gestión del Valor Ganado redefinida en sección secundaria.\n"
        "- **CCB**: Change Control Board del proyecto.\n"
    )
    res = extract_markdown_glossary_definitions(md)
    assert res["total_definitions"] == 3
    assert res["acronym_count"] == 2
    assert res["duplicate_terms"] == ["EVM"]
    assert res["shallow_definitions"] == []
    assert res["glossary_posture"] == "DUPLICATE_TERM_CONFLICTS"


def test_extract_markdown_glossary_definitions_shallow_definitions():
    """Definiciones cortas (<10 chars) o marcadores TBD/TODO/N/A/PENDIENTE -> 'SHALLOW_GLOSSARY_DEFINITIONS'."""
    from backend.services.anydoc_service import extract_markdown_glossary_definitions

    md = (
        "- **BAC**: Budget at Completion total autorizado del proyecto.\n"
        "- **EAC**: TBD\n"
        "- **VAC**: Corto\n"
        "- **TCPI**: PENDIENTE\n"
    )
    res = extract_markdown_glossary_definitions(md)
    assert res["total_definitions"] == 4
    assert res["acronym_count"] == 4
    assert res["duplicate_terms"] == []
    assert res["shallow_definitions"] == ["EAC", "TCPI", "VAC"]
    assert res["glossary_posture"] == "SHALLOW_GLOSSARY_DEFINITIONS"


def test_extract_markdown_glossary_definitions_no_entries_and_fenced_ignored():
    """Sin definiciones o solo dentro de bloques ``` -> 'NO_GLOSSARY_ENTRIES'."""
    from backend.services.anydoc_service import extract_markdown_glossary_definitions

    md_fenced = (
        "# Documento Técnico\n"
        "```markdown\n"
        "- **EVM**: Earned Value Management dentro de bloque de código ignorado.\n"
        "**CCB**: Comité de Control de Cambios en ejemplo.\n"
        "```\n"
        "Texto normal sin definiciones de glosario.\n"
    )
    for payload in (None, "", md_fenced):
        res = extract_markdown_glossary_definitions(payload)
        assert res == {
            "total_definitions": 0,
            "acronym_count": 0,
            "entries": [],
            "duplicate_terms": [],
            "shallow_definitions": [],
            "glossary_posture": "NO_GLOSSARY_ENTRIES",
        }


def test_audit_markdown_mermaid_diagrams_governed_architecture():
    """Bloques mermaid con encabezado soportado, >=2 líneas útiles y sin etiquetas HTML -> 'GOVERNED_ARCHITECTURE_DIAGRAMS'."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_mermaid_diagrams,
    )

    md = (
        "# Arquitectura de Gobernanza\n\n"
        "```mermaid\n"
        "%% Diagrama de flujo CCB\n"
        "flowchart TD\n"
        '    A["Solicitud CR"] --> B["Evaluación Impacto EVM"]\n'
        '    B --> C["Dictamen CCB"]\n'
        "```\n\n"
        "```mermaid\n"
        "stateDiagram-v2\n"
        "    [*] --> Borrador\n"
        "    Borrador --> Autorizado\n"
        "```\n"
    )
    res = AnyDocService.audit_markdown_mermaid_diagrams(md)
    assert res == {
        "total_diagrams": 2,
        "diagram_types": ["flowchart", "stateDiagram-v2"],
        "empty_diagram_indices": [],
        "unsupported_diagram_indices": [],
        "html_tag_hazard_indices": [],
        "valid_diagram_count": 2,
        "diagram_posture": "GOVERNED_ARCHITECTURE_DIAGRAMS",
    }
    assert audit_markdown_mermaid_diagrams({"markdown": md}) == res
    assert "audit_markdown_mermaid_diagrams" in anydoc_module.__all__


def test_audit_markdown_mermaid_diagrams_invalid_or_unsupported():
    """Bloques vacíos (<2 líneas útiles) o con tipo no soportado -> 'INVALID_OR_UNSUPPORTED_DIAGRAM'."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagrams

    md = (
        "```mermaid\n"
        "%% Solo comentario y una línea\n"
        "flowchart LR\n"
        "```\n\n"
        "```mermaid\n"
        "mindmap\n"
        "  root((Proyecto))\n"
        "    Alcance\n"
        "```\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    PM->>Sponsor: Solicita firma Charter\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagrams(md)
    assert res["total_diagrams"] == 3
    assert res["diagram_types"] == ["flowchart", "sequenceDiagram"]
    assert res["empty_diagram_indices"] == [1]
    assert res["unsupported_diagram_indices"] == [2]
    assert res["html_tag_hazard_indices"] == []
    assert res["valid_diagram_count"] == 1
    assert res["diagram_posture"] == "INVALID_OR_UNSUPPORTED_DIAGRAM"


def test_audit_markdown_mermaid_diagrams_html_label_hazard():
    """Bloques válidos en tipo pero con etiquetas HTML crudas (<br>, <b>, <div>, etc.) -> 'HTML_LABEL_SYNTAX_HAZARD'."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagrams

    md = (
        "```mermaid\n"
        "graph TD\n"
        '    A["Fase 1<br/>Inicio"] --> B["<b>Cierre</b>"]\n'
        "```\n"
    )
    res = audit_markdown_mermaid_diagrams(md)
    assert res["total_diagrams"] == 1
    assert res["diagram_types"] == ["graph"]
    assert res["empty_diagram_indices"] == []
    assert res["unsupported_diagram_indices"] == []
    assert res["html_tag_hazard_indices"] == [1]
    assert res["valid_diagram_count"] == 0
    assert res["diagram_posture"] == "HTML_LABEL_SYNTAX_HAZARD"


def test_audit_markdown_mermaid_diagrams_no_diagrams():
    """Texto vacío, None o solo bloques de otros lenguajes -> 'NO_MERMAID_DIAGRAMS'."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagrams

    other_code = "```python\nprint('hello')\n```\n"
    for payload in (None, "", other_code):
        res = audit_markdown_mermaid_diagrams(payload)
        assert res == {
            "total_diagrams": 0,
            "diagram_types": [],
            "empty_diagram_indices": [],
            "unsupported_diagram_indices": [],
            "html_tag_hazard_indices": [],
            "valid_diagram_count": 0,
            "diagram_posture": "NO_MERMAID_DIAGRAMS",
        }


def test_audit_markdown_media_accessibility_governed_accessible_media():
    """Imágenes con alt-text descriptivo y URLs seguras/relativas válidas -> GOVERNED_ACCESSIBLE_MEDIA."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_media_accessibility,
    )

    md = (
        "# Arquitectura del Proyecto\n"
        "![Diagrama de red EDT fase 1](https://cdn.ccf.org/assets/edt-fase-1.png)\n"
        "![Curva S de valor ganado CPI SPI](/static/evm/curva-s-q3.svg)\n"
        "```markdown\n"
        "![img](http://insecure.example.com/broken image.png)\n"
        "```\n"
    )
    res = audit_markdown_media_accessibility(md)
    assert res == {
        "total_images": 2,
        "compliant_images_count": 2,
        "missing_alt_text_urls": [],
        "insecure_or_broken_urls": [],
        "accessibility_rate_pct": 100.0,
        "media_posture": "GOVERNED_ACCESSIBLE_MEDIA",
    }
    assert AnyDocService.audit_markdown_media_accessibility({"markdown": md}) == res


def test_audit_markdown_media_accessibility_insecure_or_broken_links():
    """URLs con http://, vacías o con espacios sin codificar -> INSECURE_OR_BROKEN_MEDIA_LINKS."""
    from backend.services.anydoc_service import audit_markdown_media_accessibility

    md = (
        "![Cronograma maestro aprobado](https://cdn.ccf.org/gantt-v2.png)\n"
        "![Topología de red insegura](http://intranet.ccf.org/topologia.png)\n"
        "![Matriz RACI con espacios](https://cdn.ccf.org/matriz raci 2026.png)\n"
        "![Foto]()\n"
    )
    res = audit_markdown_media_accessibility(md)
    assert res["total_images"] == 4
    assert res["compliant_images_count"] == 1
    assert res["missing_alt_text_urls"] == ["<empty-url>"]
    assert res["insecure_or_broken_urls"] == [
        "http://intranet.ccf.org/topologia.png",
        "https://cdn.ccf.org/matriz raci 2026.png",
        "<empty-url>",
    ]
    assert res["accessibility_rate_pct"] == 25.0
    assert res["media_posture"] == "INSECURE_OR_BROKEN_MEDIA_LINKS"


def test_audit_markdown_media_accessibility_missing_accessible_alt_text():
    """URLs válidas pero con alt-text corto (<3) o genérico (image, screenshot, foto, etc.) -> MISSING_ACCESSIBLE_ALT_TEXT."""
    from backend.services.anydoc_service import audit_markdown_media_accessibility

    md = (
        "![Arquitectura de microservicios CCF](https://cdn.ccf.org/arch.png)\n"
        "![Screenshot](https://cdn.ccf.org/screen1.png)\n"
        "![ab](https://cdn.ccf.org/short-alt.png)\n"
        "![captura](/docs/img/cap.png)\n"
    )
    res = audit_markdown_media_accessibility(md)
    assert res["total_images"] == 4
    assert res["compliant_images_count"] == 1
    assert res["missing_alt_text_urls"] == [
        "https://cdn.ccf.org/screen1.png",
        "https://cdn.ccf.org/short-alt.png",
        "/docs/img/cap.png",
    ]
    assert res["insecure_or_broken_urls"] == []
    assert res["accessibility_rate_pct"] == 25.0
    assert res["media_posture"] == "MISSING_ACCESSIBLE_ALT_TEXT"


def test_audit_markdown_media_accessibility_no_embedded_media():
    """Sin imágenes fuera de bloques de código cercados o entrada vacía/None -> NO_EMBEDDED_MEDIA."""
    from backend.services.anydoc_service import audit_markdown_media_accessibility

    fenced_only = (
        "Texto con [enlace normal](https://ccf.org) sin imágenes.\n"
        "```md\n"
        "![Diagrama ignorado](https://ccf.org/ignored.png)\n"
        "```\n"
    )
    for payload in (None, "", fenced_only):
        res = audit_markdown_media_accessibility(payload)
        assert res == {
            "total_images": 0,
            "compliant_images_count": 0,
            "missing_alt_text_urls": [],
            "insecure_or_broken_urls": [],
            "accessibility_rate_pct": 0.0,
            "media_posture": "NO_EMBEDDED_MEDIA",
        }


def test_audit_markdown_toc_anchor_alignment_aligned_structure():
    """ToC con anclas válidas y jerarquía secuencial H1->H2->H3 -> ALIGNED_DOCUMENT_STRUCTURE."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_toc_anchor_alignment,
    )

    md = (
        "# Alcance del Proyecto\n"
        "- [Alcance](#alcance-del-proyecto)\n"
        "- [Entregables](#entregables-clave)\n\n"
        "## Entregables Clave\n"
        "Detalle de paquetes de trabajo.\n\n"
        "### Criterios de Aceptacion\n"
        "Lista de verificación DoD.\n"
    )
    res = audit_markdown_toc_anchor_alignment(md)
    assert res == {
        "heading_count": 3,
        "internal_anchor_count": 2,
        "broken_toc_anchors": [],
        "skipped_level_headings": [],
        "is_aligned": True,
        "toc_posture": "ALIGNED_DOCUMENT_STRUCTURE",
    }
    assert AnyDocService.audit_markdown_toc_anchor_alignment(md) == res


def test_audit_markdown_toc_anchor_alignment_broken_toc_anchors():
    """Enlaces de ToC hacia secciones inexistentes (ignorando bloques cercados) -> BROKEN_TOC_ANCHORS."""
    from backend.services.anydoc_service import audit_markdown_toc_anchor_alignment

    md = (
        "# Gobernanza PMI\n"
        "- [Gobernanza](#gobernanza-pmi)\n"
        "- [Riesgos](#seccion-inexistente)\n"
        "- [Riesgos Duplicado](#seccion-inexistente)\n"
        "```markdown\n"
        "[Ignorado en bloque](#ancla-fantasma)\n"
        "# Encabezado en codigo\n"
        "```\n"
        "~~~md\n"
        "[Ignorado en tilde](#otra-fantasma)\n"
        "~~~\n"
        "## Control de Cambios\n"
    )
    res = audit_markdown_toc_anchor_alignment(md)
    assert res["heading_count"] == 2
    assert res["internal_anchor_count"] == 3
    assert res["broken_toc_anchors"] == ["#seccion-inexistente"]
    assert res["skipped_level_headings"] == []
    assert res["is_aligned"] is False
    assert res["toc_posture"] == "BROKEN_TOC_ANCHORS"


def test_audit_markdown_toc_anchor_alignment_heading_hierarchy_skip():
    """Salto de jerarquía (# Nivel 1 -> ### Nivel 3 Saltado) sin anclas rotas -> HEADING_HIERARCHY_SKIP."""
    from backend.services.anydoc_service import audit_markdown_toc_anchor_alignment

    md = (
        "# Nivel 1\n"
        "[Ir a Nivel 1](#nivel-1)\n\n"
        "### Nivel 3 Saltado\n"
        "Contenido bajo H3 directo.\n"
    )
    res = audit_markdown_toc_anchor_alignment(md)
    assert res["heading_count"] == 2
    assert res["internal_anchor_count"] == 1
    assert res["broken_toc_anchors"] == []
    assert res["skipped_level_headings"] == ["Nivel 3 Saltado"]
    assert res["is_aligned"] is False
    assert res["toc_posture"] == "HEADING_HIERARCHY_SKIP"


def test_audit_markdown_toc_anchor_alignment_no_headings_found():
    """Texto vacío, None o prosa sin encabezados ATX -> NO_HEADINGS_FOUND."""
    from backend.services.anydoc_service import audit_markdown_toc_anchor_alignment

    prose_only = "Documento de notas rápidas sin encabezados ATX.\n```\n# No cuenta\n```\n"
    for payload in (None, "", "   ", prose_only):
        res = audit_markdown_toc_anchor_alignment(payload)
        assert res["heading_count"] == 0
        assert res["broken_toc_anchors"] == []
        assert res["skipped_level_headings"] == []
        assert res["is_aligned"] is True
        assert res["toc_posture"] == "NO_HEADINGS_FOUND"


def test_extract_markdown_checklist_progress_fully_completed():
    """Checklist 100% completada ignorando bloques cercados -> CHECKLIST_FULLY_COMPLETED."""
    from backend.services.anydoc_service import (
        AnyDocService,
        extract_markdown_checklist_progress,
    )

    md = (
        "# Checklist de Calidad PMBOK §8.3\n"
        "- [x] Validar firma de Acta de Constitución @pm\n"
        "* [X] Aprobar línea base de alcance WBS\n"
        "1. [x] Registrar lecciones aprendidas de fase\n"
        "```markdown\n"
        "- [ ] [BLOCKER] Ítem pendiente dentro de bloque de código\n"
        "```\n"
        "~~~md\n"
        "* [ ] Otro pendiente ignorado en tilde\n"
        "~~~\n"
    )
    res = extract_markdown_checklist_progress(md)
    assert res == {
        "total_items": 3,
        "completed_items": 3,
        "pending_items": 0,
        "completion_rate_pct": 100.0,
        "open_blocker_items": [],
        "unassigned_pending_items": [],
        "is_complete": True,
        "checklist_posture": "CHECKLIST_FULLY_COMPLETED",
    }
    assert AnyDocService.extract_markdown_checklist_progress(md) == res


def test_extract_markdown_checklist_progress_blocked_items():
    """Ítems pendientes con marcador [BLOQUEANTE] / [BLOCKER] -> BLOCKED_CHECKLIST_ITEMS."""
    from backend.services.anydoc_service import extract_markdown_checklist_progress

    md = (
        "- [x] Diseño aprobado @arquitecto\n"
        "- [ ] [BLOQUEANTE] Liberar credenciales de pasarela @devops\n"
        "+ [ ] [BLOCKER] Certificación de seguridad pendiente\n"
    )
    res = extract_markdown_checklist_progress(md)
    assert res["total_items"] == 3
    assert res["completed_items"] == 1
    assert res["pending_items"] == 2
    assert res["completion_rate_pct"] == 33.33
    assert res["open_blocker_items"] == [
        "[BLOQUEANTE] Liberar credenciales de pasarela @devops",
        "[BLOCKER] Certificación de seguridad pendiente",
    ]
    assert res["unassigned_pending_items"] == [
        "[BLOCKER] Certificación de seguridad pendiente",
    ]
    assert res["is_complete"] is False
    assert res["checklist_posture"] == "BLOCKED_CHECKLIST_ITEMS"


def test_extract_markdown_checklist_progress_unassigned_and_in_progress():
    """Ítems pendientes sin bloqueantes: UNASSIGNED_PENDING_ITEMS vs CHECKLIST_IN_PROGRESS."""
    from backend.services.anydoc_service import extract_markdown_checklist_progress

    md_unassigned = (
        "- [x] Entregable 1 completado @ana\n"
        "- [ ] Revisar matriz de trazabilidad sin responsable\n"
    )
    res_unassigned = extract_markdown_checklist_progress(md_unassigned)
    assert res_unassigned["total_items"] == 2
    assert res_unassigned["completed_items"] == 1
    assert res_unassigned["pending_items"] == 1
    assert res_unassigned["completion_rate_pct"] == 50.0
    assert res_unassigned["open_blocker_items"] == []
    assert res_unassigned["unassigned_pending_items"] == [
        "Revisar matriz de trazabilidad sin responsable"
    ]
    assert res_unassigned["is_complete"] is False
    assert res_unassigned["checklist_posture"] == "UNASSIGNED_PENDING_ITEMS"

    md_assigned = (
        "- [x] Entregable 1 completado @ana\n"
        "- [ ] Ejecutar pruebas de regresión @qa.lead\n"
        "2. [ ] Validar criterios DoD Responsable: Carlos\n"
    )
    res_assigned = extract_markdown_checklist_progress(md_assigned)
    assert res_assigned["total_items"] == 3
    assert res_assigned["completed_items"] == 1
    assert res_assigned["pending_items"] == 2
    assert res_assigned["completion_rate_pct"] == 33.33
    assert res_assigned["open_blocker_items"] == []
    assert res_assigned["unassigned_pending_items"] == []
    assert res_assigned["is_complete"] is False
    assert res_assigned["checklist_posture"] == "CHECKLIST_IN_PROGRESS"


def test_extract_markdown_checklist_progress_no_checklist_items():
    """Texto vacío, None o sin casillas de verificación -> NO_CHECKLIST_ITEMS."""
    from backend.services.anydoc_service import extract_markdown_checklist_progress

    prose_only = "# Acta de Reunión\n- Punto normal sin casilla\n```\n- [ ] En código\n```\n"
    for payload in (None, "", "   ", prose_only):
        res = extract_markdown_checklist_progress(payload)
        assert res == {
            "total_items": 0,
            "completed_items": 0,
            "pending_items": 0,
            "completion_rate_pct": 0.0,
            "open_blocker_items": [],
            "unassigned_pending_items": [],
            "is_complete": True,
            "checklist_posture": "NO_CHECKLIST_ITEMS",
        }


def test_audit_markdown_footnote_citations_consistent():
    """Notas al pie consistentes ignorando bloques cercados -> CONSISTENT_FOOTNOTE_CITATIONS."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_footnote_citations,
    )

    md = (
        "# Informe Técnico PMI §4.4\n"
        "El cálculo de EVM sigue el estándar oficial[^pmbok] y la guía de auditoría[^1].\n"
        "Repetir la cita[^PMBOK] mantiene el conteo único.\n"
        "```markdown\n"
        "Cita fantasma en código[^ghost] y definición[^code_def]: ignorada.\n"
        "```\n"
        "[^pmbok]: PMI Practice Standard for Earned Value Management.\n"
        "[^1]: Manual Operativo PMO CCF.\n"
    )
    res = audit_markdown_footnote_citations(md)
    assert res == {
        "referenced_footnotes_count": 2,
        "defined_footnotes_count": 2,
        "unresolved_footnote_refs": [],
        "unused_footnote_defs": [],
        "is_consistent": True,
        "citation_posture": "CONSISTENT_FOOTNOTE_CITATIONS",
    }
    assert AnyDocService.audit_markdown_footnote_citations(md) == res


def test_audit_markdown_footnote_citations_unresolved_references():
    """Referencias sin definición o con definición vacía -> UNRESOLVED_CITATION_REFERENCES."""
    from backend.services.anydoc_service import audit_markdown_footnote_citations

    md = (
        "Se requiere aprobación del comité[^ccb] y validación de arquitectura[^arch].\n"
        "También se cita una nota con definición vacía[^empty_def].\n"
        "[^ccb]: Comité de Control de Cambios PMBOK §4.6.\n"
        "[^empty_def]:    \n"
    )
    res = audit_markdown_footnote_citations(md)
    assert res["referenced_footnotes_count"] == 3
    assert res["defined_footnotes_count"] == 1
    assert res["unresolved_footnote_refs"] == ["arch", "empty_def"]
    assert res["unused_footnote_defs"] == []
    assert res["is_consistent"] is False
    assert res["citation_posture"] == "UNRESOLVED_CITATION_REFERENCES"


def test_audit_markdown_footnote_citations_orphan_definitions():
    """Definiciones huérfanas nunca citadas en el cuerpo -> ORPHAN_FOOTNOTE_DEFINITIONS."""
    from backend.services.anydoc_service import audit_markdown_footnote_citations

    md = (
        "El alcance está documentado en la WBS[^wbs].\n"
        "[^wbs]: Diccionario de la EDT aprobado.\n"
        "[^obsolete]: Nota histórica que ya no se referencia en el texto.\n"
    )
    res = audit_markdown_footnote_citations(md)
    assert res["referenced_footnotes_count"] == 1
    assert res["defined_footnotes_count"] == 2
    assert res["unresolved_footnote_refs"] == []
    assert res["unused_footnote_defs"] == ["obsolete"]
    assert res["is_consistent"] is False
    assert res["citation_posture"] == "ORPHAN_FOOTNOTE_DEFINITIONS"


def test_audit_markdown_footnote_citations_no_footnotes_present():
    """Texto vacío, None o sin notas al pie -> NO_FOOTNOTES_PRESENT."""
    from backend.services.anydoc_service import audit_markdown_footnote_citations

    prose_only = "# Documento sin notas\nTexto normal con [enlace](https://example.org).\n~~~md\n[^1]: En código\n~~~\n"
    for payload in (None, "", "   ", prose_only):
        res = audit_markdown_footnote_citations(payload)
        assert res == {
            "referenced_footnotes_count": 0,
            "defined_footnotes_count": 0,
            "unresolved_footnote_refs": [],
            "unused_footnote_defs": [],
            "is_consistent": True,
            "citation_posture": "NO_FOOTNOTES_PRESENT",
        }


def test_audit_markdown_frontmatter_governance_compliant():
    """Documento con YAML frontmatter completo -> COMPLIANT_DOCUMENT_FRONTMATTER."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_frontmatter_governance,
    )

    md = (
        "---\n"
        'title: "Manual de Gestión de Configuración PMI"\n'
        "owner: PMO-Ministerial\n"
        "version: '2.1.0'\n"
        "status: Approved\n"
        "classification: Internal\n"
        "---\n"
        "# Introducción\n"
        "Contenido del documento.\n"
    )
    res = audit_markdown_frontmatter_governance(md)
    assert res == {
        "has_frontmatter": True,
        "parsed_keys_count": 5,
        "missing_required_keys": [],
        "completeness_pct": 100.0,
        "is_compliant": True,
        "frontmatter_posture": "COMPLIANT_DOCUMENT_FRONTMATTER",
    }
    assert AnyDocService.audit_markdown_frontmatter_governance(md) == res


def test_audit_markdown_frontmatter_governance_incomplete_or_placeholder():
    """Frontmatter incompleto o con valores placeholder (TBD, vacío) -> INCOMPLETE_FRONTMATTER_METADATA."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_governance

    md = (
        "---\n"
        "title: Plan de Calidad\n"
        "owner: TBD\n"
        "version: ''\n"
        "status: Draft\n"
        "...\n"
        "# Alcance\n"
    )
    res = audit_markdown_frontmatter_governance(md)
    assert res == {
        "has_frontmatter": True,
        "parsed_keys_count": 2,
        "missing_required_keys": ["owner", "version"],
        "completeness_pct": 50.0,
        "is_compliant": False,
        "frontmatter_posture": "INCOMPLETE_FRONTMATTER_METADATA",
    }


def test_audit_markdown_frontmatter_governance_unclosed_block():
    """Bloque frontmatter abierto sin --- de cierre -> UNCLOSED_FRONTMATTER_BLOCK."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_governance

    md = (
        "---\n"
        "title: Acta sin cierre de frontmatter\n"
        "owner: PMO\n"
        "version: 1.0\n"
        "status: Active\n"
        "# Encabezado nunca precedido por cierre YAML\n"
    )
    res = audit_markdown_frontmatter_governance(md)
    assert res == {
        "has_frontmatter": False,
        "parsed_keys_count": 0,
        "missing_required_keys": ["title", "owner", "version", "status"],
        "completeness_pct": 0.0,
        "is_compliant": False,
        "frontmatter_posture": "UNCLOSED_FRONTMATTER_BLOCK",
    }


def test_audit_markdown_frontmatter_governance_missing_or_empty():
    """Documento sin frontmatter o vacío -> MISSING_FRONTMATTER_BLOCK."""
    from backend.services.anydoc_service import audit_markdown_frontmatter_governance

    for payload in (None, "", "   ", "# Título directo sin YAML\n---\ntitle: X\n---\n"):
        res = audit_markdown_frontmatter_governance(payload, required_keys=["title", "owner"])
        assert res == {
            "has_frontmatter": False,
            "parsed_keys_count": 0,
            "missing_required_keys": ["title", "owner"],
            "completeness_pct": 0.0,
            "is_compliant": False,
            "frontmatter_posture": "MISSING_FRONTMATTER_BLOCK",
        }


def test_audit_markdown_admonition_callouts_valid_governance():
    """Alertas válidas NOTE, WARNING, CAUTION con cuerpo e ignorando bloques cercados -> VALID_CALLOUT_GOVERNANCE."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_admonition_callouts,
    )

    md = (
        "# Manual Operativo\n"
        "> [!NOTE]\n"
        "> Esta nota explica el proceso de revisión de alcance.\n\n"
        "> [!WARNING] Riesgo de sobrecosto si se omite el CCB.\n\n"
        "> [!CAUTION]\n"
        "> Acción irreversible sobre la línea base.\n"
        "```markdown\n"
        "> [!INVALID]\n"
        "```\n"
    )
    res = audit_markdown_admonition_callouts(md)
    assert res == {
        "total_callouts": 3,
        "high_severity_callouts_count": 2,
        "unsupported_callout_types": [],
        "empty_callout_refs": [],
        "nested_callout_refs": [],
        "is_callout_hygiene_valid": True,
        "callout_posture": "VALID_CALLOUT_GOVERNANCE",
    }
    assert AnyDocService.audit_markdown_admonition_callouts(md) == res


def test_audit_markdown_admonition_callouts_unsupported_type():
    """Tipo no soportado (> [!DANGER] o > [!BUG]) -> UNSUPPORTED_CALLOUT_TYPE."""
    from backend.services.anydoc_service import audit_markdown_admonition_callouts

    md = (
        "> [!DANGER]\n"
        "> Alerta fuera del estándar GFM.\n\n"
        "> [!TIP]\n"
        "> Consejo válido.\n"
    )
    res = audit_markdown_admonition_callouts(md)
    assert res["total_callouts"] == 2
    assert res["unsupported_callout_types"] == ["DANGER"]
    assert res["is_callout_hygiene_valid"] is False
    assert res["callout_posture"] == "UNSUPPORTED_CALLOUT_TYPE"


def test_audit_markdown_admonition_callouts_nested_and_empty_body():
    """Alerta anidada (> > [!WARNING]) -> NESTED_OR_MALFORMED_CALLOUT y cuerpo vacío -> EMPTY_CALLOUT_BODY."""
    from backend.services.anydoc_service import audit_markdown_admonition_callouts

    nested_md = "> > [!WARNING]\n> Contenido anidado no permitido.\n"
    nested_res = audit_markdown_admonition_callouts(nested_md)
    assert nested_res["nested_callout_refs"] == ["L1:WARNING"]
    assert nested_res["is_callout_hygiene_valid"] is False
    assert nested_res["callout_posture"] == "NESTED_OR_MALFORMED_CALLOUT"

    empty_md = "> [!IMPORTANT]\n>    \n\nPárrafo fuera de la alerta.\n"
    empty_res = audit_markdown_admonition_callouts(empty_md)
    assert empty_res["empty_callout_refs"] == ["L1:IMPORTANT"]
    assert empty_res["is_callout_hygiene_valid"] is False
    assert empty_res["callout_posture"] == "EMPTY_CALLOUT_BODY"


def test_audit_markdown_admonition_callouts_no_callouts_found():
    """Documento sin alertas o None -> NO_CALLOUTS_FOUND."""
    from backend.services.anydoc_service import audit_markdown_admonition_callouts

    for payload in (None, "", "   ", "> Cita normal sin marcador de alerta.\n"):
        res = audit_markdown_admonition_callouts(payload)
        assert res == {
            "total_callouts": 0,
            "high_severity_callouts_count": 0,
            "unsupported_callout_types": [],
            "empty_callout_refs": [],
            "nested_callout_refs": [],
            "is_callout_hygiene_valid": True,
            "callout_posture": "NO_CALLOUTS_FOUND",
        }


def test_audit_markdown_code_fence_hygiene_clean():
    """Bloques de código bien formados con etiqueta de lenguaje y contenido -> CLEAN_CODE_FENCE_HYGIENE."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_code_fence_hygiene,
    )

    md = (
        "# Especificación Técnica\n"
        "```python\n"
        "def calc_cpi(ev: float, ac: float) -> float:\n"
        "    return ev / ac\n"
        "```\n\n"
        "~~~sql\n"
        "SELECT id, title FROM projects;\n"
        "~~~\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "total_code_blocks": 2,
        "typed_code_blocks_count": 2,
        "untyped_fence_lines": [],
        "empty_fence_lines": [],
        "unclosed_fence_lines": [],
        "is_fence_hygiene_valid": True,
        "fence_posture": "CLEAN_CODE_FENCE_HYGIENE",
    }
    assert AnyDocService.audit_markdown_code_fence_hygiene(md) == res


def test_audit_markdown_code_fence_hygiene_unclosed_fence():
    """Bloque de código sin cerrar al final del documento -> UNCLOSED_CODE_FENCE_ERROR."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    md = (
        "Texto introductorio\n"
        "```mermaid\n"
        "flowchart TD\n"
        "  A --> B\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "total_code_blocks": 1,
        "typed_code_blocks_count": 1,
        "untyped_fence_lines": [],
        "empty_fence_lines": [],
        "unclosed_fence_lines": [2],
        "is_fence_hygiene_valid": False,
        "fence_posture": "UNCLOSED_CODE_FENCE_ERROR",
    }


def test_audit_markdown_code_fence_hygiene_untyped_and_empty_blocks():
    """Bloque sin lenguaje -> UNTYPED_CODE_FENCE_WARNING y bloque vacío -> EMPTY_CODE_FENCE_WARNING."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    untyped_md = "```\necho 'sin lenguaje'\n```\n"
    untyped_res = audit_markdown_code_fence_hygiene(untyped_md)
    assert untyped_res["untyped_fence_lines"] == [1]
    assert untyped_res["is_fence_hygiene_valid"] is False
    assert untyped_res["fence_posture"] == "UNTYPED_CODE_FENCE_WARNING"

    empty_md = "```bash\n   \n```\n"
    empty_res = audit_markdown_code_fence_hygiene(empty_md)
    assert empty_res["empty_fence_lines"] == [1]
    assert empty_res["is_fence_hygiene_valid"] is False
    assert empty_res["fence_posture"] == "EMPTY_CODE_FENCE_WARNING"


def test_audit_markdown_code_fence_hygiene_no_code_blocks():
    """Documento sin bloques de código o None -> NO_CODE_BLOCKS_FOUND."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    for payload in (None, "", "   ", "# Solo prosa sin bloques cercados\n"):
        res = audit_markdown_code_fence_hygiene(payload)
        assert res == {
            "total_code_blocks": 0,
            "typed_code_blocks_count": 0,
            "untyped_fence_lines": [],
            "empty_fence_lines": [],
            "unclosed_fence_lines": [],
            "is_fence_hygiene_valid": True,
            "fence_posture": "NO_CODE_BLOCKS_FOUND",
        }


def test_audit_markdown_image_asset_hygiene_compliant():
    """Imágenes con alt-text descriptivo y rutas HTTPS/relativas (ignorando cercados) -> COMPLIANT_IMAGE_ASSET_HYGIENE."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_image_asset_hygiene,
    )

    md = (
        "# Arquitectura de Proyecto\n"
        "![Diagrama de red lógica PDM](https://cdn.ccf.org/assets/pdm.png \"PDM\")\n"
        "![Curva S de valor ganado EVM](/assets/charts/evm-s-curve.svg)\n"
        "```markdown\n"
        "![](http://insecure-inside-fence.local/img.png)\n"
        "```\n"
    )
    res = audit_markdown_image_asset_hygiene(md)
    assert res == {
        "total_images": 2,
        "compliant_images_count": 2,
        "missing_alt_text_refs": [],
        "invalid_asset_url_refs": [],
        "is_image_hygiene_valid": True,
        "image_hygiene_posture": "COMPLIANT_IMAGE_ASSET_HYGIENE",
    }
    assert AnyDocService.audit_markdown_image_asset_hygiene(md) == res


def test_audit_markdown_image_asset_hygiene_invalid_or_insecure_url():
    """Imagen con URL vacía, http:// o /tmp/ -> INVALID_OR_INSECURE_ASSET_URL."""
    from backend.services.anydoc_service import audit_markdown_image_asset_hygiene

    md = (
        "![Diagrama inseguro HTTP](http://legacy.ccf.org/chart.png)\n"
        "![Archivo temporal local](/tmp/captura_temp.png)\n"
        "![Sin destino]()\n"
    )
    res = audit_markdown_image_asset_hygiene(md)
    assert res["total_images"] == 3
    assert res["compliant_images_count"] == 0
    assert res["invalid_asset_url_refs"] == [
        "L1:http://legacy.ccf.org/chart.png",
        "L2:/tmp/captura_temp.png",
        "L3:EMPTY_URL",
    ]
    assert res["is_image_hygiene_valid"] is False
    assert res["image_hygiene_posture"] == "INVALID_OR_INSECURE_ASSET_URL"


def test_audit_markdown_image_asset_hygiene_missing_or_generic_alt_text():
    """Imagen sin alt-text o con alt-text genérico ('image', 'screenshot') -> MISSING_ACCESSIBLE_ALT_TEXT."""
    from backend.services.anydoc_service import audit_markdown_image_asset_hygiene

    md = (
        "![](https://cdn.ccf.org/assets/wbs.png)\n"
        "![screenshot](https://cdn.ccf.org/assets/dashboard.png)\n"
        "![Matriz RACI aprobada](https://cdn.ccf.org/assets/raci.png)\n"
    )
    res = audit_markdown_image_asset_hygiene(md)
    assert res["total_images"] == 3
    assert res["compliant_images_count"] == 1
    assert res["missing_alt_text_refs"] == [
        "L1:https://cdn.ccf.org/assets/wbs.png",
        "L2:https://cdn.ccf.org/assets/dashboard.png",
    ]
    assert res["invalid_asset_url_refs"] == []
    assert res["is_image_hygiene_valid"] is False
    assert res["image_hygiene_posture"] == "MISSING_ACCESSIBLE_ALT_TEXT"


def test_audit_markdown_image_asset_hygiene_no_images():
    """Documento sin imágenes o None -> NO_IMAGES_FOUND."""
    from backend.services.anydoc_service import audit_markdown_image_asset_hygiene

    for payload in (None, "", "   ", "# Acta sin imágenes\n[Enlace normal](https://ccf.org)\n"):
        res = audit_markdown_image_asset_hygiene(payload)
        assert res == {
            "total_images": 0,
            "compliant_images_count": 0,
            "missing_alt_text_refs": [],
            "invalid_asset_url_refs": [],
            "is_image_hygiene_valid": True,
            "image_hygiene_posture": "NO_IMAGES_FOUND",
        }

