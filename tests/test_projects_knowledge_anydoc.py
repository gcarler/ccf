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

