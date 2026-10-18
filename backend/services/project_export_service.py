"""Servicio de exportación 360° de Proyectos, incluida la gobernanza PMI."""

from __future__ import annotations

import csv
import io
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.crud.projects import (
    generate_project_expenses_csv,
    generate_project_summary_pdf,
    generate_project_tasks_csv,
    get_project_executive_report_data,
)

__all__ = [
    "get_project_executive_report_data",
    "generate_project_summary_pdf",
    "generate_project_tasks_csv",
    "generate_project_expenses_csv",
    "evaluate_executive_report_completeness",
    "audit_csv_export_integrity",
    "audit_pdf_export_binary",
    "ProjectExportService",
]


def audit_csv_export_integrity(
    csv_content: Optional[str],
    required_headers: Optional[list[str]] = None,
) -> dict:
    """Valida la integridad estructural RFC-4180 y cabeceras requeridas de un CSV exportado."""
    has_utf8_bom = bool(
        isinstance(csv_content, str) and csv_content.startswith("\ufeff")
    )
    normalized_required = [
        str(h).strip() for h in (required_headers or []) if str(h).strip()
    ]

    if not isinstance(csv_content, str) or not csv_content.lstrip("\ufeff").strip():
        missing_required_headers = sorted(set(normalized_required))
        return {
            "has_utf8_bom": has_utf8_bom,
            "header_columns": [],
            "data_row_count": 0,
            "ragged_row_count": 0,
            "missing_required_headers": missing_required_headers,
            "is_rfc4180_compliant": False,
        }

    rows = list(csv.reader(io.StringIO(csv_content.lstrip("\ufeff"))))
    if not rows or not any(str(col).strip() for col in rows[0]):
        missing_required_headers = sorted(set(normalized_required))
        return {
            "has_utf8_bom": has_utf8_bom,
            "header_columns": [],
            "data_row_count": 0,
            "ragged_row_count": 0,
            "missing_required_headers": missing_required_headers,
            "is_rfc4180_compliant": False,
        }

    header_columns = [str(col).strip() for col in rows[0]]
    data_rows = rows[1:]
    data_row_count = len(data_rows)
    ragged_row_count = int(
        sum(1 for row in data_rows if len(row) != len(header_columns))
    )
    header_set = set(header_columns)
    missing_required_headers = sorted(
        {req for req in normalized_required if req not in header_set}
    )
    is_rfc4180_compliant = bool(
        len(header_columns) > 0
        and ragged_row_count == 0
        and len(missing_required_headers) == 0
    )

    return {
        "has_utf8_bom": has_utf8_bom,
        "header_columns": header_columns,
        "data_row_count": data_row_count,
        "ragged_row_count": ragged_row_count,
        "missing_required_headers": missing_required_headers,
        "is_rfc4180_compliant": is_rfc4180_compliant,
    }


def evaluate_executive_report_completeness(report_data: Optional[dict]) -> dict:
    """Evalúa la completitud y preparación de auditoría PMI 360° de un informe ejecutivo."""
    if not isinstance(report_data, dict):
        return {
            "has_project_header": False,
            "has_evm_financials": False,
            "has_raid_risks": False,
            "has_cpm_schedule": False,
            "has_pmi_governance": False,
            "has_ccb_quality": False,
            "sections_present_count": 0,
            "completeness_pct": 0.0,
            "is_audit_ready": False,
        }

    project_obj = report_data.get("project")
    has_project_header = bool(
        isinstance(project_obj, dict) and project_obj.get("title")
    )
    has_evm_financials = bool(isinstance(report_data.get("financial_kpis"), dict))
    has_raid_risks = bool(isinstance(report_data.get("raid_kpis"), dict))
    has_cpm_schedule = bool(isinstance(report_data.get("cpm_metrics"), dict))
    has_pmi_governance = bool(isinstance(report_data.get("governance_summary"), dict))
    has_ccb_quality = bool(isinstance(report_data.get("ccb_and_quality_summary"), dict))

    sections = (
        has_project_header,
        has_evm_financials,
        has_raid_risks,
        has_cpm_schedule,
        has_pmi_governance,
        has_ccb_quality,
    )
    sections_present_count = int(sum(1 for flag in sections if flag))
    completeness_pct = round((sections_present_count / 6) * 100.0, 1)

    return {
        "has_project_header": has_project_header,
        "has_evm_financials": has_evm_financials,
        "has_raid_risks": has_raid_risks,
        "has_cpm_schedule": has_cpm_schedule,
        "has_pmi_governance": has_pmi_governance,
        "has_ccb_quality": has_ccb_quality,
        "sections_present_count": sections_present_count,
        "completeness_pct": completeness_pct,
        "is_audit_ready": bool(sections_present_count == 6),
    }


def audit_pdf_export_binary(
    pdf_bytes: Optional[bytes | bytearray],
) -> dict:
    """Audita la integridad estructural binaria de un reporte PDF ejecutivo (ISO 32000-1 / PMI Formal Reporting)."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or len(pdf_bytes) == 0:
        return {
            "is_valid_pdf_header": False,
            "has_eof_marker": False,
            "byte_size": 0,
            "estimated_page_count": 0,
            "is_export_ready": False,
        }

    raw = bytes(pdf_bytes)
    byte_size = len(raw)
    is_valid_pdf_header = bool(raw.startswith(b"%PDF-"))
    has_eof_marker = bool(b"%%EOF" in raw[-1024:])
    page_matches = re.findall(rb"/Type\s*/Page\b", raw)

    if is_valid_pdf_header:
        estimated_page_count = (
            max(1, len(page_matches)) if has_eof_marker else len(page_matches)
        )
    else:
        estimated_page_count = 0

    is_export_ready = bool(
        is_valid_pdf_header
        and has_eof_marker
        and byte_size >= 100
        and estimated_page_count >= 1
    )

    return {
        "is_valid_pdf_header": is_valid_pdf_header,
        "has_eof_marker": has_eof_marker,
        "byte_size": byte_size,
        "estimated_page_count": estimated_page_count,
        "is_export_ready": is_export_ready,
    }


class ProjectExportService:
    """Fachada canónica de informes ejecutivos con ``governance_summary`` PMI."""

    @staticmethod
    def audit_pdf_export_binary(
        pdf_bytes: Optional[bytes | bytearray],
    ) -> dict:
        return audit_pdf_export_binary(pdf_bytes)

    @staticmethod
    def audit_csv_export_integrity(
        csv_content: Optional[str],
        required_headers: Optional[list[str]] = None,
    ) -> dict:
        return audit_csv_export_integrity(
            csv_content, required_headers=required_headers
        )

    @staticmethod
    def evaluate_executive_report_completeness(report_data: Optional[dict]) -> dict:
        return evaluate_executive_report_completeness(report_data)

    @staticmethod
    def get_project_executive_report_data(
        db: Session,
        project_id: UUID | str,
        *,
        user_sede_id: Optional[UUID | str] = None,
    ) -> Optional[dict]:
        return get_project_executive_report_data(
            db, project_id, user_sede_id=user_sede_id
        )

    @staticmethod
    def generate_project_summary_pdf(
        report_data_or_db: dict | Session,
        project_id: Optional[UUID | str] = None,
        *,
        user_sede_id: Optional[UUID | str] = None,
    ) -> bytes:
        return generate_project_summary_pdf(
            report_data_or_db, project_id, user_sede_id=user_sede_id
        )

    @staticmethod
    def generate_project_tasks_csv(
        db: Session,
        project_id: UUID | str,
        *,
        user_sede_id: Optional[UUID | str] = None,
    ) -> str:
        return generate_project_tasks_csv(db, project_id, user_sede_id=user_sede_id)

    @staticmethod
    def generate_project_expenses_csv(
        db: Session,
        project_id: UUID | str,
        *,
        user_sede_id: Optional[UUID | str] = None,
    ) -> str:
        return generate_project_expenses_csv(db, project_id, user_sede_id=user_sede_id)
