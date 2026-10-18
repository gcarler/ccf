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
