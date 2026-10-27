"""Pruebas unitarias para extractores nativos de AnyDoc y previsualización documental universal.

Cubre:
1. Extractor CSV a Markdown GFM.
2. Extractor Excel (.xlsx) nativo (openpyxl y XML fallback) a Markdown GFM.
3. Extractor Word (.docx) nativo a Markdown GFM con jerarquías y tablas.
4. Extractor PowerPoint (.pptx) nativo por diapositivas.
5. Extractor OpenDocument (.odt) nativo.
6. Extractor RTF a texto limpio.
7. Formatos de código y texto (JSON, TXT, MD).
8. Endpoint convert_document_endpoint con file_url y prevención de path traversal.
"""

from __future__ import annotations

import io
import os
import zipfile
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.datastructures import Headers

from backend.core.storage import storage_service
from backend.services.anydoc_service import convert_bytes_to_markdown


def test_native_csv_extraction():
    data = b"Codigo,Nombre,Monto\nPROJ-01,Sistema Web,15000\nPROJ-02,App Movil,22000\n"
    res = convert_bytes_to_markdown(data, filename="presupuesto.csv")
    assert res["success"] is True
    assert res["format"] == "csv"
    assert "| Codigo | Nombre | Monto |" in res["markdown"]
    assert "| PROJ-01 | Sistema Web | 15000 |" in res["markdown"]
    assert "| PROJ-02 | App Movil | 22000 |" in res["markdown"]


def test_native_excel_extraction_zipfile_xml():
    # Construir un .xlsx válido en memoria con zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        # shared strings
        sst_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">'
            '<si><t>Hito</t></si>'
            '<si><t>Avance</t></si>'
            '<si><t>Fase 1</t></si>'
            '<si><t>100%</t></si>'
            '</sst>'
        )
        z.writestr("xl/sharedStrings.xml", sst_xml)
        # sheet1.xml
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>'
            '</sheetData>'
            '</worksheet>'
        )
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    excel_bytes = buf.getvalue()
    res = convert_bytes_to_markdown(excel_bytes, filename="cronograma.xlsx")
    assert res["success"] is True
    assert res["format"] == "xlsx"
    assert "## Hoja: " in res["markdown"]
    assert "| Hito | Avance |" in res["markdown"]
    assert "| Fase 1 | 100% |" in res["markdown"]


def test_native_docx_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p>'
            '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
            '<w:r><w:t>Acta de Constitucion</w:t></w:r>'
            '</w:p>'
            '<w:p>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t>Objetivo General:</w:t></w:r>'
            '<w:r><w:t> Implementar plataforma.</w:t></w:r>'
            '</w:p>'
            '<w:p>'
            '<w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr>'
            '<w:r><w:t>Primer requerimiento clave</w:t></w:r>'
            '</w:p>'
            '<w:tbl>'
            '<w:tr>'
            '<w:tc><w:p><w:r><w:t>Rol</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>Responsable</w:t></w:r></w:p></w:tc>'
            '</w:tr>'
            '<w:tr>'
            '<w:tc><w:p><w:r><w:t>Patrocinador</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>Pastor Titular</w:t></w:r></w:p></w:tc>'
            '</w:tr>'
            '</w:tbl>'
            '</w:body>'
            '</w:document>'
        )
        z.writestr("word/document.xml", doc_xml)

    docx_bytes = buf.getvalue()
    res = convert_bytes_to_markdown(docx_bytes, filename="acta.docx")
    assert res["success"] is True
    assert res["format"] == "docx"
    assert "# Acta de Constitucion" in res["markdown"]
    assert "**Objetivo General:**" in res["markdown"]
    assert "- Primer requerimiento clave" in res["markdown"]
    assert "| Rol | Responsable |" in res["markdown"]
    assert "| Patrocinador | Pastor Titular |" in res["markdown"]


def test_native_pptx_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        slide1_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:sp><p:txBody>'
            '<a:p><a:r><a:t>Vision Estrategica 2026</a:t></a:r></a:p>'
            '<a:p><a:r><a:t>Avance consolidado de sedes</a:t></a:r></a:p>'
            '</p:txBody></p:sp>'
            '</p:spTree></p:cSld>'
            '</p:sld>'
        )
        z.writestr("ppt/slides/slide1.xml", slide1_xml)

    pptx_bytes = buf.getvalue()
    res = convert_bytes_to_markdown(pptx_bytes, filename="presentacion.pptx")
    assert res["success"] is True
    assert res["format"] == "pptx"
    assert "## Diapositiva 1" in res["markdown"]
    assert "Vision Estrategica 2026" in res["markdown"]
    assert "Avance consolidado de sedes" in res["markdown"]


def test_native_odt_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        content_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
            '<office:body><office:text>'
            '<text:h text:outline-level="1">Capitulo 1: Marco de Referencia</text:h>'
            '<text:p>Este documento describe los estandares aplicables.</text:p>'
            '</office:text></office:body>'
            '</office:document-content>'
        )
        z.writestr("content.xml", content_xml)

    odt_bytes = buf.getvalue()
    res = convert_bytes_to_markdown(odt_bytes, filename="marco.odt")
    assert res["success"] is True
    assert res["format"] == "odt"
    assert "Capitulo 1: Marco de Referencia" in res["markdown"]
    assert "Este documento describe los estandares aplicables." in res["markdown"]


def test_native_rtf_extraction():
    rtf_bytes = b"{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Courier;}}\\f0\\pard Resumen Ejecutivo\\par Detalle de aprobacion.\\par}"
    res = convert_bytes_to_markdown(rtf_bytes, filename="informe.rtf")
    assert res["success"] is True
    assert res["format"] == "rtf"
    assert "Resumen Ejecutivo" in res["markdown"]
    assert "Detalle de aprobacion." in res["markdown"]


def test_json_and_plain_text():
    json_bytes = b'{\n  "proyecto": "PMI-CCF",\n  "estado": "ACTIVO"\n}'
    res = convert_bytes_to_markdown(json_bytes, filename="config.json")
    assert res["success"] is True
    assert res["format"] == "json"
    assert "```json" in res["markdown"]
    assert '"proyecto": "PMI-CCF"' in res["markdown"]


@pytest.mark.anyio
async def test_convert_document_endpoint_file_url_resolution():
    from backend.api.projects import convert_document_endpoint

    # 1. Crear un archivo temporal dentro de storage_service.base_dir
    os.makedirs(os.path.join(storage_service.base_dir, "projects"), exist_ok=True)
    test_file_path = os.path.join(storage_service.base_dir, "projects", "test_doc_preview.txt")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("# Archivo Local Verificado\n\nContenido leido directamente de disco.")

    mock_request = MagicMock()
    mock_request.headers = Headers({"content-type": "application/json"})

    # Probar con file_url relativa
    async def json_body_rel():
        return {
            "filename": "test_doc_preview.txt",
            "file_url": "/api/static/projects/test_doc_preview.txt",
        }

    mock_request.json = json_body_rel
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000001"

    response = await convert_document_endpoint(
        request=mock_request,
        file=None,
        format_hint=None,
        ocr="reject",
        current_user=mock_user,
    )

    assert response.success is True
    assert "# Archivo Local Verificado" in response.markdown

    # Probar prevención de path traversal
    async def json_body_traversal():
        return {
            "filename": "passwd",
            "file_url": "/api/static/../../../../../../etc/passwd",
        }

    mock_request.json = json_body_traversal
    with pytest.raises(HTTPException) as exc_info:
        await convert_document_endpoint(
            request=mock_request,
            file=None,
            format_hint=None,
            ocr="reject",
            current_user=mock_user,
        )
    assert exc_info.value.status_code == 400

    # Limpiar archivo temporal
    if os.path.exists(test_file_path):
        os.remove(test_file_path)


def test_native_docx_rejects_entity_expansion():
    """Imported XML must not expand attacker-controlled document entities."""
    from backend.services.anydoc_service import _extract_docx_to_markdown

    document = b'''<?xml version="1.0"?>
<!DOCTYPE document [<!ENTITY injected "ENTITY_EXPANSION_MUST_NOT_APPEAR">]>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>&injected;</w:t></w:r></w:p></w:body>
</w:document>'''
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("word/document.xml", document)
    result = _extract_docx_to_markdown(archive.getvalue())
    assert "ENTITY_EXPANSION_MUST_NOT_APPEAR" not in result
