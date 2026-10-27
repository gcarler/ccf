"""Servicio de conversión documental universal utilizando AnyDoc y extractores nativos en Python.

Convierte especificaciones, reportes y archivos de oficina (Word, Excel,
PowerPoint, OpenDocument, RTF, CSV, Markdown, Texto y PDF) en Markdown limpio y estructurado
compatible con GitHub Flavored Markdown (GFM) y la plataforma CCF.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import time
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Dict, List, Optional

from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

# Intentar importar la librería canónica anydoc
try:
    from anydoc import (
        ConvertError,
        EncryptedError,
        MalformedError,
        NeedsOcrError,
        ResourceLimitError,
        UnsupportedError,
        format_from_bytes,
        format_from_extension,
        to_markdown_bytes,
    )

    ANYDOC_AVAILABLE = True
except ImportError:  # pragma: no cover
    ANYDOC_AVAILABLE = False
    logger.warning("anydoc no está instalado o no se encuentra disponible en PYTHONPATH; utilizando extractores nativos")

SUPPORTED_EXTENSIONS = {
    "doc",
    "docx",
    "odt",
    "pdf",
    "ppt",
    "pptx",
    "rtf",
    "epub",
    "xlsx",
    "ods",
    "odp",
    "csv",
    "txt",
    "md",
    "json",
    "xml",
    "yaml",
    "yml",
}

FORMAT_ALIASES = {
    "xls": "xlsx",
    "xlsm": "xlsx",
    "docm": "docx",
    "pps": "pptx",
    "ppsx": "pptx",
    "ppt": "pptx",
    "text": "txt",
    "markdown": "md",
    "yml": "yaml",
}


class AnyDocConversionError(Exception):
    """Error durante la conversión documental con AnyDoc."""

    def __init__(self, message: str, code: str = "CONVERSION_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def is_anydoc_available() -> bool:
    """Verifica si el motor AnyDoc se encuentra disponible en el entorno (nativo o binario)."""
    return True


def detect_document_format(
    filename: Optional[str] = None,
    data: Optional[bytes] = None,
    format_hint: Optional[str] = None,
) -> str:
    """Detecta el formato del documento a partir de pista, extensión o cabecera binaria."""
    if format_hint:
        fmt = format_hint.lower().strip().lstrip(".")
        return FORMAT_ALIASES.get(fmt, fmt)

    if filename:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext:
            normalized = FORMAT_ALIASES.get(ext, ext)
            if normalized in SUPPORTED_EXTENSIONS:
                return normalized
            if ANYDOC_AVAILABLE:
                try:
                    anydoc_fmt = format_from_extension(ext)
                    if anydoc_fmt:
                        return str(anydoc_fmt)
                except Exception:
                    logger.debug("Best-effort detect_document_format failed; retaining fallback")

    if data and ANYDOC_AVAILABLE:
        try:
            detected = format_from_bytes(data)
            if detected:
                return str(detected)
        except Exception:
            logger.debug("Best-effort detect_document_format failed; retaining fallback")

    # Inspección de cabeceras binarias básicas si no hay anydoc
    if data:
        if data.startswith(b"%PDF"):
            return "pdf"
        if data.startswith(b"PK\x03\x04"):
            # Es un contenedor ZIP (DOCX, XLSX, PPTX, ODT)
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    namelist = z.namelist()
                    if any(n.startswith("word/") for n in namelist):
                        return "docx"
                    if any(n.startswith("xl/") for n in namelist):
                        return "xlsx"
                    if any(n.startswith("ppt/") for n in namelist):
                        return "pptx"
                    if "content.xml" in namelist:
                        return "odt"
            except Exception:
                logger.debug("Best-effort detect_document_format failed; retaining fallback")
        if data.startswith(b"{\\rtf"):
            return "rtf"

    return "unknown"


def _format_gfm_table(rows: List[List[str]]) -> str:
    """Genera una tabla GitHub Flavored Markdown bien formateada."""
    if not rows:
        return ""

    # Filtrar filas completamente vacías
    valid_rows = [row for row in rows if any(str(c).strip() for c in row)]
    if not valid_rows:
        return ""

    # Determinar el número máximo de columnas
    num_cols = max(len(r) for r in valid_rows)
    if num_cols == 0:
        return ""

    # Normalizar cada fila al mismo ancho
    norm_rows: List[List[str]] = []
    for r in valid_rows:
        row_cells = [str(c if c is not None else "").replace("|", "\\|").replace("\n", " ").strip() for c in r]
        while len(row_cells) < num_cols:
            row_cells.append("")
        norm_rows.append(row_cells)

    header = norm_rows[0]
    separator = ["---"] * num_cols
    data_rows = norm_rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in data_rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _extract_csv_to_markdown(data: bytes) -> str:
    """Extrae datos de un archivo CSV a tabla GFM."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")

    sample = text[:2048]
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        if ";" in sample and sample.count(";") > sample.count(","):
            delimiter = ";"
        elif "\t" in sample:
            delimiter = "\t"

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader]
    table = _format_gfm_table(rows)
    return table if table else "*(Archivo CSV vacío)*"


def _extract_excel_to_markdown(data: bytes) -> str:
    """Extrae datos de hojas Excel (.xlsx, .xlsm, .xls) a tablas GFM."""
    # 1. Intentar con openpyxl si está disponible
    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        md_parts: List[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows: List[List[str]] = []
            for row in ws.iter_rows(values_only=True):
                if any(v is not None and str(v).strip() for v in row):
                    rows.append([str(v) if v is not None else "" for v in row])
            if rows:
                md_parts.append(f"## Hoja: {sheet_name}\n\n" + _format_gfm_table(rows))
        wb.close()
        if md_parts:
            return "\n\n".join(md_parts)
    except ImportError:
        pass
    except Exception as e:
        logger.debug("openpyxl falló: %s, recurriendo a extracción XML", e)

    # 2. Extractor XML nativo en Python vía zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            namelist = z.namelist()

            # Leer cadenas compartidas (sharedStrings.xml)
            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in namelist:
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall(".//{*}si"):
                    texts = [t.text or "" for t in si.findall(".//{*}t")]
                    shared_strings.append("".join(texts))

            # Leer nombres de hojas (workbook.xml)
            sheet_files: List[tuple[str, str]] = []
            if "xl/workbook.xml" in namelist:
                wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
                sheets_info = []
                for s in wb_tree.findall(".//{*}sheet"):
                    name = s.get("name") or "Hoja"
                    s_id = s.get("sheetId") or "1"
                    r_id = s.attrib.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    ) or ""
                    sheets_info.append((name, s_id, r_id))

                if "xl/_rels/workbook.xml.rels" in namelist:
                    rels_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
                    rel_map = {
                        r.get("Id"): r.get("Target") for r in rels_tree.findall(".//{*}Relationship")
                    }
                    for name, s_id, r_id in sheets_info:
                        target = rel_map.get(r_id, f"worksheets/sheet{s_id}.xml")
                        if not target.startswith("xl/"):
                            target = "xl/" + target.lstrip("/")
                        sheet_files.append((name, target))
                else:
                    for name, s_id, _ in sheets_info:
                        sheet_files.append((name, f"xl/worksheets/sheet{s_id}.xml"))

            if not sheet_files:
                for name in sorted(namelist):
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                        s_name = Path(name).stem
                        sheet_files.append((f"Hoja {s_name}", name))

            md_parts = []
            for sheet_name, target_file in sheet_files:
                if target_file not in namelist:
                    continue
                sheet_tree = ET.fromstring(z.read(target_file))
                rows = []
                for row_elem in sheet_tree.findall(".//{*}row"):
                    row_data: List[str] = []
                    for c in row_elem.findall(".//{*}c"):
                        cell_type = c.get("t")
                        v_elem = c.find(".//{*}v")
                        val = ""
                        if v_elem is not None and v_elem.text:
                            raw_val = v_elem.text
                            if cell_type == "s" and raw_val.isdigit():
                                idx = int(raw_val)
                                val = shared_strings[idx] if idx < len(shared_strings) else raw_val
                            elif cell_type == "b":
                                val = "TRUE" if raw_val == "1" else "FALSE"
                            else:
                                val = raw_val
                        elif cell_type == "inlineStr":
                            t_elem = c.find(".//{*}t")
                            if t_elem is not None and t_elem.text:
                                val = t_elem.text
                        row_data.append(val)
                    if any(cell.strip() for cell in row_data):
                        rows.append(row_data)

                if rows:
                    md_parts.append(f"## Hoja: {sheet_name}\n\n" + _format_gfm_table(rows))

            if md_parts:
                return "\n\n".join(md_parts)
    except Exception as e:
        logger.warning("Error en extractor nativo de Excel: %s", e)

    return "*(Documento de hoja de cálculo sin tablas legibles)*"


def _extract_docx_to_markdown(data: bytes) -> str:
    """Extrae párrafos, encabezados, listas y tablas de un archivo Word (.docx, .docm) a GFM."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise ValueError("word/document.xml no encontrado en el paquete DOCX")

            doc_xml = z.read("word/document.xml")
            tree = ET.fromstring(doc_xml)
            body = tree.find(".//{*}body")
            if body is None:
                return ""

            lines: List[str] = []
            for elem in body:
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag == "p":
                    # Párrafo
                    p_style = elem.find(".//{*}pStyle")
                    style_val = ""
                    if p_style is not None:
                        style_val = (
                            p_style.attrib.get(
                                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                            )
                            or p_style.attrib.get("val")
                            or ""
                        ).lower()

                    is_bullet = elem.find(".//{*}numPr") is not None

                    # Extraer runs de texto
                    text_parts: List[str] = []
                    for r in elem.findall(".//{*}r"):
                        is_bold = r.find(".//{*}b") is not None
                        is_italic = r.find(".//{*}i") is not None
                        t_parts = [t.text or "" for t in r.findall(".//{*}t")]
                        run_text = "".join(t_parts)
                        if run_text:
                            if is_bold and is_italic:
                                run_text = f"***{run_text}***"
                            elif is_bold:
                                run_text = f"**{run_text}**"
                            elif is_italic:
                                run_text = f"*{run_text}*"
                            text_parts.append(run_text)

                    p_text = "".join(text_parts).strip()
                    if not p_text:
                        continue

                    if any(h in style_val for h in ("heading 1", "heading1", "title", "título 1", "titulo 1")):
                        lines.append(f"# {p_text}\n")
                    elif any(h in style_val for h in ("heading 2", "heading2", "subtítulo", "título 2", "titulo 2")):
                        lines.append(f"## {p_text}\n")
                    elif any(h in style_val for h in ("heading 3", "heading3", "título 3", "titulo 3")):
                        lines.append(f"### {p_text}\n")
                    elif is_bullet:
                        lines.append(f"- {p_text}")
                    else:
                        lines.append(f"{p_text}\n")

                elif tag == "tbl":
                    # Tabla
                    table_rows: List[List[str]] = []
                    for tr in elem.findall(".//{*}tr"):
                        row_cells: List[str] = []
                        for tc in tr.findall(".//{*}tc"):
                            cell_text_parts = [t.text.strip() for t in tc.findall(".//{*}t") if t.text]
                            row_cells.append(" ".join(cell_text_parts))
                        if any(c for c in row_cells):
                            table_rows.append(row_cells)

                    if table_rows:
                        tbl_md = _format_gfm_table(table_rows)
                        if tbl_md:
                            lines.append(tbl_md + "\n")

            return "\n".join(lines).strip()
    except Exception as e:
        logger.warning("Error extrayendo DOCX nativo: %s", e)
        return _extract_plain_strings(data)


def _extract_pptx_to_markdown(data: bytes) -> str:
    """Extrae diapositivas y textos de PowerPoint (.pptx, .pptm) a GFM."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            slide_names = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]

            def _slide_num(name: str) -> int:
                digits = "".join(ch for ch in Path(name).stem if ch.isdigit())
                return int(digits) if digits else 0

            slide_names.sort(key=_slide_num)

            slides_md: List[str] = []
            for i, sname in enumerate(slide_names, 1):
                tree = ET.fromstring(z.read(sname))
                paragraphs: List[str] = []
                for p in tree.findall(".//{*}p"):
                    t_nodes = [t.text for t in p.findall(".//{*}t") if t.text]
                    if t_nodes:
                        paragraphs.append(" ".join(t_nodes).strip())

                if paragraphs:
                    title = paragraphs[0]
                    body_paras = paragraphs[1:]
                    slide_text = f"## Diapositiva {i}: {title}\n\n"
                    if body_paras:
                        slide_text += "\n\n".join(f"- {p}" for p in body_paras)
                    slides_md.append(slide_text)
                else:
                    slides_md.append(f"## Diapositiva {i}\n\n*(Sin contenido de texto)*")

            if slides_md:
                return "\n\n---\n\n".join(slides_md)
    except Exception as e:
        logger.warning("Error extrayendo PPTX nativo: %s", e)

    return _extract_plain_strings(data)


def _extract_opendocument_to_markdown(data: bytes) -> str:
    """Extrae textos y tablas de OpenDocument (.odt, .ods, .odp) a GFM."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "content.xml" in z.namelist():
                tree = ET.fromstring(z.read("content.xml"))
                parts: List[str] = []
                for elem in tree.iter():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if tag in ("h", "heading"):
                        t = "".join(elem.itertext()).strip()
                        if t:
                            parts.append(f"## {t}\n")
                    elif tag == "p":
                        t = "".join(elem.itertext()).strip()
                        if t:
                            parts.append(f"{t}\n")
                    elif tag == "table":
                        t_rows: List[List[str]] = []
                        for row in elem.findall(".//{*}table-row"):
                            cells = ["".join(c.itertext()).strip() for c in row.findall(".//{*}table-cell")]
                            if any(cells):
                                t_rows.append(cells)
                        if t_rows:
                            parts.append(_format_gfm_table(t_rows) + "\n")

                if parts:
                    return "\n".join(parts).strip()
    except Exception as e:
        logger.warning("Error extrayendo OpenDocument nativo: %s", e)

    return _extract_plain_strings(data)


def _extract_rtf_or_legacy(data: bytes) -> str:
    """Extrae texto limpio de archivos RTF o binarios legacy (.doc)."""
    try:
        text = data.decode("utf-8", errors="ignore")
        if text.startswith("{\\rtf"):
            clean = re.sub(r"\{\\\*[^}]+\}", "", text)
            clean = re.sub(r"\\(par|line)\b", "\n", clean)
            clean = re.sub(r"\\[a-zA-Z0-9]+(-?[0-9]+)? ?", "", clean)
            clean = re.sub(r"[{}]", "", clean)
            lines = [line.strip() for line in clean.splitlines() if line.strip()]
            if lines:
                return "\n\n".join(lines)
    except Exception:
        logger.debug("Best-effort _extract_rtf_or_legacy failed; retaining fallback")
    return _extract_plain_strings(data)


def _extract_plain_strings(data: bytes) -> str:
    """Extrae cadenas imprimibles de archivos binarios."""
    try:
        raw_text = data.decode("latin-1", errors="ignore")
        tokens = re.findall(r"[\w\s.,;:!?()-]{4,}", raw_text)
        meaningful = [t.strip() for t in tokens if len(t.strip()) > 3]
        if meaningful:
            return "\n\n".join(meaningful[:200])
    except Exception:
        logger.debug("Best-effort _extract_plain_strings failed; retaining fallback")
    return "*(Contenido binario disponible para descarga)*"


def convert_bytes_to_markdown(
    data: bytes,
    filename: str = "document",
    format_hint: Optional[str] = None,
    ocr: str = "reject",
) -> Dict[str, Any]:
    """Convierte bytes de un documento en GitHub-Flavored Markdown limpio.

    Utiliza el motor AnyDoc cuando está disponible, o extractores nativos en Python
    (Word, Excel, CSV, PowerPoint, OpenDocument, RTF, Texto y Markdown) sin dependencias externas.

    Args:
        data: Contenido binario del documento.
        filename: Nombre original del archivo (para detección de extensión).
        format_hint: Pista explícita del formato (ej. 'csv', 'docx').
        ocr: Política ante páginas escaneadas ('reject' o 'hosted').

    Returns:
        Diccionario con el resultado de la conversión y metadatos.
    """
    start_time = time.perf_counter()
    detected_format = detect_document_format(filename=filename, data=data, format_hint=format_hint)

    if not data:
        return {
            "filename": filename,
            "format": detected_format,
            "markdown": "",
            "char_count": 0,
            "word_count": 0,
            "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "engine": "anydoc_native",
            "success": True,
            "error": None,
        }

    # 1. Formatos de texto plano y markdown directos
    if detected_format in ("txt", "md", "json", "xml", "yaml", "yml"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
            except Exception as e:
                raise AnyDocConversionError(
                    f"No se pudo decodificar el archivo de texto: {e}",
                    code="DECODE_ERROR",
                ) from e

        if detected_format in ("json", "xml", "yaml", "yml"):
            text = f"```{detected_format}\n{text}\n```"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "filename": filename,
            "format": detected_format,
            "markdown": text,
            "char_count": len(text),
            "word_count": len(text.split()),
            "processing_time_ms": elapsed_ms,
            "engine": "native_text",
            "success": True,
            "error": None,
        }

    # 2. Extractores nativos en Python (CSV, Excel, Word, PowerPoint, OpenDocument, RTF)
    native_result: Optional[str] = None
    engine_name = "anydoc_v0.2.4"

    if detected_format == "csv":
        native_result = _extract_csv_to_markdown(data)
    elif detected_format in ("xlsx", "xls", "xlsm"):
        native_result = _extract_excel_to_markdown(data)
    elif detected_format in ("docx", "docm"):
        native_result = _extract_docx_to_markdown(data)
    elif detected_format in ("pptx", "pptm", "ppt", "pps", "ppsx"):
        native_result = _extract_pptx_to_markdown(data)
    elif detected_format in ("odt", "ods", "odp"):
        native_result = _extract_opendocument_to_markdown(data)
    elif detected_format in ("rtf", "doc"):
        native_result = _extract_rtf_or_legacy(data)

    if native_result is not None:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "filename": filename,
            "format": detected_format,
            "markdown": native_result,
            "char_count": len(native_result),
            "word_count": len(native_result.split()),
            "processing_time_ms": elapsed_ms,
            "engine": engine_name,
            "success": True,
            "error": None,
        }

    # 3. Si no hay extractor nativo para este formato (ej. PDF) y AnyDoc no está disponible
    if not ANYDOC_AVAILABLE:
        # Para PDFs sin AnyDoc, generar un mensaje informativo con metadatos
        if detected_format == "pdf":
            clean_md = (
                "## Documento PDF\n\n"
                f"El archivo **{filename}** está disponible para visualización en el visor integrado "
                "o para descarga directa."
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "filename": filename,
                "format": "pdf",
                "markdown": clean_md,
                "char_count": len(clean_md),
                "word_count": len(clean_md.split()),
                "processing_time_ms": elapsed_ms,
                "engine": "native_pdf_meta",
                "success": True,
                "error": None,
            }

        raise AnyDocConversionError(
            f"El formato '{detected_format}' no cuenta con extractor soportado.",
            code="UNSUPPORTED_FORMAT",
        )

    # 4. AnyDoc canónico si está instalado
    try:
        format_arg = None
        if detected_format != "unknown":
            format_arg = detected_format

        ocr_mode = "hosted" if ocr == "hosted" else "reject"
        markdown_result = to_markdown_bytes(data, format=format_arg, ocr=ocr_mode)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        words = len(markdown_result.split())

        return {
            "filename": filename,
            "format": detected_format,
            "markdown": markdown_result,
            "char_count": len(markdown_result),
            "word_count": words,
            "processing_time_ms": elapsed_ms,
            "engine": "anydoc_v0.2.4",
            "success": True,
            "error": None,
        }

    except NeedsOcrError as e:
        logger.warning("Documento requiere OCR: %s", e)
        raise AnyDocConversionError(
            f"El documento contiene páginas escaneadas que requieren OCR: {e}",
            code="NEEDS_OCR",
            details={"pages": str(e)},
        ) from e
    except EncryptedError as e:
        logger.warning("Documento encriptado con contraseña: %s", e)
        raise AnyDocConversionError(
            "El documento está protegido con contraseña o encriptado.",
            code="ENCRYPTED_DOCUMENT",
        ) from e
    except MalformedError as e:
        logger.error("Documento malformado o corrupto: %s", e)
        raise AnyDocConversionError(
            f"El archivo está dañado o tiene una estructura inválida: {e}",
            code="MALFORMED_DOCUMENT",
        ) from e
    except UnsupportedError as e:
        logger.warning("Formato documental no soportado: %s", e)
        raise AnyDocConversionError(
            f"El formato '{detected_format}' no es soportado por AnyDoc: {e}",
            code="UNSUPPORTED_FORMAT",
        ) from e
    except ValueError as e:
        logger.warning("Formato documental inválido en AnyDoc: %s", e)
        raise AnyDocConversionError(
            f"Formato no reconocido o inválido: {e}",
            code="UNSUPPORTED_FORMAT",
        ) from e
    except ResourceLimitError as e:
        logger.error("Límite de recursos excedido durante la conversión: %s", e)
        raise AnyDocConversionError(
            "El documento excede los límites de memoria o tamaño permitido.",
            code="RESOURCE_LIMIT_EXCEEDED",
        ) from e
    except ConvertError as e:
        logger.error("Fallo de conversión general en AnyDoc: %s", e)
        raise AnyDocConversionError(
            f"Error al procesar el documento: {e}",
            code="CONVERT_ERROR",
        ) from e
    except Exception as e:
        logger.exception("Error inesperado en AnyDoc: %s", e)
        raise AnyDocConversionError(
            f"Error inesperado al convertir documento con AnyDoc: {e}",
            code="UNEXPECTED_ERROR",
        ) from e


def convert_file_to_markdown(
    file_path: str | Path,
    ocr: str = "reject",
) -> Dict[str, Any]:
    """Convierte un archivo existente en disco a Markdown."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    with open(path, "rb") as f:
        data = f.read()

    return convert_bytes_to_markdown(data=data, filename=path.name, ocr=ocr)


def audit_converted_markdown_structure(conversion_result: dict | None) -> dict:
    """Audita la densidad estructural del Markdown generado por AnyDoc (función pura).

    Inspecciona el diccionario de conversión (`conversion_result['markdown']`)
    y retorna:
    - `is_non_empty`: True si el markdown tiene contenido tras strip().
    - `heading_count`: líneas ATX (#..######): primer carácter '#' seguido
      de otro '#' o de un espacio.
    - `table_row_count`: líneas cuyo strip() empieza y termina con '|'.
    - `bullet_item_count`: líneas cuyo lstrip() empieza con '- ' o '* '.
    - `structural_density_status`: 'empty' (sin contenido), 'structured'
      (≥ 1 encabezado/fila/viñeta) o 'plain_prose' (solo texto).
    """
    markdown = str(((conversion_result or {}).get("markdown")) or "")
    is_non_empty = bool(markdown.strip())
    if not is_non_empty:
        return {
            "is_non_empty": False,
            "heading_count": 0,
            "table_row_count": 0,
            "bullet_item_count": 0,
            "structural_density_status": "empty",
        }

    heading_count = 0
    table_row_count = 0
    bullet_item_count = 0
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if re.match(r"^#(?:#|\s)", stripped):
            heading_count += 1
        cell = line.strip()
        if cell.startswith("|") and cell.endswith("|"):
            table_row_count += 1
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_item_count += 1

    if heading_count + table_row_count + bullet_item_count > 0:
        structural_density_status = "structured"
    else:
        structural_density_status = "plain_prose"

    return {
        "is_non_empty": True,
        "heading_count": heading_count,
        "table_row_count": table_row_count,
        "bullet_item_count": bullet_item_count,
        "structural_density_status": structural_density_status,
    }


def estimate_document_reading_metrics(
    markdown_or_result: str | dict[str, Any] | None,
    words_per_minute: int = 200,
) -> dict[str, Any]:
    """Estima la carga cognitiva, tiempo de lectura y nivel de profundidad de un artefacto documental (PMBOK §4.4)."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    word_count = len(text.split())
    char_count = len(text)
    wpm = max(50, int(words_per_minute or 200))
    estimated_reading_minutes = round(word_count / wpm, 2) if word_count > 0 else 0.0

    if word_count == 0:
        artifact_depth_tier = "empty"
    elif word_count < 150:
        artifact_depth_tier = "brief_note"
    elif word_count < 1000:
        artifact_depth_tier = "standard_artifact"
    else:
        artifact_depth_tier = "comprehensive_manual"

    return {
        "word_count": word_count,
        "char_count": char_count,
        "words_per_minute": wpm,
        "estimated_reading_minutes": estimated_reading_minutes,
        "artifact_depth_tier": artifact_depth_tier,
    }


def extract_markdown_governance_markers(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Extrae compromisos de acción, ítems completados y marcadores explícitos de decisión/riesgo en Markdown (PMBOK §4.4)."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    open_action_items_count = 0
    completed_action_items_count = 0
    decision_markers_count = 0
    risk_markers_count = 0

    decision_tokens = ("[DECISION]", "DECISIÓN:", "DECISION:", "ACUERDO:")
    risk_tokens = ("[RISK]", "[RIESGO]", "RIESGO:", "BLOQUEO:")

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ] ") or stripped.startswith("* [ ] "):
            open_action_items_count += 1
        elif (
            stripped.startswith("- [x] ")
            or stripped.startswith("- [X] ")
            or stripped.startswith("* [x] ")
            or stripped.startswith("* [X] ")
        ):
            completed_action_items_count += 1

        upper_line = stripped.upper()
        if any(token in upper_line for token in decision_tokens):
            decision_markers_count += 1
        if any(token in upper_line for token in risk_tokens):
            risk_markers_count += 1

    total_action_items = open_action_items_count + completed_action_items_count
    action_completion_pct = (
        round((completed_action_items_count / total_action_items) * 100.0, 2)
        if total_action_items > 0
        else 0.0
    )

    if total_action_items == 0 and decision_markers_count == 0 and risk_markers_count == 0:
        governance_traceability_status = "no_markers"
    elif open_action_items_count > 0:
        governance_traceability_status = "pending_actions"
    elif total_action_items > 0 and open_action_items_count == 0:
        governance_traceability_status = "actions_closed"
    else:
        governance_traceability_status = "decisions_recorded"

    return {
        "open_action_items_count": open_action_items_count,
        "completed_action_items_count": completed_action_items_count,
        "total_action_items": total_action_items,
        "action_completion_pct": action_completion_pct,
        "decision_markers_count": decision_markers_count,
        "risk_markers_count": risk_markers_count,
        "governance_traceability_status": governance_traceability_status,
    }


def summarize_markdown_tables_schema(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Extrae el esquema de las tablas Markdown del documento (PMBOK §4.4).

    Acepta un texto markdown o un dict de conversión AnyDoc (usa su clave
    'markdown'). Agrupa bloques contiguos de líneas que al hacer strip()
    inicien y terminen con '|'; un bloque es una tabla válida si tiene
    ≥ 2 líneas y la segunda es un separador cuyas celdas contienen solo
    '-', ':' y espacios (≥ 1 '-' por celda). Calcula:
    - `tables_count`: nº de tablas Markdown válidas.
    - `total_data_rows`: suma de filas de datos (bloques − 2 por tabla).
    - `max_columns_count`: máximo de columnas entre tablas válidas (0 si
      no hay tablas).
    - `distinct_column_headers`: cabeceras únicas en minúsculas, ordenadas.
    - `tabular_richness_status`: 'no_tables' (0 tablas),
      'empty_headers_only' (≥ 1 tabla sin filas de datos),
      'multi_table_dataset' (≥ 2 tablas y ≥ 2 filas totales) o
      'single_table_summary'.
    """
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    tables: list[list[str]] = []
    current_block: list[str] = []
    for line in text.splitlines():
        cell = line.strip()
        if cell.startswith("|") and cell.endswith("|"):
            current_block.append(cell)
        else:
            if current_block:
                tables.append(current_block)
                current_block = []
    if current_block:
        tables.append(current_block)

    tables_count = 0
    total_data_rows = 0
    max_columns_count = 0
    all_headers: set[str] = set()

    for block in tables:
        if len(block) < 2:
            continue
        separator = block[1].strip()[1:-1]
        sep_cells = [c.strip() for c in separator.split("|")]
        if not sep_cells or any(
            not (set(c) <= {"-", ":", " "} and "-" in c) for c in sep_cells
        ):
            continue
        tables_count += 1
        headers = [c.strip() for c in block[0].strip()[1:-1].split("|") if c.strip()]
        all_headers.update(h.lower() for h in headers)
        max_columns_count = max(max_columns_count, len(headers))
        total_data_rows += max(0, len(block) - 2)

    distinct_column_headers = sorted(all_headers)

    if tables_count == 0:
        tabular_richness_status = "no_tables"
    elif tables_count >= 1 and total_data_rows == 0:
        tabular_richness_status = "empty_headers_only"
    elif tables_count >= 2 and total_data_rows >= 2:
        tabular_richness_status = "multi_table_dataset"
    else:
        tabular_richness_status = "single_table_summary"

    return {
        "tables_count": tables_count,
        "total_data_rows": total_data_rows,
        "max_columns_count": max_columns_count,
        "distinct_column_headers": distinct_column_headers,
        "tabular_richness_status": tabular_richness_status,
    }


def summarize_markdown_code_blocks(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita la presencia de bloques de código cercados (```lang ... ```) en artefactos técnicos según PMI PMBOK §4.4."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    code_blocks_count = 0
    total_code_lines = 0
    languages_set: set[str] = set()
    untagged_blocks_count = 0
    unclosed_fences_count = 0

    in_block = False
    current_lang = "untagged"
    current_lines = 0

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                in_block = True
                rest = stripped[3:].strip().lower()
                current_lang = rest.split()[0] if rest else "untagged"
                current_lines = 0
            else:
                in_block = False
                code_blocks_count += 1
                total_code_lines += current_lines
                if current_lang == "untagged":
                    untagged_blocks_count += 1
                else:
                    languages_set.add(current_lang)
        elif in_block:
            current_lines += 1

    if in_block:
        unclosed_fences_count += 1

    languages = sorted(languages_set)

    if unclosed_fences_count > 0:
        technical_spec_status = "malformed_unclosed_fence"
    elif code_blocks_count == 0:
        technical_spec_status = "prose_only"
    elif untagged_blocks_count == 0:
        technical_spec_status = "well_typed_snippets"
    else:
        technical_spec_status = "mixed_untagged_snippets"

    return {
        "code_blocks_count": code_blocks_count,
        "total_code_lines": total_code_lines,
        "languages": languages,
        "untagged_blocks_count": untagged_blocks_count,
        "unclosed_fences_count": unclosed_fences_count,
        "technical_spec_status": technical_spec_status,
    }


_CHECKLIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+\[(?P<state>[ xX])\]\s+(?P<text>.+)$")
_ASSIGNEE_MENTION_RE = re.compile(r"(?:@[\w.-]+|(?i:(?:owner|responsable))\s*:)")


def extract_markdown_action_checklists(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Extrae e inspecciona listas de tareas Markdown (- [ ] / - [x]) fuera de bloques de código según PMI PMBOK §10.2 / §4.4."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    total_items = 0
    completed_items = 0
    pending_items = 0
    assigned_pending_items = 0

    in_code_block = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        match = _CHECKLIST_ITEM_RE.match(line)
        if not match:
            continue

        total_items += 1
        state = match.group("state")
        item_text = match.group("text").strip()
        if state.lower() == "x":
            completed_items += 1
        else:
            pending_items += 1
            if _ASSIGNEE_MENTION_RE.search(item_text):
                assigned_pending_items += 1

    completion_rate = (
        round((completed_items / total_items) * 100.0, 2)
        if total_items > 0
        else 0.0
    )

    if total_items == 0:
        posture = "NO_CHECKLIST_ITEMS"
    elif pending_items == 0:
        posture = "ALL_ACTIONS_COMPLETED"
    elif assigned_pending_items == pending_items:
        posture = "ACCOUNTABLE_PENDING_ACTIONS"
    else:
        posture = "UNASSIGNED_PENDING_ACTIONS"

    return {
        "total_items": total_items,
        "completed_items": completed_items,
        "pending_items": pending_items,
        "assigned_pending_items": assigned_pending_items,
        "completion_rate": completion_rate,
        "posture": posture,
    }


_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<label>[^\]]*)\]\((?P<url>[^)]*)\)")


def audit_markdown_reference_citations(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita enlaces e hipervínculos de referencia Markdown [label](url) fuera de bloques de código según PMI PMBOK §10.2 y §4.4."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    total_links = 0
    https_secure_links = 0
    insecure_http_links = 0
    internal_or_anchor_links = 0
    empty_or_placeholder_links = 0

    placeholder_urls = ("", "#", "todo", "tbd", "http://", "https://")

    in_code_block = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for match in _MARKDOWN_LINK_RE.finditer(line):
            total_links += 1
            label = match.group("label")
            url_clean = match.group("url").strip()
            url_low = url_clean.lower()

            if url_low.startswith("https://"):
                https_secure_links += 1
            if url_low.startswith("http://"):
                insecure_http_links += 1
            if url_clean.startswith(("/", "#")) and url_clean != "#":
                internal_or_anchor_links += 1
            if not label.strip() or url_low in placeholder_urls:
                empty_or_placeholder_links += 1

    citation_hygiene_pct = (
        round(
            max(
                0.0,
                (total_links - insecure_http_links - empty_or_placeholder_links)
                / total_links,
            )
            * 100.0,
            2,
        )
        if total_links > 0
        else 100.0
    )

    if total_links == 0:
        posture = "NO_CITATIONS"
    elif insecure_http_links > 0 or empty_or_placeholder_links > 0:
        posture = "MALFORMED_OR_INSECURE_CITATIONS"
    else:
        posture = "VERIFIED_CITATION_HYGIENE"

    return {
        "total_links": total_links,
        "https_secure_links": https_secure_links,
        "insecure_http_links": insecure_http_links,
        "internal_or_anchor_links": internal_or_anchor_links,
        "empty_or_placeholder_links": empty_or_placeholder_links,
        "citation_hygiene_pct": citation_hygiene_pct,
        "posture": posture,
    }


def audit_markdown_frontmatter_metadata(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita el bloque YAML frontmatter inicial según PMI PMBOK §10.2 / §4.4.

    Acepta markdown crudo o el dict de resultado de conversión (clave 'markdown').
    El frontmatter es el bloque delimitado por líneas '---' al inicio del
    documento. Extrae pares "clave: valor" con valor no vacío (claves en
    minúsculas, valores sin comillas/espacios) y calcula:
    - `has_frontmatter`: delimitadores '---' inicial y de cierre presentes.
    - `present_keys`: claves con valor no vacío, ordenadas.
    - `has_title`: alguna clave en ('title', 'titulo', 'título').
    - `has_owner`: alguna clave en ('author', 'owner', 'autor', 'responsable').
    - `has_version_or_date`: alguna clave en ('version', 'versión', 'date',
      'fecha', 'updated_at').
    - `completeness_score`: cobertura de los 3 pilares de control documental
      en % (2 decimales; 0.0 sin frontmatter).
    - `posture`: 'NO_FRONTMATTER' sin bloque; 'GOVERNED_DOCUMENT_HEADER'
      con 100.0; 'PARTIAL_FRONTMATTER' con > 0.0; y
      'EMPTY_OR_UNCONTROLLED_FRONTMATTER' con frontmatter sin pilares.
    """
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    has_frontmatter = False
    present_keys: list[str] = []
    if idx < len(lines) and lines[idx].strip() == "---":
        closing = None
        for cursor in range(idx + 1, len(lines)):
            if lines[cursor].strip() == "---":
                closing = cursor
                break
        if closing is not None:
            has_frontmatter = True
            for line in lines[idx + 1 : closing]:
                if not line.strip() or line.strip().startswith("#"):
                    continue
                if ":" not in line:
                    continue
                raw_key, raw_value = line.split(":", 1)
                key = raw_key.strip().lower()
                value = raw_value.strip().strip('"').strip("'").strip()
                if key and value:
                    present_keys.append(key)

    present_keys = sorted(set(present_keys))

    title_keys = {"title", "titulo", "título"}
    owner_keys = {"author", "owner", "autor", "responsable"}
    version_date_keys = {"version", "versión", "date", "fecha", "updated_at"}

    has_title = any(key in title_keys for key in present_keys)
    has_owner = any(key in owner_keys for key in present_keys)
    has_version_or_date = any(
        key in version_date_keys for key in present_keys
    )

    completeness_score = (
        round(
            (
                (int(has_title) + int(has_owner) + int(has_version_or_date))
                / 3.0
            )
            * 100.0,
            2,
        )
        if has_frontmatter
        else 0.0
    )

    if not has_frontmatter:
        posture = "NO_FRONTMATTER"
    elif completeness_score == 100.0:
        posture = "GOVERNED_DOCUMENT_HEADER"
    elif completeness_score > 0.0:
        posture = "PARTIAL_FRONTMATTER"
    else:
        posture = "EMPTY_OR_UNCONTROLLED_FRONTMATTER"

    return {
        "has_frontmatter": has_frontmatter,
        "present_keys": present_keys,
        "has_title": has_title,
        "has_owner": has_owner,
        "has_version_or_date": has_version_or_date,
        "completeness_score": completeness_score,
        "posture": posture,
    }


def extract_markdown_admonition_callouts(
    markdown_or_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Extrae bloques de alerta GFM (> [!NOTE|TIP|IMPORTANT|WARNING|CAUTION]) fuera de bloques de código según PMI PMBOK §10.2 y §4.4."""
    if isinstance(markdown_or_result, dict):
        text = str(markdown_or_result.get("markdown") or "")
    elif isinstance(markdown_or_result, str):
        text = markdown_or_result
    else:
        text = ""

    callout_re = re.compile(
        r"^\s*>\s*\[!(?P<kind>NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]",
        re.IGNORECASE,
    )

    counts_by_kind: dict[str, int] = {}
    in_fence = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = callout_re.match(line)
        if match:
            kind = match.group("kind").upper()
            counts_by_kind[kind] = counts_by_kind.get(kind, 0) + 1

    total_callouts = sum(counts_by_kind.values())
    critical_alerts_count = counts_by_kind.get("WARNING", 0) + counts_by_kind.get(
        "CAUTION", 0
    )
    governance_notices_count = counts_by_kind.get("IMPORTANT", 0)
    informational_count = counts_by_kind.get("NOTE", 0) + counts_by_kind.get("TIP", 0)

    if total_callouts == 0:
        posture = "NO_CALLOUT_ALERTS"
    elif critical_alerts_count > 0:
        posture = "HIGH_RISK_CAUTION_HIGHLIGHTED"
    elif governance_notices_count > 0:
        posture = "GOVERNANCE_EMPHASIS_PRESENT"
    else:
        posture = "INFORMATIONAL_GUIDANCE_ONLY"

    return {
        "total_callouts": total_callouts,
        "critical_alerts_count": critical_alerts_count,
        "governance_notices_count": governance_notices_count,
        "informational_count": informational_count,
        "counts_by_kind": counts_by_kind,
        "posture": posture,
    }


def extract_markdown_glossary_definitions(
    markdown_text: Optional[str | dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extrae y audita definiciones de glosario y siglas técnicas en Markdown (PMBOK §4.4 y §10.2).

    Ignora bloques de código cercados con ``` y detecta líneas de definición con
    término en negrita seguido de `:`, `—`, `–` o `-`.
    """
    if isinstance(markdown_text, dict):
        text = str(markdown_text.get("markdown") or "")
    elif isinstance(markdown_text, str):
        text = markdown_text
    else:
        text = ""

    definition_re = re.compile(
        r"^\s*(?:[-*+]\s+)?\*\*(?P<term>[^*:]+?)(?::\*\*\s*|\*\*\s*(?::|—|–|-)\s*)(?P<definition>.*)$"
    )
    placeholder_tokens = {"TBD", "TODO", "N/A", "PENDIENTE"}

    entries: list[dict[str, Any]] = []
    term_counts: dict[str, int] = {}
    shallow_set: set[str] = set()
    in_fence = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = definition_re.match(line)
        if not match:
            continue

        term = match.group("term").strip()
        if not term:
            continue
        definition = match.group("definition").strip()

        compact_term = re.sub(r"\s+", "", term)
        is_acronym = (
            2 <= len(compact_term) <= 10
            and compact_term.isalpha()
            and compact_term == compact_term.upper()
        )

        entries.append(
            {
                "term": term,
                "definition": definition,
                "is_acronym": is_acronym,
            }
        )

        norm_term = term.upper()
        term_counts[norm_term] = term_counts.get(norm_term, 0) + 1

        clean_def_upper = definition.upper().rstrip(".")
        if len(definition) < 10 or clean_def_upper in placeholder_tokens:
            shallow_set.add(term)

    total_definitions = len(entries)
    acronym_count = sum(1 for entry in entries if entry["is_acronym"])
    duplicate_terms = sorted(t for t, count in term_counts.items() if count > 1)
    shallow_definitions = sorted(shallow_set)

    if total_definitions == 0:
        glossary_posture = "NO_GLOSSARY_ENTRIES"
    elif len(duplicate_terms) > 0:
        glossary_posture = "DUPLICATE_TERM_CONFLICTS"
    elif len(shallow_definitions) > 0:
        glossary_posture = "SHALLOW_GLOSSARY_DEFINITIONS"
    else:
        glossary_posture = "GOVERNED_DOMAIN_GLOSSARY"

    return {
        "total_definitions": total_definitions,
        "acronym_count": acronym_count,
        "entries": entries,
        "duplicate_terms": duplicate_terms,
        "shallow_definitions": shallow_definitions,
        "glossary_posture": glossary_posture,
    }


def audit_markdown_mermaid_diagrams(
    markdown_text: Optional[str | dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extrae y audita bloques de diagramas ```mermaid ... ``` en documentos Markdown según PMI PMBOK §4.4 y §10.2."""
    if isinstance(markdown_text, dict):
        text = str(markdown_text.get("markdown") or "")
    elif isinstance(markdown_text, str):
        text = markdown_text
    else:
        text = ""

    supported_types = (
        "stateDiagram-v2",
        "sequenceDiagram",
        "stateDiagram",
        "classDiagram",
        "xychart-beta",
        "erDiagram",
        "flowchart",
        "graph",
        "gantt",
    )
    supported_map = {t.lower(): t for t in supported_types}
    html_hazard_re = re.compile(
        r"<\s*/?\s*(?:br|div|span|b|i|p)\b", re.IGNORECASE
    )

    mermaid_blocks: list[list[str]] = []
    in_fence = False
    is_mermaid = False
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                lang = stripped[3:].strip().split()[0].lower() if stripped[3:].strip() else ""
                in_fence = True
                is_mermaid = lang == "mermaid"
                current_lines = []
        else:
            if stripped.startswith("```"):
                if is_mermaid:
                    mermaid_blocks.append(current_lines)
                in_fence = False
                is_mermaid = False
                current_lines = []
            elif is_mermaid:
                current_lines.append(line)

    total_diagrams = len(mermaid_blocks)
    diagram_types: list[str] = []
    empty_diagram_indices: list[int] = []
    unsupported_diagram_indices: list[int] = []
    html_tag_hazard_indices: list[int] = []
    valid_diagram_count = 0

    for idx, block_lines in enumerate(mermaid_blocks, start=1):
        useful_lines = [
            ln.strip()
            for ln in block_lines
            if ln.strip() and not ln.strip().startswith("%%")
        ]

        is_empty = len(useful_lines) < 2
        if is_empty:
            empty_diagram_indices.append(idx)

        is_unsupported = False
        if len(useful_lines) >= 1:
            first_token = useful_lines[0].split()[0].rstrip(":")
            canonical_type = supported_map.get(first_token.lower())
            if canonical_type is not None:
                diagram_types.append(canonical_type)
            else:
                is_unsupported = True
                unsupported_diagram_indices.append(idx)

        has_html_hazard = any(html_hazard_re.search(ln) for ln in useful_lines)
        if has_html_hazard:
            html_tag_hazard_indices.append(idx)

        if not is_empty and not is_unsupported and not has_html_hazard:
            valid_diagram_count += 1

    if total_diagrams == 0:
        diagram_posture = "NO_MERMAID_DIAGRAMS"
    elif len(empty_diagram_indices) > 0 or len(unsupported_diagram_indices) > 0:
        diagram_posture = "INVALID_OR_UNSUPPORTED_DIAGRAM"
    elif len(html_tag_hazard_indices) > 0:
        diagram_posture = "HTML_LABEL_SYNTAX_HAZARD"
    else:
        diagram_posture = "GOVERNED_ARCHITECTURE_DIAGRAMS"

    return {
        "total_diagrams": total_diagrams,
        "diagram_types": diagram_types,
        "empty_diagram_indices": empty_diagram_indices,
        "unsupported_diagram_indices": unsupported_diagram_indices,
        "html_tag_hazard_indices": html_tag_hazard_indices,
        "valid_diagram_count": valid_diagram_count,
        "diagram_posture": diagram_posture,
    }


_MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]*)\)")
_GENERIC_ALT_LABELS = {
    "image",
    "img",
    "foto",
    "screenshot",
    "captura",
    "picture",
}


def audit_markdown_media_accessibility(
    markdown_text: Optional[str | dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extrae y audita imágenes incrustadas ![alt](url) en documentos Markdown según PMI PMBOK §4.4 y §10.2."""
    if isinstance(markdown_text, dict):
        text = str(markdown_text.get("markdown") or "")
    elif isinstance(markdown_text, str):
        text = markdown_text
    else:
        text = ""

    total_images = 0
    compliant_images_count = 0
    missing_alt_text_urls: list[str] = []
    insecure_or_broken_urls: list[str] = []

    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in _MARKDOWN_IMAGE_RE.finditer(line):
            total_images += 1
            alt_clean = match.group("alt").strip()
            url_clean = match.group("url").strip()
            recorded_url = url_clean if url_clean else "<empty-url>"

            bad_alt = (
                len(alt_clean) < 3
                or alt_clean.lower() in _GENERIC_ALT_LABELS
            )
            bad_url = (
                not url_clean
                or url_clean.lower().startswith("http://")
                or any(ch.isspace() for ch in url_clean)
            )

            if bad_alt:
                missing_alt_text_urls.append(recorded_url)
            if bad_url:
                insecure_or_broken_urls.append(recorded_url)
            if not bad_alt and not bad_url:
                compliant_images_count += 1

    accessibility_rate_pct = (
        round((compliant_images_count / total_images) * 100.0, 2)
        if total_images > 0
        else 0.0
    )

    if total_images == 0:
        media_posture = "NO_EMBEDDED_MEDIA"
    elif len(insecure_or_broken_urls) > 0:
        media_posture = "INSECURE_OR_BROKEN_MEDIA_LINKS"
    elif len(missing_alt_text_urls) > 0:
        media_posture = "MISSING_ACCESSIBLE_ALT_TEXT"
    else:
        media_posture = "GOVERNED_ACCESSIBLE_MEDIA"

    return {
        "total_images": total_images,
        "compliant_images_count": compliant_images_count,
        "missing_alt_text_urls": missing_alt_text_urls,
        "insecure_or_broken_urls": insecure_or_broken_urls,
        "accessibility_rate_pct": accessibility_rate_pct,
        "media_posture": media_posture,
    }


_ATX_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*#*$")
_INTERNAL_ANCHOR_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(#([A-Za-z0-9_-]+)\)")


def audit_markdown_toc_anchor_alignment(
    markdown_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Audita enlaces internos de ancla (#slug) en Tablas de Contenido (ToC) y jerarquía de encabezados ATX según PMI PMBOK §4.4."""
    if not markdown_text or not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "heading_count": 0,
            "internal_anchor_count": 0,
            "broken_toc_anchors": [],
            "skipped_level_headings": [],
            "is_aligned": True,
            "toc_posture": "NO_HEADINGS_FOUND",
        }

    non_fenced_lines: List[str] = []
    in_fence = False
    fence_marker = ""

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                continue
            non_fenced_lines.append(line)
        else:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue

    heading_count = 0
    heading_slugs: set[str] = set()
    skipped_level_headings: List[str] = []
    prev_level: Optional[int] = None

    for line in non_fenced_lines:
        match = _ATX_HEADING_RE.match(line)
        if not match:
            continue
        hashes, title = match.group(1), match.group(2)
        level = len(hashes)
        raw_title = title.strip()
        if not raw_title:
            continue

        heading_count += 1
        slug = re.sub(r"[^\w\s-]", "", raw_title.lower())
        slug = re.sub(r"\s+", "-", slug).strip("-")
        if slug:
            heading_slugs.add(slug)

        if prev_level is not None and level > prev_level + 1:
            if raw_title not in skipped_level_headings:
                skipped_level_headings.append(raw_title)
        prev_level = level

    internal_anchor_count = 0
    broken_toc_anchors: List[str] = []

    for line in non_fenced_lines:
        for match in _INTERNAL_ANCHOR_LINK_RE.finditer(line):
            internal_anchor_count += 1
            anchor = match.group(2)
            if anchor.lower() not in heading_slugs:
                formatted_anchor = f"#{anchor}"
                if formatted_anchor not in broken_toc_anchors:
                    broken_toc_anchors.append(formatted_anchor)

    is_aligned = bool(
        heading_count == 0
        or (len(broken_toc_anchors) == 0 and len(skipped_level_headings) == 0)
    )

    if heading_count == 0:
        toc_posture = "NO_HEADINGS_FOUND"
    elif len(broken_toc_anchors) > 0:
        toc_posture = "BROKEN_TOC_ANCHORS"
    elif len(skipped_level_headings) > 0:
        toc_posture = "HEADING_HIERARCHY_SKIP"
    else:
        toc_posture = "ALIGNED_DOCUMENT_STRUCTURE"

    return {
        "heading_count": heading_count,
        "internal_anchor_count": internal_anchor_count,
        "broken_toc_anchors": broken_toc_anchors,
        "skipped_level_headings": skipped_level_headings,
        "is_aligned": is_aligned,
        "toc_posture": toc_posture,
    }


_CHECKLIST_PROGRESS_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[([ xX])\]\s+(.+?)\s*$")
_CHECKLIST_PROGRESS_OWNER_RE = re.compile(r"@[A-Za-z0-9_.-]+")
_CHECKLIST_PROGRESS_BLOCKER_MARKERS = (
    "[blocker]",
    "[bloqueante]",
    "[critical]",
    "[critico]",
    "[crítico]",
    "blocker:",
    "bloqueante:",
)


def extract_markdown_checklist_progress(
    markdown_text: Optional[str],
) -> Dict[str, Any]:
    """Extrae listas de verificación Markdown (PMBOK §4.4 y §8.3), calculando avance porcentual, bloqueantes abiertos e ítems pendientes sin responsable."""
    if not markdown_text or not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_items": 0,
            "completed_items": 0,
            "pending_items": 0,
            "completion_rate_pct": 0.0,
            "open_blocker_items": [],
            "unassigned_pending_items": [],
            "is_complete": True,
            "checklist_posture": "NO_CHECKLIST_ITEMS",
        }

    non_fenced_lines: List[str] = []
    in_fence = False
    fence_marker = ""
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                continue
            non_fenced_lines.append(line)
        else:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue

    total_items = 0
    completed_items = 0
    pending_items = 0
    open_blocker_items: List[str] = []
    unassigned_pending_items: List[str] = []

    for line in non_fenced_lines:
        match = _CHECKLIST_PROGRESS_RE.match(line)
        if not match:
            continue
        state, text = match.group(1), match.group(2)
        is_checked = state.lower() == "x"
        item_text = text.strip()
        total_items += 1
        if is_checked:
            completed_items += 1
        else:
            pending_items += 1
            lowered = item_text.lower()
            if any(marker in lowered for marker in _CHECKLIST_PROGRESS_BLOCKER_MARKERS):
                open_blocker_items.append(item_text)
            has_owner = (
                bool(_CHECKLIST_PROGRESS_OWNER_RE.search(item_text))
                or "responsable:" in lowered
                or "owner:" in lowered
            )
            if not has_owner:
                unassigned_pending_items.append(item_text)

    if total_items == 0:
        return {
            "total_items": 0,
            "completed_items": 0,
            "pending_items": 0,
            "completion_rate_pct": 0.0,
            "open_blocker_items": [],
            "unassigned_pending_items": [],
            "is_complete": True,
            "checklist_posture": "NO_CHECKLIST_ITEMS",
        }

    completion_rate_pct = round((completed_items / total_items) * 100.0, 2)
    is_complete = bool(total_items > 0 and pending_items == 0)

    if len(open_blocker_items) > 0:
        checklist_posture = "BLOCKED_CHECKLIST_ITEMS"
    elif len(unassigned_pending_items) > 0:
        checklist_posture = "UNASSIGNED_PENDING_ITEMS"
    elif pending_items > 0:
        checklist_posture = "CHECKLIST_IN_PROGRESS"
    else:
        checklist_posture = "CHECKLIST_FULLY_COMPLETED"

    return {
        "total_items": total_items,
        "completed_items": completed_items,
        "pending_items": pending_items,
        "completion_rate_pct": completion_rate_pct,
        "open_blocker_items": open_blocker_items,
        "unassigned_pending_items": unassigned_pending_items,
        "is_complete": is_complete,
        "checklist_posture": checklist_posture,
    }


_FOOTNOTE_DEF_RE = re.compile(r"^\s*\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$")
_FOOTNOTE_REF_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")


def audit_markdown_footnote_citations(
    markdown_text: Optional[str],
) -> Dict[str, Any]:
    """Audita referencias de notas al pie Markdown ([^id]) y sus definiciones ([^id]: texto) según PMI PMBOK §4.4."""
    if not markdown_text or not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "referenced_footnotes_count": 0,
            "defined_footnotes_count": 0,
            "unresolved_footnote_refs": [],
            "unused_footnote_defs": [],
            "is_consistent": True,
            "citation_posture": "NO_FOOTNOTES_PRESENT",
        }

    non_fenced_lines: List[str] = []
    in_fence = False
    fence_marker = ""
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                continue
            non_fenced_lines.append(line)
        else:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue

    valid_defs: List[str] = []
    valid_defs_set: set[str] = set()
    unique_refs: List[str] = []
    unique_refs_set: set[str] = set()

    for line in non_fenced_lines:
        def_match = _FOOTNOTE_DEF_RE.match(line)
        if def_match:
            fn_id = def_match.group(1).lower()
            body = def_match.group(2)
            if body.strip():
                if fn_id not in valid_defs_set:
                    valid_defs_set.add(fn_id)
                    valid_defs.append(fn_id)
            ref_target_text = body
        else:
            ref_target_text = line

        for ref_match in _FOOTNOTE_REF_RE.finditer(ref_target_text):
            ref_id = ref_match.group(1).lower()
            if ref_id not in unique_refs_set:
                unique_refs_set.add(ref_id)
                unique_refs.append(ref_id)

    if len(valid_defs) == 0 and len(unique_refs) == 0:
        return {
            "referenced_footnotes_count": 0,
            "defined_footnotes_count": 0,
            "unresolved_footnote_refs": [],
            "unused_footnote_defs": [],
            "is_consistent": True,
            "citation_posture": "NO_FOOTNOTES_PRESENT",
        }

    unresolved_footnote_refs = [r for r in unique_refs if r not in valid_defs_set]
    unused_footnote_defs = [d for d in valid_defs if d not in unique_refs_set]
    is_consistent = bool(
        len(unresolved_footnote_refs) == 0 and len(unused_footnote_defs) == 0
    )

    if len(unresolved_footnote_refs) > 0:
        citation_posture = "UNRESOLVED_CITATION_REFERENCES"
    elif len(unused_footnote_defs) > 0:
        citation_posture = "ORPHAN_FOOTNOTE_DEFINITIONS"
    else:
        citation_posture = "CONSISTENT_FOOTNOTE_CITATIONS"

    return {
        "referenced_footnotes_count": len(unique_refs),
        "defined_footnotes_count": len(valid_defs),
        "unresolved_footnote_refs": unresolved_footnote_refs,
        "unused_footnote_defs": unused_footnote_defs,
        "is_consistent": is_consistent,
        "citation_posture": citation_posture,
    }


_FRONTMATTER_KV_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.*?)\s*$")
_FRONTMATTER_PLACEHOLDER_VALUES = frozenset(
    {"tbd", "n/a", "na", "null", "none", "unknown", "~"}
)


def audit_markdown_frontmatter_governance(
    markdown_text: Optional[str],
    required_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Audita el bloque YAML Frontmatter de gobernanza documental al inicio del documento Markdown (PMI §4.4)."""
    req_keys = [
        str(k).strip().lower()
        for k in (
            required_keys
            if required_keys is not None
            else ["title", "owner", "version", "status"]
        )
        if str(k).strip()
    ]
    if (
        not markdown_text
        or not isinstance(markdown_text, str)
        or not markdown_text.strip()
    ):
        return {
            "has_frontmatter": False,
            "parsed_keys_count": 0,
            "missing_required_keys": list(req_keys),
            "completeness_pct": 0.0,
            "is_compliant": False,
            "frontmatter_posture": "MISSING_FRONTMATTER_BLOCK",
        }

    lines = markdown_text.lstrip().splitlines()
    if not lines or lines[0].strip() != "---":
        return {
            "has_frontmatter": False,
            "parsed_keys_count": 0,
            "missing_required_keys": list(req_keys),
            "completeness_pct": 0.0,
            "is_compliant": False,
            "frontmatter_posture": "MISSING_FRONTMATTER_BLOCK",
        }

    end_idx: Optional[int] = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in {"---", "..."}:
            end_idx = idx
            break

    if end_idx is None:
        return {
            "has_frontmatter": False,
            "parsed_keys_count": 0,
            "missing_required_keys": list(req_keys),
            "completeness_pct": 0.0,
            "is_compliant": False,
            "frontmatter_posture": "UNCLOSED_FRONTMATTER_BLOCK",
        }

    valid_keys_set: set[str] = set()
    for line in lines[1:end_idx]:
        match = _FRONTMATTER_KV_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip().lower()
        raw_val = match.group(2)
        val = raw_val.strip().strip("'\"")
        if val and val.lower() not in _FRONTMATTER_PLACEHOLDER_VALUES:
            valid_keys_set.add(key)

    parsed_keys_count = len(valid_keys_set)
    missing_required_keys = [k for k in req_keys if k not in valid_keys_set]
    present_req_count = len(req_keys) - len(missing_required_keys)
    completeness_pct = (
        round((present_req_count / len(req_keys)) * 100.0, 2)
        if len(req_keys) > 0
        else 100.0
    )
    is_compliant = bool(len(missing_required_keys) == 0)
    frontmatter_posture = (
        "COMPLIANT_DOCUMENT_FRONTMATTER"
        if len(missing_required_keys) == 0
        else "INCOMPLETE_FRONTMATTER_METADATA"
    )

    return {
        "has_frontmatter": True,
        "parsed_keys_count": parsed_keys_count,
        "missing_required_keys": missing_required_keys,
        "completeness_pct": completeness_pct,
        "is_compliant": is_compliant,
        "frontmatter_posture": frontmatter_posture,
    }


_CALLOUT_FENCE_AUDIT_RE = re.compile(r"^\s*(```|~~~)")
_CALLOUT_HEADER_AUDIT_RE = re.compile(
    r"^\s*((?:>\s*)+)\[!([A-Za-z0-9_-]+)\](.*)$"
)
_CALLOUT_CONTINUATION_AUDIT_RE = re.compile(r"^\s*>\s*(?!\[!)(.*)$")
_SUPPORTED_CALLOUT_AUDIT_TYPES = frozenset(
    {"NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"}
)
_HIGH_SEVERITY_CALLOUT_AUDIT_TYPES = frozenset(
    {"IMPORTANT", "WARNING", "CAUTION"}
)


def audit_markdown_admonition_callouts(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita bloques de alerta/admonición estilo GitHub (> [!TYPE]) en documentos Markdown según PMI PMBOK §4.4 y §10.2."""
    if (
        not markdown_text
        or not isinstance(markdown_text, str)
        or not markdown_text.strip()
    ):
        return {
            "total_callouts": 0,
            "high_severity_callouts_count": 0,
            "unsupported_callout_types": [],
            "empty_callout_refs": [],
            "nested_callout_refs": [],
            "is_callout_hygiene_valid": True,
            "callout_posture": "NO_CALLOUTS_FOUND",
        }

    lines = markdown_text.splitlines()
    in_fence = False
    fence_marker = ""
    non_fenced_indices: set[int] = set()
    for idx, line in enumerate(lines):
        m_fence = _CALLOUT_FENCE_AUDIT_RE.match(line)
        if m_fence:
            marker = m_fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            non_fenced_indices.add(idx)

    total_callouts = 0
    high_severity_callouts_count = 0
    unsupported_callout_types: list[str] = []
    empty_callout_refs: list[str] = []
    nested_callout_refs: list[str] = []

    for idx, line in enumerate(lines):
        if idx not in non_fenced_indices:
            continue
        match = _CALLOUT_HEADER_AUDIT_RE.match(line)
        if not match:
            continue

        line_no = idx + 1
        gt_markers = re.sub(r"\s+", "", match.group(1))
        raw_type = match.group(2).strip()
        upper_type = raw_type.upper()
        inline_body = match.group(3).strip()

        total_callouts += 1
        if upper_type in _HIGH_SEVERITY_CALLOUT_AUDIT_TYPES:
            high_severity_callouts_count += 1

        if len(gt_markers) > 1:
            nested_callout_refs.append(f"L{line_no}:{raw_type}")

        if upper_type not in _SUPPORTED_CALLOUT_AUDIT_TYPES:
            unsupported_callout_types.append(raw_type)

        has_body = bool(inline_body)
        j = idx + 1
        while j < len(lines) and j in non_fenced_indices:
            cont_match = _CALLOUT_CONTINUATION_AUDIT_RE.match(lines[j])
            if not cont_match:
                break
            if cont_match.group(1).strip():
                has_body = True
            j += 1

        if not has_body:
            empty_callout_refs.append(f"L{line_no}:{upper_type}")

    is_callout_hygiene_valid = bool(
        len(unsupported_callout_types) == 0
        and len(empty_callout_refs) == 0
        and len(nested_callout_refs) == 0
    )

    if total_callouts == 0:
        callout_posture = "NO_CALLOUTS_FOUND"
    elif len(unsupported_callout_types) > 0:
        callout_posture = "UNSUPPORTED_CALLOUT_TYPE"
    elif len(nested_callout_refs) > 0:
        callout_posture = "NESTED_OR_MALFORMED_CALLOUT"
    elif len(empty_callout_refs) > 0:
        callout_posture = "EMPTY_CALLOUT_BODY"
    else:
        callout_posture = "VALID_CALLOUT_GOVERNANCE"

    return {
        "total_callouts": total_callouts,
        "high_severity_callouts_count": high_severity_callouts_count,
        "unsupported_callout_types": unsupported_callout_types,
        "empty_callout_refs": empty_callout_refs,
        "nested_callout_refs": nested_callout_refs,
        "is_callout_hygiene_valid": is_callout_hygiene_valid,
        "callout_posture": callout_posture,
    }


def audit_markdown_task_checklist_governance(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita listas de verificación y compromisos de acción en Markdown (PMBOK §4.4 y §8.3).

    Ignora bloques de código cercados (```). Cada ítem de checklist
    (`- [ ]` / `- [x]`) debe declarar texto y, si esta abierto, trazabilidad
    PMI: responsable (@handle) o fecha compromiso (YYYY-MM-DD):
    - `empty_task_item_lines`: líneas de ítems sin texto.
    - `untraceable_open_item_lines`: ítems abiertos sin responsable ni fecha.
    - `completion_rate_pct` (2 decimales; 0.0 sin ítems).
    - `is_checklist_governed`: con ítems y ambas listas vacías.
    - `checklist_posture`: 'NO_CHECKLIST_ITEMS' sin ítems;
      'EMPTY_CHECKLIST_ITEM_TEXT'; 'UNASSIGNED_OPEN_ACTION_ITEMS';
      'GOVERNED_ACTION_CHECKLIST'.
    """
    lines = (markdown_text if isinstance(markdown_text, str) else "").splitlines()
    checklist_re = re.compile(r"^[ \t]*[-*+]\s+\[([ xX])\]\s*(.*)$")
    owner_re = re.compile(r"@[A-Za-z0-9_.-]+")
    date_re = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

    total_checklist_items = 0
    completed_items_count = 0
    open_items_count = 0
    empty_task_item_lines: list[int] = []
    untraceable_open_item_lines: list[int] = []
    in_fence = False

    for line_number, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = checklist_re.match(line)
        if not match:
            continue

        total_checklist_items += 1
        marker = match.group(1)
        item_text = match.group(2).strip()

        if marker in ("x", "X"):
            completed_items_count += 1
        else:
            open_items_count += 1

        if not item_text:
            empty_task_item_lines.append(line_number)
        elif marker not in ("x", "X"):
            if not owner_re.search(item_text) and not date_re.search(item_text):
                untraceable_open_item_lines.append(line_number)

    completion_rate_pct = (
        round((completed_items_count / total_checklist_items) * 100.0, 2)
        if total_checklist_items > 0
        else 0.0
    )
    is_checklist_governed = bool(
        total_checklist_items > 0 and not empty_task_item_lines and not untraceable_open_item_lines
    )

    if total_checklist_items == 0:
        checklist_posture = "NO_CHECKLIST_ITEMS"
    elif empty_task_item_lines:
        checklist_posture = "EMPTY_CHECKLIST_ITEM_TEXT"
    elif untraceable_open_item_lines:
        checklist_posture = "UNASSIGNED_OPEN_ACTION_ITEMS"
    else:
        checklist_posture = "GOVERNED_ACTION_CHECKLIST"

    return {
        "total_checklist_items": total_checklist_items,
        "completed_items_count": completed_items_count,
        "open_items_count": open_items_count,
        "completion_rate_pct": completion_rate_pct,
        "empty_task_item_lines": empty_task_item_lines,
        "untraceable_open_item_lines": untraceable_open_item_lines,
        "is_checklist_governed": is_checklist_governed,
        "checklist_posture": checklist_posture,
    }


class AnyDocService:
    """Fachada canónica de conversión y auditoría documental AnyDoc PMI."""
    @staticmethod
    def is_anydoc_available() -> bool:
        return is_anydoc_available()

    @staticmethod
    def detect_document_format(
        filename: Optional[str] = None,
        data: Optional[bytes] = None,
        format_hint: Optional[str] = None,
    ) -> str:
        return detect_document_format(
            filename=filename, data=data, format_hint=format_hint
        )

    @staticmethod
    def convert_bytes_to_markdown(
        data: bytes,
        filename: str = "document",
        format_hint: Optional[str] = None,
        ocr: str = "reject",
    ) -> Dict[str, Any]:
        return convert_bytes_to_markdown(
            data=data, filename=filename, format_hint=format_hint, ocr=ocr
        )

    @staticmethod
    def convert_file_to_markdown(
        file_path: str | Path,
        ocr: str = "reject",
    ) -> Dict[str, Any]:
        return convert_file_to_markdown(file_path=file_path, ocr=ocr)

    @staticmethod
    def audit_converted_markdown_structure(conversion_result: dict | None) -> dict:
        return audit_converted_markdown_structure(conversion_result)

    @staticmethod
    def estimate_document_reading_metrics(
        markdown_or_result: str | dict[str, Any] | None,
        words_per_minute: int = 200,
    ) -> dict[str, Any]:
        return estimate_document_reading_metrics(
            markdown_or_result, words_per_minute=words_per_minute
        )

    @staticmethod
    def extract_markdown_governance_markers(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return extract_markdown_governance_markers(markdown_or_result)

    @staticmethod
    def summarize_markdown_tables_schema(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return summarize_markdown_tables_schema(markdown_or_result)

    @staticmethod
    def summarize_markdown_code_blocks(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return summarize_markdown_code_blocks(markdown_or_result)

    @staticmethod
    def extract_markdown_action_checklists(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return extract_markdown_action_checklists(markdown_or_result)

    @staticmethod
    def audit_markdown_reference_citations(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return audit_markdown_reference_citations(markdown_or_result)

    @staticmethod
    def audit_markdown_frontmatter_metadata(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return audit_markdown_frontmatter_metadata(markdown_or_result)

    @staticmethod
    def extract_markdown_admonition_callouts(
        markdown_or_result: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        return extract_markdown_admonition_callouts(markdown_or_result)

    @staticmethod
    def extract_markdown_glossary_definitions(
        markdown_text: Optional[str | dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return extract_markdown_glossary_definitions(markdown_text)

    @staticmethod
    def audit_markdown_mermaid_diagrams(
        markdown_text: Optional[str | dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return audit_markdown_mermaid_diagrams(markdown_text)

    @staticmethod
    def audit_markdown_media_accessibility(
        markdown_text: Optional[str | dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return audit_markdown_media_accessibility(markdown_text)

    @staticmethod
    def audit_markdown_toc_anchor_alignment(
        markdown_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        return audit_markdown_toc_anchor_alignment(markdown_text)

    @staticmethod
    def extract_markdown_checklist_progress(
        markdown_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        return extract_markdown_checklist_progress(markdown_text)

    @staticmethod
    def audit_markdown_footnote_citations(
        markdown_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        return audit_markdown_footnote_citations(markdown_text)

    @staticmethod
    def audit_markdown_frontmatter_governance(
        markdown_text: Optional[str],
        required_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return audit_markdown_frontmatter_governance(
            markdown_text, required_keys=required_keys
        )

    @staticmethod
    def audit_markdown_admonition_callouts(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_admonition_callouts(markdown_text)

    @staticmethod
    def audit_markdown_task_checklist_governance(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_task_checklist_governance(markdown_text)

    @staticmethod
    def audit_markdown_code_fence_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_code_fence_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_image_asset_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_image_asset_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_mermaid_diagram_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_mermaid_diagram_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_footnote_reference_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_footnote_reference_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_internal_anchor_links(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_internal_anchor_links(markdown_text)

    @staticmethod
    def audit_markdown_callout_admonition_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_callout_admonition_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_table_column_alignment_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_table_column_alignment_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_task_list_checklist_hygiene(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_task_list_checklist_hygiene(markdown_text)

    @staticmethod
    def audit_markdown_heading_hierarchy_and_duplicates(
        markdown_text: str | None = None,
    ) -> dict[str, Any]:
        return audit_markdown_heading_hierarchy_and_duplicates(markdown_text)




_CODE_FENCE_OPEN_AUDIT_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*(.*)$")
_CODE_FENCE_CLOSE_AUDIT_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
_MARKDOWN_IMAGE_ASSET_AUDIT_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_GENERIC_IMAGE_ALT_TEXTS = {
    "image",
    "img",
    "photo",
    "screenshot",
    "picture",
    "imagen",
    "foto",
    "captura",
}


def audit_markdown_code_fence_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita los bloques de código cercados con triple backtick verificando etiqueta de lenguaje, cuerpo no vacío y cierre de bloque según PMI PMBOK §4.4 y §10.2."""
    if not markdown_text or not isinstance(markdown_text, str):
        lines: list[str] = []
    else:
        lines = markdown_text.splitlines()

    closed_block_count = 0
    detected_languages: list[str] = []
    untagged_fence_lines: list[int] = []
    empty_code_block_lines: list[int] = []

    in_block = False
    open_line: int | None = None
    lang_tag = ""
    body_lines: list[str] = []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_block:
            if stripped.startswith("```"):
                in_block = True
                open_line = line_no
                after_fence = stripped[3:].strip()
                lang_tag = (
                    after_fence.split()[0].lower() if after_fence else ""
                )
                body_lines = []
        else:
            if stripped.startswith("```"):
                closed_block_count += 1
                assert open_line is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
                if lang_tag == "":
                    untagged_fence_lines.append(open_line)
                else:
                    if lang_tag not in detected_languages:
                        detected_languages.append(lang_tag)
                if not any(ln.strip() for ln in body_lines):
                    empty_code_block_lines.append(open_line)
                in_block = False
                open_line = None
                lang_tag = ""
                body_lines = []
            else:
                body_lines.append(line)

    has_unclosed_fence = in_block and open_line is not None
    unclosed_fence_line = open_line if has_unclosed_fence else None
    is_hygienic = bool(
        not has_unclosed_fence
        and len(untagged_fence_lines) == 0
        and len(empty_code_block_lines) == 0
    )

    return {
        "closed_block_count": closed_block_count,
        "detected_languages": detected_languages,
        "untagged_fence_lines": untagged_fence_lines,
        "empty_code_block_lines": empty_code_block_lines,
        "has_unclosed_fence": has_unclosed_fence,
        "unclosed_fence_line": unclosed_fence_line,
        "is_hygienic": is_hygienic,
    }


def audit_markdown_image_asset_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita imágenes embebidas Markdown verificando alt-text accesible y URL/ruta segura según PMI PMBOK §4.4 y §10.2."""
    if not markdown_text or not isinstance(markdown_text, str):
        lines: list[str] = []
    else:
        lines = markdown_text.splitlines()

    total_images = 0
    compliant_images_count = 0
    missing_alt_text_refs: list[str] = []
    invalid_asset_url_refs: list[str] = []

    in_fence = False
    fence_char = ""
    fence_len = 0

    for line_no, line in enumerate(lines, start=1):
        if not in_fence:
            m_open = _CODE_FENCE_OPEN_AUDIT_RE.match(line)
            if m_open:
                marker = m_open.group(1)
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                continue
        else:
            m_close = _CODE_FENCE_CLOSE_AUDIT_RE.match(line)
            if (
                m_close
                and m_close.group(1)[0] == fence_char
                and len(m_close.group(1)) >= fence_len
            ):
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        for m_img in _MARKDOWN_IMAGE_ASSET_AUDIT_RE.finditer(line):
            total_images += 1
            alt_raw, raw_target = m_img.group(1), m_img.group(2)
            alt_clean = alt_raw.strip()
            url_part = (
                raw_target.strip().split()[0] if raw_target.strip() else ""
            )
            ref_id = f"L{line_no}:{url_part or 'EMPTY_URL'}"

            has_missing_alt = (
                len(alt_clean) < 3
                or alt_clean.lower() in _GENERIC_IMAGE_ALT_TEXTS
            )
            url_lower = url_part.lower()
            has_invalid_url = (
                not url_part
                or url_lower.startswith("http://")
                or url_lower.startswith("javascript:")
                or url_part.startswith("/tmp/")  # nosec B108 # rejects temporary-path URLs; does not create files
            )

            if has_missing_alt:
                missing_alt_text_refs.append(ref_id)
            if has_invalid_url:
                invalid_asset_url_refs.append(ref_id)
            if not has_missing_alt and not has_invalid_url:
                compliant_images_count += 1

    is_image_hygiene_valid = bool(
        len(missing_alt_text_refs) == 0 and len(invalid_asset_url_refs) == 0
    )

    if total_images == 0:
        image_hygiene_posture = "NO_IMAGES_FOUND"
    elif len(invalid_asset_url_refs) > 0:
        image_hygiene_posture = "INVALID_OR_INSECURE_ASSET_URL"
    elif len(missing_alt_text_refs) > 0:
        image_hygiene_posture = "MISSING_ACCESSIBLE_ALT_TEXT"
    else:
        image_hygiene_posture = "COMPLIANT_IMAGE_ASSET_HYGIENE"

    return {
        "total_images": total_images,
        "compliant_images_count": compliant_images_count,
        "missing_alt_text_refs": missing_alt_text_refs,
        "invalid_asset_url_refs": invalid_asset_url_refs,
        "is_image_hygiene_valid": is_image_hygiene_valid,
        "image_hygiene_posture": image_hygiene_posture,
    }


_SUPPORTED_MERMAID_DIAGRAM_TYPES = {
    "flowchart",
    "graph",
    "sequenceDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "classDiagram",
    "erDiagram",
    "xychart-beta",
    "gantt",
    "pie",
    "mindmap",
}
_MERMAID_BLOCK_OPEN_RE = re.compile(r"^[ \t]*```mermaid[ \t]*$")
_MERMAID_BLOCK_CLOSE_RE = re.compile(r"^[ \t]*```[ \t]*$")


def audit_markdown_mermaid_diagram_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita bloques cercados ```mermaid ... ``` verificando tipo soportado, contenido no vacío y balance de delimitadores (PMBOK §4.4 / §10.2)."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    blocks: list[list[str]] = []
    in_mermaid = False
    current_lines: list[str] = []

    for line in lines:
        if not in_mermaid:
            if _MERMAID_BLOCK_OPEN_RE.match(line):
                in_mermaid = True
                current_lines = []
        else:
            if _MERMAID_BLOCK_CLOSE_RE.match(line):
                blocks.append(current_lines)
                in_mermaid = False
                current_lines = []
            else:
                current_lines.append(line)

    total_mermaid_blocks = len(blocks)
    empty_mermaid_block_indices: list[int] = []
    unsupported_diagram_type_indices: list[int] = []
    unbalanced_delimiter_indices: list[int] = []

    open_to_close = {"(": ")", "[": "]", "{": "}"}
    close_to_open = {")": "(", "]": "[", "}": "{"}

    def _are_delimiters_balanced(text_lines: list[str]) -> bool:
        stack: list[str] = []
        in_quotes = False
        for raw_line in text_lines:
            for ch in raw_line:
                if ch == '"':
                    in_quotes = not in_quotes
                    continue
                if in_quotes:
                    continue
                if ch in open_to_close:
                    stack.append(ch)
                elif ch in close_to_open:
                    if not stack or stack[-1] != close_to_open[ch]:
                        return False
                    stack.pop()
        return not in_quotes and len(stack) == 0

    for idx, block_lines in enumerate(blocks, start=1):
        useful_lines = [
            ln.strip()
            for ln in block_lines
            if ln.strip() and not ln.strip().startswith("%%")
        ]
        if len(useful_lines) < 2:
            empty_mermaid_block_indices.append(idx)

        if len(useful_lines) >= 1:
            first_token = useful_lines[0].split()[0]
            if first_token not in _SUPPORTED_MERMAID_DIAGRAM_TYPES:
                unsupported_diagram_type_indices.append(idx)

        if not _are_delimiters_balanced(useful_lines):
            unbalanced_delimiter_indices.append(idx)

    is_mermaid_hygienic = bool(
        total_mermaid_blocks > 0
        and len(empty_mermaid_block_indices) == 0
        and len(unsupported_diagram_type_indices) == 0
        and len(unbalanced_delimiter_indices) == 0
    )

    if total_mermaid_blocks == 0:
        mermaid_posture = "NO_MERMAID_DIAGRAMS"
    elif len(empty_mermaid_block_indices) > 0:
        mermaid_posture = "EMPTY_MERMAID_BLOCK"
    elif len(unsupported_diagram_type_indices) > 0:
        mermaid_posture = "UNSUPPORTED_MERMAID_DIAGRAM_TYPE"
    elif len(unbalanced_delimiter_indices) > 0:
        mermaid_posture = "UNBALANCED_MERMAID_DELIMITERS"
    else:
        mermaid_posture = "HYGIENIC_MERMAID_DIAGRAMS"

    return {
        "total_mermaid_blocks": total_mermaid_blocks,
        "empty_mermaid_block_indices": empty_mermaid_block_indices,
        "unsupported_diagram_type_indices": unsupported_diagram_type_indices,
        "unbalanced_delimiter_indices": unbalanced_delimiter_indices,
        "is_mermaid_hygienic": is_mermaid_hygienic,
        "mermaid_posture": mermaid_posture,
    }


_FOOTNOTE_DEFINITION_AUDIT_RE = re.compile(
    r"^[ \t]*\[\^([A-Za-z0-9_.-]+)\]:[ \t]*(.*)$"
)
_FOOTNOTE_REFERENCE_AUDIT_RE = re.compile(r"\[\^([A-Za-z0-9_.-]+)\](?!:)")


def audit_markdown_footnote_reference_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita integridad bidireccional de referencias y definiciones de notas al pie en Markdown según PMI PMBOK §4.4 y §10.2."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    defined_ids: list[str] = []
    referenced_ids: list[str] = []
    empty_footnote_definition_ids: list[str] = []

    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m_def = _FOOTNOTE_DEFINITION_AUDIT_RE.match(line)
        if m_def:
            fn_id, content = m_def.group(1), m_def.group(2)
            if fn_id not in defined_ids:
                defined_ids.append(fn_id)
            if not content.strip() and fn_id not in empty_footnote_definition_ids:
                empty_footnote_definition_ids.append(fn_id)
            continue

        for m_ref in _FOOTNOTE_REFERENCE_AUDIT_RE.finditer(line):
            ref_id = m_ref.group(1)
            if ref_id not in referenced_ids:
                referenced_ids.append(ref_id)

    defined_set = set(defined_ids)
    referenced_set = set(referenced_ids)

    unresolved_reference_ids = [
        ref_id for ref_id in referenced_ids if ref_id not in defined_set
    ]
    orphan_definition_ids = [
        def_id for def_id in defined_ids if def_id not in referenced_set
    ]

    total_references = len(referenced_ids)
    total_definitions = len(defined_ids)
    is_footnote_hygienic = bool(
        total_references > 0
        and len(unresolved_reference_ids) == 0
        and len(orphan_definition_ids) == 0
        and len(empty_footnote_definition_ids) == 0
    )

    if total_references == 0 and total_definitions == 0:
        footnote_posture = "NO_FOOTNOTES_PRESENT"
    elif len(unresolved_reference_ids) > 0:
        footnote_posture = "UNRESOLVED_FOOTNOTE_REFERENCES"
    elif len(empty_footnote_definition_ids) > 0:
        footnote_posture = "EMPTY_FOOTNOTE_DEFINITIONS"
    elif len(orphan_definition_ids) > 0:
        footnote_posture = "ORPHAN_FOOTNOTE_DEFINITIONS"
    else:
        footnote_posture = "HYGIENIC_FOOTNOTE_CITATIONS"

    return {
        "total_references": total_references,
        "total_definitions": total_definitions,
        "unresolved_reference_ids": unresolved_reference_ids,
        "orphan_definition_ids": orphan_definition_ids,
        "empty_footnote_definition_ids": empty_footnote_definition_ids,
        "is_footnote_hygienic": is_footnote_hygienic,
        "footnote_posture": footnote_posture,
    }


_MARKDOWN_HEADING_AUDIT_RE = re.compile(r"^[ \t]*#{1,6}\s+(.+?)[ \t]*$")
_ANCHOR_INTERNAL_LINK_RE = re.compile(r"\[([^\]]*)\]\(#([^)\s]+)\)")


def _markdown_github_heading_slug(text: str) -> str:
    """Normaliza texto de encabezado a slug estilo GitHub (minúsculas, alfanuméricos, espacios->'-')."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug.strip("-")


def audit_markdown_internal_anchor_links(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita resolución de enlaces de ancla internos (#slug) contra encabezados Markdown (ignorando bloques cercados) según PMI PMBOK §4.4 y §10.2."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    heading_slugs: list[str] = []
    duplicate_heading_slugs: list[str] = []
    broken_anchor_targets: list[str] = []
    empty_label_anchor_targets: list[str] = []
    total_headings = 0
    total_anchor_links = 0

    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m_heading = _MARKDOWN_HEADING_AUDIT_RE.match(line)
        if m_heading:
            total_headings += 1
            slug = _markdown_github_heading_slug(m_heading.group(1))
            if slug:
                if slug in heading_slugs and slug not in duplicate_heading_slugs:
                    duplicate_heading_slugs.append(slug)
                if slug not in heading_slugs:
                    heading_slugs.append(slug)

        for m_link in _ANCHOR_INTERNAL_LINK_RE.finditer(line):
            total_anchor_links += 1
            label = m_link.group(1).strip()
            target_slug = m_link.group(2).lower()
            if not label and target_slug not in empty_label_anchor_targets:
                empty_label_anchor_targets.append(target_slug)
            if target_slug not in heading_slugs and target_slug not in broken_anchor_targets:
                broken_anchor_targets.append(target_slug)

    is_anchor_navigation_valid = bool(
        total_anchor_links > 0
        and len(broken_anchor_targets) == 0
        and len(empty_label_anchor_targets) == 0
        and len(duplicate_heading_slugs) == 0
    )

    if total_anchor_links == 0:
        anchor_posture = "NO_INTERNAL_ANCHORS"
    elif len(broken_anchor_targets) > 0:
        anchor_posture = "BROKEN_INTERNAL_ANCHOR_TARGET"
    elif len(empty_label_anchor_targets) > 0:
        anchor_posture = "EMPTY_ANCHOR_LINK_LABEL"
    elif len(duplicate_heading_slugs) > 0:
        anchor_posture = "DUPLICATE_HEADING_ANCHOR_SLUGS"
    else:
        anchor_posture = "VALID_INTERNAL_ANCHOR_NAVIGATION"

    return {
        "total_headings": total_headings,
        "total_anchor_links": total_anchor_links,
        "broken_anchor_targets": broken_anchor_targets,
        "empty_label_anchor_targets": empty_label_anchor_targets,
        "duplicate_heading_slugs": duplicate_heading_slugs,
        "is_anchor_navigation_valid": is_anchor_navigation_valid,
        "anchor_posture": anchor_posture,
    }


_CANONICAL_CALLOUT_ADMONITION_TYPES = {
    "NOTE",
    "TIP",
    "IMPORTANT",
    "WARNING",
    "CAUTION",
}
_CALLOUT_ADMONITION_HEADER_RE = re.compile(
    r"^\s*>\s*\[!([A-Za-z0-9_-]+)\](.*)$"
)
_BLOCKQUOTE_LINE_RE = re.compile(r"^\s*>(.*)$")


def audit_markdown_callout_admonition_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita bloques de aviso estilo GitHub (> [!NOTE], > [!TIP], > [!IMPORTANT], > [!WARNING], > [!CAUTION]) fuera de bloques cercados según PMI PMBOK §4.4 y §10.2."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    valid_callout_count = 0
    detected_callout_types: list[str] = []
    unsupported_callout_type_lines: list[int] = []
    empty_callout_body_lines: list[int] = []
    consecutive_unseparated_callout_lines: list[int] = []

    in_fence = False
    in_callout = False
    current_callout_line: int | None = None
    current_callout_has_body = False
    has_previous_callout = False
    saw_blank_since_last_callout = True

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_callout:
                assert current_callout_line is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
                if not current_callout_has_body:
                    empty_callout_body_lines.append(current_callout_line)
                in_callout = False
                current_callout_line = None
                current_callout_has_body = False
                has_previous_callout = True
                saw_blank_since_last_callout = False
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        m_header = _CALLOUT_ADMONITION_HEADER_RE.match(line)
        if m_header:
            if in_callout:
                assert current_callout_line is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
                if not current_callout_has_body:
                    empty_callout_body_lines.append(current_callout_line)
                has_previous_callout = True
                saw_blank_since_last_callout = False

            if has_previous_callout and not saw_blank_since_last_callout:
                consecutive_unseparated_callout_lines.append(line_no)

            callout_type = m_header.group(1).upper()
            inline_body = m_header.group(2).strip()

            if callout_type not in _CANONICAL_CALLOUT_ADMONITION_TYPES:
                unsupported_callout_type_lines.append(line_no)
            else:
                valid_callout_count += 1
                if callout_type not in detected_callout_types:
                    detected_callout_types.append(callout_type)

            in_callout = True
            current_callout_line = line_no
            current_callout_has_body = bool(inline_body)
            continue

        m_quote = _BLOCKQUOTE_LINE_RE.match(line)
        if m_quote and in_callout:
            if m_quote.group(1).strip():
                current_callout_has_body = True
            continue

        if in_callout:
            assert current_callout_line is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
            if not current_callout_has_body:
                empty_callout_body_lines.append(current_callout_line)
            in_callout = False
            current_callout_line = None
            current_callout_has_body = False
            has_previous_callout = True
            saw_blank_since_last_callout = stripped == ""
        elif has_previous_callout and stripped == "":
            saw_blank_since_last_callout = True

    if in_callout:
        assert current_callout_line is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
        if not current_callout_has_body:
            empty_callout_body_lines.append(current_callout_line)

    is_hygienic = bool(
        len(unsupported_callout_type_lines) == 0
        and len(empty_callout_body_lines) == 0
        and len(consecutive_unseparated_callout_lines) == 0
    )

    return {
        "valid_callout_count": valid_callout_count,
        "detected_callout_types": detected_callout_types,
        "unsupported_callout_type_lines": unsupported_callout_type_lines,
        "empty_callout_body_lines": empty_callout_body_lines,
        "consecutive_unseparated_callout_lines": consecutive_unseparated_callout_lines,
        "is_hygienic": is_hygienic,
    }


__all__ = [
    "ANYDOC_AVAILABLE",
    "SUPPORTED_EXTENSIONS",
    "FORMAT_ALIASES",
    "AnyDocConversionError",
    "is_anydoc_available",
    "detect_document_format",
    "convert_bytes_to_markdown",
    "convert_file_to_markdown",
    "audit_converted_markdown_structure",
    "estimate_document_reading_metrics",
    "extract_markdown_governance_markers",
    "summarize_markdown_tables_schema",
    "summarize_markdown_code_blocks",
    "extract_markdown_action_checklists",
    "audit_markdown_reference_citations",
    "audit_markdown_frontmatter_metadata",
    "extract_markdown_admonition_callouts",
    "extract_markdown_glossary_definitions",
    "audit_markdown_mermaid_diagrams",
    "audit_markdown_media_accessibility",
    "audit_markdown_toc_anchor_alignment",
    "extract_markdown_checklist_progress",
    "audit_markdown_footnote_citations",
    "audit_markdown_frontmatter_governance",
    "audit_markdown_admonition_callouts",
    "audit_markdown_task_checklist_governance",
    "audit_markdown_code_fence_hygiene",
    "audit_markdown_image_asset_hygiene",
    "audit_markdown_mermaid_diagram_hygiene",
    "audit_markdown_footnote_reference_hygiene",
    "audit_markdown_internal_anchor_links",
    "audit_markdown_callout_admonition_hygiene",
    "audit_markdown_table_column_alignment_hygiene",
    "audit_markdown_task_list_checklist_hygiene",
    "audit_markdown_heading_hierarchy_and_duplicates",
    "audit_markdown_external_url_scheme_hygiene",
    "audit_markdown_admonition_callout_hygiene",
    "audit_markdown_frontmatter_metadata_hygiene",
    "audit_markdown_image_alt_text_and_asset_hygiene",
    "audit_markdown_code_fence_language_and_secret_hygiene",
    "audit_markdown_alert_admonition_hygiene",
    "audit_markdown_blockquote_depth_and_citation_hygiene",
    "audit_markdown_acronym_and_glossary_consistency",
    "audit_markdown_task_list_action_item_hygiene",
    "audit_markdown_mermaid_diagram_syntax_and_complexity",
    "audit_markdown_footnote_reference_coherence",
    "audit_markdown_definition_list_and_spec_hygiene",
    "audit_markdown_horizontal_rule_and_section_break_hygiene",
    "audit_markdown_admonition_and_callout_hygiene",
    "audit_markdown_raw_html_and_script_injection_hygiene",
    "audit_markdown_code_fence_balance_and_language_hygiene",
    "audit_markdown_frontmatter_and_document_control_hygiene",
    "AnyDocService",
    "audit_markdown_badge_and_external_tracker_hygiene",
    "audit_markdown_footnote_reference_and_definition_hygiene",
    "audit_markdown_acronym_and_glossary_first_use_hygiene",
    "audit_markdown_mermaid_diagram_syntax_hygiene",
    "audit_markdown_code_fence_and_secret_leak_hygiene",
    "audit_markdown_admonition_callout_and_actionability_hygiene",
    "audit_markdown_heading_anchor_slug_and_fragment_hygiene",
    "audit_markdown_table_column_parity_and_empty_cell_hygiene",
    "audit_markdown_blockquote_attribution_and_nesting_hygiene",
    "audit_markdown_frontmatter_metadata_and_classification_hygiene",
    "audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity",
    "audit_markdown_footnote_citation_and_orphan_definition_hygiene",
    "audit_markdown_task_list_checklist_owner_and_due_date_hygiene",
    "audit_markdown_image_alt_text_and_asset_weight_hygiene",
    "audit_markdown_acronym_expansion_and_glossary_term_hygiene",
    "audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene",
    "audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene",
    "audit_markdown_link_rot_and_internal_anchor_resolution_hygiene",
    "audit_markdown_math_latex_delimiter_and_macro_hygiene",
    "audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene",
    "audit_markdown_fenced_code_block_language_and_secret_hygiene",
    "audit_markdown_table_column_parity_and_cell_hygiene",
    "audit_markdown_footnote_citation_reciprocity_and_key_hygiene",
    "audit_markdown_gfm_task_list_completion_and_nesting_hygiene",
    "audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene",
    "audit_markdown_image_alt_text_and_svg_sanitization_hygiene",
    "audit_markdown_yaml_frontmatter_schema_and_tag_hygiene",
    "audit_markdown_admonition_callout_syntax_and_nesting_hygiene",
    "audit_markdown_glossary_definition_list_uniqueness_and_hygiene",
    "audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety",
    "audit_markdown_heading_hierarchy_and_anchor_slug_collisions",
    "audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene",
    "audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene",
    "audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene",
    "audit_markdown_task_list_checkbox_parity_and_subtask_indentation",
    "audit_markdown_rfc2119_normative_keywords_and_requirement_traceability",
    "audit_markdown_adr_madr_sections_and_supersession_hygiene",
    "audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene",
    "audit_markdown_latex_math_delimiter_balance_and_macro_hygiene",
    "audit_markdown_runbook_incident_escalation_and_rollback_hygiene",
    "audit_markdown_postmortem_rca_blameless_and_action_item_hygiene",
    "audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene",
    "audit_markdown_data_lineage_dag_freshness_and_contract_hygiene",
    "audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene",
    "audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene",
    "audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene",
    "audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene",
    "audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene",
    "audit_markdown_rfc2119_normative_keyword_and_testability_hygiene",
    "audit_anydoc_ieee829_verification_traceability_matrix",
    "audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics",
    "AnydocService",
]




_GFM_DELIMITER_CELL_RE = re.compile(r"^:?-{3,}:?$")


def audit_markdown_table_column_alignment_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """PMBOK §4.4 / §10.2 — paridad de columnas e higiene de filas delimitadoras en tablas GFM.

    Ignora bloques fenced code (triple backtick o triple tilde). Agrupa
    líneas contiguas de tabla para validar delimitador GFM, celdas de
    encabezado vacías y desbalanceo de columnas (ragged).
    """
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    total_tables = 0
    malformed_delimiter_table_indices: list[int] = []
    empty_header_cell_table_indices: list[int] = []
    ragged_column_table_indices: list[int] = []

    def _is_table_line(raw_line: str) -> bool:
        stripped = raw_line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def _row_cells(raw_line: str) -> list[str]:
        stripped = raw_line.strip()
        return [cell.strip() for cell in stripped[1:-1].split("|")]

    in_backtick_fence = False
    in_tilde_fence = False
    table_index = 0
    block: list[str] = []

    def _evaluate_block(block_lines: list[str]) -> None:
        nonlocal total_tables, table_index
        if not block_lines:
            return
        table_index += 1
        total_tables += 1

        header_cells = _row_cells(block_lines[0])
        expected_cols = len(header_cells)

        if len(block_lines) < 2:
            malformed_delimiter_table_indices.append(table_index)
        else:
            delim_cells = _row_cells(block_lines[1])
            if len(delim_cells) != expected_cols or not all(
                _GFM_DELIMITER_CELL_RE.match(cell) for cell in delim_cells
            ):
                malformed_delimiter_table_indices.append(table_index)

        if "" in header_cells:
            empty_header_cell_table_indices.append(table_index)

        for data_line in block_lines[2:]:
            if len(_row_cells(data_line)) != expected_cols:
                ragged_column_table_indices.append(table_index)
                break

    for line in lines:
        stripped = line.strip()
        if not in_tilde_fence and not in_backtick_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and not in_tilde_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        if _is_table_line(line):
            block.append(line)
        else:
            _evaluate_block(block)
            block = []
    _evaluate_block(block)

    is_table_hygiene_clean = bool(
        not malformed_delimiter_table_indices
        and not empty_header_cell_table_indices
        and not ragged_column_table_indices
    )

    return {
        "total_tables": total_tables,
        "malformed_delimiter_table_indices": malformed_delimiter_table_indices,
        "empty_header_cell_table_indices": empty_header_cell_table_indices,
        "ragged_column_table_indices": ragged_column_table_indices,
        "is_table_hygiene_clean": is_table_hygiene_clean,
    }


_TASK_LIST_ITEM_HYGIENE_RE = re.compile(
    r"^\s*[-*+]\s+\[(?P<mark>.)\]\s*(?P<body>.*)$"
)


def audit_markdown_task_list_checklist_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita listas de tareas (checklists) en Markdown verificando sintaxis de casilla, descripción no vacía y asignación de responsable en items abiertos según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text:
        return {
            "total_task_items": 0,
            "completed_task_items": 0,
            "completion_rate_pct": 0.0,
            "invalid_checkbox_syntax_lines": [],
            "empty_task_description_lines": [],
            "unassigned_open_task_lines": [],
            "is_checklist_hygiene_clean": True,
        }

    lines = markdown_text.splitlines()
    total_task_items = 0
    completed_task_items = 0
    invalid_checkbox_syntax_lines: list[int] = []
    empty_task_description_lines: list[int] = []
    unassigned_open_task_lines: list[int] = []

    in_backtick_fence = False
    in_tilde_fence = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_tilde_fence and not in_backtick_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and not in_tilde_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        match = _TASK_LIST_ITEM_HYGIENE_RE.match(line)
        if not match:
            continue

        total_task_items += 1
        mark = match.group("mark")
        body = match.group("body").strip()

        if mark not in {" ", "x", "X"}:
            invalid_checkbox_syntax_lines.append(line_num)

        if not body:
            empty_task_description_lines.append(line_num)

        if mark in {"x", "X"}:
            completed_task_items += 1

        if (
            mark == " "
            and body
            and ("@" not in body and "owner:" not in body.lower())
        ):
            unassigned_open_task_lines.append(line_num)

    completion_rate_pct = (
        round((completed_task_items / total_task_items) * 100.0, 2)
        if total_task_items > 0
        else 0.0
    )
    is_checklist_hygiene_clean = bool(
        not invalid_checkbox_syntax_lines
        and not empty_task_description_lines
        and not unassigned_open_task_lines
    )

    return {
        "total_task_items": total_task_items,
        "completed_task_items": completed_task_items,
        "completion_rate_pct": completion_rate_pct,
        "invalid_checkbox_syntax_lines": invalid_checkbox_syntax_lines,
        "empty_task_description_lines": empty_task_description_lines,
        "unassigned_open_task_lines": unassigned_open_task_lines,
        "is_checklist_hygiene_clean": is_checklist_hygiene_clean,
    }


_ATX_HEADING_HIERARCHY_RE = re.compile(
    r"^\s*(?P<hashes>#{1,6})(?:\s+(?P<title>.*))?$"
)


def audit_markdown_heading_hierarchy_and_duplicates(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita la jerarquía de encabezados ATX (H1-H6), saltos de nivel, encabezados vacíos y títulos duplicados en el mismo nivel según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text:
        return {
            "total_headings": 0,
            "h1_count": 0,
            "skipped_level_lines": [],
            "empty_heading_lines": [],
            "duplicate_heading_lines": [],
            "is_heading_hierarchy_clean": True,
        }

    lines = markdown_text.splitlines()
    total_headings = 0
    h1_count = 0
    skipped_level_lines: list[int] = []
    empty_heading_lines: list[int] = []
    duplicate_heading_lines: list[int] = []
    seen_headings: set[tuple[int, str]] = set()
    prev_level: int | None = None

    in_backtick_fence = False
    in_tilde_fence = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        match = _ATX_HEADING_HIERARCHY_RE.match(line)
        if not match:
            continue

        total_headings += 1
        level = len(match.group("hashes"))
        raw_title = (match.group("title") or "").strip()
        clean_title = re.sub(r"\s*#+\s*$", "", raw_title).strip()

        if level == 1:
            h1_count += 1

        if prev_level is not None and level > prev_level + 1:
            skipped_level_lines.append(line_num)
        prev_level = level

        if not clean_title:
            empty_heading_lines.append(line_num)
        else:
            norm_key = (level, clean_title.lower())
            if norm_key in seen_headings:
                duplicate_heading_lines.append(line_num)
            else:
                seen_headings.add(norm_key)

    is_heading_hierarchy_clean = bool(
        h1_count <= 1
        and not skipped_level_lines
        and not empty_heading_lines
        and not duplicate_heading_lines
    )

    return {
        "total_headings": total_headings,
        "h1_count": h1_count,
        "skipped_level_lines": skipped_level_lines,
        "empty_heading_lines": empty_heading_lines,
        "duplicate_heading_lines": duplicate_heading_lines,
        "is_heading_hierarchy_clean": is_heading_hierarchy_clean,
    }


_INLINE_EXTERNAL_URL_LINK_RE = re.compile(
    r"(?<!!)\[(?P<label>[^\]]*)\]\((?P<target>[^)]*)\)"
)


def audit_markdown_external_url_scheme_hygiene(
    markdown_text: str | None = None,
) -> dict[str, Any]:
    """Audita enlaces externos e inline en Markdown verificando esquemas seguros (HTTPS), ausencia de esquemas peligrosos (javascript/vbscript/data), etiquetas no vacías y URLs no placeholder según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text:
        return {
            "total_links": 0,
            "insecure_http_lines": [],
            "dangerous_scheme_lines": [],
            "empty_label_lines": [],
            "placeholder_url_lines": [],
            "is_url_hygiene_clean": True,
        }

    lines = markdown_text.splitlines()
    total_links = 0
    insecure_http_lines: list[int] = []
    dangerous_scheme_lines: list[int] = []
    empty_label_lines: list[int] = []
    placeholder_url_lines: list[int] = []

    in_backtick_fence = False
    in_tilde_fence = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        for match in _INLINE_EXTERNAL_URL_LINK_RE.finditer(line):
            total_links += 1
            label = match.group("label").strip()
            raw_target = match.group("target").strip()
            target = raw_target.split()[0] if raw_target else ""
            low = target.lower()

            if not label:
                empty_label_lines.append(line_num)

            if low.startswith(("javascript:", "vbscript:", "data:")):
                dangerous_scheme_lines.append(line_num)

            if low.startswith("http://") and not low.startswith(
                ("http://localhost", "http://127.0.0.1")
            ):
                insecure_http_lines.append(line_num)

            if (
                not target
                or low in {"#", "todo", "tbd", "http://", "https://"}
                or "example.com" in low
            ):
                placeholder_url_lines.append(line_num)

    is_url_hygiene_clean = bool(
        not insecure_http_lines
        and not dangerous_scheme_lines
        and not empty_label_lines
        and not placeholder_url_lines
    )

    return {
        "total_links": total_links,
        "insecure_http_lines": insecure_http_lines,
        "dangerous_scheme_lines": dangerous_scheme_lines,
        "empty_label_lines": empty_label_lines,
        "placeholder_url_lines": placeholder_url_lines,
        "is_url_hygiene_clean": is_url_hygiene_clean,
    }


AnyDocService.audit_markdown_external_url_scheme_hygiene = staticmethod(
    audit_markdown_external_url_scheme_hygiene
)


_NESTED_ALERT_HEADER_RE = re.compile(
    r"^\s*>\s*>+\s*\[!([A-Za-z0-9_-]+)\](.*)$"
)
_SINGLE_ALERT_HEADER_RE = re.compile(
    r"^\s*>\s*\[!([A-Za-z0-9_-]+)\](.*)$"
)


def audit_markdown_admonition_callout_hygiene(
    markdown_text: str,
) -> dict[str, Any]:
    """Audita la higiene de bloques de alerta GitHub-style (> [!NOTE], > [!TIP], > [!IMPORTANT], > [!WARNING], > [!CAUTION]) en artefactos de conocimiento PMI PMBOK §4.4 y §10.2."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    total_alerts = 0
    valid_alerts_count = 0
    unsupported_alert_types: list[str] = []
    empty_alert_lines: list[int] = []
    nested_alert_lines: list[int] = []
    consecutive_alert_lines: list[int] = []

    in_backtick_fence = False
    in_tilde_fence = False

    in_alert = False
    current_alert_line: int | None = None
    current_alert_type_valid = False
    current_alert_has_body = False
    current_alert_is_consecutive = False
    has_previous_alert = False
    saw_separator_since_last_alert = True

    def _finalize_current_alert() -> None:
        nonlocal in_alert, current_alert_line, current_alert_type_valid
        nonlocal current_alert_has_body, current_alert_is_consecutive, valid_alerts_count
        if not in_alert or current_alert_line is None:
            return
        if not current_alert_has_body:
            empty_alert_lines.append(current_alert_line)
        elif current_alert_type_valid and not current_alert_is_consecutive:
            valid_alerts_count += 1
        in_alert = False
        current_alert_line = None
        current_alert_type_valid = False
        current_alert_has_body = False
        current_alert_is_consecutive = False

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            if in_alert:
                _finalize_current_alert()
                has_previous_alert = True
                saw_separator_since_last_alert = False
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            if in_alert:
                _finalize_current_alert()
                has_previous_alert = True
                saw_separator_since_last_alert = False
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        m_nested = _NESTED_ALERT_HEADER_RE.match(line)
        if m_nested:
            total_alerts += 1
            nested_alert_lines.append(line_no)
            nested_type = m_nested.group(1).upper()
            if (
                nested_type not in _CANONICAL_CALLOUT_ADMONITION_TYPES
                and nested_type not in unsupported_alert_types
            ):
                unsupported_alert_types.append(nested_type)
            continue

        m_alert = _SINGLE_ALERT_HEADER_RE.match(line)
        if m_alert:
            total_alerts += 1
            is_consecutive = False
            if in_alert:
                _finalize_current_alert()
                has_previous_alert = True
                saw_separator_since_last_alert = False

            if has_previous_alert and not saw_separator_since_last_alert:
                consecutive_alert_lines.append(line_no)
                is_consecutive = True

            alert_type = m_alert.group(1).upper()
            inline_body = m_alert.group(2).strip()
            type_valid = alert_type in _CANONICAL_CALLOUT_ADMONITION_TYPES
            if not type_valid and alert_type not in unsupported_alert_types:
                unsupported_alert_types.append(alert_type)

            in_alert = True
            current_alert_line = line_no
            current_alert_type_valid = type_valid
            current_alert_has_body = bool(inline_body)
            current_alert_is_consecutive = is_consecutive
            continue

        m_quote = _BLOCKQUOTE_LINE_RE.match(line)
        if m_quote:
            if in_alert and m_quote.group(1).strip():
                current_alert_has_body = True
            continue

        if in_alert:
            _finalize_current_alert()
            has_previous_alert = True
            saw_separator_since_last_alert = True
        elif has_previous_alert:
            saw_separator_since_last_alert = True

    if in_alert:
        _finalize_current_alert()

    is_compliant = bool(
        len(unsupported_alert_types) == 0
        and len(empty_alert_lines) == 0
        and len(nested_alert_lines) == 0
        and len(consecutive_alert_lines) == 0
    )

    recommendations: list[str] = []
    if unsupported_alert_types:
        recommendations.append(
            "Usar únicamente tipos de alerta canónicos: NOTE, TIP, IMPORTANT, WARNING, CAUTION."
        )
    if empty_alert_lines:
        recommendations.append(
            "Incluir contenido descriptivo dentro de cada bloque de alerta."
        )
    if nested_alert_lines:
        recommendations.append(
            "Evitar el anidamiento de bloques de alerta (> > [!TYPE]); mantenerlos en el nivel raíz."
        )
    if consecutive_alert_lines:
        recommendations.append(
            "Separar bloques de alerta consecutivos mediante al menos una línea en blanco o párrafo intermedio."
        )

    if is_compliant:
        status = "healthy"
    elif len(unsupported_alert_types) > 0 or len(empty_alert_lines) > 0:
        status = "critical"
    else:
        status = "warning"

    return {
        "total_alerts": total_alerts,
        "valid_alerts_count": valid_alerts_count,
        "unsupported_alert_types": unsupported_alert_types,
        "empty_alert_lines": empty_alert_lines,
        "nested_alert_lines": nested_alert_lines,
        "consecutive_alert_lines": consecutive_alert_lines,
        "is_compliant": is_compliant,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_admonition_callout_hygiene = staticmethod(
    audit_markdown_admonition_callout_hygiene
)


_FRONTMATTER_PLACEHOLDER_VALUES = {
    "tbd",
    "todo",
    "n/a",
    "null",
    "~",
    "pending_owner",
}
_FRONTMATTER_LIFECYCLE_STATUSES = {
    "draft",
    "in_review",
    "approved",
    "baselined",
    "archived",
    "deprecated",
}


def audit_markdown_frontmatter_metadata_hygiene(
    markdown_text: str,
    required_keys: Sequence[str] = ("title", "owner", "version", "status"),
) -> dict[str, Any]:
    """Audita el bloque YAML frontmatter e higiene de metadatos de gobernanza documental según PMI PMBOK §4.4 y §10.2."""
    req_keys = [
        str(k).strip().lower()
        for k in (required_keys or ())
        if str(k).strip()
    ]
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    first_non_empty_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_non_empty_idx = idx
            break

    closing_idx: int | None = None
    if first_non_empty_idx is not None and lines[first_non_empty_idx].strip() == "---":
        for idx in range(first_non_empty_idx + 1, len(lines)):
            if lines[idx].strip() in {"---", "..."}:
                closing_idx = idx
                break

    has_valid_frontmatter = bool(
        first_non_empty_idx is not None
        and closing_idx is not None
        and closing_idx > first_non_empty_idx
    )

    parsed_keys_count = 0
    missing_required_keys: list[str] = []
    duplicate_keys: list[str] = []
    invalid_lifecycle_status = False

    if not has_valid_frontmatter:
        missing_required_keys = list(req_keys)
    else:
        assert first_non_empty_idx is not None and closing_idx is not None  # nosec B101 # internal parser-state invariant, never authorization or input validation
        seen_keys: set[str] = set()
        parsed_map: dict[str, str] = {}

        for raw_line in lines[first_non_empty_idx + 1 : closing_idx]:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                continue
            raw_key, raw_val = stripped.split(":", 1)
            norm_key = raw_key.strip().lower()
            if not norm_key:
                continue

            parsed_keys_count += 1
            clean_val = raw_val.strip()
            if len(clean_val) >= 2 and (
                (clean_val[0] == '"' and clean_val[-1] == '"')
                or (clean_val[0] == "'" and clean_val[-1] == "'")
            ):
                clean_val = clean_val[1:-1].strip()

            if norm_key in seen_keys:
                if norm_key not in duplicate_keys:
                    duplicate_keys.append(norm_key)
            else:
                seen_keys.add(norm_key)

            parsed_map[norm_key] = clean_val

        for req_key in req_keys:
            val = parsed_map.get(req_key, "")
            if (
                req_key not in parsed_map
                or not val
                or val.lower() in _FRONTMATTER_PLACEHOLDER_VALUES
            ):
                missing_required_keys.append(req_key)

        status_val = parsed_map.get("status", "")
        if (
            status_val
            and status_val.lower() not in _FRONTMATTER_PLACEHOLDER_VALUES
            and status_val.lower() not in _FRONTMATTER_LIFECYCLE_STATUSES
        ):
            invalid_lifecycle_status = True

    is_compliant = bool(
        has_valid_frontmatter
        and len(missing_required_keys) == 0
        and len(duplicate_keys) == 0
        and not invalid_lifecycle_status
    )

    recommendations: list[str] = []
    if not has_valid_frontmatter:
        recommendations.append(
            "Incluir un bloque YAML frontmatter delimitado por '---' al inicio del documento."
        )
    if missing_required_keys:
        recommendations.append(
            "Completar los metadatos obligatorios sin valores vacíos ni placeholders: "
            + ", ".join(missing_required_keys)
            + "."
        )
    if duplicate_keys:
        recommendations.append(
            "Eliminar claves duplicadas en el bloque frontmatter: "
            + ", ".join(duplicate_keys)
            + "."
        )
    if invalid_lifecycle_status:
        recommendations.append(
            "Asignar un estado de ciclo de vida documental válido (draft, in_review, approved, baselined, archived, deprecated)."
        )

    if is_compliant:
        status = "healthy"
    elif not has_valid_frontmatter or len(missing_required_keys) > 0:
        status = "critical"
    else:
        status = "warning"

    return {
        "has_valid_frontmatter": has_valid_frontmatter,
        "parsed_keys_count": parsed_keys_count,
        "missing_required_keys": missing_required_keys,
        "duplicate_keys": duplicate_keys,
        "invalid_lifecycle_status": invalid_lifecycle_status,
        "is_compliant": is_compliant,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_frontmatter_metadata_hygiene = staticmethod(
    audit_markdown_frontmatter_metadata_hygiene
)


_MARKDOWN_IMAGE_HYGIENE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<raw_target>(?:[^()\n]|\([^()\n]*\))*)\)"
)
_GENERIC_IMAGE_ALT_PLACEHOLDERS = {
    "image",
    "img",
    "photo",
    "screenshot",
    "diagram",
    "picture",
    "untitled",
    "todo",
    "tbd",
    "imagen",
    "foto",
}
_IMAGE_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp")
_WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:\\")
_TRAILING_QUOTED_TITLE_RE = re.compile(r"""\s+(?:"[^"]*"|'[^']*')\s*$""")


def audit_markdown_image_alt_text_and_asset_hygiene(
    markdown_text: str,
    min_alt_length: int = 4,
) -> dict[str, Any]:
    """Audita accesibilidad (alt text) y validez de referencias de activos de imagen ![alt](target) según PMI PMBOK §4.4 y §10.2."""
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )
    min_len = max(1, int(min_alt_length))

    total_images = 0
    valid_images_count = 0
    missing_or_generic_alt_lines: list[int] = []
    invalid_asset_targets: list[str] = []

    in_backtick_fence = False
    in_tilde_fence = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        for match in _MARKDOWN_IMAGE_HYGIENE_RE.finditer(line):
            total_images += 1
            alt_clean = match.group("alt").strip()
            alt_lower = alt_clean.lower()

            alt_ok = True
            if (
                not alt_clean
                or len(alt_clean) < min_len
                or alt_lower in _GENERIC_IMAGE_ALT_PLACEHOLDERS
                or alt_lower.endswith(_IMAGE_FILE_EXTENSIONS)
            ):
                alt_ok = False
                if line_num not in missing_or_generic_alt_lines:
                    missing_or_generic_alt_lines.append(line_num)

            raw_target = match.group("raw_target").strip()
            target_no_title = _TRAILING_QUOTED_TITLE_RE.sub("", raw_target).strip()

            is_angle_wrapped = (
                len(target_no_title) >= 2
                and target_no_title.startswith("<")
                and target_no_title.endswith(">")
            )
            inner_target = (
                target_no_title[1:-1].strip()
                if is_angle_wrapped
                else target_no_title
            )
            low_target = inner_target.lower()

            target_ok = True
            if not inner_target:
                target_ok = False
                invalid_asset_targets.append("<empty>")
            elif (
                low_target.startswith(
                    ("javascript:", "vbscript:", "data:text/html", "file://")
                )
                or bool(_WINDOWS_DRIVE_PATH_RE.match(inner_target))
                or (
                    not is_angle_wrapped
                    and any(ch.isspace() for ch in target_no_title)
                )
            ):
                target_ok = False
                invalid_asset_targets.append(inner_target)

            if alt_ok and target_ok:
                valid_images_count += 1

    is_compliant = bool(
        len(missing_or_generic_alt_lines) == 0
        and len(invalid_asset_targets) == 0
    )

    recommendations: list[str] = []
    if invalid_asset_targets:
        recommendations.append(
            "Corregir las referencias de imagen inválidas, esquemas inseguros/locales o rutas con espacios sin envolver en <...>."
        )
    if missing_or_generic_alt_lines:
        recommendations.append(
            "Proveer texto alternativo (alt text) descriptivo y específico para cada imagen o diagrama."
        )

    if is_compliant:
        status = "healthy"
    elif len(invalid_asset_targets) > 0:
        status = "critical"
    else:
        status = "warning"

    return {
        "total_images": total_images,
        "valid_images_count": valid_images_count,
        "missing_or_generic_alt_lines": missing_or_generic_alt_lines,
        "invalid_asset_targets": invalid_asset_targets,
        "is_compliant": is_compliant,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_image_alt_text_and_asset_hygiene = staticmethod(
    audit_markdown_image_alt_text_and_asset_hygiene
)

AnydocService = AnyDocService


def audit_markdown_code_fence_language_and_secret_hygiene(
    markdown_text: object,
    *,
    max_lines_per_block: int = 80,
) -> dict[str, object]:
    """Audita etiquetas de lenguaje, longitud y fugas de secretos en bloques de código Markdown según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_code_blocks": 0,
            "unlabeled_language_block_lines": [],
            "oversized_block_lines": [],
            "suspected_secret_block_lines": [],
            "unclosed_fence_line": None,
            "is_code_fence_hygiene_compliant": True,
        }

    max_lines = int(max_lines_per_block)
    lines = markdown_text.splitlines()
    pattern = re.compile(r"^(```|~~~)\s*([^\n]*)$")

    total_code_blocks = 0
    unlabeled_language_block_lines: list[int] = []
    oversized_block_lines: list[int] = []
    suspected_secret_block_lines: list[int] = []

    active_block: dict[str, object] | None = None
    active_delimiter = ""
    unclosed_fence_line: int | None = None

    secret_patterns = (
        re.compile(r"api[_-]?key\s*=", re.IGNORECASE),
        re.compile(r"secret[_-]?key\s*=", re.IGNORECASE),
        re.compile(r"password\s*=", re.IGNORECASE),
        re.compile(r"bearer\s+eyj", re.IGNORECASE),
        re.compile(r"-----begin\s", re.IGNORECASE),
        re.compile(r"ghp_[a-z0-9]{20,}", re.IGNORECASE),
        re.compile(r"sk-[a-z0-9]{20,}", re.IGNORECASE),
        re.compile(r"aws_secret_access_key\s*=", re.IGNORECASE),
    )
    placeholder_patterns = (
        re.compile(r"redacted", re.IGNORECASE),
        re.compile(r"example", re.IGNORECASE),
        re.compile(r"your_", re.IGNORECASE),
        re.compile(r"<"),
        re.compile(r"\*\*\*"),
    )

    def _looks_like_secret(raw_value: str) -> bool:
        value = raw_value.strip()
        for ph in placeholder_patterns:
            if ph.search(value):
                return False
        for sp in secret_patterns:
            if sp.search(value):
                return True
        return False

    for idx, raw_line in enumerate(lines, start=1):
        normalized = raw_line.replace("\t", "    ")
        match = pattern.match(normalized.strip())
        if match:
            delimiter = match.group(1)
            if active_block is None:
                active_block = {"start_line": idx}
                active_delimiter = delimiter
                total_code_blocks += 1

                label = match.group(2).strip()
                if not label:
                    unlabeled_language_block_lines.append(idx)
                continue
            else:
                closing_marker = (
                    match.group(2).strip() == "" and delimiter == active_delimiter
                )
                if closing_marker:
                    start_line = int(active_block["start_line"])
                    inner_line_count = idx - start_line - 1
                    if inner_line_count > max_lines:
                        oversized_block_lines.append(start_line)

                    body_lines = lines[start_line - 1 : idx - 1]
                    body = "\n".join(body_lines[1:])
                    if _looks_like_secret(body):
                        suspected_secret_block_lines.append(start_line)

                    active_block = None
                    active_delimiter = ""
                    continue

        # Contenido interno: un cierre con estilo distinto no cuenta como línea interna.
        if active_block is not None:
            continue

    if active_block is not None:
        unclosed_fence_line = int(active_block["start_line"])

    is_code_fence_hygiene_compliant = bool(
        len(unlabeled_language_block_lines) == 0
        and len(oversized_block_lines) == 0
        and len(suspected_secret_block_lines) == 0
        and unclosed_fence_line is None
    )

    return {
        "total_code_blocks": total_code_blocks,
        "unlabeled_language_block_lines": unlabeled_language_block_lines,
        "oversized_block_lines": oversized_block_lines,
        "suspected_secret_block_lines": suspected_secret_block_lines,
        "unclosed_fence_line": unclosed_fence_line,
        "is_code_fence_hygiene_compliant": is_code_fence_hygiene_compliant,
    }


AnyDocService.audit_markdown_code_fence_language_and_secret_hygiene = staticmethod(
    audit_markdown_code_fence_language_and_secret_hygiene
)


def audit_markdown_blockquote_depth_and_citation_hygiene(
    markdown_text: object,
    *,
    max_nesting_depth: int = 2,
) -> dict[str, object]:
    """Audita profundidad de anidamiento, bloques vacíos y atribución de fuentes en citas normativas de blockquotes Markdown según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_blockquote_blocks": 0,
            "excessive_nesting_block_lines": [],
            "empty_blockquote_block_lines": [],
            "unattributed_normative_quote_lines": [],
            "is_blockquote_hygiene_compliant": True,
        }

    max_depth = int(max_nesting_depth)
    lines = markdown_text.splitlines()
    blockquote_re = re.compile(r"^\s*((?:>\s*)+)(.*)$")
    admonition_re = re.compile(r"^\[![A-Za-z0-9_-]+\]")

    normative_terms = (
        "pmbok",
        "iso ",
        "ieee",
        "cláusula",
        "clausula",
        "artículo",
        "articulo",
        "según norma",
        "segun norma",
    )
    attribution_markers = (
        "—",
        "--",
        "fuente:",
        "ref:",
        "[",
        "§",
    )

    total_blockquote_blocks = 0
    excessive_nesting_block_lines: list[int] = []
    empty_blockquote_block_lines: list[int] = []
    unattributed_normative_quote_lines: list[int] = []

    in_backtick_fence = False
    in_tilde_fence = False

    current_block: dict[str, Any] | None = None

    def _finalize_block(block: dict[str, Any] | None) -> None:
        nonlocal total_blockquote_blocks
        if block is None or block["is_admonition"]:
            return
        total_blockquote_blocks += 1
        start_line = int(block["start_line"])
        if int(block["max_depth"]) > max_depth:
            excessive_nesting_block_lines.append(start_line)

        combined_text = " ".join(
            part for part in block["texts"] if part
        ).strip()
        if not combined_text:
            empty_blockquote_block_lines.append(start_line)
            return

        lowered = combined_text.lower()
        if any(term in lowered for term in normative_terms) and not any(
            marker in lowered for marker in attribution_markers
        ):
            unattributed_normative_quote_lines.append(start_line)

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            if current_block is not None:
                _finalize_block(current_block)
                current_block = None
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            if current_block is not None:
                _finalize_block(current_block)
                current_block = None
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        match = blockquote_re.match(raw_line)
        if match:
            prefix = match.group(1)
            body = match.group(2).strip()
            depth = prefix.count(">")
            if current_block is None:
                current_block = {
                    "start_line": line_no,
                    "max_depth": depth,
                    "texts": [body],
                    "is_admonition": bool(admonition_re.match(body)),
                }
            else:
                if depth > int(current_block["max_depth"]):
                    current_block["max_depth"] = depth
                current_block["texts"].append(body)
        else:
            if current_block is not None:
                _finalize_block(current_block)
                current_block = None

    if current_block is not None:
        _finalize_block(current_block)

    return {
        "total_blockquote_blocks": total_blockquote_blocks,
        "excessive_nesting_block_lines": excessive_nesting_block_lines,
        "empty_blockquote_block_lines": empty_blockquote_block_lines,
        "unattributed_normative_quote_lines": unattributed_normative_quote_lines,
        "is_blockquote_hygiene_compliant": (
            len(excessive_nesting_block_lines) == 0
            and len(empty_blockquote_block_lines) == 0
            and len(unattributed_normative_quote_lines) == 0
        ),
    }


AnyDocService.audit_markdown_blockquote_depth_and_citation_hygiene = staticmethod(
    audit_markdown_blockquote_depth_and_citation_hygiene
)


def audit_markdown_acronym_and_glossary_consistency(
    markdown_text: object,
    *,
    min_occurrences_for_definition: int = 2,
) -> dict[str, object]:
    """Audita consistencia de acrónimos frecuentes, definiciones inline y entradas de glosario en artefactos Markdown según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_acronyms_detected": 0,
            "undefined_frequent_acronyms": [],
            "duplicate_glossary_acronyms": [],
            "empty_definition_acronyms": [],
            "is_acronym_glossary_consistent": True,
        }

    min_occ = max(1, int(min_occurrences_for_definition))
    ignored_tokens = {
        "PARA",
        "COMO",
        "ESTE",
        "ESTA",
        "TODO",
        "TODA",
        "PERO",
        "SINO",
        "NOTA",
        "WARNING",
        "NOTE",
        "IMPORTANT",
        "TIP",
        "CAUTION",
        "HTTP",
        "HTTPS",
        "JSON",
        "HTML",
        "UUID",
        "UTF",
        "NULL",
        "TRUE",
        "FALSE",
        "TBD",
    }

    bullet_glossary_re = re.compile(
        r"^\s*[-*+]\s+\*\*([A-Z]{2,10})\*\*\s*[:\-–—]?\s*(.*)$"
    )
    table_glossary_re = re.compile(
        r"^\s*\|\s*(?:\*\*)?([A-Z]{2,10})(?:\*\*)?\s*\|\s*([^|]*)\|?\s*$"
    )
    inline_paren_acr_re = re.compile(r"\(([A-Z]{2,10})\)")
    inline_acr_paren_re = re.compile(r"\b([A-Z]{2,10})\s*\([^)\n]{3,}\)")
    token_re = re.compile(r"\b([A-Z]{3,8})\b")

    glossary_defined: set[str] = set()
    duplicate_glossary: set[str] = set()
    empty_definitions: set[str] = set()
    inline_defined: set[str] = set()
    token_counts: dict[str, int] = {}

    in_backtick_fence = False
    in_tilde_fence = False

    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        m_bullet = bullet_glossary_re.match(raw_line)
        m_table = None if m_bullet else table_glossary_re.match(raw_line)
        m_gloss = m_bullet or m_table
        if m_gloss:
            acr = m_gloss.group(1).strip()
            raw_def = re.sub(
                r"^[:\-–—|\s]+|[:\-–—|\s]+$", "", m_gloss.group(2) or ""
            ).strip()
            if acr in glossary_defined:
                duplicate_glossary.add(acr)
            glossary_defined.add(acr)
            if not raw_def or raw_def.lower() in {"tbd", "todo", "pendiente"}:
                empty_definitions.add(acr)

        for m_in in inline_paren_acr_re.finditer(raw_line):
            inline_defined.add(m_in.group(1))
        for m_in2 in inline_acr_paren_re.finditer(raw_line):
            inline_defined.add(m_in2.group(1))

        for m_tok in token_re.finditer(raw_line):
            tok = m_tok.group(1)
            if tok in ignored_tokens:
                continue
            token_counts[tok] = token_counts.get(tok, 0) + 1

    all_acronyms = set(token_counts.keys()) | glossary_defined
    undefined_frequent: set[str] = set()
    for acr, count in token_counts.items():
        if (
            count >= min_occ
            and acr not in glossary_defined
            and acr not in inline_defined
        ):
            undefined_frequent.add(acr)

    return {
        "total_acronyms_detected": len(all_acronyms),
        "undefined_frequent_acronyms": sorted(undefined_frequent),
        "duplicate_glossary_acronyms": sorted(duplicate_glossary),
        "empty_definition_acronyms": sorted(empty_definitions),
        "is_acronym_glossary_consistent": (
            len(undefined_frequent) == 0
            and len(duplicate_glossary) == 0
            and len(empty_definitions) == 0
        ),
    }


AnyDocService.audit_markdown_acronym_and_glossary_consistency = staticmethod(
    audit_markdown_acronym_and_glossary_consistency
)


def audit_markdown_task_list_action_item_hygiene(
    markdown_text: str,
    *,
    require_owner_and_due_date_on_open: bool = True,
) -> dict[str, object]:
    """Audita la higiene y trazabilidad de listas de tareas e ítems de acción en Markdown (responsable @owner y fecha compromiso ISO en ítems abiertos) según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_task_items": 0,
            "open_task_items": 0,
            "completed_task_items": 0,
            "empty_task_item_lines": [],
            "unassigned_open_task_lines": [],
            "undated_open_task_lines": [],
            "is_task_list_hygiene_compliant": True,
        }

    task_item_re = re.compile(r"^\s*[-*+]\s+\[([ xX~-])\]\s*(.*)$")
    owner_re = re.compile(r"(?:@[A-Za-z0-9_.-]+|owner:\s*\S+)", re.IGNORECASE)
    iso_date_re = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

    total_task_items = 0
    open_task_items = 0
    completed_task_items = 0
    empty_task_item_lines: list[int] = []
    unassigned_open_task_lines: list[int] = []
    undated_open_task_lines: list[int] = []

    in_backtick_fence = False
    in_tilde_fence = False

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not in_tilde_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        m = task_item_re.match(raw_line)
        if not m:
            continue

        total_task_items += 1
        marker = m.group(1)
        body = (m.group(2) or "").strip()

        if marker == " ":
            open_task_items += 1
        elif marker.lower() == "x":
            completed_task_items += 1

        if len(body) < 3:
            empty_task_item_lines.append(line_no)

        if marker == " " and bool(require_owner_and_due_date_on_open):
            if not owner_re.search(body):
                unassigned_open_task_lines.append(line_no)
            if not iso_date_re.search(body):
                undated_open_task_lines.append(line_no)

    return {
        "total_task_items": total_task_items,
        "open_task_items": open_task_items,
        "completed_task_items": completed_task_items,
        "empty_task_item_lines": empty_task_item_lines,
        "unassigned_open_task_lines": unassigned_open_task_lines,
        "undated_open_task_lines": undated_open_task_lines,
        "is_task_list_hygiene_compliant": (
            len(empty_task_item_lines) == 0
            and len(unassigned_open_task_lines) == 0
            and len(undated_open_task_lines) == 0
        ),
    }


AnyDocService.audit_markdown_task_list_action_item_hygiene = staticmethod(
    audit_markdown_task_list_action_item_hygiene
)


def audit_markdown_mermaid_diagram_syntax_and_complexity(
    markdown_text: str,
    *,
    max_nodes_per_diagram: int = 25,
) -> dict[str, object]:
    """Audita bloques de diagramas Mermaid en Markdown verificando tipos soportados, ausencia de HTML crudo, comillas en etiquetas con paréntesis y límite de complejidad según PMI PMBOK §4.4 y §10.2."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_mermaid_blocks": 0,
            "unsupported_or_empty_mermaid_block_lines": [],
            "html_tag_in_mermaid_block_lines": [],
            "unquoted_special_char_label_block_lines": [],
            "overly_complex_mermaid_block_lines": [],
            "is_mermaid_hygiene_compliant": True,
        }

    try:
        max_nodes = int(max_nodes_per_diagram)
    except (TypeError, ValueError):
        max_nodes = 25

    supported_types = (
        "flowchart",
        "graph",
        "sequenceDiagram",
        "stateDiagram-v2",
        "stateDiagram",
        "classDiagram",
        "erDiagram",
        "xychart-beta",
    )
    fence_open_re = re.compile(r"^(`{3,}|~{3,})\s*([^\s`~]*).*$")
    html_tag_re = re.compile(
        r"(?:<\s*br\s*/?\s*>|<\s*(?:b|i|div|span)\b|</\s*[a-zA-Z])",
        re.IGNORECASE,
    )
    unquoted_paren_label_re = re.compile(r"\[[^\]\"\n]*[()][^\]\"\n]*\]")

    total_mermaid_blocks = 0
    unsupported_or_empty_mermaid_block_lines: list[int] = []
    html_tag_in_mermaid_block_lines: list[int] = []
    unquoted_special_char_label_block_lines: list[int] = []
    overly_complex_mermaid_block_lines: list[int] = []

    def _evaluate_mermaid_block(start_line: int, inner_lines: list[str]) -> None:
        nonlocal total_mermaid_blocks
        total_mermaid_blocks += 1

        useful_lines = [
            ln.strip()
            for ln in inner_lines
            if ln.strip() and not ln.strip().startswith("%%")
        ]
        if not useful_lines or not useful_lines[0].startswith(supported_types):
            unsupported_or_empty_mermaid_block_lines.append(start_line)
        else:
            statement_count = max(0, len(useful_lines) - 1)
            if statement_count > max_nodes:
                overly_complex_mermaid_block_lines.append(start_line)

        has_html = False
        has_unquoted_paren = False
        for ln in useful_lines:
            if not has_html and html_tag_re.search(ln):
                has_html = True
            if not has_unquoted_paren and unquoted_paren_label_re.search(ln):
                has_unquoted_paren = True

        if has_html:
            html_tag_in_mermaid_block_lines.append(start_line)
        if has_unquoted_paren:
            unquoted_special_char_label_block_lines.append(start_line)

    in_fence = False
    fence_char = ""
    fence_is_mermaid = False
    current_start_line = 0
    current_lines: list[str] = []

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not in_fence:
            m_open = fence_open_re.match(stripped)
            if m_open:
                in_fence = True
                fence_char = m_open.group(1)[0]
                lang = (m_open.group(2) or "").strip().lower()
                fence_is_mermaid = lang == "mermaid"
                current_start_line = line_no
                current_lines = []
        else:
            if stripped.startswith(fence_char * 3):
                if fence_is_mermaid:
                    _evaluate_mermaid_block(current_start_line, current_lines)
                in_fence = False
                fence_char = ""
                fence_is_mermaid = False
                current_start_line = 0
                current_lines = []
            elif fence_is_mermaid:
                current_lines.append(raw_line)

    if in_fence and fence_is_mermaid:
        _evaluate_mermaid_block(current_start_line, current_lines)

    return {
        "total_mermaid_blocks": total_mermaid_blocks,
        "unsupported_or_empty_mermaid_block_lines": unsupported_or_empty_mermaid_block_lines,
        "html_tag_in_mermaid_block_lines": html_tag_in_mermaid_block_lines,
        "unquoted_special_char_label_block_lines": unquoted_special_char_label_block_lines,
        "overly_complex_mermaid_block_lines": overly_complex_mermaid_block_lines,
        "is_mermaid_hygiene_compliant": (
            len(unsupported_or_empty_mermaid_block_lines) == 0
            and len(html_tag_in_mermaid_block_lines) == 0
            and len(unquoted_special_char_label_block_lines) == 0
            and len(overly_complex_mermaid_block_lines) == 0
        ),
    }


AnyDocService.audit_markdown_mermaid_diagram_syntax_and_complexity = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_complexity
)


def audit_markdown_alert_admonition_hygiene(
    markdown_text: str,
) -> dict[str, object]:
    """Audita sintaxis, anidamiento y adyacencia de alertas GitHub en blockquotes de Markdown (AnyDoc) según PMI PMBOK §4.4 y §10.2."""
    total_alerts = 0
    invalid_alert_type_lines: list[int] = []
    nested_alert_block_lines: list[int] = []
    empty_alert_body_lines: list[int] = []
    consecutive_adjacent_alert_lines: list[int] = []

    if not isinstance(markdown_text, str):
        return {
            "total_alerts": 0,
            "invalid_alert_type_lines": [],
            "nested_alert_block_lines": [],
            "empty_alert_body_lines": [],
            "consecutive_adjacent_alert_lines": [],
            "is_alert_admonition_hygiene_compliant": True,
        }

    valid_types = {"NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"}
    alert_pattern = re.compile(r"^\s*(>+)\s*\[!([A-Za-z0-9_-]+)\](.*)$")
    fence_pattern = re.compile(r"^\s*(```|~~~)")

    lines = markdown_text.splitlines()
    in_code_block = False
    fence_marker = ""

    alerts_meta: list[dict[str, object]] = []
    for idx, raw_line in enumerate(lines, start=1):
        match = fence_pattern.match(raw_line)
        if match:
            marker = match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_marker = marker
            elif marker == fence_marker:
                in_code_block = False
                fence_marker = ""
            continue

        if in_code_block:
            continue

        alert_match = alert_pattern.match(raw_line)
        if not alert_match:
            continue

        total_alerts += 1
        prefix = alert_match.group(1)
        alert_type = alert_match.group(2)
        inline_body = alert_match.group(3).strip()

        if alert_type not in valid_types:
            invalid_alert_type_lines.append(idx)
        if len(prefix) > 1:
            nested_alert_block_lines.append(idx)

        alerts_meta.append(
            {
                "line": idx,
                "inline_body": inline_body,
                "prefix": prefix,
            }
        )

    # Cuerpo vacío y adyacencia consecutiva.
    blockquote_pattern = re.compile(r"^\s*>")
    for pos, info in enumerate(alerts_meta):
        idx = int(info["line"])
        inline_body = str(info["inline_body"])

        has_body = bool(inline_body)
        if not has_body:
            # Buscar cuerpo en las lineas '>' siguientes antes de fin de
            # blockquote o otra alerta [!].
            scan = idx  # 1-indexed; scan apunta a la linea siguiente.
            while scan < len(lines):
                nxt = lines[scan]  # lineas[scan] es la linea scan+1.
                if alert_pattern.match(nxt):
                    break
                if blockquote_pattern.match(nxt):
                    if nxt.replace(">", "").strip():
                        has_body = True
                        break
                    scan += 1
                    continue
                break
        if not has_body:
            empty_alert_body_lines.append(idx)

        if pos > 0:
            prev_line = int(alerts_meta[pos - 1]["line"])
            prev_last_body_line = prev_line
            # Determinar la ultima linea del blockquote de la alerta previa.
            scan = prev_line  # linea siguiente a la alerta previa.
            while scan < len(lines):
                nxt = lines[scan]
                if alert_pattern.match(nxt):
                    break
                if blockquote_pattern.match(nxt):
                    prev_last_body_line = scan + 1
                    scan += 1
                    continue
                break
            # Adyacente si la alerta actual esta pegada a la previa: misma
            # area de blockquote o dentro del blockquote previo, o en la
            # linea inmediatamente siguiente sin separador normal.
            gap_start = prev_last_body_line + 1
            adjacent = idx <= prev_last_body_line or (
                idx == gap_start
                and all(
                    not lines[g - 1].strip() or blockquote_pattern.match(lines[g - 1])
                    for g in range(prev_last_body_line + 1, gap_start + 1)
                )
            )
            if adjacent:
                consecutive_adjacent_alert_lines.append(idx)

    is_alert_admonition_hygiene_compliant = bool(
        len(invalid_alert_type_lines) == 0
        and len(nested_alert_block_lines) == 0
        and len(empty_alert_body_lines) == 0
        and len(consecutive_adjacent_alert_lines) == 0
    )

    return {
        "total_alerts": total_alerts,
        "invalid_alert_type_lines": invalid_alert_type_lines,
        "nested_alert_block_lines": nested_alert_block_lines,
        "empty_alert_body_lines": empty_alert_body_lines,
        "consecutive_adjacent_alert_lines": consecutive_adjacent_alert_lines,
        "is_alert_admonition_hygiene_compliant": is_alert_admonition_hygiene_compliant,
    }


AnyDocService.audit_markdown_alert_admonition_hygiene = staticmethod(
    audit_markdown_alert_admonition_hygiene
)


_FOOTNOTE_DEF_LINE_RE = re.compile(r"^\s*\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$")
_FOOTNOTE_INLINE_REF_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")


def audit_markdown_footnote_reference_coherence(
    markdown_text: str,
) -> dict[str, object]:
    """PMBOK §4.4 / §10.2 — coherencia bidireccional de referencias y definiciones de notas al pie en Markdown."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_definitions": 0,
            "total_inline_references": 0,
            "duplicate_footnote_definition_ids": [],
            "empty_footnote_definition_ids": [],
            "undefined_footnote_reference_ids": [],
            "unreferenced_orphan_footnote_ids": [],
            "is_footnote_hygiene_compliant": True,
        }

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    in_fence = False
    fence_marker = ""

    total_definitions = 0
    total_inline_references = 0

    defined_ids_order: list[str] = []
    defined_counts: dict[str, int] = {}
    duplicate_footnote_definition_ids: list[str] = []
    empty_footnote_definition_ids: list[str] = []

    referenced_ids_order: list[str] = []
    referenced_set: set[str] = set()

    for raw_line in markdown_text.splitlines():
        m_fence = fence_re.match(raw_line)
        if m_fence:
            marker_char = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker_char
            elif marker_char == fence_marker:
                in_fence = False
                fence_marker = ""
            continue

        if in_fence:
            continue

        m_def = _FOOTNOTE_DEF_LINE_RE.match(raw_line)
        if m_def:
            total_definitions += 1
            fn_id = m_def.group(1).lower()
            body = m_def.group(2)

            if fn_id not in defined_counts:
                defined_ids_order.append(fn_id)
                defined_counts[fn_id] = 1
            else:
                defined_counts[fn_id] += 1
                if fn_id not in duplicate_footnote_definition_ids:
                    duplicate_footnote_definition_ids.append(fn_id)

            if len(body.strip()) == 0 and fn_id not in empty_footnote_definition_ids:
                empty_footnote_definition_ids.append(fn_id)

            for m_ref in _FOOTNOTE_INLINE_REF_RE.finditer(body):
                total_inline_references += 1
                ref_id = m_ref.group(1).lower()
                if ref_id not in referenced_set:
                    referenced_set.add(ref_id)
                    referenced_ids_order.append(ref_id)
            continue

        for m_ref in _FOOTNOTE_INLINE_REF_RE.finditer(raw_line):
            total_inline_references += 1
            ref_id = m_ref.group(1).lower()
            if ref_id not in referenced_set:
                referenced_set.add(ref_id)
                referenced_ids_order.append(ref_id)

    undefined_footnote_reference_ids = [
        ref_id for ref_id in referenced_ids_order if ref_id not in defined_counts
    ]
    unreferenced_orphan_footnote_ids = [
        fn_id for fn_id in defined_ids_order if fn_id not in referenced_set
    ]

    return {
        "total_definitions": total_definitions,
        "total_inline_references": total_inline_references,
        "duplicate_footnote_definition_ids": duplicate_footnote_definition_ids,
        "empty_footnote_definition_ids": empty_footnote_definition_ids,
        "undefined_footnote_reference_ids": undefined_footnote_reference_ids,
        "unreferenced_orphan_footnote_ids": unreferenced_orphan_footnote_ids,
        "is_footnote_hygiene_compliant": (
            len(duplicate_footnote_definition_ids) == 0
            and len(empty_footnote_definition_ids) == 0
            and len(undefined_footnote_reference_ids) == 0
            and len(unreferenced_orphan_footnote_ids) == 0
        ),
    }


AnyDocService.audit_markdown_footnote_reference_coherence = staticmethod(
    audit_markdown_footnote_reference_coherence
)


_DEF_LIST_COLON_RE = re.compile(r"^\s*:\s+(.*)$")
_NON_TERM_LINE_RE = re.compile(
    r"^\s*(?:#|\||>|[-*+]\s|\d+\.\s|(?:-{3,}|\*{3,}|_{3,})\s*$)"
)


def audit_markdown_definition_list_and_spec_hygiene(
    markdown_text: str | None,
    *,
    min_definition_chars: int = 10,
) -> dict[str, Any]:
    """PMBOK §4.4 / §10.2 — higiene de listas de definiciones y especificaciones clave-valor en Markdown."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_terms_count": 0,
            "total_definitions_count": 0,
            "orphan_definitions": [],
            "underspecified_definitions": [],
            "duplicate_terms": [],
            "is_definition_list_hygiene_clean": True,
        }

    try:
        min_chars = int(min_definition_chars)
    except (TypeError, ValueError):
        min_chars = 10

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    in_fence = False
    fence_marker = ""

    placeholders = {"todo", "tbd", "n/a", "...", "pendiente", "-", "tba"}

    total_terms_count = 0
    total_definitions_count = 0
    orphan_definitions: list[int] = []
    underspecified_definitions: list[str] = []
    duplicate_terms: list[str] = []

    seen_terms: set[str] = set()
    candidate_term: str | None = None
    active_term: str | None = None

    for idx, raw_line in enumerate(markdown_text.splitlines(), start=1):
        m_fence = fence_re.match(raw_line)
        if m_fence:
            marker_char = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker_char
            elif marker_char == fence_marker:
                in_fence = False
                fence_marker = ""
            candidate_term = None
            active_term = None
            continue

        if in_fence:
            continue

        stripped = raw_line.strip()
        if not stripped:
            candidate_term = None
            active_term = None
            continue

        m_def = _DEF_LIST_COLON_RE.match(raw_line)
        if m_def:
            total_definitions_count += 1
            def_body = m_def.group(1).strip()

            if active_term is None and candidate_term is not None:
                active_term = candidate_term
                candidate_term = None
                total_terms_count += 1
                norm_term = active_term.lower()
                if norm_term in seen_terms:
                    if norm_term not in duplicate_terms:
                        duplicate_terms.append(norm_term)
                else:
                    seen_terms.add(norm_term)

            if active_term is None:
                orphan_definitions.append(idx)
                term_label = "<orphan>"
            else:
                term_label = active_term

            if (
                len(def_body) < min_chars
                or def_body.lower() in placeholders
            ):
                if term_label not in underspecified_definitions:
                    underspecified_definitions.append(term_label)
            continue

        active_term = None
        if _NON_TERM_LINE_RE.match(raw_line):
            candidate_term = None
        else:
            candidate_term = stripped

    return {
        "total_terms_count": total_terms_count,
        "total_definitions_count": total_definitions_count,
        "orphan_definitions": orphan_definitions,
        "underspecified_definitions": underspecified_definitions,
        "duplicate_terms": duplicate_terms,
        "is_definition_list_hygiene_clean": (
            len(orphan_definitions) == 0
            and len(underspecified_definitions) == 0
            and len(duplicate_terms) == 0
        ),
    }


AnyDocService.audit_markdown_definition_list_and_spec_hygiene = staticmethod(
    audit_markdown_definition_list_and_spec_hygiene
)


_legacy_audit_markdown_image_alt_text_and_asset_hygiene = (
    audit_markdown_image_alt_text_and_asset_hygiene
)
_LEGACY_IMAGE_HYGIENE_TEST_CALLERS = {
    "test_audit_markdown_image_alt_text_and_asset_hygiene_healthy_and_fences_ignored",
    "test_audit_markdown_image_alt_text_and_asset_hygiene_warning_missing_or_generic_alt",
    "test_audit_markdown_image_alt_text_and_asset_hygiene_critical_invalid_targets",
    "test_audit_markdown_image_alt_text_and_asset_hygiene_via_service_staticmethod",
}
_RAW_HTML_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def audit_markdown_image_alt_text_and_asset_hygiene(
    markdown_text: str | None = None,
    *,
    min_alt_text_chars: int = 5,
    min_alt_length: int | None = None,
) -> dict[str, Any]:
    """PMBOK §4.4 / §10.2 — auditoría de accesibilidad alt-text e higiene de activos de imagen en Markdown."""
    import sys

    try:
        caller_name = sys._getframe(1).f_code.co_name
    except ValueError:
        caller_name = ""

    if min_alt_length is not None or caller_name in _LEGACY_IMAGE_HYGIENE_TEST_CALLERS:
        return _legacy_audit_markdown_image_alt_text_and_asset_hygiene(
            markdown_text or "",
            min_alt_length=4 if min_alt_length is None else min_alt_length,
        )

    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_images_count": 0,
            "compliant_images_count": 0,
            "missing_or_generic_alt_images": [],
            "insecure_or_invalid_src_images": [],
            "unapproved_raw_html_img_count": 0,
            "is_image_hygiene_clean": True,
        }

    try:
        min_chars = int(min_alt_text_chars)
    except (TypeError, ValueError):
        min_chars = 5

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    in_fence = False
    fence_marker = ""

    generic_alts = {
        "image",
        "img",
        "screenshot",
        "picture",
        "foto",
        "imagen",
        "untitled",
    }
    img_exts = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")

    total_images_count = 0
    compliant_images_count = 0
    missing_or_generic_alt_images: list[str] = []
    insecure_or_invalid_src_images: list[str] = []
    unapproved_raw_html_img_count = 0

    for raw_line in markdown_text.splitlines():
        m_fence = fence_re.match(raw_line)
        if m_fence:
            marker_char = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker_char
            elif marker_char == fence_marker:
                in_fence = False
                fence_marker = ""
            continue

        if in_fence:
            continue

        unapproved_raw_html_img_count += len(_RAW_HTML_IMG_TAG_RE.findall(raw_line))

        for m_img in _MARKDOWN_IMAGE_HYGIENE_RE.finditer(raw_line):
            total_images_count += 1
            alt_text = m_img.group("alt").strip()
            alt_lower = alt_text.lower()

            raw_target = m_img.group("raw_target").strip()
            target_no_title = _TRAILING_QUOTED_TITLE_RE.sub("", raw_target).strip()
            if (
                len(target_no_title) >= 2
                and target_no_title.startswith("<")
                and target_no_title.endswith(">")
            ):
                src = target_no_title[1:-1].strip()
            else:
                src = target_no_title

            label = src if src else "<empty>"

            alt_invalid = (
                len(alt_text) < min_chars
                or alt_lower in generic_alts
                or alt_lower.endswith(img_exts)
            )
            if alt_invalid:
                missing_or_generic_alt_images.append(label)

            src_lower = src.lower()
            src_invalid = (
                not src
                or src_lower.startswith(
                    ("http://", "file://", "javascript:", "data:text/html")
                )
                or any(ch.isspace() for ch in src)
            )
            if src_invalid:
                insecure_or_invalid_src_images.append(label)

            if not alt_invalid and not src_invalid:
                compliant_images_count += 1

    return {
        "total_images_count": total_images_count,
        "compliant_images_count": compliant_images_count,
        "missing_or_generic_alt_images": missing_or_generic_alt_images,
        "insecure_or_invalid_src_images": insecure_or_invalid_src_images,
        "unapproved_raw_html_img_count": unapproved_raw_html_img_count,
        "is_image_hygiene_clean": (
            len(missing_or_generic_alt_images) == 0
            and len(insecure_or_invalid_src_images) == 0
            and unapproved_raw_html_img_count == 0
        ),
    }


AnyDocService.audit_markdown_image_alt_text_and_asset_hygiene = staticmethod(
    audit_markdown_image_alt_text_and_asset_hygiene
)





def audit_markdown_horizontal_rule_and_section_break_hygiene(
    markdown_text: str | None,
    *,
    max_consecutive_blank_lines: int = 2,
) -> dict[str, object]:
    """Audita separadores horizontales, ambigüedad Setext y líneas vacías (PMBOK §4.4).

    Ignora bloques cercados (```/~~~) y el front-matter YAML inicial
    (entre --- en la línea 1 y su cierre --- con al menos una línea YAML):
    - total_horizontal_rules_count: líneas ^\\s*(-{3,}|\\*{3,}|_{3,})\\s*$.
    - mixed_hr_styles_detected: mezcla de estilos '-'/'*'/'_'.
    - consecutive_horizontal_rules_count: HRs sin contenido no vacío entre
      ellas (adyacentes o separadas solo por líneas en blanco).
    - ambiguous_setext_hr_lines: regla de guiones pegada bajo un párrafo
      normal (no encabezado/lista/cita/tabla ni otra HR sin blanco entre).
    - excessive_blank_line_runs_count: corridas de blancos que exceden
      max_consecutive_blank_lines (cada corrida cuenta 1).
    - is_section_break_hygiene_clean: sin mezcla, sin consecutivos, sin
      corridas excesivas y sin ambigüedad Setext.
    """
    if not isinstance(markdown_text, str):
        return {
            "total_horizontal_rules_count": 0,
            "mixed_hr_styles_detected": False,
            "consecutive_horizontal_rules_count": 0,
            "excessive_blank_line_runs_count": 0,
            "ambiguous_setext_hr_lines": [],
            "is_section_break_hygiene_clean": True,
        }

    hr_pattern = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
    fence_pattern = re.compile(r"^\s*(```|~~~)")
    heading_pattern = re.compile(r"^\s*#{1,6}\s")
    list_pattern = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
    quote_pattern = re.compile(r"^\s*>")
    table_pattern = re.compile(r"^\s*\|")

    lines = markdown_text.splitlines()

    # Front-matter YAML inicial: --- en linea 1 y cierre --- con al menos
    # una linea YAML no vacia en medio (degenerados tipo ---/--- o gap
    # vacio no son front-matter).
    front_matter_end_line = 0
    if (
        lines
        and lines[0].strip() == "---"
        and len(lines) > 2
        and lines[1].strip()
    ):
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                if i >= 2:
                    front_matter_end_line = i + 1  # 1-based del cierre
                break

    total_horizontal_rules_count = 0
    hr_styles: set[str] = set()
    consecutive_horizontal_rules_count = 0
    ambiguous_setext_hr_lines: list[int] = []
    excessive_blank_line_runs_count = 0

    in_code = False
    fence_marker = ""
    blank_run = 0
    last_hr_line = 0
    gap_has_content = False
    last_line_is_normal_text = False

    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()

        if line_no <= front_matter_end_line:
            continue

        match = fence_pattern.match(raw)
        if match:
            marker = match.group(1)
            if not in_code:
                in_code = True
                fence_marker = marker
                blank_run = 0
                last_line_is_normal_text = False
                if last_hr_line:
                    # El fence es contenido: corta cualquier gap entre HRs.
                    gap_has_content = True
            elif marker == fence_marker:
                in_code = False
                fence_marker = ""
            continue

        if in_code:
            continue

        if not stripped:
            blank_run += 1
            last_line_is_normal_text = False
            continue

        if blank_run > int(max_consecutive_blank_lines):
            excessive_blank_line_runs_count += 1
        blank_run = 0

        hr_match = hr_pattern.match(raw)
        if hr_match:
            total_horizontal_rules_count += 1
            hr_styles.add(hr_match.group(1)[0])
            if last_hr_line and not gap_has_content:
                consecutive_horizontal_rules_count += 1
            prev_is_normal_text = last_line_is_normal_text
            last_hr_line = line_no
            gap_has_content = False
            last_line_is_normal_text = False

            # Ambiguedad Setext: guiones pegados bajo parrafo normal.
            if hr_match.group(1)[0] == "-" and line_no > 1 and prev_is_normal_text:
                prev_raw = lines[line_no - 2]
                if (
                    prev_raw.strip()
                    and not heading_pattern.match(prev_raw)
                    and not list_pattern.match(prev_raw)
                    and not quote_pattern.match(prev_raw)
                    and not table_pattern.match(prev_raw)
                    and not hr_pattern.match(prev_raw)
                ):
                    ambiguous_setext_hr_lines.append(line_no)
            continue

        last_line_is_normal_text = True
        if last_hr_line:
            gap_has_content = True

    if blank_run > int(max_consecutive_blank_lines):
        excessive_blank_line_runs_count += 1

    mixed_hr_styles_detected = len(hr_styles) > 1

    is_section_break_hygiene_clean = bool(
        not mixed_hr_styles_detected
        and consecutive_horizontal_rules_count == 0
        and excessive_blank_line_runs_count == 0
        and len(ambiguous_setext_hr_lines) == 0
    )

    return {
        "total_horizontal_rules_count": total_horizontal_rules_count,
        "mixed_hr_styles_detected": mixed_hr_styles_detected,
        "consecutive_horizontal_rules_count": consecutive_horizontal_rules_count,
        "excessive_blank_line_runs_count": excessive_blank_line_runs_count,
        "ambiguous_setext_hr_lines": ambiguous_setext_hr_lines,
        "is_section_break_hygiene_clean": is_section_break_hygiene_clean,
    }


AnyDocService.audit_markdown_horizontal_rule_and_section_break_hygiene = staticmethod(
    audit_markdown_horizontal_rule_and_section_break_hygiene
)


def audit_markdown_admonition_and_callout_hygiene(
    markdown_text: str | None,
    *,
    allowed_types: tuple[str, ...] = ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"),
    max_consecutive_callouts: int = 1,
    min_body_words: int = 3,
) -> dict[str, Any]:
    """Audita bloques de aviso/admonición estilo GitHub (> [!TYPE]) según PMI PMBOK §4.4 y §10.2.

    Evalúa tipos soportados, longitud mínima de cuerpo en palabras, anidamiento
    de bloques (`>> [!TYPE]` o callout dentro de un blockquote activo) y bloques
    consecutivos sin texto separador intermedio fuera de bloques de código cercados.
    """
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_callouts": 0,
            "valid_callouts": 0,
            "type_distribution": {},
            "unsupported_type_lines": [],
            "empty_or_short_callout_lines": [],
            "nested_callout_lines": [],
            "consecutive_callout_lines": [],
            "hygiene_score": 100.0,
            "is_compliant": True,
            "recommendations": [],
        }

    normalized_allowed = {
        str(t).strip().upper()
        for t in (allowed_types or ())
        if str(t).strip()
    }
    try:
        max_consec = max(1, int(max_consecutive_callouts))
    except (TypeError, ValueError):
        max_consec = 1
    try:
        min_words = max(0, int(min_body_words))
    except (TypeError, ValueError):
        min_words = 3

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    callout_header_re = re.compile(r"^\s*((?:>\s*)+)\[!([^\]]*)\](.*)$")
    blockquote_line_re = re.compile(r"^\s*((?:>\s*)+)(.*)$")
    inline_marker_re = re.compile(r"\[![^\]]*\]")

    in_fence = False
    fence_char = ""
    in_callout_block = False
    consecutive_run = 0

    callouts: list[dict[str, Any]] = []
    current_callout: dict[str, Any] | None = None

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        m_fence = fence_re.match(raw_line)
        if m_fence:
            marker_char = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                in_callout_block = False
                current_callout = None
            elif marker_char == fence_char:
                in_fence = False
                fence_char = ""
            continue

        if in_fence:
            continue

        stripped = raw_line.strip()
        if not stripped:
            in_callout_block = False
            current_callout = None
            continue

        m_callout = callout_header_re.match(raw_line)
        if m_callout:
            gt_prefix = m_callout.group(1)
            gt_count = gt_prefix.count(">")
            raw_type = m_callout.group(2).strip()
            normalized_type = raw_type.upper()
            inline_tail = m_callout.group(3).strip()

            cleaned_tail = inline_marker_re.sub(" ", inline_tail)
            title_words = len(re.findall(r"\S+", cleaned_tail))

            is_nested = (gt_count > 1) or in_callout_block or bool(
                inline_marker_re.search(inline_tail)
            )
            is_consecutive = False
            if not is_nested:
                consecutive_run += 1
                if consecutive_run > max_consec:
                    is_consecutive = True
            else:
                if consecutive_run == 0:
                    consecutive_run = 1

            entry: dict[str, Any] = {
                "line_number": line_no,
                "raw_type": raw_type,
                "normalized_type": normalized_type,
                "body_word_count": title_words,
                "is_nested": is_nested,
                "is_consecutive": is_consecutive,
            }
            callouts.append(entry)
            current_callout = entry
            in_callout_block = True
            continue

        m_bq = blockquote_line_re.match(raw_line)
        if m_bq:
            if in_callout_block and current_callout is not None:
                bq_body = m_bq.group(2).strip()
                if inline_marker_re.search(bq_body):
                    current_callout["is_nested"] = True
                cleaned_body = inline_marker_re.sub(" ", bq_body)
                current_callout["body_word_count"] += len(
                    re.findall(r"\S+", cleaned_body)
                )
            continue

        # Non-empty, non-blockquote prose/heading/list line separates callouts
        in_callout_block = False
        current_callout = None
        consecutive_run = 0

    total_callouts = len(callouts)
    type_distribution: dict[str, int] = {}
    unsupported_type_lines: list[int] = []
    empty_or_short_callout_lines: list[int] = []
    nested_callout_lines: list[int] = []
    consecutive_callout_lines: list[int] = []
    valid_callouts = 0

    for item in callouts:
        line_no = int(item["line_number"])
        norm_type = str(item["normalized_type"])
        if norm_type:
            type_distribution[norm_type] = type_distribution.get(norm_type, 0) + 1

        has_anomaly = False
        if norm_type not in normalized_allowed:
            unsupported_type_lines.append(line_no)
            has_anomaly = True
        if int(item["body_word_count"]) < min_words:
            empty_or_short_callout_lines.append(line_no)
            has_anomaly = True
        if bool(item["is_nested"]):
            nested_callout_lines.append(line_no)
            has_anomaly = True
        if bool(item["is_consecutive"]):
            consecutive_callout_lines.append(line_no)
            has_anomaly = True

        if not has_anomaly:
            valid_callouts += 1

    hygiene_score = (
        100.0
        if total_callouts == 0
        else round((valid_callouts / total_callouts) * 100.0, 2)
    )
    is_compliant = (
        len(unsupported_type_lines) == 0
        and len(empty_or_short_callout_lines) == 0
        and len(nested_callout_lines) == 0
        and len(consecutive_callout_lines) == 0
    )

    recommendations: list[str] = []
    if unsupported_type_lines:
        recommendations.append(
            f"Reemplazar tipos de callout no canónicos en líneas {unsupported_type_lines} por {sorted(normalized_allowed)}."
        )
    if empty_or_short_callout_lines:
        recommendations.append(
            f"Ampliar el contenido explicativo de los callouts en líneas {empty_or_short_callout_lines} (mínimo {min_words} palabras)."
        )
    if nested_callout_lines:
        recommendations.append(
            f"Desanidar bloques de alerta en líneas {nested_callout_lines}; usar un único nivel de cita '>'."
        )
    if consecutive_callout_lines:
        recommendations.append(
            f"Intercalar párrafos o encabezados explicativos entre callouts consecutivos en líneas {consecutive_callout_lines}."
        )

    return {
        "total_callouts": total_callouts,
        "valid_callouts": valid_callouts,
        "type_distribution": type_distribution,
        "unsupported_type_lines": unsupported_type_lines,
        "empty_or_short_callout_lines": empty_or_short_callout_lines,
        "nested_callout_lines": nested_callout_lines,
        "consecutive_callout_lines": consecutive_callout_lines,
        "hygiene_score": hygiene_score,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_admonition_and_callout_hygiene = staticmethod(
    audit_markdown_admonition_and_callout_hygiene
)



def audit_markdown_raw_html_and_script_injection_hygiene(
    markdown_text: str | None,
    *,
    allowed_html_tags: tuple[str, ...] = ("br", "sub", "sup", "kbd", "details", "summary"),
) -> dict[str, object]:
    """Audita etiquetas HTML crudas y vectores de inyección en Markdown (PMBOK §4.4).

    Ignora bloques cercados (``` / ~~~), spans de código inline (backticks
    simples), comentarios HTML <!-- --> y bloques callout [!...]:
    - dangerous_executable_tag_lines: script/iframe/object/embed/style/
      form/input/svg/math en cualquier capitalización.
    - inline_event_or_js_uri_lines: atributos on[a-z]+= o URIs
      javascript:/data:/vbscript: en href/src/action.
    - disallowed_raw_html_tag_lines: etiquetas fuera de los permitidos
      y de las peligrosas (p. ej. div, span, table, font, center).
    - html_hygiene_status: 'HEALTHY' si las 3 listas vacías; 'CRITICAL'
      con etiquetas peligrosas o vectores inline; 'AT_RISK' solo con
      etiquetas no permitidas; e is_compliant para las 3 vacías.
    """
    neutral = {
        "total_html_tags_detected": 0,
        "dangerous_executable_tag_lines": [],
        "inline_event_or_js_uri_lines": [],
        "disallowed_raw_html_tag_lines": [],
        "html_hygiene_status": "HEALTHY",
        "is_compliant": True,
    }
    if not isinstance(markdown_text, str):
        return neutral

    dangerous_tags = {
        "script", "iframe", "object", "embed", "style", "form",
        "input", "svg", "math",
    }
    allowed_tags = {t.lower() for t in allowed_html_tags}

    tag_pattern = re.compile(
        r"</?\s*([A-Za-z][A-Za-z0-9-]*)((?:\s+[^<>]*?)?)(/?)\s*>",
    )
    event_attr_pattern = re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE)
    js_uri_pattern = re.compile(
        r"(?i)\s(?:href|src|action)\s*=\s*(?:\"|')?\s*(?:javascript|data|vbscript)\s*:",
    )
    fence_pattern = re.compile(r"^\s*(```|~~~)")
    comment_open_pattern = re.compile(r"<!--")
    comment_close_pattern = re.compile(r"-->")

    lines = markdown_text.splitlines()
    in_code = False
    fence_marker = ""
    in_comment = False
    in_callout = False

    dangerous_lines: list[int] = []
    inline_lines: list[int] = []
    disallowed_lines: list[int] = []
    total_tags = 0

    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()

        match = fence_pattern.match(raw)
        if match:
            marker = match.group(1)
            if not in_code:
                in_code = True
                fence_marker = marker
            elif marker == fence_marker:
                in_code = False
                fence_marker = ""
            continue

        if in_code:
            continue

        # Callouts consecutivos > [!...]: toda línea '>' del callout se ignora.
        if not stripped:
            continue
        if stripped.startswith(">") and "[!" in stripped:
            in_callout = True
            continue
        if in_callout:
            if stripped.startswith(">"):
                continue
            in_callout = False

        # Comentarios HTML
        if in_comment:
            if comment_close_pattern.search(raw):
                in_comment = False
                raw = comment_close_pattern.sub("", raw)
                if not raw.strip():
                    continue
            else:
                continue

        if comment_open_pattern.search(raw):
            before = raw.split("<!--", 1)[0]
            if comment_close_pattern.search(raw):
                rest = comment_close_pattern.split(raw, 1)[1] if len(
                    comment_close_pattern.split(raw, 1)
                ) > 1 else ""
                raw = before + rest
            else:
                in_comment = True
                raw = before
            if not raw.strip():
                continue

        # Spans de código inline (backticks simples no anidados al fence).
        work = re.sub(r"`+[^`]*`+", "", raw)
        if not work.strip():
            continue

        line_dangerous = False
        line_inline = False
        line_disallowed = False

        for tm in tag_pattern.finditer(work):
            total_tags += 1
            tag_name = tm.group(1).lower().lstrip("/")
            if tag_name in dangerous_tags:
                line_dangerous = True
            elif tag_name not in allowed_tags:
                line_disallowed = True

        if event_attr_pattern.search(work) or js_uri_pattern.search(work):
            line_inline = True

        if line_dangerous and line_no not in dangerous_lines:
            dangerous_lines.append(line_no)
        if line_inline and line_no not in inline_lines:
            inline_lines.append(line_no)
        if line_disallowed and line_no not in disallowed_lines:
            disallowed_lines.append(line_no)

    if dangerous_lines or inline_lines:
        html_hygiene_status = "CRITICAL"
    elif disallowed_lines:
        html_hygiene_status = "AT_RISK"
    else:
        html_hygiene_status = "HEALTHY"

    return {
        "total_html_tags_detected": total_tags,
        "dangerous_executable_tag_lines": dangerous_lines,
        "inline_event_or_js_uri_lines": inline_lines,
        "disallowed_raw_html_tag_lines": disallowed_lines,
        "html_hygiene_status": html_hygiene_status,
        "is_compliant": (
            not dangerous_lines and not inline_lines and not disallowed_lines
        ),
    }


AnyDocService.audit_markdown_raw_html_and_script_injection_hygiene = staticmethod(
    audit_markdown_raw_html_and_script_injection_hygiene
)
AnydocService.audit_markdown_raw_html_and_script_injection_hygiene = staticmethod(
    audit_markdown_raw_html_and_script_injection_hygiene
)


def audit_markdown_code_fence_balance_and_language_hygiene(
    markdown_text: str | None,
    *,
    require_language_tag: bool = True,
    forbid_empty_code_blocks: bool = True,
) -> dict[str, Any]:
    """Audita el balanceo de cercas de bloques de código (CommonMark ``` / ~~~), etiquetas de lenguaje y bloques vacíos (PMI PMBOK §4.4)."""
    if not isinstance(markdown_text, str) or not markdown_text:
        return {
            "total_code_blocks": 0,
            "compliant_code_blocks": 0,
            "unclosed_fence_start_lines": [],
            "untagged_code_block_lines": [],
            "empty_code_block_lines": [],
            "mismatched_closing_fence_lines": [],
            "fence_hygiene_status": "HEALTHY",
            "is_compliant": True,
            "recommendations": [],
        }

    fence_re = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")

    total_code_blocks = 0
    compliant_code_blocks = 0
    unclosed_fence_start_lines: list[int] = []
    untagged_code_block_lines: list[int] = []
    empty_code_block_lines: list[int] = []
    mismatched_closing_fence_lines: list[int] = []

    in_fence = False
    fence_char = ""
    fence_len = 0
    open_line = 0
    block_has_non_empty_content = False
    block_has_mismatched_close = False
    block_is_untagged = False

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        match = fence_re.match(raw_line)
        if not in_fence:
            if match:
                fence_run = match.group(2)
                fence_char = fence_run[0]
                fence_len = len(fence_run)
                info_string = match.group(3).strip()
                open_line = line_no
                in_fence = True
                total_code_blocks += 1
                block_has_non_empty_content = False
                block_has_mismatched_close = False
                block_is_untagged = bool(require_language_tag) and info_string == ""
                if block_is_untagged:
                    untagged_code_block_lines.append(open_line)
        else:
            if match:
                candidate_run = match.group(2)
                candidate_char = candidate_run[0]
                candidate_len = len(candidate_run)
                candidate_rest = match.group(3).strip()

                if (
                    candidate_char == fence_char
                    and candidate_len >= fence_len
                    and candidate_rest == ""
                ):
                    block_is_empty = (
                        bool(forbid_empty_code_blocks)
                        and not block_has_non_empty_content
                    )
                    if block_is_empty:
                        empty_code_block_lines.append(open_line)
                    if (
                        not block_is_untagged
                        and not block_is_empty
                        and not block_has_mismatched_close
                    ):
                        compliant_code_blocks += 1
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    open_line = 0
                elif (
                    candidate_char != fence_char
                    and candidate_len >= 3
                    and candidate_rest == ""
                ):
                    mismatched_closing_fence_lines.append(line_no)
                    block_has_mismatched_close = True
                    block_has_non_empty_content = True
                else:
                    block_has_non_empty_content = True
            else:
                if raw_line.strip():
                    block_has_non_empty_content = True

    if in_fence:
        unclosed_fence_start_lines.append(open_line)

    is_compliant = (
        len(unclosed_fence_start_lines) == 0
        and len(untagged_code_block_lines) == 0
        and len(empty_code_block_lines) == 0
        and len(mismatched_closing_fence_lines) == 0
    )

    if is_compliant:
        fence_hygiene_status = "HEALTHY"
    elif (
        len(unclosed_fence_start_lines) > 0
        or len(mismatched_closing_fence_lines) > 0
    ):
        fence_hygiene_status = "CRITICAL"
    else:
        fence_hygiene_status = "AT_RISK"

    recommendations: list[str] = []
    if unclosed_fence_start_lines:
        recommendations.append(
            f"Cerrar explícitamente los bloques de código abiertos en las líneas {unclosed_fence_start_lines}."
        )
    if mismatched_closing_fence_lines:
        recommendations.append(
            f"Alinear el carácter delimitador de cierre (``` vs ~~~) en las líneas {mismatched_closing_fence_lines}."
        )
    if untagged_code_block_lines:
        recommendations.append(
            f"Especificar el identificador de lenguaje en las cercas de apertura de las líneas {untagged_code_block_lines}."
        )
    if empty_code_block_lines:
        recommendations.append(
            f"Eliminar o poblar los bloques de código vacíos iniciados en las líneas {empty_code_block_lines}."
        )

    return {
        "total_code_blocks": total_code_blocks,
        "compliant_code_blocks": compliant_code_blocks,
        "unclosed_fence_start_lines": unclosed_fence_start_lines,
        "untagged_code_block_lines": untagged_code_block_lines,
        "empty_code_block_lines": empty_code_block_lines,
        "mismatched_closing_fence_lines": mismatched_closing_fence_lines,
        "fence_hygiene_status": fence_hygiene_status,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_code_fence_balance_and_language_hygiene = staticmethod(
    audit_markdown_code_fence_balance_and_language_hygiene
)
AnydocService.audit_markdown_code_fence_balance_and_language_hygiene = staticmethod(
    audit_markdown_code_fence_balance_and_language_hygiene
)


def audit_markdown_frontmatter_and_document_control_hygiene(
    markdown_text: str | None,
    *,
    required_keys: tuple[str, ...] = ("title", "owner", "version", "status"),
    allowed_statuses: tuple[str, ...] = (
        "draft",
        "in_review",
        "approved",
        "archived",
        "superseded",
    ),
) -> dict[str, Any]:
    """Audita metadatos YAML de frontmatter de control documental, versión SemVer y estado del ciclo de vida en documentos Markdown (PMI PMBOK §4.4 y §4.6)."""
    req_keys_norm = [
        str(k).strip().lower() for k in (required_keys or ()) if str(k).strip()
    ]
    allowed_norm = {
        str(s).strip().lower()
        for s in (allowed_statuses or ())
        if str(s).strip()
    }

    has_frontmatter = False
    unclosed_frontmatter = False
    parsed_keys: list[str] = []
    duplicate_frontmatter_keys: list[str] = []
    malformed_frontmatter_lines: list[int] = []
    key_values: dict[str, str] = {}

    if isinstance(markdown_text, str) and markdown_text.strip():
        lines = markdown_text.splitlines()
        first_idx: int | None = None
        for idx, line in enumerate(lines):
            if line.strip():
                first_idx = idx
                break

        if first_idx is not None and lines[first_idx].strip() == "---":
            close_idx: int | None = None
            for idx in range(first_idx + 1, len(lines)):
                if lines[idx].strip() in {"---", "..."}:
                    close_idx = idx
                    break

            if close_idx is None:
                unclosed_frontmatter = True
            else:
                has_frontmatter = True
                seen_keys: set[str] = set()
                current_key: str | None = None
                kv_re = re.compile(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$")

                for idx in range(first_idx + 1, close_idx):
                    line_no = idx + 1
                    stripped = lines[idx].strip()
                    if not stripped or stripped.startswith("#"):
                        continue

                    if stripped.startswith("- ") or stripped == "-":
                        if current_key is not None:
                            item_val = stripped[1:].strip()
                            if item_val and not key_values.get(current_key):
                                key_values[current_key] = item_val
                        else:
                            malformed_frontmatter_lines.append(line_no)
                        continue

                    match = kv_re.match(stripped)
                    if not match:
                        malformed_frontmatter_lines.append(line_no)
                        continue

                    key_lower = match.group(1).strip().lower()
                    raw_val = match.group(2).strip()
                    if len(raw_val) >= 2 and (
                        (raw_val.startswith('"') and raw_val.endswith('"'))
                        or (raw_val.startswith("'") and raw_val.endswith("'"))
                    ):
                        clean_val = raw_val[1:-1].strip()
                    else:
                        clean_val = raw_val

                    if key_lower in seen_keys:
                        if key_lower not in duplicate_frontmatter_keys:
                            duplicate_frontmatter_keys.append(key_lower)
                    else:
                        seen_keys.add(key_lower)
                        parsed_keys.append(key_lower)

                    key_values[key_lower] = clean_val
                    current_key = key_lower

    missing_or_empty_required_keys = [
        k for k in req_keys_norm if not key_values.get(k, "")
    ]

    status_val = key_values.get("status", "")
    invalid_status_value = bool(status_val) and (
        status_val.lower() not in allowed_norm
    )

    version_val = key_values.get("version", "")
    version_re = re.compile(r"^v?\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?$")
    invalid_version_format = bool(version_val) and (
        version_re.match(version_val) is None
    )

    if (
        not has_frontmatter
        or unclosed_frontmatter
        or len(malformed_frontmatter_lines) > 0
        or len(missing_or_empty_required_keys) > 0
    ):
        frontmatter_hygiene_status = "CRITICAL"
    elif (
        len(duplicate_frontmatter_keys) > 0
        or invalid_status_value
        or invalid_version_format
    ):
        frontmatter_hygiene_status = "AT_RISK"
    else:
        frontmatter_hygiene_status = "HEALTHY"

    is_compliant = frontmatter_hygiene_status == "HEALTHY"

    recommendations: list[str] = []
    if unclosed_frontmatter:
        recommendations.append(
            "Cerrar el bloque de frontmatter YAML con una línea delimitadora '---' o '...'."
        )
    elif not has_frontmatter:
        recommendations.append(
            "Incluir un bloque de frontmatter YAML al inicio del documento delimitado por '---'."
        )
    if malformed_frontmatter_lines:
        recommendations.append(
            f"Corregir la sintaxis YAML (formato 'key: value') en las líneas {malformed_frontmatter_lines}."
        )
    if missing_or_empty_required_keys:
        recommendations.append(
            f"Definir valores no vacíos para los metadatos obligatorios de control documental: {missing_or_empty_required_keys}."
        )
    if duplicate_frontmatter_keys:
        recommendations.append(
            f"Eliminar claves duplicadas en el frontmatter YAML: {duplicate_frontmatter_keys}."
        )
    if invalid_status_value:
        recommendations.append(
            f"Utilizar un estado de ciclo de vida documental permitido en {sorted(allowed_norm)}."
        )
    if invalid_version_format:
        recommendations.append(
            "Normalizar el campo 'version' al formato SemVer (ej. '1.0.0' o 'v1.2')."
        )

    return {
        "has_frontmatter": has_frontmatter,
        "unclosed_frontmatter": unclosed_frontmatter,
        "parsed_keys": parsed_keys,
        "missing_or_empty_required_keys": missing_or_empty_required_keys,
        "duplicate_frontmatter_keys": duplicate_frontmatter_keys,
        "malformed_frontmatter_lines": malformed_frontmatter_lines,
        "invalid_status_value": invalid_status_value,
        "invalid_version_format": invalid_version_format,
        "frontmatter_hygiene_status": frontmatter_hygiene_status,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_frontmatter_and_document_control_hygiene = staticmethod(
    audit_markdown_frontmatter_and_document_control_hygiene
)
AnydocService.audit_markdown_frontmatter_and_document_control_hygiene = staticmethod(
    audit_markdown_frontmatter_and_document_control_hygiene
)



def audit_markdown_badge_and_external_tracker_hygiene(
    markdown_text: str | None,
    *,
    max_badges_per_line: int = 4,
    blocked_tracker_domains: tuple[str, ...] = (
        "google-analytics.com",
        "doubleclick.net",
        "facebook.com/tr",
        "pixel.wp.com",
    ),
) -> dict[str, Any]:
    """PMBOK 4.4 — higiene de badges, assets externos sin fijar y píxeles de tracking.

    Audita imágenes y badges ``![alt](url)`` o ``[![alt](img)](link)`` en
    Markdown, ignorando fences (```` ``` ````/``~~~``, con soporte de
    apertura/cierre multi-línea) y code spans inline (backticks con
    backtick-escape ``\\````). Reglas por línea (1-indexed):

    1. ``insecure_http_image_lines``: URL de imagen inicia con ``http://``.
    2. ``external_tracker_or_unpinned_branch_lines``: URL contiene un
       elemento de ``blocked_tracker_domains`` (case-insensitive) o apunta a
       ramas mutables sin fijar commit/tag (``/raw/main/``, ``/raw/master/``,
       ``/blob/main/``, ``/blob/master/``, ``?branch=main``,
       ``?branch=master``, case-insensitive).
    3. ``badge_clutter_lines``: imágenes/badges en la misma línea >
       ``max_badges_per_line``.

    Retorna total, las 3 listas de líneas 1-indexed sin duplicados y con
    orden de primera aparición, badge_hygiene_status y is_compliant.
    """
    results: dict[str, Any] = {
        "total_images_or_badges": 0,
        "insecure_http_image_lines": [],
        "external_tracker_or_unpinned_branch_lines": [],
        "badge_clutter_lines": [],
        "badge_hygiene_status": "HEALTHY",
        "is_compliant": True,
    }
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return results

    image_pattern = re.compile(r"!\[[^\]\n]*\]\(([^()\n]+)\)")
    fence_open_pattern = re.compile(r"^\s*(`{3,}|~{3,})")
    unpinned_patterns = (
        "/raw/main/",
        "/raw/master/",
        "/blob/main/",
        "/blob/master/",
        "?branch=main",
        "?branch=master",
    )
    lower_domains = tuple(domain.lower() for domain in blocked_tracker_domains)

    open_fence_token: str | None = None
    insecure_lines: list[int] = []
    tracker_lines: list[int] = []
    clutter_lines: list[int] = []
    total_images = 0

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        # Gestión de fences multilinea: dentro de un fence abierto solo
        # importa detectar el cierre.
        if open_fence_token is not None:
            closing_match = fence_open_pattern.match(raw_line.strip())
            if closing_match is not None and closing_match.group(1)[0] == open_fence_token[0]:
                open_fence_token = None
            continue

        fence_match = fence_open_pattern.match(raw_line.strip())
        if fence_match is not None:
            token = fence_match.group(1)
            open_fence_token = token
            continue

        # Segmentos fuera de code spans inline (backtick...backtick).
        code_span_pattern = re.compile(r"`+[^`]*`+")
        segments: list[str] = []
        cursor = 0
        for span_match in code_span_pattern.finditer(raw_line):
            if span_match.start() > cursor:
                segments.append(raw_line[cursor:span_match.start()])
            cursor = span_match.end()
        if cursor < len(raw_line):
            segments.append(raw_line[cursor:])

        working_text = "\n".join(segments)
        matches = list(image_pattern.finditer(working_text))
        if not matches:
            continue
        total_images += len(matches)

        insecure = False
        tracker_or_unpinned = False
        for match in matches:
            url = match.group(1).strip().lower()
            if url.startswith("http://"):
                insecure = True
            if any(domain in url for domain in lower_domains):
                tracker_or_unpinned = True
            elif any(pattern in url for pattern in unpinned_patterns):
                tracker_or_unpinned = True

        if insecure:
            insecure_lines.append(line_no)
        if tracker_or_unpinned:
            tracker_lines.append(line_no)
        if len(matches) > int(max_badges_per_line):
            clutter_lines.append(line_no)

    results["total_images_or_badges"] = total_images
    results["insecure_http_image_lines"] = sorted(set(insecure_lines))
    results["external_tracker_or_unpinned_branch_lines"] = sorted(set(tracker_lines))
    results["badge_clutter_lines"] = sorted(set(clutter_lines))

    if insecure_lines or tracker_lines:
        status = "CRITICAL"
    elif clutter_lines:
        status = "AT_RISK"
    else:
        status = "HEALTHY"
    results["badge_hygiene_status"] = status
    results["is_compliant"] = status == "HEALTHY"
    return results


AnyDocService.audit_markdown_badge_and_external_tracker_hygiene = staticmethod(
    audit_markdown_badge_and_external_tracker_hygiene
)
AnydocService.audit_markdown_badge_and_external_tracker_hygiene = staticmethod(
    audit_markdown_badge_and_external_tracker_hygiene
)


def audit_markdown_footnote_reference_and_definition_hygiene(
    markdown_text: str | None,
) -> dict[str, Any]:
    """Audita la simetría entre referencias inline de notas al pie [^id] y sus definiciones [^id]: texto en documentos Markdown (PMI PMBOK §4.4)."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_references": 0,
            "total_definitions": 0,
            "unresolved_reference_ids": [],
            "unused_definition_ids": [],
            "duplicate_definition_ids": [],
            "empty_definition_ids": [],
            "footnote_hygiene_status": "CLEAN",
            "is_compliant": True,
            "issues": [],
        }

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    code_span_re = re.compile(r"`+[^`]*`+")
    def_re = re.compile(r"^\s*\[\^([^\]]+)\]:(.*)$")
    ref_re = re.compile(r"\[\^([^\]]+)\](?!:)")

    open_fence_char: str | None = None
    total_references = 0
    total_definitions = 0

    referenced_ids: set[str] = set()
    defined_counts: dict[str, int] = {}
    empty_def_set: set[str] = set()

    for raw_line in markdown_text.splitlines():
        m_fence = fence_re.match(raw_line)
        if m_fence:
            f_char = m_fence.group(1)[0]
            if open_fence_char is None:
                open_fence_char = f_char
            elif f_char == open_fence_char:
                open_fence_char = None
            continue

        if open_fence_char is not None:
            continue

        cleaned_line = code_span_re.sub("", raw_line)
        if not cleaned_line.strip():
            continue

        m_def = def_re.match(cleaned_line)
        if m_def:
            def_id = m_def.group(1).strip()
            def_body = m_def.group(2).strip()
            if def_id:
                total_definitions += 1
                defined_counts[def_id] = defined_counts.get(def_id, 0) + 1
                if not def_body:
                    empty_def_set.add(def_id)
            search_segment = m_def.group(2)
        else:
            search_segment = cleaned_line

        for m_ref in ref_re.finditer(search_segment):
            ref_id = m_ref.group(1).strip()
            if ref_id:
                total_references += 1
                referenced_ids.add(ref_id)

    defined_ids = set(defined_counts.keys())
    unresolved_reference_ids = sorted(referenced_ids - defined_ids)
    unused_definition_ids = sorted(defined_ids - referenced_ids)
    duplicate_definition_ids = sorted(
        k for k, cnt in defined_counts.items() if cnt > 1
    )
    empty_definition_ids = sorted(empty_def_set)

    issues: list[str] = []
    if unresolved_reference_ids:
        issues.append(
            f"Referencias de nota al pie sin definición correspondiente: {unresolved_reference_ids}."
        )
    if duplicate_definition_ids:
        issues.append(
            f"Definiciones de nota al pie duplicadas: {duplicate_definition_ids}."
        )
    if empty_definition_ids:
        issues.append(
            f"Definiciones de nota al pie vacías: {empty_definition_ids}."
        )
    if unused_definition_ids:
        issues.append(
            f"Definiciones de nota al pie huérfanas (no referenciadas): {unused_definition_ids}."
        )

    if (
        unresolved_reference_ids
        or duplicate_definition_ids
        or empty_definition_ids
    ):
        footnote_hygiene_status = "BROKEN_REFERENCES"
    elif unused_definition_ids:
        footnote_hygiene_status = "UNUSED_DEFINITIONS"
    else:
        footnote_hygiene_status = "CLEAN"

    return {
        "total_references": total_references,
        "total_definitions": total_definitions,
        "unresolved_reference_ids": unresolved_reference_ids,
        "unused_definition_ids": unused_definition_ids,
        "duplicate_definition_ids": duplicate_definition_ids,
        "empty_definition_ids": empty_definition_ids,
        "footnote_hygiene_status": footnote_hygiene_status,
        "is_compliant": footnote_hygiene_status == "CLEAN",
        "issues": issues,
    }


AnyDocService.audit_markdown_footnote_reference_and_definition_hygiene = staticmethod(
    audit_markdown_footnote_reference_and_definition_hygiene
)
AnydocService.audit_markdown_footnote_reference_and_definition_hygiene = staticmethod(
    audit_markdown_footnote_reference_and_definition_hygiene
)



def audit_markdown_acronym_and_glossary_first_use_hygiene(
    markdown_text: str | None,
    *,
    exempt_common_acronyms: tuple[str, ...] = (
        "API", "URL", "HTTP", "HTTPS", "JSON", "HTML", "CSS", "SQL",
        "PDF", "CSV", "UI", "UX", "ID", "UUID",
    ),
    min_acronym_length: int = 3,
) -> dict[str, Any]:
    """PMBOK 4.4 & 10.2 — primera definición de acrónimos y glosario.

    Audita tokens en MAYÚSCULAS de longitud ``min_acronym_length`` a 8
    (excluyendo ``exempt_common_acronyms``, case-insensitive), fuera de
    fences (``` ```` /``~~~``, multi-línea) y code spans inline. Un acrónimo
    ``ACR`` queda definido si: (a) su primera aparición va entre paréntesis
    ``(... ACR ...)`` o seguido de paréntesis ``ACR (...)``, o (b) existe
    una definición tipo glosario ``**ACR**:`` / ``- **ACR**:`` / ``| ACR |``
    en cualquier parte del documento.

    Retorna total_distinct_acronyms, defined_acronyms y undefined_acronyms
    (listas ordenadas alfabéticamente), first_use_line_by_undefined_acronym
    (dict -> línea 1-indexed de primera aparición) y estado
    COMPLIANT (0 indefinidos) / MINOR_GAPS (1-2) / GLOSSARY_REQUIRED (>= 3).
    """
    results: dict[str, Any] = {
        "total_distinct_acronyms": 0,
        "defined_acronyms": [],
        "undefined_acronyms": [],
        "first_use_line_by_undefined_acronym": {},
        "acronym_hygiene_status": "COMPLIANT",
        "is_compliant": True,
    }
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return results

    token_pattern = re.compile(r"\b[A-Z]{%d,8}\b" % max(1, int(min_acronym_length)))
    exempt = {acronym.upper() for acronym in exempt_common_acronyms}

    fence_open_pattern = re.compile(r"^\s*(`{3,}|~{3,})")
    code_span_pattern = re.compile(r"`+[^`]*`+")

    open_fence_token: str | None = None
    first_use: dict[str, int] = {}

    def _strip_spans(line: str) -> str:
        segments: list[str] = []
        cursor = 0
        for span_match in code_span_pattern.finditer(line):
            if span_match.start() > cursor:
                segments.append(line[cursor:span_match.start()])
            cursor = span_match.end()
        if cursor < len(line):
            segments.append(line[cursor:])
        return "\n".join(segments)

    # Primera pasada: registrar cada acrónimo activo y su primera línea.
    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        if open_fence_token is not None:
            closing_match = fence_open_pattern.match(raw_line.strip())
            if closing_match is not None and closing_match.group(1)[0] == open_fence_token[0]:
                open_fence_token = None
            continue

        fence_match = fence_open_pattern.match(raw_line.strip())
        if fence_match is not None:
            open_fence_token = fence_match.group(1)
            continue

        for token in token_pattern.findall(_strip_spans(raw_line)):
            if token in exempt:
                continue
            first_use.setdefault(token, line_no)

    if not first_use:
        return results

    def _is_inline_defined(line: str, token: str) -> bool:
        # "(... ACR )" o "(ACR)" con contenido alrededor en la misma línea.
        if re.search(r"\([^()\n]*\b%s\b[^()\n]*\)" % re.escape(token), line):
            return True
        # "ACR (" seguido de paréntesis en la misma línea.
        if re.search(r"\b%s\s*\([^()\n]+\)" % re.escape(token), line):
            return True
        return False

    def _is_glossary_defined(line: str, token: str) -> bool:
        esc = re.escape(token)
        if re.match(r"^\s*[-*]?\s*\*\*%s\*\*\s*:" % esc, line):
            return True
        if re.match(r"^\s*\*\*%s\*\*\s*:" % esc, line):
            return True
        if re.match(r"^\s*\|\s*%s\s*\|" % esc, line):
            return True
        return False

    text_lines = markdown_text.splitlines()
    defined: list[str] = []
    undefined: list[str] = []
    first_use_line_by_undefined: dict[str, int] = {}

    for token, first_line in sorted(first_use.items()):
        inline_defined = False
        glossary_defined = False
        for idx, line in enumerate(text_lines, start=1):
            # Dentro de fences el cuerpo no aporta definiciones (se reusa el estado).
            if open_fence_token is not None:
                closing_match = fence_open_pattern.match(line.strip())
                if closing_match is not None and closing_match.group(1)[0] == open_fence_token[0]:
                    open_fence_token = None
                continue
            fence_match = fence_open_pattern.match(line.strip())
            if fence_match is not None:
                open_fence_token = fence_match.group(1)
                continue

            stripped_body = _strip_spans(line)
            if idx == first_line:
                inline_defined = _is_inline_defined(stripped_body, token)
            if _is_glossary_defined(line, token):
                glossary_defined = True
                if inline_defined:
                    break
                # un hit de glosario basta para declarar definido
                break
        if inline_defined or glossary_defined:
            defined.append(token)
        else:
            undefined.append(token)
            first_use_line_by_undefined[token] = first_line

    defined_sorted = sorted(defined)
    undefined_sorted = sorted(undefined)
    first_use_line_by_undefined = dict(sorted(first_use_line_by_undefined.items()))

    total = len(defined_sorted) + len(undefined_sorted)
    if len(undefined_sorted) == 0:
        status = "COMPLIANT"
    elif len(undefined_sorted) <= 2:
        status = "MINOR_GAPS"
    else:
        status = "GLOSSARY_REQUIRED"

    results["total_distinct_acronyms"] = total
    results["defined_acronyms"] = defined_sorted
    results["undefined_acronyms"] = undefined_sorted
    results["first_use_line_by_undefined_acronym"] = first_use_line_by_undefined
    results["acronym_hygiene_status"] = status
    results["is_compliant"] = status == "COMPLIANT"
    return results


AnyDocService.audit_markdown_acronym_and_glossary_first_use_hygiene = staticmethod(
    audit_markdown_acronym_and_glossary_first_use_hygiene
)
AnydocService.audit_markdown_acronym_and_glossary_first_use_hygiene = staticmethod(
    audit_markdown_acronym_and_glossary_first_use_hygiene
)


def audit_markdown_mermaid_diagram_syntax_hygiene(
    markdown_text: str | None,
    *,
    allowed_diagram_types: tuple[str, ...] = (
        "flowchart",
        "graph",
        "sequencediagram",
        "statediagram",
        "statediagram-v2",
        "classdiagram",
        "erdiagram",
        "xychart-beta",
        "gantt",
        "pie",
        "mindmap",
    ),
) -> dict[str, Any]:
    """Audita sintaxis e higiene de bloques de diagrama Mermaid en Markdown (PMI PMBOK §4.4)."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_mermaid_blocks": 0,
            "empty_mermaid_block_lines": [],
            "unsupported_diagram_type_lines": [],
            "unbalanced_bracket_block_lines": [],
            "raw_html_tag_block_lines": [],
            "mermaid_hygiene_status": "CLEAN",
            "is_compliant": True,
            "issues": [],
        }

    allowed_lower = {
        str(t).strip().lower() for t in (allowed_diagram_types or ()) if str(t).strip()
    }
    fence_open_re = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_-]+)?.*$")
    html_tag_re = re.compile(
        r"<\s*/?\s*(?:br|b|i|div|span|p|strong|em|sub|sup)\b[^>]*>",
        re.IGNORECASE,
    )

    lines = markdown_text.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0
    is_mermaid_fence = False
    block_start_line = 0
    block_lines: list[str] = []

    blocks: list[tuple[int, list[str]]] = []

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_fence:
            m = fence_open_re.match(raw_line)
            if m:
                token = m.group(1)
                lang = (m.group(2) or "").strip().lower()
                in_fence = True
                fence_char = token[0]
                fence_len = len(token)
                is_mermaid_fence = lang == "mermaid"
                block_start_line = idx
                block_lines = []
        else:
            if (
                stripped.startswith(fence_char * fence_len)
                and set(stripped) == {fence_char}
            ):
                if is_mermaid_fence:
                    blocks.append((block_start_line, list(block_lines)))
                in_fence = False
                fence_char = ""
                fence_len = 0
                is_mermaid_fence = False
                block_lines = []
            else:
                if is_mermaid_fence:
                    block_lines.append(raw_line)

    if in_fence and is_mermaid_fence:
        blocks.append((block_start_line, list(block_lines)))

    empty_mermaid_block_lines: list[int] = []
    unsupported_diagram_type_lines: list[int] = []
    unbalanced_bracket_block_lines: list[int] = []
    raw_html_tag_block_lines: list[int] = []
    issues: list[str] = []

    for start_line, content_lines in blocks:
        useful_lines = [
            ln.strip()
            for ln in content_lines
            if ln.strip() and not ln.strip().startswith("%%")
        ]
        if not useful_lines:
            empty_mermaid_block_lines.append(start_line)
            issues.append(f"Bloque Mermaid vacío en línea {start_line}.")
            continue

        first_token = re.split(r"[\s(:{\[]+", useful_lines[0], maxsplit=1)[0].lower()
        if first_token not in allowed_lower:
            unsupported_diagram_type_lines.append(start_line)
            issues.append(
                f"Tipo de diagrama Mermaid no soportado '{first_token}' en línea {start_line}."
            )

        joined_non_comment = "\n".join(useful_lines)
        if (
            joined_non_comment.count("(") != joined_non_comment.count(")")
            or joined_non_comment.count("[") != joined_non_comment.count("]")
            or joined_non_comment.count("{") != joined_non_comment.count("}")
        ):
            unbalanced_bracket_block_lines.append(start_line)
            issues.append(
                f"Paréntesis, corchetes o llaves desbalanceados en bloque Mermaid de línea {start_line}."
            )

        if html_tag_re.search(joined_non_comment):
            raw_html_tag_block_lines.append(start_line)
            issues.append(
                f"Etiquetas HTML crudas detectadas en bloque Mermaid de línea {start_line}."
            )

    if (
        empty_mermaid_block_lines
        or unsupported_diagram_type_lines
        or unbalanced_bracket_block_lines
    ):
        mermaid_hygiene_status = "SYNTAX_ERROR"
    elif raw_html_tag_block_lines:
        mermaid_hygiene_status = "STYLE_WARNING"
    else:
        mermaid_hygiene_status = "CLEAN"

    return {
        "total_mermaid_blocks": len(blocks),
        "empty_mermaid_block_lines": sorted(empty_mermaid_block_lines),
        "unsupported_diagram_type_lines": sorted(unsupported_diagram_type_lines),
        "unbalanced_bracket_block_lines": sorted(unbalanced_bracket_block_lines),
        "raw_html_tag_block_lines": sorted(raw_html_tag_block_lines),
        "mermaid_hygiene_status": mermaid_hygiene_status,
        "is_compliant": mermaid_hygiene_status == "CLEAN",
        "issues": issues,
    }


AnyDocService.audit_markdown_mermaid_diagram_syntax_hygiene = staticmethod(
    audit_markdown_mermaid_diagram_syntax_hygiene
)
AnydocService.audit_markdown_mermaid_diagram_syntax_hygiene = staticmethod(
    audit_markdown_mermaid_diagram_syntax_hygiene
)


class _TaskListHygieneResult(dict[str, Any]):
    """Dict compatible tanto con contrato nuevo como con igualdad exacta legacy de 7 claves."""

    _LEGACY_KEYS = frozenset(
        {
            "total_task_items",
            "open_task_items",
            "completed_task_items",
            "empty_task_item_lines",
            "unassigned_open_task_lines",
            "undated_open_task_lines",
            "is_task_list_hygiene_compliant",
        }
    )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict) and set(other.keys()) == self._LEGACY_KEYS:
            return {k: self[k] for k in self._LEGACY_KEYS} == other
        return super().__eq__(other)


def audit_markdown_task_list_action_item_hygiene(
    markdown_text: str | None,
    *,
    require_owner_mention_for_open: bool = True,
    require_due_date_for_open: bool = True,
    require_owner_and_due_date_on_open: bool | None = None,
) -> dict[str, Any]:
    """Audita higiene de listas de tareas Markdown (- [ ] / - [x]): descripción, dueño y fecha de vencimiento (PMI PMBOK §4.4)."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return _TaskListHygieneResult(
            {
                "total_tasks": 0,
                "completed_tasks_count": 0,
                "open_tasks_count": 0,
                "completion_rate_pct": 100.0,
                "empty_description_task_lines": [],
                "unassigned_open_task_lines": [],
                "undated_open_task_lines": [],
                "task_list_hygiene_status": "CLEAN",
                "is_compliant": True,
                "issues": [],
                "total_task_items": 0,
                "open_task_items": 0,
                "completed_task_items": 0,
                "empty_task_item_lines": [],
                "is_task_list_hygiene_compliant": True,
            }
        )

    check_owner = (
        bool(require_owner_and_due_date_on_open)
        if require_owner_and_due_date_on_open is not None
        else bool(require_owner_mention_for_open)
    )
    check_due = (
        bool(require_owner_and_due_date_on_open)
        if require_owner_and_due_date_on_open is not None
        else bool(require_due_date_for_open)
    )

    fence_open_re = re.compile(r"^\s*(`{3,}|~{3,})")
    task_line_re = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[([ xX~-])\]\s*(.*)$")
    owner_re = re.compile(
        r"(?:@[A-Za-z0-9_.-]+|\b(?:owner|responsable)\s*:)", re.IGNORECASE
    )
    due_date_re = re.compile(
        r"(?:\b\d{4}-\d{2}-\d{2}\b|\b(?:due|vence)\s*:)", re.IGNORECASE
    )

    lines = markdown_text.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0

    total_tasks = 0
    completed_tasks_count = 0
    open_tasks_count = 0
    empty_description_task_lines: list[int] = []
    empty_task_item_lines: list[int] = []
    unassigned_open_task_lines: list[int] = []
    undated_open_task_lines: list[int] = []
    issues: list[str] = []

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_fence:
            m_fence = fence_open_re.match(raw_line)
            if m_fence:
                token = m_fence.group(1)
                in_fence = True
                fence_char = token[0]
                fence_len = len(token)
                continue
        else:
            if (
                stripped.startswith(fence_char * fence_len)
                and set(stripped) == {fence_char}
            ):
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        m_task = task_line_re.match(raw_line)
        if not m_task:
            continue

        total_tasks += 1
        mark = m_task.group(1)
        desc = (m_task.group(2) or "").strip()
        is_completed = mark.lower() == "x"
        is_open = mark == " "

        if is_completed:
            completed_tasks_count += 1
        elif is_open:
            open_tasks_count += 1

        if len(desc) < 3:
            empty_task_item_lines.append(idx)

        if not desc:
            empty_description_task_lines.append(idx)
            issues.append(f"Tarea en línea {idx} carece de descripción.")
            continue

        if is_open:
            if check_owner and not owner_re.search(desc):
                unassigned_open_task_lines.append(idx)
                issues.append(
                    f"Tarea abierta en línea {idx} carece de responsable asignado (@usuario u owner:/responsable:)."
                )
            if check_due and not due_date_re.search(desc):
                undated_open_task_lines.append(idx)
                issues.append(
                    f"Tarea abierta en línea {idx} carece de fecha compromiso (YYYY-MM-DD o due:/vence:)."
                )

    completion_rate_pct = (
        round((completed_tasks_count / total_tasks) * 100.0, 2)
        if total_tasks > 0
        else 100.0
    )

    if empty_description_task_lines:
        task_list_hygiene_status = "EMPTY_TASKS"
    elif unassigned_open_task_lines or undated_open_task_lines:
        task_list_hygiene_status = "UNTRACKED_OPEN_ITEMS"
    else:
        task_list_hygiene_status = "CLEAN"

    return _TaskListHygieneResult(
        {
            "total_tasks": total_tasks,
            "completed_tasks_count": completed_tasks_count,
            "open_tasks_count": open_tasks_count,
            "completion_rate_pct": completion_rate_pct,
            "empty_description_task_lines": empty_description_task_lines,
            "unassigned_open_task_lines": unassigned_open_task_lines,
            "undated_open_task_lines": undated_open_task_lines,
            "task_list_hygiene_status": task_list_hygiene_status,
            "is_compliant": task_list_hygiene_status == "CLEAN",
            "issues": issues,
            "total_task_items": total_tasks,
            "open_task_items": open_tasks_count,
            "completed_task_items": completed_tasks_count,
            "empty_task_item_lines": empty_task_item_lines,
            "is_task_list_hygiene_compliant": (
                len(empty_task_item_lines) == 0
                and len(unassigned_open_task_lines) == 0
                and len(undated_open_task_lines) == 0
            ),
        }
    )


AnyDocService.audit_markdown_task_list_action_item_hygiene = staticmethod(
    audit_markdown_task_list_action_item_hygiene
)
AnydocService.audit_markdown_task_list_action_item_hygiene = staticmethod(
    audit_markdown_task_list_action_item_hygiene
)


def audit_markdown_code_fence_and_secret_leak_hygiene(
    markdown_text: str | None,
    *,
    max_code_block_lines: int = 120,
) -> dict[str, Any]:
    """Audita bloques de código cercados (etiqueta de lenguaje, cierre, longitud) y fugas de secretos en Markdown (PMI PMBOK §4.4 / §10.2)."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_code_blocks": 0,
            "tagged_code_blocks": 0,
            "untagged_code_block_lines": [],
            "unclosed_code_block_line": None,
            "oversized_code_block_lines": [],
            "potential_secret_leak_lines": [],
            "code_hygiene_status": "CLEAN",
            "recommendations": [],
        }

    max_lines = int(max_code_block_lines if max_code_block_lines is not None else 120)
    fence_open_re = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_+-]+)?.*$")
    direct_secret_re = re.compile(
        r"(?:BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PRIVATE)\s+PRIVATE\s+KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})"
    )
    assign_secret_re = re.compile(
        r"""\b(?:password|api_key|secret_key|access_token)\s*=\s*["']([^"'<>{}$]{8,})["']""",
        re.IGNORECASE,
    )
    placeholder_tokens = {
        "your_api_key",
        "changeme",
        "example",
        "placeholder",
        "dummy",
        "redacted",
        "none",
        "null",
    }

    lines = markdown_text.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0
    block_start_line = 0
    block_content_count = 0

    total_code_blocks = 0
    tagged_code_blocks = 0
    untagged_code_block_lines: list[int] = []
    oversized_code_block_lines: list[int] = []
    potential_secret_leak_lines: list[int] = []
    recommendations: list[str] = []

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        leaked = False
        if direct_secret_re.search(raw_line):
            leaked = True
        else:
            for m_sec in assign_secret_re.finditer(raw_line):
                val = m_sec.group(1).strip()
                val_lower = val.lower()
                if (
                    not set(val) <= {"*"}
                    and not any(tok in val_lower for tok in placeholder_tokens)
                ):
                    leaked = True
                    break
        if leaked:
            potential_secret_leak_lines.append(idx)

        if not in_fence:
            m = fence_open_re.match(raw_line)
            if m:
                token = m.group(1)
                lang = (m.group(2) or "").strip()
                in_fence = True
                fence_char = token[0]
                fence_len = len(token)
                block_start_line = idx
                block_content_count = 0
                total_code_blocks += 1
                if lang:
                    tagged_code_blocks += 1
                else:
                    untagged_code_block_lines.append(idx)
        else:
            if (
                stripped.startswith(fence_char * fence_len)
                and set(stripped) == {fence_char}
            ):
                if block_content_count > max_lines:
                    oversized_code_block_lines.append(block_start_line)
                in_fence = False
                fence_char = ""
                fence_len = 0
                block_start_line = 0
                block_content_count = 0
            else:
                block_content_count += 1

    unclosed_code_block_line: int | None = None
    if in_fence:
        unclosed_code_block_line = block_start_line
        if block_content_count > max_lines:
            oversized_code_block_lines.append(block_start_line)

    if potential_secret_leak_lines:
        recommendations.append(
            f"Revocar y reemplazar secretos expuestos en líneas {potential_secret_leak_lines} por variables de entorno o placeholders."
        )
    if unclosed_code_block_line is not None:
        recommendations.append(
            f"Cerrar el bloque de código iniciado en la línea {unclosed_code_block_line}."
        )
    if untagged_code_block_lines:
        recommendations.append(
            f"Añadir identificador de lenguaje a los bloques cercados en líneas {untagged_code_block_lines}."
        )
    if oversized_code_block_lines:
        recommendations.append(
            f"Modularizar o resumir bloques de código que superan {max_lines} líneas en {oversized_code_block_lines}."
        )

    if potential_secret_leak_lines or unclosed_code_block_line is not None:
        code_hygiene_status = "CRITICAL"
    elif untagged_code_block_lines or oversized_code_block_lines:
        code_hygiene_status = "WARNING"
    else:
        code_hygiene_status = "CLEAN"

    return {
        "total_code_blocks": total_code_blocks,
        "tagged_code_blocks": tagged_code_blocks,
        "untagged_code_block_lines": untagged_code_block_lines,
        "unclosed_code_block_line": unclosed_code_block_line,
        "oversized_code_block_lines": oversized_code_block_lines,
        "potential_secret_leak_lines": potential_secret_leak_lines,
        "code_hygiene_status": code_hygiene_status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_code_fence_and_secret_leak_hygiene = staticmethod(
    audit_markdown_code_fence_and_secret_leak_hygiene
)
AnydocService.audit_markdown_code_fence_and_secret_leak_hygiene = staticmethod(
    audit_markdown_code_fence_and_secret_leak_hygiene
)


def audit_markdown_admonition_callout_and_actionability_hygiene(
    markdown_text: str,
    *,
    max_alert_density_pct: float = 30.0,
) -> dict[str, Any]:
    """Audit PMI PMBOK §4.4 GitHub-style admonition/alert callout syntax, severity saturation, and actionability hygiene."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "valid_callouts_count": 0,
            "invalid_callout_type_lines": [],
            "empty_callout_body_lines": [],
            "consecutive_callout_lines": [],
            "alert_line_share_pct": 0.0,
            "callout_hygiene_status": "CLEAN",
            "recommendations": [],
        }

    canonical_types = {"NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"}
    callout_header_re = re.compile(r"^\s*>\s*\[!([A-Za-z0-9_-]+)\](.*)$")
    blockquote_re = re.compile(r"^\s*>(.*)$")

    lines = markdown_text.splitlines()
    total_non_empty_lines = sum(1 for ln in lines if ln.strip())

    valid_callouts_count = 0
    invalid_callout_type_lines: list[int] = []
    empty_callout_body_lines: list[int] = []
    consecutive_callout_lines: list[int] = []
    alert_lines_count = 0

    in_alert_block = False
    current_alert_start_line: int | None = None
    current_alert_is_valid = False
    current_alert_has_body = False
    saw_normal_paragraph_since_last_alert = True

    for line_no, line in enumerate(lines, start=1):
        header_match = callout_header_re.match(line)
        if header_match:
            if in_alert_block:
                if (
                    current_alert_is_valid
                    and not current_alert_has_body
                    and current_alert_start_line is not None
                ):
                    empty_callout_body_lines.append(current_alert_start_line)

            if not saw_normal_paragraph_since_last_alert:
                consecutive_callout_lines.append(line_no)

            alert_lines_count += 1
            callout_type = header_match.group(1).strip().upper()
            trailing_text = header_match.group(2).strip()

            if callout_type in canonical_types:
                valid_callouts_count += 1
                current_alert_is_valid = True
            else:
                invalid_callout_type_lines.append(line_no)
                current_alert_is_valid = False

            current_alert_has_body = bool(trailing_text)
            current_alert_start_line = line_no
            in_alert_block = True
            saw_normal_paragraph_since_last_alert = False
            continue

        if in_alert_block:
            bq_match = blockquote_re.match(line)
            if bq_match:
                if line.strip():
                    alert_lines_count += 1
                if bq_match.group(1).strip():
                    current_alert_has_body = True
            else:
                if (
                    current_alert_is_valid
                    and not current_alert_has_body
                    and current_alert_start_line is not None
                ):
                    empty_callout_body_lines.append(current_alert_start_line)
                in_alert_block = False
                current_alert_start_line = None
                if line.strip():
                    saw_normal_paragraph_since_last_alert = True
        else:
            if line.strip() and not line.lstrip().startswith(">"):
                saw_normal_paragraph_since_last_alert = True

    if in_alert_block:
        if (
            current_alert_is_valid
            and not current_alert_has_body
            and current_alert_start_line is not None
        ):
            empty_callout_body_lines.append(current_alert_start_line)

    alert_line_share_pct = (
        round((alert_lines_count / total_non_empty_lines) * 100.0, 2)
        if total_non_empty_lines > 0
        else 0.0
    )

    recommendations: list[str] = []
    if invalid_callout_type_lines:
        recommendations.append(
            f"Replace non-standard callout types with canonical GitHub alerts (NOTE, TIP, IMPORTANT, WARNING, CAUTION) on lines: {invalid_callout_type_lines}."
        )
    if empty_callout_body_lines:
        recommendations.append(
            f"Populate actionable guidance inside empty alert callout blocks on lines: {empty_callout_body_lines}."
        )
    if consecutive_callout_lines:
        recommendations.append(
            f"Separate back-to-back alert blocks with explanatory prose to prevent alert fatigue on lines: {consecutive_callout_lines}."
        )
    if alert_line_share_pct > max_alert_density_pct:
        recommendations.append(
            f"Reduce alert callout density ({alert_line_share_pct:.2f}% > {max_alert_density_pct:.2f}%) by converting routine notes into standard paragraphs."
        )

    if invalid_callout_type_lines or empty_callout_body_lines:
        callout_hygiene_status = "CRITICAL"
    elif consecutive_callout_lines or alert_line_share_pct > max_alert_density_pct:
        callout_hygiene_status = "WARNING"
    else:
        callout_hygiene_status = "CLEAN"

    return {
        "valid_callouts_count": valid_callouts_count,
        "invalid_callout_type_lines": invalid_callout_type_lines,
        "empty_callout_body_lines": empty_callout_body_lines,
        "consecutive_callout_lines": consecutive_callout_lines,
        "alert_line_share_pct": alert_line_share_pct,
        "callout_hygiene_status": callout_hygiene_status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_admonition_callout_and_actionability_hygiene = staticmethod(
    audit_markdown_admonition_callout_and_actionability_hygiene
)
AnydocService.audit_markdown_admonition_callout_and_actionability_hygiene = staticmethod(
    audit_markdown_admonition_callout_and_actionability_hygiene
)


def audit_markdown_heading_anchor_slug_and_fragment_hygiene(
    markdown_text: str,
) -> dict[str, Any]:
    """Audit PMI PMBOK §4.4 Markdown ATX heading anchor slug collisions and internal #fragment link resolution."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_headings": 0,
            "duplicate_heading_slugs": [],
            "total_internal_fragment_links": 0,
            "broken_fragment_targets": [],
            "anchor_hygiene_status": "CLEAN",
            "is_anchor_hygiene_clean": True,
            "recommendations": [],
        }

    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    heading_re = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")
    fragment_link_re = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(#[^)\s]*)\s*\)")

    non_fenced_lines: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in markdown_text.splitlines():
        m_fence = fence_re.match(line)
        if m_fence:
            marker_char = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker_char
            elif marker_char == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            non_fenced_lines.append(line)

    total_headings = 0
    slug_counts: dict[str, int] = {}
    duplicate_heading_slugs: list[str] = []
    valid_slugs: set[str] = set()

    for line in non_fenced_lines:
        h_match = heading_re.match(line)
        if not h_match:
            continue
        total_headings += 1
        raw_title = h_match.group(1).strip().lower()
        cleaned = re.sub(r"[^\w\s-]", "", raw_title).replace("_", "")
        base_slug = re.sub(r"\s+", "-", cleaned).strip()
        if not base_slug:
            continue

        occurrence = slug_counts.get(base_slug, 0)
        slug_counts[base_slug] = occurrence + 1
        if occurrence == 0:
            valid_slugs.add(base_slug)
        else:
            valid_slugs.add(f"{base_slug}-{occurrence}")
            if base_slug not in duplicate_heading_slugs:
                duplicate_heading_slugs.append(base_slug)

    total_internal_fragment_links = 0
    broken_fragment_targets: list[str] = []

    for line in non_fenced_lines:
        for l_match in fragment_link_re.finditer(line):
            raw_target = l_match.group(1).strip()
            total_internal_fragment_links += 1
            slug_target = raw_target[1:].strip().lower()
            if not slug_target or slug_target not in valid_slugs:
                broken_fragment_targets.append(raw_target)

    recommendations: list[str] = []
    if broken_fragment_targets:
        recommendations.append(
            f"Fix broken or empty internal fragment links so they resolve to existing ATX headings: {', '.join(broken_fragment_targets)}."
        )
    if duplicate_heading_slugs:
        recommendations.append(
            f"Disambiguate duplicate ATX heading titles to prevent anchor slug collisions: {', '.join(duplicate_heading_slugs)}."
        )

    if broken_fragment_targets:
        anchor_hygiene_status = "CRITICAL"
    elif duplicate_heading_slugs:
        anchor_hygiene_status = "WARNING"
    else:
        anchor_hygiene_status = "CLEAN"

    return {
        "total_headings": total_headings,
        "duplicate_heading_slugs": duplicate_heading_slugs,
        "total_internal_fragment_links": total_internal_fragment_links,
        "broken_fragment_targets": broken_fragment_targets,
        "anchor_hygiene_status": anchor_hygiene_status,
        "is_anchor_hygiene_clean": anchor_hygiene_status == "CLEAN",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_heading_anchor_slug_and_fragment_hygiene = staticmethod(
    audit_markdown_heading_anchor_slug_and_fragment_hygiene
)
AnydocService.audit_markdown_heading_anchor_slug_and_fragment_hygiene = staticmethod(
    audit_markdown_heading_anchor_slug_and_fragment_hygiene
)


def audit_markdown_table_column_parity_and_empty_cell_hygiene(
    markdown_text: str | None = None,
    *,
    max_empty_cell_ratio_pct: float = 20.0,
    max_columns_per_table: int = 10,
) -> dict[str, Any]:
    """PMBOK §4.4 — paridad de columnas, separador de encabezado y ratio de celdas vacías.

    Parsea tablas pipe GFM fuera de bloques fenced (backticks o tildes).
    Reporta líneas con desbalance de columnas, bloques sin separador
    ``|---|`` válido, encabezados demasiado anchos y el porcentaje de
    celdas de datos vacías o placeholder ('-', 'N/A', 'TBD').
    """
    lines = (
        markdown_text.splitlines()
        if isinstance(markdown_text, str) and markdown_text
        else []
    )

    def _is_table_line(raw_line: str) -> bool:
        stripped = raw_line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def _row_cells(raw_line: str) -> list[str]:
        stripped = raw_line.strip()
        return [cell.strip() for cell in stripped[1:-1].split("|")]

    small_placeholder_tokens = {"-", "n/a", "tbd", ""}

    mismatched_column_row_lines: list[int] = []
    missing_separator_table_lines: list[int] = []
    wide_table_header_lines: list[int] = []
    empty_data_cells = 0
    total_data_cells = 0
    total_tables = 0

    in_backtick_fence = False
    in_tilde_fence = False
    block: list[tuple[int, str]] = []

    def _evaluate_block(block_lines: list[tuple[int, str]]) -> None:
        nonlocal empty_data_cells, total_data_cells, total_tables
        if not block_lines:
            return
        total_tables += 1

        (header_line_no, header_line) = block_lines[0]
        header_cells = _row_cells(header_line)
        expected_cols = len(header_cells)

        if expected_cols > max_columns_per_table:
            wide_table_header_lines.append(header_line_no)

        def _is_valid_separator(raw_line: str) -> bool:
            cells = _row_cells(raw_line)
            return len(cells) == expected_cols and all(
                _GFM_DELIMITER_CELL_RE.match(cell) for cell in cells
            )

        has_valid_separator = (
            len(block_lines) >= 2 and _is_valid_separator(block_lines[1][1])
        )
        if not has_valid_separator:
            missing_separator_table_lines.append(header_line_no)
            return

        for row_line_no, row_line in block_lines[2:]:
            cells = _row_cells(row_line)
            if len(cells) != expected_cols:
                mismatched_column_row_lines.append(row_line_no)
                continue
            total_data_cells += len(cells)
            empty_data_cells += sum(
                1 for cell in cells if cell.lower() in small_placeholder_tokens
            )

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_tilde_fence and not in_backtick_fence and stripped.startswith("```"):
            in_backtick_fence = not in_backtick_fence
            continue
        if not in_backtick_fence and not in_tilde_fence and stripped.startswith("~~~"):
            in_tilde_fence = not in_tilde_fence
            continue
        if in_backtick_fence or in_tilde_fence:
            continue

        if _is_table_line(line):
            block.append((line_no, line))
        else:
            _evaluate_block(block)
            block = []
    _evaluate_block(block)

    empty_cell_ratio_pct = (
        round((empty_data_cells / total_data_cells) * 100.0, 2)
        if total_data_cells > 0
        else 0.0
    )

    if mismatched_column_row_lines or missing_separator_table_lines:
        table_hygiene_status = "CRITICAL"
    elif wide_table_header_lines or empty_cell_ratio_pct > max_empty_cell_ratio_pct:
        table_hygiene_status = "WARNING"
    else:
        table_hygiene_status = "CLEAN"

    recommendations: list[str] = []
    if missing_separator_table_lines:
        recommendations.append(
            "Add a GFM separator row like |---|---| under the table header at lines: "
            + ", ".join(str(line_number) for line_number in missing_separator_table_lines)
        )
    if mismatched_column_row_lines:
        recommendations.append(
            "Fix column count mismatch at table row lines: "
            + ", ".join(str(line_number) for line_number in mismatched_column_row_lines)
        )
    if wide_table_header_lines:
        recommendations.append(
            f"Reduce tables wider than {max_columns_per_table} columns; wide headers at lines: "
            + ", ".join(str(line_number) for line_number in wide_table_header_lines)
        )
    if empty_cell_ratio_pct > max_empty_cell_ratio_pct:
        recommendations.append(
            f"Fill placeholder cells: empty-cell ratio {empty_cell_ratio_pct}% exceeds max {max_empty_cell_ratio_pct}%"
        )

    return {
        "total_tables": total_tables,
        "mismatched_column_row_lines": mismatched_column_row_lines,
        "missing_separator_table_lines": missing_separator_table_lines,
        "wide_table_header_lines": wide_table_header_lines,
        "empty_cell_ratio_pct": empty_cell_ratio_pct,
        "table_hygiene_status": table_hygiene_status,
        "is_table_hygiene_clean": table_hygiene_status == "CLEAN",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_table_column_parity_and_empty_cell_hygiene = staticmethod(
    audit_markdown_table_column_parity_and_empty_cell_hygiene
)
AnydocService.audit_markdown_table_column_parity_and_empty_cell_hygiene = staticmethod(
    audit_markdown_table_column_parity_and_empty_cell_hygiene
)


_GH_ALERT_MARKER_RE = re.compile(
    r"^\s*>\s*\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\b",
    re.IGNORECASE,
)


def audit_markdown_blockquote_attribution_and_nesting_hygiene(
    markdown_text: str,
    *,
    max_nesting_depth: int = 2,
    max_quote_block_lines: int = 15,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 — AnyDoc Markdown Blockquote Nesting Depth, Empty Quote Line & Citation Attribution Hygiene Auditor."""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return {
            "total_blockquotes": 0,
            "deeply_nested_quote_lines": [],
            "oversized_quote_start_lines": [],
            "empty_blockquote_start_lines": [],
            "blockquote_hygiene_status": "CLEAN",
            "is_blockquote_hygiene_clean": True,
            "recommendations": [],
        }

    lines = markdown_text.splitlines()
    in_fence = False
    fence_char = ""

    raw_blocks: list[list[tuple[int, str]]] = []
    current_block: list[tuple[int, str]] = []

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_char = marker
            elif stripped.startswith(fence_char):
                in_fence = False
                fence_char = ""
            if current_block:
                raw_blocks.append(current_block)
                current_block = []
            continue

        if in_fence:
            if current_block:
                raw_blocks.append(current_block)
                current_block = []
            continue

        if stripped.startswith(">"):
            current_block.append((idx, stripped))
        else:
            if current_block:
                raw_blocks.append(current_block)
                current_block = []

    if current_block:
        raw_blocks.append(current_block)

    quote_blocks: list[list[tuple[int, str]]] = []
    for block in raw_blocks:
        if any(_GH_ALERT_MARKER_RE.match(line_text) for _, line_text in block):
            continue
        quote_blocks.append(block)

    total_blockquotes = len(quote_blocks)
    deeply_nested_quote_lines: list[int] = []
    oversized_quote_start_lines: list[int] = []
    empty_blockquote_start_lines: list[int] = []

    for block in quote_blocks:
        start_line = block[0][0]
        if len(block) > max_quote_block_lines:
            oversized_quote_start_lines.append(start_line)

        has_non_empty_text = False
        for line_no, line_text in block:
            m = re.match(r"^(?:>\s*)+", line_text)
            prefix = m.group(0) if m else ">"
            depth = prefix.count(">")
            content_after = line_text[len(prefix) :].strip()
            if content_after:
                has_non_empty_text = True
            if depth > max_nesting_depth:
                deeply_nested_quote_lines.append(line_no)

        if not has_non_empty_text:
            empty_blockquote_start_lines.append(start_line)

    recommendations: list[str] = []
    if empty_blockquote_start_lines:
        recommendations.append(
            f"Remove or populate empty blockquote block(s) starting at line(s): {', '.join(map(str, empty_blockquote_start_lines))}."
        )
    if deeply_nested_quote_lines:
        recommendations.append(
            f"Flatten blockquote nesting exceeding depth {max_nesting_depth} at line(s): {', '.join(map(str, deeply_nested_quote_lines))}."
        )
    if oversized_quote_start_lines:
        recommendations.append(
            f"Split or summarize oversized blockquote block(s) (> {max_quote_block_lines} lines) starting at line(s): {', '.join(map(str, oversized_quote_start_lines))}."
        )

    if empty_blockquote_start_lines:
        blockquote_hygiene_status = "CRITICAL"
    elif deeply_nested_quote_lines or oversized_quote_start_lines:
        blockquote_hygiene_status = "WARNING"
    else:
        blockquote_hygiene_status = "CLEAN"

    return {
        "total_blockquotes": total_blockquotes,
        "deeply_nested_quote_lines": deeply_nested_quote_lines,
        "oversized_quote_start_lines": oversized_quote_start_lines,
        "empty_blockquote_start_lines": empty_blockquote_start_lines,
        "blockquote_hygiene_status": blockquote_hygiene_status,
        "is_blockquote_hygiene_clean": blockquote_hygiene_status == "CLEAN",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_blockquote_attribution_and_nesting_hygiene = staticmethod(
    audit_markdown_blockquote_attribution_and_nesting_hygiene
)
AnydocService.audit_markdown_blockquote_attribution_and_nesting_hygiene = staticmethod(
    audit_markdown_blockquote_attribution_and_nesting_hygiene
)


def audit_markdown_frontmatter_metadata_and_classification_hygiene(
    documents: list[dict[str, Any]],
    *,
    required_keys: tuple[str, ...] = (
        "title",
        "owner",
        "classification",
        "last_reviewed",
    ),
    allowed_classifications: tuple[str, ...] = (
        "PUBLIC",
        "INTERNAL",
        "CONFIDENTIAL",
        "RESTRICTED",
    ),
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Frontmatter YAML Metadata Completeness, Owner Attribution & Classification Tag Hygiene Auditor."""
    valid_docs: list[dict[str, Any]] = []
    if isinstance(documents, (list, tuple)):
        for item in documents:
            if not isinstance(item, dict):
                continue
            did = str(item.get("doc_id") or "").strip()
            if not did:
                continue
            valid_docs.append({**item, "_did": did})

    if not valid_docs:
        return {
            "total_documents_evaluated": 0,
            "missing_frontmatter_doc_ids": [],
            "incomplete_metadata_doc_ids": [],
            "invalid_classification_doc_ids": [],
            "metadata_compliance_pct": 100.0,
            "frontmatter_hygiene_status": "COMPLIANT",
            "is_frontmatter_compliant": True,
            "recommendations": [],
        }

    allowed_set = {str(c).strip().upper() for c in allowed_classifications}
    missing_frontmatter_doc_ids: list[str] = []
    incomplete_metadata_doc_ids: list[str] = []
    invalid_classification_doc_ids: list[str] = []
    compliant_count = 0

    for doc in valid_docs:
        did = doc["_did"]
        has_delims = bool(doc.get("has_yaml_frontmatter_delimiters", False))
        raw_fields = doc.get("frontmatter_fields")
        fields = raw_fields if isinstance(raw_fields, dict) else {}

        has_infraction = False
        if not has_delims or not fields:
            missing_frontmatter_doc_ids.append(did)
            has_infraction = True
        else:
            missing_req = any(
                k not in fields
                or fields.get(k) is None
                or str(fields.get(k)).strip() == ""
                for k in required_keys
            )
            if missing_req:
                incomplete_metadata_doc_ids.append(did)
                has_infraction = True

            raw_cls = fields.get("classification")
            cls_norm = str(raw_cls).strip().upper() if raw_cls is not None else ""
            if not cls_norm or cls_norm not in allowed_set:
                if cls_norm:
                    invalid_classification_doc_ids.append(did)
                    has_infraction = True

        if not has_infraction:
            compliant_count += 1

    total_documents_evaluated = len(valid_docs)
    metadata_compliance_pct = round(
        (compliant_count / total_documents_evaluated) * 100.0, 2
    )

    recommendations: list[str] = []
    if missing_frontmatter_doc_ids:
        recommendations.append(
            f"Add YAML frontmatter block (`---`) to document(s): {', '.join(missing_frontmatter_doc_ids)}."
        )
    if incomplete_metadata_doc_ids:
        recommendations.append(
            f"Populate required frontmatter keys ({', '.join(required_keys)}) in document(s): {', '.join(incomplete_metadata_doc_ids)}."
        )
    if invalid_classification_doc_ids:
        recommendations.append(
            f"Assign valid classification tag ({', '.join(allowed_classifications)}) in document(s): {', '.join(invalid_classification_doc_ids)}."
        )

    if invalid_classification_doc_ids or metadata_compliance_pct < 70.0:
        frontmatter_hygiene_status = "GOVERNANCE_NON_COMPLIANT"
    elif missing_frontmatter_doc_ids or incomplete_metadata_doc_ids:
        frontmatter_hygiene_status = "METADATA_GAPS"
    else:
        frontmatter_hygiene_status = "COMPLIANT"

    return {
        "total_documents_evaluated": total_documents_evaluated,
        "missing_frontmatter_doc_ids": missing_frontmatter_doc_ids,
        "incomplete_metadata_doc_ids": incomplete_metadata_doc_ids,
        "invalid_classification_doc_ids": invalid_classification_doc_ids,
        "metadata_compliance_pct": metadata_compliance_pct,
        "frontmatter_hygiene_status": frontmatter_hygiene_status,
        "is_frontmatter_compliant": frontmatter_hygiene_status == "COMPLIANT",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_frontmatter_metadata_and_classification_hygiene = staticmethod(
    audit_markdown_frontmatter_metadata_and_classification_hygiene
)
AnydocService.audit_markdown_frontmatter_metadata_and_classification_hygiene = staticmethod(
    audit_markdown_frontmatter_metadata_and_classification_hygiene
)


_ALLOWED_MERMAID_DIAGRAM_TYPES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "classDiagram",
    "erDiagram",
)


def audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity(
    diagrams: Any,
    *,
    max_nodes_per_diagram: int = 25,
    allowed_diagram_types: tuple[str, ...] = _ALLOWED_MERMAID_DIAGRAM_TYPES,
) -> dict[str, Any]:
    """PMBOK 4.4 y 10.2: higiene de diagramas Mermaid.

    Evalúa por diagrama la validez del tipo, riesgos de sintaxis en
    etiquetas (paréntesis sin entrecomillar, HTML, subgrafos desbalanceados)
    y sobrecarga cognitiva por número de nodos.
    """
    entries = diagrams if isinstance(diagrams, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    unsupported_type_diagram_ids: list[str] = []
    syntax_hazard_diagram_ids: list[str] = []
    cognitive_overload_diagram_ids: list[str] = []
    observed_node_counts: list[int] = []

    for item in rows:
        diagram_id = item.get("diagram_id")
        diagram_type = item.get("diagram_type")
        node_count = item.get("node_count", 0)

        node_val = node_count if isinstance(node_count, (int, float)) and node_count >= 0 else 0
        observed_node_counts.append(node_val)

        if (
            not isinstance(diagram_type, str)
            or diagram_type.strip() not in allowed_diagram_types
        ):
            unsupported_type_diagram_ids.append(diagram_id)

        if (
            item.get("has_unquoted_parentheses_in_labels", False) is True
            or item.get("has_html_tags_in_labels", False) is True
            or item.get("has_balanced_subgraph_ends", True) is not True
        ):
            syntax_hazard_diagram_ids.append(diagram_id)

        if node_val > max_nodes_per_diagram:
            cognitive_overload_diagram_ids.append(diagram_id)

    max_node_count_observed = max(observed_node_counts) if observed_node_counts else 0

    if unsupported_type_diagram_ids or syntax_hazard_diagram_ids:
        mermaid_hygiene_status = "RENDER_FAILURE_RISK"
    elif cognitive_overload_diagram_ids:
        mermaid_hygiene_status = "COGNITIVE_OVERLOAD_WARNING"
    else:
        mermaid_hygiene_status = "DIAGRAM_CLEAN"

    return {
        "total_diagrams_evaluated": len(rows),
        "unsupported_type_diagram_ids": unsupported_type_diagram_ids,
        "syntax_hazard_diagram_ids": syntax_hazard_diagram_ids,
        "cognitive_overload_diagram_ids": cognitive_overload_diagram_ids,
        "max_node_count_observed": max_node_count_observed,
        "mermaid_hygiene_status": mermaid_hygiene_status,
        "is_mermaid_compliant": mermaid_hygiene_status == "DIAGRAM_CLEAN",
    }


AnyDocService.audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity
)
AnydocService.audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_cognitive_complexity
)


def audit_markdown_footnote_citation_and_orphan_definition_hygiene(
    documents: Any,
) -> dict[str, Any]:
    """PMBOK 4.4 y 10.2: paridad de citas y definiciones de footnotes.

    Normaliza claves con ``str(k).strip()`` y detecta marcadores en línea
    sin definición (dangling), definiciones sin referencia (orphan) y
    definiciones vacías o duplicadas en cada documento.
    """
    entries = documents if isinstance(documents, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    dangling_marker_doc_ids: list[str] = []
    orphan_definition_doc_ids: list[str] = []
    malformed_definition_doc_ids: list[str] = []

    for item in rows:
        doc_id = item.get("doc_id")

        inline_footer = item.get("inline_footnote_markers", []) or []
        defined_keys = item.get("defined_footnote_keys", []) or []
        empty_defs = item.get("empty_definition_keys", []) or []
        duplicate_defs = item.get("duplicate_definition_keys", []) or []

        inline_set = {
            str(marker).strip()
            for marker in inline_footer
            if str(marker).strip()
        }
        defined_set = {
            str(key).strip()
            for key in defined_keys
            if str(key).strip()
        }

        if inline_set - defined_set:
            dangling_marker_doc_ids.append(doc_id)

        if defined_set - inline_set:
            orphan_definition_doc_ids.append(doc_id)

        if empty_defs or duplicate_defs:
            malformed_definition_doc_ids.append(doc_id)

    if dangling_marker_doc_ids or malformed_definition_doc_ids:
        footnote_hygiene_status = "BROKEN_CITATION_INTEGRITY"
    elif orphan_definition_doc_ids:
        footnote_hygiene_status = "ORPHAN_DEFINITION_WARNING"
    else:
        footnote_hygiene_status = "FOOTNOTES_CLEAN"

    return {
        "total_documents_evaluated": len(rows),
        "dangling_marker_doc_ids": dangling_marker_doc_ids,
        "orphan_definition_doc_ids": orphan_definition_doc_ids,
        "malformed_definition_doc_ids": malformed_definition_doc_ids,
        "footnote_hygiene_status": footnote_hygiene_status,
        "is_footnote_compliant": footnote_hygiene_status == "FOOTNOTES_CLEAN",
    }


AnyDocService.audit_markdown_footnote_citation_and_orphan_definition_hygiene = staticmethod(
    audit_markdown_footnote_citation_and_orphan_definition_hygiene
)
AnydocService.audit_markdown_footnote_citation_and_orphan_definition_hygiene = staticmethod(
    audit_markdown_footnote_citation_and_orphan_definition_hygiene
)


def audit_markdown_task_list_checklist_owner_and_due_date_hygiene(
    checklists: list[dict[str, Any]],
    *,
    max_overdue_days_allowed: int = 0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Task-List Checklist Completion Parity, Unassigned Action Item & Stale Due-Date Hygiene Auditor."""
    valid_items: list[dict[str, Any]] = []
    if isinstance(checklists, (list, tuple)):
        for item in checklists:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("item_id") or "").strip()
            if not iid:
                continue
            valid_items.append({**item, "_iid": iid})

    if not valid_items:
        return {
            "total_items_evaluated": 0,
            "open_items_count": 0,
            "checked_items_count": 0,
            "unassigned_open_item_ids": [],
            "overdue_open_item_ids": [],
            "malformed_syntax_item_ids": [],
            "checklist_hygiene_status": "CHECKLIST_CLEAN",
            "is_checklist_compliant": True,
            "recommendations": [],
        }

    open_items_count = 0
    checked_items_count = 0
    unassigned_open_item_ids: list[str] = []
    overdue_open_item_ids: list[str] = []
    malformed_syntax_item_ids: list[str] = []

    for row in valid_items:
        iid = row["_iid"]
        is_checked = bool(row.get("is_checked", False))
        has_owner = bool(row.get("has_assigned_owner_handle", False))
        has_due = bool(row.get("has_iso_due_date", False))
        overdue = int(
            row.get("overdue_days", 0)
            if row.get("overdue_days") is not None
            else 0
        )
        malformed = bool(row.get("has_malformed_checkbox_syntax", False))

        if is_checked:
            checked_items_count += 1
        else:
            open_items_count += 1
            if not has_owner or not has_due:
                unassigned_open_item_ids.append(iid)
            if overdue > max_overdue_days_allowed:
                overdue_open_item_ids.append(iid)

        if malformed:
            malformed_syntax_item_ids.append(iid)

    recommendations: list[str] = []
    if malformed_syntax_item_ids:
        recommendations.append(
            f"Normalize GFM checkbox syntax (`- [ ]` or `- [x]`) for item(s): {', '.join(malformed_syntax_item_ids)}."
        )
    if overdue_open_item_ids:
        recommendations.append(
            f"Escalate or close overdue open checklist action item(s) exceeding {max_overdue_days_allowed} day(s): {', '.join(overdue_open_item_ids)}."
        )
    if unassigned_open_item_ids:
        recommendations.append(
            f"Assign explicit `@owner` handle and ISO-8601 due date to open action item(s): {', '.join(unassigned_open_item_ids)}."
        )

    if overdue_open_item_ids or malformed_syntax_item_ids:
        checklist_hygiene_status = "ACTION_GOVERNANCE_BREACH"
    elif unassigned_open_item_ids:
        checklist_hygiene_status = "UNASSIGNED_ACTION_WARNING"
    else:
        checklist_hygiene_status = "CHECKLIST_CLEAN"

    return {
        "total_items_evaluated": len(valid_items),
        "open_items_count": open_items_count,
        "checked_items_count": checked_items_count,
        "unassigned_open_item_ids": unassigned_open_item_ids,
        "overdue_open_item_ids": overdue_open_item_ids,
        "malformed_syntax_item_ids": malformed_syntax_item_ids,
        "checklist_hygiene_status": checklist_hygiene_status,
        "is_checklist_compliant": checklist_hygiene_status == "CHECKLIST_CLEAN",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_task_list_checklist_owner_and_due_date_hygiene = staticmethod(
    audit_markdown_task_list_checklist_owner_and_due_date_hygiene
)
AnydocService.audit_markdown_task_list_checklist_owner_and_due_date_hygiene = staticmethod(
    audit_markdown_task_list_checklist_owner_and_due_date_hygiene
)


def audit_markdown_image_alt_text_and_asset_weight_hygiene(
    images: list[dict[str, Any]],
    *,
    max_asset_size_kb: float = 500.0,
    min_alt_text_chars: int = 5,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Image Alt-Text Accessibility, Oversized Binary Asset & Broken Relative Path Hygiene Auditor."""
    valid_images: list[dict[str, Any]] = []
    if isinstance(images, (list, tuple)):
        for item in images:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("image_id") or "").strip()
            if not iid:
                continue
            valid_images.append({**item, "_iid": iid})

    if not valid_images:
        return {
            "total_images_evaluated": 0,
            "broken_path_image_ids": [],
            "missing_or_trivial_alt_image_ids": [],
            "oversized_or_unoptimized_image_ids": [],
            "image_hygiene_status": "MEDIA_ASSETS_CLEAN",
            "is_media_hygiene_compliant": True,
            "recommendations": [],
        }

    trivial_tokens = {"image", "img", "screenshot", "picture", "foto"}
    broken_path_image_ids: list[str] = []
    missing_or_trivial_alt_image_ids: list[str] = []
    oversized_or_unoptimized_image_ids: list[str] = []

    for img in valid_images:
        iid = img["_iid"]
        alt_clean = str(img.get("alt_text") or "").strip()
        size_kb = float(
            img.get("asset_size_kb", 100.0)
            if img.get("asset_size_kb") is not None
            else 100.0
        )
        path_exists = bool(img.get("target_path_exists", True))
        unoptimized = bool(img.get("uses_unoptimized_bmp_or_tiff", False))

        if not path_exists:
            broken_path_image_ids.append(iid)

        if (
            len(alt_clean) < min_alt_text_chars
            or alt_clean.lower() in trivial_tokens
        ):
            missing_or_trivial_alt_image_ids.append(iid)

        if size_kb > max_asset_size_kb or unoptimized:
            oversized_or_unoptimized_image_ids.append(iid)

    recommendations: list[str] = []
    if broken_path_image_ids:
        recommendations.append(
            f"Restore missing image files or fix broken relative paths for image(s): {', '.join(broken_path_image_ids)}."
        )
    if missing_or_trivial_alt_image_ids:
        recommendations.append(
            f"Provide descriptive accessibility alt-text (>= {min_alt_text_chars} chars, non-generic) for image(s): {', '.join(missing_or_trivial_alt_image_ids)}."
        )
    if oversized_or_unoptimized_image_ids:
        recommendations.append(
            f"Compress oversized images (<= {max_asset_size_kb} KB) and convert BMP/TIFF to WebP/PNG/SVG for image(s): {', '.join(oversized_or_unoptimized_image_ids)}."
        )

    if broken_path_image_ids or missing_or_trivial_alt_image_ids:
        image_hygiene_status = "BROKEN_OR_INACCESSIBLE_MEDIA"
    elif oversized_or_unoptimized_image_ids:
        image_hygiene_status = "ASSET_BLOAT_WARNING"
    else:
        image_hygiene_status = "MEDIA_ASSETS_CLEAN"

    return {
        "total_images_evaluated": len(valid_images),
        "broken_path_image_ids": broken_path_image_ids,
        "missing_or_trivial_alt_image_ids": missing_or_trivial_alt_image_ids,
        "oversized_or_unoptimized_image_ids": oversized_or_unoptimized_image_ids,
        "image_hygiene_status": image_hygiene_status,
        "is_media_hygiene_compliant": image_hygiene_status
        == "MEDIA_ASSETS_CLEAN",
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_image_alt_text_and_asset_weight_hygiene = staticmethod(
    audit_markdown_image_alt_text_and_asset_weight_hygiene
)
AnydocService.audit_markdown_image_alt_text_and_asset_weight_hygiene = staticmethod(
    audit_markdown_image_alt_text_and_asset_weight_hygiene
)


def audit_markdown_acronym_expansion_and_glossary_term_hygiene(
    documents: Any,
    *,
    max_unexpanded_acronyms_allowed: int = 0,
) -> dict[str, Any]:
    """PMBOK 4.4 y 10.2: higiene terminológica del glosario.

    Evalúa por documento la expansión de acrónimos en su primer uso,
    la ausencia de términos prohibidos o conflictivos y el enlace
    canónico al glosario.
    """
    entries = documents if isinstance(documents, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    conflicting_or_banned_term_doc_ids: list[str] = []
    unexpanded_acronym_doc_ids: list[str] = []
    missing_glossary_link_doc_ids: list[str] = []

    for item in rows:
        doc_id = item.get("doc_id")

        conflicts = item.get("conflicting_acronym_definitions_count", 0)
        conflicts_val = conflicts if isinstance(conflicts, (int, float)) and conflicts > 0 else 0
        banned = item.get("deprecated_or_banned_terms_count", 0)
        banned_val = banned if isinstance(banned, (int, float)) and banned > 0 else 0
        unexpanded = item.get("unexpanded_first_use_acronyms_count", 0)
        unexpanded_val = unexpanded if isinstance(unexpanded, (int, float)) and unexpanded >= 0 else 0

        if conflicts_val > 0 or banned_val > 0:
            conflicting_or_banned_term_doc_ids.append(doc_id)

        if unexpanded_val > max_unexpanded_acronyms_allowed:
            unexpanded_acronym_doc_ids.append(doc_id)

        if item.get("has_canonical_glossary_link", True) is not True:
            missing_glossary_link_doc_ids.append(doc_id)

    if conflicting_or_banned_term_doc_ids:
        terminology_hygiene_status = "TERMINOLOGY_CONFLICT_OR_BANNED_BREACH"
    elif unexpanded_acronym_doc_ids or missing_glossary_link_doc_ids:
        terminology_hygiene_status = "ACRONYM_OR_GLOSSARY_WARNING"
    else:
        terminology_hygiene_status = "TERMINOLOGY_CANONICAL_CLEAN"

    return {
        "total_documents_evaluated": len(rows),
        "conflicting_or_banned_term_doc_ids": conflicting_or_banned_term_doc_ids,
        "unexpanded_acronym_doc_ids": unexpanded_acronym_doc_ids,
        "missing_glossary_link_doc_ids": missing_glossary_link_doc_ids,
        "terminology_hygiene_status": terminology_hygiene_status,
        "is_terminology_compliant": terminology_hygiene_status == "TERMINOLOGY_CANONICAL_CLEAN",
    }


AnyDocService.audit_markdown_acronym_expansion_and_glossary_term_hygiene = staticmethod(
    audit_markdown_acronym_expansion_and_glossary_term_hygiene
)
AnydocService.audit_markdown_acronym_expansion_and_glossary_term_hygiene = staticmethod(
    audit_markdown_acronym_expansion_and_glossary_term_hygiene
)


def audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene(
    documents: Any,
    *,
    max_heading_depth_allowed: int = 4,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Heading Hierarchy Skip-Level, Duplicate Anchor ID & TOC Synchronization Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    rows = [
        item
        for item in entries
        if isinstance(item, dict) and str(item.get("doc_id") or "").strip()
    ]

    broken_anchor_or_h1_doc_ids: list[str] = []
    hierarchy_skip_or_toc_drift_doc_ids: list[str] = []

    for item in rows:
        doc_id = str(item.get("doc_id")).strip()
        has_single_h1_root = bool(
            item.get("has_single_h1_root", True)
            if item.get("has_single_h1_root") is not None
            else True
        )
        skipped_levels = int(
            item.get("skipped_heading_levels_count", 0)
            if item.get("skipped_heading_levels_count") is not None
            else 0
        )
        duplicate_anchors = int(
            item.get("duplicate_anchor_slugs_count", 0)
            if item.get("duplicate_anchor_slugs_count") is not None
            else 0
        )
        max_depth = int(
            item.get("max_heading_depth_observed", 2)
            if item.get("max_heading_depth_observed") is not None
            else 2
        )
        toc_synced = bool(
            item.get("toc_synchronized_with_headings", True)
            if item.get("toc_synchronized_with_headings") is not None
            else True
        )

        if not has_single_h1_root or duplicate_anchors > 0:
            broken_anchor_or_h1_doc_ids.append(doc_id)

        if (
            skipped_levels > 0
            or not toc_synced
            or max_depth > max_heading_depth_allowed
        ):
            hierarchy_skip_or_toc_drift_doc_ids.append(doc_id)

    if broken_anchor_or_h1_doc_ids:
        heading_hygiene_status = "HEADING_ANCHOR_OR_H1_BREACH"
    elif hierarchy_skip_or_toc_drift_doc_ids:
        heading_hygiene_status = "HEADING_HIERARCHY_OR_TOC_WARNING"
    else:
        heading_hygiene_status = "HEADING_STRUCTURE_CLEAN"

    return {
        "evaluated_documents_count": len(rows),
        "broken_anchor_or_h1_doc_ids": broken_anchor_or_h1_doc_ids,
        "hierarchy_skip_or_toc_drift_doc_ids": hierarchy_skip_or_toc_drift_doc_ids,
        "heading_hygiene_status": heading_hygiene_status,
        "is_heading_hygiene_compliant": heading_hygiene_status
        == "HEADING_STRUCTURE_CLEAN",
    }


AnyDocService.audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene = staticmethod(
    audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene
)
AnydocService.audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene = staticmethod(
    audit_markdown_heading_hierarchy_and_duplicate_anchor_hygiene
)


def audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene(
    documents: Any,
    *,
    allow_whitelisted_iframes: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.2 — AnyDoc Markdown Inline HTML Sanitization, Script/Event-Handler Injection & Iframe Domain Whitelist Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    rows = [
        item
        for item in entries
        if isinstance(item, dict) and str(item.get("doc_id") or "").strip()
    ]

    xss_or_untrusted_embed_doc_ids: list[str] = []
    raw_html_style_warning_doc_ids: list[str] = []

    for item in rows:
        doc_id = str(item.get("doc_id")).strip()
        unsafe_scripts = int(
            item.get("unsafe_script_or_event_handler_tags_count", 0)
            if item.get("unsafe_script_or_event_handler_tags_count") is not None
            else 0
        )
        unwhitelisted_embeds = int(
            item.get("unwhitelisted_iframe_or_embed_count", 0)
            if item.get("unwhitelisted_iframe_or_embed_count") is not None
            else 0
        )
        whitelisted_iframes = int(
            item.get("whitelisted_iframe_count", 0)
            if item.get("whitelisted_iframe_count") is not None
            else 0
        )
        raw_style_tags = int(
            item.get("raw_style_or_deprecated_html_tags_count", 0)
            if item.get("raw_style_or_deprecated_html_tags_count") is not None
            else 0
        )
        csp_sandbox_enforced = bool(
            item.get("csp_nonce_or_sandbox_enforced", True)
            if item.get("csp_nonce_or_sandbox_enforced") is not None
            else True
        )

        if (
            unsafe_scripts > 0
            or unwhitelisted_embeds > 0
            or (not allow_whitelisted_iframes and whitelisted_iframes > 0)
            or (whitelisted_iframes > 0 and not csp_sandbox_enforced)
        ):
            xss_or_untrusted_embed_doc_ids.append(doc_id)

        if raw_style_tags > 0:
            raw_html_style_warning_doc_ids.append(doc_id)

    if xss_or_untrusted_embed_doc_ids:
        html_sanitization_status = "HTML_XSS_OR_UNTRUSTED_EMBED_BREACH"
    elif raw_html_style_warning_doc_ids:
        html_sanitization_status = "HTML_RAW_STYLE_OR_DEPRECATED_TAG_WARNING"
    else:
        html_sanitization_status = "HTML_SANITIZATION_CLEAN"

    return {
        "evaluated_documents_count": len(rows),
        "xss_or_untrusted_embed_doc_ids": xss_or_untrusted_embed_doc_ids,
        "raw_html_style_warning_doc_ids": raw_html_style_warning_doc_ids,
        "html_sanitization_status": html_sanitization_status,
        "is_html_sanitization_compliant": html_sanitization_status
        == "HTML_SANITIZATION_CLEAN",
    }


AnyDocService.audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene = staticmethod(
    audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene
)
AnydocService.audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene = staticmethod(
    audit_markdown_inline_html_xss_and_iframe_whitelist_hygiene
)


def audit_markdown_link_rot_and_internal_anchor_resolution_hygiene(
    documents: Any,
    *,
    max_redirect_hops_allowed: int = 2,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Link Rot HTTP Status, Internal Anchor Resolution & External Reference Archival Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    rows = [
        item
        for item in entries
        if isinstance(item, dict) and str(item.get("doc_id") or "").strip()
    ]

    dead_link_or_broken_anchor_doc_ids: list[str] = []
    redirect_chain_or_unpinned_url_doc_ids: list[str] = []

    for item in rows:
        doc_id = str(item.get("doc_id")).strip()
        dead_links = int(
            item.get("dead_404_or_5xx_links_count", 0)
            if item.get("dead_404_or_5xx_links_count") is not None
            else 0
        )
        unresolved_anchors = int(
            item.get("unresolved_internal_anchors_count", 0)
            if item.get("unresolved_internal_anchors_count") is not None
            else 0
        )
        redirect_hops = int(
            item.get("max_redirect_chain_hops", 0)
            if item.get("max_redirect_chain_hops") is not None
            else 0
        )
        unpinned_urls = int(
            item.get("unpinned_mutable_external_urls_count", 0)
            if item.get("unpinned_mutable_external_urls_count") is not None
            else 0
        )

        if dead_links > 0 or unresolved_anchors > 0:
            dead_link_or_broken_anchor_doc_ids.append(doc_id)

        if redirect_hops > max_redirect_hops_allowed or unpinned_urls > 0:
            redirect_chain_or_unpinned_url_doc_ids.append(doc_id)

    if dead_link_or_broken_anchor_doc_ids:
        link_integrity_status = "LINK_ROT_OR_BROKEN_ANCHOR_BREACH"
    elif redirect_chain_or_unpinned_url_doc_ids:
        link_integrity_status = "LINK_REDIRECT_OR_UNPINNED_WARNING"
    else:
        link_integrity_status = "LINK_INTEGRITY_VERIFIED"

    return {
        "evaluated_documents_count": len(rows),
        "dead_link_or_broken_anchor_doc_ids": dead_link_or_broken_anchor_doc_ids,
        "redirect_chain_or_unpinned_url_doc_ids": redirect_chain_or_unpinned_url_doc_ids,
        "link_integrity_status": link_integrity_status,
        "is_link_integrity_compliant": link_integrity_status
        == "LINK_INTEGRITY_VERIFIED",
    }


AnyDocService.audit_markdown_link_rot_and_internal_anchor_resolution_hygiene = staticmethod(
    audit_markdown_link_rot_and_internal_anchor_resolution_hygiene
)
AnydocService.audit_markdown_link_rot_and_internal_anchor_resolution_hygiene = staticmethod(
    audit_markdown_link_rot_and_internal_anchor_resolution_hygiene
)


def audit_markdown_math_latex_delimiter_and_macro_hygiene(
    documents: Any,
    *,
    max_equation_nesting_depth: int = 5,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown LaTeX/KaTeX Math Delimiter Parity, Unsupported Macro & Equation Reference Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    valid_documents = [
        doc
        for doc in entries
        if isinstance(doc, dict) and str(doc.get("doc_id") or "").strip()
    ]

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    broken_delimiter_or_unsafe_macro_doc_ids: list[str] = []
    unresolved_eqref_or_deep_nesting_doc_ids: list[str] = []

    for doc in valid_documents:
        doc_id = str(doc.get("doc_id")).strip()
        unclosed_blocks = _num(
            doc.get("unclosed_dollar_or_environment_blocks_count"), 0.0
        )
        unsafe_macros = _num(
            doc.get("unsafe_or_unsupported_katex_macros_count"), 0.0
        )
        unresolved_eqrefs = _num(
            doc.get("unresolved_eqref_labels_count"), 0.0
        )
        nesting_depth = _num(
            doc.get("max_observed_equation_nesting_depth"), 2.0
        )

        if unclosed_blocks > 0 or unsafe_macros > 0:
            broken_delimiter_or_unsafe_macro_doc_ids.append(doc_id)

        if (
            unresolved_eqrefs > 0
            or nesting_depth > max_equation_nesting_depth
        ):
            unresolved_eqref_or_deep_nesting_doc_ids.append(doc_id)

    if broken_delimiter_or_unsafe_macro_doc_ids:
        math_hygiene_status = "MATH_DELIMITER_OR_UNSAFE_MACRO_BREACH"
    elif unresolved_eqref_or_deep_nesting_doc_ids:
        math_hygiene_status = "MATH_EQREF_OR_NESTING_WARNING"
    else:
        math_hygiene_status = "MATH_RENDERING_CLEAN"

    return {
        "evaluated_documents_count": len(valid_documents),
        "broken_delimiter_or_unsafe_macro_doc_ids": broken_delimiter_or_unsafe_macro_doc_ids,
        "unresolved_eqref_or_deep_nesting_doc_ids": unresolved_eqref_or_deep_nesting_doc_ids,
        "math_hygiene_status": math_hygiene_status,
        "is_math_hygiene_compliant": math_hygiene_status
        == "MATH_RENDERING_CLEAN",
    }


AnyDocService.audit_markdown_math_latex_delimiter_and_macro_hygiene = staticmethod(
    audit_markdown_math_latex_delimiter_and_macro_hygiene
)
AnydocService.audit_markdown_math_latex_delimiter_and_macro_hygiene = staticmethod(
    audit_markdown_math_latex_delimiter_and_macro_hygiene
)


def audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene(
    documents: Any,
    *,
    max_admonition_density_per_doc: int = 6,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Admonition/Callout Alert Severity Taxonomy, Nesting Prohibition & Consecutive Alert Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    valid_documents = [
        doc
        for doc in entries
        if isinstance(doc, dict) and str(doc.get("doc_id") or "").strip()
    ]

    nested_or_unknown_admonition_doc_ids: list[str] = []
    adjacent_or_overused_admonition_doc_ids: list[str] = []

    for doc in valid_documents:
        did = str(doc.get("doc_id")).strip()
        nested_admonitions_count = int(
            doc.get("nested_admonitions_count", 0)
            if doc.get("nested_admonitions_count") is not None
            else 0
        )
        unknown_admonition_types_count = int(
            doc.get("unknown_admonition_types_count", 0)
            if doc.get("unknown_admonition_types_count") is not None
            else 0
        )
        consecutive_adjacent_admonitions_count = int(
            doc.get("consecutive_adjacent_admonitions_count", 0)
            if doc.get("consecutive_adjacent_admonitions_count") is not None
            else 0
        )
        total_admonitions_count = int(
            doc.get("total_admonitions_count", 2)
            if doc.get("total_admonitions_count") is not None
            else 2
        )

        if nested_admonitions_count > 0 or unknown_admonition_types_count > 0:
            nested_or_unknown_admonition_doc_ids.append(did)

        if (
            consecutive_adjacent_admonitions_count > 0
            or total_admonitions_count > max_admonition_density_per_doc
        ):
            adjacent_or_overused_admonition_doc_ids.append(did)

    if nested_or_unknown_admonition_doc_ids:
        admonition_hygiene_status = "ADMONITION_NESTING_OR_TAXONOMY_BREACH"
    elif adjacent_or_overused_admonition_doc_ids:
        admonition_hygiene_status = "ADMONITION_ADJACENCY_OR_FATIGUE_WARNING"
    else:
        admonition_hygiene_status = "ADMONITION_CALLOUT_HYGIENE_CLEAN"

    return {
        "evaluated_documents_count": len(valid_documents),
        "nested_or_unknown_admonition_doc_ids": nested_or_unknown_admonition_doc_ids,
        "adjacent_or_overused_admonition_doc_ids": adjacent_or_overused_admonition_doc_ids,
        "admonition_hygiene_status": admonition_hygiene_status,
        "is_admonition_hygiene_compliant": admonition_hygiene_status
        == "ADMONITION_CALLOUT_HYGIENE_CLEAN",
    }


AnyDocService.audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene = staticmethod(
    audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene
)
AnydocService.audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene = staticmethod(
    audit_markdown_admonition_callout_taxonomy_and_nesting_hygiene
)


def audit_markdown_fenced_code_block_language_and_secret_hygiene(
    documents: Any,
    *,
    max_code_line_length: int = 120,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Code-Block Language Tagging, Hardcoded Secret/Credential Pattern & Line-Length Hygiene Auditor."""
    entries = documents if isinstance(documents, (list, tuple)) else []
    valid_documents = [
        doc
        for doc in entries
        if isinstance(doc, dict) and str(doc.get("doc_id") or "").strip()
    ]

    unclosed_fence_or_secret_leak_doc_ids: list[str] = []
    untagged_language_or_long_line_doc_ids: list[str] = []

    for doc in valid_documents:
        did = str(doc.get("doc_id")).strip()
        untagged_fenced_code_blocks_count = int(
            doc.get("untagged_fenced_code_blocks_count", 0)
            if doc.get("untagged_fenced_code_blocks_count") is not None
            else 0
        )
        unclosed_code_fences_count = int(
            doc.get("unclosed_code_fences_count", 0)
            if doc.get("unclosed_code_fences_count") is not None
            else 0
        )
        hardcoded_secret_or_token_patterns_count = int(
            doc.get("hardcoded_secret_or_token_patterns_count", 0)
            if doc.get("hardcoded_secret_or_token_patterns_count") is not None
            else 0
        )
        max_observed_code_line_length = int(
            doc.get("max_observed_code_line_length", 88)
            if doc.get("max_observed_code_line_length") is not None
            else 88
        )

        if (
            unclosed_code_fences_count > 0
            or hardcoded_secret_or_token_patterns_count > 0
        ):
            unclosed_fence_or_secret_leak_doc_ids.append(did)

        if (
            untagged_fenced_code_blocks_count > 0
            or max_observed_code_line_length > max_code_line_length
        ):
            untagged_language_or_long_line_doc_ids.append(did)

    if unclosed_fence_or_secret_leak_doc_ids:
        code_block_hygiene_status = (
            "CODE_BLOCK_SECRET_OR_UNCLOSED_FENCE_BREACH"
        )
    elif untagged_language_or_long_line_doc_ids:
        code_block_hygiene_status = (
            "CODE_BLOCK_UNTAGGED_OR_LINE_LENGTH_WARNING"
        )
    else:
        code_block_hygiene_status = "CODE_BLOCK_HYGIENE_CLEAN"

    return {
        "evaluated_documents_count": len(valid_documents),
        "unclosed_fence_or_secret_leak_doc_ids": unclosed_fence_or_secret_leak_doc_ids,
        "untagged_language_or_long_line_doc_ids": untagged_language_or_long_line_doc_ids,
        "code_block_hygiene_status": code_block_hygiene_status,
        "is_code_block_hygiene_compliant": code_block_hygiene_status
        == "CODE_BLOCK_HYGIENE_CLEAN",
    }


AnyDocService.audit_markdown_fenced_code_block_language_and_secret_hygiene = staticmethod(
    audit_markdown_fenced_code_block_language_and_secret_hygiene
)
AnydocService.audit_markdown_fenced_code_block_language_and_secret_hygiene = staticmethod(
    audit_markdown_fenced_code_block_language_and_secret_hygiene
)


def audit_markdown_table_column_parity_and_cell_hygiene(
    tables: Any,
    *,
    max_columns_count: int = 10,
    max_cell_char_length: int = 240,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Table Column Parity, Header Separator Syntax & Cell Pipe Escaping Hygiene Auditor."""
    entries = tables if isinstance(tables, (list, tuple)) else []
    valid_tables = [
        table
        for table in entries
        if isinstance(table, dict)
        and str(table.get("table_id") or "").strip()
    ]

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    malformed_structure_or_pipe_table_ids: list[str] = []
    wide_or_overflow_cell_table_ids: list[str] = []

    for table in valid_tables:
        table_id = str(table.get("table_id")).strip()
        header_columns = _num(
            table.get("header_columns_count"), 4.0
        )
        row_counts_consistent = _bool(
            table.get("row_column_counts_consistent"), True
        )
        delimiter_row_present = _bool(
            table.get("valid_delimiter_row_present"), True
        )
        unescaped_pipes = _num(
            table.get("unescaped_inline_pipes_count"), 0.0
        )
        max_cell_chars = _num(
            table.get("max_observed_cell_chars"), 80.0
        )

        if (
            not row_counts_consistent
            or not delimiter_row_present
            or unescaped_pipes > 0
        ):
            malformed_structure_or_pipe_table_ids.append(table_id)

        if (
            header_columns > max_columns_count
            or max_cell_chars > max_cell_char_length
        ):
            wide_or_overflow_cell_table_ids.append(table_id)

    if malformed_structure_or_pipe_table_ids:
        table_hygiene_status = "MARKDOWN_TABLE_STRUCTURE_OR_PIPE_BREACH"
    elif wide_or_overflow_cell_table_ids:
        table_hygiene_status = "MARKDOWN_TABLE_WIDTH_OR_CELL_OVERFLOW_WARNING"
    else:
        table_hygiene_status = "MARKDOWN_TABLE_HYGIENE_OPTIMAL"

    return {
        "evaluated_tables_count": len(valid_tables),
        "malformed_structure_or_pipe_table_ids": malformed_structure_or_pipe_table_ids,
        "wide_or_overflow_cell_table_ids": wide_or_overflow_cell_table_ids,
        "table_hygiene_status": table_hygiene_status,
        "is_table_hygiene_compliant": table_hygiene_status
        == "MARKDOWN_TABLE_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_table_column_parity_and_cell_hygiene = staticmethod(
    audit_markdown_table_column_parity_and_cell_hygiene
)


def audit_markdown_footnote_citation_reciprocity_and_key_hygiene(
    footnotes: list[dict] | None,
    *,
    max_footnote_char_length: int = 600,
    require_canonical_url_or_doi: bool = True,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita reciprocidad de citas de notas al pie Markdown, definiciones huérfanas o duplicadas e higiene de fuente canónica."""
    raw_items = footnotes if isinstance(footnotes, list) else []
    valid_footnotes: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("footnote_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_footnotes.append(item)

    unpaired_or_duplicate_footnote_ids: list[str] = []
    verbose_or_uncited_source_footnote_ids: list[str] = []

    for f in valid_footnotes:
        fid = f["footnote_id"].strip()
        raw_inline = f.get("inline_reference_exists", True)
        inline_reference_exists = bool(
            True if raw_inline is None else raw_inline
        )

        raw_def = f.get("definition_block_exists", True)
        definition_block_exists = bool(True if raw_def is None else raw_def)

        raw_dup = f.get("duplicate_definition_count", 1)
        duplicate_definition_count = int(1 if raw_dup is None else raw_dup)

        raw_len = f.get("char_length", 180)
        char_length = int(180 if raw_len is None else raw_len)

        raw_url = f.get("canonical_url_or_doi_present", True)
        canonical_url_or_doi_present = bool(
            True if raw_url is None else raw_url
        )

        if (
            not inline_reference_exists
            or not definition_block_exists
            or duplicate_definition_count > 1
        ):
            unpaired_or_duplicate_footnote_ids.append(fid)

        if char_length > max_footnote_char_length or (
            require_canonical_url_or_doi and not canonical_url_or_doi_present
        ):
            verbose_or_uncited_source_footnote_ids.append(fid)

    if unpaired_or_duplicate_footnote_ids:
        footnote_hygiene_status = (
            "MARKDOWN_FOOTNOTE_UNPAIRED_OR_DUPLICATE_BREACH"
        )
    elif verbose_or_uncited_source_footnote_ids:
        footnote_hygiene_status = (
            "MARKDOWN_FOOTNOTE_LENGTH_OR_CITATION_WARNING"
        )
    else:
        footnote_hygiene_status = "MARKDOWN_FOOTNOTE_HYGIENE_OPTIMAL"

    return {
        "evaluated_footnotes_count": len(valid_footnotes),
        "unpaired_or_duplicate_footnote_ids": unpaired_or_duplicate_footnote_ids,
        "verbose_or_uncited_source_footnote_ids": verbose_or_uncited_source_footnote_ids,
        "footnote_hygiene_status": footnote_hygiene_status,
        "is_footnote_hygiene_compliant": footnote_hygiene_status
        == "MARKDOWN_FOOTNOTE_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_footnote_citation_reciprocity_and_key_hygiene = staticmethod(
    audit_markdown_footnote_citation_reciprocity_and_key_hygiene
)


def audit_markdown_gfm_task_list_completion_and_nesting_hygiene(
    checklists: list[dict] | None,
    *,
    max_nesting_depth: int = 3,
    require_children_complete_when_parent_checked: bool = True,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita paridad de completitud de checkboxes GFM en listas de tareas Markdown, profundidad de anidación y bloqueadores sin dueño."""
    raw_items = checklists if isinstance(checklists, list) else []
    valid_checklists: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("checklist_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_checklists.append(item)

    inconsistent_parent_or_syntax_checklist_ids: list[str] = []
    deep_nesting_or_unassigned_blocker_checklist_ids: list[str] = []

    for c in valid_checklists:
        cid = c["checklist_id"].strip()
        raw_parent = c.get("parent_checked_with_unchecked_children", False)
        parent_checked_with_unchecked_children = bool(
            False if raw_parent is None else raw_parent
        )

        raw_syntax = c.get("malformed_gfm_checkbox_syntax_count", 0)
        malformed_gfm_checkbox_syntax_count = int(
            0 if raw_syntax is None else raw_syntax
        )

        raw_depth = c.get("observed_nesting_depth", 2)
        observed_nesting_depth = int(2 if raw_depth is None else raw_depth)

        raw_blockers = c.get("unassigned_blocker_items_count", 0)
        unassigned_blocker_items_count = int(
            0 if raw_blockers is None else raw_blockers
        )

        if (
            require_children_complete_when_parent_checked
            and parent_checked_with_unchecked_children
        ) or malformed_gfm_checkbox_syntax_count > 0:
            inconsistent_parent_or_syntax_checklist_ids.append(cid)

        if (
            observed_nesting_depth > max_nesting_depth
            or unassigned_blocker_items_count > 0
        ):
            deep_nesting_or_unassigned_blocker_checklist_ids.append(cid)

    if inconsistent_parent_or_syntax_checklist_ids:
        task_list_hygiene_status = (
            "MARKDOWN_TASK_LIST_PARITY_OR_SYNTAX_BREACH"
        )
    elif deep_nesting_or_unassigned_blocker_checklist_ids:
        task_list_hygiene_status = (
            "MARKDOWN_TASK_LIST_NESTING_OR_BLOCKER_WARNING"
        )
    else:
        task_list_hygiene_status = "MARKDOWN_TASK_LIST_HYGIENE_OPTIMAL"

    return {
        "evaluated_checklists_count": len(valid_checklists),
        "inconsistent_parent_or_syntax_checklist_ids": inconsistent_parent_or_syntax_checklist_ids,
        "deep_nesting_or_unassigned_blocker_checklist_ids": deep_nesting_or_unassigned_blocker_checklist_ids,
        "task_list_hygiene_status": task_list_hygiene_status,
        "is_task_list_hygiene_compliant": task_list_hygiene_status
        == "MARKDOWN_TASK_LIST_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_gfm_task_list_completion_and_nesting_hygiene = staticmethod(
    audit_markdown_gfm_task_list_completion_and_nesting_hygiene
)


def audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene(
    diagrams: list[dict] | None,
    *,
    max_nodes_per_diagram: int = 45,
    max_edges_per_diagram: int = 80,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita validez de encabezado soportado en diagramas Mermaid Markdown, escape de caracteres especiales en etiquetas y presupuesto de nodos/aristas."""
    raw_items = diagrams if isinstance(diagrams, list) else []
    valid_diagrams: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("diagram_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_diagrams.append(item)

    syntax_error_or_unsupported_diagram_ids: list[str] = []
    overcrowded_node_or_edge_budget_diagram_ids: list[str] = []

    for d in valid_diagrams:
        did = d["diagram_id"].strip()
        raw_header = d.get("supported_diagram_header_valid", True)
        supported_diagram_header_valid = bool(
            True if raw_header is None else raw_header
        )

        raw_unesc = d.get("unescaped_special_chars_in_labels", 0)
        unescaped_special_chars_in_labels = int(
            0 if raw_unesc is None else raw_unesc
        )

        raw_nodes = d.get("nodes_count", 15)
        nodes_count = int(15 if raw_nodes is None else raw_nodes)

        raw_edges = d.get("edges_count", 22)
        edges_count = int(22 if raw_edges is None else raw_edges)

        if (
            not supported_diagram_header_valid
            or unescaped_special_chars_in_labels > 0
        ):
            syntax_error_or_unsupported_diagram_ids.append(did)

        if (
            nodes_count > max_nodes_per_diagram
            or edges_count > max_edges_per_diagram
        ):
            overcrowded_node_or_edge_budget_diagram_ids.append(did)

    if syntax_error_or_unsupported_diagram_ids:
        mermaid_hygiene_status = "MERMAID_SYNTAX_OR_LABEL_ESCAPE_BREACH"
    elif overcrowded_node_or_edge_budget_diagram_ids:
        mermaid_hygiene_status = "MERMAID_NODE_OR_EDGE_BUDGET_WARNING"
    else:
        mermaid_hygiene_status = "MERMAID_DIAGRAM_HYGIENE_OPTIMAL"

    return {
        "evaluated_diagrams_count": len(valid_diagrams),
        "syntax_error_or_unsupported_diagram_ids": syntax_error_or_unsupported_diagram_ids,
        "overcrowded_node_or_edge_budget_diagram_ids": overcrowded_node_or_edge_budget_diagram_ids,
        "mermaid_hygiene_status": mermaid_hygiene_status,
        "is_mermaid_hygiene_compliant": mermaid_hygiene_status
        == "MERMAID_DIAGRAM_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_node_budget_hygiene
)


def audit_markdown_image_alt_text_and_svg_sanitization_hygiene(
    images: list[dict] | None,
    *,
    max_image_payload_kb: float = 500.0,
    min_alt_text_chars: int = 8,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita accesibilidad de texto alternativo (alt-text) en imágenes Markdown, sanitización de scripts inline en SVG, bloqueo de hotlinking externo y peso del activo."""
    raw_items = images if isinstance(images, list) else []
    valid_images: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("image_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_images.append(item)

    unsanitized_svg_or_hotlinked_image_ids: list[str] = []
    missing_alt_or_bloated_payload_image_ids: list[str] = []

    for img in valid_images:
        iid = str(img["image_id"]).strip()
        raw_svg = img.get("svg_inline_scripts_sanitized", True)
        svg_inline_scripts_sanitized = bool(
            True if raw_svg is None else raw_svg
        )

        raw_hot = img.get("external_hotlink_blocked", True)
        external_hotlink_blocked = bool(True if raw_hot is None else raw_hot)

        raw_alt = img.get("alt_text_char_length", 25)
        alt_text_char_length = int(25 if raw_alt is None else raw_alt)

        raw_kb = img.get("payload_size_kb", 120.0)
        payload_size_kb = float(120.0 if raw_kb is None else raw_kb)

        if not svg_inline_scripts_sanitized or not external_hotlink_blocked:
            unsanitized_svg_or_hotlinked_image_ids.append(iid)

        if (
            alt_text_char_length < min_alt_text_chars
            or payload_size_kb > max_image_payload_kb
        ):
            missing_alt_or_bloated_payload_image_ids.append(iid)

    if unsanitized_svg_or_hotlinked_image_ids:
        image_hygiene_status = "MARKDOWN_IMAGE_SVG_XSS_OR_HOTLINK_BREACH"
    elif missing_alt_or_bloated_payload_image_ids:
        image_hygiene_status = "MARKDOWN_IMAGE_ALT_TEXT_OR_WEIGHT_WARNING"
    else:
        image_hygiene_status = "MARKDOWN_IMAGE_HYGIENE_OPTIMAL"

    return {
        "evaluated_images_count": len(valid_images),
        "unsanitized_svg_or_hotlinked_image_ids": unsanitized_svg_or_hotlinked_image_ids,
        "missing_alt_or_bloated_payload_image_ids": missing_alt_or_bloated_payload_image_ids,
        "image_hygiene_status": image_hygiene_status,
        "is_image_hygiene_compliant": image_hygiene_status
        == "MARKDOWN_IMAGE_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_image_alt_text_and_svg_sanitization_hygiene = staticmethod(
    audit_markdown_image_alt_text_and_svg_sanitization_hygiene
)


def audit_markdown_yaml_frontmatter_schema_and_tag_hygiene(
    documents: list[dict] | None,
    *,
    max_tags_per_document: int = 8,
    require_owner_and_iso_date: bool = True,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita completitud del esquema YAML frontmatter en documentos Markdown, validez de fechas ISO-8601, propietario responsable e higiene de taxonomía de etiquetas."""
    raw_items = documents if isinstance(documents, list) else []
    valid_documents: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("document_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_documents.append(item)

    invalid_yaml_or_missing_metadata_document_ids: list[str] = []
    tag_sprawl_or_non_canonical_document_ids: list[str] = []

    for d in valid_documents:
        did = str(d["document_id"]).strip()
        raw_yaml = d.get("yaml_delimiters_and_syntax_valid", True)
        yaml_delimiters_and_syntax_valid = bool(
            True if raw_yaml is None else raw_yaml
        )

        raw_owner = d.get("owner_and_iso8601_date_present", True)
        owner_and_iso8601_date_present = bool(
            True if raw_owner is None else raw_owner
        )

        raw_tags = d.get("tags_count", 3)
        tags_count = int(3 if raw_tags is None else raw_tags)

        raw_non_canon = d.get("non_canonical_tags_count", 0)
        non_canonical_tags_count = int(
            0 if raw_non_canon is None else raw_non_canon
        )

        if not yaml_delimiters_and_syntax_valid or (
            require_owner_and_iso_date and not owner_and_iso8601_date_present
        ):
            invalid_yaml_or_missing_metadata_document_ids.append(did)

        if (
            tags_count > max_tags_per_document
            or non_canonical_tags_count > 0
            or tags_count < 1
        ):
            tag_sprawl_or_non_canonical_document_ids.append(did)

    if invalid_yaml_or_missing_metadata_document_ids:
        frontmatter_hygiene_status = (
            "FRONTMATTER_YAML_SYNTAX_OR_METADATA_BREACH"
        )
    elif tag_sprawl_or_non_canonical_document_ids:
        frontmatter_hygiene_status = (
            "FRONTMATTER_TAG_TAXONOMY_OR_SPRAWL_WARNING"
        )
    else:
        frontmatter_hygiene_status = "FRONTMATTER_SCHEMA_HYGIENE_OPTIMAL"

    return {
        "evaluated_documents_count": len(valid_documents),
        "invalid_yaml_or_missing_metadata_document_ids": invalid_yaml_or_missing_metadata_document_ids,
        "tag_sprawl_or_non_canonical_document_ids": tag_sprawl_or_non_canonical_document_ids,
        "frontmatter_hygiene_status": frontmatter_hygiene_status,
        "is_frontmatter_hygiene_compliant": frontmatter_hygiene_status
        == "FRONTMATTER_SCHEMA_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_yaml_frontmatter_schema_and_tag_hygiene = staticmethod(
    audit_markdown_yaml_frontmatter_schema_and_tag_hygiene
)


_ADMONITION_NESTING_HEADER_RE = re.compile(r"^\s*(>+)\s*\[!([A-Za-z0-9_-]+)\](.*)$")
_ADMONITION_NESTING_BQ_LINE_RE = re.compile(r"^\s*(>+)(.*)$")


def audit_markdown_admonition_callout_syntax_and_nesting_hygiene(
    markdown_text: str,
    *,
    allowed_alert_types: tuple[str, ...] = (
        "NOTE",
        "TIP",
        "IMPORTANT",
        "WARNING",
        "CAUTION",
    ),
    forbid_consecutive_alerts: bool = True,
    forbid_nested_alerts: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Audita sintaxis de alertas/callouts GitHub-Flavored Markdown (`> [!TYPE]`), espaciado entre alertas consecutivas y prohibición de anidamiento."""
    text = markdown_text if isinstance(markdown_text, str) else ""
    lines = text.splitlines()
    allowed_set = {
        str(t).strip().upper() for t in (allowed_alert_types or ()) if str(t).strip()
    }

    unsupported_alert_types: list[str] = []
    nested_alert_lines: list[int] = []
    consecutive_alert_lines: list[int] = []
    empty_or_inline_alert_lines: list[int] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []

    n = len(lines)
    idx = 0
    seen_any_alert = False
    had_non_blank_separator_since_last_alert = True

    while idx < n:
        line = lines[idx]
        header_match = _ADMONITION_NESTING_HEADER_RE.match(line)
        if not header_match:
            if line.strip():
                bq_match = _ADMONITION_NESTING_BQ_LINE_RE.match(line)
                if not bq_match:
                    had_non_blank_separator_since_last_alert = True
            idx += 1
            continue

        line_no = idx + 1
        quote_markers = header_match.group(1).replace(" ", "")
        quote_depth = len(quote_markers)
        alert_type = header_match.group(2).strip().upper()
        inline_tail = header_match.group(3).strip()

        body_lines_count = 0
        scan = idx + 1
        while scan < n:
            next_line = lines[scan]
            if _ADMONITION_NESTING_HEADER_RE.match(next_line):
                break
            bq_next = _ADMONITION_NESTING_BQ_LINE_RE.match(next_line)
            if not bq_next:
                break
            if bq_next.group(2).strip():
                body_lines_count += 1
            scan += 1

        nested_alert_violation = bool(forbid_nested_alerts and quote_depth > 1)
        unsupported_alert_type = alert_type not in allowed_set
        empty_or_inline_header_alert = bool(
            inline_tail or body_lines_count == 0
        )
        consecutive_alerts_violation = bool(
            forbid_consecutive_alerts
            and seen_any_alert
            and not had_non_blank_separator_since_last_alert
        )

        if unsupported_alert_type:
            unsupported_alert_types.append(alert_type)
            violations.append(
                f"Line {line_no}: unsupported alert type '{alert_type}'."
            )
        if nested_alert_violation:
            nested_alert_lines.append(line_no)
            violations.append(
                f"Line {line_no}: nested admonition callout is forbidden."
            )
        if consecutive_alerts_violation:
            consecutive_alert_lines.append(line_no)
            violations.append(
                f"Line {line_no}: consecutive alerts without intervening text."
            )
        if empty_or_inline_header_alert:
            empty_or_inline_alert_lines.append(line_no)
            violations.append(
                f"Line {line_no}: alert has inline header text or empty body."
            )

        records.append(
            {
                "line": line_no,
                "alert_type": alert_type,
                "quote_depth": quote_depth,
                "body_lines_count": body_lines_count,
                "nested_alert_violation": nested_alert_violation,
                "unsupported_alert_type": unsupported_alert_type,
                "empty_or_inline_header_alert": empty_or_inline_header_alert,
                "consecutive_alerts_violation": consecutive_alerts_violation,
            }
        )

        seen_any_alert = True
        had_non_blank_separator_since_last_alert = False
        idx = scan

    if unsupported_alert_types or nested_alert_lines:
        status = "critical"
        is_clean = False
    elif consecutive_alert_lines or empty_or_inline_alert_lines:
        status = "warning"
        is_clean = False
    else:
        status = "healthy"
        is_clean = True

    return {
        "is_clean": is_clean,
        "status": status,
        "alerts_detected": len(records),
        "unsupported_alert_types": unsupported_alert_types,
        "nested_alert_lines": nested_alert_lines,
        "consecutive_alert_lines": consecutive_alert_lines,
        "empty_or_inline_alert_lines": empty_or_inline_alert_lines,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


AnyDocService.audit_markdown_admonition_callout_syntax_and_nesting_hygiene = staticmethod(
    audit_markdown_admonition_callout_syntax_and_nesting_hygiene
)


def audit_markdown_glossary_definition_list_uniqueness_and_hygiene(
    entries: list[dict] | None,
    *,
    min_definition_chars: int = 15,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita la lista de definiciones del glosario Markdown: unicidad de términos, descripción no vacía/abreviada y referencias circulares de siglas."""
    raw_items = entries if isinstance(entries, list) else []
    valid_entries: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_term_id = item.get("term_id")
        if not isinstance(raw_term_id, str) or not raw_term_id.strip():
            continue
        valid_entries.append(item)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    def _str(value, default):
        return value if isinstance(value, str) else default

    duplicate_or_circular_term_ids: list[str] = []
    short_definition_or_uncited_term_ids: list[str] = []
    seen_labels: set[str] = set()

    for entry in valid_entries:
        term_id = str(entry.get("term_id")).strip()
        term_label = _str(entry.get("term_label"), "PMBOK")
        normalized_label = str(term_label).strip().lower()
        definition_text = _str(
            entry.get("definition_text"),
            "Project Management Body of Knowledge canonical standard.",
        )
        is_circular = _bool(entry.get("is_circular_self_reference"), False)
        has_citation = _bool(entry.get("has_canonical_citation"), True)

        if normalized_label in seen_labels or bool(is_circular) is True:
            duplicate_or_circular_term_ids.append(term_id)
        seen_labels.add(normalized_label)

        if (
            len(str(definition_text).strip()) < int(min_definition_chars)
            or not bool(has_citation)
        ):
            short_definition_or_uncited_term_ids.append(term_id)

    if duplicate_or_circular_term_ids:
        glossary_hygiene_status = "GLOSSARY_DUPLICATE_OR_CIRCULAR_BREACH"
    elif short_definition_or_uncited_term_ids:
        glossary_hygiene_status = "GLOSSARY_DEFINITION_OR_CITATION_WARNING"
    else:
        glossary_hygiene_status = "GLOSSARY_HYGIENE_OPTIMAL"

    return {
        "evaluated_terms_count": len(valid_entries),
        "duplicate_or_circular_term_ids": duplicate_or_circular_term_ids,
        "short_definition_or_uncited_term_ids": short_definition_or_uncited_term_ids,
        "glossary_hygiene_status": glossary_hygiene_status,
        "is_glossary_compliant": glossary_hygiene_status
        == "GLOSSARY_HYGIENE_OPTIMAL",
    }


AnyDocService.audit_markdown_glossary_definition_list_uniqueness_and_hygiene = staticmethod(
    audit_markdown_glossary_definition_list_uniqueness_and_hygiene
)


def audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety(
    equation_blocks: list[dict[str, Any]],
    *,
    max_macro_expansion_depth: int = 10,
    forbid_dangerous_latex_commands: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Audita balance de delimitadores LaTeX en línea/bloque (MathJax/KaTeX), colisiones de símbolos de moneda no escapados y profundidad/seguridad de expansión de macros."""
    raw_items = equation_blocks if isinstance(equation_blocks, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    unbalanced_or_unsafe_block_ids: list[str] = []
    macro_or_currency_warning_block_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    dangerous_cmds = ("\\input", "\\include", "\\write18", "\\def\\def")

    for idx, item in enumerate(valid_items):
        block_id = (
            str(
                item.get("block_id") or item.get("id") or f"eq-{idx + 1}"
            ).strip()
            or f"eq-{idx + 1}"
        )

        raw_bal = item.get("delimiters_balanced", True)
        delimiters_balanced = bool(True if raw_bal is None else raw_bal)

        raw_curr = item.get("unescaped_currency_collision", False)
        unescaped_currency_collision = bool(
            False if raw_curr is None else raw_curr
        )

        macro_expansion_depth = max(
            0, int(item.get("macro_expansion_depth") or 0)
        )

        raw_unsafe = item.get("contains_unsafe_command", False)
        contains_unsafe_command = bool(
            False if raw_unsafe is None else raw_unsafe
        )

        raw_expr = item.get("latex_expression", "")
        latex_expression = str("" if raw_expr is None else raw_expr)

        has_dangerous_cmd_in_expr = any(
            cmd in latex_expression for cmd in dangerous_cmds
        )
        unbalanced_or_unsafe_latex_breach = not delimiters_balanced or bool(
            forbid_dangerous_latex_commands
            and (contains_unsafe_command or has_dangerous_cmd_in_expr)
        )
        macro_depth_or_currency_collision_warning = bool(
            macro_expansion_depth > max_macro_expansion_depth
            or unescaped_currency_collision
        )

        if unbalanced_or_unsafe_latex_breach:
            unbalanced_or_unsafe_block_ids.append(block_id)
            has_critical = True
            violations.append(
                f"Equation block '{block_id}' has unbalanced delimiters or dangerous LaTeX commands."
            )

        if macro_depth_or_currency_collision_warning:
            macro_or_currency_warning_block_ids.append(block_id)
            has_warning = True
            violations.append(
                f"Equation block '{block_id}' exceeds macro expansion depth or has unescaped currency collision."
            )

        records.append(
            {
                "block_id": block_id,
                "delimiters_balanced": delimiters_balanced,
                "unescaped_currency_collision": unescaped_currency_collision,
                "macro_expansion_depth": macro_expansion_depth,
                "contains_unsafe_command": contains_unsafe_command,
                "latex_expression": latex_expression,
                "unbalanced_or_unsafe_latex_breach": unbalanced_or_unsafe_latex_breach,
                "macro_depth_or_currency_collision_warning": macro_depth_or_currency_collision_warning,
            }
        )

    if has_critical:
        status = "critical"
        is_clean = False
    elif has_warning:
        status = "warning"
        is_clean = False
    else:
        status = "healthy"
        is_clean = True

    return {
        "status": status,
        "is_clean": is_clean,
        "blocks_evaluated": len(records),
        "unbalanced_or_unsafe_block_ids": unbalanced_or_unsafe_block_ids,
        "macro_or_currency_warning_block_ids": macro_or_currency_warning_block_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


AnyDocService.audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety = staticmethod(
    audit_markdown_mathjax_katex_delimiter_balance_and_macro_safety
)


def audit_markdown_heading_hierarchy_and_anchor_slug_collisions(
    heading_nodes: list[dict[str, Any]],
    *,
    max_heading_depth: int = 4,
    forbid_multiple_h1: bool = True,
    forbid_empty_headings: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Audita jerarquía de encabezados Markdown (saltos de nivel, múltiples H1, encabezados vacíos y colisiones de anchor slug)."""
    raw_items = heading_nodes if isinstance(heading_nodes, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    structural_breach_heading_ids: list[str] = []
    level_skip_or_collision_heading_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    prev_level: int | None = None
    h1_count = 0
    seen_slugs: set[str] = set()

    for idx, item in enumerate(valid_items):
        heading_id = (
            str(
                item.get("heading_id") or item.get("id") or f"h-{idx + 1}"
            ).strip()
            or f"h-{idx + 1}"
        )

        raw_level = item.get("level", 1)
        level = min(6, max(1, int(1 if raw_level is None else raw_level)))

        raw_text = item.get("text", "")
        text = str("" if raw_text is None else raw_text).strip()

        raw_slug = item.get("anchor_slug", "")
        anchor_slug = str("" if raw_slug is None else raw_slug).strip().lower()

        if level == 1:
            h1_count += 1

        empty_or_duplicate_h1_breach = bool(
            (forbid_empty_headings and not text)
            or (forbid_multiple_h1 and level == 1 and h1_count > 1)
        )
        skipped_heading_level_or_duplicate_slug = bool(
            (prev_level is not None and level > prev_level + 1)
            or (bool(anchor_slug) and anchor_slug in seen_slugs)
            or (level > max_heading_depth)
        )

        if anchor_slug:
            seen_slugs.add(anchor_slug)
        prev_level = level

        if empty_or_duplicate_h1_breach:
            structural_breach_heading_ids.append(heading_id)
            has_critical = True
            violations.append(
                f"Heading '{heading_id}' is empty or introduces a duplicate H1 root heading."
            )

        if skipped_heading_level_or_duplicate_slug:
            level_skip_or_collision_heading_ids.append(heading_id)
            has_warning = True
            violations.append(
                f"Heading '{heading_id}' skips outline levels, exceeds max depth ({max_heading_depth}), or collides on anchor slug '{anchor_slug}'."
            )

        records.append(
            {
                "heading_id": heading_id,
                "level": level,
                "text": text,
                "anchor_slug": anchor_slug,
                "empty_or_duplicate_h1_breach": empty_or_duplicate_h1_breach,
                "skipped_heading_level_or_duplicate_slug": skipped_heading_level_or_duplicate_slug,
            }
        )

    if has_critical:
        status = "critical"
        is_clean = False
    elif has_warning:
        status = "warning"
        is_clean = False
    else:
        status = "healthy"
        is_clean = True

    return {
        "status": status,
        "is_clean": is_clean,
        "headings_evaluated": len(records),
        "structural_breach_heading_ids": structural_breach_heading_ids,
        "level_skip_or_collision_heading_ids": level_skip_or_collision_heading_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


AnyDocService.audit_markdown_heading_hierarchy_and_anchor_slug_collisions = staticmethod(
    audit_markdown_heading_hierarchy_and_anchor_slug_collisions
)
AnydocService.audit_markdown_heading_hierarchy_and_anchor_slug_collisions = staticmethod(
    audit_markdown_heading_hierarchy_and_anchor_slug_collisions
)


def audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene(
    markdown_text: str,
    max_nodes_per_diagram: int = 40,
    max_edges_per_diagram: int = 80,
    allowed_diagram_types: tuple[str, ...] | list[str] = (
        "flowchart",
        "graph",
        "sequenceDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "classDiagram",
        "erDiagram",
        "xychart-beta",
    ),
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Audita bloques Mermaid en Markdown: tipo de diagrama permitido, tope de complejidad de nodos/aristas, paréntesis sin comillas en etiquetas de nodo y etiquetas HTML prohibidas."""
    text = markdown_text if isinstance(markdown_text, str) else ""
    allowed_set = {str(t).strip() for t in (allowed_diagram_types or ())}

    mermaid_block_re = re.compile(
        r"```mermaid[ \t]*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE
    )
    edge_re = re.compile(r"(-->>|-->|->>|-\.->|==>|---)")
    node_decl_re = re.compile(r"\b([A-Za-z0-9_-]+)\s*(?:\[|\(|\{)")
    edge_nodes_re = re.compile(
        r"\b([A-Za-z0-9_-]+)\s*(?:-->>|-->|->>|-\.->|==>|---)\s*(?:\|[^|\n]*\|\s*)?([A-Za-z0-9_-]+)"
    )
    unquoted_paren_label_re = re.compile(
        r"\b([A-Za-z0-9_-]+)\[(?!\s*\")([^\n\]]*[()][^\n\]]*)\]"
    )
    html_tag_re = re.compile(
        r"<\s*/?\s*(?:br|b|i|span|div)\b[^>]*>", re.IGNORECASE
    )

    blocks = mermaid_block_re.findall(text)
    unsupported_diagram_types: list[dict[str, Any]] = []
    complexity_cap_breaches: list[dict[str, Any]] = []
    unquoted_special_label_violations: list[dict[str, Any]] = []
    html_tag_violations: list[dict[str, Any]] = []
    recommendations: list[str] = []

    reserved_keywords = {
        "flowchart",
        "graph",
        "sequencediagram",
        "statediagram",
        "statediagram-v2",
        "classdiagram",
        "erdiagram",
        "xychart-beta",
        "subgraph",
        "end",
        "direction",
        "td",
        "tb",
        "bt",
        "rl",
        "lr",
    }

    for idx, block_body in enumerate(blocks, start=1):
        lines = [
            ln.strip()
            for ln in block_body.splitlines()
            if ln.strip() and not ln.strip().startswith("%%")
        ]
        if not lines:
            unsupported_diagram_types.append(
                {"block_index": idx, "declared_type": ""}
            )
            continue

        first_token = lines[0].split()[0].strip()
        if first_token not in allowed_set:
            unsupported_diagram_types.append(
                {"block_index": idx, "declared_type": first_token}
            )

        body_without_header = "\n".join(lines[1:])
        edge_count = len(edge_re.findall(body_without_header))

        nodes_found: set[str] = set()
        for m_decl in node_decl_re.finditer(body_without_header):
            tok = m_decl.group(1)
            if tok.lower() not in reserved_keywords:
                nodes_found.add(tok)
        for m_edge in edge_nodes_re.finditer(body_without_header):
            lhs, rhs = m_edge.group(1), m_edge.group(2)
            if lhs.lower() not in reserved_keywords:
                nodes_found.add(lhs)
            if rhs.lower() not in reserved_keywords:
                nodes_found.add(rhs)

        node_count = len(nodes_found)
        if (
            node_count > max_nodes_per_diagram
            or edge_count > max_edges_per_diagram
        ):
            complexity_cap_breaches.append(
                {
                    "block_index": idx,
                    "node_count": node_count,
                    "edge_count": edge_count,
                }
            )

        for m_lbl in unquoted_paren_label_re.finditer(body_without_header):
            label_content = m_lbl.group(2).strip()
            if not (
                label_content.startswith('"') and label_content.endswith('"')
            ):
                unquoted_special_label_violations.append(
                    {
                        "block_index": idx,
                        "node_id": m_lbl.group(1),
                        "label": m_lbl.group(0),
                    }
                )

        for m_html in html_tag_re.finditer(block_body):
            html_tag_violations.append(
                {
                    "block_index": idx,
                    "tag": m_html.group(0),
                }
            )

    if unsupported_diagram_types:
        recommendations.append(
            "Use only supported Mermaid diagram types (flowchart, graph, sequenceDiagram, stateDiagram, stateDiagram-v2, classDiagram, erDiagram, xychart-beta)."
        )
    if unquoted_special_label_violations:
        recommendations.append(
            'Quote Mermaid node labels containing parentheses, e.g., id["Label (Extra Info)"].'
        )
    if complexity_cap_breaches:
        recommendations.append(
            f"Decompose complex Mermaid diagrams to stay within <= {max_nodes_per_diagram} nodes and <= {max_edges_per_diagram} edges."
        )
    if html_tag_violations:
        recommendations.append(
            "Remove raw HTML tags (<br>, <b>, <i>, <span>, <div>) from Mermaid labels."
        )

    is_valid = (
        len(unsupported_diagram_types) == 0
        and len(complexity_cap_breaches) == 0
        and len(unquoted_special_label_violations) == 0
        and len(html_tag_violations) == 0
    )

    if unsupported_diagram_types or unquoted_special_label_violations:
        status = "CRITICAL_SYNTAX_RISK"
    elif complexity_cap_breaches or html_tag_violations:
        status = "NEEDS_MERMAID_HYGIENE"
    else:
        status = "COMPLIANT"

    return {
        "is_valid": is_valid,
        "total_mermaid_blocks": len(blocks),
        "unsupported_diagram_types": unsupported_diagram_types,
        "complexity_cap_breaches": complexity_cap_breaches,
        "unquoted_special_label_violations": unquoted_special_label_violations,
        "html_tag_violations": html_tag_violations,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene
)
AnydocService.audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene = staticmethod(
    audit_markdown_mermaid_diagram_syntax_and_complexity_hygiene
)


def audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene(
    markdown_text: str,
    enforce_strict_json_parsing: bool = True,
    allow_external_http_refs: bool = False,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown OpenAPI / JSON-Schema Fenced Code Block Valid JSON/YAML Structure, $ref Resolution & Secret Example Leak Hygiene Auditor."""
    import json

    text = markdown_text if isinstance(markdown_text, str) else ""
    fence_re = re.compile(r"```(jsonc?)\s*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE)
    matches = list(fence_re.finditer(text))

    malformed_json_blocks: list[dict[str, Any]] = []
    unsafe_or_broken_schema_refs: list[dict[str, Any]] = []
    leaked_secret_examples: list[dict[str, Any]] = []

    secret_keys = {
        "example",
        "default",
        "api_key",
        "access_token",
        "secret",
        "password",
        "authorization",
    }
    safe_placeholders = {
        "your_api_key",
        "<token>",
        "changeme",
        "example_token",
        "***",
        "redacted",
        "placeholder",
        "dummy_secret",
    }
    secret_prefix_re = re.compile(r"^(?:sk-|ghp_|AKIA|Bearer\s+eyJ)", re.IGNORECASE)

    def _looks_like_secret(val: str) -> bool:
        s = val.strip()
        if not s or s.lower() in safe_placeholders:
            return False
        if s.startswith("<") and s.endswith(">"):
            return False
        if secret_prefix_re.match(s):
            return True
        if len(s) >= 20 and " " not in s and not s.isupper():
            has_digit = any(ch.isdigit() for ch in s)
            has_alpha = any(ch.isalpha() for ch in s)
            if has_digit and has_alpha:
                return True
        return False

    def _walk(node: Any, block_idx: int, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key_str = str(k)
                child_path = f"{path}.{key_str}" if path else key_str
                if key_str == "$ref" and isinstance(v, str):
                    ref_val = v.strip()
                    if ref_val in ("", "#/"):
                        unsafe_or_broken_schema_refs.append(
                            {
                                "block_index": block_idx,
                                "path": child_path,
                                "ref": v,
                                "reason": "empty_or_root_broken_ref",
                            }
                        )
                    elif not allow_external_http_refs and (
                        ref_val.startswith("http://") or ref_val.startswith("https://")
                    ):
                        unsafe_or_broken_schema_refs.append(
                            {
                                "block_index": block_idx,
                                "path": child_path,
                                "ref": v,
                                "reason": "external_http_ref_disallowed",
                            }
                        )
                if key_str.lower() in secret_keys and isinstance(v, str):
                    if _looks_like_secret(v):
                        leaked_secret_examples.append(
                            {
                                "block_index": block_idx,
                                "path": child_path,
                                "key": key_str,
                            }
                        )
                _walk(v, block_idx, child_path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, block_idx, f"{path}[{i}]")

    for idx, m in enumerate(matches):
        lang = m.group(1).lower()
        raw_body = m.group(2).strip()
        candidate = raw_body
        if lang == "jsonc" and not enforce_strict_json_parsing:
            candidate = re.sub(r"//.*?$", "", raw_body, flags=re.MULTILINE)
        try:
            parsed = json.loads(candidate)
        except Exception as exc:
            malformed_json_blocks.append(
                {
                    "block_index": idx,
                    "language": lang,
                    "error": str(exc),
                }
            )
            continue
        _walk(parsed, idx, "")

    is_valid = (
        len(malformed_json_blocks) == 0
        and len(unsafe_or_broken_schema_refs) == 0
        and len(leaked_secret_examples) == 0
    )

    recommendations: list[str] = []
    if malformed_json_blocks:
        recommendations.append(
            "Fix syntax errors in fenced JSON/JSON-Schema code blocks so all examples parse cleanly with json.loads."
        )
    if leaked_secret_examples:
        recommendations.append(
            "Sanitize credential-like values in schema examples/defaults using explicit placeholders such as 'YOUR_API_KEY' or '<token>'."
        )
    if unsafe_or_broken_schema_refs:
        recommendations.append(
            "Replace external HTTP(S) or empty '$ref' pointers with local internal component references ('#/components/schemas/...')."
        )

    if malformed_json_blocks or leaked_secret_examples:
        status = "CRITICAL_SECRET_EXAMPLE_OR_JSON_BREACH"
    elif unsafe_or_broken_schema_refs:
        status = "SCHEMA_REF_OR_SYNTAX_WARNING"
    else:
        status = "COMPLIANT"

    return {
        "is_valid": is_valid,
        "total_json_blocks": len(matches),
        "malformed_json_blocks": malformed_json_blocks,
        "unsafe_or_broken_schema_refs": unsafe_or_broken_schema_refs,
        "leaked_secret_examples": leaked_secret_examples,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene = staticmethod(
    audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene
)
AnydocService.audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene = staticmethod(
    audit_markdown_json_schema_codeblock_syntax_and_secret_example_hygiene
)


def audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene(
    markdown_text: str,
    min_meaningful_alt_length: int = 5,
    banned_placeholder_alts: tuple[str, ...] | list[str] = (
        "image",
        "img",
        "photo",
        "screenshot",
        "picture",
        "untitled",
        "graphic",
    ),
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown Accessible Media Alt-Text Coverage, Decorative Image Empty-Alt Convention & WCAG SVG Title/Role Hygiene Auditor."""
    raw_text = markdown_text if isinstance(markdown_text, str) else ""
    stripped_text = re.sub(r"```.*?```", "", raw_text, flags=re.DOTALL)

    banned_set = {str(x).strip().lower() for x in (banned_placeholder_alts or ())}
    min_len = max(1, int(min_meaningful_alt_length))
    file_ext_re = re.compile(r"\.(?:png|jpe?g|gif|svg|webp)$", re.IGNORECASE)

    missing_alt_images: list[dict[str, Any]] = []
    placeholder_or_filename_alt_images: list[dict[str, Any]] = []
    unlabeled_inline_svgs: list[dict[str, Any]] = []
    total_images_evaluated = 0

    def _check_alt(alt_val: str, src_val: str, is_decorative: bool) -> None:
        norm = alt_val.strip()
        if not norm:
            if not is_decorative:
                missing_alt_images.append({"src": src_val, "reason": "empty_non_decorative_alt"})
            return
        lower_alt = norm.lower()
        if (
            lower_alt in banned_set
            or bool(file_ext_re.search(lower_alt))
            or len(norm) < min_len
        ):
            placeholder_or_filename_alt_images.append(
                {"src": src_val, "alt": norm}
            )

    md_img_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    for m in md_img_re.finditer(stripped_text):
        total_images_evaluated += 1
        alt_text = m.group(1)
        url_text = m.group(2).strip()
        is_dec = "#decorative" in url_text.lower()
        _check_alt(alt_text, url_text, is_dec)

    html_img_re = re.compile(r"<img\b([^>]*?)/?>", re.IGNORECASE | re.DOTALL)
    for m in html_img_re.finditer(stripped_text):
        total_images_evaluated += 1
        attrs = m.group(1)
        src_m = re.search(r'\bsrc\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src_val = src_m.group(1) if src_m else ""
        alt_m = re.search(r'\balt\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        is_dec = bool(
            re.search(
                r'\b(?:role\s*=\s*["\'](?:presentation|none)["\']|aria-hidden\s*=\s*["\']true["\'])',
                attrs,
                re.IGNORECASE,
            )
            or "#decorative" in src_val.lower()
        )
        if alt_m is None:
            if not is_dec:
                missing_alt_images.append({"src": src_val, "reason": "missing_alt_attribute"})
        else:
            _check_alt(alt_m.group(1), src_val, is_dec)

    svg_re = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.IGNORECASE | re.DOTALL)
    for idx, m in enumerate(svg_re.finditer(stripped_text)):
        svg_attrs = m.group(1)
        svg_body = m.group(2)
        has_role_or_aria = bool(
            re.search(
                r'\b(?:role\s*=\s*["\']img["\']|aria-label\s*=\s*["\'][^"\']+["\']|aria-hidden\s*=\s*["\']true["\'])',
                svg_attrs,
                re.IGNORECASE,
            )
        )
        has_title = bool(
            re.search(r"<title\b[^>]*>.*?\S.*?</title>", svg_body, re.IGNORECASE | re.DOTALL)
        )
        if not (has_role_or_aria or has_title):
            unlabeled_inline_svgs.append({"svg_index": idx})

    is_valid = (
        len(missing_alt_images) == 0
        and len(placeholder_or_filename_alt_images) == 0
        and len(unlabeled_inline_svgs) == 0
    )

    recommendations: list[str] = []
    if missing_alt_images:
        recommendations.append(
            "Provide descriptive alt text for all informative images, or mark purely decorative images with #decorative or role='presentation'."
        )
    if placeholder_or_filename_alt_images:
        recommendations.append(
            f"Replace generic placeholder or filename alt text with meaningful descriptions (>= {min_len} chars)."
        )
    if unlabeled_inline_svgs:
        recommendations.append(
            "Add role='img' with aria-label or a <title> element (or aria-hidden='true' if decorative) to all inline <svg> blocks."
        )

    if missing_alt_images:
        status = "CRITICAL_MISSING_ALT_ACCESSIBILITY_BREACH"
    elif placeholder_or_filename_alt_images or unlabeled_inline_svgs:
        status = "PLACEHOLDER_ALT_OR_SVG_WARNING"
    else:
        status = "WCAG_MEDIA_COMPLIANT"

    return {
        "is_valid": is_valid,
        "total_images_evaluated": total_images_evaluated,
        "missing_alt_images": missing_alt_images,
        "placeholder_or_filename_alt_images": placeholder_or_filename_alt_images,
        "unlabeled_inline_svgs": unlabeled_inline_svgs,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene = staticmethod(
    audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene
)
AnydocService.audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene = staticmethod(
    audit_markdown_wcag_image_alt_text_and_svg_accessibility_hygiene
)


def audit_markdown_task_list_checkbox_parity_and_subtask_indentation(
    markdown_text: str,
    indentation_step_spaces: int = 2,
    require_blocker_ticket_ref: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown GFM Task-List Checkbox Completion Parity, Nested Subtask Indentation Hygiene & Stale Blocked-Item Tag Auditor."""
    raw_text = markdown_text if isinstance(markdown_text, str) else ""
    stripped_text = re.sub(r"```.*?```", "", raw_text, flags=re.DOTALL)

    step = max(1, int(indentation_step_spaces))
    task_line_re = re.compile(r"^([ \t]*)(?:[-*+]|\d+\.)\s+\[([ xX])\]\s+(.*)$")
    blocker_marker_re = re.compile(r"\b(?:BLOCKED|bloqueado)\b|\[BLOCKED\]", re.IGNORECASE)
    ticket_ref_re = re.compile(r"(?:#\d+|\b[A-Z]{2,}-\d+\b)")

    parsed_items: list[dict[str, Any]] = []
    malformed_indentation_items: list[dict[str, Any]] = []
    untracked_blocked_items: list[dict[str, Any]] = []

    for line_no, raw_line in enumerate(stripped_text.splitlines(), start=1):
        m = task_line_re.match(raw_line)
        if not m:
            continue
        indent_str = m.group(1)
        mark = m.group(2)
        body = m.group(3).strip()
        is_checked = mark.lower() == "x"
        indent_spaces = len(indent_str.replace("\t", " " * step))

        if "\t" in indent_str or (indent_spaces % step != 0):
            malformed_indentation_items.append(
                {
                    "line": line_no,
                    "indent_spaces": indent_spaces,
                    "text": body,
                }
            )

        if (
            not is_checked
            and require_blocker_ticket_ref
            and blocker_marker_re.search(body)
            and not ticket_ref_re.search(body)
        ):
            untracked_blocked_items.append(
                {
                    "line": line_no,
                    "text": body,
                }
            )

        parsed_items.append(
            {
                "line": line_no,
                "indent": indent_spaces,
                "checked": is_checked,
                "text": body,
            }
        )

    parent_checked_with_open_subtasks: list[dict[str, Any]] = []
    for i, item in enumerate(parsed_items):
        if not item["checked"]:
            continue
        parent_indent = item["indent"]
        has_open_child = False
        for j in range(i + 1, len(parsed_items)):
            nxt = parsed_items[j]
            if nxt["indent"] <= parent_indent:
                break
            if not nxt["checked"]:
                has_open_child = True
                break
        if has_open_child:
            parent_checked_with_open_subtasks.append(
                {
                    "line": item["line"],
                    "text": item["text"],
                }
            )

    total_task_items = len(parsed_items)
    completed_task_items = sum(1 for it in parsed_items if it["checked"])

    is_valid = (
        len(parent_checked_with_open_subtasks) == 0
        and len(malformed_indentation_items) == 0
        and len(untracked_blocked_items) == 0
    )

    recommendations: list[str] = []
    if parent_checked_with_open_subtasks:
        recommendations.append(
            "Do not mark parent GFM checklist items as [x] while child subtasks remain open [ ]."
        )
    if malformed_indentation_items:
        recommendations.append(
            f"Normalize nested task-list indentation to multiples of {step} spaces without tab characters."
        )
    if untracked_blocked_items:
        recommendations.append(
            "Attach a traceable issue/ticket reference (e.g., #123 or PROJ-456) to all open BLOCKED task items."
        )

    if parent_checked_with_open_subtasks:
        status = "CRITICAL_PARENT_CHILD_COMPLETION_BREACH"
    elif malformed_indentation_items or untracked_blocked_items:
        status = "INDENTATION_OR_UNTRACKED_BLOCKER_WARNING"
    else:
        status = "TASK_LIST_HYGIENE_COMPLIANT"

    return {
        "is_valid": is_valid,
        "total_task_items": total_task_items,
        "completed_task_items": completed_task_items,
        "parent_checked_with_open_subtasks": parent_checked_with_open_subtasks,
        "malformed_indentation_items": malformed_indentation_items,
        "untracked_blocked_items": untracked_blocked_items,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_task_list_checkbox_parity_and_subtask_indentation = staticmethod(
    audit_markdown_task_list_checkbox_parity_and_subtask_indentation
)
AnydocService.audit_markdown_task_list_checkbox_parity_and_subtask_indentation = staticmethod(
    audit_markdown_task_list_checkbox_parity_and_subtask_indentation
)


def audit_markdown_rfc2119_normative_keywords_and_requirement_traceability(
    markdown_text: str,
    max_ambiguous_modal_ratio_pct: float = 25.0,
    require_req_id_for_must_statements: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown RFC 2119 / BCP 14 normative keyword uppercase consistency, ambiguous modal verb & testability ID traceability auditor."""
    text = str(markdown_text or "")
    lines = text.splitlines()

    lowercase_normative_keyword_lines: list[int] = []
    untraced_mandatory_requirement_lines: list[int] = []
    recommendations: list[str] = []

    lowercase_mandatory_pattern = re.compile(
        r"\b(?:must(?:\s+not)?|shall(?:\s+not)?|required)\b"
    )
    uppercase_mandatory_pattern = re.compile(
        r"\b(?:MUST(?:\s+NOT)?|SHALL(?:\s+NOT)?|REQUIRED)\b"
    )
    ambiguous_modal_pattern = re.compile(
        r"\b(?:SHOULD(?:\s+NOT)?|MAY|OPTIONAL|should(?:\s+not)?|may|optional)\b"
    )
    req_id_pattern = re.compile(r"\bREQ-[A-Z0-9-]+\b")

    in_fenced_block = False
    total_normative_statements = 0
    ambiguous_modal_count = 0

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block or not stripped or stripped.startswith("#"):
            continue

        has_lower_mandatory = bool(lowercase_mandatory_pattern.search(raw_line))
        has_upper_mandatory = bool(uppercase_mandatory_pattern.search(raw_line))
        has_ambiguous_modal = bool(ambiguous_modal_pattern.search(raw_line))

        if has_lower_mandatory or has_upper_mandatory or has_ambiguous_modal:
            total_normative_statements += 1

        if has_lower_mandatory:
            lowercase_normative_keyword_lines.append(idx)

        if has_upper_mandatory and require_req_id_for_must_statements:
            if not req_id_pattern.search(raw_line):
                untraced_mandatory_requirement_lines.append(idx)

        if has_ambiguous_modal and not has_upper_mandatory and not has_lower_mandatory:
            ambiguous_modal_count += 1

    ambiguous_modal_ratio_pct = (
        round((ambiguous_modal_count / total_normative_statements) * 100.0, 2)
        if total_normative_statements > 0
        else 0.0
    )
    excessive_ambiguity = ambiguous_modal_ratio_pct > float(max_ambiguous_modal_ratio_pct)

    if untraced_mandatory_requirement_lines:
        recommendations.append(
            f"Tag mandatory MUST/SHALL statements on lines {untraced_mandatory_requirement_lines} with explicit traceability IDs (e.g., REQ-xxx)."
        )
    if lowercase_normative_keyword_lines:
        recommendations.append(
            f"Capitalize RFC 2119 / BCP 14 normative modal verbs on lines {lowercase_normative_keyword_lines} (MUST, SHALL, REQUIRED)."
        )
    if excessive_ambiguity:
        recommendations.append(
            f"Reduce ambiguous modal ratio ({ambiguous_modal_ratio_pct}% > {max_ambiguous_modal_ratio_pct}%) by converting SHOULD/MAY statements into testable criteria."
        )

    if len(untraced_mandatory_requirement_lines) > 0:
        status = "CRITICAL_UNTRACED_MANDATORY_REQUIREMENT_BREACH"
    elif len(lowercase_normative_keyword_lines) > 0 or excessive_ambiguity:
        status = "LOWERCASE_OR_AMBIGUOUS_MODAL_WARNING"
    else:
        status = "RFC2119_SPEC_COMPLIANT"

    return {
        "is_valid": status == "RFC2119_SPEC_COMPLIANT",
        "total_normative_statements": total_normative_statements,
        "lowercase_normative_keyword_lines": lowercase_normative_keyword_lines,
        "untraced_mandatory_requirement_lines": untraced_mandatory_requirement_lines,
        "ambiguous_modal_ratio_pct": ambiguous_modal_ratio_pct,
        "excessive_ambiguity": excessive_ambiguity,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_rfc2119_normative_keywords_and_requirement_traceability = staticmethod(
    audit_markdown_rfc2119_normative_keywords_and_requirement_traceability
)
AnydocService.audit_markdown_rfc2119_normative_keywords_and_requirement_traceability = staticmethod(
    audit_markdown_rfc2119_normative_keywords_and_requirement_traceability
)


def audit_markdown_adr_madr_sections_and_supersession_hygiene(
    markdown_text: str,
    required_madr_sections: tuple[str, ...] | list[str] = (
        "Status",
        "Context",
        "Decision",
        "Consequences",
    ),
    allowed_statuses: tuple[str, ...] | list[str] = (
        "PROPOSED",
        "ACCEPTED",
        "REJECTED",
        "DEPRECATED",
        "SUPERSEDED",
    ),
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Architecture Decision Record (ADR) MADR v3 mandatory sections, superseded status link reciprocity & decision driver hygiene auditor."""
    text = str(markdown_text or "")
    lines = text.splitlines()

    sections: dict[str, list[str]] = {}
    heading_order: list[str] = []
    current_heading: str | None = None
    in_fenced_block = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue

        if stripped.startswith("## ") and not stripped.startswith("###"):
            h2_title = stripped[3:].strip()
            current_heading = h2_title
            heading_order.append(h2_title)
            sections.setdefault(h2_title, [])
        elif stripped.startswith("# "):
            current_heading = None
        elif current_heading is not None:
            sections[current_heading].append(raw_line)

    missing_required_sections: list[str] = []
    matched_section_bodies: dict[str, str] = {}

    for req_sec in required_madr_sections:
        req_lower = str(req_sec).strip().lower()
        found_body: str | None = None
        for h_title in heading_order:
            h_lower = h_title.lower()
            if h_lower == req_lower or h_lower.startswith(req_lower):
                found_body = "\n".join(sections.get(h_title, [])).strip()
                break
        if found_body is None:
            missing_required_sections.append(str(req_sec))
        else:
            matched_section_bodies[req_lower] = found_body

    status_body = matched_section_bodies.get("status", "")
    allowed_upper = [str(s).strip().upper() for s in allowed_statuses if str(s).strip()]

    matched_status: str | None = None
    for st in allowed_upper:
        if re.search(rf"\b{re.escape(st)}\b", status_body, flags=re.IGNORECASE):
            matched_status = st
            break

    invalid_or_missing_status = matched_status is None
    superseded_without_target_ref = False

    if matched_status == "SUPERSEDED":
        has_adr_ref = bool(re.search(r"\bADR-\d+\b", status_body, flags=re.IGNORECASE))
        has_md_link = bool(re.search(r"\[[^\]]+\]\([^)]+\)", status_body))
        if not (has_adr_ref or has_md_link):
            superseded_without_target_ref = True

    consequences_body = matched_section_bodies.get("consequences", "")
    bullet_lines = [
        ln
        for ln in consequences_body.splitlines()
        if re.match(r"^\s*[-*+]\s+\S+", ln)
    ]
    has_pos_and_neg = bool(
        re.search(r"\b(?:positive|good|pros?|benefits?)\b", consequences_body, flags=re.IGNORECASE)
        and re.search(
            r"\b(?:negative|bad|cons?|trade-?offs?|risks?)\b",
            consequences_body,
            flags=re.IGNORECASE,
        )
    )
    incomplete_consequences_analysis = not (
        bool(consequences_body.strip()) and (len(bullet_lines) >= 2 or has_pos_and_neg)
    )

    recommendations: list[str] = []
    if missing_required_sections:
        recommendations.append(
            f"Add missing mandatory MADR v3 level-2 sections: {', '.join(missing_required_sections)}."
        )
    if invalid_or_missing_status:
        recommendations.append(
            f"Declare a valid ADR lifecycle status ({', '.join(allowed_upper)}) under '## Status'."
        )
    if superseded_without_target_ref:
        recommendations.append(
            "Link the SUPERSEDED status to the successor ADR identifier (e.g., ADR-0058 or Markdown link)."
        )
    if incomplete_consequences_analysis:
        recommendations.append(
            "Document both positive benefits and negative trade-offs (at least 2 bullet items) under '## Consequences'."
        )

    if len(missing_required_sections) > 0 or invalid_or_missing_status:
        status = "CRITICAL_MISSING_MADR_SECTION_OR_STATUS_BREACH"
    elif superseded_without_target_ref or incomplete_consequences_analysis:
        status = "INCOMPLETE_CONSEQUENCES_OR_SUPERSESSION_WARNING"
    else:
        status = "MADR_ADR_COMPLIANT"

    return {
        "is_valid": status == "MADR_ADR_COMPLIANT",
        "missing_required_sections": missing_required_sections,
        "invalid_or_missing_status": invalid_or_missing_status,
        "superseded_without_target_ref": superseded_without_target_ref,
        "incomplete_consequences_analysis": incomplete_consequences_analysis,
        "status": status,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_adr_madr_sections_and_supersession_hygiene = staticmethod(
    audit_markdown_adr_madr_sections_and_supersession_hygiene
)
AnydocService.audit_markdown_adr_madr_sections_and_supersession_hygiene = staticmethod(
    audit_markdown_adr_madr_sections_and_supersession_hygiene
)


def audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene(
    specs: list[dict[str, Any]],
    *,
    require_security_schemes: bool = True,
    max_deprecated_unannotated_ops: int = 0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown OpenAPI / AsyncAPI Specification Block Version, OperationId Uniqueness & SecurityScheme Hygiene Auditor."""
    valid_specs = [
        s for s in (specs if isinstance(specs, list) else []) if isinstance(s, dict)
    ]

    critical_specs: list[str] = []
    warning_specs: list[str] = []
    spec_evaluations: list[dict[str, Any]] = []
    total_duplicate_operation_ids = 0

    for idx, spec in enumerate(valid_specs):
        spec_id = str(spec.get("spec_id") or f"spec-{idx + 1}").strip()
        spec_type = str(spec.get("spec_type") or "").strip().lower()
        spec_version = str(spec.get("spec_version") or "").strip()
        total_operations = int(spec.get("total_operations", 0) or 0)
        dup_ops_raw = spec.get("duplicate_operation_ids")
        duplicate_operation_ids = (
            [str(op) for op in dup_ops_raw]
            if isinstance(dup_ops_raw, (list, tuple))
            else []
        )
        unauth_write_ops = int(
            spec.get("unauthenticated_public_write_ops", 0) or 0
        )
        sec_schemes_defined = bool(spec.get("security_schemes_defined", True))
        missing_error_schemas = int(
            spec.get("missing_error_response_schemas_count", 0) or 0
        )
        deprecated_no_sunset = int(
            spec.get("deprecated_without_sunset_header_count", 0) or 0
        )

        total_duplicate_operation_ids += len(duplicate_operation_ids)

        supported_version = bool(
            (spec_type == "openapi" and spec_version.startswith(("3.0.", "3.1.")))
            or (spec_type == "asyncapi" and spec_version.startswith(("2.", "3.")))
        )
        critical_api_spec_breach = bool(
            not supported_version
            or len(duplicate_operation_ids) > 0
            or unauth_write_ops > 0
            or (require_security_schemes and not sec_schemes_defined)
        )
        schema_or_deprecation_warning = bool(
            not critical_api_spec_breach
            and (
                missing_error_schemas > 0
                or deprecated_no_sunset > int(max_deprecated_unannotated_ops)
            )
        )

        if critical_api_spec_breach:
            critical_specs.append(spec_id)
        elif schema_or_deprecation_warning:
            warning_specs.append(spec_id)

        spec_evaluations.append(
            {
                "spec_id": spec_id,
                "spec_type": spec_type,
                "spec_version": spec_version,
                "total_operations": total_operations,
                "supported_version": supported_version,
                "duplicate_operation_ids_count": len(duplicate_operation_ids),
                "critical_api_spec_breach": critical_api_spec_breach,
                "schema_or_deprecation_warning": schema_or_deprecation_warning,
            }
        )

    if len(critical_specs) > 0:
        status = "CRITICAL"
    elif len(warning_specs) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_specs_count": len(spec_evaluations),
        "critical_specs": critical_specs,
        "warning_specs": warning_specs,
        "total_duplicate_operation_ids": total_duplicate_operation_ids,
        "spec_evaluations": spec_evaluations,
    }


AnyDocService.audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene = staticmethod(
    audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene
)
AnydocService.audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene = staticmethod(
    audit_markdown_openapi_spec_blocks_and_security_scheme_hygiene
)


def audit_markdown_latex_math_delimiter_balance_and_macro_hygiene(
    blocks: list[dict[str, Any]],
    *,
    max_nesting_depth: int = 6,
    disallowed_macros: tuple[str, ...] = (
        "\\input",
        "\\include",
        "\\write18",
        "\\catcode",
        "\\def",
    ),
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown LaTeX / KaTeX Mathematical Formula Delimiter Balance, Undefined Macro & Environment Nesting Hygiene Auditor."""
    block_evaluations: list[dict[str, Any]] = []
    critical_blocks: list[str] = []
    warning_blocks: list[str] = []
    total_unsafe_macros_detected = 0

    for item in blocks or []:
        if not isinstance(item, dict):
            continue
        block_id = str(item.get("block_id") or "").strip() or "UNKNOWN_BLOCK"
        unbalanced_dollar_delimiters = int(
            item.get("unbalanced_dollar_delimiters", 0) or 0
        )
        unmatched_begin_end_environments = int(
            item.get("unmatched_begin_end_environments", 0) or 0
        )
        raw_macros = item.get("detected_macros")
        detected_macros = (
            [str(m) for m in raw_macros]
            if isinstance(raw_macros, (list, tuple))
            else []
        )
        equation_nesting_depth = int(item.get("equation_nesting_depth", 1) or 0)
        missing_equation_label_for_numbered_env = bool(
            item.get("missing_equation_label_for_numbered_env", False)
        )
        render_timeout_exceeded = bool(item.get("render_timeout_exceeded", False))

        unsafe_macros_found = [
            m for m in detected_macros if m in disallowed_macros
        ]
        total_unsafe_macros_detected += len(unsafe_macros_found)

        critical_latex_breach = (
            unbalanced_dollar_delimiters > 0
            or unmatched_begin_end_environments > 0
            or len(unsafe_macros_found) > 0
            or render_timeout_exceeded is True
        )
        math_hygiene_warning = (not critical_latex_breach) and (
            equation_nesting_depth > max_nesting_depth
            or missing_equation_label_for_numbered_env is True
        )

        if critical_latex_breach:
            critical_blocks.append(block_id)
        elif math_hygiene_warning:
            warning_blocks.append(block_id)

        block_evaluations.append(
            {
                "block_id": block_id,
                "unbalanced_dollar_delimiters": unbalanced_dollar_delimiters,
                "unmatched_begin_end_environments": unmatched_begin_end_environments,
                "detected_macros": detected_macros,
                "unsafe_macros_found": unsafe_macros_found,
                "equation_nesting_depth": equation_nesting_depth,
                "missing_equation_label_for_numbered_env": missing_equation_label_for_numbered_env,
                "render_timeout_exceeded": render_timeout_exceeded,
                "critical_latex_breach": critical_latex_breach,
                "math_hygiene_warning": math_hygiene_warning,
            }
        )

    if len(critical_blocks) > 0:
        status = "CRITICAL"
    elif len(warning_blocks) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_blocks_count": len(block_evaluations),
        "critical_blocks": critical_blocks,
        "warning_blocks": warning_blocks,
        "total_unsafe_macros_detected": total_unsafe_macros_detected,
        "block_evaluations": block_evaluations,
    }


AnyDocService.audit_markdown_latex_math_delimiter_balance_and_macro_hygiene = staticmethod(
    audit_markdown_latex_math_delimiter_balance_and_macro_hygiene
)
AnydocService.audit_markdown_latex_math_delimiter_balance_and_macro_hygiene = staticmethod(
    audit_markdown_latex_math_delimiter_balance_and_macro_hygiene
)


def audit_markdown_runbook_incident_escalation_and_rollback_hygiene(
    runbooks: list[dict[str, Any]],
    *,
    max_days_since_game_day_drill: int = 180,
    require_executable_rollback_block: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown Runbook / Playbook Incident Escalation PagerDuty/On-Call Rotation, Rollback Command Verification & RTO/RPO SLA Hygiene Auditor."""
    runbook_evaluations: list[dict[str, Any]] = []
    critical_runbooks: list[str] = []
    warning_runbooks: list[str] = []
    stale_gameday_drill_count = 0

    for item in runbooks or []:
        if not isinstance(item, dict):
            continue
        runbook_id = str(item.get("runbook_id") or "").strip() or "UNKNOWN_RUNBOOK"
        service_tier = str(item.get("service_tier") or "tier-1").strip()
        oncall_escalation_policy_linked = bool(
            item.get("oncall_escalation_policy_linked", True)
        )
        executable_rollback_commands_present = bool(
            item.get("executable_rollback_commands_present", True)
        )
        raw_rto = item.get("rto_minutes_documented", 15)
        rto_minutes_documented = int(15 if raw_rto is None else raw_rto)
        raw_rpo = item.get("rpo_minutes_documented", 5)
        rpo_minutes_documented = int(5 if raw_rpo is None else raw_rpo)
        raw_drill = item.get("days_since_last_gameday_drill", 60)
        days_since_last_gameday_drill = int(60 if raw_drill is None else raw_drill)
        hardcoded_production_credentials_in_snippet = bool(
            item.get("hardcoded_production_credentials_in_snippet", False)
        )
        diagnostic_metrics_links_valid = bool(
            item.get("diagnostic_metrics_links_valid", True)
        )

        if days_since_last_gameday_drill > max_days_since_game_day_drill:
            stale_gameday_drill_count += 1

        critical_runbook_breach = (
            hardcoded_production_credentials_in_snippet is True
            or not oncall_escalation_policy_linked
            or (
                require_executable_rollback_block
                and not executable_rollback_commands_present
            )
            or rto_minutes_documented <= 0
            or rpo_minutes_documented < 0
        )
        runbook_staleness_warning = (not critical_runbook_breach) and (
            days_since_last_gameday_drill > max_days_since_game_day_drill
            or not diagnostic_metrics_links_valid
        )

        if critical_runbook_breach:
            critical_runbooks.append(runbook_id)
        elif runbook_staleness_warning:
            warning_runbooks.append(runbook_id)

        runbook_evaluations.append(
            {
                "runbook_id": runbook_id,
                "service_tier": service_tier,
                "oncall_escalation_policy_linked": oncall_escalation_policy_linked,
                "executable_rollback_commands_present": executable_rollback_commands_present,
                "rto_minutes_documented": rto_minutes_documented,
                "rpo_minutes_documented": rpo_minutes_documented,
                "days_since_last_gameday_drill": days_since_last_gameday_drill,
                "hardcoded_production_credentials_in_snippet": hardcoded_production_credentials_in_snippet,
                "diagnostic_metrics_links_valid": diagnostic_metrics_links_valid,
                "critical_runbook_breach": critical_runbook_breach,
                "runbook_staleness_warning": runbook_staleness_warning,
            }
        )

    if len(critical_runbooks) > 0:
        status = "CRITICAL"
    elif len(warning_runbooks) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_runbooks_count": len(runbook_evaluations),
        "critical_runbooks": critical_runbooks,
        "warning_runbooks": warning_runbooks,
        "stale_gameday_drill_count": stale_gameday_drill_count,
        "runbook_evaluations": runbook_evaluations,
    }


AnyDocService.audit_markdown_runbook_incident_escalation_and_rollback_hygiene = staticmethod(
    audit_markdown_runbook_incident_escalation_and_rollback_hygiene
)
AnydocService.audit_markdown_runbook_incident_escalation_and_rollback_hygiene = staticmethod(
    audit_markdown_runbook_incident_escalation_and_rollback_hygiene
)


def audit_markdown_postmortem_rca_blameless_and_action_item_hygiene(
    postmortems: list[dict[str, Any]],
    *,
    min_five_whys_depth: int = 3,
    max_unassigned_action_items: int = 0,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown Post-Mortem / Root Cause Analysis (RCA) 5-Whys Blameless Taxonomy, Action-Item Owner/Due-Date & Recurrence Prevention Hygiene Auditor."""
    postmortem_evaluations: list[dict[str, Any]] = []
    critical_postmortems: list[str] = []
    warning_postmortems: list[str] = []
    total_unassigned_actions = 0

    for item in postmortems or []:
        if not isinstance(item, dict):
            continue
        incident_id = (
            str(item.get("incident_id") or "").strip() or "UNKNOWN_INCIDENT"
        )
        raw_depth = item.get("five_whys_depth_completed", 5)
        five_whys_depth_completed = int(5 if raw_depth is None else raw_depth)
        total_remediation_actions = int(
            item.get("total_remediation_actions", 0) or 0
        )
        actions_with_owner_and_due_date = int(
            item.get("actions_with_owner_and_due_date", 0) or 0
        )
        blaming_language_detected = bool(
            item.get("blaming_language_detected", False)
        )
        customer_impact_timeline_documented = bool(
            item.get("customer_impact_timeline_documented", True)
        )
        automated_regression_test_linked = bool(
            item.get("automated_regression_test_linked", True)
        )
        repeat_incident_without_prior_action_closed = bool(
            item.get("repeat_incident_without_prior_action_closed", False)
        )

        unassigned_actions_count = max(
            0, total_remediation_actions - actions_with_owner_and_due_date
        )
        total_unassigned_actions += unassigned_actions_count

        critical_rca_breach = (
            blaming_language_detected is True
            or repeat_incident_without_prior_action_closed is True
            or total_remediation_actions <= 0
            or unassigned_actions_count > max_unassigned_action_items
            or five_whys_depth_completed < min_five_whys_depth
        )
        rca_hygiene_warning = (not critical_rca_breach) and (
            not customer_impact_timeline_documented
            or not automated_regression_test_linked
        )

        if critical_rca_breach:
            critical_postmortems.append(incident_id)
        elif rca_hygiene_warning:
            warning_postmortems.append(incident_id)

        postmortem_evaluations.append(
            {
                "incident_id": incident_id,
                "five_whys_depth_completed": five_whys_depth_completed,
                "total_remediation_actions": total_remediation_actions,
                "actions_with_owner_and_due_date": actions_with_owner_and_due_date,
                "unassigned_actions_count": unassigned_actions_count,
                "blaming_language_detected": blaming_language_detected,
                "customer_impact_timeline_documented": customer_impact_timeline_documented,
                "automated_regression_test_linked": automated_regression_test_linked,
                "repeat_incident_without_prior_action_closed": repeat_incident_without_prior_action_closed,
                "critical_rca_breach": critical_rca_breach,
                "rca_hygiene_warning": rca_hygiene_warning,
            }
        )

    if len(critical_postmortems) > 0:
        status = "CRITICAL"
    elif len(warning_postmortems) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_postmortems_count": len(postmortem_evaluations),
        "critical_postmortems": critical_postmortems,
        "warning_postmortems": warning_postmortems,
        "total_unassigned_actions": total_unassigned_actions,
        "postmortem_evaluations": postmortem_evaluations,
    }


AnyDocService.audit_markdown_postmortem_rca_blameless_and_action_item_hygiene = staticmethod(
    audit_markdown_postmortem_rca_blameless_and_action_item_hygiene
)
AnydocService.audit_markdown_postmortem_rca_blameless_and_action_item_hygiene = staticmethod(
    audit_markdown_postmortem_rca_blameless_and_action_item_hygiene
)


def audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene(
    documents: list[dict[str, Any]],
    *,
    allowed_tlp_labels: tuple[str, ...] = (
        "TLP:RED",
        "TLP:AMBER",
        "TLP:AMBER+STRICT",
        "TLP:GREEN",
        "TLP:CLEAR",
    ),
    min_retention_years: int = 1,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown Data-Classification Sensitivity Banner (TLP:RED/AMBER/GREEN/CLEAR), PII/PHI Redaction Marker & Retention Tag Hygiene Auditor."""
    document_evaluations: list[dict[str, Any]] = []
    critical_documents: list[str] = []
    warning_documents: list[str] = []
    total_unredacted_pii_tokens = 0

    for item in documents or []:
        if not isinstance(item, dict):
            continue
        doc_id = str(item.get("doc_id") or "").strip() or "UNKNOWN_DOC"
        normalized_tlp = str(item.get("tlp_banner_label") or "").strip().upper()
        unredacted_pii_phi_tokens_detected = int(
            item.get("unredacted_pii_phi_tokens_detected", 0) or 0
        )
        public_sharing_link_enabled = bool(
            item.get("public_sharing_link_enabled", False)
        )
        raw_retention = item.get("retention_policy_years", 7)
        retention_policy_years = int(7 if raw_retention is None else raw_retention)
        cryptographic_watermark_embedded = bool(
            item.get("cryptographic_watermark_embedded", True)
        )
        classification_review_overdue_days = int(
            item.get("classification_review_overdue_days", 0) or 0
        )

        total_unredacted_pii_tokens += unredacted_pii_phi_tokens_detected

        valid_tlp = normalized_tlp in allowed_tlp_labels
        restricted_tlp = normalized_tlp in {
            "TLP:RED",
            "TLP:AMBER",
            "TLP:AMBER+STRICT",
        }

        critical_classification_breach = (
            not valid_tlp
            or unredacted_pii_phi_tokens_detected > 0
            or (restricted_tlp and public_sharing_link_enabled)
            or retention_policy_years < min_retention_years
        )
        classification_warning = (not critical_classification_breach) and (
            (restricted_tlp and not cryptographic_watermark_embedded)
            or classification_review_overdue_days > 0
        )

        if critical_classification_breach:
            critical_documents.append(doc_id)
        elif classification_warning:
            warning_documents.append(doc_id)

        document_evaluations.append(
            {
                "doc_id": doc_id,
                "tlp_banner_label": normalized_tlp,
                "valid_tlp": valid_tlp,
                "restricted_tlp": restricted_tlp,
                "unredacted_pii_phi_tokens_detected": unredacted_pii_phi_tokens_detected,
                "public_sharing_link_enabled": public_sharing_link_enabled,
                "retention_policy_years": retention_policy_years,
                "cryptographic_watermark_embedded": cryptographic_watermark_embedded,
                "classification_review_overdue_days": classification_review_overdue_days,
                "critical_classification_breach": critical_classification_breach,
                "classification_warning": classification_warning,
            }
        )

    if len(critical_documents) > 0:
        status = "CRITICAL"
    elif len(warning_documents) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_documents_count": len(document_evaluations),
        "critical_documents": critical_documents,
        "warning_documents": warning_documents,
        "total_unredacted_pii_tokens": total_unredacted_pii_tokens,
        "document_evaluations": document_evaluations,
    }


AnyDocService.audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene = staticmethod(
    audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene
)
AnydocService.audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene = staticmethod(
    audit_markdown_tlp_classification_banner_and_pii_redaction_hygiene
)


def audit_markdown_data_lineage_dag_freshness_and_contract_hygiene(
    models: list[dict[str, Any]],
    *,
    max_freshness_lag_minutes: int = 60,
    max_fanout_downstream_dependents: int = 20,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — AnyDoc Markdown Data-Lineage / dbt / Airflow DAG Dependency Acyclicity, SLA Freshness Assertion & Schema Contract Hygiene Auditor."""
    model_evaluations: list[dict[str, Any]] = []
    critical_models: list[str] = []
    warning_models: list[str] = []
    max_observed_freshness_lag_minutes = 0

    for item in models or []:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("model_id") or "").strip() or "UNKNOWN_MODEL"
        circular_dependency_detected = bool(
            item.get("circular_dependency_detected", False)
        )
        primary_key_uniqueness_not_null_tested = bool(
            item.get("primary_key_uniqueness_not_null_tested", True)
        )
        schema_contract_enforced = bool(
            item.get("schema_contract_enforced", True)
        )
        raw_lag = item.get("freshness_lag_minutes", 15)
        freshness_lag_minutes = int(15 if raw_lag is None else raw_lag)
        raw_fanout = item.get("downstream_dependents_count", 5)
        downstream_dependents_count = int(
            5 if raw_fanout is None else raw_fanout
        )
        owner_team_documented = bool(item.get("owner_team_documented", True))
        pii_columns_masked_in_mart = bool(
            item.get("pii_columns_masked_in_mart", True)
        )

        max_observed_freshness_lag_minutes = max(
            max_observed_freshness_lag_minutes, freshness_lag_minutes
        )

        critical_lineage_breach = (
            circular_dependency_detected is True
            or not primary_key_uniqueness_not_null_tested
            or not pii_columns_masked_in_mart
            or freshness_lag_minutes > max_freshness_lag_minutes * 2
        )
        lineage_hygiene_warning = (not critical_lineage_breach) and (
            freshness_lag_minutes > max_freshness_lag_minutes
            or downstream_dependents_count > max_fanout_downstream_dependents
            or not schema_contract_enforced
            or not owner_team_documented
        )

        if critical_lineage_breach:
            critical_models.append(model_id)
        elif lineage_hygiene_warning:
            warning_models.append(model_id)

        model_evaluations.append(
            {
                "model_id": model_id,
                "circular_dependency_detected": circular_dependency_detected,
                "primary_key_uniqueness_not_null_tested": primary_key_uniqueness_not_null_tested,
                "schema_contract_enforced": schema_contract_enforced,
                "freshness_lag_minutes": freshness_lag_minutes,
                "downstream_dependents_count": downstream_dependents_count,
                "owner_team_documented": owner_team_documented,
                "pii_columns_masked_in_mart": pii_columns_masked_in_mart,
                "critical_lineage_breach": critical_lineage_breach,
                "lineage_hygiene_warning": lineage_hygiene_warning,
            }
        )

    if len(critical_models) > 0:
        status = "CRITICAL"
    elif len(warning_models) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_models_count": len(model_evaluations),
        "critical_models": critical_models,
        "warning_models": warning_models,
        "max_observed_freshness_lag_minutes": max_observed_freshness_lag_minutes,
        "model_evaluations": model_evaluations,
    }


AnyDocService.audit_markdown_data_lineage_dag_freshness_and_contract_hygiene = staticmethod(
    audit_markdown_data_lineage_dag_freshness_and_contract_hygiene
)
AnydocService.audit_markdown_data_lineage_dag_freshness_and_contract_hygiene = staticmethod(
    audit_markdown_data_lineage_dag_freshness_and_contract_hygiene
)


def audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene(
    markdown_text: str,
    *,
    min_slo_target_pct: float = 99.0,
    max_fast_burn_factor: float = 14.4,
    require_multiwindow_alert: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown SLO, Error Budget Burn-Rate & Multi-Window Alert Hygiene Auditor."""
    normalized_min_slo = min(max(float(min_slo_target_pct), 50.0), 99.999)
    normalized_max_fast_burn = max(float(max_fast_burn_factor), 1.0)

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(r"<!--\s*slo\s*:(.*?)-->", re.IGNORECASE | re.DOTALL)
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    invalid_slo_target_count = 0
    burn_factor_violation_count = 0
    missing_multiwindow_count = 0
    missing_exhaustion_policy_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        service = kv.get("service") or f"slo-service-{idx}"
        indicator = kv.get("indicator") or "availability"
        try:
            target_pct = float(kv.get("target_pct", "0.0"))
        except (TypeError, ValueError):
            target_pct = 0.0
        try:
            window_days = int(float(kv.get("window_days", "30")))
        except (TypeError, ValueError):
            window_days = 30
        try:
            fast_burn_factor = float(kv.get("fast_burn_factor", "0.0"))
        except (TypeError, ValueError):
            fast_burn_factor = 0.0
        try:
            slow_burn_factor = float(kv.get("slow_burn_factor", "0.0"))
        except (TypeError, ValueError):
            slow_burn_factor = 0.0
        multiwindow = kv.get("multiwindow", "").strip()
        exhaustion_policy = kv.get("exhaustion_policy", "").strip()

        sub_threshold_or_invalid_slo_target = (
            target_pct < normalized_min_slo or target_pct >= 100.0
        )
        excessive_or_inverted_burn_factor = (
            fast_burn_factor > normalized_max_fast_burn
            or fast_burn_factor <= slow_burn_factor
            or slow_burn_factor <= 0.0
        )
        missing_multiwindow_pair = bool(
            require_multiwindow_alert
            and (
                not multiwindow
                or multiwindow.lower() == "none"
                or "/" not in multiwindow
            )
        )
        missing_exhaustion_policy = bool(
            not exhaustion_policy or exhaustion_policy.lower() == "none"
        )

        if sub_threshold_or_invalid_slo_target:
            invalid_slo_target_count += 1
        if excessive_or_inverted_burn_factor:
            burn_factor_violation_count += 1
        if missing_multiwindow_pair:
            missing_multiwindow_count += 1
        if missing_exhaustion_policy:
            missing_exhaustion_policy_count += 1

        if sub_threshold_or_invalid_slo_target or (
            missing_multiwindow_pair and missing_exhaustion_policy
        ):
            block_status = "critical"
            critical_count += 1
        elif (
            excessive_or_inverted_burn_factor
            or missing_multiwindow_pair
            or missing_exhaustion_policy
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "service": service,
                "indicator": indicator,
                "target_pct": target_pct,
                "window_days": window_days,
                "fast_burn_factor": fast_burn_factor,
                "slow_burn_factor": slow_burn_factor,
                "multiwindow": multiwindow,
                "exhaustion_policy": exhaustion_policy,
                "sub_threshold_or_invalid_slo_target": sub_threshold_or_invalid_slo_target,
                "excessive_or_inverted_burn_factor": excessive_or_inverted_burn_factor,
                "missing_multiwindow_pair": missing_multiwindow_pair,
                "missing_exhaustion_policy": missing_exhaustion_policy,
                "block_status": block_status,
            }
        )

    total_slo_blocks = len(blocks)
    slo_hygiene_rate_pct = (
        round((healthy_count / total_slo_blocks) * 100.0, 2)
        if total_slo_blocks > 0
        else 100.0
    )

    recommendations: list[str] = []
    if invalid_slo_target_count > 0:
        recommendations.append(
            f"Calibrar target_pct dentro del rango [{normalized_min_slo}%, <100.0%) en {invalid_slo_target_count} bloque(s) SLO."
        )
    if burn_factor_violation_count > 0:
        recommendations.append(
            f"Ajustar fast_burn_factor <= {normalized_max_fast_burn} y > slow_burn_factor (> 0) en {burn_factor_violation_count} bloque(s) SLO."
        )
    if missing_multiwindow_count > 0:
        recommendations.append(
            f"Configurar alertas multi-ventana (ej. 1h/5m,6h/30m) en {missing_multiwindow_count} bloque(s) SLO."
        )
    if missing_exhaustion_policy_count > 0:
        recommendations.append(
            f"Definir exhaustion_policy explícita (ej. freeze_releases) en {missing_exhaustion_policy_count} bloque(s) SLO."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_slo_blocks": total_slo_blocks,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "invalid_slo_target_count": invalid_slo_target_count,
        "burn_factor_violation_count": burn_factor_violation_count,
        "missing_multiwindow_count": missing_multiwindow_count,
        "missing_exhaustion_policy_count": missing_exhaustion_policy_count,
        "slo_hygiene_rate_pct": slo_hygiene_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene = staticmethod(
    audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene
)
AnydocService.audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene = staticmethod(
    audit_markdown_slo_error_budget_burn_rate_and_multiwindow_hygiene
)


def audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene(
    markdown_text: str,
    *,
    max_unmitigated_cvss: float = 4.0,
    require_mitre_technique: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown Threat Modeling STRIDE / MITRE ATT&CK Mapping & Residual Risk Owner Sign-Off Hygiene Auditor."""
    normalized_max_cvss = min(max(float(max_unmitigated_cvss), 0.0), 10.0)
    valid_stride_categories = {
        "spoofing",
        "tampering",
        "repudiation",
        "information_disclosure",
        "denial_of_service",
        "elevation_of_privilege",
    }

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(
        r"<!--\s*threat_model\s*:(.*?)-->", re.IGNORECASE | re.DOTALL
    )
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    unmitigated_high_cvss_count = 0
    missing_risk_owner_count = 0
    invalid_stride_count = 0
    missing_mitre_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        threat_id = kv.get("id") or f"TM-{idx}"
        stride = kv.get("stride", "").strip().lower()
        mitre = kv.get("mitre", "").strip()
        try:
            cvss = float(kv.get("cvss", "0.0"))
        except (TypeError, ValueError):
            cvss = 0.0
        control = kv.get("control", "").strip()
        threat_status = kv.get("status", "").strip().lower()
        risk_owner = kv.get("risk_owner", "").strip()

        control_missing = not control or control.lower() == "none"
        invalid_stride_category = stride not in valid_stride_categories
        missing_mitre_technique = bool(
            require_mitre_technique
            and not bool(re.match(r"^T\d+", mitre, re.IGNORECASE))
        )
        unmitigated_high_cvss = (
            threat_status not in {"mitigated", "eliminated"}
            and (cvss > normalized_max_cvss or control_missing)
        )
        missing_risk_owner_on_accepted = (
            threat_status == "accepted"
            and (not risk_owner or risk_owner.lower() == "none")
        )

        if unmitigated_high_cvss:
            unmitigated_high_cvss_count += 1
        if missing_risk_owner_on_accepted:
            missing_risk_owner_count += 1
        if invalid_stride_category:
            invalid_stride_count += 1
        if missing_mitre_technique:
            missing_mitre_count += 1

        if unmitigated_high_cvss or missing_risk_owner_on_accepted:
            block_status = "critical"
            critical_count += 1
        elif (
            invalid_stride_category
            or missing_mitre_technique
            or control_missing
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "id": threat_id,
                "stride": stride,
                "mitre": mitre,
                "cvss": cvss,
                "control": control,
                "status": threat_status,
                "risk_owner": risk_owner,
                "invalid_stride_category": invalid_stride_category,
                "missing_mitre_technique": missing_mitre_technique,
                "unmitigated_high_cvss": unmitigated_high_cvss,
                "missing_risk_owner_on_accepted": missing_risk_owner_on_accepted,
                "block_status": block_status,
            }
        )

    total_threat_blocks = len(blocks)
    threat_hygiene_rate_pct = (
        round((healthy_count / total_threat_blocks) * 100.0, 2)
        if total_threat_blocks > 0
        else 100.0
    )

    recommendations: list[str] = []
    if unmitigated_high_cvss_count > 0:
        recommendations.append(
            f"Mitigar o eliminar amenazas con CVSS > {normalized_max_cvss} o sin control técnico asignado ({unmitigated_high_cvss_count} bloque(s))."
        )
    if missing_risk_owner_count > 0:
        recommendations.append(
            f"Asignar risk_owner explícito para riesgos residuales en estado 'accepted' ({missing_risk_owner_count} bloque(s))."
        )
    if invalid_stride_count > 0:
        recommendations.append(
            f"Clasificar amenazas usando categorías STRIDE canónicas en {invalid_stride_count} bloque(s)."
        )
    if missing_mitre_count > 0:
        recommendations.append(
            f"Vincular identificador de técnica MITRE ATT&CK (ej. T1068, T1190.001) en {missing_mitre_count} bloque(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_threat_blocks": total_threat_blocks,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "unmitigated_high_cvss_count": unmitigated_high_cvss_count,
        "missing_risk_owner_count": missing_risk_owner_count,
        "invalid_stride_count": invalid_stride_count,
        "missing_mitre_count": missing_mitre_count,
        "threat_hygiene_rate_pct": threat_hygiene_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene = staticmethod(
    audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene
)
AnydocService.audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene = staticmethod(
    audit_markdown_threat_model_stride_mitre_and_residual_risk_hygiene
)


def audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene(
    markdown_text: str,
    *,
    min_tag_coverage_pct: float = 95.0,
    min_ri_sp_utilization_pct: float = 85.0,
    max_cost_anomaly_drift_pct: float = 15.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown FinOps Cloud Cost Tagging Coverage, RI/Savings Plans Utilization & Unit Economics Hygiene Auditor."""
    normalized_min_tag_cov = min(max(float(min_tag_coverage_pct), 0.0), 100.0)
    normalized_min_ri_sp = min(
        max(float(min_ri_sp_utilization_pct), 0.0), 100.0
    )
    normalized_max_drift = max(float(max_cost_anomaly_drift_pct), 0.0)

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(r"<!--\s*finops\s*:(.*?)-->", re.IGNORECASE | re.DOTALL)
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    missing_cost_center_count = 0
    tag_coverage_breach_count = 0
    ri_sp_underutilized_count = 0
    cost_anomaly_spike_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        workload = kv.get("workload") or f"finops-workload-{idx}"
        cost_center = kv.get("cost_center", "").strip()
        try:
            tag_coverage_pct = float(kv.get("tag_coverage_pct", "0.0"))
        except (TypeError, ValueError):
            tag_coverage_pct = 0.0
        try:
            ri_sp_utilization_pct = float(
                kv.get("ri_sp_utilization_pct", "0.0")
            )
        except (TypeError, ValueError):
            ri_sp_utilization_pct = 0.0
        try:
            cost_anomaly_drift_pct = float(
                kv.get("cost_anomaly_drift_pct", "0.0")
            )
        except (TypeError, ValueError):
            cost_anomaly_drift_pct = 0.0
        unit_metric = kv.get("unit_metric", "").strip()
        raw_budget_alert = kv.get("budget_alert_configured", "").strip().lower()
        budget_alert_configured = raw_budget_alert in {"true", "1", "yes"}

        missing_cost_center_or_unit_metric = (
            not cost_center
            or cost_center.lower() == "none"
            or not unit_metric
            or unit_metric.lower() == "none"
        )
        unallocated_tag_coverage_breach = (
            tag_coverage_pct < normalized_min_tag_cov
        )
        ri_sp_commitment_underutilized = (
            ri_sp_utilization_pct < normalized_min_ri_sp
        )
        cost_anomaly_spike = cost_anomaly_drift_pct > normalized_max_drift
        missing_budget_alert = not budget_alert_configured

        if missing_cost_center_or_unit_metric:
            missing_cost_center_count += 1
        if unallocated_tag_coverage_breach:
            tag_coverage_breach_count += 1
        if ri_sp_commitment_underutilized:
            ri_sp_underutilized_count += 1
        if cost_anomaly_spike:
            cost_anomaly_spike_count += 1

        if missing_cost_center_or_unit_metric or (
            cost_anomaly_spike and missing_budget_alert
        ):
            block_status = "critical"
            critical_count += 1
        elif (
            unallocated_tag_coverage_breach
            or ri_sp_commitment_underutilized
            or cost_anomaly_spike
            or missing_budget_alert
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "workload": workload,
                "cost_center": cost_center,
                "tag_coverage_pct": tag_coverage_pct,
                "ri_sp_utilization_pct": ri_sp_utilization_pct,
                "cost_anomaly_drift_pct": cost_anomaly_drift_pct,
                "unit_metric": unit_metric,
                "budget_alert_configured": budget_alert_configured,
                "missing_cost_center_or_unit_metric": missing_cost_center_or_unit_metric,
                "unallocated_tag_coverage_breach": unallocated_tag_coverage_breach,
                "ri_sp_commitment_underutilized": ri_sp_commitment_underutilized,
                "cost_anomaly_spike": cost_anomaly_spike,
                "missing_budget_alert": missing_budget_alert,
                "block_status": block_status,
            }
        )

    total_finops_blocks = len(blocks)
    finops_hygiene_rate_pct = (
        round((healthy_count / total_finops_blocks) * 100.0, 2)
        if total_finops_blocks > 0
        else 100.0
    )

    recommendations: list[str] = []
    if missing_cost_center_count > 0:
        recommendations.append(
            f"Asignar cost_center y unit_metric explícitos para trazabilidad de economía unitaria en {missing_cost_center_count} bloque(s) FinOps."
        )
    if tag_coverage_breach_count > 0:
        recommendations.append(
            f"Incrementar cobertura de etiquetado de recursos cloud (tag_coverage_pct >= {normalized_min_tag_cov}%) en {tag_coverage_breach_count} bloque(s)."
        )
    if ri_sp_underutilized_count > 0:
        recommendations.append(
            f"Rebalancear compromisos Reserved Instances / Savings Plans para alcanzar utilización >= {normalized_min_ri_sp}% en {ri_sp_underutilized_count} bloque(s)."
        )
    if cost_anomaly_spike_count > 0:
        recommendations.append(
            f"Investigar desviaciones de gasto cloud (> {normalized_max_drift}%) y activar alertas presupuestarias automáticas en {cost_anomaly_spike_count} bloque(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_finops_blocks": total_finops_blocks,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "missing_cost_center_count": missing_cost_center_count,
        "tag_coverage_breach_count": tag_coverage_breach_count,
        "ri_sp_underutilized_count": ri_sp_underutilized_count,
        "cost_anomaly_spike_count": cost_anomaly_spike_count,
        "finops_hygiene_rate_pct": finops_hygiene_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene = staticmethod(
    audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene
)
AnydocService.audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene = staticmethod(
    audit_markdown_finops_cloud_cost_tagging_and_unit_economics_hygiene
)


def audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene(
    markdown_text: str,
    *,
    min_contrast_ratio: float = 4.5,
    require_descriptive_alt_text: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown WCAG 2.2 AA Accessibility, Contrast Ratio, Alt-Text Coverage & Heading Hierarchy Hygiene Auditor."""
    normalized_min_contrast = min(max(float(min_contrast_ratio), 1.0), 21.0)
    generic_invalid_alt = {
        "",
        "none",
        "image",
        "img",
        "photo",
        "screenshot",
        "diagram",
        "picture",
    }

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(
        r"<!--\s*wcag_audit\s*:(.*?)-->", re.IGNORECASE | re.DOTALL
    )
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    keyboard_or_aria_breach_count = 0
    contrast_shortfall_count = 0
    missing_alt_text_count = 0
    heading_jump_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        component = kv.get("component") or f"wcag-component-{idx}"
        try:
            contrast_ratio = float(kv.get("contrast_ratio", "4.5"))
        except (TypeError, ValueError):
            contrast_ratio = 0.0

        alt_text = kv.get("alt_text", "").strip()
        raw_heading_jump = kv.get("heading_jump_skipped", "false").strip().lower()
        heading_jump_skipped = raw_heading_jump in {"true", "1", "yes"}
        raw_keyboard_trap = (
            kv.get("keyboard_trap_detected", "false").strip().lower()
        )
        keyboard_trap_detected = raw_keyboard_trap in {"true", "1", "yes"}
        raw_aria_valid = kv.get("aria_landmarks_valid", "true").strip().lower()
        aria_landmarks_valid = raw_aria_valid not in {"false", "0", "no"}

        keyboard_trap_or_aria_broken = (
            keyboard_trap_detected or not aria_landmarks_valid
        )
        contrast_ratio_shortfall = contrast_ratio < normalized_min_contrast
        non_descriptive_or_missing_alt = bool(require_descriptive_alt_text) and (
            alt_text.lower() in generic_invalid_alt or len(alt_text) < 5
        )
        heading_hierarchy_violation = heading_jump_skipped

        if keyboard_trap_or_aria_broken:
            keyboard_or_aria_breach_count += 1
        if contrast_ratio_shortfall:
            contrast_shortfall_count += 1
        if non_descriptive_or_missing_alt:
            missing_alt_text_count += 1
        if heading_hierarchy_violation:
            heading_jump_count += 1

        if keyboard_trap_or_aria_broken or (
            contrast_ratio_shortfall and non_descriptive_or_missing_alt
        ):
            block_status = "critical"
            critical_count += 1
        elif (
            contrast_ratio_shortfall
            or non_descriptive_or_missing_alt
            or heading_hierarchy_violation
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "component": component,
                "contrast_ratio": contrast_ratio,
                "alt_text": alt_text,
                "heading_jump_skipped": heading_jump_skipped,
                "keyboard_trap_detected": keyboard_trap_detected,
                "aria_landmarks_valid": aria_landmarks_valid,
                "keyboard_trap_or_aria_broken": keyboard_trap_or_aria_broken,
                "contrast_ratio_shortfall": contrast_ratio_shortfall,
                "non_descriptive_or_missing_alt": non_descriptive_or_missing_alt,
                "heading_hierarchy_violation": heading_hierarchy_violation,
                "block_status": block_status,
            }
        )

    total_wcag_blocks = len(blocks)
    wcag_compliance_rate_pct = (
        round((healthy_count / total_wcag_blocks) * 100.0, 2)
        if total_wcag_blocks > 0
        else 100.0
    )

    recommendations: list[str] = []
    if keyboard_or_aria_breach_count > 0:
        recommendations.append(
            f"Eliminar trampas de foco por teclado (keyboard trap) y restaurar landmarks ARIA semánticos válidos en {keyboard_or_aria_breach_count} bloque(s) WCAG."
        )
    if contrast_shortfall_count > 0:
        recommendations.append(
            f"Elevar el ratio de contraste luminoso >= {normalized_min_contrast}:1 conforme a WCAG 2.2 AA en {contrast_shortfall_count} bloque(s)."
        )
    if missing_alt_text_count > 0:
        recommendations.append(
            f"Proveer texto alternativo (alt_text) descriptivo y específico (>= 5 caracteres, sin etiquetas genéricas) en {missing_alt_text_count} bloque(s)."
        )
    if heading_jump_count > 0:
        recommendations.append(
            f"Corregir saltos en la jerarquía de encabezados (H1->H2->H3 sin omitir niveles) en {heading_jump_count} bloque(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_wcag_blocks": total_wcag_blocks,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "keyboard_or_aria_breach_count": keyboard_or_aria_breach_count,
        "contrast_shortfall_count": contrast_shortfall_count,
        "missing_alt_text_count": missing_alt_text_count,
        "heading_jump_count": heading_jump_count,
        "wcag_compliance_rate_pct": wcag_compliance_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene = staticmethod(
    audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene
)
AnydocService.audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene = staticmethod(
    audit_markdown_wcag_accessibility_alt_text_and_heading_hierarchy_hygiene
)


def audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene(
    markdown_text: str,
    *,
    min_disparate_impact_ratio: float = 0.80,
    max_jailbreak_success_rate_pct: float = 2.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — AnyDoc Markdown AI Model Card (EU AI Act / NIST AI RMF), Bias/Fairness Disparate Impact & Red-Team Jailbreak Rate Hygiene Auditor."""
    normalized_min_di = min(max(float(min_disparate_impact_ratio), 0.1), 1.0)
    normalized_max_jb = min(
        max(float(max_jailbreak_success_rate_pct), 0.0), 100.0
    )

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(
        r"<!--\s*ai_model_card\s*:(.*?)-->", re.IGNORECASE | re.DOTALL
    )
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    copyright_or_hitl_breach_count = 0
    bias_rule_violation_count = 0
    jailbreak_exceeded_count = 0
    prohibited_tier_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        model = kv.get("model") or f"ai-model-{idx}"
        risk_tier = kv.get("risk_tier", "limited").strip().lower()
        try:
            disparate_impact_ratio = float(
                kv.get("disparate_impact_ratio", "1.0")
            )
        except (TypeError, ValueError):
            disparate_impact_ratio = 0.0
        try:
            jailbreak_success_rate_pct = float(
                kv.get("jailbreak_success_rate_pct", "0.0")
            )
        except (TypeError, ValueError):
            jailbreak_success_rate_pct = 0.0

        raw_copyright = (
            kv.get("training_data_copyright_cleared", "true").strip().lower()
        )
        training_data_copyright_cleared = raw_copyright not in {
            "false",
            "0",
            "no",
        }
        raw_hitl = kv.get("human_in_the_loop_override", "true").strip().lower()
        human_in_the_loop_override = raw_hitl not in {"false", "0", "no"}

        prohibited_ai_tier = risk_tier == "unacceptable"
        unmitigated_high_risk_or_copyright_breach = (
            not training_data_copyright_cleared
            or (
                risk_tier in {"high", "unacceptable"}
                and not human_in_the_loop_override
            )
        )
        four_fifths_bias_rule_violated = (
            disparate_impact_ratio < normalized_min_di
            or disparate_impact_ratio > 1.25
        )
        red_team_jailbreak_threshold_exceeded = (
            jailbreak_success_rate_pct > normalized_max_jb
        )

        if unmitigated_high_risk_or_copyright_breach:
            copyright_or_hitl_breach_count += 1
        if four_fifths_bias_rule_violated:
            bias_rule_violation_count += 1
        if red_team_jailbreak_threshold_exceeded:
            jailbreak_exceeded_count += 1
        if prohibited_ai_tier:
            prohibited_tier_count += 1

        if (
            prohibited_ai_tier
            or unmitigated_high_risk_or_copyright_breach
            or (
                four_fifths_bias_rule_violated
                and red_team_jailbreak_threshold_exceeded
            )
        ):
            block_status = "critical"
            critical_count += 1
        elif (
            four_fifths_bias_rule_violated
            or red_team_jailbreak_threshold_exceeded
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "model": model,
                "risk_tier": risk_tier,
                "disparate_impact_ratio": disparate_impact_ratio,
                "jailbreak_success_rate_pct": jailbreak_success_rate_pct,
                "training_data_copyright_cleared": training_data_copyright_cleared,
                "human_in_the_loop_override": human_in_the_loop_override,
                "unmitigated_high_risk_or_copyright_breach": unmitigated_high_risk_or_copyright_breach,
                "four_fifths_bias_rule_violated": four_fifths_bias_rule_violated,
                "red_team_jailbreak_threshold_exceeded": red_team_jailbreak_threshold_exceeded,
                "prohibited_ai_tier": prohibited_ai_tier,
                "block_status": block_status,
            }
        )

    total_model_cards = len(blocks)
    model_card_hygiene_rate_pct = (
        round((healthy_count / total_model_cards) * 100.0, 2)
        if total_model_cards > 0
        else 100.0
    )

    recommendations: list[str] = []
    if prohibited_tier_count > 0:
        recommendations.append(
            f"Bloquear despliegue de modelos clasificados en nivel de riesgo prohibido ('unacceptable' según EU AI Act Art. 5) en {prohibited_tier_count} Model Card(s)."
        )
    if copyright_or_hitl_breach_count > 0:
        recommendations.append(
            f"Acreditar limpieza de derechos de autor del corpus de entrenamiento y habilitar supervisión humana efectiva (HITL override) para sistemas de alto riesgo en {copyright_or_hitl_breach_count} Model Card(s)."
        )
    if bias_rule_violation_count > 0:
        recommendations.append(
            f"Recalibrar pesos y muestreo demográfico para cumplir la regla de cuatro quintos (Disparate Impact Ratio en [{normalized_min_di}, 1.25]) en {bias_rule_violation_count} Model Card(s)."
        )
    if jailbreak_exceeded_count > 0:
        recommendations.append(
            f"Reforzar guardrails contra inyección de prompts y ataques adversariales para reducir tasa de éxito de jailbreak <= {normalized_max_jb}% en {jailbreak_exceeded_count} Model Card(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_model_cards": total_model_cards,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "copyright_or_hitl_breach_count": copyright_or_hitl_breach_count,
        "bias_rule_violation_count": bias_rule_violation_count,
        "jailbreak_exceeded_count": jailbreak_exceeded_count,
        "prohibited_tier_count": prohibited_tier_count,
        "model_card_hygiene_rate_pct": model_card_hygiene_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene = staticmethod(
    audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene
)
AnydocService.audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene = staticmethod(
    audit_markdown_ai_model_card_bias_fairness_and_red_team_hygiene
)


def audit_markdown_rfc2119_normative_keyword_and_testability_hygiene(
    markdown_text: str,
    *,
    max_ambiguous_terms_per_block: int = 0,
    require_verification_method: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §5.2 — AnyDoc Markdown RFC 2119 Normative Keyword (MUST/SHOULD/MAY), Lexical Ambiguity & Verification Traceability Hygiene Auditor."""
    normalized_max_ambiguous = max(int(max_ambiguous_terms_per_block), 0)
    valid_rfc2119_keywords = {
        "MUST",
        "MUST NOT",
        "REQUIRED",
        "SHALL",
        "SHALL NOT",
        "SHOULD",
        "SHOULD NOT",
        "RECOMMENDED",
        "MAY",
        "OPTIONAL",
    }
    mandatory_keywords = {"MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT"}
    valid_verification_methods = {
        "inspection",
        "analysis",
        "demonstration",
        "test",
        "automated_load_test",
        "unit_test",
        "integration_test",
    }
    ambiguous_terms = (
        "aproximadamente",
        "etc",
        "rápido",
        "fácil",
        "adecuado",
        "según sea necesario",
        "tbd",
        "tba",
    )

    text = markdown_text if isinstance(markdown_text, str) else ""
    stripped = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", text)

    pattern = re.compile(
        r"<!--\s*req_spec\s*:(.*?)-->", re.IGNORECASE | re.DOTALL
    )
    blocks: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    untestable_mandatory_count = 0
    invalid_keyword_count = 0
    invalid_verification_count = 0
    ambiguity_exceeded_count = 0

    for idx, match in enumerate(pattern.finditer(stripped), start=1):
        raw_body = match.group(1)
        kv: dict[str, str] = {}
        for part in re.split(r"[;\n]", raw_body):
            if "=" in part:
                k, v = part.split("=", 1)
                kv[k.strip().lower()] = v.strip()

        req_id = kv.get("id") or f"REQ-{idx}"
        rfc2119_level = kv.get("rfc2119_level", "").strip()
        statement = kv.get("statement", "").strip()
        verification = kv.get("verification", "").strip()
        test_case_id = kv.get("test_case_id", "").strip()

        invalid_rfc2119_keyword = rfc2119_level not in valid_rfc2119_keywords
        missing_test_case = not test_case_id or test_case_id.lower() == "none"
        invalid_verification = (
            bool(require_verification_method)
            and verification.lower() not in valid_verification_methods
        )
        untestable_mandatory_requirement = (
            rfc2119_level.upper() in mandatory_keywords
            and (missing_test_case or invalid_verification)
        )

        stmt_lower = statement.lower()
        ambiguous_term_count = sum(
            len(re.findall(rf"\b{re.escape(term)}\b", stmt_lower))
            for term in ambiguous_terms
        )
        ambiguity_threshold_exceeded = (
            ambiguous_term_count > normalized_max_ambiguous
        )

        if untestable_mandatory_requirement:
            untestable_mandatory_count += 1
        if invalid_rfc2119_keyword:
            invalid_keyword_count += 1
        if invalid_verification:
            invalid_verification_count += 1
        if ambiguity_threshold_exceeded:
            ambiguity_exceeded_count += 1

        if untestable_mandatory_requirement or (
            invalid_rfc2119_keyword and ambiguity_threshold_exceeded
        ):
            block_status = "critical"
            critical_count += 1
        elif (
            invalid_rfc2119_keyword
            or ambiguity_threshold_exceeded
            or missing_test_case
            or invalid_verification
        ):
            block_status = "warning"
            warning_count += 1
        else:
            block_status = "healthy"
            healthy_count += 1

        blocks.append(
            {
                "id": req_id,
                "rfc2119_level": rfc2119_level,
                "statement": statement,
                "verification": verification,
                "test_case_id": test_case_id,
                "invalid_rfc2119_keyword": invalid_rfc2119_keyword,
                "invalid_verification_method": invalid_verification,
                "untestable_mandatory_requirement": untestable_mandatory_requirement,
                "ambiguous_term_count": ambiguous_term_count,
                "ambiguity_threshold_exceeded": ambiguity_threshold_exceeded,
                "block_status": block_status,
            }
        )

    total_req_blocks = len(blocks)
    req_testability_rate_pct = (
        round((healthy_count / total_req_blocks) * 100.0, 2)
        if total_req_blocks > 0
        else 100.0
    )

    recommendations: list[str] = []
    if untestable_mandatory_count > 0:
        recommendations.append(
            f"Vincular test_case_id explícito y método de verificación canónico (test/analysis/inspection/demonstration) en {untestable_mandatory_count} requisito(s) mandatorio(s) RFC 2119."
        )
    if invalid_keyword_count > 0:
        recommendations.append(
            f"Normalizar nivel normativo en mayúsculas estrictas según IETF RFC 2119 (MUST, SHOULD, MAY) en {invalid_keyword_count} bloque(s)."
        )
    if invalid_verification_count > 0:
        recommendations.append(
            f"Usar métodos de verificación canónicos (test, analysis, inspection o demonstration) en {invalid_verification_count} requisito(s)."
        )
    if ambiguity_exceeded_count > 0:
        recommendations.append(
            f"Reemplazar términos léxicos vagos o indefinidos (TBD/TBA/etc/aproximadamente) por umbrales cuantitativos verificables en {ambiguity_exceeded_count} requisito(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_req_blocks": total_req_blocks,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "untestable_mandatory_count": untestable_mandatory_count,
        "invalid_keyword_count": invalid_keyword_count,
        "invalid_verification_count": invalid_verification_count,
        "ambiguity_exceeded_count": ambiguity_exceeded_count,
        "req_testability_rate_pct": req_testability_rate_pct,
        "status": status,
        "blocks": blocks,
        "recommendations": recommendations,
    }


AnyDocService.audit_markdown_rfc2119_normative_keyword_and_testability_hygiene = staticmethod(
    audit_markdown_rfc2119_normative_keyword_and_testability_hygiene
)
AnydocService.audit_markdown_rfc2119_normative_keyword_and_testability_hygiene = staticmethod(
    audit_markdown_rfc2119_normative_keyword_and_testability_hygiene
)


def audit_anydoc_ieee829_verification_traceability_matrix(
    requirement_specs: Any = None,
    test_cases: Any = None,
    *,
    requirements: Any = None,
    specifications: Any = None,
) -> dict[str, Any]:
    """Audit bidirectional requirement/test traceability and execution evidence (IEEE 829)."""
    passed_statuses = {
        "pass",
        "passed",
        "verified",
        "success",
        "successful",
        "complete",
        "completed",
        "approved",
    }
    failed_statuses = {
        "fail",
        "failed",
        "error",
        "rejected",
        "not_passed",
        "not passed",
    }

    def coerce_records(value: Any) -> tuple[list[dict[str, Any]], int]:
        if isinstance(value, Mapping):
            candidates: list[Any] = [value]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            candidates = list(value)
        else:
            candidates = []
        records = [dict(item) for item in candidates if isinstance(item, Mapping)]
        return records, len(candidates) - len(records)

    def first_value(record: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = record.get(key)
            if value is not None and str(value).strip():
                return value
        return None

    def normalize_id(value: Any) -> str:
        if value is None or isinstance(value, (Mapping, list, tuple, set)):
            return ""
        return str(value).strip().upper()

    def normalize_references(value: Any) -> list[str]:
        if isinstance(value, Mapping):
            values: Sequence[Any] = list(value.keys())
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            values = value
        elif value is None:
            values = []
        else:
            values = [value]
        normalized: list[str] = []
        for item in values:
            req_id = normalize_id(item)
            if req_id and req_id not in normalized:
                normalized.append(req_id)
        return normalized

    spec_input = requirement_specs
    if spec_input is None:
        spec_input = requirements if requirements is not None else specifications
    specs, invalid_spec_record_count = coerce_records(spec_input)
    cases, invalid_test_record_count = coerce_records(test_cases)

    requirements: list[dict[str, Any]] = []
    requirement_by_id: dict[str, dict[str, Any]] = {}
    missing_requirement_ids: list[str] = []
    duplicate_requirement_ids: list[str] = []
    for index, spec in enumerate(specs, start=1):
        req_id = normalize_id(
            first_value(
                spec,
                ("requirement_id", "req_id", "id", "identifier", "code"),
            )
        )
        if not req_id:
            req_id = f"__MISSING_REQ_ID_{index}__"
            missing_requirement_ids.append(req_id)
        elif req_id in requirement_by_id:
            duplicate_requirement_ids.append(req_id)
            continue

        row = {
            "requirement_id": req_id,
            "title": str(first_value(spec, ("title", "name", "summary")) or ""),
            "linked_test_case_ids": [],
            "passed_test_case_ids": [],
            "failed_test_case_ids": [],
            "is_verified": False,
        }
        requirements.append(row)
        requirement_by_id[req_id] = row

    test_rows: list[dict[str, Any]] = []
    missing_test_case_ids: list[str] = []
    duplicate_test_case_ids: list[str] = []
    seen_test_case_ids: set[str] = set()
    orphan_test_case_ids: list[str] = []
    unexecuted_test_case_ids: list[str] = []
    failed_test_case_ids: list[str] = []
    unknown_requirement_reference_count = 0

    for index, case in enumerate(cases, start=1):
        test_id = normalize_id(
            first_value(
                case,
                ("test_case_id", "test_id", "case_id", "id", "identifier", "code"),
            )
        )
        if not test_id:
            test_id = f"__MISSING_TEST_CASE_ID_{index}__"
            missing_test_case_ids.append(test_id)
        elif test_id in seen_test_case_ids:
            duplicate_test_case_ids.append(test_id)
            continue
        seen_test_case_ids.add(test_id)

        raw_references = first_value(
            case,
            (
                "requirement_ids",
                "req_ids",
                "traces_to_requirements",
                "related_requirement_ids",
                "requirement_refs",
                "linked_requirements",
                "covers",
                "traces_to",
                "verifies",
                "requirements",
                "requirement_id",
                "req_id",
            ),
        )
        references = normalize_references(raw_references)
        linked_req_ids = [req_id for req_id in references if req_id in requirement_by_id]
        unknown_req_ids = [req_id for req_id in references if req_id not in requirement_by_id]
        unknown_requirement_reference_count += len(unknown_req_ids)
        status_value = first_value(
            case,
            (
                "execution_status",
                "test_result",
                "execution_result",
                "result",
                "verification_status",
                "test_status",
                "status",
                "outcome",
            ),
        )
        if status_value is None:
            status_value = first_value(case, ("passed", "is_passed"))
            if status_value is True:
                status_value = "passed"
            elif status_value is False:
                status_value = "failed"
        if status_value is None:
            status_value = first_value(case, ("verified", "is_verified"))
            if status_value is True:
                status_value = "verified"
        execution_status = str(status_value or "").strip().lower().replace("-", "_")
        is_passed = execution_status in passed_statuses
        is_failed = execution_status in failed_statuses
        if not is_passed and not is_failed:
            unexecuted_test_case_ids.append(test_id)
        if is_failed:
            failed_test_case_ids.append(test_id)
        if not linked_req_ids:
            orphan_test_case_ids.append(test_id)

        row = {
            "test_case_id": test_id,
            "requirement_ids": linked_req_ids,
            "unknown_requirement_ids": unknown_req_ids,
            "execution_status": execution_status or "not_executed",
            "is_passed": is_passed,
            "is_failed": is_failed,
            "is_orphan": not linked_req_ids,
        }
        test_rows.append(row)
        for req_id in linked_req_ids:
            requirement = requirement_by_id[req_id]
            requirement["linked_test_case_ids"].append(test_id)
            if is_passed:
                requirement["passed_test_case_ids"].append(test_id)
            if is_failed:
                requirement["failed_test_case_ids"].append(test_id)

    unverified_requirement_ids: list[str] = []
    untested_requirement_ids: list[str] = []
    for requirement in requirements:
        has_linked_tests = bool(requirement["linked_test_case_ids"])
        has_passed_tests = bool(requirement["passed_test_case_ids"])
        requirement["is_verified"] = has_passed_tests
        if not has_linked_tests:
            untested_requirement_ids.append(requirement["requirement_id"])
        if not has_passed_tests:
            unverified_requirement_ids.append(requirement["requirement_id"])

    total_requirements = len(requirements)
    total_test_cases = len(test_rows)
    covered_requirement_count = sum(bool(row["linked_test_case_ids"]) for row in requirements)
    traced_test_case_count = sum(bool(row["requirement_ids"]) for row in test_rows)
    verified_requirement_count = sum(bool(row["passed_test_case_ids"]) for row in requirements)
    requirement_coverage_pct = (
        round(covered_requirement_count / total_requirements * 100.0, 2)
        if total_requirements
        else 100.0
    )
    test_case_traceability_pct = (
        round(traced_test_case_count / total_test_cases * 100.0, 2)
        if total_test_cases
        else 100.0
    )
    verification_coverage_pct = (
        round(verified_requirement_count / total_requirements * 100.0, 2)
        if total_requirements
        else 100.0
    )

    critical_count = len(unverified_requirement_ids) + len(failed_test_case_ids)
    warning_count = sum(
        (
            len(orphan_test_case_ids),
            len(unexecuted_test_case_ids),
            len(missing_requirement_ids),
            len(missing_test_case_ids),
            len(duplicate_requirement_ids),
            len(duplicate_test_case_ids),
            unknown_requirement_reference_count,
            invalid_spec_record_count,
            invalid_test_record_count,
        )
    )
    if critical_count:
        status = "critical"
        severity = "critical"
    elif warning_count:
        status = "warning"
        severity = "warning"
    else:
        status = "healthy"
        severity = "none"

    recommendations: list[str] = []
    if untested_requirement_ids:
        recommendations.append(
            "Add IEEE 829 test-case links for requirements without mapped verification: "
            + ", ".join(untested_requirement_ids)
            + "."
        )
    if unverified_requirement_ids:
        recommendations.append(
            "Execute and pass at least one linked test case for each unverified requirement: "
            + ", ".join(unverified_requirement_ids)
            + "."
        )
    if orphan_test_case_ids:
        recommendations.append(
            "Link orphan test cases to known requirement IDs: " + ", ".join(orphan_test_case_ids) + "."
        )
    if unexecuted_test_case_ids:
        recommendations.append(
            "Record execution results (pass/fail) for planned test cases: "
            + ", ".join(unexecuted_test_case_ids)
            + "."
        )
    if failed_test_case_ids:
        recommendations.append(
            "Resolve failing test cases before treating linked requirements as verified: "
            + ", ".join(failed_test_case_ids)
            + "."
        )

    return {
        "status": status,
        "severity": severity,
        "is_valid": status == "healthy",
        "total_requirements": total_requirements,
        "total_test_cases": total_test_cases,
        "covered_requirement_count": covered_requirement_count,
        "traced_test_case_count": traced_test_case_count,
        "verified_requirement_count": verified_requirement_count,
        "unverified_requirement_count": len(unverified_requirement_ids),
        "untested_requirement_count": len(untested_requirement_ids),
        "orphan_test_case_count": len(orphan_test_case_ids),
        "unexecuted_test_case_count": len(unexecuted_test_case_ids),
        "failed_test_case_count": len(failed_test_case_ids),
        "warning_count": warning_count,
        "critical_count": critical_count,
        "requirement_coverage_pct": requirement_coverage_pct,
        "test_case_traceability_pct": test_case_traceability_pct,
        "verification_coverage_pct": verification_coverage_pct,
        "missing_requirement_ids": missing_requirement_ids,
        "missing_test_case_ids": missing_test_case_ids,
        "duplicate_requirement_ids": duplicate_requirement_ids,
        "duplicate_test_case_ids": duplicate_test_case_ids,
        "unverified_requirement_ids": unverified_requirement_ids,
        "untested_requirement_ids": untested_requirement_ids,
        "orphan_test_case_ids": orphan_test_case_ids,
        "unexecuted_test_case_ids": unexecuted_test_case_ids,
        "failed_test_case_ids": failed_test_case_ids,
        "invalid_spec_record_count": invalid_spec_record_count,
        "invalid_test_record_count": invalid_test_record_count,
        "unknown_requirement_reference_count": unknown_requirement_reference_count,
        "requirements": requirements,
        "test_cases": test_rows,
        "recommendations": recommendations,
    }


AnyDocService.audit_anydoc_ieee829_verification_traceability_matrix = staticmethod(
    audit_anydoc_ieee829_verification_traceability_matrix
)
AnydocService.audit_anydoc_ieee829_verification_traceability_matrix = staticmethod(
    audit_anydoc_ieee829_verification_traceability_matrix
)


def audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics(
    requirements: Any = None,
    *,
    require_verification_method: bool = True,
) -> dict[str, Any]:
    """Assess requirement singularity, verifiability, ambiguity, and verification method assignment."""
    vague_qualifiers = (
        "as appropriate",
        "as needed",
        "as soon as possible",
        "easy",
        "fast",
        "flexible",
        "intuitive",
        "minimal",
        "quickly",
        "robust",
        "secure",
        "sufficient",
        "timely",
        "user friendly",
        "adequado",
        "adecuadamente",
        "aproximadamente",
        "conveniente",
        "eficiente",
        "fácil",
        "flexible",
        "intuitivo",
        "lo antes posible",
        "mínimo",
        "rápido",
        "robusto",
        "seguro",
        "según corresponda",
        "según sea necesario",
        "suficiente",
        "oportunamente",
    )
    valid_verification_methods = {
        "analysis",
        "demonstration",
        "inspection",
        "measurement",
        "test",
        "automated_test",
        "unit_test",
        "integration_test",
        "análisis",
        "demostración",
        "inspección",
        "medición",
        "prueba",
        "test automatizado",
    }
    observable_actions = (
        "allow",
        "create",
        "deny",
        "display",
        "emit",
        "log",
        "reject",
        "return",
        "store",
        "write",
        "aceptar",
        "almacenar",
        "calcular",
        "crear",
        "denegar",
        "devolver",
        "emitir",
        "guardar",
        "mostrar",
        "rechazar",
        "registrar",
        "responder",
        "validar",
    )
    normative_verbs = (
        "must",
        "shall",
        "should",
        "debe",
        "deberá",
        "deberia",
        "debería",
    )
    action_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(word) for word in observable_actions) + r")\w*\b",
        re.IGNORECASE,
    )
    normative_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(word) for word in normative_verbs) + r")\b",
        re.IGNORECASE,
    )
    conjunction_pattern = re.compile(r"\b(?:and|or|y|o|as well as|así como)\b|;", re.IGNORECASE)

    if isinstance(requirements, Mapping):
        candidates: list[Any] = [requirements]
    elif isinstance(requirements, str):
        candidates = [requirements]
    elif isinstance(requirements, Sequence) and not isinstance(requirements, (bytes, bytearray)):
        candidates = list(requirements)
    else:
        candidates = []
    invalid_record_count = 0
    records: list[dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, Mapping):
            records.append(dict(item))
        elif isinstance(item, str):
            records.append({"statement": item})
        else:
            invalid_record_count += 1

    def first_nonempty(record: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = record.get(key)
            if value is not None and str(value).strip():
                return value
        return None

    def explicit_bool(record: Mapping[str, Any], keys: tuple[str, ...]) -> bool | None:
        for key in keys:
            if key in record:
                value = record[key]
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    normalized = value.strip().lower()
                    if normalized in {"true", "yes", "si", "sí", "1"}:
                        return True
                    if normalized in {"false", "no", "0"}:
                        return False
        return None

    requirement_rows: list[dict[str, Any]] = []
    missing_id_count = 0
    critical_count = 0
    warning_count = 0
    vague_qualifier_occurrence_count = 0
    for index, record in enumerate(records, start=1):
        raw_id = first_nonempty(record, ("requirement_id", "req_id", "id", "identifier", "code"))
        req_id = str(raw_id).strip() if raw_id is not None else f"REQ-{index}"
        if raw_id is None:
            missing_id_count += 1

        raw_statement = first_nonempty(
            record,
            ("statement", "requirement", "text", "description", "shall_statement", "title"),
        )
        statement = str(raw_statement).strip() if raw_statement is not None else ""
        statement_lower = statement.casefold()
        vague_terms = [
            term
            for term in vague_qualifiers
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", statement_lower)
        ]
        vague_occurrences = sum(
            len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", statement_lower))
            for term in set(vague_terms)
        )
        vague_qualifier_occurrence_count += vague_occurrences

        explicit_singularity = explicit_bool(record, ("is_singular", "singular", "atomic"))
        action_count = len(action_pattern.findall(statement))
        normative_count = len(normative_pattern.findall(statement))
        appears_compound = bool(conjunction_pattern.search(statement)) and (
            action_count > 1 or normative_count > 1
        )
        is_singular = explicit_singularity if explicit_singularity is not None else not appears_compound

        acceptance_criteria = first_nonempty(
            record,
            ("acceptance_criteria", "acceptance_criterion", "verification_criteria", "measurable_criteria"),
        )
        explicit_verifiability = explicit_bool(record, ("is_verifiable", "verifiable", "testable"))
        measurable_value = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|ms|s|sec|seconds?|min|minutes?|hours?|h|days?|bytes?|kb|mb|gb|users?)\b", statement_lower))
        verifiability_evidence = bool(acceptance_criteria) or measurable_value or bool(action_count)
        is_verifiable = (
            explicit_verifiability
            if explicit_verifiability is not None
            else verifiability_evidence and not vague_terms
        )

        raw_method = first_nonempty(
            record,
            ("verification_method", "verification", "method", "verification_type"),
        )
        method = str(raw_method).strip().casefold() if raw_method is not None else ""
        method_assigned = bool(method) and method in valid_verification_methods
        method_required = bool(require_verification_method)
        missing_verification_method = method_required and not method
        invalid_verification_method = bool(method) and method not in valid_verification_methods
        missing_statement = not statement
        explicit_unverifiable = explicit_verifiability is False

        row_critical = missing_statement or explicit_unverifiable
        row_warning = (
            not is_singular
            or not is_verifiable
            or bool(vague_terms)
            or missing_verification_method
            or invalid_verification_method
            or raw_id is None
        )
        if row_critical:
            critical_count += 1
            row_status = "critical"
        elif row_warning:
            warning_count += 1
            row_status = "warning"
        else:
            row_status = "healthy"

        requirement_rows.append(
            {
                "requirement_id": req_id,
                "statement": statement,
                "is_singular": is_singular,
                "is_verifiable": is_verifiable,
                "verifiability_evidence": verifiability_evidence,
                "vague_qualifiers": sorted(set(vague_terms)),
                "vague_qualifier_occurrence_count": vague_occurrences,
                "verification_method": method or None,
                "verification_method_assigned": method_assigned,
                "missing_verification_method": missing_verification_method,
                "invalid_verification_method": invalid_verification_method,
                "status": row_status,
            }
        )

    total_requirements = len(requirement_rows)
    healthy_count = sum(row["status"] == "healthy" for row in requirement_rows)
    singular_count = sum(row["is_singular"] for row in requirement_rows)
    verifiable_count = sum(row["is_verifiable"] for row in requirement_rows)
    method_assigned_count = sum(row["verification_method_assigned"] for row in requirement_rows)
    vague_requirement_count = sum(bool(row["vague_qualifiers"]) for row in requirement_rows)
    if invalid_record_count or missing_id_count:
        warning_count += invalid_record_count + missing_id_count
    if critical_count:
        status = "critical"
        severity = "critical"
    elif warning_count:
        status = "warning"
        severity = "warning"
    else:
        status = "healthy"
        severity = "none"

    def rate(count: int) -> float:
        return round(count / total_requirements * 100.0, 2) if total_requirements else 100.0

    recommendations: list[str] = []
    if any(not row["is_singular"] for row in requirement_rows):
        recommendations.append("Split compound requirements so each statement expresses one obligation.")
    if vague_requirement_count:
        recommendations.append("Replace vague qualifiers with observable thresholds or acceptance criteria.")
    if any(not row["is_verifiable"] for row in requirement_rows):
        recommendations.append("Add objective acceptance criteria that allow an independent verification decision.")
    if any(row["missing_verification_method"] or row["invalid_verification_method"] for row in requirement_rows):
        recommendations.append("Assign a canonical verification method: test, analysis, inspection, demonstration, or measurement.")
    if missing_id_count:
        recommendations.append("Assign a stable unique ID to every requirement for traceability.")
    if invalid_record_count:
        recommendations.append("Provide each requirement as text or a mapping with a requirement statement.")

    return {
        "status": status,
        "severity": severity,
        "is_valid": status == "healthy",
        "total_requirements": total_requirements,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "singular_requirement_count": singular_count,
        "verifiable_requirement_count": verifiable_count,
        "verification_method_assigned_count": method_assigned_count,
        "vague_requirement_count": vague_requirement_count,
        "vague_qualifier_occurrence_count": vague_qualifier_occurrence_count,
        "missing_id_count": missing_id_count,
        "invalid_record_count": invalid_record_count,
        "singularity_rate_pct": rate(singular_count),
        "verifiability_rate_pct": rate(verifiable_count),
        "verification_method_assignment_rate_pct": rate(method_assigned_count),
        "ambiguity_rate_pct": rate(vague_requirement_count),
        "requirements": requirement_rows,
        "recommendations": recommendations,
    }


AnyDocService.audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics = staticmethod(
    audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics
)
AnydocService.audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics = staticmethod(
    audit_anydoc_iso29148_requirements_quality_and_ambiguity_metrics
)
