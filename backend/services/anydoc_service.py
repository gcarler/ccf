"""Servicio de conversión documental universal utilizando AnyDoc.

Convierte especificaciones, reportes y archivos de oficina (Word, Excel,
PowerPoint, OpenDocument, RTF, EPUB, CSV y PDF) en Markdown limpio y estructurado
compatible con GitHub Flavored Markdown (GFM) y la plataforma CCF.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
    logger.warning("anydoc no está instalado o no se encuentra disponible en PYTHONPATH")

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
}

FORMAT_ALIASES = {
    "xls": "xlsx",
    "xlsm": "xlsx",
    "docm": "docx",
    "pps": "ppt",
    "ppsx": "pptx",
    "text": "txt",
    "markdown": "md",
}


class AnyDocConversionError(Exception):
    """Error durante la conversión documental con AnyDoc."""

    def __init__(self, message: str, code: str = "CONVERSION_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def is_anydoc_available() -> bool:
    """Verifica si el motor AnyDoc se encuentra disponible en el entorno."""
    return ANYDOC_AVAILABLE


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

    return "unknown"


def convert_bytes_to_markdown(
    data: bytes,
    filename: str = "document",
    format_hint: Optional[str] = None,
    ocr: str = "reject",
) -> Dict[str, Any]:
    """Convierte bytes de un documento en GitHub-Flavored Markdown limpio.

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
            "engine": "anydoc_v0.2.4",
            "success": True,
            "error": None,
        }

    # Formatos de texto plano y markdown directos
    if detected_format in ("txt", "md"):
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

    if not ANYDOC_AVAILABLE:
        raise AnyDocConversionError(
            "El motor AnyDoc no está disponible en este entorno.",
            code="ENGINE_UNAVAILABLE",
        )

    try:
        # anydoc acepta format de tipo anydoc.Format o None para auto-detección
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
