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

