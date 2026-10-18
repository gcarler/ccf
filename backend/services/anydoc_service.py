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
    "AnyDocService",
]

