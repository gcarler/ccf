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
    """Bloques de código bien formados con etiqueta de lenguaje y contenido -> is_hygienic True."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_code_fence_hygiene,
    )

    md = (
        "# Especificación Técnica\n"
        "```Python\n"
        "def calc_cpi(ev: float, ac: float) -> float:\n"
        "    return ev / ac\n"
        "```\n\n"
        "```SQL\n"
        "SELECT id, title FROM projects;\n"
        "```\n\n"
        "```python\n"
        "print('duplicado de lenguaje no repite en detected_languages')\n"
        "```\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "closed_block_count": 3,
        "detected_languages": ["python", "sql"],
        "untagged_fence_lines": [],
        "empty_code_block_lines": [],
        "has_unclosed_fence": False,
        "unclosed_fence_line": None,
        "is_hygienic": True,
    }
    assert AnyDocService.audit_markdown_code_fence_hygiene(md) == res


def test_audit_markdown_code_fence_hygiene_unclosed_fence():
    """Bloque de código sin cerrar al final del documento -> has_unclosed_fence True y unclosed_fence_line."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    md = (
        "Texto introductorio\n"
        "```mermaid\n"
        "flowchart TD\n"
        "  A --> B\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "closed_block_count": 0,
        "detected_languages": [],
        "untagged_fence_lines": [],
        "empty_code_block_lines": [],
        "has_unclosed_fence": True,
        "unclosed_fence_line": 2,
        "is_hygienic": False,
    }


def test_audit_markdown_code_fence_hygiene_untagged_and_empty_blocks():
    """Bloque sin lenguaje -> untagged_fence_lines y bloque vacío -> empty_code_block_lines."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    untagged_md = "```\necho 'sin lenguaje'\n```\n"
    untagged_res = audit_markdown_code_fence_hygiene(untagged_md)
    assert untagged_res["untagged_fence_lines"] == [1]
    assert untagged_res["empty_code_block_lines"] == []
    assert untagged_res["is_hygienic"] is False

    empty_md = "```bash\n   \n```\n"
    empty_res = audit_markdown_code_fence_hygiene(empty_md)
    assert empty_res["detected_languages"] == ["bash"]
    assert empty_res["empty_code_block_lines"] == [1]
    assert empty_res["is_hygienic"] is False


def test_audit_markdown_code_fence_hygiene_no_code_blocks():
    """Documento sin bloques de código o None -> closed_block_count 0, is_hygienic True."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    for payload in (None, "", "   ", "# Solo prosa sin bloques cercados\n"):
        res = audit_markdown_code_fence_hygiene(payload)
        assert res == {
            "closed_block_count": 0,
            "detected_languages": [],
            "untagged_fence_lines": [],
            "empty_code_block_lines": [],
            "has_unclosed_fence": False,
            "unclosed_fence_line": None,
            "is_hygienic": True,
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



def test_audit_markdown_task_checklist_governance_governed():
    """Checklist con cierres y acciones trazables -> GOVERNED_ACTION_CHECKLIST."""
    from backend.services.anydoc_service import (
        audit_markdown_task_checklist_governance as audit_fn,
    )

    res = audit_fn(
        "\n".join(
            [
                "# Actas CCB",
                "- [x] Aprobar charter firmado el 2026-09-30",
                "- [x] Publicar minutas en la wiki @secretaria",
                "- [ ] Enviar acta a patrocinadores @mediacion 2026-10-25",
                "- [ ] Agendar retro del cierre @pm",
            ]
        )
    )
    assert res["total_checklist_items"] == 4
    assert res["completed_items_count"] == 2
    assert res["open_items_count"] == 2
    assert res["completion_rate_pct"] == 50.0
    assert res["empty_task_item_lines"] == []
    assert res["untraceable_open_item_lines"] == []
    assert res["is_checklist_governed"] is True
    assert res["checklist_posture"] == "GOVERNED_ACTION_CHECKLIST"


def test_audit_markdown_task_checklist_governance_empty_item_text():
    """Ítems sin texto -> EMPTY_CHECKLIST_ITEM_TEXT (precedencia)."""
    from backend.services.anydoc_service import (
        audit_markdown_task_checklist_governance as audit_fn,
    )

    res = audit_fn(
        "\n".join(
            [
                "- [x] Cierre fiscal 2026-09-30 completado",
                "- [ ]",
                "- [ ]   ",
                "- [x] Redactar checklist final @lider",
            ]
        )
    )
    assert res["total_checklist_items"] == 4
    assert res["completed_items_count"] == 2
    assert res["open_items_count"] == 2
    assert res["empty_task_item_lines"] == [2, 3]
    assert res["untraceable_open_item_lines"] == []
    assert res["is_checklist_governed"] is False
    assert res["checklist_posture"] == "EMPTY_CHECKLIST_ITEM_TEXT"


def test_audit_markdown_task_checklist_governance_untraceable_open_items():
    """Ítems abiertos sin responsable ni fecha -> UNASSIGNED_OPEN_ACTION_ITEMS."""
    from backend.services.anydoc_service import (
        audit_markdown_task_checklist_governance as audit_fn,
    )

    res = audit_fn(
        "\n".join(
            [
                "- [x] Convocatoria aprobada @consejo",
                "- [ ] Contactar sedes nuevas",
                "- [ ] Preparar telemetria @tecnica",
                "- [ ] Rpondear peticiones sin dueño ni fecha",
            ]
        )
    )
    assert res["total_checklist_items"] == 4
    assert res["completed_items_count"] == 1
    assert res["open_items_count"] == 3
    assert res["empty_task_item_lines"] == []
    assert res["untraceable_open_item_lines"] == [2, 4]
    assert res["is_checklist_governed"] is False
    assert res["checklist_posture"] == "UNASSIGNED_OPEN_ACTION_ITEMS"


def test_audit_markdown_task_checklist_governance_empty_or_fenced():
    """> Sin ítems (o solo dentro de fences) -> NO_CHECKLIST_ITEMS."""
    from backend.services.anydoc_service import (
        audit_markdown_task_checklist_governance as audit_fn,
    )

    for payload in (None, "Sin checklist en el texto", ""):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_checklist_items": 0,
            "completed_items_count": 0,
            "open_items_count": 0,
            "completion_rate_pct": 0.0,
            "empty_task_item_lines": [],
            "untraceable_open_item_lines": [],
            "is_checklist_governed": False,
            "checklist_posture": "NO_CHECKLIST_ITEMS",
        }

    fenced = "\n".join(
        [
            "```markdown",
            "- [x] Item invisible dentro del fence",
            "```",
            "- [ ] Visible fuera del fence @responsable",
        ]
    )
    res = audit_fn(fenced)
    assert res["total_checklist_items"] == 1
    assert res["completed_items_count"] == 0
    assert res["is_checklist_governed"] is True


def test_audit_markdown_mermaid_diagram_hygiene_hygienic():
    """Bloques mermaid con cabecera válida, cuerpo y delimitadores balanceados (incluso con paréntesis entre comillas) -> HYGIENIC_MERMAID_DIAGRAMS."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_mermaid_diagram_hygiene,
    )

    md = (
        "# Arquitectura\n"
        "```mermaid\n"
        "%% Comentario inicial ignorado\n"
        "flowchart TD\n"
        '    A["Inicio (Fase 1"] --> B{"¿Aprobado [CCB]?"}\n'
        "    B -->|Sí| C[Despliegue]\n"
        "```\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    Sponsor->>PMO: Autoriza Acta\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_hygiene(md)
    assert res == {
        "total_mermaid_blocks": 2,
        "empty_mermaid_block_indices": [],
        "unsupported_diagram_type_indices": [],
        "unbalanced_delimiter_indices": [],
        "is_mermaid_hygienic": True,
        "mermaid_posture": "HYGIENIC_MERMAID_DIAGRAMS",
    }
    assert AnyDocService.audit_markdown_mermaid_diagram_hygiene(md) == res


def test_audit_markdown_mermaid_diagram_hygiene_empty_block():
    """Bloque mermaid vacío o solo con cabecera/comentarios -> EMPTY_MERMAID_BLOCK."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagram_hygiene

    md = (
        "```mermaid\n"
        "%% Solo comentario\n"
        "```\n"
        "```mermaid\n"
        "flowchart LR\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_hygiene(md)
    assert res["total_mermaid_blocks"] == 2
    assert res["empty_mermaid_block_indices"] == [1, 2]
    assert res["is_mermaid_hygienic"] is False
    assert res["mermaid_posture"] == "EMPTY_MERMAID_BLOCK"


def test_audit_markdown_mermaid_diagram_hygiene_unsupported_and_unbalanced():
    """Tipo no soportado -> UNSUPPORTED_MERMAID_DIAGRAM_TYPE; delimitadores desbalanceados -> UNBALANCED_MERMAID_DELIMITERS."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagram_hygiene

    md_unsup = (
        "```mermaid\n"
        "c4Context\n"
        "    Person(user, \"Usuario\")\n"
        "```\n"
    )
    res_unsup = audit_markdown_mermaid_diagram_hygiene(md_unsup)
    assert res_unsup["unsupported_diagram_type_indices"] == [1]
    assert res_unsup["is_mermaid_hygienic"] is False
    assert res_unsup["mermaid_posture"] == "UNSUPPORTED_MERMAID_DIAGRAM_TYPE"

    md_unbal = (
        "```mermaid\n"
        "flowchart TD\n"
        "    A[Nodo sin cerrar --> B(Destino)\n"
        "```\n"
    )
    res_unbal = audit_markdown_mermaid_diagram_hygiene(md_unbal)
    assert res_unbal["unbalanced_delimiter_indices"] == [1]
    assert res_unbal["is_mermaid_hygienic"] is False
    assert res_unbal["mermaid_posture"] == "UNBALANCED_MERMAID_DELIMITERS"


def test_audit_markdown_mermaid_diagram_hygiene_no_diagrams():
    """Texto sin bloques mermaid o None -> NO_MERMAID_DIAGRAMS."""
    from backend.services.anydoc_service import audit_markdown_mermaid_diagram_hygiene

    for payload in (None, "", "# Documento sin diagramas\n```python\nprint(1)\n```\n"):
        res = audit_markdown_mermaid_diagram_hygiene(payload)
        assert res == {
            "total_mermaid_blocks": 0,
            "empty_mermaid_block_indices": [],
            "unsupported_diagram_type_indices": [],
            "unbalanced_delimiter_indices": [],
            "is_mermaid_hygienic": False,
            "mermaid_posture": "NO_MERMAID_DIAGRAMS",
        }


def test_audit_markdown_footnote_reference_hygiene_hygienic_citations():
    """Referencias y definiciones de notas al pie emparejadas (ignorando bloques ```) -> HYGIENIC_FOOTNOTE_CITATIONS."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_footnote_reference_hygiene,
    )

    md = (
        "# Informe de Lecciones Aprendidas\n"
        "El cálculo de EVM se basa en la línea base aprobada[^pmbok-7] y el acta de CCB[^ccb-12].\n"
        "Repetimos la cita principal[^pmbok-7] para trazabilidad.\n"
        "```markdown\n"
        "Referencia ignorada en código[^fake-ref]\n"
        "[^fake-orphan]: Definición ignorada en bloque de código\n"
        "```\n"
        "\n"
        "[^pmbok-7]: PMI PMBOK Guide, Sección 7.4 Controlar los Costos.\n"
        "[^ccb-12]: Acta de Comité de Control de Cambios #12 del 2026-10-10.\n"
    )
    res = audit_markdown_footnote_reference_hygiene(md)
    assert res == {
        "total_references": 2,
        "total_definitions": 2,
        "unresolved_reference_ids": [],
        "orphan_definition_ids": [],
        "empty_footnote_definition_ids": [],
        "is_footnote_hygienic": True,
        "footnote_posture": "HYGIENIC_FOOTNOTE_CITATIONS",
    }
    assert AnyDocService.audit_markdown_footnote_reference_hygiene(md) == res


def test_audit_markdown_footnote_reference_hygiene_unresolved_references():
    """Referencia [^id] sin definición correspondiente -> UNRESOLVED_FOOTNOTE_REFERENCES."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_hygiene,
    )

    md = (
        "Hallazgo crítico documentado en auditoría[^aud-1] y anexo faltante[^missing-99].\n"
        "[^aud-1]: Informe de Auditoría Interna Q3.\n"
    )
    res = audit_markdown_footnote_reference_hygiene(md)
    assert res["total_references"] == 2
    assert res["total_definitions"] == 1
    assert res["unresolved_reference_ids"] == ["missing-99"]
    assert res["orphan_definition_ids"] == []
    assert res["empty_footnote_definition_ids"] == []
    assert res["is_footnote_hygienic"] is False
    assert res["footnote_posture"] == "UNRESOLVED_FOOTNOTE_REFERENCES"


def test_audit_markdown_footnote_reference_hygiene_empty_and_orphan_definitions():
    """Definición vacía -> EMPTY_FOOTNOTE_DEFINITIONS; definición no referenciada -> ORPHAN_FOOTNOTE_DEFINITIONS."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_hygiene,
    )

    md_empty = (
        "Texto con nota al pie sin contenido[^empty-1].\n"
        "[^empty-1]:    \n"
    )
    res_empty = audit_markdown_footnote_reference_hygiene(md_empty)
    assert res_empty["empty_footnote_definition_ids"] == ["empty-1"]
    assert res_empty["is_footnote_hygienic"] is False
    assert res_empty["footnote_posture"] == "EMPTY_FOOTNOTE_DEFINITIONS"

    md_orphan = (
        "Texto con cita válida[^ref-ok].\n"
        "[^ref-ok]: Fuente primaria verificada.\n"
        "[^unused-note]: Nota al pie huérfana nunca citada en el cuerpo.\n"
    )
    res_orphan = audit_markdown_footnote_reference_hygiene(md_orphan)
    assert res_orphan["orphan_definition_ids"] == ["unused-note"]
    assert res_orphan["is_footnote_hygienic"] is False
    assert res_orphan["footnote_posture"] == "ORPHAN_FOOTNOTE_DEFINITIONS"


def test_audit_markdown_footnote_reference_hygiene_no_footnotes():
    """Documento sin notas al pie o vacío -> NO_FOOTNOTES_PRESENT."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_hygiene,
    )

    for payload in (None, "", "# Acta simple sin notas al pie\n"):
        res = audit_markdown_footnote_reference_hygiene(payload)
        assert res == {
            "total_references": 0,
            "total_definitions": 0,
            "unresolved_reference_ids": [],
            "orphan_definition_ids": [],
            "empty_footnote_definition_ids": [],
            "is_footnote_hygienic": False,
            "footnote_posture": "NO_FOOTNOTES_PRESENT",
        }



def test_audit_markdown_internal_anchor_links_valid_navigation():
    """> Anclas internas que resuelven contra slugs de encabezado -> VALID."""
    from backend.services.anydoc_service import (
        audit_markdown_internal_anchor_links,
    )

    md = (
        "# Setup Guide\n"
        "## Configuration Reference\n"
        "Consulta [la guía de configuración](#setup-guide) y la "
        "[referencia de parámetros](#configuration-reference).\n"
    )
    res = audit_markdown_internal_anchor_links(md)
    assert res["total_headings"] == 2
    assert res["total_anchor_links"] == 2
    assert res["broken_anchor_targets"] == []
    assert res["empty_label_anchor_targets"] == []
    assert res["duplicate_heading_slugs"] == []
    assert res["is_anchor_navigation_valid"] is True
    assert res["anchor_posture"] == "VALID_INTERNAL_ANCHOR_NAVIGATION"

    from backend.services.anydoc_service import AnyDocService

    assert AnyDocService.audit_markdown_internal_anchor_links(md) == res


def test_audit_markdown_internal_anchor_links_broken_empty_and_duplicates():
    """> Ancla rota (precedencia 1), etiqueta vacía y encabezados duplicados."""
    from backend.services.anydoc_service import (
        audit_markdown_internal_anchor_links,
    )

    md = (
        "# Setup Guide\n"
        "## Setup Guide\n"
        "Enlace roto [a resolver](#missing-slug), etiqueta vacía "
        "[](#setup-guide) y otro roto [x](#NO-SLUG).\n"
    )
    res = audit_markdown_internal_anchor_links(md)
    assert res["total_headings"] == 2
    assert res["total_anchor_links"] == 3
    assert res["broken_anchor_targets"] == ["missing-slug", "no-slug"]
    assert res["empty_label_anchor_targets"] == ["setup-guide"]
    assert res["duplicate_heading_slugs"] == ["setup-guide"]
    assert res["is_anchor_navigation_valid"] is False
    assert res["anchor_posture"] == "BROKEN_INTERNAL_ANCHOR_TARGET"


    md_only_empty = (
        "# Resumen Ejecutivo\n"
        "[](#resumen-ejecutivo)\n"
    )
    res2 = audit_markdown_internal_anchor_links(md_only_empty)
    assert res2["total_anchor_links"] == 1
    assert res2["broken_anchor_targets"] == []
    assert res2["empty_label_anchor_targets"] == ["resumen-ejecutivo"]
    assert res2["anchor_posture"] == "EMPTY_ANCHOR_LINK_LABEL"


    md_only_duplicates = (
        "# Estado Financiero\n"
        "## Estado Financiero\n"
        "[corte contable](#estado-financiero)\n"
    )
    res3 = audit_markdown_internal_anchor_links(md_only_duplicates)
    assert res3["total_anchor_links"] == 1
    assert res3["broken_anchor_targets"] == []
    assert res3["empty_label_anchor_targets"] == []
    assert res3["duplicate_heading_slugs"] == ["estado-financiero"]
    assert res3["anchor_posture"] == "DUPLICATE_HEADING_ANCHOR_SLUGS"


def test_audit_markdown_internal_anchor_links_ignores_fenced_code():
    """> Encabezados y anclas dentro de bloques cercados se ignoran."""
    from backend.services.anydoc_service import (
        audit_markdown_internal_anchor_links,
    )

    md = (
        "# Reporte Mensual\n"
        "[ver detalle](#reporte-mensual)\n"
        "```bash\n"
        "# comando falso como encabezado\n"
        "grep '[fake](#no-existo)' archivo.md\n"
        "```\n"
    )
    res = audit_markdown_internal_anchor_links(md)
    assert res["total_headings"] == 1
    assert res["total_anchor_links"] == 1
    assert res["broken_anchor_targets"] == []
    assert res["empty_label_anchor_targets"] == []
    assert res["duplicate_heading_slugs"] == []
    assert res["is_anchor_navigation_valid"] is True
    assert res["anchor_posture"] == "VALID_INTERNAL_ANCHOR_NAVIGATION"


def test_audit_markdown_internal_anchor_links_no_anchors():
    """> None, vacío o documento sin anclas internas -> NO_INTERNAL_ANCHORS."""
    from backend.services.anydoc_service import (
        audit_markdown_internal_anchor_links,
    )

    for payload in (None, "", "# Solo encabezados, sin anclas\n"):
        res = audit_markdown_internal_anchor_links(payload)  # type: ignore[arg-type]
        assert res == {
            "total_headings": 1 if isinstance(payload, str) and payload else 0,
            "total_anchor_links": 0,
            "broken_anchor_targets": [],
            "empty_label_anchor_targets": [],
            "duplicate_heading_slugs": [],
            "is_anchor_navigation_valid": False,
            "anchor_posture": "NO_INTERNAL_ANCHORS",
        }


def test_audit_markdown_code_fence_hygiene_info_string_with_attributes():
    """Info-string con atributos adicionales tras el lenguaje extrae solo el primer token en minúsculas."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    md = (
        "```TypeScript title=\"api.ts\" {1-3}\n"
        "export const cpi = 1.05;\n"
        "```\n"
        "```JSON\n"
        "{\"ok\": true}\n"
        "```\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "closed_block_count": 2,
        "detected_languages": ["typescript", "json"],
        "untagged_fence_lines": [],
        "empty_code_block_lines": [],
        "has_unclosed_fence": False,
        "unclosed_fence_line": None,
        "is_hygienic": True,
    }


def test_audit_markdown_code_fence_hygiene_multiple_violations_combined():
    """Combina bloque sin lenguaje, bloque vacío y bloque final sin cerrar."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    md = (
        "```\n"
        "echo 'bloque 1 sin tag'\n"
        "```\n"
        "```yaml\n"
        "\n"
        "```\n"
        "```sql\n"
        "SELECT 1;\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "closed_block_count": 2,
        "detected_languages": ["yaml"],
        "untagged_fence_lines": [1],
        "empty_code_block_lines": [4],
        "has_unclosed_fence": True,
        "unclosed_fence_line": 7,
        "is_hygienic": False,
    }


def test_audit_markdown_code_fence_hygiene_indented_fences():
    """Bloques cercados con sangría en listas son detectados tras strip()."""
    from backend.services.anydoc_service import audit_markdown_code_fence_hygiene

    md = (
        "- Paso 1:\n"
        "  ```bash\n"
        "  pytest -q\n"
        "  ```\n"
    )
    res = audit_markdown_code_fence_hygiene(md)
    assert res == {
        "closed_block_count": 1,
        "detected_languages": ["bash"],
        "untagged_fence_lines": [],
        "empty_code_block_lines": [],
        "has_unclosed_fence": False,
        "unclosed_fence_line": None,
        "is_hygienic": True,
    }


def test_audit_markdown_internal_anchor_links_and_code_fence_coexistence():
    """Verifica coexistencia de audit_markdown_internal_anchor_links y audit_markdown_code_fence_hygiene sobre el mismo artefacto."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_hygiene,
        audit_markdown_internal_anchor_links,
    )

    md = (
        "# Plan de Gestión\n"
        "## Arquitectura Base\n"
        "Ver [sección técnica](#arquitectura-base).\n"
        "```python\n"
        "assert True\n"
        "```\n"
    )
    anchor_res = audit_markdown_internal_anchor_links(md)
    fence_res = audit_markdown_code_fence_hygiene(md)
    assert anchor_res["is_anchor_navigation_valid"] is True
    assert fence_res["is_hygienic"] is True


def test_audit_markdown_callout_admonition_hygiene_valid_separated_callouts():
    """Callouts canónicos separados por línea en blanco y con cuerpo válido pasan is_hygienic=True."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_callout_admonition_hygiene,
    )

    md = (
        "# Guía Operativa\n"
        "> [!NOTE]\n"
        "> Esta nota documenta el supuesto base del cronograma.\n"
        "\n"
        "> [!WARNING] Riesgo de corte eléctrico en ventana de mantenimiento.\n"
        "\n"
        "```markdown\n"
        "> [!INVALID_IN_CODE]\n"
        "```\n"
    )
    res = audit_markdown_callout_admonition_hygiene(md)
    assert res == {
        "valid_callout_count": 2,
        "detected_callout_types": ["NOTE", "WARNING"],
        "unsupported_callout_type_lines": [],
        "empty_callout_body_lines": [],
        "consecutive_unseparated_callout_lines": [],
        "is_hygienic": True,
    }
    assert AnyDocService.audit_markdown_callout_admonition_hygiene(md) == res


def test_audit_markdown_callout_admonition_hygiene_unsupported_and_empty_body():
    """Detecta tipos fuera de los 5 canónicos y bloques de alerta sin texto explicativo."""
    from backend.services.anydoc_service import (
        audit_markdown_callout_admonition_hygiene,
    )

    md = (
        "> [!DANGER]\n"
        "> Alerta con etiqueta no estándar.\n"
        "\n"
        "> [!IMPORTANT]\n"
        ">\n"
        "\n"
        "> [!CAUTION]\n"
    )
    res = audit_markdown_callout_admonition_hygiene(md)
    assert res == {
        "valid_callout_count": 2,
        "detected_callout_types": ["IMPORTANT", "CAUTION"],
        "unsupported_callout_type_lines": [1],
        "empty_callout_body_lines": [4, 7],
        "consecutive_unseparated_callout_lines": [],
        "is_hygienic": False,
    }


def test_audit_markdown_callout_admonition_hygiene_consecutive_unseparated():
    """Detecta callouts consecutivos sin línea en blanco intermedia."""
    from backend.services.anydoc_service import (
        audit_markdown_callout_admonition_hygiene,
    )

    md = (
        "> [!NOTE]\n"
        "> Primer aviso con cuerpo.\n"
        "> [!TIP]\n"
        "> Segundo aviso pegado en el mismo blockquote.\n"
    )
    res = audit_markdown_callout_admonition_hygiene(md)
    assert res == {
        "valid_callout_count": 2,
        "detected_callout_types": ["NOTE", "TIP"],
        "unsupported_callout_type_lines": [],
        "empty_callout_body_lines": [],
        "consecutive_unseparated_callout_lines": [3],
        "is_hygienic": False,
    }


def test_audit_markdown_callout_admonition_hygiene_empty_or_no_callouts():
    """Texto vacío, None o sin callouts retorna contadores en cero e is_hygienic=True."""
    from backend.services.anydoc_service import (
        audit_markdown_callout_admonition_hygiene,
    )

    for payload in (None, "", "# Solo título\n\n> Cita normal sin callout.\n"):
        assert audit_markdown_callout_admonition_hygiene(payload) == {
            "valid_callout_count": 0,
            "detected_callout_types": [],
            "unsupported_callout_type_lines": [],
            "empty_callout_body_lines": [],
            "consecutive_unseparated_callout_lines": [],
            "is_hygienic": True,
        }



def test_audit_markdown_table_column_alignment_hygiene_clean_tables():
    """Tablas GFM limpias (alineaciones :---, :---:, ---:) e ignores en fences -> clean."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_alignment_hygiene,
        AnyDocService,
    )

    md = (
        "| Activo | Fecha | Importe |\n"
        "| :--- | :---: | ---: |\n"
        "| Caja | 2026-10-18 | 500 |\n"
        "\n"
        "Texto entre tablas.\n"
        "\n"
        "| Estado | Nota |\n"
        "| :--- | :--- |\n"
        "| OK | - |\n"
        "```markdown\n"
        "| Falso | Encabezado |\n"
        "| a | b |\n"
        "```\n"
    )
    res = audit_markdown_table_column_alignment_hygiene(md)
    assert res["total_tables"] == 2
    assert res["malformed_delimiter_table_indices"] == []
    assert res["empty_header_cell_table_indices"] == []
    assert res["ragged_column_table_indices"] == []
    assert res["is_table_hygiene_clean"] is True

    static_res = AnyDocService.audit_markdown_table_column_alignment_hygiene(
        "| A | B |\n| :--- | ---: |\n| 1 | 2 |\n"
    )
    assert static_res["is_table_hygiene_clean"] is True
    assert static_res["total_tables"] == 1


def test_audit_markdown_table_column_alignment_hygiene_malformed_delimiters():
    """Delimitador con <3 guiones o bloque sin fila delimitadora -> malformed."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_alignment_hygiene,
    )

    md = (
        "| Activo | Fecha |\n"
        "| :-- | --- |\n"
        "| Caja | 1 |\n"
        "\n"
        "| Sin delimitador | X |\n"
        "| 1 | 2 |\n"
    )
    res = audit_markdown_table_column_alignment_hygiene(md)
    assert res["total_tables"] == 2
    assert res["malformed_delimiter_table_indices"] == [1, 2]
    assert res["empty_header_cell_table_indices"] == []
    assert res["ragged_column_table_indices"] == []
    assert res["is_table_hygiene_clean"] is False


def test_audit_markdown_table_column_alignment_hygiene_empty_header_and_ragged():
    """Encabezado vacío y filas ragged -> listas separadas por tabla."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_alignment_hygiene,
    )

    md = (
        "| Activo |  | Importe |\n"
        "| --- | --- | --- |\n"
        "| Caja | 1 | 2 |\n"
        "\n"
        "| Activo | Fecha |\n"
        "| --- | --- |\n"
        "| Caja | 1 | extra |\n"
        "| Corto |\n"
        "\n"
        "| Solo header |\n"
    )
    res = audit_markdown_table_column_alignment_hygiene(md)
    assert res["total_tables"] == 3
    assert res["empty_header_cell_table_indices"] == [1]
    assert res["ragged_column_table_indices"] == [2]
    assert res["malformed_delimiter_table_indices"] == [3]
    assert res["is_table_hygiene_clean"] is False


def test_audit_markdown_table_column_alignment_hygiene_no_tables():
    """None, vacío o texto sin tablas -> total 0 y clean True."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_alignment_hygiene,
    )

    for payload in (None, "", "Texto sin tablas GFM.\n", "| sin cierre\n", None):
        res = audit_markdown_table_column_alignment_hygiene(payload)
        assert res == {
            "total_tables": 0,
            "malformed_delimiter_table_indices": [],
            "empty_header_cell_table_indices": [],
            "ragged_column_table_indices": [],
            "is_table_hygiene_clean": True,
        }


def test_audit_markdown_task_list_checklist_hygiene_clean_and_assigned():
    """Items con sintaxis válida y tareas abiertas con responsable (@ o owner:) pasan is_checklist_hygiene_clean=True."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_task_list_checklist_hygiene,
    )

    md = (
        "# Checklist de Liberación\n"
        "- [x] Congelar rama de release\n"
        "- [X] Ejecutar pruebas de regresión\n"
        "- [ ] Validar backup de base de datos @dba-team\n"
        "* [ ] Confirmar ventana de cambio owner: pmo-lead\n"
        "```markdown\n"
        "- [?] Ignorado dentro de bloque cercado\n"
        "- [ ] Sin dueño pero en código\n"
        "```\n"
    )
    res = audit_markdown_task_list_checklist_hygiene(md)
    assert res == {
        "total_task_items": 4,
        "completed_task_items": 2,
        "completion_rate_pct": 50.0,
        "invalid_checkbox_syntax_lines": [],
        "empty_task_description_lines": [],
        "unassigned_open_task_lines": [],
        "is_checklist_hygiene_clean": True,
    }
    assert AnyDocService.audit_markdown_task_list_checklist_hygiene(md) == res


def test_audit_markdown_task_list_checklist_hygiene_invalid_mark_and_empty_body():
    """Detecta marcas fuera de {' ', 'x', 'X'} y descripciones vacías."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_hygiene,
    )

    md = (
        "- [?] Tarea con estado ambiguo @dev\n"
        "- [x]   \n"
        "+ [ ]   \n"
    )
    res = audit_markdown_task_list_checklist_hygiene(md)
    assert res == {
        "total_task_items": 3,
        "completed_task_items": 1,
        "completion_rate_pct": 33.33,
        "invalid_checkbox_syntax_lines": [1],
        "empty_task_description_lines": [2, 3],
        "unassigned_open_task_lines": [],
        "is_checklist_hygiene_clean": False,
    }


def test_audit_markdown_task_list_checklist_hygiene_unassigned_open_tasks():
    """Detecta tareas abiertas sin responsable (@usuario ni owner:)."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_hygiene,
    )

    md = (
        "- [x] Tarea ya completada sin mención\n"
        "- [ ] Tarea huérfana pendiente de revisión\n"
        "- [ ] Segunda tarea abierta sin responsable\n"
    )
    res = audit_markdown_task_list_checklist_hygiene(md)
    assert res == {
        "total_task_items": 3,
        "completed_task_items": 1,
        "completion_rate_pct": 33.33,
        "invalid_checkbox_syntax_lines": [],
        "empty_task_description_lines": [],
        "unassigned_open_task_lines": [2, 3],
        "is_checklist_hygiene_clean": False,
    }


def test_audit_markdown_task_list_checklist_hygiene_empty_or_none():
    """Texto vacío, None o sin items de checklist retorna contadores en 0 e is_checklist_hygiene_clean=True."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_hygiene,
    )

    for payload in (None, "", "# Solo texto\n- Viñeta normal sin checkbox\n"):
        assert audit_markdown_task_list_checklist_hygiene(payload) == {
            "total_task_items": 0,
            "completed_task_items": 0,
            "completion_rate_pct": 0.0,
            "invalid_checkbox_syntax_lines": [],
            "empty_task_description_lines": [],
            "unassigned_open_task_lines": [],
            "is_checklist_hygiene_clean": True,
        }


def test_audit_markdown_heading_hierarchy_and_duplicates_clean():
    """Jerarquía H1 -> H2 -> H3 sin saltos, vacíos ni duplicados (ignorando bloques cercados)."""
    from backend.services.anydoc_service import (
        AnydocService,
        audit_markdown_heading_hierarchy_and_duplicates,
    )

    md = (
        "# Plan de Dirección del Proyecto\n"
        "## Alcance y Entregables\n"
        "### Estructura de Desglose del Trabajo ###\n"
        "## Cronograma Maestro\n"
        "```markdown\n"
        "# Segundo H1 dentro de código ignorado\n"
        "#### Salto de nivel en código ignorado\n"
        "##\n"
        "```\n"
    )
    res = audit_markdown_heading_hierarchy_and_duplicates(md)
    assert res == {
        "total_headings": 4,
        "h1_count": 1,
        "skipped_level_lines": [],
        "empty_heading_lines": [],
        "duplicate_heading_lines": [],
        "is_heading_hierarchy_clean": True,
    }
    assert AnydocService.audit_markdown_heading_hierarchy_and_duplicates(md) == res


def test_audit_markdown_heading_hierarchy_and_duplicates_multiple_h1_and_skipped_levels():
    """Múltiples H1 y saltos de nivel (ej. H1 -> H3, H2 -> H4) -> is_heading_hierarchy_clean=False."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicates,
    )

    md = (
        "# Acta de Constitución\n"
        "### Riesgos de Alto Nivel\n"
        "# Segundo H1 Indebido\n"
        "## Presupuesto\n"
        "#### Reserva de Contingencia\n"
    )
    res = audit_markdown_heading_hierarchy_and_duplicates(md)
    assert res == {
        "total_headings": 5,
        "h1_count": 2,
        "skipped_level_lines": [2, 5],
        "empty_heading_lines": [],
        "duplicate_heading_lines": [],
        "is_heading_hierarchy_clean": False,
    }


def test_audit_markdown_heading_hierarchy_and_duplicates_empty_and_duplicate_titles():
    """Encabezados sin título o duplicados en el mismo nivel (case-insensitive) se reportan por línea."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicates,
    )

    md = (
        "# Informe de Estado\n"
        "##   \n"
        "## Matriz de Riesgos\n"
        "### matriz de riesgos\n"
        "## MATRIZ DE RIESGOS ###\n"
        "### ###\n"
    )
    res = audit_markdown_heading_hierarchy_and_duplicates(md)
    assert res == {
        "total_headings": 6,
        "h1_count": 1,
        "skipped_level_lines": [],
        "empty_heading_lines": [2, 6],
        "duplicate_heading_lines": [5],
        "is_heading_hierarchy_clean": False,
    }


def test_audit_markdown_heading_hierarchy_and_duplicates_empty_or_non_string():
    """Entrada None, vacía o no string retorna contadores en 0 e is_heading_hierarchy_clean=True."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicates,
    )

    for payload in (None, "", 123, ["### heading"]):
        assert audit_markdown_heading_hierarchy_and_duplicates(payload) == {  # type: ignore[arg-type]
            "total_headings": 0,
            "h1_count": 0,
            "skipped_level_lines": [],
            "empty_heading_lines": [],
            "duplicate_heading_lines": [],
            "is_heading_hierarchy_clean": True,
        }


def test_audit_markdown_external_url_scheme_hygiene_clean():
    """Enlaces HTTPS, localhost, rutas relativas e imágenes ignoradas pasan is_url_hygiene_clean=True."""
    from backend.services.anydoc_service import (
        AnydocService,
        audit_markdown_external_url_scheme_hygiene,
    )

    md = (
        "# Referencias del Proyecto\n"
        "- [Portal PMI](https://www.pmi.org/pmbok-guide-standards)\n"
        "- [Entorno Local](http://localhost:8000/docs)\n"
        "- [Loopback](http://127.0.0.1:3000/plataforma)\n"
        "- [Guía Interna](/plataforma/proyectos/wiki)\n"
        "![Diagrama](http://inseguro-pero-imagen.org/logo.png)\n"
        "```markdown\n"
        "[Ignorado en código](javascript:alert(1))\n"
        "[HTTP en código](http://sitio-inseguro.org)\n"
        "```\n"
    )
    res = audit_markdown_external_url_scheme_hygiene(md)
    assert res == {
        "total_links": 4,
        "insecure_http_lines": [],
        "dangerous_scheme_lines": [],
        "empty_label_lines": [],
        "placeholder_url_lines": [],
        "is_url_hygiene_clean": True,
    }
    assert AnydocService.audit_markdown_external_url_scheme_hygiene(md) == res


def test_audit_markdown_external_url_scheme_hygiene_insecure_and_dangerous():
    """Detecta enlaces http:// externos y esquemas peligrosos (javascript:, vbscript:, data:)."""
    from backend.services.anydoc_service import (
        audit_markdown_external_url_scheme_hygiene,
    )

    md = (
        "[Proveedor Legacy](http://proveedor-externo.org/api)\n"
        "[Exploit XSS](javascript:alert('xss'))\n"
        "[Payload Data](data:text/html;base64,PHNjcmlwdD4=)\n"
    )
    res = audit_markdown_external_url_scheme_hygiene(md)
    assert res == {
        "total_links": 3,
        "insecure_http_lines": [1],
        "dangerous_scheme_lines": [2, 3],
        "empty_label_lines": [],
        "placeholder_url_lines": [],
        "is_url_hygiene_clean": False,
    }


def test_audit_markdown_external_url_scheme_hygiene_empty_label_and_placeholders():
    """Detecta etiquetas vacías y URLs placeholder (#, todo, tbd, example.com o vacías)."""
    from backend.services.anydoc_service import (
        audit_markdown_external_url_scheme_hygiene,
    )

    md = (
        "[   ](https://ccf.org/doc)\n"
        "[Pendiente Ancla](#)\n"
        "[Por definir](TBD)\n"
        "[Dominio Demo](https://api.example.com/v1)\n"
        "[Sin Destino](   )\n"
    )
    res = audit_markdown_external_url_scheme_hygiene(md)
    assert res == {
        "total_links": 5,
        "insecure_http_lines": [],
        "dangerous_scheme_lines": [],
        "empty_label_lines": [1],
        "placeholder_url_lines": [2, 3, 4, 5],
        "is_url_hygiene_clean": False,
    }


def test_audit_markdown_external_url_scheme_hygiene_empty_or_non_string():
    """Entrada None, vacía o no string retorna total_links=0 e is_url_hygiene_clean=True."""
    from backend.services.anydoc_service import (
        audit_markdown_external_url_scheme_hygiene,
    )

    for payload in (None, "", 42, ["[link](http://bad.com)"]):
        assert audit_markdown_external_url_scheme_hygiene(payload) == {  # type: ignore[arg-type]
            "total_links": 0,
            "insecure_http_lines": [],
            "dangerous_scheme_lines": [],
            "empty_label_lines": [],
            "placeholder_url_lines": [],
            "is_url_hygiene_clean": True,
        }


def test_audit_markdown_admonition_callout_hygiene_healthy_with_fenced_code_ignored():
    """Documento con alertas válidas bien separadas y ejemplos ignorados dentro de bloques de código -> healthy."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_hygiene,
    )

    md = (
        "# Guía Operativa PMI\n"
        "> [!NOTE]\n"
        "> Esta nota documenta el alcance de la línea base.\n"
        "\n"
        "Párrafo separador entre alertas.\n"
        "\n"
        "> [!IMPORTANT] Revisar criterios de aceptación antes del Gate.\n"
        "\n"
        "```markdown\n"
        "> [!DANGER]\n"
        ">> [!NOTE] Anidado en código ignorado\n"
        "```\n"
    )
    res = audit_markdown_admonition_callout_hygiene(md)
    assert res == {
        "total_alerts": 2,
        "valid_alerts_count": 2,
        "unsupported_alert_types": [],
        "empty_alert_lines": [],
        "nested_alert_lines": [],
        "consecutive_alert_lines": [],
        "is_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_markdown_admonition_callout_hygiene_unsupported_and_empty_critical():
    """Detecta tipo de alerta no soportado (> [!DANGER]) y bloque vacío (> [!WARNING] sin cuerpo) -> critical."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_hygiene,
    )

    md = (
        "> [!DANGER]\n"
        "> Tipo fuera del estándar GitHub.\n"
        "\n"
        "> [!WARNING]\n"
        ">   \n"
    )
    res = audit_markdown_admonition_callout_hygiene(md)
    assert res["total_alerts"] == 2
    assert res["valid_alerts_count"] == 0
    assert res["unsupported_alert_types"] == ["DANGER"]
    assert res["empty_alert_lines"] == [4]
    assert res["is_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 2


def test_audit_markdown_admonition_callout_hygiene_consecutive_and_nested_warning():
    """Detecta alertas consecutivas sin separador y alertas anidadas (>> [!NOTE]) -> warning."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_hygiene,
    )

    md = (
        "> [!NOTE]\n"
        "> Primera alerta válida.\n"
        "> [!TIP]\n"
        "> Segunda alerta consecutiva en el mismo blockquote.\n"
        "\n"
        ">> [!CAUTION]\n"
        ">> Alerta anidada no permitida.\n"
    )
    res = audit_markdown_admonition_callout_hygiene(md)
    assert res["total_alerts"] == 3
    assert res["valid_alerts_count"] == 1
    assert res["unsupported_alert_types"] == []
    assert res["empty_alert_lines"] == []
    assert res["consecutive_alert_lines"] == [3]
    assert res["nested_alert_lines"] == [6]
    assert res["is_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_audit_markdown_admonition_callout_hygiene_via_service_staticmethod():
    """Verifica invocación desde AnydocService.audit_markdown_admonition_callout_hygiene."""
    from backend.services.anydoc_service import (
        AnydocService,
        audit_markdown_admonition_callout_hygiene,
    )

    md = "> [!CAUTION]\n> Acción irreversible sobre la línea base.\n"
    assert (
        AnydocService.audit_markdown_admonition_callout_hygiene(md)
        == audit_markdown_admonition_callout_hygiene(md)
    )


def test_audit_markdown_frontmatter_metadata_hygiene_healthy():
    """Verifica frontmatter YAML completo y válido según PMI PMBOK §4.4 y §10.2."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_hygiene,
    )

    md = (
        "---\n"
        "# Cabecera de gobernanza documental\n"
        'title: "Plan de Gestión del Alcance"\n'
        "owner: pmo.lead@ccf.org\n"
        "version: '2.1.0'\n"
        "status: approved\n"
        "---\n\n"
        "# Introducción\n"
        "Contenido del documento.\n"
    )
    res = audit_markdown_frontmatter_metadata_hygiene(md)
    assert res == {
        "has_valid_frontmatter": True,
        "parsed_keys_count": 4,
        "missing_required_keys": [],
        "duplicate_keys": [],
        "invalid_lifecycle_status": False,
        "is_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_markdown_frontmatter_metadata_hygiene_critical_missing_or_placeholder():
    """Detecta ausencia de frontmatter o campos obligatorios vacíos/placeholder (critical)."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_hygiene,
    )

    res_no_fm = audit_markdown_frontmatter_metadata_hygiene("# Documento sin frontmatter\nTexto.")
    assert res_no_fm["has_valid_frontmatter"] is False
    assert res_no_fm["parsed_keys_count"] == 0
    assert res_no_fm["missing_required_keys"] == ["title", "owner", "version", "status"]
    assert res_no_fm["is_compliant"] is False
    assert res_no_fm["status"] == "critical"
    assert len(res_no_fm["recommendations"]) >= 1

    md_placeholders = (
        "---\n"
        "title: Acta de Constitución\n"
        "owner: TBD\n"
        "version: \n"
        "status: in_review\n"
        "...\n"
        "Cuerpo.\n"
    )
    res_ph = audit_markdown_frontmatter_metadata_hygiene(md_placeholders)
    assert res_ph["has_valid_frontmatter"] is True
    assert res_ph["parsed_keys_count"] == 4
    assert res_ph["missing_required_keys"] == ["owner", "version"]
    assert res_ph["duplicate_keys"] == []
    assert res_ph["invalid_lifecycle_status"] is False
    assert res_ph["is_compliant"] is False
    assert res_ph["status"] == "critical"
    assert len(res_ph["recommendations"]) == 1


def test_audit_markdown_frontmatter_metadata_hygiene_warning_duplicates_and_lifecycle():
    """Detecta claves duplicadas en frontmatter o status fuera del ciclo de vida permitido (warning)."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_hygiene,
    )

    md = (
        "\n"
        "---\n"
        "title: Matriz RACI\n"
        "owner: dir.proyectos@ccf.org\n"
        "owner: coord.calidad@ccf.org\n"
        "version: 1.0\n"
        "status: experimental_beta\n"
        "---\n"
        "# RACI\n"
    )
    res = audit_markdown_frontmatter_metadata_hygiene(md)
    assert res["has_valid_frontmatter"] is True
    assert res["parsed_keys_count"] == 5
    assert res["missing_required_keys"] == []
    assert res["duplicate_keys"] == ["owner"]
    assert res["invalid_lifecycle_status"] is True
    assert res["is_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_audit_markdown_frontmatter_metadata_hygiene_via_service_staticmethod():
    """Verifica invocación desde AnydocService.audit_markdown_frontmatter_metadata_hygiene."""
    from backend.services.anydoc_service import (
        AnydocService,
        audit_markdown_frontmatter_metadata_hygiene,
    )

    md = (
        "---\n"
        "title: Plan de Calidad\n"
        "owner: qa@ccf.org\n"
        "version: 1.0.0\n"
        "status: baselined\n"
        "---\n"
    )
    assert (
        AnydocService.audit_markdown_frontmatter_metadata_hygiene(md)
        == audit_markdown_frontmatter_metadata_hygiene(md)
    )


def test_audit_markdown_image_alt_text_and_asset_hygiene_healthy_and_fences_ignored():
    """Imágenes con alt descriptivo y rutas válidas + ejemplos ignorados en bloques de código -> healthy."""
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "# Arquitectura de Solución\n"
        '![Diagrama de red de cronograma PDM](https://cdn.ccf.org/pmo/pdm-network.svg "Red PDM")\n'
        "![Flujo de aprobación CCB](<assets/ccb approval flow.png>)\n"
        "```markdown\n"
        "![image](javascript:alert(1))\n"
        "![]()\n"
        "```\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md)
    assert res == {
        "total_images": 2,
        "valid_images_count": 2,
        "missing_or_generic_alt_lines": [],
        "invalid_asset_targets": [],
        "is_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_markdown_image_alt_text_and_asset_hygiene_warning_missing_or_generic_alt():
    """Imágenes sin alt, con alt corto, genérico o nombre de archivo -> warning."""
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "![](https://cdn.ccf.org/a.png)\n"
        "![image](https://cdn.ccf.org/b.png)\n"
        "![diagram.png](https://cdn.ccf.org/c.png)\n"
        "![Matriz RACI aprobada](https://cdn.ccf.org/raci.png)\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md)
    assert res["total_images"] == 4
    assert res["valid_images_count"] == 1
    assert res["missing_or_generic_alt_lines"] == [1, 2, 3]
    assert res["invalid_asset_targets"] == []
    assert res["is_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 1


def test_audit_markdown_image_alt_text_and_asset_hygiene_critical_invalid_targets():
    """Imágenes con target vacío, javascript:/file://, ruta Windows o espacios sin <...> -> critical."""
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "![Curva S de Valor Ganado]()\n"
        "![Organigrama del proyecto](javascript:evil())\n"
        "![Acta escaneada](file:///etc/passwd)\n"
        "![Cronograma maestro](C:\\Users\\pmo\\gantt.png)\n"
        "![Estructura de Desglose del Trabajo](assets/wbs tree diagram.png)\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md)
    assert res["total_images"] == 5
    assert res["valid_images_count"] == 0
    assert res["missing_or_generic_alt_lines"] == []
    assert res["invalid_asset_targets"] == [
        "<empty>",
        "javascript:evil()",
        "file:///etc/passwd",
        "C:\\Users\\pmo\\gantt.png",
        "assets/wbs tree diagram.png",
    ]
    assert res["is_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 1


def test_audit_markdown_image_alt_text_and_asset_hygiene_via_service_staticmethod():
    """Verifica invocación vía AnydocService.audit_markdown_image_alt_text_and_asset_hygiene."""
    from backend.services.anydoc_service import (
        AnydocService,
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = "![Histograma de recursos críticos](https://cdn.ccf.org/pmo/resources.webp)\n"
    assert (
        AnydocService.audit_markdown_image_alt_text_and_asset_hygiene(md)
        == audit_markdown_image_alt_text_and_asset_hygiene(md)
    )


def test_audit_markdown_code_fence_hygiene_compliant_blocks():
    """Bloques etiquetados, cortos, sin secretos y cerrados -> compliant."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_language_and_secret_hygiene,
    )

    doc = (
        "Intro.\n"
        "\n"
        "```python\n"
        'print("hola")\n'
        "```\n"
        "\n"
        "~~~sql\n"
        "SELECT 1;\n"
        "~~~\n"
        "\n"
        "Fin.\n"
    )
    res = audit_markdown_code_fence_language_and_secret_hygiene(doc)
    assert res == {
        "total_code_blocks": 2,
        "unlabeled_language_block_lines": [],
        "oversized_block_lines": [],
        "suspected_secret_block_lines": [],
        "unclosed_fence_line": None,
        "is_code_fence_hygiene_compliant": True,
    }


def test_audit_markdown_code_fence_unlabeled_and_oversized():
    """Bloques sin etiqueta de lenguaje y bloques que exceden max_lines_per_block."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_language_and_secret_hygiene,
    )

    doc = (
        "```\n"
        "sin etiqueta\n"
        "```\n"
        "\n"
        "```js\n"
        "a\n"
        "b\n"
        "c\n"
        "```\n"
    )
    res = audit_markdown_code_fence_language_and_secret_hygiene(doc, max_lines_per_block=2)
    assert res["total_code_blocks"] == 2
    assert res["unlabeled_language_block_lines"] == [1]
    assert res["oversized_block_lines"] == [5]
    assert res["is_code_fence_hygiene_compliant"] is False

    # Con el maximo por defecto (80) el segundo bloque ya no es oversized.
    ok = audit_markdown_code_fence_language_and_secret_hygiene(doc)
    assert ok["oversized_block_lines"] == []
    assert ok["unlabeled_language_block_lines"] == [1]


def test_audit_markdown_code_fence_secret_leak_detection():
    """Detecta credenciales expuestas e ignora placeholders REDACTED/EXAMPLE/YOUR_/</***."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_language_and_secret_hygiene,
    )

    leaky_bits = (
        ('```bash\napi_key=abc123realkey\n```\n', 'api_key='), 
        ('```yaml\nsecret_key=deadbeef1234\n```\n', 'secret_key='),
        ('```sh\ntoken=ghp_abcdefghijklmnopqrst1234\n```\n', 'ghp_'),
        ('```json\nAuthorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\n```\n', 'bearer'),
        ('```pem\n-----BEGIN RSA PRIVATE KEY-----\n```\n', '-----begin '),
        ('```env\naws_secret_access_key=wJalrXUtnFEMI\n```\n', 'aws_secret_access_key='),
    )
    for doc, hint in leaky_bits:
        res = audit_markdown_code_fence_language_and_secret_hygiene(doc)
        assert res["suspected_secret_block_lines"] == [1], (hint, res)
        assert res["is_code_fence_hygiene_compliant"] is False

    # Placeholders que contienen REDACTED, EXAMPLE, YOUR_, < o *** no se reportan.
    placeholders = (
        "```bash\napi_key=REDACTED\n```\n", 
        "```py\npassword=EXAMPLE_PLACEHOLDER\n```\n", 
        "```env\nDB_PASSWORD=YOUR_SECRET_HERE\n```\n", 
        "```env\nTOKEN=<paste-your-token>\n```\n", 
        "```env\nAWS_SECRET_ACCESS_KEY=***\n```\n", 
    )
    for doc in placeholders:
        res = audit_markdown_code_fence_language_and_secret_hygiene(doc)
        assert res["suspected_secret_block_lines"] == [], res
        assert res["is_code_fence_hygiene_compliant"] is True


def test_audit_markdown_code_fence_unclosed_and_scope():
    """Bloque sin cerrar; entradas vacias/None y limpieza sanitaria del escaneo."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_language_and_secret_hygiene,
    )

    doc = "# Documento de gobierno\n\n```text\ncontenido sin cerrar\n"
    res = audit_markdown_code_fence_language_and_secret_hygiene(doc)
    assert res["unclosed_fence_line"] == 3
    assert res["is_code_fence_hygiene_compliant"] is False

    empty = {
        "total_code_blocks": 0,
        "unlabeled_language_block_lines": [],
        "oversized_block_lines": [],
        "suspected_secret_block_lines": [],
        "unclosed_fence_line": None,
        "is_code_fence_hygiene_compliant": True,
    }
    for payload in (None, "", "   \n  ", 42, ["x"]):
        assert audit_markdown_code_fence_language_and_secret_hygiene(payload) == empty

    import backend.services.anydoc_service as _m
    assert "audit_markdown_code_fence_language_and_secret_hygiene" in _m.__all__


def test_audit_markdown_blockquote_depth_and_citation_hygiene_compliant():
    """Valida citas con atribución explícita, anidamiento permitido e ignora admonitions y code fences."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_blockquote_depth_and_citation_hygiene,
    )

    doc = (
        "# Acta de Gobernanza\n\n"
        "> [!NOTE]\n"
        "> Esta alerta no se contabiliza como blockquote estándar.\n\n"
        "> El control integrado de cambios según PMBOK §4.6 exige trazabilidad formal.\n"
        "> > Nota complementaria de segundo nivel.\n\n"
        "```markdown\n"
        "> > > > Bloque dentro de code fence ignorado\n"
        "```\n"
    )
    res = audit_markdown_blockquote_depth_and_citation_hygiene(
        doc, max_nesting_depth=2
    )
    assert res == {
        "total_blockquote_blocks": 1,
        "excessive_nesting_block_lines": [],
        "empty_blockquote_block_lines": [],
        "unattributed_normative_quote_lines": [],
        "is_blockquote_hygiene_compliant": True,
    }
    assert (
        AnyDocService.audit_markdown_blockquote_depth_and_citation_hygiene(doc)
        == res
    )


def test_audit_markdown_blockquote_excessive_nesting_and_empty_blocks():
    """Detecta bloques con anidamiento superior a max_nesting_depth y blockquotes vacíos."""
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_depth_and_citation_hygiene,
    )

    doc = (
        "> Nivel 1\n"
        "> > Nivel 2\n"
        "> > > Nivel 3 excesivo\n\n"
        ">    \n"
        "> >   \n"
    )
    res = audit_markdown_blockquote_depth_and_citation_hygiene(
        doc, max_nesting_depth=2
    )
    assert res["total_blockquote_blocks"] == 2
    assert res["excessive_nesting_block_lines"] == [1]
    assert res["empty_blockquote_block_lines"] == [5]
    assert res["unattributed_normative_quote_lines"] == []
    assert res["is_blockquote_hygiene_compliant"] is False


def test_audit_markdown_blockquote_unattributed_normative_quotes():
    """Exige marcador de atribución cuando un blockquote cita normas (PMBOK, ISO, IEEE, cláusula, artículo)."""
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_depth_and_citation_hygiene,
    )

    doc = (
        "> Según el estándar PMBOK toda línea base requiere aprobación del comité.\n\n"
        "> La cláusula de penalización aplica tras 15 días de mora — Fuente: Contrato Marco.\n\n"
        "> El estándar ISO 21502 define la gobernanza de proyectos sin referencia explícita.\n"
    )
    res = audit_markdown_blockquote_depth_and_citation_hygiene(doc)
    assert res["total_blockquote_blocks"] == 3
    assert res["excessive_nesting_block_lines"] == []
    assert res["empty_blockquote_block_lines"] == []
    assert res["unattributed_normative_quote_lines"] == [1, 5]
    assert res["is_blockquote_hygiene_compliant"] is False


def test_audit_markdown_blockquote_invalid_inputs_and_export():
    """Retorna estructura limpia ante entradas vacías o no-string y verifica exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_depth_and_citation_hygiene,
    )

    assert "audit_markdown_blockquote_depth_and_citation_hygiene" in _m.__all__
    expected_empty = {
        "total_blockquote_blocks": 0,
        "excessive_nesting_block_lines": [],
        "empty_blockquote_block_lines": [],
        "unattributed_normative_quote_lines": [],
        "is_blockquote_hygiene_compliant": True,
    }
    for bad in (None, "", "   \n  ", 123, ["blockquote"]):
        assert (
            audit_markdown_blockquote_depth_and_citation_hygiene(bad)
            == expected_empty
        )


def test_audit_markdown_acronym_and_glossary_consistency_compliant():
    """Valida documento con acrónimos definidos en glosario o inline e ignora code fences."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_acronym_and_glossary_consistency,
    )

    doc = (
        "# Plan de Gestión del Valor Ganado (EVM)\n\n"
        "El sistema EVM monitorea el BAC durante todo el ciclo.\n\n"
        "## Glosario\n"
        "- **BAC**: Budget at Completion aprobado en la línea base.\n"
        "| CPI | Cost Performance Index acumulado |\n\n"
        "```python\n"
        "# UNDEF aparece 3 veces aquí: UNDEF UNDEF\n"
        "```\n"
    )
    res = audit_markdown_acronym_and_glossary_consistency(
        doc, min_occurrences_for_definition=2
    )
    assert res == {
        "total_acronyms_detected": 3,
        "undefined_frequent_acronyms": [],
        "duplicate_glossary_acronyms": [],
        "empty_definition_acronyms": [],
        "is_acronym_glossary_consistent": True,
    }
    assert (
        AnyDocService.audit_markdown_acronym_and_glossary_consistency(doc)
        == res
    )


def test_audit_markdown_acronym_undefined_frequent_acronyms():
    """Detecta acrónimos con ocurrencias >= min_occurrences_for_definition sin definición en glosario ni inline."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_consistency,
    )

    doc = (
        "El comité CCB revisa cada cambio remitido al CCB.\n"
        "Además el índice TCPI se recalcula cuando TCPI supera 1.10.\n"
        "Una mención única de RACI no exige glosario cuando el umbral es 2.\n"
    )
    res = audit_markdown_acronym_and_glossary_consistency(
        doc, min_occurrences_for_definition=2
    )
    assert res["total_acronyms_detected"] == 3
    assert res["undefined_frequent_acronyms"] == ["CCB", "TCPI"]
    assert res["duplicate_glossary_acronyms"] == []
    assert res["empty_definition_acronyms"] == []
    assert res["is_acronym_glossary_consistent"] is False


def test_audit_markdown_acronym_duplicate_and_empty_glossary_entries():
    """Detecta entradas duplicadas en el glosario y definiciones vacías o placeholders (TBD/TODO/pendiente)."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_consistency,
    )

    doc = (
        "## Glosario del Proyecto\n"
        "- **WBS**: Work Breakdown Structure jerárquica.\n"
        "* **WBS** - Estructura de Desglose del Trabajo duplicada.\n"
        "- **OBS**: TBD\n"
        "| RAM |   |\n"
    )
    res = audit_markdown_acronym_and_glossary_consistency(doc)
    assert res["total_acronyms_detected"] == 3
    assert res["undefined_frequent_acronyms"] == []
    assert res["duplicate_glossary_acronyms"] == ["WBS"]
    assert res["empty_definition_acronyms"] == ["OBS", "RAM"]
    assert res["is_acronym_glossary_consistent"] is False


def test_audit_markdown_acronym_invalid_inputs_and_export():
    """Retorna estructura limpia ante entradas vacías o no-string y verifica exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_consistency,
    )

    assert "audit_markdown_acronym_and_glossary_consistency" in _m.__all__
    expected_empty = {
        "total_acronyms_detected": 0,
        "undefined_frequent_acronyms": [],
        "duplicate_glossary_acronyms": [],
        "empty_definition_acronyms": [],
        "is_acronym_glossary_consistent": True,
    }
    for bad in (None, "", "   \n  ", 42, ["WBS"]):
        assert (
            audit_markdown_acronym_and_glossary_consistency(bad)
            == expected_empty
        )


def test_audit_markdown_task_list_action_item_hygiene_compliant():
    """Listas de acción con @owner o owner: y fecha ISO en ítems abiertos cumplen PMBOK §4.4 y §10.2."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_task_list_action_item_hygiene,
    )

    doc = (
        "# Plan de Acción del Comité\n"
        "- [x] Publicar acta de inicio de fase\n"
        "- [ ] Emitir matriz RACI actualizada @pm.lead 2026-11-15\n"
        "* [ ] Validar reserva de contingencia owner: finanzas_ccf (vencimiento 2026-11-20)\n"
        "+ [X] Archivar línea base preliminar\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(doc)
    assert res == {
        "total_task_items": 4,
        "open_task_items": 2,
        "completed_task_items": 2,
        "empty_task_item_lines": [],
        "unassigned_open_task_lines": [],
        "undated_open_task_lines": [],
        "is_task_list_hygiene_compliant": True,
    }
    assert AnyDocService.audit_markdown_task_list_action_item_hygiene(doc) == res


def test_audit_markdown_task_list_unassigned_and_undated_open_items():
    """Detecta tareas abiertas sin responsable (@owner/owner:) o sin fecha compromiso ISO YYYY-MM-DD."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    doc = (
        "## Seguimiento de Compromisos\n"
        "- [ ] Revisar presupuesto con proveedor antes del 2026-12-01\n"
        "- [ ] Actualizar cronograma maestro @scheduler_pmo\n"
        "- [ ] Pendiente definir alcance de entregable\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(doc)
    assert res["total_task_items"] == 3
    assert res["open_task_items"] == 3
    assert res["completed_task_items"] == 0
    assert res["empty_task_item_lines"] == []
    assert res["unassigned_open_task_lines"] == [2, 4]
    assert res["undated_open_task_lines"] == [3, 4]
    assert res["is_task_list_hygiene_compliant"] is False

    # Cuando require_owner_and_due_date_on_open=False no exige responsable ni fecha
    relaxed = audit_markdown_task_list_action_item_hygiene(
        doc, require_owner_and_due_date_on_open=False
    )
    assert relaxed["unassigned_open_task_lines"] == []
    assert relaxed["undated_open_task_lines"] == []
    assert relaxed["is_task_list_hygiene_compliant"] is True


def test_audit_markdown_task_list_empty_items_and_fenced_code_exclusion():
    """Detecta checkboxes vacíos (< 3 caracteres) e ignora checkboxes dentro de bloques de código cercados."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    doc = (
        "- [x]   \n"
        "- [ ] ok\n"
        "```markdown\n"
        "- [ ] Tarea ficticia en ejemplo sin dueño ni fecha\n"
        "- [x] \n"
        "```\n"
        "~~~\n"
        "* [ ] Otra tarea dentro de bloque tilde\n"
        "~~~\n"
        "- [ ] Entregar informe final @qa.lead 2026-12-10\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(doc)
    assert res["total_task_items"] == 3
    assert res["open_task_items"] == 2
    assert res["completed_task_items"] == 1
    assert res["empty_task_item_lines"] == [1, 2]
    assert res["unassigned_open_task_lines"] == [2]
    assert res["undated_open_task_lines"] == [2]
    assert res["is_task_list_hygiene_compliant"] is False


def test_audit_markdown_task_list_invalid_inputs_and_export():
    """Retorna estructura limpia ante entradas vacías o no-string y verifica exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    assert "audit_markdown_task_list_action_item_hygiene" in _m.__all__
    expected_empty = {
        "total_task_items": 0,
        "open_task_items": 0,
        "completed_task_items": 0,
        "empty_task_item_lines": [],
        "unassigned_open_task_lines": [],
        "undated_open_task_lines": [],
        "is_task_list_hygiene_compliant": True,
    }
    for bad in (None, "", "   \n  ", 123, ["-[ ] item"]):
        assert audit_markdown_task_list_action_item_hygiene(bad) == expected_empty


def test_audit_markdown_mermaid_diagram_syntax_and_complexity_compliant():
    """Diagramas Mermaid de tipos soportados con etiquetas entrecomilladas y sin HTML cumplen §4.4 y §10.2."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_mermaid_diagram_syntax_and_complexity,
    )

    doc = (
        "# Arquitectura de Gobernanza\n"
        "```mermaid\n"
        "%% Diagrama de flujo principal\n"
        "flowchart TD\n"
        '    A["Inicio (Charter Aprobado)"] --> B["Planificación (PMB)"]\n'
        '    B --> C["Cierre (Handover)"]\n'
        "```\n"
        "~~~mermaid\n"
        "sequenceDiagram\n"
        "    Sponsor->>PM: Autoriza línea base\n"
        "~~~\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_and_complexity(doc)
    assert res == {
        "total_mermaid_blocks": 2,
        "unsupported_or_empty_mermaid_block_lines": [],
        "html_tag_in_mermaid_block_lines": [],
        "unquoted_special_char_label_block_lines": [],
        "overly_complex_mermaid_block_lines": [],
        "is_mermaid_hygiene_compliant": True,
    }
    assert (
        AnyDocService.audit_markdown_mermaid_diagram_syntax_and_complexity(doc)
        == res
    )


def test_audit_markdown_mermaid_unsupported_and_empty_blocks():
    """Detecta bloques Mermaid vacíos o con tipos de diagrama no soportados (ej. gantt, pie)."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_complexity,
    )

    doc = (
        "```mermaid\n"
        "%% Solo comentario sin sentencias\n"
        "```\n"
        "```mermaid\n"
        "gantt\n"
        "    title Cronograma no soportado\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_and_complexity(doc)
    assert res["total_mermaid_blocks"] == 2
    assert res["unsupported_or_empty_mermaid_block_lines"] == [1, 4]
    assert res["is_mermaid_hygiene_compliant"] is False


def test_audit_markdown_mermaid_html_tags_unquoted_parens_and_complexity():
    """Detecta tags HTML crudos, paréntesis sin comillas en etiquetas de nodos y exceso de complejidad."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_complexity,
    )

    doc = (
        "```mermaid\n"
        "flowchart LR\n"
        "    A[Nodo con (Paréntesis) sin comillas] --> B[\"Etiqueta con <br/> HTML\"]\n"
        "    B --> C[\"Nodo 3\"]\n"
        "    C --> D[\"Nodo 4\"]\n"
        "    D --> E[\"Nodo 5\"]\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_and_complexity(
        doc, max_nodes_per_diagram=3
    )
    assert res["total_mermaid_blocks"] == 1
    assert res["unsupported_or_empty_mermaid_block_lines"] == []
    assert res["html_tag_in_mermaid_block_lines"] == [1]
    assert res["unquoted_special_char_label_block_lines"] == [1]
    assert res["overly_complex_mermaid_block_lines"] == [1]
    assert res["is_mermaid_hygiene_compliant"] is False


def test_audit_markdown_mermaid_invalid_inputs_and_export():
    """Maneja entradas vacías o no-string, ignora otros bloques de código y verifica __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_complexity,
    )

    assert "audit_markdown_mermaid_diagram_syntax_and_complexity" in _m.__all__
    expected_empty = {
        "total_mermaid_blocks": 0,
        "unsupported_or_empty_mermaid_block_lines": [],
        "html_tag_in_mermaid_block_lines": [],
        "unquoted_special_char_label_block_lines": [],
        "overly_complex_mermaid_block_lines": [],
        "is_mermaid_hygiene_compliant": True,
    }
    for bad in (None, "", "   \n  ", 99, ["```mermaid"]):
        assert (
            audit_markdown_mermaid_diagram_syntax_and_complexity(bad)
            == expected_empty
        )


def test_audit_markdown_alert_admonition_hygiene_compliant():
    """Alertas tipadas correctamente, con cuerpo y separadas por parrafo."""
    from backend.services.anydoc_service import (
        audit_markdown_alert_admonition_hygiene,
    )

    doc = (
        "Intro.\n"
        "\n"
        "> [!NOTE]\n"
        "> Cuerpo de la nota.\n"
        "\n"
        "Texto separador normal.\n"
        "\n"
        "> [!CAUTION] cuerpo inline\n"
        "\n"
        "Fin.\n"
    )
    res = audit_markdown_alert_admonition_hygiene(doc)
    assert res == {
        "total_alerts": 2,
        "invalid_alert_type_lines": [],
        "nested_alert_block_lines": [],
        "empty_alert_body_lines": [],
        "consecutive_adjacent_alert_lines": [],
        "is_alert_admonition_hygiene_compliant": True,
    }


def test_audit_markdown_alert_admonition_hygiene_invalid_and_nested():
    """Tipos fuera del catalogo (case-sensitive en MAYUSCULAS) y prefijos anidados."""
    from backend.services.anydoc_service import (
        audit_markdown_alert_admonition_hygiene,
    )

    doc = (
        "> [!FOO]\n"
        "> cuerpo.\n"
        "\n"
        ">> [!NOTE]\n"
        "> anidado.\n"
        "\n"
        ">> [!TIP] anidado pegado sin espacio\n"
        "> cuerpo.\n"
        "\n"
        "> [!note] minusculas invalidas\n"
        "> cuerpo.\n"
    )
    res = audit_markdown_alert_admonition_hygiene(doc)
    assert res["total_alerts"] == 4
    assert res["invalid_alert_type_lines"] == [1, 10]
    assert res["nested_alert_block_lines"] == [4, 7]
    assert res["is_alert_admonition_hygiene_compliant"] is False


def test_audit_markdown_alert_admonition_hygiene_empty_and_adjacent():
    """Alertas sin cuerpo y alertas pegadas consecutivamente sin separador."""
    from backend.services.anydoc_service import (
        audit_markdown_alert_admonition_hygiene,
    )

    doc = (
        "> [!WARNING]\n"          # sin cuerpo: blockquote termina aca.
        "\n"
        "> [!NOTE]\n"
        "> cuerpo A.\n"
        "> [!TIP]\n"              # pegada dentro del mismo blockquote.
        "> cuerpo B.\n"
    )
    res = audit_markdown_alert_admonition_hygiene(doc)
    assert res["total_alerts"] == 3
    assert res["empty_alert_body_lines"] == [1]
    assert res["consecutive_adjacent_alert_lines"] == [5]
    assert res["is_alert_admonition_hygiene_compliant"] is False

    # El cuerpo en las lineas '>' siguientes del blockquote evita empty.
    ok = audit_markdown_alert_admonition_hygiene(
        "> [!NOTE]\n> cuerpo en la siguiente linea.\n"
    )
    assert ok["empty_alert_body_lines"] == []
    assert ok["is_alert_admonition_hygiene_compliant"] is True

    # Code fences ignoran alertas; vacio/None/no-str retornan dict neutral.
    fenced = audit_markdown_alert_admonition_hygiene(
        "```\n> [!FOO] dentro de fence\n```\n\n> [!NOTE] fuera con cuerpo\n"
    )
    assert fenced["total_alerts"] == 1
    assert fenced["invalid_alert_type_lines"] == []

    import backend.services.anydoc_service as _m
    assert "audit_markdown_alert_admonition_hygiene" in _m.__all__


def test_audit_markdown_alert_admonition_hygiene_scope_and_proxy():
    """Entradas vacias/None/invalidas + llamada via AnyDocService (staticmethod + __all__)."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_alert_admonition_hygiene,
    )

    empty = {
        "total_alerts": 0,
        "invalid_alert_type_lines": [],
        "nested_alert_block_lines": [],
        "empty_alert_body_lines": [],
        "consecutive_adjacent_alert_lines": [],
        "is_alert_admonition_hygiene_compliant": True,
    }
    for payload in (None, "", "   \n  ", 42, ["x"]):
        assert audit_markdown_alert_admonition_hygiene(payload) == empty

    sample = (
        "> [!TIP]\n> consejo.\n"
    )
    assert (
        AnyDocService.audit_markdown_alert_admonition_hygiene(sample)
        == audit_markdown_alert_admonition_hygiene(sample)
    )


def test_audit_markdown_footnote_reference_coherence_compliant():
    """Cumple cuando todas las notas al pie referenciadas están definidas una sola vez con contenido y sin huérfanas."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_footnote_reference_coherence,
    )

    md = (
        "El estándar PMBOK[^pmbok7] exige trazabilidad documental[^trace-1].\n\n"
        "```markdown\n"
        "Referencia ignorada en bloque de código[^ghost_code]\n"
        "[^dup_in_code]: Definición ignorada\n"
        "```\n\n"
        "[^PMBOK7]: Project Management Institute, Séptima Edición.\n"
        "[^trace-1]: Matriz de trazabilidad de requisitos §5.2.\n"
    )
    res = audit_markdown_footnote_reference_coherence(md)
    assert res == {
        "total_definitions": 2,
        "total_inline_references": 2,
        "duplicate_footnote_definition_ids": [],
        "empty_footnote_definition_ids": [],
        "undefined_footnote_reference_ids": [],
        "unreferenced_orphan_footnote_ids": [],
        "is_footnote_hygiene_compliant": True,
    }
    assert AnyDocService.audit_markdown_footnote_reference_coherence(md) == res


def test_audit_markdown_footnote_reference_undefined_and_orphan():
    """Detecta referencias inline sin definición y definiciones huérfanas nunca citadas en el texto."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_coherence,
    )

    md = (
        "Texto con cita inexistente[^missing_ref] y otra válida[^valid_ref].\n\n"
        "[^valid_ref]: Fuente oficial verificada.\n"
        "[^orphan_def]: Nota al pie que nunca fue citada en ningún párrafo.\n"
    )
    res = audit_markdown_footnote_reference_coherence(md)
    assert res["total_definitions"] == 2
    assert res["total_inline_references"] == 2
    assert res["undefined_footnote_reference_ids"] == ["missing_ref"]
    assert res["unreferenced_orphan_footnote_ids"] == ["orphan_def"]
    assert res["is_footnote_hygiene_compliant"] is False


def test_audit_markdown_footnote_reference_duplicate_and_empty_definitions():
    """Detecta definiciones duplicadas (case-insensitive) y definiciones con cuerpo vacío."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_coherence,
    )

    md = (
        "Cita uno[^fn1] y cita vacía[^empty_fn].\n\n"
        "[^fn1]: Primera definición válida.\n"
        "[^FN1]: Segunda definición duplicada.\n"
        "[^empty_fn]:    \n"
    )
    res = audit_markdown_footnote_reference_coherence(md)
    assert res["total_definitions"] == 3
    assert res["duplicate_footnote_definition_ids"] == ["fn1"]
    assert res["empty_footnote_definition_ids"] == ["empty_fn"]
    assert res["is_footnote_hygiene_compliant"] is False


def test_audit_markdown_footnote_reference_coherence_edge_cases_and_export():
    """Verifica manejo de entradas vacías o no string y exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_coherence,
    )

    assert "audit_markdown_footnote_reference_coherence" in _m.__all__
    for empty_in in ("", "   \n  ", None, 123):
        assert audit_markdown_footnote_reference_coherence(empty_in) == {
            "total_definitions": 0,
            "total_inline_references": 0,
            "duplicate_footnote_definition_ids": [],
            "empty_footnote_definition_ids": [],
            "undefined_footnote_reference_ids": [],
            "unreferenced_orphan_footnote_ids": [],
            "is_footnote_hygiene_compliant": True,
        }


def test_audit_markdown_definition_list_and_spec_hygiene_clean():
    """Cumple cuando los términos técnicos tienen definiciones completas, sin huérfanas ni duplicados."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_definition_list_and_spec_hygiene,
    )

    md = (
        "RPO (Recovery Point Objective)\n"
        ": Máximo período tolerable de pérdida de datos ante un desastre.\n"
        ": Sincronización continua cada 5 minutos en base de datos.\n\n"
        "```markdown\n"
        ": Definición huérfana ignorada dentro de bloque de código\n"
        "```\n\n"
        "RTO (Recovery Time Objective)\n"
        ": Tiempo máximo de restauración del servicio tras una interrupción.\n"
    )
    res = audit_markdown_definition_list_and_spec_hygiene(md, min_definition_chars=10)
    assert res == {
        "total_terms_count": 2,
        "total_definitions_count": 3,
        "orphan_definitions": [],
        "underspecified_definitions": [],
        "duplicate_terms": [],
        "is_definition_list_hygiene_clean": True,
    }
    assert AnyDocService.audit_markdown_definition_list_and_spec_hygiene(md) == res


def test_audit_markdown_definition_list_orphan_definitions():
    """Detecta líneas de definición (: ...) sin término válido previo (inicio, tras línea en blanco o encabezado)."""
    from backend.services.anydoc_service import (
        audit_markdown_definition_list_and_spec_hygiene,
    )

    md = (
        ": Definición huérfana al inicio del documento sin término.\n\n"
        "# Sección Técnica\n"
        ": Otra definición huérfana inmediatamente tras un encabezado.\n"
    )
    res = audit_markdown_definition_list_and_spec_hygiene(md)
    assert res["total_terms_count"] == 0
    assert res["total_definitions_count"] == 2
    assert len(res["orphan_definitions"]) == 2
    assert res["is_definition_list_hygiene_clean"] is False


def test_audit_markdown_definition_list_duplicate_and_underspecified():
    """Detecta términos redefinidos en bloques separados y definiciones vagas o con marcadores TBD/TODO."""
    from backend.services.anydoc_service import (
        audit_markdown_definition_list_and_spec_hygiene,
    )

    md = (
        "SLA Disponibilidad\n"
        ": Garantía contractual de uptime mensual de 99.95% en producción.\n\n"
        "Latencia P99\n"
        ": TBD\n\n"
        "sla disponibilidad\n"
        ": Corto\n"
    )
    res = audit_markdown_definition_list_and_spec_hygiene(md, min_definition_chars=10)
    assert res["total_terms_count"] == 3
    assert res["total_definitions_count"] == 3
    assert res["duplicate_terms"] == ["sla disponibilidad"]
    assert "Latencia P99" in res["underspecified_definitions"]
    assert "sla disponibilidad" in res["underspecified_definitions"]
    assert res["is_definition_list_hygiene_clean"] is False


def test_audit_markdown_definition_list_edge_cases_and_export():
    """Verifica manejo de entradas vacías o no string y exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_definition_list_and_spec_hygiene,
    )

    assert "audit_markdown_definition_list_and_spec_hygiene" in _m.__all__
    for empty_in in ("", "   \n  ", None, 42):
        assert audit_markdown_definition_list_and_spec_hygiene(empty_in) == {
            "total_terms_count": 0,
            "total_definitions_count": 0,
            "orphan_definitions": [],
            "underspecified_definitions": [],
            "duplicate_terms": [],
            "is_definition_list_hygiene_clean": True,
        }


def test_audit_markdown_image_alt_text_and_asset_hygiene_clean_v2():
    """Verifica que imágenes Markdown con alt descriptivo (>=5 chars) y URLs HTTPS/relativas limpias pasen sin hallazgos."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "![Diagrama de Arquitectura Cloud](https://cdn.ccf.org/arch-v2.svg \"Arquitectura\")\n"
        "![Curva S de Valor Ganado](assets/evm-s-curve.png)\n\n"
        "```html\n"
        "<img src=\"http://insecure-ignored.local/a.png\">\n"
        "![img](http://insecure-ignored.local/b.png)\n"
        "```\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md, min_alt_text_chars=5)
    assert res == {
        "total_images_count": 2,
        "compliant_images_count": 2,
        "missing_or_generic_alt_images": [],
        "insecure_or_invalid_src_images": [],
        "unapproved_raw_html_img_count": 0,
        "is_image_hygiene_clean": True,
    }
    assert (
        AnyDocService.audit_markdown_image_alt_text_and_asset_hygiene(
            md, min_alt_text_chars=5
        )
        == res
    )


def test_audit_markdown_image_alt_text_generic_or_filename_v2():
    """Detecta textos alternativos cortos, genéricos (image, foto, screenshot) o terminados en extensión de archivo."""
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "![foto](https://cdn.ccf.org/photo1.jpg)\n"
        "![chart.png](https://cdn.ccf.org/chart.png)\n"
        "![ui](https://cdn.ccf.org/ui.webp)\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md, min_alt_text_chars=5)
    assert res["total_images_count"] == 3
    assert res["compliant_images_count"] == 0
    assert len(res["missing_or_generic_alt_images"]) == 3
    assert res["is_image_hygiene_clean"] is False


def test_audit_markdown_image_alt_text_insecure_src_and_raw_html_v2():
    """Detecta orígenes HTTP/file/javascript o con espacios sin codificar y etiquetas HTML <img> crudas."""
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    md = (
        "<img src=\"https://cdn.ccf.org/raw.png\" alt=\"raw\" />\n"
        "![Cronograma Maestro del Proyecto](http://unencrypted.ccf.org/gantt.png)\n"
        "![Matriz de Riesgos](assets/uninlined space file.png)\n"
    )
    res = audit_markdown_image_alt_text_and_asset_hygiene(md)
    assert res["unapproved_raw_html_img_count"] == 1
    assert len(res["insecure_or_invalid_src_images"]) == 2
    assert res["is_image_hygiene_clean"] is False


def test_audit_markdown_image_alt_text_edge_cases_and_export_v2():
    """Verifica manejo de entradas vacías o no string y exportación en __all__."""
    import backend.services.anydoc_service as _m
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_hygiene,
    )

    assert "audit_markdown_image_alt_text_and_asset_hygiene" in _m.__all__
    for empty_in in ("", "   \n  ", None, 99):
        assert audit_markdown_image_alt_text_and_asset_hygiene(empty_in) == {
            "total_images_count": 0,
            "compliant_images_count": 0,
            "missing_or_generic_alt_images": [],
            "insecure_or_invalid_src_images": [],
            "unapproved_raw_html_img_count": 0,
            "is_image_hygiene_clean": True,
        }





def test_audit_markdown_horizontal_rule_and_section_break_hygiene_clean():
    """Documento limpio: front-matter ignorado y HR unica bien separada."""
    from backend.services.anydoc_service import (
        audit_markdown_horizontal_rule_and_section_break_hygiene,
    )

    res = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "---\ntitle: Ok\n---\n\n## Seccion\n\nParrafo 1.\n\n---\n\nParrafo 2.\n"
    )
    assert res == {
        "total_horizontal_rules_count": 1,
        "mixed_hr_styles_detected": False,
        "consecutive_horizontal_rules_count": 0,
        "excessive_blank_line_runs_count": 0,
        "ambiguous_setext_hr_lines": [],
        "is_section_break_hygiene_clean": True,
    }


def test_audit_markdown_horizontal_rule_and_section_break_hygiene_hr_findings():
    """Mezcla de estilos, HRs consecutivas (incl. separadas solo por blancos) y fences."""
    from backend.services.anydoc_service import (
        audit_markdown_horizontal_rule_and_section_break_hygiene,
    )

    mixed = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "## Titulo\n\n---\n***\n___\n\nTexto.\n"
    )
    assert mixed["total_horizontal_rules_count"] == 3
    assert mixed["mixed_hr_styles_detected"] is True
    assert mixed["consecutive_horizontal_rules_count"] == 2
    assert mixed["is_section_break_hygiene_clean"] is False

    cons = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "---\n---\n---\n\nTexto.\n"
    )
    assert cons["total_horizontal_rules_count"] == 3
    assert cons["consecutive_horizontal_rules_count"] == 2
    assert cons["mixed_hr_styles_detected"] is False
    assert cons["is_section_break_hygiene_clean"] is False

    # Blancos intermedios no separan: siguen siendo consecutivas (sin contenido entre ellas).
    gapped = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "---\n\n---\n\nTexto.\n"
    )
    assert gapped["consecutive_horizontal_rules_count"] == 1

    # HRs dentro de fences no cuentan.
    fenced = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "```\n---\n***\n```\n\nTexto.\n"
    )
    assert fenced["total_horizontal_rules_count"] == 0
    assert fenced["mixed_hr_styles_detected"] is False
    assert fenced["is_section_break_hygiene_clean"] is True


def test_audit_markdown_horizontal_rule_and_section_break_hygiene_setext_and_blanks():
    """Ambiguedad Setext (parrafo+guiones pegados) y corridas de blancos excesivas."""
    from backend.services.anydoc_service import (
        audit_markdown_horizontal_rule_and_section_break_hygiene,
    )

    ambiguous = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "Parrafo normal.\n---\n\nTexto.\n"
    )
    assert ambiguous["ambiguous_setext_hr_lines"] == [2]
    assert ambiguous["total_horizontal_rules_count"] == 1
    assert ambiguous["is_section_break_hygiene_clean"] is False

    # Precedentes seguros: encabezado, lista, cita, tabla o linea en blanco.
    assert (
        audit_markdown_horizontal_rule_and_section_break_hygiene("# Titulo\n---\n\nTexto.\n")[
            "ambiguous_setext_hr_lines"
        ]
        == []
    )
    assert (
        audit_markdown_horizontal_rule_and_section_break_hygiene("- item\n---\n\nTexto.\n")[
            "ambiguous_setext_hr_lines"
        ]
        == []
    )
    assert (
        audit_markdown_horizontal_rule_and_section_break_hygiene("> cita\n---\n\nTexto.\n")[
            "ambiguous_setext_hr_lines"
        ]
        == []
    )
    assert (
        audit_markdown_horizontal_rule_and_section_break_hygiene("| a |\n---\n\nTexto.\n")[
            "ambiguous_setext_hr_lines"
        ]
        == []
    )
    assert (
        audit_markdown_horizontal_rule_and_section_break_hygiene("Parrafo.\n\n---\n\nTexto.\n")[
            "ambiguous_setext_hr_lines"
        ]
        == []
    )

    # Corridas de blancos: cada corrida que excede max cuenta 1 (borde: max permitido OK).
    runs = audit_markdown_horizontal_rule_and_section_break_hygiene("A.\n\n\n\nB.\n\n\n\n\nC.\n")
    assert runs["excessive_blank_line_runs_count"] == 2
    assert runs["is_section_break_hygiene_clean"] is False
    allowed = audit_markdown_horizontal_rule_and_section_break_hygiene("A.\n\n\nB.\n")
    assert allowed["excessive_blank_line_runs_count"] == 0
    single_run = audit_markdown_horizontal_rule_and_section_break_hygiene("A.\n\n\n\n\n\n\nB.\n")
    assert single_run["excessive_blank_line_runs_count"] == 1
    # Umbral custom: con max 4, la corrida de 6 ya no es excesiva... 6 > 4 si lo es.
    custom = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "A.\n\n\n\n\n\n\nB.\n", max_consecutive_blank_lines=4
    )
    assert custom["excessive_blank_line_runs_count"] == 1


def test_audit_markdown_horizontal_rule_and_section_break_hygiene_frontmatter_and_empty():
    """Front-matter valido ignorado; degenerado (sin YAML) tratado como HRs; vacio/None + __all__."""
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_horizontal_rule_and_section_break_hygiene,
    )
    import backend.services.anydoc_service as mod

    fm = audit_markdown_horizontal_rule_and_section_break_hygiene(
        "---\ny: 1\nz: 2\n---\n\nTexto.\n\n***\n"
    )
    assert fm["total_horizontal_rules_count"] == 1
    assert fm["ambiguous_setext_hr_lines"] == []

    # Front-matter degenerado (---/--- sin YAML) no se come los guiones: son HRs.
    degen = audit_markdown_horizontal_rule_and_section_break_hygiene("---\n---\n\nTexto.\n")
    assert degen["total_horizontal_rules_count"] == 2
    assert degen["consecutive_horizontal_rules_count"] == 1
    assert degen["is_section_break_hygiene_clean"] is False

    for payload in (None, "", 42):
        empty = audit_markdown_horizontal_rule_and_section_break_hygiene(payload)
        assert empty["total_horizontal_rules_count"] == 0
        assert empty["is_section_break_hygiene_clean"] is True

    sample = "Texto.\n\n---\n"
    assert (
        AnyDocService.audit_markdown_horizontal_rule_and_section_break_hygiene(sample)
        == audit_markdown_horizontal_rule_and_section_break_hygiene(sample)
    )
    assert "audit_markdown_horizontal_rule_and_section_break_hygiene" in mod.__all__


def test_audit_markdown_admonition_and_callout_hygiene_compliant_and_fences_ignored():
    """Callouts canónicos con cuerpo suficiente separados por prosa y código cercado ignorado."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_and_callout_hygiene,
    )

    md = (
        "# Manual Operativo PMO\n\n"
        "> [!NOTE]\n"
        "> Esta nota documenta el contexto de línea base del cronograma.\n\n"
        "Párrafo intermedio de transición entre alertas operativas.\n\n"
        "> [!WARNING] Precaución crítica en liberación de cambios\n"
        "> Validar firmas de comité antes de desplegar.\n\n"
        "```markdown\n"
        "> [!DANGER]\n"
        ">> [!NOTE]\n"
        "```\n"
    )
    res = audit_markdown_admonition_and_callout_hygiene(md)
    assert res["total_callouts"] == 2
    assert res["valid_callouts"] == 2
    assert res["type_distribution"] == {"NOTE": 1, "WARNING": 1}
    assert res["unsupported_type_lines"] == []
    assert res["empty_or_short_callout_lines"] == []
    assert res["nested_callout_lines"] == []
    assert res["consecutive_callout_lines"] == []
    assert res["hygiene_score"] == 100.0
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_markdown_admonition_and_callout_hygiene_unsupported_and_short_body():
    """Detecta tipos no soportados ([!DANGER]) y cuerpos vacíos o menores a min_body_words."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_and_callout_hygiene,
    )

    md = (
        "> [!DANGER]\n"
        "> Este bloque usa un identificador fuera del estándar GitHub.\n\n"
        "Texto separador normal.\n\n"
        "> [!TIP]\n"
        "> Corto\n"
    )
    res = audit_markdown_admonition_and_callout_hygiene(md, min_body_words=3)
    assert res["total_callouts"] == 2
    assert res["valid_callouts"] == 0
    assert res["unsupported_type_lines"] == [1]
    assert res["empty_or_short_callout_lines"] == [6]
    assert res["hygiene_score"] == 0.0
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_admonition_and_callout_hygiene_nested_and_consecutive():
    """Detecta callouts anidados (>> [!...] o dentro de blockquote) y callouts consecutivos sin prosa."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_and_callout_hygiene,
    )

    md = (
        "> [!IMPORTANT]\n"
        "> Primer bloque válido con suficientes palabras de detalle.\n\n"
        "> [!CAUTION]\n"
        "> Segundo bloque consecutivo sin párrafo intermedio de separación.\n\n"
        "Párrafo explicativo que separa secciones.\n\n"
        ">> [!NOTE] Bloque anidado con doble nivel de cita\n"
    )
    res = audit_markdown_admonition_and_callout_hygiene(md, max_consecutive_callouts=1)
    assert res["total_callouts"] == 3
    assert res["valid_callouts"] == 1
    assert res["consecutive_callout_lines"] == [4]
    assert res["nested_callout_lines"] == [9]
    assert res["hygiene_score"] == 33.33
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_admonition_and_callout_hygiene_empty_and_service_binding():
    """Entradas vacías/None retornan 100% cumplimiento y el método está expuesto en AnyDocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_admonition_and_callout_hygiene,
    )

    for empty_val in (None, "", "   \n  "):
        res = audit_markdown_admonition_and_callout_hygiene(empty_val)
        assert res["total_callouts"] == 0
        assert res["valid_callouts"] == 0
        assert res["hygiene_score"] == 100.0
        assert res["is_compliant"] is True
        assert res["recommendations"] == []

    sample = "> [!TIP] Recomendación operativa con suficientes palabras.\n"
    assert (
        AnyDocService.audit_markdown_admonition_and_callout_hygiene(sample)
        == audit_markdown_admonition_and_callout_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_admonition_and_callout_hygiene(sample)
        == audit_markdown_admonition_and_callout_hygiene(sample)
    )
    assert "audit_markdown_admonition_and_callout_hygiene" in mod.__all__



def test_audit_markdown_raw_html_and_script_injection_hygiene_critical():
    """Tags peligrosos, eventos inline y URIs js/data/vbscript -> CRITICAL."""
    from backend.services.anydoc_service import (
        audit_markdown_raw_html_and_script_injection_hygiene,
    )

    res = audit_markdown_raw_html_and_script_injection_hygiene(
        "Texto <br> normal.\n"
        "<script>alert(1)</script>\n"
        "<a href=\"javascript:alert(2)\">link</a>\n"
        "<img src=\"x\" onerror=\"alert(3)\">\n"
        "<a href=\"data:text/html;base64,XXXX\">d</a>\n"
        "<a href='vbscript:boom'>v</a>\n"
    )
    assert res["dangerous_executable_tag_lines"] == [2]
    assert res["inline_event_or_js_uri_lines"] == [3, 4, 5, 6]
    # a/img no permitidas pero <script> ya es peligrosa: no se duplica en disallowed.
    assert res["disallowed_raw_html_tag_lines"] == [3, 4, 5, 6]
    assert res["html_hygiene_status"] == "CRITICAL"
    assert res["is_compliant"] is False
    assert isinstance(res["total_html_tags_detected"], int)

    # Case-insensitive: <SCRIPT> y <SVG onload=...>.
    upper = audit_markdown_raw_html_and_script_injection_hygiene(
        "<SCRIPT>x</SCRIPT>\n<SVG onload=x>\n"
    )
    assert upper["dangerous_executable_tag_lines"] == [1, 2]
    assert upper["inline_event_or_js_uri_lines"] == [2]

    # Autocerrada <br/> y cierre con espacios no rompen el parseo.
    selfclose = audit_markdown_raw_html_and_script_injection_hygiene(
        "<br/>linea<br />\n<IFRAME src=x onerror=y></iframe>\n"
    )
    assert selfclose["dangerous_executable_tag_lines"] == [2]
    assert selfclose["inline_event_or_js_uri_lines"] == [2]
    # iframe es peligrosa: la lista disallowed excluye las peligrosas (spec).
    assert selfclose["disallowed_raw_html_tag_lines"] == []
    assert selfclose["is_compliant"] is False


def test_audit_markdown_raw_html_and_script_injection_hygiene_at_risk():
    """Solo etiquetas no permitidas (div/span/font) -> AT_RISK; allowed custom relaja."""
    from backend.services.anydoc_service import (
        audit_markdown_raw_html_and_script_injection_hygiene,
    )

    risk = audit_markdown_raw_html_and_script_injection_hygiene(
        "<div>hola</div>\n<span>x</span>\n<font size=\"3\">y</font>\n"
    )
    assert risk["disallowed_raw_html_tag_lines"] == [1, 2, 3]
    assert risk["dangerous_executable_tag_lines"] == []
    assert risk["inline_event_or_js_uri_lines"] == []
    assert risk["html_hygiene_status"] == "AT_RISK"
    assert risk["is_compliant"] is False

    custom = audit_markdown_raw_html_and_script_injection_hygiene(
        "<div>ok</div>", allowed_html_tags=("div",)
    )
    assert custom["disallowed_raw_html_tag_lines"] == []
    assert custom["is_compliant"] is True
    assert custom["html_hygiene_status"] == "HEALTHY"


def test_audit_markdown_raw_html_and_script_injection_hygiene_ignores():
    """Code spans inline, fences, comentarios HTML y callouts se ignoran."""
    from backend.services.anydoc_service import (
        audit_markdown_raw_html_and_script_injection_hygiene,
    )

    clean = audit_markdown_raw_html_and_script_injection_hygiene(
        "Texto <br> salto, <sub>x</sub>, <sup>2</sup>, <kbd>Ctrl</kbd>.\n"
        "<details><summary>ver</summary>mas</details>\n"
        "`<script>x</script>` inline code ignorado.\n"
        "```html\n<script>ignore</script>\n<span>ign</span>\n```\n"
        "> [!NOTE]\n"
        "> <div>callout ignorado</div>\n"
        "Texto final sin html.\n"
    )
    assert clean["dangerous_executable_tag_lines"] == []
    assert clean["inline_event_or_js_uri_lines"] == []
    assert clean["disallowed_raw_html_tag_lines"] == []
    assert clean["html_hygiene_status"] == "HEALTHY"
    assert clean["is_compliant"] is True

    commented = audit_markdown_raw_html_and_script_injection_hygiene(
        "<!-- <script>evil</script> -->\nTexto.\n<!-- parcial\ncomentario --> <b>bold</b>\n"
    )
    assert commented["dangerous_executable_tag_lines"] == []
    # b aparece solo tras el cierre del comentario multilinea (linea 4).
    assert commented["disallowed_raw_html_tag_lines"] == [4]


def test_audit_markdown_raw_html_and_script_injection_hygiene_neutral_and_export():
    """Entradas no-str/None, proxies estaticos de AnyDocService/AnydocService y __all__."""
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_raw_html_and_script_injection_hygiene,
    )
    import backend.services.anydoc_service as mod

    for payload in (None, "", 42):
        empty = audit_markdown_raw_html_and_script_injection_hygiene(payload)
        assert empty["total_html_tags_detected"] == 0
        assert empty["is_compliant"] is True
        assert empty["html_hygiene_status"] == "HEALTHY"
        assert empty["dangerous_executable_tag_lines"] == []

    sample = "<div>x</div>"
    assert (
        AnyDocService.audit_markdown_raw_html_and_script_injection_hygiene(sample)
        == audit_markdown_raw_html_and_script_injection_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_raw_html_and_script_injection_hygiene(sample)
        == audit_markdown_raw_html_and_script_injection_hygiene(sample)
    )
    assert "audit_markdown_raw_html_and_script_injection_hygiene" in mod.__all__


def test_audit_markdown_code_fence_balance_and_language_hygiene_healthy():
    """Valida bloques cercados balanceados (``` y ~~~) con lenguaje especificado y contenido."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_balance_and_language_hygiene,
    )

    md = (
        "# Manual Técnico\n\n"
        "```python\n"
        "def calcular_cpi(ev: float, ac: float) -> float:\n"
        "    return ev / ac\n"
        "```\n\n"
        "~~~yaml\n"
        "pmo:\n"
        "  status: active\n"
        "~~~\n"
    )
    res = audit_markdown_code_fence_balance_and_language_hygiene(md)
    assert res["total_code_blocks"] == 2
    assert res["compliant_code_blocks"] == 2
    assert res["unclosed_fence_start_lines"] == []
    assert res["untagged_code_block_lines"] == []
    assert res["empty_code_block_lines"] == []
    assert res["mismatched_closing_fence_lines"] == []
    assert res["fence_hygiene_status"] == "HEALTHY"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_markdown_code_fence_balance_and_language_hygiene_at_risk():
    """Detecta bloques sin etiqueta de lenguaje y bloques vacíos cerrados ('AT_RISK')."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_balance_and_language_hygiene,
    )

    md = (
        "```\n"
        "SELECT * FROM projects;\n"
        "```\n\n"
        "```bash\n"
        "   \n"
        "```\n"
    )
    res = audit_markdown_code_fence_balance_and_language_hygiene(md)
    assert res["total_code_blocks"] == 2
    assert res["compliant_code_blocks"] == 0
    assert res["unclosed_fence_start_lines"] == []
    assert res["untagged_code_block_lines"] == [1]
    assert res["empty_code_block_lines"] == [5]
    assert res["mismatched_closing_fence_lines"] == []
    assert res["fence_hygiene_status"] == "AT_RISK"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_code_fence_balance_and_language_hygiene_critical():
    """Detecta cercas de cierre desalineadas (``` cerrado con ~~~) y bloques sin cerrar al final ('CRITICAL')."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_balance_and_language_hygiene,
    )

    md = (
        "```json\n"
        "{\"ok\": true}\n"
        "~~~\n"
        "```\n\n"
        "```sql\n"
        "SELECT 1;\n"
    )
    res = audit_markdown_code_fence_balance_and_language_hygiene(md)
    assert res["total_code_blocks"] == 2
    assert res["compliant_code_blocks"] == 0
    assert res["mismatched_closing_fence_lines"] == [3]
    assert res["unclosed_fence_start_lines"] == [6]
    assert res["fence_hygiene_status"] == "CRITICAL"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_code_fence_balance_and_language_hygiene_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-str y exposición en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_code_fence_balance_and_language_hygiene,
    )

    for payload in (None, "", 123):
        empty = audit_markdown_code_fence_balance_and_language_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_code_blocks"] == 0
        assert empty["compliant_code_blocks"] == 0
        assert empty["unclosed_fence_start_lines"] == []
        assert empty["untagged_code_block_lines"] == []
        assert empty["empty_code_block_lines"] == []
        assert empty["mismatched_closing_fence_lines"] == []
        assert empty["fence_hygiene_status"] == "HEALTHY"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = "```python\nx = 1\n```\n"
    assert (
        AnyDocService.audit_markdown_code_fence_balance_and_language_hygiene(sample)
        == audit_markdown_code_fence_balance_and_language_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_code_fence_balance_and_language_hygiene(sample)
        == audit_markdown_code_fence_balance_and_language_hygiene(sample)
    )
    assert "audit_markdown_code_fence_balance_and_language_hygiene" in mod.__all__


def test_audit_markdown_frontmatter_and_document_control_hygiene_healthy():
    """Valida frontmatter YAML completo con claves requeridas, versión SemVer y estado aprobado ('HEALTHY')."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_and_document_control_hygiene,
    )

    md = (
        "---\n"
        "title: Plan de Gestión de Configuración\n"
        "owner: PMO Lead\n"
        "version: 1.2.0\n"
        "status: approved\n"
        "---\n\n"
        "# Contenido\n"
    )
    res = audit_markdown_frontmatter_and_document_control_hygiene(md)
    assert res["has_frontmatter"] is True
    assert res["unclosed_frontmatter"] is False
    assert res["parsed_keys"] == ["title", "owner", "version", "status"]
    assert res["missing_or_empty_required_keys"] == []
    assert res["duplicate_frontmatter_keys"] == []
    assert res["malformed_frontmatter_lines"] == []
    assert res["invalid_status_value"] is False
    assert res["invalid_version_format"] is False
    assert res["frontmatter_hygiene_status"] == "HEALTHY"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_markdown_frontmatter_and_document_control_hygiene_critical():
    """Detecta ausencia de frontmatter, frontmatter sin cerrar o claves faltantes/líneas malformadas ('CRITICAL')."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_and_document_control_hygiene,
    )

    no_fm = audit_markdown_frontmatter_and_document_control_hygiene(
        "# Sin frontmatter\nTexto.\n"
    )
    assert no_fm["has_frontmatter"] is False
    assert no_fm["frontmatter_hygiene_status"] == "CRITICAL"
    assert no_fm["is_compliant"] is False

    unclosed = audit_markdown_frontmatter_and_document_control_hygiene(
        "---\ntitle: Abierto\nowner: PM\n"
    )
    assert unclosed["unclosed_frontmatter"] is True
    assert unclosed["frontmatter_hygiene_status"] == "CRITICAL"
    assert unclosed["is_compliant"] is False

    malformed = audit_markdown_frontmatter_and_document_control_hygiene(
        "---\n"
        "title: Especificación\n"
        "linea sin dos puntos\n"
        "owner: \"\"\n"
        "---\n"
    )
    assert malformed["has_frontmatter"] is True
    assert malformed["malformed_frontmatter_lines"] == [3]
    assert "owner" in malformed["missing_or_empty_required_keys"]
    assert "version" in malformed["missing_or_empty_required_keys"]
    assert malformed["frontmatter_hygiene_status"] == "CRITICAL"
    assert malformed["is_compliant"] is False
    assert len(malformed["recommendations"]) >= 2


def test_audit_markdown_frontmatter_and_document_control_hygiene_at_risk():
    """Detecta claves duplicadas, estado inválido o formato de versión no SemVer ('AT_RISK')."""
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_and_document_control_hygiene,
    )

    md = (
        "---\n"
        "title: Manual Operativo\n"
        "owner: Arquitecto\n"
        "owner: Director PMO\n"
        "version: borrador-final\n"
        "status: obsoleto\n"
        "---\n"
    )
    res = audit_markdown_frontmatter_and_document_control_hygiene(md)
    assert res["has_frontmatter"] is True
    assert res["missing_or_empty_required_keys"] == []
    assert res["malformed_frontmatter_lines"] == []
    assert res["duplicate_frontmatter_keys"] == ["owner"]
    assert res["invalid_version_format"] is True
    assert res["invalid_status_value"] is True
    assert res["frontmatter_hygiene_status"] == "AT_RISK"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_markdown_frontmatter_and_document_control_hygiene_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-str y exposición en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_frontmatter_and_document_control_hygiene,
    )

    for payload in (None, "", 42):
        empty = audit_markdown_frontmatter_and_document_control_hygiene(payload)  # type: ignore[arg-type]
        assert empty["has_frontmatter"] is False
        assert empty["frontmatter_hygiene_status"] == "CRITICAL"
        assert empty["is_compliant"] is False
        assert len(empty["recommendations"]) >= 1

    sample = "---\ntitle: Doc\nowner: PM\nversion: v2.0\nstatus: draft\n---\n"
    assert (
        AnyDocService.audit_markdown_frontmatter_and_document_control_hygiene(sample)
        == audit_markdown_frontmatter_and_document_control_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_frontmatter_and_document_control_hygiene(sample)
        == audit_markdown_frontmatter_and_document_control_hygiene(sample)
    )
    assert "audit_markdown_frontmatter_and_document_control_hygiene" in mod.__all__




def test_audit_markdown_badge_and_external_tracker_hygiene_critical():
    """http://, dominios tracker y ramas main/master sin fijar -> CRITICAL."""
    from backend.services.anydoc_service import (
        audit_markdown_badge_and_external_tracker_hygiene,
    )

    res = audit_markdown_badge_and_external_tracker_hygiene(
        "![a](http://example.com/x.svg)\n"
        "![t](https://www.google-analytics.com/collect)\n"
        "![u](https://github.com/org/repo/raw/main/img.png)\n"
        "![b](https://github.com/org/repo/blob/master/y.png)\n"
        "![d](https://node.example.com/pixel?q=1)\n"
    )
    assert res["badge_hygiene_status"] == "CRITICAL"
    assert res["is_compliant"] is False
    assert res["insecure_http_image_lines"] == [1]
    assert res["external_tracker_or_unpinned_branch_lines"] == [2, 3, 4]
    assert res["badge_clutter_lines"] == []
    assert res["total_images_or_badges"] == 5

    # Dominios del bloque case-insensitive y query param branch.
    ci = audit_markdown_badge_and_external_tracker_hygiene(
        "![t](https://WWW.GOOGLE-ANALYTICS.com/x)\n"
        "![b](https://ci.company.io/img.svg?branch=main)\n"
    )
    assert ci["external_tracker_or_unpinned_branch_lines"] == [1, 2]

    # Badge compuesto [![i](img)](link): la URL imagen es la evaluada.
    nested = audit_markdown_badge_and_external_tracker_hygiene(
        "[![build](http://b.io/s.svg)](https://log.io/x)\n"
    )
    assert nested["insecure_http_image_lines"] == [1]
    assert nested["total_images_or_badges"] == 1


def test_audit_markdown_badge_and_external_tracker_hygiene_clutter():
    """Exceso de badges en una linea -> AT_RISK; max custom y limite exacto."""
    from backend.services.anydoc_service import (
        audit_markdown_badge_and_external_tracker_hygiene,
    )

    many = " ".join("![b](https://e.io/b%02d.svg)" % idx for idx in range(6))
    at_risk = audit_markdown_badge_and_external_tracker_hygiene(many + "\n")
    assert at_risk["badge_clutter_lines"] == [1]
    assert at_risk["insecure_http_image_lines"] == []
    assert at_risk["external_tracker_or_unpinned_branch_lines"] == []
    assert at_risk["badge_hygiene_status"] == "AT_RISK"
    assert at_risk["is_compliant"] is False
    assert at_risk["total_images_or_badges"] == 6

    # 4 badges (limite exacto): no es clutter.
    ok = audit_markdown_badge_and_external_tracker_hygiene(
        " ".join("![b](https://e.io/b.svg)" for _ in range(4))
    )
    assert ok["badge_clutter_lines"] == []
    assert ok["badge_hygiene_status"] == "HEALTHY"
    assert ok["is_compliant"] is True

    # max custom 2 con 3 badges -> clutter.
    custom = audit_markdown_badge_and_external_tracker_hygiene(
        "![b](https://e.io/1.svg) ![b](https://e.io/2.svg) ![b](https://e.io/3.svg)",
        max_badges_per_line=2,
    )
    assert custom["badge_clutter_lines"] == [1]
    assert custom["badge_hygiene_status"] == "AT_RISK"


def test_audit_markdown_badge_and_external_tracker_hygiene_ignores_code_and_fences():
    """Code spans inline y fences multi-línea (``` y ~~~) se ignoran; HTTPS/relativas son sanas."""
    from backend.services.anydoc_service import (
        audit_markdown_badge_and_external_tracker_hygiene,
    )

    clean = audit_markdown_badge_and_external_tracker_hygiene(
        "Texto `![img](http://span.io/x.svg)` inline ignorado.\n"
        "```html\n"
        "![img](http://fence.io/x.svg)\n"
        "![t](https://pixel.wp.com/x)\n"
        "```\n"
        "~~~\n"
        "![img](https://x.io/raw/main/z.svg)\n"
        "~~~\n"
        "![ok](https://ok.io/x.svg)\n"
        "![rel](assets/img.png)\n"
    )
    assert clean["badge_hygiene_status"] == "HEALTHY"
    assert clean["is_compliant"] is True
    assert clean["total_images_or_badges"] == 2
    assert clean["insecure_http_image_lines"] == []
    assert clean["external_tracker_or_unpinned_branch_lines"] == []
    assert clean["badge_clutter_lines"] == []

    # Reset de fence: tras cerrar vuelve a auditar.
    reset = audit_markdown_badge_and_external_tracker_hygiene(
        "```\n"
        "![img](http://inside.io/a.svg)\n"
        "```\n"
        "![after](http://outside.io/b.svg)\n"
    )
    assert reset["insecure_http_image_lines"] == [4]
    assert reset["badge_hygiene_status"] == "CRITICAL"


def test_audit_markdown_badge_and_external_tracker_hygiene_neutral_and_binding():
    """None/vacio/whitespace -> vacio; proxys estaticos y __all__."""
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_badge_and_external_tracker_hygiene,
    )
    import backend.services.anydoc_service as mod

    for payload in (None, "", "   \n\t"):
        empty = audit_markdown_badge_and_external_tracker_hygiene(payload)
        assert empty["total_images_or_badges"] == 0
        assert empty["insecure_http_image_lines"] == []
        assert empty["external_tracker_or_unpinned_branch_lines"] == []
        assert empty["badge_clutter_lines"] == []
        assert empty["badge_hygiene_status"] == "HEALTHY"
        assert empty["is_compliant"] is True

    sample = "![b](https://e.io/x.svg)"
    assert (
        AnyDocService.audit_markdown_badge_and_external_tracker_hygiene(sample)
        == audit_markdown_badge_and_external_tracker_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_badge_and_external_tracker_hygiene(sample)
        == audit_markdown_badge_and_external_tracker_hygiene(sample)
    )
    assert "audit_markdown_badge_and_external_tracker_hygiene" in mod.__all__


def test_audit_markdown_footnote_reference_and_definition_hygiene_clean():
    """Valida simetría limpia entre referencias [^id] y definiciones [^id]: texto, ignorando fences y code spans ('CLEAN')."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_and_definition_hygiene,
    )

    md = (
        "El Acta de Constitución[^charter] y la línea base[^baseline] están aprobadas.\n"
        "En código inline `[^ignored_inline]` no cuenta.\n"
        "```markdown\n"
        "Referencia en bloque [^ignored_fence]\n"
        "[^ignored_def]: Definición dentro de fence\n"
        "```\n\n"
        "[^charter]: Aprobado por el Comité Ejecutivo en enero.\n"
        "[^baseline]: Consolidada según PMBOK §4.2.\n"
    )
    res = audit_markdown_footnote_reference_and_definition_hygiene(md)
    assert res["total_references"] == 2
    assert res["total_definitions"] == 2
    assert res["unresolved_reference_ids"] == []
    assert res["unused_definition_ids"] == []
    assert res["duplicate_definition_ids"] == []
    assert res["empty_definition_ids"] == []
    assert res["footnote_hygiene_status"] == "CLEAN"
    assert res["is_compliant"] is True
    assert res["issues"] == []


def test_audit_markdown_footnote_reference_and_definition_hygiene_broken():
    """Detecta referencias sin definición, definiciones duplicadas y definiciones vacías ('BROKEN_REFERENCES')."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_and_definition_hygiene,
    )

    md = (
        "Texto con referencia huérfana[^missing], duplicada[^dup] y vacía[^empty].\n\n"
        "[^dup]: Primera definición.\n"
        "[^dup]: Segunda definición repetida.\n"
        "[^empty]:    \n"
    )
    res = audit_markdown_footnote_reference_and_definition_hygiene(md)
    assert res["unresolved_reference_ids"] == ["missing"]
    assert res["duplicate_definition_ids"] == ["dup"]
    assert res["empty_definition_ids"] == ["empty"]
    assert res["footnote_hygiene_status"] == "BROKEN_REFERENCES"
    assert res["is_compliant"] is False
    assert len(res["issues"]) >= 3


def test_audit_markdown_footnote_reference_and_definition_hygiene_unused():
    """Detecta definiciones de notas al pie que nunca son referenciadas en el texto ('UNUSED_DEFINITIONS')."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_reference_and_definition_hygiene,
    )

    md = (
        "Documento con cita activa[^active].\n\n"
        "[^active]: Referencia utilizada correctamente.\n"
        "[^orphan]: Nota al pie definida pero nunca citada.\n"
    )
    res = audit_markdown_footnote_reference_and_definition_hygiene(md)
    assert res["unresolved_reference_ids"] == []
    assert res["duplicate_definition_ids"] == []
    assert res["empty_definition_ids"] == []
    assert res["unused_definition_ids"] == ["orphan"]
    assert res["footnote_hygiene_status"] == "UNUSED_DEFINITIONS"
    assert res["is_compliant"] is False
    assert len(res["issues"]) == 1


def test_audit_markdown_footnote_reference_and_definition_hygiene_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/None y exposición en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_footnote_reference_and_definition_hygiene,
    )

    for payload in (None, "", "   \n\t"):
        empty = audit_markdown_footnote_reference_and_definition_hygiene(payload)
        assert empty["total_references"] == 0
        assert empty["total_definitions"] == 0
        assert empty["footnote_hygiene_status"] == "CLEAN"
        assert empty["is_compliant"] is True
        assert empty["issues"] == []

    sample = "Cita[^1].\n\n[^1]: Fuente oficial."
    assert (
        AnyDocService.audit_markdown_footnote_reference_and_definition_hygiene(
            sample
        )
        == audit_markdown_footnote_reference_and_definition_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_footnote_reference_and_definition_hygiene(
            sample
        )
        == audit_markdown_footnote_reference_and_definition_hygiene(sample)
    )
    assert (
        "audit_markdown_footnote_reference_and_definition_hygiene"
        in mod.__all__
    )


def test_audit_markdown_acronym_glossary_first_use_compliant():
    """Inline '(ACR)' / 'ACR (' y glosario '**ACR**:'/'| ACR |' -> COMPLIANT."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_first_use_hygiene,
    )

    ok = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "El servicio SLA (Service Level Agreement) se mide.\n"
        "- **KPI**: indicador clave.\n"
        "El KPI aplica.\n"
        "| EVM | Earned Value Management |\n"
    )
    assert ok["total_distinct_acronyms"] == 3
    assert ok["defined_acronyms"] == ["EVM", "KPI", "SLA"]
    assert ok["undefined_acronyms"] == []
    assert ok["first_use_line_by_undefined_acronym"] == {}
    assert ok["acronym_hygiene_status"] == "COMPLIANT"
    assert ok["is_compliant"] is True

    # 'ACR (' en línea de primera aparición.
    inline = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "Activamos EAC (Estimate at Completion) ahora.\n"
    )
    assert inline["defined_acronyms"] == ["EAC"]
    assert inline["is_compliant"] is True


def test_audit_markdown_acronym_glossary_first_use_gaps_and_thresholds():
    """1-2 indefinidos -> MINOR_GAPS con línea de primera aparición; >= 3 -> GLOSSARY_REQUIRED."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_first_use_hygiene,
    )

    minor = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "El EVM (Earned Value Management) y el CCB operan juntos.\n"
        "El CCB sigue en línea 2.\n"
    )
    assert minor["defined_acronyms"] == ["EVM"]
    assert minor["undefined_acronyms"] == ["CCB"]
    assert minor["first_use_line_by_undefined_acronym"] == {"CCB": 1}
    assert minor["acronym_hygiene_status"] == "MINOR_GAPS"
    assert minor["is_compliant"] is False

    # 2 indefinidos siguen en MINOR_GAPS.
    two = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "El CCB y el PMO se reúnen.\n"
    )
    assert sorted(two["undefined_acronyms"]) == ["CCB", "PMO"]
    assert two["first_use_line_by_undefined_acronym"] == {"CCB": 1, "PMO": 1}
    assert two["acronym_hygiene_status"] == "MINOR_GAPS"

    # 3 indefinidos -> GLOSSARY_REQUIRED.
    required = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "El CCB, el PMO y el RACI participan.\n"
    )
    assert sorted(required["undefined_acronyms"]) == ["CCB", "PMO", "RACI"]
    assert required["acronym_hygiene_status"] == "GLOSSARY_REQUIRED"


def test_audit_markdown_acronym_glossary_exempt_and_code_ignores():
    """Exentos (API/HTML/etc. case-insensitive) y fences/code spans se ignoran; límites de longitud."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_and_glossary_first_use_hygiene,
    )

    exempt = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "La API y el https y el JSON listos.\n"
        "BFF sin definir.\n"
    )
    assert "BFF" in exempt["undefined_acronyms"]
    assert "API" not in exempt["undefined_acronyms"]
    assert "JSON" not in exempt["undefined_acronyms"]

    # Comparación invariant-case de exentos.
    ci = audit_markdown_acronym_and_glossary_first_use_hygiene("API una vez; api no es token del patrón.\n")
    assert "API" not in ci["defined_acronyms"] and "API" not in ci["undefined_acronyms"]

    clean = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "Texto con `PMO y BFF` en code span ignorado.\n"
        "```\n"
        "RACI y PMO en fence ignorado\n"
        "```\n"
        "~~~\n"
        "BFF también en tilde fence\n"
        "~~~\n"
        "Sin acrónimos activos.\n"
    )
    assert clean["total_distinct_acronyms"] == 0
    assert clean["is_compliant"] is True

    # min custom: 2 letras se detectan.
    short = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "OK y QA revisan.\n",
        min_acronym_length=2,
    )
    assert "OK" in short["undefined_acronyms"]
    assert "QA" in short["undefined_acronyms"]

    # 9 letras exceden el techo de 8: no detectado.
    long_token = audit_markdown_acronym_and_glossary_first_use_hygiene(
        "DISCIPLINA no es un acrónimo del patrón (10 letras).\n"
    )
    assert long_token["total_distinct_acronyms"] == 0


def test_audit_markdown_acronym_glossary_neutral_and_binding():
    """None/vacío/whitespace -> vacío; doble proxy estático y entrada en __all__."""
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_acronym_and_glossary_first_use_hygiene,
    )
    import backend.services.anydoc_service as mod

    for payload in (None, "", "   \n\t"):
        empty = audit_markdown_acronym_and_glossary_first_use_hygiene(payload)
        assert empty["total_distinct_acronyms"] == 0
        assert empty["defined_acronyms"] == []
        assert empty["undefined_acronyms"] == []
        assert empty["first_use_line_by_undefined_acronym"] == {}
        assert empty["acronym_hygiene_status"] == "COMPLIANT"
        assert empty["is_compliant"] is True

    sample = "El EVM (Earned Value Management) sigue.\n"
    assert (
        AnyDocService.audit_markdown_acronym_and_glossary_first_use_hygiene(sample)
        == audit_markdown_acronym_and_glossary_first_use_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_acronym_and_glossary_first_use_hygiene(sample)
        == audit_markdown_acronym_and_glossary_first_use_hygiene(sample)
    )
    assert "audit_markdown_acronym_and_glossary_first_use_hygiene" in mod.__all__


def test_audit_markdown_mermaid_diagram_syntax_hygiene_clean():
    """Caso 1: Bloques mermaid bien formados, tipos válidos y sin HTML crudo -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_hygiene,
    )

    md = (
        "# Arquitectura\n\n"
        "```mermaid\n"
        "%% Comentario inicial\n"
        "flowchart TD\n"
        '    A["Inicio (PMO)"] --> B{"Aprobado?"}\n'
        "```\n\n"
        "~~~Mermaid\n"
        "sequenceDiagram\n"
        "    Alice->>Bob: Hola\n"
        "~~~\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_hygiene(md)
    assert res["total_mermaid_blocks"] == 2
    assert res["empty_mermaid_block_lines"] == []
    assert res["unsupported_diagram_type_lines"] == []
    assert res["unbalanced_bracket_block_lines"] == []
    assert res["raw_html_tag_block_lines"] == []
    assert res["mermaid_hygiene_status"] == "CLEAN"
    assert res["is_compliant"] is True
    assert res["issues"] == []


def test_audit_markdown_mermaid_diagram_syntax_hygiene_syntax_errors():
    """Caso 2: Bloque vacío, tipo no soportado o corchetes desbalanceados -> SYNTAX_ERROR."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_hygiene,
    )

    md = (
        "```mermaid\n"
        "%% solo comentario\n"
        "\n"
        "```\n"
        "```mermaid\n"
        "unknownDiagram\n"
        "    A --> B\n"
        "```\n"
        "```mermaid\n"
        "flowchart LR\n"
        "    A[Nodo sin cerrar --> B(Otro)\n"
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_hygiene(md)
    assert res["total_mermaid_blocks"] == 3
    assert res["empty_mermaid_block_lines"] == [1]
    assert res["unsupported_diagram_type_lines"] == [5]
    assert res["unbalanced_bracket_block_lines"] == [9]
    assert res["mermaid_hygiene_status"] == "SYNTAX_ERROR"
    assert res["is_compliant"] is False
    assert len(res["issues"]) >= 3


def test_audit_markdown_mermaid_diagram_syntax_hygiene_style_warning():
    """Caso 3: Diagrama válido pero con etiquetas HTML crudas (<br>, <b>, etc.) -> STYLE_WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_hygiene,
    )

    md = (
        "Intro\n"
        "```mermaid\n"
        "flowchart TD\n"
        '    A["Línea 1<br/>Línea 2"] --> B["<b>Título</b>"]\n'
        "```\n"
    )
    res = audit_markdown_mermaid_diagram_syntax_hygiene(md)
    assert res["total_mermaid_blocks"] == 1
    assert res["empty_mermaid_block_lines"] == []
    assert res["unsupported_diagram_type_lines"] == []
    assert res["unbalanced_bracket_block_lines"] == []
    assert res["raw_html_tag_block_lines"] == [2]
    assert res["mermaid_hygiene_status"] == "STYLE_WARNING"
    assert res["is_compliant"] is False
    assert len(res["issues"]) >= 1


def test_audit_markdown_mermaid_diagram_syntax_hygiene_empty_and_binding():
    """Caso 4: Entradas vacías/None y exposición en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_mermaid_diagram_syntax_hygiene,
    )

    for payload in (None, "", "   \n", "```python\nprint(1)\n```\n"):
        empty = audit_markdown_mermaid_diagram_syntax_hygiene(payload)
        assert empty["total_mermaid_blocks"] == 0
        assert empty["empty_mermaid_block_lines"] == []
        assert empty["unsupported_diagram_type_lines"] == []
        assert empty["unbalanced_bracket_block_lines"] == []
        assert empty["raw_html_tag_block_lines"] == []
        assert empty["mermaid_hygiene_status"] == "CLEAN"
        assert empty["is_compliant"] is True
        assert empty["issues"] == []

    sample = "```mermaid\ngraph LR\n    A --> B\n```\n"
    assert (
        AnyDocService.audit_markdown_mermaid_diagram_syntax_hygiene(sample)
        == audit_markdown_mermaid_diagram_syntax_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_mermaid_diagram_syntax_hygiene(sample)
        == audit_markdown_mermaid_diagram_syntax_hygiene(sample)
    )
    assert "audit_markdown_mermaid_diagram_syntax_hygiene" in mod.__all__


def test_audit_markdown_task_list_action_item_hygiene_clean():
    """Caso 1: Tareas cerradas y abiertas con propietario (@usuario o owner:) y fecha ISO/due: -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    md = (
        "# Plan de Acción\n\n"
        "- [x] Revisar acta de constitución\n"
        "- [ ] Actualizar matriz RACI @ana.perez 2026-11-15\n"
        "* [ ] Validar presupuesto owner: carlos due: 2026-12-01\n"
        "```markdown\n"
        "- [ ] Ignorado en bloque cercado\n"
        "```\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(md)
    assert res["total_tasks"] == 3
    assert res["completed_tasks_count"] == 1
    assert res["open_tasks_count"] == 2
    assert res["completion_rate_pct"] == 33.33
    assert res["empty_description_task_lines"] == []
    assert res["unassigned_open_task_lines"] == []
    assert res["undated_open_task_lines"] == []
    assert res["task_list_hygiene_status"] == "CLEAN"
    assert res["is_compliant"] is True
    assert res["issues"] == []


def test_audit_markdown_task_list_action_item_hygiene_untracked_open_items():
    """Caso 2: Tareas abiertas sin responsable o sin fecha -> UNTRACKED_OPEN_ITEMS."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    md = (
        "- [ ] Tarea sin dueño pero con fecha 2026-11-20\n"
        "- [ ] Tarea con @pedro pero sin fecha\n"
        "- [X] Tarea completada sin metadatos\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(md)
    assert res["total_tasks"] == 3
    assert res["completed_tasks_count"] == 1
    assert res["open_tasks_count"] == 2
    assert res["empty_description_task_lines"] == []
    assert res["unassigned_open_task_lines"] == [1]
    assert res["undated_open_task_lines"] == [2]
    assert res["task_list_hygiene_status"] == "UNTRACKED_OPEN_ITEMS"
    assert res["is_compliant"] is False
    assert len(res["issues"]) >= 2


def test_audit_markdown_task_list_action_item_hygiene_empty_tasks():
    """Caso 3: Tarea con descripción vacía domina -> EMPTY_TASKS."""
    from backend.services.anydoc_service import (
        audit_markdown_task_list_action_item_hygiene,
    )

    md = (
        "- [ ]    \n"
        "1. [x] \n"
        "- [ ] Tarea abierta sin dueño ni fecha\n"
    )
    res = audit_markdown_task_list_action_item_hygiene(md)
    assert res["total_tasks"] == 3
    assert res["empty_description_task_lines"] == [1, 2]
    assert res["unassigned_open_task_lines"] == [3]
    assert res["undated_open_task_lines"] == [3]
    assert res["task_list_hygiene_status"] == "EMPTY_TASKS"
    assert res["is_compliant"] is False
    assert len(res["issues"]) >= 2


def test_audit_markdown_task_list_action_item_hygiene_empty_and_binding():
    """Caso 4: Entradas vacías/None y exposición en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_task_list_action_item_hygiene,
    )

    for payload in (None, "", "   \n", "Texto sin tareas\n"):
        empty = audit_markdown_task_list_action_item_hygiene(payload)
        assert empty["total_tasks"] == 0
        assert empty["completed_tasks_count"] == 0
        assert empty["open_tasks_count"] == 0
        assert empty["completion_rate_pct"] == 100.0
        assert empty["empty_description_task_lines"] == []
        assert empty["unassigned_open_task_lines"] == []
        assert empty["undated_open_task_lines"] == []
        assert empty["task_list_hygiene_status"] == "CLEAN"
        assert empty["is_compliant"] is True
        assert empty["issues"] == []

    sample = "- [ ] Cerrar entregable responsable: maria vence: 2026-10-30\n"
    assert (
        AnyDocService.audit_markdown_task_list_action_item_hygiene(sample)
        == audit_markdown_task_list_action_item_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_task_list_action_item_hygiene(sample)
        == audit_markdown_task_list_action_item_hygiene(sample)
    )
    assert "audit_markdown_task_list_action_item_hygiene" in mod.__all__


def test_audit_markdown_code_fence_and_secret_leak_hygiene_clean():
    """Caso 1: Bloques cercados etiquetados, cerrados, cortos y con placeholders seguros -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_and_secret_leak_hygiene,
    )

    md = (
        "# Guía de Configuración\n\n"
        "```python\n"
        'api_key = "YOUR_API_KEY"\n'
        'password = "<token>"\n'
        "```\n\n"
        "~~~bash\n"
        "echo 'ok'\n"
        "~~~\n"
    )
    res = audit_markdown_code_fence_and_secret_leak_hygiene(
        md, max_code_block_lines=120
    )
    assert res["total_code_blocks"] == 2
    assert res["tagged_code_blocks"] == 2
    assert res["untagged_code_block_lines"] == []
    assert res["unclosed_code_block_line"] is None
    assert res["oversized_code_block_lines"] == []
    assert res["potential_secret_leak_lines"] == []
    assert res["code_hygiene_status"] == "CLEAN"
    assert res["recommendations"] == []


def test_audit_markdown_code_fence_and_secret_leak_hygiene_warning():
    """Caso 2: Bloque sin lenguaje o bloque demasiado largo sin fugas ni bloque sin cerrar -> WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_and_secret_leak_hygiene,
    )

    md = (
        "```\n"
        "linea 1\n"
        "```\n"
        "```python\n"
        "l1\n"
        "l2\n"
        "l3\n"
        "l4\n"
        "```\n"
    )
    res = audit_markdown_code_fence_and_secret_leak_hygiene(
        md, max_code_block_lines=3
    )
    assert res["total_code_blocks"] == 2
    assert res["tagged_code_blocks"] == 1
    assert res["untagged_code_block_lines"] == [1]
    assert res["unclosed_code_block_line"] is None
    assert res["oversized_code_block_lines"] == [4]
    assert res["potential_secret_leak_lines"] == []
    assert res["code_hygiene_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_code_fence_and_secret_leak_hygiene_critical():
    """Caso 3: Fuga de secretos (AKIA, ghp_, PRIVATE KEY o password real) o bloque no cerrado -> CRITICAL."""
    from backend.services.anydoc_service import (
        audit_markdown_code_fence_and_secret_leak_hygiene,
    )

    md = (
        "```env\n"
        "AWS_KEY=AKIA1234567890ABCDEF\n"
        'password = "SuperSecretProd9988"\n'
        "```\n"
        "```bash\n"
        "curl -H 'Authorization: Bearer ghp_1234567890abcdefghijklmnop'\n"
    )
    res = audit_markdown_code_fence_and_secret_leak_hygiene(md)
    assert res["total_code_blocks"] == 2
    assert res["unclosed_code_block_line"] == 5
    assert res["potential_secret_leak_lines"] == [2, 3, 6]
    assert res["code_hygiene_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_code_fence_and_secret_leak_hygiene_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_code_fence_and_secret_leak_hygiene,
    )

    for payload in (None, "", "   \n"):
        empty = audit_markdown_code_fence_and_secret_leak_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_code_blocks"] == 0
        assert empty["tagged_code_blocks"] == 0
        assert empty["untagged_code_block_lines"] == []
        assert empty["unclosed_code_block_line"] is None
        assert empty["oversized_code_block_lines"] == []
        assert empty["potential_secret_leak_lines"] == []
        assert empty["code_hygiene_status"] == "CLEAN"
        assert empty["recommendations"] == []

    sample = "```json\n{\"ok\": true}\n```\n"
    assert (
        AnyDocService.audit_markdown_code_fence_and_secret_leak_hygiene(sample)
        == audit_markdown_code_fence_and_secret_leak_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_code_fence_and_secret_leak_hygiene(sample)
        == audit_markdown_code_fence_and_secret_leak_hygiene(sample)
    )
    assert "audit_markdown_code_fence_and_secret_leak_hygiene" in mod.__all__


def test_audit_markdown_admonition_callout_and_actionability_hygiene_clean():
    """Caso 1: Callouts GitHub-style bien espaciados, tipos canónicos y baja densidad -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_and_actionability_hygiene,
    )

    md = (
        "# Guía Operativa de Despliegue\n\n"
        "Antes de iniciar la ventana de mantenimiento verifique los backups.\n"
        "Asegúrese de contar con la firma del CAB.\n"
        "Valide las métricas base de latencia p95.\n\n"
        "> [!NOTE]\n"
        "> El mantenimiento estándar dura 30 minutos.\n\n"
        "Durante la ejecución monitoree los paneles de observabilidad.\n"
        "Si la tasa de error supera el 1%, ejecute el plan de rollback.\n"
        "Registre la evidencia en el acta de cierre.\n"
        "Notifique al canal de operaciones al finalizar.\n"
    )
    res = audit_markdown_admonition_callout_and_actionability_hygiene(
        md, max_alert_density_pct=30.0
    )
    assert res["valid_callouts_count"] == 1
    assert res["invalid_callout_type_lines"] == []
    assert res["empty_callout_body_lines"] == []
    assert res["consecutive_callout_lines"] == []
    assert res["alert_line_share_pct"] == 20.0
    assert res["callout_hygiene_status"] == "CLEAN"
    assert res["recommendations"] == []


def test_audit_markdown_admonition_callout_and_actionability_hygiene_warning():
    """Caso 2: Callouts consecutivos sin párrafo intermedio y densidad alta -> WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_and_actionability_hygiene,
    )

    md = (
        "# Runbook\n\n"
        "> [!TIP]\n"
        "> Use conexiones persistentes.\n\n"
        "> [!WARNING]\n"
        "> No reinicie el nodo primario en horario pico.\n"
    )
    res = audit_markdown_admonition_callout_and_actionability_hygiene(
        md, max_alert_density_pct=30.0
    )
    assert res["valid_callouts_count"] == 2
    assert res["invalid_callout_type_lines"] == []
    assert res["empty_callout_body_lines"] == []
    assert res["consecutive_callout_lines"] == [6]
    assert res["alert_line_share_pct"] == 80.0
    assert res["callout_hygiene_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_admonition_callout_and_actionability_hygiene_critical():
    """Caso 3: Tipo de callout no canónico (> [!DANGER]) y callout válido vacío -> CRITICAL."""
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_and_actionability_hygiene,
    )

    md = (
        "# Manual de Seguridad\n\n"
        "Introducción general.\n\n"
        "> [!DANGER]\n"
        "> Esta sintaxis no es válida en GitHub Flavored Markdown.\n\n"
        "Párrafo intermedio explicativo.\n\n"
        "> [!IMPORTANT]\n\n"
        "Cierre del documento.\n"
    )
    res = audit_markdown_admonition_callout_and_actionability_hygiene(md)
    assert res["valid_callouts_count"] == 1
    assert res["invalid_callout_type_lines"] == [5]
    assert res["empty_callout_body_lines"] == [10]
    assert res["callout_hygiene_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_admonition_callout_and_actionability_hygiene_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_admonition_callout_and_actionability_hygiene,
    )

    for payload in (None, "", "   \n"):
        empty = audit_markdown_admonition_callout_and_actionability_hygiene(payload)  # type: ignore[arg-type]
        assert empty["valid_callouts_count"] == 0
        assert empty["invalid_callout_type_lines"] == []
        assert empty["empty_callout_body_lines"] == []
        assert empty["consecutive_callout_lines"] == []
        assert empty["alert_line_share_pct"] == 0.0
        assert empty["callout_hygiene_status"] == "CLEAN"
        assert empty["recommendations"] == []

    sample = "# Doc\n\nPárrafo 1\nPárrafo 2\nPárrafo 3\nPárrafo 4\n\n> [!CAUTION]\n> Revisar credenciales.\n"
    assert (
        AnyDocService.audit_markdown_admonition_callout_and_actionability_hygiene(sample)
        == audit_markdown_admonition_callout_and_actionability_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_admonition_callout_and_actionability_hygiene(sample)
        == audit_markdown_admonition_callout_and_actionability_hygiene(sample)
    )
    assert (
        "audit_markdown_admonition_callout_and_actionability_hygiene" in mod.__all__
    )


def test_audit_markdown_heading_anchor_slug_and_fragment_hygiene_clean():
    """Caso 1: Encabezados únicos y enlaces internos #fragment que resuelven correctamente -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_anchor_slug_and_fragment_hygiene,
    )

    md = (
        "# Manual de Arquitectura\n\n"
        "Ver [Requisitos de Red](#requisitos-de-red) y [Seguridad API](#seguridad-api).\n\n"
        "```markdown\n"
        "# Requisitos de Red\n"
        "[Enlace ignorado en bloque de código](#no-existe)\n"
        "```\n\n"
        "## Requisitos de Red\n"
        "Detalle de topología.\n\n"
        "## Seguridad API!\n"
        "Detalle de OAuth2.\n"
    )
    res = audit_markdown_heading_anchor_slug_and_fragment_hygiene(md)
    assert res["total_headings"] == 3
    assert res["duplicate_heading_slugs"] == []
    assert res["total_internal_fragment_links"] == 2
    assert res["broken_fragment_targets"] == []
    assert res["anchor_hygiene_status"] == "CLEAN"
    assert res["is_anchor_hygiene_clean"] is True
    assert res["recommendations"] == []


def test_audit_markdown_heading_anchor_slug_and_fragment_hygiene_warning():
    """Caso 2: Slugs de encabezado duplicados pero todos los enlaces #fragment resuelven (incluyendo -1) -> WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_anchor_slug_and_fragment_hygiene,
    )

    md = (
        "# Guía de Servicios\n\n"
        "Ir a [Configuración Inicial](#configuracin-1).\n\n"
        "## Configuración\n"
        "Módulo A.\n\n"
        "## Configuración\n"
        "Módulo B.\n"
    )
    # Con soporte unicode o ascii: probemos con un slug sin tildes ambiguas
    md_ascii = (
        "# Guia de Servicios\n\n"
        "Ir a [Configuracion B](#configuracion-1).\n\n"
        "## Configuracion\n"
        "Modulo A.\n\n"
        "## Configuracion\n"
        "Modulo B.\n"
    )
    res = audit_markdown_heading_anchor_slug_and_fragment_hygiene(md_ascii)
    assert res["total_headings"] == 3
    assert res["duplicate_heading_slugs"] == ["configuracion"]
    assert res["total_internal_fragment_links"] == 1
    assert res["broken_fragment_targets"] == []
    assert res["anchor_hygiene_status"] == "WARNING"
    assert res["is_anchor_hygiene_clean"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_markdown_heading_anchor_slug_and_fragment_hygiene_critical():
    """Caso 3: Enlaces internos #fragment rotos o vacíos (#) -> CRITICAL."""
    from backend.services.anydoc_service import (
        audit_markdown_heading_anchor_slug_and_fragment_hygiene,
    )

    md = (
        "# Plan de Contingencia\n\n"
        "Consulte [Fase de Rollback](#fase-de-rollback) o [Vacío](#).\n\n"
        "## Fase de Deteccion\n"
        "Alertas tempranas.\n"
    )
    res = audit_markdown_heading_anchor_slug_and_fragment_hygiene(md)
    assert res["total_headings"] == 2
    assert res["total_internal_fragment_links"] == 2
    assert res["broken_fragment_targets"] == ["#fase-de-rollback", "#"]
    assert res["anchor_hygiene_status"] == "CRITICAL"
    assert res["is_anchor_hygiene_clean"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_markdown_heading_anchor_slug_and_fragment_hygiene_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en AnyDocService, AnydocService y __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_heading_anchor_slug_and_fragment_hygiene,
    )

    for payload in (None, "", "   \n"):
        empty = audit_markdown_heading_anchor_slug_and_fragment_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_headings"] == 0
        assert empty["duplicate_heading_slugs"] == []
        assert empty["total_internal_fragment_links"] == 0
        assert empty["broken_fragment_targets"] == []
        assert empty["anchor_hygiene_status"] == "CLEAN"
        assert empty["is_anchor_hygiene_clean"] is True
        assert empty["recommendations"] == []

    sample = "# Seccion Uno\n\nVer [Uno](#seccion-uno).\n"
    assert (
        AnyDocService.audit_markdown_heading_anchor_slug_and_fragment_hygiene(sample)
        == audit_markdown_heading_anchor_slug_and_fragment_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_heading_anchor_slug_and_fragment_hygiene(sample)
        == audit_markdown_heading_anchor_slug_and_fragment_hygiene(sample)
    )
    assert (
        "audit_markdown_heading_anchor_slug_and_fragment_hygiene" in mod.__all__
    )


def test_audit_markdown_table_parity_critical_paths():
    """Caso 1: filas desbalanceadas y bloque sin separador -> CRITICAL con números de línea."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_empty_cell_hygiene,
    )

    md = "\n".join(
        [
            "| A | B | C |",      # 1
            "|---|---|---|",      # 2
            "| 1 | 2 | 3 |",      # 3
            "| 4 | 5 |",          # 4  (desbalanceada)
            "",                   # 5
            "| X | Y |",          # 6 (sin separador)
        ]
    )
    res = audit_markdown_table_column_parity_and_empty_cell_hygiene(md)
    assert res["total_tables"] == 2
    assert res["mismatched_column_row_lines"] == [4]
    assert res["missing_separator_table_lines"] == [6]
    assert res["wide_table_header_lines"] == []
    assert res["empty_cell_ratio_pct"] == 0.0
    assert res["table_hygiene_status"] == "CRITICAL"
    assert res["is_table_hygiene_clean"] is False
    assert len(res["recommendations"]) == 2


def test_audit_markdown_table_parity_warning_paths():
    """Caso 2: tabla ancha o ratio de celdas vacías/placeholder -> WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_empty_cell_hygiene,
    )

    wide_header_cells = [f"C{i}" for i in range(1, 12)]
    md_wide = (
        "| " + " | ".join(wide_header_cells) + " |\n"
        "| " + " | ".join("-" * 3 for _ in range(11)) + " |\n"
        "| " + " | ".join("d" for _ in range(11)) + " |"
    )
    res_wide = audit_markdown_table_column_parity_and_empty_cell_hygiene(md_wide)
    assert res_wide["wide_table_header_lines"] == [1]
    assert res_wide["empty_cell_ratio_pct"] == 0.0
    assert res_wide["table_hygiene_status"] == "WARNING"
    assert res_wide["is_table_hygiene_clean"] is False

    md_empty = "\n".join(
        [
            "| A | B | C | D |",
            "|---|---|---|---|",
            "| 1 |   | - | 4 |",
            "| 5 | n/a | 7 | TBD |",
        ]
    )
    res_empty = audit_markdown_table_column_parity_and_empty_cell_hygiene(md_empty)
    assert res_empty["total_tables"] == 1
    assert res_empty["empty_cell_ratio_pct"] == 50.0
    assert res_empty["table_hygiene_status"] == "WARNING"
    assert len(res_empty["recommendations"]) == 1


def test_audit_markdown_table_parity_clean_and_boundaries():
    """Caso 3: tabla bien formada con ratio en la frontera -> CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_empty_cell_hygiene,
    )

    md = "\n".join(
        [
            "| A | B | C |",     # header 3 cols
            "|---|---|---|",     # separador válido
            "| 1 | 2 | 3 |",
            "|   | x | y |",     # 1 vacía de 7 celdas de datos -> 14.29% <= 20
            "",
            "texto normal fuera de tabla",
        ]
    )
    res = audit_markdown_table_column_parity_and_empty_cell_hygiene(md)
    assert res["total_tables"] == 1
    assert res["mismatched_column_row_lines"] == []
    assert res["missing_separator_table_lines"] == []
    assert res["wide_table_header_lines"] == []
    assert res["empty_cell_ratio_pct"] == round(1 / 6 * 100, 2)
    assert res["table_hygiene_status"] == "CLEAN"
    assert res["is_table_hygiene_clean"] is True
    assert res["recommendations"] == []


def test_audit_markdown_table_parity_fences_and_invalid_and_binding():
    """Caso 4: tablas dentro de fenced se ignoran, entradas no-str y binding + __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_table_column_parity_and_empty_cell_hygiene,
    )

    md = "\n".join(
        [
            "```",
            "| R | T |",
            "|---|---|",
            "| 1 | 2 |",
            "```",
            "~~~",
            "| R | T | s |",
            "~~~",
        ]
    )
    res = audit_markdown_table_column_parity_and_empty_cell_hygiene(md)
    assert res["total_tables"] == 0
    assert res["missing_separator_table_lines"] == []
    assert res["mismatched_column_row_lines"] == []
    assert res["table_hygiene_status"] == "CLEAN"

    for payload in (None, "", 123, ["lista"]):
        empty = audit_markdown_table_column_parity_and_empty_cell_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_tables"] == 0
        assert empty["empty_cell_ratio_pct"] == 0.0
        assert empty["table_hygiene_status"] == "CLEAN"
        assert empty["is_table_hygiene_clean"] is True
        assert empty["recommendations"] == []

    valid = "| A | B |\n|---|---|\n| 1 | 2 |"
    assert (
        AnyDocService.audit_markdown_table_column_parity_and_empty_cell_hygiene(valid)
        == audit_markdown_table_column_parity_and_empty_cell_hygiene(valid)
    )
    assert (
        AnydocService.audit_markdown_table_column_parity_and_empty_cell_hygiene(valid)
        == audit_markdown_table_column_parity_and_empty_cell_hygiene(valid)
    )
    assert "audit_markdown_table_column_parity_and_empty_cell_hygiene" in mod.__all__


def test_audit_markdown_blockquote_attribution_and_nesting_hygiene_critical_empty():
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_attribution_and_nesting_hygiene,
    )

    md = (
        "# Executive Summary\n"
        ">   \n"
        "> > \n"
        "\n"
        "> Valid quote line\n"
    )
    res = audit_markdown_blockquote_attribution_and_nesting_hygiene(md)
    assert res["total_blockquotes"] == 2
    assert res["empty_blockquote_start_lines"] == [2]
    assert res["blockquote_hygiene_status"] == "CRITICAL"
    assert res["is_blockquote_hygiene_clean"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_markdown_blockquote_attribution_and_nesting_hygiene_warning_depth_and_oversized():
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_attribution_and_nesting_hygiene,
    )

    md = (
        "> Level 1\n"
        ">> Level 2\n"
        ">>> Level 3 too deep\n"
        "> > > > Level 4 too deep\n"
    )
    res = audit_markdown_blockquote_attribution_and_nesting_hygiene(
        md,
        max_nesting_depth=2,
        max_quote_block_lines=3,
    )
    assert res["total_blockquotes"] == 1
    assert res["deeply_nested_quote_lines"] == [3, 4]
    assert res["oversized_quote_start_lines"] == [1]
    assert res["empty_blockquote_start_lines"] == []
    assert res["blockquote_hygiene_status"] == "WARNING"
    assert res["is_blockquote_hygiene_clean"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_markdown_blockquote_attribution_and_nesting_hygiene_ignores_fences_and_callouts():
    from backend.services.anydoc_service import (
        audit_markdown_blockquote_attribution_and_nesting_hygiene,
    )

    md = (
        "```markdown\n"
        ">>> inside code fence\n"
        ">\n"
        "```\n"
        "> [!NOTE]\n"
        "> This is a GitHub alert callout, not a standard blockquote.\n"
        "\n"
        "> Standard clean blockquote.\n"
        ">> Nested level 2 allowed.\n"
    )
    res = audit_markdown_blockquote_attribution_and_nesting_hygiene(
        md,
        max_nesting_depth=2,
        max_quote_block_lines=15,
    )
    assert res["total_blockquotes"] == 1
    assert res["deeply_nested_quote_lines"] == []
    assert res["oversized_quote_start_lines"] == []
    assert res["empty_blockquote_start_lines"] == []
    assert res["blockquote_hygiene_status"] == "CLEAN"
    assert res["is_blockquote_hygiene_clean"] is True
    assert res["recommendations"] == []


def test_audit_markdown_blockquote_attribution_and_nesting_hygiene_empty_and_bindings():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_blockquote_attribution_and_nesting_hygiene,
    )

    for payload in (None, "", "   ", 123):
        empty = audit_markdown_blockquote_attribution_and_nesting_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_blockquotes"] == 0
        assert empty["deeply_nested_quote_lines"] == []
        assert empty["oversized_quote_start_lines"] == []
        assert empty["empty_blockquote_start_lines"] == []
        assert empty["blockquote_hygiene_status"] == "CLEAN"
        assert empty["is_blockquote_hygiene_clean"] is True
        assert empty["recommendations"] == []

    sample = "> Clean quote — PMBOK §4.4"
    assert (
        AnyDocService.audit_markdown_blockquote_attribution_and_nesting_hygiene(sample)
        == audit_markdown_blockquote_attribution_and_nesting_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_blockquote_attribution_and_nesting_hygiene(sample)
        == audit_markdown_blockquote_attribution_and_nesting_hygiene(sample)
    )
    assert (
        "audit_markdown_blockquote_attribution_and_nesting_hygiene" in mod.__all__
    )


def test_audit_markdown_frontmatter_metadata_and_classification_hygiene_governance_non_compliant():
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_and_classification_hygiene,
    )

    res = audit_markdown_frontmatter_metadata_and_classification_hygiene(
        [
            {
                "doc_id": "DOC-01",
                "has_yaml_frontmatter_delimiters": False,
                "frontmatter_fields": {},
            },
            {
                "doc_id": "DOC-02",
                "has_yaml_frontmatter_delimiters": True,
                "frontmatter_fields": {
                    "title": "Runbook",
                    "owner": "   ",
                    "classification": "TOP_SECRET",
                    "last_reviewed": "2026-10-01",
                },
            },
        ]
    )
    assert res["total_documents_evaluated"] == 2
    assert res["missing_frontmatter_doc_ids"] == ["DOC-01"]
    assert res["incomplete_metadata_doc_ids"] == ["DOC-02"]
    assert res["invalid_classification_doc_ids"] == ["DOC-02"]
    assert res["metadata_compliance_pct"] == 0.0
    assert res["frontmatter_hygiene_status"] == "GOVERNANCE_NON_COMPLIANT"
    assert res["is_frontmatter_compliant"] is False


def test_audit_markdown_frontmatter_metadata_and_classification_hygiene_metadata_gaps():
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_and_classification_hygiene,
    )

    docs = [
        {
            "doc_id": f"DOC-OK-{i}",
            "has_yaml_frontmatter_delimiters": True,
            "frontmatter_fields": {
                "title": f"Doc {i}",
                "owner": "pmo@ccf.org",
                "classification": "INTERNAL",
                "last_reviewed": "2026-10-01",
            },
        }
        for i in range(1, 4)
    ] + [
        {
            "doc_id": "DOC-GAP-4",
            "has_yaml_frontmatter_delimiters": True,
            "frontmatter_fields": {
                "title": "Incomplete Doc",
                "owner": "",
                "classification": "PUBLIC",
                "last_reviewed": "2026-10-01",
            },
        }
    ]
    res = audit_markdown_frontmatter_metadata_and_classification_hygiene(docs)
    assert res["total_documents_evaluated"] == 4
    assert res["missing_frontmatter_doc_ids"] == []
    assert res["incomplete_metadata_doc_ids"] == ["DOC-GAP-4"]
    assert res["invalid_classification_doc_ids"] == []
    assert res["metadata_compliance_pct"] == 75.0
    assert res["frontmatter_hygiene_status"] == "METADATA_GAPS"
    assert res["is_frontmatter_compliant"] is False


def test_audit_markdown_frontmatter_metadata_and_classification_hygiene_compliant():
    from backend.services.anydoc_service import (
        audit_markdown_frontmatter_metadata_and_classification_hygiene,
    )

    res = audit_markdown_frontmatter_metadata_and_classification_hygiene(
        [
            {
                "doc_id": "DOC-100",
                "has_yaml_frontmatter_delimiters": True,
                "frontmatter_fields": {
                    "title": "Architecture Charter",
                    "owner": "arch@ccf.org",
                    "classification": "confidential",
                    "last_reviewed": "2026-10-15",
                },
            }
        ]
    )
    assert res["total_documents_evaluated"] == 1
    assert res["missing_frontmatter_doc_ids"] == []
    assert res["incomplete_metadata_doc_ids"] == []
    assert res["invalid_classification_doc_ids"] == []
    assert res["metadata_compliance_pct"] == 100.0
    assert res["frontmatter_hygiene_status"] == "COMPLIANT"
    assert res["is_frontmatter_compliant"] is True


def test_audit_markdown_frontmatter_metadata_and_classification_hygiene_empty_and_bindings():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_frontmatter_metadata_and_classification_hygiene,
    )

    for payload in (None, [], "invalid", [{"doc_id": "   "}]):
        empty = audit_markdown_frontmatter_metadata_and_classification_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_documents_evaluated"] == 0
        assert empty["missing_frontmatter_doc_ids"] == []
        assert empty["incomplete_metadata_doc_ids"] == []
        assert empty["invalid_classification_doc_ids"] == []
        assert empty["metadata_compliance_pct"] == 100.0
        assert empty["frontmatter_hygiene_status"] == "COMPLIANT"
        assert empty["is_frontmatter_compliant"] is True

    sample = [
        {
            "doc_id": "DOC-99",
            "has_yaml_frontmatter_delimiters": True,
            "frontmatter_fields": {
                "title": "SOP",
                "owner": "ops",
                "classification": "RESTRICTED",
                "last_reviewed": "2026-10-18",
            },
        }
    ]
    assert (
        AnyDocService.audit_markdown_frontmatter_metadata_and_classification_hygiene(
            sample
        )
        == audit_markdown_frontmatter_metadata_and_classification_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_frontmatter_metadata_and_classification_hygiene(
            sample
        )
        == audit_markdown_frontmatter_metadata_and_classification_hygiene(sample)
    )
    assert (
        "audit_markdown_frontmatter_metadata_and_classification_hygiene"
        in mod.__all__
    )


def test_audit_markdown_mermaid_render_failure_risk_paths():
    """Caso 1: tipo no soportado o riesgos de sintaxis -> RENDER_FAILURE_RISK."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity,
    )

    res = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
        [
            {
                "diagram_id": "DIA-01",
                "diagram_type": "gitGraph",
                "node_count": 5,
            },
            {
                "diagram_id": "DIA-02",
                "diagram_type": "flowchart",
                "node_count": 3,
                "has_unquoted_parentheses_in_labels": True,
            },
            {
                "diagram_id": "DIA-03",
                "diagram_type": "sequenceDiagram",
                "node_count": 4,
                "has_html_tags_in_labels": True,
            },
            {
                "diagram_id": "DIA-04",
                "diagram_type": "erDiagram",
                "node_count": 2,
                "has_balanced_subgraph_ends": False,
            },
        ]
    )
    assert res["total_diagrams_evaluated"] == 4
    assert res["unsupported_type_diagram_ids"] == ["DIA-01"]
    assert res["syntax_hazard_diagram_ids"] == ["DIA-02", "DIA-03", "DIA-04"]
    assert res["cognitive_overload_diagram_ids"] == []
    assert res["max_node_count_observed"] == 5
    assert res["mermaid_hygiene_status"] == "RENDER_FAILURE_RISK"
    assert res["is_mermaid_compliant"] is False

    # Tipo válido con espacios alrededor del strip: sigue soportado.
    res_trim = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
        [
            {"diagram_id": "DIA-05", "diagram_type": "  stateDiagram-v2  ", "node_count": 6},
        ]
    )
    assert res_trim["unsupported_type_diagram_ids"] == []
    assert res_trim["mermaid_hygiene_status"] == "DIAGRAM_CLEAN"


def test_audit_markdown_mermaid_cognitive_overload_only():
    """Caso 2: solo sobrecarga cognitiva de nodos -> COGNITIVE_OVERLOAD_WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity,
    )

    res = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
        [
            {
                "diagram_id": "DIA-10",
                "diagram_type": "flowchart",
                "node_count": 26,
            },
            {
                "diagram_id": "DIA-11",
                "diagram_type": "graph",
                "node_count": 25,
            },
        ]
    )
    assert res["total_diagrams_evaluated"] == 2
    assert res["unsupported_type_diagram_ids"] == []
    assert res["syntax_hazard_diagram_ids"] == []
    assert res["cognitive_overload_diagram_ids"] == ["DIA-10"]
    assert res["max_node_count_observed"] == 26
    assert res["mermaid_hygiene_status"] == "COGNITIVE_OVERLOAD_WARNING"
    assert res["is_mermaid_compliant"] is False

    # Precisión: RENDER_FAILURE_RISK domina sobre la sobrecarga cognitiva.
    res_mixed = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
        [
            {
                "diagram_id": "DIA-12",
                "diagram_type": "classDiagram",
                "node_count": 30,
                "has_unquoted_parentheses_in_labels": True,
            },
        ]
    )
    assert res_mixed["mermaid_hygiene_status"] == "RENDER_FAILURE_RISK"


def test_audit_markdown_mermaid_clean_and_boundaries():
    """Caso 3: diagramas válidos con node_count en la frontera -> DIAGRAM_CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity,
    )

    res = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
        [
            {
                "diagram_id": "DIA-20",
                "diagram_type": "sequenceDiagram",
                "node_count": 25,
                "has_unquoted_parentheses_in_labels": False,
                "has_html_tags_in_labels": False,
                "has_balanced_subgraph_ends": True,
            },
            {
                "diagram_id": "DIA-21",
                "diagram_type": "flowchart",
                "node_count": 0,
            },
        ]
    )
    assert res["total_diagrams_evaluated"] == 2
    assert res["unsupported_type_diagram_ids"] == []
    assert res["syntax_hazard_diagram_ids"] == []
    assert res["cognitive_overload_diagram_ids"] == []
    assert res["max_node_count_observed"] == 25
    assert res["mermaid_hygiene_status"] == "DIAGRAM_CLEAN"
    assert res["is_mermaid_compliant"] is True


def test_audit_markdown_mermaid_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding en AnyDocService/AnydocService + __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(payload)  # type: ignore[arg-type]
        assert empty["total_diagrams_evaluated"] == 0
        assert empty["unsupported_type_diagram_ids"] == []
        assert empty["syntax_hazard_diagram_ids"] == []
        assert empty["cognitive_overload_diagram_ids"] == []
        assert empty["max_node_count_observed"] == 0
        assert empty["mermaid_hygiene_status"] == "DIAGRAM_CLEAN"
        assert empty["is_mermaid_compliant"] is True

    sample = [
        {"diagram_id": "DIA-30", "diagram_type": "flowchart", "node_count": 4},
    ]
    assert (
        AnyDocService.audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(sample)
        == audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(sample)
    )
    assert (
        AnydocService.audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(sample)
        == audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(sample)
    )
    assert "audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity" in mod.__all__


def test_audit_markdown_footnote_broken_citation_integrity_paths():
    """Caso 1: marcador sin definición o definiciones vacías/duplicadas -> BROKEN_CITATION_INTEGRITY."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_and_orphan_definition_hygiene,
    )

    res = audit_markdown_footnote_citation_and_orphan_definition_hygiene(
        [
            {
                "doc_id": "DOC-01",
                "inline_footnote_markers": ["1", "2", "3"],
                "defined_footnote_keys": ["1", "2"],
            },
            {
                "doc_id": "DOC-02",
                "inline_footnote_markers": ["5"],
                "defined_footnote_keys": ["5"],
                "empty_definition_keys": ["7"],
            },
            {
                "doc_id": "DOC-03",
                "inline_footnote_markers": ["8"],
                "defined_footnote_keys": ["8"],
                "duplicate_definition_keys": ["9"],
            },
        ]
    )
    assert res["total_documents_evaluated"] == 3
    assert res["dangling_marker_doc_ids"] == ["DOC-01"]
    assert res["orphan_definition_doc_ids"] == []
    assert res["malformed_definition_doc_ids"] == ["DOC-02", "DOC-03"]
    assert res["footnote_hygiene_status"] == "BROKEN_CITATION_INTEGRITY"
    assert res["is_footnote_compliant"] is False


def test_audit_markdown_footnote_orphan_warning_only():
    """Caso 2: solo definiciones huérfanas -> ORPHAN_DEFINITION_WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_and_orphan_definition_hygiene,
    )

    res = audit_markdown_footnote_citation_and_orphan_definition_hygiene(
        [
            {
                "doc_id": "DOC-10",
                "inline_footnote_markers": ["1"],
                "defined_footnote_keys": ["1", "2", "3"],
            },
        ]
    )
    assert res["total_documents_evaluated"] == 1
    assert res["dangling_marker_doc_ids"] == []
    assert res["orphan_definition_doc_ids"] == ["DOC-10"]
    assert res["malformed_definition_doc_ids"] == []
    assert res["footnote_hygiene_status"] == "ORPHAN_DEFINITION_WARNING"
    assert res["is_footnote_compliant"] is False

    # Precisión: BROKEN_CITATION_INTEGRITY domina sobre orphan.
    res_mixed = audit_markdown_footnote_citation_and_orphan_definition_hygiene(
        [
            {
                "doc_id": "DOC-11",
                "inline_footnote_markers": ["1", "x"],
                "defined_footnote_keys": ["1", "2"],
            },
        ]
    )
    assert res_mixed["dangling_marker_doc_ids"] == ["DOC-11"]
    assert res_mixed["orphan_definition_doc_ids"] == ["DOC-11"]
    assert res_mixed["footnote_hygiene_status"] == "BROKEN_CITATION_INTEGRITY"


def test_audit_markdown_footnote_clean_and_normalization():
    """Caso 3: paridad perfecta con espacios alrededor de claves -> FOOTNOTES_CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_and_orphan_definition_hygiene,
    )

    res = audit_markdown_footnote_citation_and_orphan_definition_hygiene(
        [
            {
                "doc_id": "DOC-20",
                "inline_footnote_markers": [" 1 ", "2"],
                "defined_footnote_keys": ["1", " 2 "],
            },
            {
                "doc_id": "DOC-21",
            },
        ]
    )
    assert res["total_documents_evaluated"] == 2
    assert res["dangling_marker_doc_ids"] == []
    assert res["orphan_definition_doc_ids"] == []
    assert res["malformed_definition_doc_ids"] == []
    assert res["footnote_hygiene_status"] == "FOOTNOTES_CLEAN"
    assert res["is_footnote_compliant"] is True


def test_audit_markdown_footnote_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_footnote_citation_and_orphan_definition_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_markdown_footnote_citation_and_orphan_definition_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_documents_evaluated"] == 0
        assert empty["dangling_marker_doc_ids"] == []
        assert empty["orphan_definition_doc_ids"] == []
        assert empty["malformed_definition_doc_ids"] == []
        assert empty["footnote_hygiene_status"] == "FOOTNOTES_CLEAN"
        assert empty["is_footnote_compliant"] is True

    sample = [
        {
            "doc_id": "DOC-30",
            "inline_footnote_markers": ["1"],
            "defined_footnote_keys": ["1"],
        },
    ]
    assert (
        AnyDocService.audit_markdown_footnote_citation_and_orphan_definition_hygiene(sample)
        == audit_markdown_footnote_citation_and_orphan_definition_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_footnote_citation_and_orphan_definition_hygiene(sample)
        == audit_markdown_footnote_citation_and_orphan_definition_hygiene(sample)
    )
    assert "audit_markdown_footnote_citation_and_orphan_definition_hygiene" in mod.__all__


def test_audit_markdown_task_list_checklist_owner_and_due_date_hygiene_governance_breach():
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_owner_and_due_date_hygiene,
    )

    res = audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
        [
            {
                "item_id": "ACT-001",
                "is_checked": False,
                "has_assigned_owner_handle": True,
                "has_iso_due_date": True,
                "overdue_days": 5,
                "has_malformed_checkbox_syntax": False,
            },
            {
                "item_id": "ACT-002",
                "is_checked": True,
                "has_assigned_owner_handle": False,
                "has_iso_due_date": False,
                "overdue_days": 10,
                "has_malformed_checkbox_syntax": True,
            },
        ],
        max_overdue_days_allowed=0,
    )
    assert res["total_items_evaluated"] == 2
    assert res["open_items_count"] == 1
    assert res["checked_items_count"] == 1
    assert res["unassigned_open_item_ids"] == []
    assert res["overdue_open_item_ids"] == ["ACT-001"]
    assert res["malformed_syntax_item_ids"] == ["ACT-002"]
    assert res["checklist_hygiene_status"] == "ACTION_GOVERNANCE_BREACH"
    assert res["is_checklist_compliant"] is False


def test_audit_markdown_task_list_checklist_owner_and_due_date_hygiene_unassigned_warning():
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_owner_and_due_date_hygiene,
    )

    res = audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
        [
            {
                "item_id": "ACT-010",
                "is_checked": False,
                "has_assigned_owner_handle": True,
                "has_iso_due_date": False,
                "overdue_days": 0,
                "has_malformed_checkbox_syntax": False,
            }
        ],
        max_overdue_days_allowed=0,
    )
    assert res["unassigned_open_item_ids"] == ["ACT-010"]
    assert res["overdue_open_item_ids"] == []
    assert res["malformed_syntax_item_ids"] == []
    assert res["checklist_hygiene_status"] == "UNASSIGNED_ACTION_WARNING"
    assert res["is_checklist_compliant"] is False


def test_audit_markdown_task_list_checklist_owner_and_due_date_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_task_list_checklist_owner_and_due_date_hygiene,
    )

    empty = audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
        [{"item_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_items_evaluated"] == 0
    assert empty["checklist_hygiene_status"] == "CHECKLIST_CLEAN"
    assert empty["is_checklist_compliant"] is True

    clean = audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
        [
            {
                "item_id": "ACT-020",
                "is_checked": False,
                "has_assigned_owner_handle": True,
                "has_iso_due_date": True,
                "overdue_days": 0,
                "has_malformed_checkbox_syntax": False,
            },
            {
                "item_id": "ACT-021",
                "is_checked": True,
                "has_assigned_owner_handle": False,
                "has_iso_due_date": False,
                "overdue_days": 0,
                "has_malformed_checkbox_syntax": False,
            },
        ]
    )
    assert clean["total_items_evaluated"] == 2
    assert clean["open_items_count"] == 1
    assert clean["checked_items_count"] == 1
    assert clean["checklist_hygiene_status"] == "CHECKLIST_CLEAN"
    assert clean["is_checklist_compliant"] is True


def test_audit_markdown_task_list_checklist_owner_and_due_date_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_task_list_checklist_owner_and_due_date_hygiene,
    )

    sample = [
        {
            "item_id": "ACT-99",
            "is_checked": True,
            "has_malformed_checkbox_syntax": False,
        }
    ]
    assert (
        AnyDocService.audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
            sample
        )
        == audit_markdown_task_list_checklist_owner_and_due_date_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
            sample
        )
        == audit_markdown_task_list_checklist_owner_and_due_date_hygiene(sample)
    )
    assert (
        "audit_markdown_task_list_checklist_owner_and_due_date_hygiene"
        in mod.__all__
    )


def test_audit_markdown_image_alt_text_and_asset_weight_hygiene_broken_or_inaccessible():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_weight_hygiene,
    )

    res = audit_markdown_image_alt_text_and_asset_weight_hygiene(
        [
            {
                "image_id": "IMG-BROKEN",
                "alt_text": "Architecture diagram of multi-tenant router",
                "asset_size_kb": 120.0,
                "target_path_exists": False,
                "uses_unoptimized_bmp_or_tiff": False,
            },
            {
                "image_id": "IMG-TRIVIAL-ALT",
                "alt_text": "Screenshot",
                "asset_size_kb": 80.0,
                "target_path_exists": True,
                "uses_unoptimized_bmp_or_tiff": False,
            },
        ],
        max_asset_size_kb=500.0,
        min_alt_text_chars=5,
    )
    assert res["total_images_evaluated"] == 2
    assert res["broken_path_image_ids"] == ["IMG-BROKEN"]
    assert res["missing_or_trivial_alt_image_ids"] == ["IMG-TRIVIAL-ALT"]
    assert res["oversized_or_unoptimized_image_ids"] == []
    assert res["image_hygiene_status"] == "BROKEN_OR_INACCESSIBLE_MEDIA"
    assert res["is_media_hygiene_compliant"] is False


def test_audit_markdown_image_alt_text_and_asset_weight_hygiene_asset_bloat_warning():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_weight_hygiene,
    )

    res = audit_markdown_image_alt_text_and_asset_weight_hygiene(
        [
            {
                "image_id": "IMG-HEAVY-BMP",
                "alt_text": "EVM S-Curve Baseline vs Actual Cost",
                "asset_size_kb": 1200.0,
                "target_path_exists": True,
                "uses_unoptimized_bmp_or_tiff": True,
            }
        ],
        max_asset_size_kb=500.0,
        min_alt_text_chars=5,
    )
    assert res["broken_path_image_ids"] == []
    assert res["missing_or_trivial_alt_image_ids"] == []
    assert res["oversized_or_unoptimized_image_ids"] == ["IMG-HEAVY-BMP"]
    assert res["image_hygiene_status"] == "ASSET_BLOAT_WARNING"
    assert res["is_media_hygiene_compliant"] is False


def test_audit_markdown_image_alt_text_and_asset_weight_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_asset_weight_hygiene,
    )

    empty = audit_markdown_image_alt_text_and_asset_weight_hygiene(
        [{"image_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_images_evaluated"] == 0
    assert empty["image_hygiene_status"] == "MEDIA_ASSETS_CLEAN"
    assert empty["is_media_hygiene_compliant"] is True

    clean = audit_markdown_image_alt_text_and_asset_weight_hygiene(
        [
            {
                "image_id": "IMG-CLEAN-SVG",
                "alt_text": "WBS 100% Rule Decomposition Tree",
                "asset_size_kb": 45.0,
                "target_path_exists": True,
                "uses_unoptimized_bmp_or_tiff": False,
            }
        ]
    )
    assert clean["total_images_evaluated"] == 1
    assert clean["image_hygiene_status"] == "MEDIA_ASSETS_CLEAN"
    assert clean["is_media_hygiene_compliant"] is True


def test_audit_markdown_image_alt_text_and_asset_weight_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_image_alt_text_and_asset_weight_hygiene,
    )

    sample = [
        {
            "image_id": "IMG-99",
            "alt_text": "Valid accessibility caption",
            "asset_size_kb": 95.0,
        }
    ]
    assert (
        AnyDocService.audit_markdown_image_alt_text_and_asset_weight_hygiene(
            sample
        )
        == audit_markdown_image_alt_text_and_asset_weight_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_image_alt_text_and_asset_weight_hygiene(
            sample
        )
        == audit_markdown_image_alt_text_and_asset_weight_hygiene(sample)
    )
    assert (
        "audit_markdown_image_alt_text_and_asset_weight_hygiene"
        in mod.__all__
    )


def test_audit_markdown_acronym_glossary_breach_paths():
    """Caso 1: conflictos de definiciones o términos prohibidos -> TERMINOLOGY_CONFLICT_OR_BANNED_BREACH."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_expansion_and_glossary_term_hygiene,
    )

    res = audit_markdown_acronym_expansion_and_glossary_term_hygiene(
        [
            {
                "doc_id": "DOC-01",
                "unexpanded_first_use_acronyms_count": 0,
                "deprecated_or_banned_terms_count": 0,
                "conflicting_acronym_definitions_count": 2,
                "has_canonical_glossary_link": True,
            },
            {
                "doc_id": "DOC-02",
                "unexpanded_first_use_acronyms_count": 3,
                "deprecated_or_banned_terms_count": 1,
                "conflicting_acronym_definitions_count": 0,
                "has_canonical_glossary_link": False,
            },
        ]
    )
    assert res["total_documents_evaluated"] == 2
    assert res["conflicting_or_banned_term_doc_ids"] == ["DOC-01", "DOC-02"]
    assert res["unexpanded_acronym_doc_ids"] == ["DOC-02"]
    assert res["missing_glossary_link_doc_ids"] == ["DOC-02"]
    # BREACH domina sobre ACRONYM_OR_GLOSSARY_WARNING.
    assert res["terminology_hygiene_status"] == "TERMINOLOGY_CONFLICT_OR_BANNED_BREACH"
    assert res["is_terminology_compliant"] is False


def test_audit_markdown_acronym_glossary_warning_only():
    """Caso 2: solo acrónimos sin expandir o sin enlace al glosario -> ACRONYM_OR_GLOSSARY_WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_expansion_and_glossary_term_hygiene,
    )

    res = audit_markdown_acronym_expansion_and_glossary_term_hygiene(
        [
            {
                "doc_id": "DOC-10",
                "unexpanded_first_use_acronyms_count": 2,
                "deprecated_or_banned_terms_count": 0,
                "conflicting_acronym_definitions_count": 0,
                "has_canonical_glossary_link": True,
            },
            {
                "doc_id": "DOC-11",
                "unexpanded_first_use_acronyms_count": 0,
                "deprecated_or_banned_terms_count": 0,
                "conflicting_acronym_definitions_count": 0,
                "has_canonical_glossary_link": False,
            },
        ]
    )
    assert res["total_documents_evaluated"] == 2
    assert res["conflicting_or_banned_term_doc_ids"] == []
    assert res["unexpanded_acronym_doc_ids"] == ["DOC-10"]
    assert res["missing_glossary_link_doc_ids"] == ["DOC-11"]
    assert res["terminology_hygiene_status"] == "ACRONYM_OR_GLOSSARY_WARNING"
    assert res["is_terminology_compliant"] is False


def test_audit_markdown_acronym_glossary_clean_and_threshold():
    """Caso 3: umbral tolerante de acrónimos no expandidos y caso limpio -> TERMINOLOGY_CANONICAL_CLEAN."""
    from backend.services.anydoc_service import (
        audit_markdown_acronym_expansion_and_glossary_term_hygiene,
    )

    res = audit_markdown_acronym_expansion_and_glossary_term_hygiene(
        [
            {
                "doc_id": "DOC-20",
                "unexpanded_first_use_acronyms_count": 1,
                "deprecated_or_banned_terms_count": 0,
                "conflicting_acronym_definitions_count": 0,
                "has_canonical_glossary_link": True,
            },
        ],
        max_unexpanded_acronyms_allowed=2,
    )
    # 1 acrónimo <= tolerancia 2; todo lo demás limpio.
    assert res["total_documents_evaluated"] == 1
    assert res["conflicting_or_banned_term_doc_ids"] == []
    assert res["unexpanded_acronym_doc_ids"] == []
    assert res["missing_glossary_link_doc_ids"] == []
    assert res["terminology_hygiene_status"] == "TERMINOLOGY_CANONICAL_CLEAN"
    assert res["is_terminology_compliant"] is True

    # Con la tolerancia por defecto (0), el mismo doc dispara WARNING.
    res_strict = audit_markdown_acronym_expansion_and_glossary_term_hygiene(
        [
            {
                "doc_id": "DOC-21",
                "unexpanded_first_use_acronyms_count": 1,
                "has_canonical_glossary_link": True,
            },
        ],
    )
    assert res_strict["unexpanded_acronym_doc_ids"] == ["DOC-21"]
    assert res_strict["terminology_hygiene_status"] == "ACRONYM_OR_GLOSSARY_WARNING"

    # Doc vacío (sin campos) usa defaults -> CLEAN.
    res_defaults = audit_markdown_acronym_expansion_and_glossary_term_hygiene(
        [{"doc_id": "DOC-22"}]
    )
    assert res_defaults["terminology_hygiene_status"] == "TERMINOLOGY_CANONICAL_CLEAN"
    assert res_defaults["is_terminology_compliant"] is True


def test_audit_markdown_acronym_glossary_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding de ambas clases + __all__."""
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_acronym_expansion_and_glossary_term_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_markdown_acronym_expansion_and_glossary_term_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_documents_evaluated"] == 0
        assert empty["conflicting_or_banned_term_doc_ids"] == []
        assert empty["unexpanded_acronym_doc_ids"] == []
        assert empty["missing_glossary_link_doc_ids"] == []
        assert empty["terminology_hygiene_status"] == "TERMINOLOGY_CANONICAL_CLEAN"
        assert empty["is_terminology_compliant"] is True

    sample = [
        {
            "doc_id": "DOC-30",
            "unexpanded_first_use_acronyms_count": 0,
            "has_canonical_glossary_link": True,
        },
    ]
    assert (
        AnyDocService.audit_markdown_acronym_expansion_and_glossary_term_hygiene(sample)
        == audit_markdown_acronym_expansion_and_glossary_term_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_acronym_expansion_and_glossary_term_hygiene(sample)
        == audit_markdown_acronym_expansion_and_glossary_term_hygiene(sample)
    )
    assert "audit_markdown_acronym_expansion_and_glossary_term_hygiene" in mod.__all__


def test_audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene,
    )

    result = audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
        [
            {
                "doc_id": "DOC-H1-MISS",
                "has_single_h1_root": False,
                "skipped_heading_levels_count": 0,
                "duplicate_anchor_slugs_count": 0,
                "max_heading_depth_observed": 3,
                "toc_synchronized_with_headings": True,
            },
            {
                "doc_id": "DOC-ANCHOR-DUP",
                "has_single_h1_root": True,
                "skipped_heading_levels_count": 0,
                "duplicate_anchor_slugs_count": 2,
                "max_heading_depth_observed": 3,
                "toc_synchronized_with_headings": True,
            },
        ],
        max_heading_depth_allowed=4,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["broken_anchor_or_h1_doc_ids"] == ["DOC-H1-MISS", "DOC-ANCHOR-DUP"]
    assert result["hierarchy_skip_or_toc_drift_doc_ids"] == []
    assert result["heading_hygiene_status"] == "HEADING_ANCHOR_OR_H1_BREACH"
    assert result["is_heading_hygiene_compliant"] is False


def test_audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene,
    )

    result = audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
        [
            {
                "doc_id": "DOC-SKIP",
                "has_single_h1_root": True,
                "skipped_heading_levels_count": 1,
                "duplicate_anchor_slugs_count": 0,
                "max_heading_depth_observed": 4,
                "toc_synchronized_with_headings": True,
            },
            {
                "doc_id": "DOC-TOC-DRIFT",
                "has_single_h1_root": True,
                "skipped_heading_levels_count": 0,
                "duplicate_anchor_slugs_count": 0,
                "max_heading_depth_observed": 3,
                "toc_synchronized_with_headings": False,
            },
            {
                "doc_id": "DOC-DEEP",
                "has_single_h1_root": True,
                "skipped_heading_levels_count": 0,
                "duplicate_anchor_slugs_count": 0,
                "max_heading_depth_observed": 5,
                "toc_synchronized_with_headings": True,
            },
        ],
        max_heading_depth_allowed=4,
    )
    assert result["evaluated_documents_count"] == 3
    assert result["broken_anchor_or_h1_doc_ids"] == []
    assert result["hierarchy_skip_or_toc_drift_doc_ids"] == [
        "DOC-SKIP",
        "DOC-TOC-DRIFT",
        "DOC-DEEP",
    ]
    assert result["heading_hygiene_status"] == "HEADING_HIERARCHY_OR_TOC_WARNING"
    assert result["is_heading_hygiene_compliant"] is False


def test_audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene,
    )

    empty = audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
        [{"doc_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_documents_count"] == 0
    assert empty["heading_hygiene_status"] == "HEADING_STRUCTURE_CLEAN"
    assert empty["is_heading_hygiene_compliant"] is True

    clean = audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
        [
            {
                "doc_id": "DOC-CLEAN-1",
                "has_single_h1_root": True,
                "skipped_heading_levels_count": 0,
                "duplicate_anchor_slugs_count": 0,
                "max_heading_depth_observed": 4,
                "toc_synchronized_with_headings": True,
            }
        ],
        max_heading_depth_allowed=4,
    )
    assert clean["evaluated_documents_count"] == 1
    assert clean["heading_hygiene_status"] == "HEADING_STRUCTURE_CLEAN"
    assert clean["is_heading_hygiene_compliant"] is True


def test_audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene,
    )

    sample = [
        {
            "doc_id": "DOC-99",
            "has_single_h1_root": True,
            "skipped_heading_levels_count": 0,
            "duplicate_anchor_slugs_count": 0,
            "max_heading_depth_observed": 3,
            "toc_synchronized_with_headings": True,
        }
    ]
    assert (
        AnyDocService.audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
            sample
        )
        == audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
            sample
        )
        == audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(sample)
    )
    assert (
        "audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene"
        in mod.__all__
    )


def test_audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene,
    )

    result = audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
        [
            {
                "doc_id": "DOC-XSS-SCRIPT",
                "unsafe_script_or_event_handler_tags_count": 1,
                "unwhitelisted_iframe_or_embed_count": 0,
                "whitelisted_iframe_count": 0,
                "raw_style_or_deprecated_html_tags_count": 0,
                "csp_nonce_or_sandbox_enforced": True,
            },
            {
                "doc_id": "DOC-UNTRUSTED-IFRAME",
                "unsafe_script_or_event_handler_tags_count": 0,
                "unwhitelisted_iframe_or_embed_count": 1,
                "whitelisted_iframe_count": 0,
                "raw_style_or_deprecated_html_tags_count": 0,
                "csp_nonce_or_sandbox_enforced": True,
            },
            {
                "doc_id": "DOC-NO-SANDBOX",
                "unsafe_script_or_event_handler_tags_count": 0,
                "unwhitelisted_iframe_or_embed_count": 0,
                "whitelisted_iframe_count": 2,
                "raw_style_or_deprecated_html_tags_count": 0,
                "csp_nonce_or_sandbox_enforced": False,
            },
        ],
        allow_whitelisted_iframes=True,
    )
    assert result["evaluated_documents_count"] == 3
    assert result["xss_or_untrusted_embed_doc_ids"] == [
        "DOC-XSS-SCRIPT",
        "DOC-UNTRUSTED-IFRAME",
        "DOC-NO-SANDBOX",
    ]
    assert result["raw_html_style_warning_doc_ids"] == []
    assert (
        result["html_sanitization_status"]
        == "HTML_XSS_OR_UNTRUSTED_EMBED_BREACH"
    )
    assert result["is_html_sanitization_compliant"] is False


def test_audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene_warning_and_disallowed_iframe():
    from backend.services.anydoc_service import (
        audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene,
    )

    warn_res = audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
        [
            {
                "doc_id": "DOC-STYLE-WARN",
                "unsafe_script_or_event_handler_tags_count": 0,
                "unwhitelisted_iframe_or_embed_count": 0,
                "whitelisted_iframe_count": 1,
                "raw_style_or_deprecated_html_tags_count": 3,
                "csp_nonce_or_sandbox_enforced": True,
            }
        ],
        allow_whitelisted_iframes=True,
    )
    assert warn_res["evaluated_documents_count"] == 1
    assert warn_res["xss_or_untrusted_embed_doc_ids"] == []
    assert warn_res["raw_html_style_warning_doc_ids"] == ["DOC-STYLE-WARN"]
    assert (
        warn_res["html_sanitization_status"]
        == "HTML_RAW_STYLE_OR_DEPRECATED_TAG_WARNING"
    )
    assert warn_res["is_html_sanitization_compliant"] is False

    strict_iframe = audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
        [
            {
                "doc_id": "DOC-WHITELIST-BLOCKED",
                "whitelisted_iframe_count": 1,
                "csp_nonce_or_sandbox_enforced": True,
            }
        ],
        allow_whitelisted_iframes=False,
    )
    assert strict_iframe["xss_or_untrusted_embed_doc_ids"] == [
        "DOC-WHITELIST-BLOCKED"
    ]
    assert (
        strict_iframe["html_sanitization_status"]
        == "HTML_XSS_OR_UNTRUSTED_EMBED_BREACH"
    )


def test_audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene,
    )

    empty = audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
        [{"doc_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_documents_count"] == 0
    assert empty["html_sanitization_status"] == "HTML_SANITIZATION_CLEAN"
    assert empty["is_html_sanitization_compliant"] is True

    clean = audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
        [
            {
                "doc_id": "DOC-SAFE-1",
                "unsafe_script_or_event_handler_tags_count": 0,
                "unwhitelisted_iframe_or_embed_count": 0,
                "whitelisted_iframe_count": 1,
                "raw_style_or_deprecated_html_tags_count": 0,
                "csp_nonce_or_sandbox_enforced": True,
            }
        ],
        allow_whitelisted_iframes=True,
    )
    assert clean["evaluated_documents_count"] == 1
    assert clean["html_sanitization_status"] == "HTML_SANITIZATION_CLEAN"
    assert clean["is_html_sanitization_compliant"] is True


def test_audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene,
    )

    sample = [
        {
            "doc_id": "DOC-99",
            "unsafe_script_or_event_handler_tags_count": 0,
            "unwhitelisted_iframe_or_embed_count": 0,
        }
    ]
    assert (
        AnyDocService.audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
            sample
        )
        == audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
            sample
        )
        == audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(sample)
    )
    assert (
        "audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene"
        in mod.__all__
    )


def test_audit_markdown_link_rot_and_internal_anchor_resolution_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_link_rot_and_internal_anchor_resolution_hygiene,
    )

    result = audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
        [
            {
                "doc_id": "DOC-DEAD-404",
                "dead_404_or_5xx_links_count": 2,
                "unresolved_internal_anchors_count": 0,
                "max_redirect_chain_hops": 0,
                "unpinned_mutable_external_urls_count": 0,
            },
            {
                "doc_id": "DOC-BROKEN-ANCHOR",
                "dead_404_or_5xx_links_count": 0,
                "unresolved_internal_anchors_count": 1,
                "max_redirect_chain_hops": 0,
                "unpinned_mutable_external_urls_count": 0,
            },
        ],
        max_redirect_hops_allowed=2,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["dead_link_or_broken_anchor_doc_ids"] == [
        "DOC-DEAD-404",
        "DOC-BROKEN-ANCHOR",
    ]
    assert result["redirect_chain_or_unpinned_url_doc_ids"] == []
    assert (
        result["link_integrity_status"] == "LINK_ROT_OR_BROKEN_ANCHOR_BREACH"
    )
    assert result["is_link_integrity_compliant"] is False


def test_audit_markdown_link_rot_and_internal_anchor_resolution_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_link_rot_and_internal_anchor_resolution_hygiene,
    )

    result = audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
        [
            {
                "doc_id": "DOC-MANY-REDIRECTS",
                "dead_404_or_5xx_links_count": 0,
                "unresolved_internal_anchors_count": 0,
                "max_redirect_chain_hops": 4,
                "unpinned_mutable_external_urls_count": 0,
            },
            {
                "doc_id": "DOC-UNPINNED-URL",
                "dead_404_or_5xx_links_count": 0,
                "unresolved_internal_anchors_count": 0,
                "max_redirect_chain_hops": 1,
                "unpinned_mutable_external_urls_count": 3,
            },
        ],
        max_redirect_hops_allowed=2,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["dead_link_or_broken_anchor_doc_ids"] == []
    assert result["redirect_chain_or_unpinned_url_doc_ids"] == [
        "DOC-MANY-REDIRECTS",
        "DOC-UNPINNED-URL",
    ]
    assert (
        result["link_integrity_status"]
        == "LINK_REDIRECT_OR_UNPINNED_WARNING"
    )
    assert result["is_link_integrity_compliant"] is False


def test_audit_markdown_link_rot_and_internal_anchor_resolution_hygiene_verified_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_link_rot_and_internal_anchor_resolution_hygiene,
    )

    empty = audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
        [{"doc_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_documents_count"] == 0
    assert empty["link_integrity_status"] == "LINK_INTEGRITY_VERIFIED"
    assert empty["is_link_integrity_compliant"] is True

    verified = audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
        [
            {
                "doc_id": "DOC-CLEAN-LINKS",
                "dead_404_or_5xx_links_count": 0,
                "unresolved_internal_anchors_count": 0,
                "max_redirect_chain_hops": 1,
                "unpinned_mutable_external_urls_count": 0,
            }
        ],
        max_redirect_hops_allowed=2,
    )
    assert verified["evaluated_documents_count"] == 1
    assert verified["link_integrity_status"] == "LINK_INTEGRITY_VERIFIED"
    assert verified["is_link_integrity_compliant"] is True


def test_audit_markdown_link_rot_and_internal_anchor_resolution_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_link_rot_and_internal_anchor_resolution_hygiene,
    )

    sample = [
        {
            "doc_id": "DOC-99",
            "dead_404_or_5xx_links_count": 0,
            "unresolved_internal_anchors_count": 0,
        }
    ]
    assert (
        AnyDocService.audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
            sample
        )
        == audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
            sample
        )
    )
    assert (
        AnydocService.audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
            sample
        )
        == audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
            sample
        )
    )
    assert (
        "audit_markdown_link_rot_and_internal_anchor_resolution_hygiene"
        in mod.__all__
    )



def test_math_delimiter_unsafe_macro_breach():
    from backend.services.anydoc_service import (
        audit_markdown_math_latex_delimiter_and_macro_hygiene,
    )

    res = audit_markdown_math_latex_delimiter_and_macro_hygiene(
        [
            {
                "doc_id": "DOC-UNCLOSED-DOLLAR",
                "unclosed_dollar_or_environment_blocks_count": 1,
            },
            {
                "doc_id": "DOC-UNSAFE-MACRO",
                "unsafe_or_unsupported_katex_macros_count": 3,
            },
        ],
        max_equation_nesting_depth=5,
    )
    assert res["evaluated_documents_count"] == 2
    assert res["broken_delimiter_or_unsafe_macro_doc_ids"] == [
        "DOC-UNCLOSED-DOLLAR",
        "DOC-UNSAFE-MACRO",
    ]
    assert res["unresolved_eqref_or_deep_nesting_doc_ids"] == []
    assert (
        res["math_hygiene_status"]
        == "MATH_DELIMITER_OR_UNSAFE_MACRO_BREACH"
    )
    assert res["is_math_hygiene_compliant"] is False


def test_math_eqref_or_deep_nesting_warning():
    from backend.services.anydoc_service import (
        audit_markdown_math_latex_delimiter_and_macro_hygiene,
    )

    res = audit_markdown_math_latex_delimiter_and_macro_hygiene(
        [
            {
                "doc_id": "DOC-EQREF",
                "unresolved_eqref_labels_count": 2,
            },
            {
                "doc_id": "DOC-DEEP-NESTING",
                "max_observed_equation_nesting_depth": 7,
            },
        ],
        max_equation_nesting_depth=5,
    )
    assert res["evaluated_documents_count"] == 2
    assert res["broken_delimiter_or_unsafe_macro_doc_ids"] == []
    assert res["unresolved_eqref_or_deep_nesting_doc_ids"] == [
        "DOC-EQREF",
        "DOC-DEEP-NESTING",
    ]
    assert res["math_hygiene_status"] == "MATH_EQREF_OR_NESTING_WARNING"
    assert res["is_math_hygiene_compliant"] is False


def test_math_nesting_boundary_optimal_and_defaults():
    from backend.services.anydoc_service import (
        audit_markdown_math_latex_delimiter_and_macro_hygiene,
    )

    res = audit_markdown_math_latex_delimiter_and_macro_hygiene(
        [
            {
                "doc_id": "DOC-BOUNDARY",
                "max_observed_equation_nesting_depth": 5,
            },
            {"doc_id": "DOC-ALL-DEFAULTS"},
        ],
        max_equation_nesting_depth=5,
    )
    assert res["evaluated_documents_count"] == 2
    assert res["broken_delimiter_or_unsafe_macro_doc_ids"] == []
    assert res["unresolved_eqref_or_deep_nesting_doc_ids"] == []
    assert res["math_hygiene_status"] == "MATH_RENDERING_CLEAN"
    assert res["is_math_hygiene_compliant"] is True


def test_math_hygiene_invalid_and_binding():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_math_latex_delimiter_and_macro_hygiene,
    )

    empty = audit_markdown_math_latex_delimiter_and_macro_hygiene(None)
    assert empty["evaluated_documents_count"] == 0
    assert empty["broken_delimiter_or_unsafe_macro_doc_ids"] == []
    assert empty["unresolved_eqref_or_deep_nesting_doc_ids"] == []
    assert empty["math_hygiene_status"] == "MATH_RENDERING_CLEAN"
    assert empty["is_math_hygiene_compliant"] is True

    invalid = audit_markdown_math_latex_delimiter_and_macro_hygiene(
        [42, "not-a-dict", None, {"doc_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_documents_count"] == 0

    defaults = audit_markdown_math_latex_delimiter_and_macro_hygiene(
        [
            {
                "doc_id": "DOC-DEFAULTS",
                "unclosed_dollar_or_environment_blocks_count": None,
                "unsafe_or_unsupported_katex_macros_count": None,
                "unresolved_eqref_labels_count": None,
                "max_observed_equation_nesting_depth": None,
            }
        ]
    )
    assert defaults["evaluated_documents_count"] == 1
    assert defaults["math_hygiene_status"] == "MATH_RENDERING_CLEAN"
    assert defaults["is_math_hygiene_compliant"] is True

    sample = [
        {
            "doc_id": "DOC-1",
            "unresolved_eqref_labels_count": 0,
            "max_observed_equation_nesting_depth": 3,
        }
    ]
    assert (
        AnyDocService.audit_markdown_math_latex_delimiter_and_macro_hygiene(
            sample
        )
        == audit_markdown_math_latex_delimiter_and_macro_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_math_latex_delimiter_and_macro_hygiene(
            sample
        )
        == audit_markdown_math_latex_delimiter_and_macro_hygiene(sample)
    )
    assert (
        "audit_markdown_math_latex_delimiter_and_macro_hygiene"
        in mod.__all__
    )


def test_audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene,
    )

    result = audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
        [
            {
                "doc_id": "DOC-NESTED-ALERT",
                "nested_admonitions_count": 2,
                "unknown_admonition_types_count": 0,
                "consecutive_adjacent_admonitions_count": 0,
                "total_admonitions_count": 3,
            },
            {
                "doc_id": "DOC-UNKNOWN-ALERT",
                "nested_admonitions_count": 0,
                "unknown_admonition_types_count": 1,
                "consecutive_adjacent_admonitions_count": 0,
                "total_admonitions_count": 2,
            },
        ],
        max_admonition_density_per_doc=6,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["nested_or_unknown_admonition_doc_ids"] == [
        "DOC-NESTED-ALERT",
        "DOC-UNKNOWN-ALERT",
    ]
    assert result["adjacent_or_overused_admonition_doc_ids"] == []
    assert (
        result["admonition_hygiene_status"]
        == "ADMONITION_NESTING_OR_TAXONOMY_BREACH"
    )
    assert result["is_admonition_hygiene_compliant"] is False


def test_audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene,
    )

    result = audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
        [
            {
                "doc_id": "DOC-ADJACENT-ALERTS",
                "nested_admonitions_count": 0,
                "unknown_admonition_types_count": 0,
                "consecutive_adjacent_admonitions_count": 2,
                "total_admonitions_count": 4,
            },
            {
                "doc_id": "DOC-ALERT-FATIGUE",
                "nested_admonitions_count": 0,
                "unknown_admonition_types_count": 0,
                "consecutive_adjacent_admonitions_count": 0,
                "total_admonitions_count": 9,
            },
        ],
        max_admonition_density_per_doc=6,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["nested_or_unknown_admonition_doc_ids"] == []
    assert result["adjacent_or_overused_admonition_doc_ids"] == [
        "DOC-ADJACENT-ALERTS",
        "DOC-ALERT-FATIGUE",
    ]
    assert (
        result["admonition_hygiene_status"]
        == "ADMONITION_ADJACENCY_OR_FATIGUE_WARNING"
    )
    assert result["is_admonition_hygiene_compliant"] is False


def test_audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene,
    )

    empty = audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
        [{"doc_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_documents_count"] == 0
    assert (
        empty["admonition_hygiene_status"]
        == "ADMONITION_CALLOUT_HYGIENE_CLEAN"
    )
    assert empty["is_admonition_hygiene_compliant"] is True

    clean = audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
        [
            {
                "doc_id": "DOC-CLEAN-CALLOUTS",
                "nested_admonitions_count": 0,
                "unknown_admonition_types_count": 0,
                "consecutive_adjacent_admonitions_count": 0,
                "total_admonitions_count": 3,
            }
        ],
        max_admonition_density_per_doc=6,
    )
    assert clean["evaluated_documents_count"] == 1
    assert clean["nested_or_unknown_admonition_doc_ids"] == []
    assert clean["adjacent_or_overused_admonition_doc_ids"] == []
    assert (
        clean["admonition_hygiene_status"]
        == "ADMONITION_CALLOUT_HYGIENE_CLEAN"
    )
    assert clean["is_admonition_hygiene_compliant"] is True


def test_audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene,
    )

    sample = [
        {
            "doc_id": "DOC-99",
            "total_admonitions_count": 2,
        }
    ]
    assert (
        AnyDocService.audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
            sample
        )
        == audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
            sample
        )
        == audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(sample)
    )
    assert (
        "audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene"
        in mod.__all__
    )


def test_audit_markdown_fenced_code_block_language_and_secret_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_fenced_code_block_language_and_secret_hygiene,
    )

    result = audit_markdown_fenced_code_block_language_and_secret_hygiene(
        [
            {
                "doc_id": "DOC-UNCLOSED-FENCE",
                "untagged_fenced_code_blocks_count": 0,
                "unclosed_code_fences_count": 1,
                "hardcoded_secret_or_token_patterns_count": 0,
                "max_observed_code_line_length": 78,
            },
            {
                "doc_id": "DOC-SECRET-LEAK",
                "untagged_fenced_code_blocks_count": 0,
                "unclosed_code_fences_count": 0,
                "hardcoded_secret_or_token_patterns_count": 2,
                "max_observed_code_line_length": 78,
            },
        ],
        max_code_line_length=120,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["unclosed_fence_or_secret_leak_doc_ids"] == [
        "DOC-UNCLOSED-FENCE",
        "DOC-SECRET-LEAK",
    ]
    assert result["untagged_language_or_long_line_doc_ids"] == []
    assert (
        result["code_block_hygiene_status"]
        == "CODE_BLOCK_SECRET_OR_UNCLOSED_FENCE_BREACH"
    )
    assert result["is_code_block_hygiene_compliant"] is False


def test_audit_markdown_fenced_code_block_language_and_secret_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_fenced_code_block_language_and_secret_hygiene,
    )

    result = audit_markdown_fenced_code_block_language_and_secret_hygiene(
        [
            {
                "doc_id": "DOC-UNTAGGED-CODE",
                "untagged_fenced_code_blocks_count": 3,
                "unclosed_code_fences_count": 0,
                "hardcoded_secret_or_token_patterns_count": 0,
                "max_observed_code_line_length": 80,
            },
            {
                "doc_id": "DOC-LONG-LINES",
                "untagged_fenced_code_blocks_count": 0,
                "unclosed_code_fences_count": 0,
                "hardcoded_secret_or_token_patterns_count": 0,
                "max_observed_code_line_length": 165,
            },
        ],
        max_code_line_length=120,
    )
    assert result["evaluated_documents_count"] == 2
    assert result["unclosed_fence_or_secret_leak_doc_ids"] == []
    assert result["untagged_language_or_long_line_doc_ids"] == [
        "DOC-UNTAGGED-CODE",
        "DOC-LONG-LINES",
    ]
    assert (
        result["code_block_hygiene_status"]
        == "CODE_BLOCK_UNTAGGED_OR_LINE_LENGTH_WARNING"
    )
    assert result["is_code_block_hygiene_compliant"] is False


def test_audit_markdown_fenced_code_block_language_and_secret_hygiene_clean_and_empty():
    from backend.services.anydoc_service import (
        audit_markdown_fenced_code_block_language_and_secret_hygiene,
    )

    empty = audit_markdown_fenced_code_block_language_and_secret_hygiene(
        [{"doc_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_documents_count"] == 0
    assert empty["code_block_hygiene_status"] == "CODE_BLOCK_HYGIENE_CLEAN"
    assert empty["is_code_block_hygiene_compliant"] is True

    clean = audit_markdown_fenced_code_block_language_and_secret_hygiene(
        [
            {
                "doc_id": "DOC-CLEAN-CODE-01",
                "untagged_fenced_code_blocks_count": 0,
                "unclosed_code_fences_count": 0,
                "hardcoded_secret_or_token_patterns_count": 0,
                "max_observed_code_line_length": 92,
            }
        ],
        max_code_line_length=120,
    )
    assert clean["evaluated_documents_count"] == 1
    assert clean["unclosed_fence_or_secret_leak_doc_ids"] == []
    assert clean["untagged_language_or_long_line_doc_ids"] == []
    assert clean["code_block_hygiene_status"] == "CODE_BLOCK_HYGIENE_CLEAN"
    assert clean["is_code_block_hygiene_compliant"] is True


def test_audit_markdown_fenced_code_block_language_and_secret_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        AnydocService,
        audit_markdown_fenced_code_block_language_and_secret_hygiene,
    )

    sample = [
        {
            "doc_id": "DOC-99",
            "max_observed_code_line_length": 88,
        }
    ]
    assert (
        AnyDocService.audit_markdown_fenced_code_block_language_and_secret_hygiene(
            sample
        )
        == audit_markdown_fenced_code_block_language_and_secret_hygiene(sample)
    )
    assert (
        AnydocService.audit_markdown_fenced_code_block_language_and_secret_hygiene(
            sample
        )
        == audit_markdown_fenced_code_block_language_and_secret_hygiene(sample)
    )
    assert (
        "audit_markdown_fenced_code_block_language_and_secret_hygiene"
        in mod.__all__
    )


def test_table_structure_or_pipe_breach():
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_cell_hygiene,
    )

    res = audit_markdown_table_column_parity_and_cell_hygiene(
        [
            {
                "table_id": "TABLE-ROW-RAGGED",
                "row_column_counts_consistent": False,
            },
            {
                "table_id": "TABLE-NO-DELIMITER",
                "valid_delimiter_row_present": False,
            },
            {
                "table_id": "TABLE-UNESCAPED-PIPES",
                "unescaped_inline_pipes_count": 2,
            },
        ],
        max_columns_count=10,
        max_cell_char_length=240,
    )
    assert res["evaluated_tables_count"] == 3
    assert res["malformed_structure_or_pipe_table_ids"] == [
        "TABLE-ROW-RAGGED",
        "TABLE-NO-DELIMITER",
        "TABLE-UNESCAPED-PIPES",
    ]
    assert res["wide_or_overflow_cell_table_ids"] == []
    assert (
        res["table_hygiene_status"]
        == "MARKDOWN_TABLE_STRUCTURE_OR_PIPE_BREACH"
    )
    assert res["is_table_hygiene_compliant"] is False


def test_table_width_or_cell_overflow_warning():
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_cell_hygiene,
    )

    res = audit_markdown_table_column_parity_and_cell_hygiene(
        [
            {
                "table_id": "TABLE-TOO-WIDE",
                "header_columns_count": 14,
            },
            {
                "table_id": "TABLE-CELL-OVERFLOW",
                "max_observed_cell_chars": 500,
            },
        ],
        max_columns_count=10,
        max_cell_char_length=240,
    )
    assert res["evaluated_tables_count"] == 2
    assert res["malformed_structure_or_pipe_table_ids"] == []
    assert res["wide_or_overflow_cell_table_ids"] == [
        "TABLE-TOO-WIDE",
        "TABLE-CELL-OVERFLOW",
    ]
    assert (
        res["table_hygiene_status"]
        == "MARKDOWN_TABLE_WIDTH_OR_CELL_OVERFLOW_WARNING"
    )
    assert res["is_table_hygiene_compliant"] is False


def test_table_boundaries_optimal_and_defaults():
    from backend.services.anydoc_service import (
        audit_markdown_table_column_parity_and_cell_hygiene,
    )

    res = audit_markdown_table_column_parity_and_cell_hygiene(
        [
            {
                "table_id": "TABLE-BOUNDARY",
                "header_columns_count": 10,
                "max_observed_cell_chars": 240,
            },
            {"table_id": "TABLE-ALL-DEFAULTS"},
        ],
        max_columns_count=10,
        max_cell_char_length=240,
    )
    assert res["evaluated_tables_count"] == 2
    assert res["malformed_structure_or_pipe_table_ids"] == []
    assert res["wide_or_overflow_cell_table_ids"] == []
    assert res["table_hygiene_status"] == "MARKDOWN_TABLE_HYGIENE_OPTIMAL"
    assert res["is_table_hygiene_compliant"] is True


def test_table_hygiene_invalid_and_binding():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_table_column_parity_and_cell_hygiene,
    )

    empty = audit_markdown_table_column_parity_and_cell_hygiene(None)
    assert empty["evaluated_tables_count"] == 0
    assert empty["malformed_structure_or_pipe_table_ids"] == []
    assert empty["wide_or_overflow_cell_table_ids"] == []
    assert empty["table_hygiene_status"] == "MARKDOWN_TABLE_HYGIENE_OPTIMAL"
    assert empty["is_table_hygiene_compliant"] is True

    invalid = audit_markdown_table_column_parity_and_cell_hygiene(
        [42, "not-a-dict", None, {"table_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_tables_count"] == 0

    defaults = audit_markdown_table_column_parity_and_cell_hygiene(
        [
            {
                "table_id": "TABLE-DEFAULTS",
                "header_columns_count": None,
                "row_column_counts_consistent": None,
                "valid_delimiter_row_present": None,
                "unescaped_inline_pipes_count": None,
                "max_observed_cell_chars": None,
            }
        ]
    )
    assert defaults["evaluated_tables_count"] == 1
    assert defaults["table_hygiene_status"] == "MARKDOWN_TABLE_HYGIENE_OPTIMAL"
    assert defaults["is_table_hygiene_compliant"] is True

    sample = [
        {
            "table_id": "TABLE-1",
            "header_columns_count": 4,
            "max_observed_cell_chars": 100,
        }
    ]
    assert (
        AnyDocService.audit_markdown_table_column_parity_and_cell_hygiene(
            sample
        )
        == audit_markdown_table_column_parity_and_cell_hygiene(sample)
    )
    assert (
        "audit_markdown_table_column_parity_and_cell_hygiene"
        in mod.__all__
    )


def test_audit_markdown_footnote_citation_reciprocity_and_key_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_reciprocity_and_key_hygiene,
    )

    res = audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
        [
            {
                "footnote_id": "  FN-ORPHAN-DEF  ",
                "inline_reference_exists": False,
                "definition_block_exists": True,
                "duplicate_definition_count": 1,
                "char_length": 150,
                "canonical_url_or_doi_present": True,
            },
            {
                "footnote_id": "FN-MISSING-DEF",
                "inline_reference_exists": True,
                "definition_block_exists": False,
                "duplicate_definition_count": 1,
                "char_length": 750,
                "canonical_url_or_doi_present": True,
            },
            {
                "footnote_id": "FN-DUPLICATE",
                "inline_reference_exists": True,
                "definition_block_exists": True,
                "duplicate_definition_count": 2,
                "char_length": 200,
                "canonical_url_or_doi_present": True,
            },
            {
                "footnote_id": "FN-CLEAN",
                "inline_reference_exists": True,
                "definition_block_exists": True,
                "duplicate_definition_count": 1,
                "char_length": 600,
                "canonical_url_or_doi_present": True,
            },
        ]
    )
    assert res["evaluated_footnotes_count"] == 4
    assert res["unpaired_or_duplicate_footnote_ids"] == [
        "FN-ORPHAN-DEF",
        "FN-MISSING-DEF",
        "FN-DUPLICATE",
    ]
    assert res["verbose_or_uncited_source_footnote_ids"] == ["FN-MISSING-DEF"]
    assert (
        res["footnote_hygiene_status"]
        == "MARKDOWN_FOOTNOTE_UNPAIRED_OR_DUPLICATE_BREACH"
    )
    assert res["is_footnote_hygiene_compliant"] is False


def test_audit_markdown_footnote_citation_reciprocity_and_key_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_reciprocity_and_key_hygiene,
    )

    res = audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
        [
            {
                "footnote_id": "FN-VERBOSE",
                "inline_reference_exists": True,
                "definition_block_exists": True,
                "duplicate_definition_count": 1,
                "char_length": 601,
                "canonical_url_or_doi_present": True,
            },
            {
                "footnote_id": "FN-NO-URL",
                "inline_reference_exists": True,
                "definition_block_exists": True,
                "duplicate_definition_count": 1,
                "char_length": 600,
                "canonical_url_or_doi_present": False,
            },
        ],
        max_footnote_char_length=600,
        require_canonical_url_or_doi=True,
    )
    assert res["evaluated_footnotes_count"] == 2
    assert res["unpaired_or_duplicate_footnote_ids"] == []
    assert res["verbose_or_uncited_source_footnote_ids"] == [
        "FN-VERBOSE",
        "FN-NO-URL",
    ]
    assert (
        res["footnote_hygiene_status"]
        == "MARKDOWN_FOOTNOTE_LENGTH_OR_CITATION_WARNING"
    )
    assert res["is_footnote_hygiene_compliant"] is False


def test_audit_markdown_footnote_citation_reciprocity_and_key_hygiene_optimal_and_flags():
    from backend.services.anydoc_service import (
        audit_markdown_footnote_citation_reciprocity_and_key_hygiene,
    )

    res = audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
        [
            {
                "footnote_id": "FN-NO-URL-ALLOWED",
                "inline_reference_exists": True,
                "definition_block_exists": True,
                "duplicate_definition_count": 1,
                "char_length": 600,
                "canonical_url_or_doi_present": False,
            }
        ],
        max_footnote_char_length=600,
        require_canonical_url_or_doi=False,
    )
    assert res["evaluated_footnotes_count"] == 1
    assert res["unpaired_or_duplicate_footnote_ids"] == []
    assert res["verbose_or_uncited_source_footnote_ids"] == []
    assert res["footnote_hygiene_status"] == "MARKDOWN_FOOTNOTE_HYGIENE_OPTIMAL"
    assert res["is_footnote_hygiene_compliant"] is True


def test_audit_markdown_footnote_citation_reciprocity_and_key_hygiene_defensive_and_service_binding():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_footnote_citation_reciprocity_and_key_hygiene,
    )

    empty = audit_markdown_footnote_citation_reciprocity_and_key_hygiene(None)
    assert empty["evaluated_footnotes_count"] == 0
    assert (
        empty["footnote_hygiene_status"] == "MARKDOWN_FOOTNOTE_HYGIENE_OPTIMAL"
    )
    assert empty["is_footnote_hygiene_compliant"] is True

    defaults = audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"footnote_id": "   "},
            {
                "footnote_id": "FN-DEFAULTS",
                "inline_reference_exists": None,
                "definition_block_exists": None,
                "duplicate_definition_count": None,
                "char_length": None,
                "canonical_url_or_doi_present": None,
            },
        ]
    )
    assert defaults["evaluated_footnotes_count"] == 1
    assert (
        defaults["footnote_hygiene_status"]
        == "MARKDOWN_FOOTNOTE_HYGIENE_OPTIMAL"
    )
    assert defaults["is_footnote_hygiene_compliant"] is True

    sample = [{"footnote_id": "FN-99", "char_length": 120}]
    assert (
        AnyDocService.audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
            sample
        )
        == audit_markdown_footnote_citation_reciprocity_and_key_hygiene(sample)
    )
    assert (
        "audit_markdown_footnote_citation_reciprocity_and_key_hygiene"
        in mod.__all__
    )


def test_audit_markdown_gfm_task_list_completion_and_nesting_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_gfm_task_list_completion_and_nesting_hygiene,
    )

    res = audit_markdown_gfm_task_list_completion_and_nesting_hygiene(
        [
            {
                "checklist_id": "  CHK-INCONSISTENT-PARENT  ",
                "parent_checked_with_unchecked_children": True,
                "malformed_gfm_checkbox_syntax_count": 0,
                "observed_nesting_depth": 2,
                "unassigned_blocker_items_count": 0,
            },
            {
                "checklist_id": "CHK-MALFORMED-SYNTAX",
                "parent_checked_with_unchecked_children": False,
                "malformed_gfm_checkbox_syntax_count": 2,
                "observed_nesting_depth": 5,
                "unassigned_blocker_items_count": 1,
            },
            {
                "checklist_id": "CHK-CLEAN",
                "parent_checked_with_unchecked_children": False,
                "malformed_gfm_checkbox_syntax_count": 0,
                "observed_nesting_depth": 3,
                "unassigned_blocker_items_count": 0,
            },
        ]
    )
    assert res["evaluated_checklists_count"] == 3
    assert res["inconsistent_parent_or_syntax_checklist_ids"] == [
        "CHK-INCONSISTENT-PARENT",
        "CHK-MALFORMED-SYNTAX",
    ]
    assert res["deep_nesting_or_unassigned_blocker_checklist_ids"] == [
        "CHK-MALFORMED-SYNTAX"
    ]
    assert (
        res["task_list_hygiene_status"]
        == "MARKDOWN_TASK_LIST_PARITY_OR_SYNTAX_BREACH"
    )
    assert res["is_task_list_hygiene_compliant"] is False


def test_audit_markdown_gfm_task_list_completion_and_nesting_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_gfm_task_list_completion_and_nesting_hygiene,
    )

    res = audit_markdown_gfm_task_list_completion_and_nesting_hygiene(
        [
            {
                "checklist_id": "CHK-DEEP-NESTING",
                "parent_checked_with_unchecked_children": True,
                "malformed_gfm_checkbox_syntax_count": 0,
                "observed_nesting_depth": 4,
                "unassigned_blocker_items_count": 0,
            },
            {
                "checklist_id": "CHK-UNASSIGNED-BLOCKER",
                "parent_checked_with_unchecked_children": False,
                "malformed_gfm_checkbox_syntax_count": 0,
                "observed_nesting_depth": 3,
                "unassigned_blocker_items_count": 1,
            },
        ],
        max_nesting_depth=3,
        require_children_complete_when_parent_checked=False,
    )
    assert res["evaluated_checklists_count"] == 2
    assert res["inconsistent_parent_or_syntax_checklist_ids"] == []
    assert res["deep_nesting_or_unassigned_blocker_checklist_ids"] == [
        "CHK-DEEP-NESTING",
        "CHK-UNASSIGNED-BLOCKER",
    ]
    assert (
        res["task_list_hygiene_status"]
        == "MARKDOWN_TASK_LIST_NESTING_OR_BLOCKER_WARNING"
    )
    assert res["is_task_list_hygiene_compliant"] is False


def test_audit_markdown_gfm_task_list_completion_and_nesting_hygiene_optimal_and_defensive():
    from backend.services.anydoc_service import (
        audit_markdown_gfm_task_list_completion_and_nesting_hygiene,
    )

    empty = audit_markdown_gfm_task_list_completion_and_nesting_hygiene(None)
    assert empty["evaluated_checklists_count"] == 0
    assert (
        empty["task_list_hygiene_status"]
        == "MARKDOWN_TASK_LIST_HYGIENE_OPTIMAL"
    )
    assert empty["is_task_list_hygiene_compliant"] is True

    defaults = audit_markdown_gfm_task_list_completion_and_nesting_hygiene(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"checklist_id": "   "},
            {
                "checklist_id": "CHK-DEFAULTS",
                "parent_checked_with_unchecked_children": None,
                "malformed_gfm_checkbox_syntax_count": None,
                "observed_nesting_depth": None,
                "unassigned_blocker_items_count": None,
            },
        ]
    )
    assert defaults["evaluated_checklists_count"] == 1
    assert (
        defaults["task_list_hygiene_status"]
        == "MARKDOWN_TASK_LIST_HYGIENE_OPTIMAL"
    )
    assert defaults["is_task_list_hygiene_compliant"] is True


def test_audit_markdown_gfm_task_list_completion_and_nesting_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_gfm_task_list_completion_and_nesting_hygiene,
    )

    sample = [{"checklist_id": "CHK-99", "observed_nesting_depth": 2}]
    assert (
        AnyDocService.audit_markdown_gfm_task_list_completion_and_nesting_hygiene(
            sample
        )
        == audit_markdown_gfm_task_list_completion_and_nesting_hygiene(sample)
    )
    assert (
        "audit_markdown_gfm_task_list_completion_and_nesting_hygiene"
        in mod.__all__
    )


def test_audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene,
    )

    res = audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
        [
            {
                "diagram_id": "  MERMAID-UNSUPPORTED-HEADER  ",
                "supported_diagram_header_valid": False,
                "unescaped_special_chars_in_labels": 0,
                "nodes_count": 10,
                "edges_count": 12,
            },
            {
                "diagram_id": "MERMAID-UNESCAPED-PARENS",
                "supported_diagram_header_valid": True,
                "unescaped_special_chars_in_labels": 3,
                "nodes_count": 60,
                "edges_count": 100,
            },
            {
                "diagram_id": "MERMAID-CLEAN",
                "supported_diagram_header_valid": True,
                "unescaped_special_chars_in_labels": 0,
                "nodes_count": 45,
                "edges_count": 80,
            },
        ]
    )
    assert res["evaluated_diagrams_count"] == 3
    assert res["syntax_error_or_unsupported_diagram_ids"] == [
        "MERMAID-UNSUPPORTED-HEADER",
        "MERMAID-UNESCAPED-PARENS",
    ]
    assert res["overcrowded_node_or_edge_budget_diagram_ids"] == [
        "MERMAID-UNESCAPED-PARENS"
    ]
    assert (
        res["mermaid_hygiene_status"]
        == "MERMAID_SYNTAX_OR_LABEL_ESCAPE_BREACH"
    )
    assert res["is_mermaid_hygiene_compliant"] is False


def test_audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene,
    )

    res = audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
        [
            {
                "diagram_id": "MERMAID-TOO-MANY-NODES",
                "supported_diagram_header_valid": True,
                "unescaped_special_chars_in_labels": 0,
                "nodes_count": 46,
                "edges_count": 80,
            },
            {
                "diagram_id": "MERMAID-TOO-MANY-EDGES",
                "supported_diagram_header_valid": True,
                "unescaped_special_chars_in_labels": 0,
                "nodes_count": 45,
                "edges_count": 81,
            },
        ],
        max_nodes_per_diagram=45,
        max_edges_per_diagram=80,
    )
    assert res["evaluated_diagrams_count"] == 2
    assert res["syntax_error_or_unsupported_diagram_ids"] == []
    assert res["overcrowded_node_or_edge_budget_diagram_ids"] == [
        "MERMAID-TOO-MANY-NODES",
        "MERMAID-TOO-MANY-EDGES",
    ]
    assert (
        res["mermaid_hygiene_status"] == "MERMAID_NODE_OR_EDGE_BUDGET_WARNING"
    )
    assert res["is_mermaid_hygiene_compliant"] is False


def test_audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene_optimal_and_defensive():
    from backend.services.anydoc_service import (
        audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene,
    )

    empty = audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(None)
    assert empty["evaluated_diagrams_count"] == 0
    assert empty["mermaid_hygiene_status"] == "MERMAID_DIAGRAM_HYGIENE_OPTIMAL"
    assert empty["is_mermaid_hygiene_compliant"] is True

    defaults = audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"diagram_id": "   "},
            {
                "diagram_id": "MERMAID-DEFAULTS",
                "supported_diagram_header_valid": None,
                "unescaped_special_chars_in_labels": None,
                "nodes_count": None,
                "edges_count": None,
            },
        ]
    )
    assert defaults["evaluated_diagrams_count"] == 1
    assert (
        defaults["mermaid_hygiene_status"] == "MERMAID_DIAGRAM_HYGIENE_OPTIMAL"
    )
    assert defaults["is_mermaid_hygiene_compliant"] is True


def test_audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene,
    )

    sample = [{"diagram_id": "MERMAID-99", "nodes_count": 12}]
    assert (
        AnyDocService.audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
            sample
        )
        == audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
            sample
        )
    )
    assert (
        "audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene"
        in mod.__all__
    )


def test_audit_markdown_image_alt_text_and_svg_sanitization_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_svg_sanitization_hygiene,
    )

    res = audit_markdown_image_alt_text_and_svg_sanitization_hygiene(
        [
            {
                "image_id": "  IMG-SVG-XSS  ",
                "svg_inline_scripts_sanitized": False,
                "external_hotlink_blocked": True,
                "alt_text_char_length": 25,
                "payload_size_kb": 120.0,
            },
            {
                "image_id": "IMG-HOTLINK",
                "svg_inline_scripts_sanitized": True,
                "external_hotlink_blocked": False,
                "alt_text_char_length": 4,
                "payload_size_kb": 600.0,
            },
            {
                "image_id": "IMG-CLEAN",
                "svg_inline_scripts_sanitized": True,
                "external_hotlink_blocked": True,
                "alt_text_char_length": 8,
                "payload_size_kb": 500.0,
            },
        ]
    )
    assert res["evaluated_images_count"] == 3
    assert res["unsanitized_svg_or_hotlinked_image_ids"] == [
        "IMG-SVG-XSS",
        "IMG-HOTLINK",
    ]
    assert res["missing_alt_or_bloated_payload_image_ids"] == ["IMG-HOTLINK"]
    assert (
        res["image_hygiene_status"]
        == "MARKDOWN_IMAGE_SVG_XSS_OR_HOTLINK_BREACH"
    )
    assert res["is_image_hygiene_compliant"] is False


def test_audit_markdown_image_alt_text_and_svg_sanitization_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_svg_sanitization_hygiene,
    )

    res = audit_markdown_image_alt_text_and_svg_sanitization_hygiene(
        [
            {
                "image_id": "IMG-SHORT-ALT",
                "svg_inline_scripts_sanitized": True,
                "external_hotlink_blocked": True,
                "alt_text_char_length": 7,
                "payload_size_kb": 500.0,
            },
            {
                "image_id": "IMG-BLOATED",
                "svg_inline_scripts_sanitized": True,
                "external_hotlink_blocked": True,
                "alt_text_char_length": 8,
                "payload_size_kb": 500.1,
            },
        ],
        max_image_payload_kb=500.0,
        min_alt_text_chars=8,
    )
    assert res["evaluated_images_count"] == 2
    assert res["unsanitized_svg_or_hotlinked_image_ids"] == []
    assert res["missing_alt_or_bloated_payload_image_ids"] == [
        "IMG-SHORT-ALT",
        "IMG-BLOATED",
    ]
    assert (
        res["image_hygiene_status"]
        == "MARKDOWN_IMAGE_ALT_TEXT_OR_WEIGHT_WARNING"
    )
    assert res["is_image_hygiene_compliant"] is False


def test_audit_markdown_image_alt_text_and_svg_sanitization_hygiene_optimal_and_defensive():
    from backend.services.anydoc_service import (
        audit_markdown_image_alt_text_and_svg_sanitization_hygiene,
    )

    empty = audit_markdown_image_alt_text_and_svg_sanitization_hygiene(None)
    assert empty["evaluated_images_count"] == 0
    assert empty["image_hygiene_status"] == "MARKDOWN_IMAGE_HYGIENE_OPTIMAL"
    assert empty["is_image_hygiene_compliant"] is True

    defaults = audit_markdown_image_alt_text_and_svg_sanitization_hygiene(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"image_id": "   "},
            {
                "image_id": "IMG-DEFAULTS",
                "svg_inline_scripts_sanitized": None,
                "external_hotlink_blocked": None,
                "alt_text_char_length": None,
                "payload_size_kb": None,
            },
        ]
    )
    assert defaults["evaluated_images_count"] == 1
    assert defaults["image_hygiene_status"] == "MARKDOWN_IMAGE_HYGIENE_OPTIMAL"
    assert defaults["is_image_hygiene_compliant"] is True


def test_audit_markdown_image_alt_text_and_svg_sanitization_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_image_alt_text_and_svg_sanitization_hygiene,
    )

    sample = [{"image_id": "IMG-99", "payload_size_kb": 100.0}]
    assert (
        AnyDocService.audit_markdown_image_alt_text_and_svg_sanitization_hygiene(
            sample
        )
        == audit_markdown_image_alt_text_and_svg_sanitization_hygiene(sample)
    )
    assert (
        "audit_markdown_image_alt_text_and_svg_sanitization_hygiene"
        in mod.__all__
    )


def test_audit_markdown_yaml_frontmatter_schema_and_tag_hygiene_breach():
    from backend.services.anydoc_service import (
        audit_markdown_yaml_frontmatter_schema_and_tag_hygiene,
    )

    res = audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(
        [
            {
                "document_id": "  DOC-BAD-YAML  ",
                "yaml_delimiters_and_syntax_valid": False,
                "owner_and_iso8601_date_present": True,
                "tags_count": 3,
                "non_canonical_tags_count": 0,
            },
            {
                "document_id": "DOC-MISSING-OWNER",
                "yaml_delimiters_and_syntax_valid": True,
                "owner_and_iso8601_date_present": False,
                "tags_count": 10,
                "non_canonical_tags_count": 2,
            },
            {
                "document_id": "DOC-CLEAN",
                "yaml_delimiters_and_syntax_valid": True,
                "owner_and_iso8601_date_present": True,
                "tags_count": 8,
                "non_canonical_tags_count": 0,
            },
        ]
    )
    assert res["evaluated_documents_count"] == 3
    assert res["invalid_yaml_or_missing_metadata_document_ids"] == [
        "DOC-BAD-YAML",
        "DOC-MISSING-OWNER",
    ]
    assert res["tag_sprawl_or_non_canonical_document_ids"] == [
        "DOC-MISSING-OWNER"
    ]
    assert (
        res["frontmatter_hygiene_status"]
        == "FRONTMATTER_YAML_SYNTAX_OR_METADATA_BREACH"
    )
    assert res["is_frontmatter_hygiene_compliant"] is False


def test_audit_markdown_yaml_frontmatter_schema_and_tag_hygiene_warning():
    from backend.services.anydoc_service import (
        audit_markdown_yaml_frontmatter_schema_and_tag_hygiene,
    )

    res = audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(
        [
            {
                "document_id": "DOC-SPRAWL",
                "yaml_delimiters_and_syntax_valid": True,
                "owner_and_iso8601_date_present": False,
                "tags_count": 9,
                "non_canonical_tags_count": 0,
            },
            {
                "document_id": "DOC-NON-CANONICAL",
                "yaml_delimiters_and_syntax_valid": True,
                "owner_and_iso8601_date_present": True,
                "tags_count": 2,
                "non_canonical_tags_count": 1,
            },
            {
                "document_id": "DOC-ZERO-TAGS",
                "yaml_delimiters_and_syntax_valid": True,
                "owner_and_iso8601_date_present": True,
                "tags_count": 0,
                "non_canonical_tags_count": 0,
            },
        ],
        max_tags_per_document=8,
        require_owner_and_iso_date=False,
    )
    assert res["evaluated_documents_count"] == 3
    assert res["invalid_yaml_or_missing_metadata_document_ids"] == []
    assert res["tag_sprawl_or_non_canonical_document_ids"] == [
        "DOC-SPRAWL",
        "DOC-NON-CANONICAL",
        "DOC-ZERO-TAGS",
    ]
    assert (
        res["frontmatter_hygiene_status"]
        == "FRONTMATTER_TAG_TAXONOMY_OR_SPRAWL_WARNING"
    )
    assert res["is_frontmatter_hygiene_compliant"] is False


def test_audit_markdown_yaml_frontmatter_schema_and_tag_hygiene_optimal_and_defensive():
    from backend.services.anydoc_service import (
        audit_markdown_yaml_frontmatter_schema_and_tag_hygiene,
    )

    empty = audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(None)
    assert empty["evaluated_documents_count"] == 0
    assert (
        empty["frontmatter_hygiene_status"]
        == "FRONTMATTER_SCHEMA_HYGIENE_OPTIMAL"
    )
    assert empty["is_frontmatter_hygiene_compliant"] is True

    defaults = audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"document_id": "   "},
            {
                "document_id": "DOC-DEFAULTS",
                "yaml_delimiters_and_syntax_valid": None,
                "owner_and_iso8601_date_present": None,
                "tags_count": None,
                "non_canonical_tags_count": None,
            },
        ]
    )
    assert defaults["evaluated_documents_count"] == 1
    assert (
        defaults["frontmatter_hygiene_status"]
        == "FRONTMATTER_SCHEMA_HYGIENE_OPTIMAL"
    )
    assert defaults["is_frontmatter_hygiene_compliant"] is True


def test_audit_markdown_yaml_frontmatter_schema_and_tag_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_yaml_frontmatter_schema_and_tag_hygiene,
    )

    sample = [{"document_id": "DOC-99", "tags_count": 4}]
    assert (
        AnyDocService.audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(
            sample
        )
        == audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(sample)
    )
    assert (
        "audit_markdown_yaml_frontmatter_schema_and_tag_hygiene"
        in mod.__all__
    )


def test_audit_markdown_admonition_callout_syntax_and_nesting_hygiene_healthy():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_syntax_and_nesting_hygiene,
    )

    md = (
        "# Governance Guide\n\n"
        "> [!NOTE]\n"
        "> Keep all baseline artifacts under configuration control.\n\n"
        "Some explanatory paragraph between callouts.\n\n"
        "> [!WARNING]\n"
        "> Do not bypass CCB gate reviews.\n"
    )
    res = audit_markdown_admonition_callout_syntax_and_nesting_hygiene(md)
    assert res["is_clean"] is True
    assert res["status"] == "healthy"
    assert res["alerts_detected"] == 2
    assert res["unsupported_alert_types"] == []
    assert res["nested_alert_lines"] == []
    assert res["consecutive_alert_lines"] == []
    assert res["empty_or_inline_alert_lines"] == []
    assert res["Violations"] == []


def test_audit_markdown_admonition_callout_syntax_and_nesting_hygiene_critical_nested_and_unsupported():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_syntax_and_nesting_hygiene,
    )

    md = (
        "> [!DANGER]\n"
        "> Unsupported callout type.\n\n"
        "Paragraph separator.\n\n"
        ">> [!NOTE]\n"
        ">> Nested callout block.\n"
    )
    res = audit_markdown_admonition_callout_syntax_and_nesting_hygiene(md)
    assert res["is_clean"] is False
    assert res["status"] == "critical"
    assert res["alerts_detected"] == 2
    assert res["unsupported_alert_types"] == ["DANGER"]
    assert res["nested_alert_lines"] == [6]
    assert len(res["Violations"]) >= 2


def test_audit_markdown_admonition_callout_syntax_and_nesting_hygiene_warning_consecutive_and_inline():
    from backend.services.anydoc_service import (
        audit_markdown_admonition_callout_syntax_and_nesting_hygiene,
    )

    md = (
        "> [!TIP] Inline header text not allowed\n"
        "> Body line.\n\n"
        "> [!IMPORTANT]\n"
    )
    res = audit_markdown_admonition_callout_syntax_and_nesting_hygiene(md)
    assert res["is_clean"] is False
    assert res["status"] == "warning"
    assert res["alerts_detected"] == 2
    assert res["consecutive_alert_lines"] == [4]
    assert res["empty_or_inline_alert_lines"] == [1, 4]


def test_audit_markdown_admonition_callout_syntax_and_nesting_hygiene_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_admonition_callout_syntax_and_nesting_hygiene,
    )

    md = "> [!CAUTION]\n> Verify backups before migration.\n"
    assert (
        AnyDocService.audit_markdown_admonition_callout_syntax_and_nesting_hygiene(
            md
        )
        == audit_markdown_admonition_callout_syntax_and_nesting_hygiene(md)
    )
    assert (
        "audit_markdown_admonition_callout_syntax_and_nesting_hygiene"
        in mod.__all__
    )


# ── audit_markdown_glossary_definition_list_uniqueness_and_hygiene (PMBOK §4.4 & §10.2, pure helper) ──


def test_glossary_hygiene_optimal_terms():
    """Términos con etiqueta única, definición >= 15 chars y citación canónica -> 'GLOSSARY_HYGIENE_OPTIMAL'."""
    import backend.services.anydoc_service as anydoc_module
    from backend.services.anydoc_service import AnyDocService, audit_markdown_glossary_definition_list_uniqueness_and_hygiene

    entries = [
        {
            "term_id": "GL-001",
            "term_label": "ISO 21500",
            "definition_text": "Estándar internacional de gestión de proyectos.",
            "is_circular_self_reference": False,
            "has_canonical_citation": True,
        },
        {
            "term_id": "GL-002",
            # Defaults implícitos por campo: 'PMBOK', definición canónica, False, True.
        },
    ]
    res = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(entries)
    assert res == {
        "evaluated_terms_count": 2,
        "duplicate_or_circular_term_ids": [],
        "short_definition_or_uncited_term_ids": [],
        "glossary_hygiene_status": "GLOSSARY_HYGIENE_OPTIMAL",
        "is_glossary_compliant": True,
    }
    # Definición exactamente en 15 chars no es corta (comparación estricta <)
    at_limit = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [{"term_id": "GL-003", "definition_text": "m" * 15}]
    )
    assert at_limit["glossary_hygiene_status"] == "GLOSSARY_HYGIENE_OPTIMAL"
    assert (
        AnyDocService.audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
            entries
        )
        == res
    )
    assert "audit_markdown_glossary_definition_list_uniqueness_and_hygiene" in anydoc_module.__all__


def test_glossary_duplicate_or_circular_breach():
    """Etiqueta normalizada repetida o autorreferencia circular -> 'GLOSSARY_DUPLICATE_OR_CIRCULAR_BREACH' con precedencia sobre WARNING."""
    from backend.services.anydoc_service import (
        audit_markdown_glossary_definition_list_uniqueness_and_hygiene,
    )

    breach = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [                {"term_id": "GL-DUP-1", "term_label": "PMBOK Guide"},
                {"term_id": "GL-DUP-2", "term_label": "  pmbok guide  "},
            {
                "term_id": "GL-CIRC",
                "term_label": "EVM",
                "is_circular_self_reference": True,
            },
        ]
    )
    assert breach["evaluated_terms_count"] == 3
    assert breach["duplicate_or_circular_term_ids"] == ["GL-DUP-2", "GL-CIRC"]
    assert breach["glossary_hygiene_status"] == "GLOSSARY_DUPLICATE_OR_CIRCULAR_BREACH"
    assert breach["is_glossary_compliant"] is False

    # Breach tiene precedencia aunque también haya definiciones cortas / sin citación
    mixed = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [
            {"term_id": "GL-SHORT", "definition_text": "Corta"},
            {"term_id": "GL-DUP-A", "term_label": "WBS"},
            {"term_id": "GL-DUP-B", "term_label": "WBS"},
        ]
    )
    assert mixed["glossary_hygiene_status"] == "GLOSSARY_DUPLICATE_OR_CIRCULAR_BREACH"


def test_glossary_definition_or_citation_warning():
    """Definición < 15 caracteres o sin citación canónica (sin duplicados ni circularidad) -> 'GLOSSARY_DEFINITION_OR_CITATION_WARNING'."""
    from backend.services.anydoc_service import (
        audit_markdown_glossary_definition_list_uniqueness_and_hygiene,
    )

    warning = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [
            {
                "term_id": "GL-SHORT",
                "term_label": "SOW",
                "definition_text": "Corta",
                "has_canonical_citation": True,
            },
            {
                "term_id": "GL-UNCITED",
                "term_label": "RBS",
                "definition_text": "Breakdown estructural de riesgos y categorías PMI.",
                "has_canonical_citation": False,
            },
        ]
    )
    assert warning["evaluated_terms_count"] == 2
    assert warning["duplicate_or_circular_term_ids"] == []
    assert warning["short_definition_or_uncited_term_ids"] == ["GL-SHORT", "GL-UNCITED"]
    assert warning["glossary_hygiene_status"] == (
        "GLOSSARY_DEFINITION_OR_CITATION_WARNING"
    )
    assert warning["is_glossary_compliant"] is False

    custom = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [{"term_id": "GL-4", "definition_text": "a" * 40}],
        min_definition_chars=50,
    )
    assert custom["glossary_hygiene_status"] == "GLOSSARY_DEFINITION_OR_CITATION_WARNING"
    assert custom["short_definition_or_uncited_term_ids"] == ["GL-4"]


def test_glossary_empty_invalid_entries_and_field_reversion():
    """None / dicts inválidos se descartan; campos no str/no bool revierten a defaults del spec."""
    from backend.services.anydoc_service import (
        audit_markdown_glossary_definition_list_uniqueness_and_hygiene,
    )

    empty_res = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(None)
    assert empty_res == {
        "evaluated_terms_count": 0,
        "duplicate_or_circular_term_ids": [],
        "short_definition_or_uncited_term_ids": [],
        "glossary_hygiene_status": "GLOSSARY_HYGIENE_OPTIMAL",
        "is_glossary_compliant": True,
    }

    invalid_res = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        ["no-dict", None, {"term_id": "   "}, {"term_id": 123}, {"definition_text": "algo"}]
    )
    assert invalid_res["evaluated_terms_count"] == 0

    bad_fields = audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
        [
            {
                "term_id": "GL-BAD",
                "term_label": 42,
                "definition_text": None,
                "is_circular_self_reference": "sí",
                "has_canonical_citation": 1,
            }
        ]
    )
    assert bad_fields == {
        "evaluated_terms_count": 1,
        "duplicate_or_circular_term_ids": [],
        "short_definition_or_uncited_term_ids": [],
        "glossary_hygiene_status": "GLOSSARY_HYGIENE_OPTIMAL",
        "is_glossary_compliant": True,
    }


def test_audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety_healthy():
    from backend.services.anydoc_service import (
        audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety,
    )

    res = audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
        [
            {
                "block_id": "EQ-EVM-CPI",
                "delimiters_balanced": True,
                "unescaped_currency_collision": False,
                "macro_expansion_depth": 2,
                "contains_unsafe_command": False,
                "latex_expression": r"CPI = \frac{EV}{AC}",
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["is_clean"] is True
    assert res["blocks_evaluated"] == 1
    assert res["unbalanced_or_unsafe_block_ids"] == []
    assert res["macro_or_currency_warning_block_ids"] == []
    assert res["Violations"] == []


def test_audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety_critical():
    from backend.services.anydoc_service import (
        audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety,
    )

    res = audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
        [
            {
                "block_id": "EQ-UNSAFE",
                "delimiters_balanced": False,
                "latex_expression": r"\write18{rm -rf /}",
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_clean"] is False
    assert res["unbalanced_or_unsafe_block_ids"] == ["EQ-UNSAFE"]
    assert len(res["Violations"]) >= 1


def test_audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety_warning():
    from backend.services.anydoc_service import (
        audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety,
    )

    res = audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
        [
            {
                "id": "EQ-DEEP-MACRO",
                "delimiters_balanced": True,
                "unescaped_currency_collision": True,
                "macro_expansion_depth": 18,
                "latex_expression": r"x + y = z",
            }
        ],
        max_macro_expansion_depth=10,
    )
    assert res["status"] == "warning"
    assert res["is_clean"] is False
    assert res["unbalanced_or_unsafe_block_ids"] == []
    assert res["macro_or_currency_warning_block_ids"] == ["EQ-DEEP-MACRO"]
    assert res["records"][0]["macro_depth_or_currency_collision_warning"] is True


def test_audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety,
    )

    sample = [{"block_id": "EQ-1", "latex_expression": "a^2 + b^2 = c^2"}]
    assert (
        AnyDocService.audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
            sample
        )
        == audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
            sample
        )
    )
    assert (
        "audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety"
        in mod.__all__
    )


def test_audit_markdown_heading_hierarchy_and_anchor_slug_collisions_healthy():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_anchor_slug_collisions,
    )

    res = audit_markdown_heading_hierarchy_and_anchor_slug_collisions(
        [
            {
                "heading_id": "H-1",
                "level": 1,
                "text": "Project Charter Overview",
                "anchor_slug": "project-charter-overview",
            },
            {
                "heading_id": "H-2",
                "level": 2,
                "text": "Scope & Objectives",
                "anchor_slug": "scope-objectives",
            },
            {
                "heading_id": "H-3",
                "level": 3,
                "text": "Milestone Schedule",
                "anchor_slug": "milestone-schedule",
            },
        ]
    )
    assert res["status"] == "healthy"
    assert res["is_clean"] is True
    assert res["headings_evaluated"] == 3
    assert res["structural_breach_heading_ids"] == []
    assert res["level_skip_or_collision_heading_ids"] == []
    assert res["Violations"] == []


def test_audit_markdown_heading_hierarchy_and_anchor_slug_collisions_critical():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_anchor_slug_collisions,
    )

    res = audit_markdown_heading_hierarchy_and_anchor_slug_collisions(
        [
            {
                "heading_id": "H-ROOT-1",
                "level": 1,
                "text": "Primary Title",
                "anchor_slug": "primary-title",
            },
            {
                "heading_id": "H-ROOT-2",
                "level": 1,
                "text": "Second H1 Title",
                "anchor_slug": "second-h1-title",
            },
            {
                "heading_id": "H-EMPTY",
                "level": 2,
                "text": "   ",
                "anchor_slug": "",
            },
        ]
    )
    assert res["status"] == "critical"
    assert res["is_clean"] is False
    assert res["structural_breach_heading_ids"] == ["H-ROOT-2", "H-EMPTY"]
    assert len(res["Violations"]) >= 2


def test_audit_markdown_heading_hierarchy_and_anchor_slug_collisions_warning():
    from backend.services.anydoc_service import (
        audit_markdown_heading_hierarchy_and_anchor_slug_collisions,
    )

    res = audit_markdown_heading_hierarchy_and_anchor_slug_collisions(
        [
            {
                "id": "H-1",
                "level": 1,
                "text": "Architecture",
                "anchor_slug": "overview",
            },
            {
                "id": "H-SKIP",
                "level": 3,
                "text": "Skipped H2 Directly to H3",
                "anchor_slug": "skipped-h2",
            },
            {
                "id": "H-DUP-SLUG",
                "level": 3,
                "text": "Overview Duplicate",
                "anchor_slug": "OVERVIEW",
            },
        ],
        max_heading_depth=4,
    )
    assert res["status"] == "warning"
    assert res["is_clean"] is False
    assert res["structural_breach_heading_ids"] == []
    assert res["level_skip_or_collision_heading_ids"] == [
        "H-SKIP",
        "H-DUP-SLUG",
    ]
    assert res["records"][1]["skipped_heading_level_or_duplicate_slug"] is True
    assert res["records"][2]["skipped_heading_level_or_duplicate_slug"] is True


def test_audit_markdown_heading_hierarchy_and_anchor_slug_collisions_staticmethod_and_dunder_all():
    import backend.services.anydoc_service as mod
    from backend.services.anydoc_service import (
        AnyDocService,
        audit_markdown_heading_hierarchy_and_anchor_slug_collisions,
    )

    sample = [
        {"heading_id": "H-1", "level": 1, "text": "Title", "anchor_slug": "title"}
    ]
    assert (
        AnyDocService.audit_markdown_heading_hierarchy_and_anchor_slug_collisions(
            sample
        )
        == audit_markdown_heading_hierarchy_and_anchor_slug_collisions(sample)
    )
    assert (
        "audit_markdown_heading_hierarchy_and_anchor_slug_collisions"
        in mod.__all__
    )

