"""Servicio de exportación 360° de Proyectos, incluida la gobernanza PMI."""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Optional
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
    "summarize_executive_report_risk_posture",
    "audit_expenses_csv_financial_totals",
    "audit_tasks_csv_schedule_completeness",
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

    @staticmethod
    def summarize_executive_report_risk_posture(report_data: Optional[dict]) -> dict:
        return summarize_executive_report_risk_posture(report_data)

    @staticmethod
    def audit_expenses_csv_financial_totals(
        csv_content: str | bytes | None,
        expected_ac_total: float | None = None,
        amount_column_candidates: tuple[str, ...] = (
            "monto",
            "amount",
            "valor",
            "costo",
            "cost",
        ),
    ) -> dict[str, Any]:
        return audit_expenses_csv_financial_totals(
            csv_content,
            expected_ac_total=expected_ac_total,
            amount_column_candidates=amount_column_candidates,
        )

    @staticmethod
    def audit_tasks_csv_schedule_completeness(
        csv_content: str | bytes | None,
    ) -> dict[str, Any]:
        return audit_tasks_csv_schedule_completeness(csv_content)


def summarize_executive_report_risk_posture(report_data: Optional[dict]) -> dict:
    """Audita la postura de riesgo ejecutivo del informe (PMBOK §11.7).

    Extrae `raid_kpis` y `ccb_and_quality_summary` (dicts si corresponde)
    y retorna:
    - `total_risks` / `critical_risks` / `high_risks`: saneados (>= 0),
      tolerando las variantes `critical_risks_count`/`critical_risks` y
      `high_risks_count`/`high_risks`.
    - `elevated_risks_count`: críticas + altas.
    - `elevated_risk_share_pct`: % de riesgo elevado (round 2; 0.0 sin
      riesgos).
    - `pending_ccb_changes`: CRs pendientes de dictamen (>= 0).
    - `requires_sponsor_escalation`: críticas >= 1, altas >= 3 o
      pendientes >= 3.
    - `risk_posture_status`: 'unassessed' (sin riesgos ni pendientes),
      'sponsor_escalation', 'watch_list' (≥ 1 elevado o pendiente) o
      'controlled'.
    """
    data = report_data if isinstance(report_data, dict) else {}
    raid = data.get("raid_kpis") if isinstance(data.get("raid_kpis"), dict) else {}
    ccb = (
        data.get("ccb_and_quality_summary")
        if isinstance(data.get("ccb_and_quality_summary"), dict)
        else {}
    )

    total_risks = max(0, int(raid.get("total_risks") or 0))
    critical_risks = max(
        0, int(raid.get("critical_risks_count") or raid.get("critical_risks") or 0)
    )
    high_risks = max(
        0, int(raid.get("high_risks_count") or raid.get("high_risks") or 0)
    )
    elevated_risks_count = critical_risks + high_risks
    elevated_risk_share_pct = (
        round((elevated_risks_count / total_risks) * 100.0, 2)
        if total_risks > 0
        else 0.0
    )
    pending_ccb_changes = max(0, int(ccb.get("pending_ccb_count") or 0))

    requires_sponsor_escalation = bool(
        critical_risks >= 1 or high_risks >= 3 or pending_ccb_changes >= 3
    )

    if total_risks == 0 and pending_ccb_changes == 0:
        risk_posture_status = "unassessed"
    elif requires_sponsor_escalation:
        risk_posture_status = "sponsor_escalation"
    elif elevated_risks_count >= 1 or pending_ccb_changes >= 1:
        risk_posture_status = "watch_list"
    else:
        risk_posture_status = "controlled"

    return {
        "total_risks": total_risks,
        "critical_risks": critical_risks,
        "high_risks": high_risks,
        "elevated_risks_count": elevated_risks_count,
        "elevated_risk_share_pct": elevated_risk_share_pct,
        "pending_ccb_changes": pending_ccb_changes,
        "requires_sponsor_escalation": requires_sponsor_escalation,
        "risk_posture_status": risk_posture_status,
    }


def audit_expenses_csv_financial_totals(
    csv_content: str | bytes | None,
    expected_ac_total: float | None = None,
    amount_column_candidates: tuple[str, ...] = (
        "monto",
        "amount",
        "valor",
        "costo",
        "cost",
    ),
) -> dict[str, Any]:
    """Reconcilia la suma de importes de un CSV de gastos exportado frente al Costo Real AC (PMBOK §7.4)."""
    if isinstance(csv_content, (bytes, bytearray)):
        text = bytes(csv_content).decode("utf-8-sig", errors="replace").lstrip("\ufeff")
    elif isinstance(csv_content, str):
        text = csv_content.lstrip("\ufeff")
    else:
        text = ""

    expected_total = (
        round(float(expected_ac_total), 2) if expected_ac_total is not None else None
    )

    if not text.strip():
        return {
            "amount_column_name": None,
            "valid_amount_rows": 0,
            "invalid_amount_rows": 0,
            "csv_sum_amount": 0.0,
            "expected_ac_total": expected_total,
            "reconciliation_delta": (
                round(0.0 - expected_total, 2) if expected_total is not None else 0.0
            ),
            "is_reconciled": False,
            "reconciliation_status": "empty_export",
        }

    rows = [
        r
        for r in csv.reader(io.StringIO(text))
        if any(str(cell).strip() for cell in r)
    ]
    if not rows:
        return {
            "amount_column_name": None,
            "valid_amount_rows": 0,
            "invalid_amount_rows": 0,
            "csv_sum_amount": 0.0,
            "expected_ac_total": expected_total,
            "reconciliation_delta": (
                round(0.0 - expected_total, 2) if expected_total is not None else 0.0
            ),
            "is_reconciled": False,
            "reconciliation_status": "empty_export",
        }

    headers = [str(h).strip() for h in rows[0]]
    candidates_lower = {str(c).strip().lower() for c in amount_column_candidates}
    col_idx: int | None = None
    amount_column_name: str | None = None

    for idx, header in enumerate(headers):
        if header.lower() in candidates_lower:
            col_idx = idx
            amount_column_name = header
            break

    valid_amount_rows = 0
    invalid_amount_rows = 0
    csv_sum_amount = 0.0

    if col_idx is not None:
        for row in rows[1:]:
            raw_cell = str(row[col_idx]) if col_idx < len(row) else ""
            cleaned = (
                raw_cell.strip()
                .lstrip("'")
                .replace("$", "")
                .replace(",", "")
                .strip()
            )
            if not cleaned:
                invalid_amount_rows += 1
            else:
                try:
                    val = float(cleaned)
                    csv_sum_amount += val
                    valid_amount_rows += 1
                except (ValueError, TypeError):
                    invalid_amount_rows += 1

    csv_sum_amount = round(csv_sum_amount, 2)

    if expected_total is not None:
        reconciliation_delta = round(csv_sum_amount - expected_total, 2)
        is_reconciled = bool(
            abs(reconciliation_delta) <= 0.01
            and invalid_amount_rows == 0
            and amount_column_name is not None
        )
    else:
        reconciliation_delta = 0.0
        is_reconciled = bool(
            invalid_amount_rows == 0 and amount_column_name is not None
        )

    if amount_column_name is None:
        reconciliation_status = "missing_amount_column"
    elif invalid_amount_rows > 0:
        reconciliation_status = "parse_errors_detected"
    elif is_reconciled:
        reconciliation_status = "reconciled"
    else:
        reconciliation_status = "discrepancy_detected"

    return {
        "amount_column_name": amount_column_name,
        "valid_amount_rows": valid_amount_rows,
        "invalid_amount_rows": invalid_amount_rows,
        "csv_sum_amount": csv_sum_amount,
        "expected_ac_total": expected_total,
        "reconciliation_delta": reconciliation_delta,
        "is_reconciled": is_reconciled,
        "reconciliation_status": reconciliation_status,
    }


def audit_tasks_csv_schedule_completeness(
    csv_content: str | bytes | None,
) -> dict[str, Any]:
    """Audita la completitud de fechas y responsables en el CSV exportado de tareas (PMI PMBOK §6.5 / §9.3)."""
    if isinstance(csv_content, (bytes, bytearray)):
        text = bytes(csv_content).decode("utf-8-sig", errors="replace").lstrip("\ufeff")
    elif isinstance(csv_content, str):
        text = csv_content.lstrip("\ufeff")
    else:
        text = ""

    if not text.strip():
        return {
            "total_tasks": 0,
            "dated_tasks_count": 0,
            "assigned_tasks_count": 0,
            "fully_scheduled_tasks_count": 0,
            "unscheduled_tasks_count": 0,
            "schedule_coverage_pct": 0.0,
            "schedule_completeness_status": "empty_export",
        }

    rows = [
        r
        for r in csv.reader(io.StringIO(text))
        if any(str(cell).strip() for cell in r)
    ]
    if len(rows) == 0:
        return {
            "total_tasks": 0,
            "dated_tasks_count": 0,
            "assigned_tasks_count": 0,
            "fully_scheduled_tasks_count": 0,
            "unscheduled_tasks_count": 0,
            "schedule_coverage_pct": 0.0,
            "schedule_completeness_status": "empty_export",
        }

    headers = [str(h).strip().lower() for h in rows[0]]
    due_candidates = {"fecha límite", "fecha limite", "due_date", "vencimiento", "fin"}
    assignee_candidates = {"responsable", "asignado", "assignee", "owner"}

    due_idx: int | None = None
    assignee_idx: int | None = None
    for idx, h in enumerate(headers):
        if due_idx is None and h in due_candidates:
            due_idx = idx
        if assignee_idx is None and h in assignee_candidates:
            assignee_idx = idx

    data_rows = rows[1:]
    total_tasks = len(data_rows)
    dated_tasks_count = 0
    assigned_tasks_count = 0
    fully_scheduled_tasks_count = 0

    empty_due_tokens = {"", "-", "n/a", "sin fecha", "none"}
    empty_assignee_tokens = {"", "-", "n/a", "sin asignar", "unassigned", "none"}

    for row in data_rows:
        has_due = False
        if due_idx is not None and due_idx < len(row):
            due_val = str(row[due_idx]).strip().lstrip("'").strip()
            if due_val.lower() not in empty_due_tokens:
                has_due = True

        has_assignee = False
        if assignee_idx is not None and assignee_idx < len(row):
            assignee_val = str(row[assignee_idx]).strip().lstrip("'").strip()
            if assignee_val.lower() not in empty_assignee_tokens:
                has_assignee = True

        if has_due:
            dated_tasks_count += 1
        if has_assignee:
            assigned_tasks_count += 1
        if has_due and has_assignee:
            fully_scheduled_tasks_count += 1

    schedule_coverage_pct = (
        round((fully_scheduled_tasks_count / total_tasks) * 100.0, 2)
        if total_tasks > 0
        else 0.0
    )
    unscheduled_tasks_count = total_tasks - fully_scheduled_tasks_count

    if len(rows) == 0 or total_tasks == 0:
        schedule_completeness_status = "empty_export"
    elif due_idx is None or assignee_idx is None:
        schedule_completeness_status = "missing_schedule_columns"
    elif schedule_coverage_pct == 100.0:
        schedule_completeness_status = "fully_baselined"
    elif schedule_coverage_pct >= 50.0:
        schedule_completeness_status = "partial_schedule_gaps"
    else:
        schedule_completeness_status = "critical_unscheduled_backlog"

    return {
        "total_tasks": total_tasks,
        "dated_tasks_count": dated_tasks_count,
        "assigned_tasks_count": assigned_tasks_count,
        "fully_scheduled_tasks_count": fully_scheduled_tasks_count,
        "unscheduled_tasks_count": unscheduled_tasks_count,
        "schedule_coverage_pct": schedule_coverage_pct,
        "schedule_completeness_status": schedule_completeness_status,
    }
