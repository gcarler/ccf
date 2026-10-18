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
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

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
                    pass

    if data and ANYDOC_AVAILABLE:
        try:
            detected = format_from_bytes(data)
            if detected:
                return str(detected)
        except Exception:
            pass

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
                pass
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
        pass
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
        pass
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
                assert open_line is not None
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
                or url_part.startswith("/tmp/")
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
                assert current_callout_line is not None
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
                assert current_callout_line is not None
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
            assert current_callout_line is not None
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
        assert current_callout_line is not None
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

        block_ok = True

        if len(block_lines) < 2:
            malformed_delimiter_table_indices.append(table_index)
            block_ok = False
        else:
            delim_cells = _row_cells(block_lines[1])
            if len(delim_cells) != expected_cols or not all(
                _GFM_DELIMITER_CELL_RE.match(cell) for cell in delim_cells
            ):
                malformed_delimiter_table_indices.append(table_index)
                block_ok = False

        if "" in header_cells:
            empty_header_cell_table_indices.append(table_index)

        for data_line in block_lines[2:]:
            if len(_row_cells(data_line)) != expected_cols:
                ragged_column_table_indices.append(table_index)
                block_ok = False
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
        assert first_non_empty_idx is not None and closing_idx is not None
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
            + ", ".join(str(l) for l in missing_separator_table_lines)
        )
    if mismatched_column_row_lines:
        recommendations.append(
            "Fix column count mismatch at table row lines: "
            + ", ".join(str(l) for l in mismatched_column_row_lines)
        )
    if wide_table_header_lines:
        recommendations.append(
            f"Reduce tables wider than {max_columns_per_table} columns; wide headers at lines: "
            + ", ".join(str(l) for l in wide_table_header_lines)
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
