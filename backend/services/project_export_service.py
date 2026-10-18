"""Servicio de exportación 360° de Proyectos, incluida la gobernanza PMI."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
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
    "audit_executive_report_milestone_coverage",
    "audit_executive_report_milestone_deliverables",
    "audit_risks_csv_register_completeness",
    "audit_stakeholders_csv_engagement_gaps",
    "audit_expenses_vendor_concentration",
    "audit_executive_report_change_governance",
    "audit_executive_report_benefits_realization",
    "audit_executive_report_esg_sustainability_and_regulatory_compliance",
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

    @staticmethod
    def audit_executive_report_milestone_coverage(
        html_content: str | None,
    ) -> dict[str, Any]:
        return audit_executive_report_milestone_coverage(html_content)

    @staticmethod
    def audit_executive_report_milestone_deliverables(
        report_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return audit_executive_report_milestone_deliverables(report_payload)

    @staticmethod
    def audit_risks_csv_register_completeness(
        csv_content: str | None,
    ) -> dict[str, Any]:
        return audit_risks_csv_register_completeness(csv_content)

    @staticmethod
    def audit_expenses_vendor_concentration(
        csv_content: str | None,
    ) -> dict[str, Any]:
        return audit_expenses_vendor_concentration(csv_content)

    @staticmethod
    def audit_executive_report_change_governance(
        report_data: Optional[dict],
    ) -> dict[str, Any]:
        return audit_executive_report_change_governance(report_data)

    @staticmethod
    def audit_executive_report_benefits_realization(
        report_payload: dict[str, Any] | None = None,
        min_realization_pct: float = 80.0,
    ) -> dict[str, Any]:
        return audit_executive_report_benefits_realization(
            report_payload,
            min_realization_pct=min_realization_pct,
        )

    @staticmethod
    def audit_executive_report_quality_disclosure(
        report_data: Optional[dict],
    ) -> dict[str, Any]:
        return audit_executive_report_quality_disclosure(report_data)

    @staticmethod
    def audit_executive_report_resource_workload(
        report_data: Optional[dict],
    ) -> dict[str, Any]:
        return audit_executive_report_resource_workload(report_data)

    @staticmethod
    def audit_executive_report_procurement_sla_and_holdbacks(
        report_payload: dict[str, Any] | None = None,
        min_holdback_pct: float = 5.0,
    ) -> dict[str, Any]:
        return audit_executive_report_procurement_sla_and_holdbacks(
            report_payload,
            min_holdback_pct=min_holdback_pct,
        )

    @staticmethod
    def audit_executive_report_procurement_slas(
        report_data: Optional[dict],
    ) -> dict[str, Any]:
        return audit_executive_report_procurement_slas(report_data)

    @staticmethod
    def audit_executive_report_stakeholder_communications(
        report_payload: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        return audit_executive_report_stakeholder_communications(report_payload)

    @staticmethod
    def audit_executive_report_risk_burndown(
        report_payload: Optional[dict[str, Any]],
        max_residual_to_initial_ratio_pct: float = 60.0,
    ) -> dict[str, Any]:
        return audit_executive_report_risk_burndown(
            report_payload,
            max_residual_to_initial_ratio_pct=max_residual_to_initial_ratio_pct,
        )




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


def audit_executive_report_milestone_coverage(
    html_content: str | None,
) -> dict[str, Any]:
    """Audita la cobertura de hitos, alertas de atraso y KPIs financieros en el reporte ejecutivo (PMI PMBOK §10.2)."""
    text = (html_content if isinstance(html_content, str) else "").lower()

    if not text.strip():
        return {
            "has_milestone_section": False,
            "completed_markers_count": 0,
            "overdue_or_delayed_markers_count": 0,
            "financial_kpi_mentions": 0,
            "coverage_score": 0.0,
            "posture": "EMPTY_REPORT",
        }

    milestone_tokens = ("hito", "milestone", "fase", "entregable", "cronograma")
    completed_tokens = ("completad", "100%", "finalizad", "cumplid")
    overdue_tokens = ("vencid", "retrasad", "atrasad", "overdue", "bloquead")
    financial_tokens = ("presupuesto", "cpi", "spi", "eac", "vac", "bac", "gasto")

    has_milestone_section = any(token in text for token in milestone_tokens)
    completed_markers_count = int(sum(text.count(token) for token in completed_tokens))
    overdue_or_delayed_markers_count = int(
        sum(text.count(token) for token in overdue_tokens)
    )
    financial_kpi_mentions = int(sum(text.count(token) for token in financial_tokens))

    score = 0.0
    if has_milestone_section:
        score += 40.0
    if financial_kpi_mentions > 0:
        score += 30.0
    if (completed_markers_count + overdue_or_delayed_markers_count) > 0:
        score += 30.0
    coverage_score = round(score, 2)

    if overdue_or_delayed_markers_count > 0:
        posture = "EXECUTIVE_ATTENTION_REQUIRED"
    elif coverage_score >= 80.0 and overdue_or_delayed_markers_count == 0:
        posture = "COMPREHENSIVE_EXECUTIVE_SUMMARY"
    else:
        posture = "PARTIAL_REPORT_COVERAGE"

    return {
        "has_milestone_section": has_milestone_section,
        "completed_markers_count": completed_markers_count,
        "overdue_or_delayed_markers_count": overdue_or_delayed_markers_count,
        "financial_kpi_mentions": financial_kpi_mentions,
        "coverage_score": coverage_score,
        "posture": posture,
    }


def audit_executive_report_benefits_realization(
    report_payload: dict[str, Any] | None = None,
    min_realization_pct: float = 80.0,
) -> dict[str, Any]:
    """Audita la realización de beneficios y KPIs estratégicos del informe (PMBOK §1.2.6.2).

    Extrae los beneficios desde `benefits`, `benefits_register` o
    `strategic_kpis` (primera fuente con dicts). Cada beneficio declara
    `id`/`benefit_id`/`code` (fallback 'BEN-{idx}'), responsable
    (`benefit_owner`/`owner`/`responsable`), meta (`target_value`/`target`/
    `planned_value`) y valor actual (`actual_value`/`realized_value`/
    `current_value`, default 0.0):
    - `unowned_benefit_ids`: sin responsable;
    - `unmeasurable_benefit_ids`: meta ausente o <= 0;
    - `underperforming_benefit_ids`: ratio < min_realization_pct.
    - `average_realization_pct`: promedio de ratios clamp [0, 100] (2 dec; 0.0 vacío).
    - `is_benefits_on_track`: las 3 listas de faltantes vacías.
    - `benefits_posture`: 'NO_BENEFITS_REPORTED' sin beneficios;
      'UNOWNED_OR_UNMEASURABLE_BENEFIT'; 'BENEFITS_REALIZATION_SHORTFALL';
      'STRATEGIC_BENEFITS_ON_TRACK'.
    """
    benefits: list[dict[str, Any]] = []
    if isinstance(report_payload, dict):
        for source_key in ("benefits", "benefits_register", "strategic_kpis"):
            candidate = report_payload.get(source_key)
            if isinstance(candidate, list):
                benefits = [b for b in candidate if isinstance(b, dict)]
                if benefits:
                    break
    total_benefits = len(benefits)
    if total_benefits == 0:
        return {
            "total_benefits": 0,
            "average_realization_pct": 0.0,
            "unowned_benefit_ids": [],
            "unmeasurable_benefit_ids": [],
            "underperforming_benefit_ids": [],
            "is_benefits_on_track": True,
            "benefits_posture": "NO_BENEFITS_REPORTED",
        }

    unowned_benefit_ids: list[str] = []
    unmeasurable_benefit_ids: list[str] = []
    underperforming_benefit_ids: list[str] = []
    realization_scores: list[float] = []

    for idx, item in enumerate(benefits, start=1):
        benefit_id = str(
            item.get("id") or item.get("benefit_id") or item.get("code") or f"BEN-{idx}"
        ).strip()
        benefit_owner = str(
            item.get("benefit_owner") or item.get("owner") or item.get("responsable") or ""
        ).strip()
        target_raw = (
            item.get("target_value")
            if item.get("target_value") is not None
            else (item.get("target") if item.get("target") is not None else item.get("planned_value"))
        )
        actual_raw = (
            item.get("actual_value")
            if item.get("actual_value") is not None
            else (item.get("realized_value") if item.get("realized_value") is not None else (item.get("current_value") or 0.0))
        )
        try:
            actual_value = float(actual_raw)
        except (TypeError, ValueError):
            actual_value = 0.0

        target_value: float | None
        try:
            target_value = float(target_raw) if target_raw is not None else None
        except (TypeError, ValueError):
            target_value = None

        if not benefit_owner:
            unowned_benefit_ids.append(benefit_id)
        if target_value is None or target_value <= 0.0:
            unmeasurable_benefit_ids.append(benefit_id)
        if target_value is not None and target_value > 0.0:
            ratio = min(100.0, max(0.0, (actual_value / target_value) * 100.0))
            realization_scores.append(ratio)
            if ratio + 1e-9 < float(min_realization_pct):
                underperforming_benefit_ids.append(benefit_id)

    average_realization_pct = (
        round(sum(realization_scores) / len(realization_scores), 2)
        if realization_scores
        else 0.0
    )
    is_benefits_on_track = bool(
        len(unowned_benefit_ids) == 0
        and len(unmeasurable_benefit_ids) == 0
        and len(underperforming_benefit_ids) == 0
    )

    if total_benefits == 0:
        benefits_posture = "NO_BENEFITS_REPORTED"
    elif unowned_benefit_ids or unmeasurable_benefit_ids:
        benefits_posture = "UNOWNED_OR_UNMEASURABLE_BENEFIT"
    elif underperforming_benefit_ids:
        benefits_posture = "BENEFITS_REALIZATION_SHORTFALL"
    else:
        benefits_posture = "STRATEGIC_BENEFITS_ON_TRACK"

    return {
        "total_benefits": total_benefits,
        "average_realization_pct": average_realization_pct,
        "unowned_benefit_ids": unowned_benefit_ids,
        "unmeasurable_benefit_ids": unmeasurable_benefit_ids,
        "underperforming_benefit_ids": underperforming_benefit_ids,
        "is_benefits_on_track": is_benefits_on_track,
        "benefits_posture": benefits_posture,
    }


def audit_executive_report_milestone_deliverables(
    report_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Audita los hitos y entregables divulgados en el informe ejecutivo (PMBOK §6.2.3.3 y §5.4).

    Extrae los hitos en orden desde `milestones`, `milestone_summary` o
    `cpm_schedule['milestones']` (solo dicts). Cada hito declara `id`/
    `milestone_id`/`code` (fallback 'MS-{idx}'), `due_date`/`target_date`/
    `baseline_date`, `status` y evidencia de aceptacion (`accepted_by`/
    `signoff_ref`/`deliverable_ref`):
    - `unscheduled_milestone_ids`: hitos sin fecha base/objetivo.
    - `unverified_completed_milestone_ids`: completados sin evidencia de signoff.
    - `overdue_milestone_ids`: `is_overdue` True o status vencido/retrasado.
    - `is_traceable`: sin faltantes en las 3 listas y con hitos divulgados.
    - `milestone_posture`: 'NO_MILESTONES_DISCLOSED' sin hitos;
      'UNVERIFIED_COMPLETED_MILESTONES'; 'UNSCHEDULED_MILESTONE_BASELINES';
      'OVERDUE_KEY_MILESTONES'; 'VERIFIED_MILESTONE_DELIVERY_GOVERNANCE'
    """
    milestones: List[Dict[str, Any]] = []
    if isinstance(report_payload, dict):
        for source_key in ("milestones", "milestone_summary", "cpm_schedule"):
            candidate = report_payload.get(source_key)
            if source_key == "cpm_schedule" and isinstance(candidate, dict):
                candidate = candidate.get("milestones")
            if isinstance(candidate, list):
                milestones.extend(item for item in candidate if isinstance(item, dict))
                if milestones:
                    break
    total_milestones = len(milestones)
    if total_milestones == 0:
        return {
            "total_milestones": 0,
            "completed_milestones_count": 0,
            "unscheduled_milestone_ids": [],
            "unverified_completed_milestone_ids": [],
            "overdue_milestone_ids": [],
            "is_traceable": False,
            "milestone_posture": "NO_MILESTONES_DISCLOSED",
        }

    COMPLETED_STATUS = {"completed", "achieved", "done", "completado", "logrado"}
    OVERDUE_STATUS = {"overdue", "delayed", "vencido", "retrasado"}

    unscheduled_milestone_ids: List[str] = []
    unverified_completed_milestone_ids: List[str] = []
    overdue_milestone_ids: List[str] = []
    completed_milestones_count = 0

    for idx, item in enumerate(milestones, start=1):
        ms_id = str(
            item.get("id") or item.get("milestone_id") or item.get("code") or ""
        ).strip() or f"MS-{idx}"
        due = str(
            item.get("due_date") or item.get("target_date") or item.get("baseline_date") or ""
        ).strip()
        status = str(item.get("status") or "").strip().lower()
        signoff = str(
            item.get("accepted_by") or item.get("signoff_ref") or item.get("deliverable_ref") or ""
        ).strip()

        if not due:
            unscheduled_milestone_ids.append(ms_id)
        if status in COMPLETED_STATUS:
            completed_milestones_count += 1
            if not signoff:
                unverified_completed_milestone_ids.append(ms_id)
        elif item.get("is_overdue") is True or status in OVERDUE_STATUS:
            overdue_milestone_ids.append(ms_id)

    is_traceable = bool(
        total_milestones > 0
        and len(unscheduled_milestone_ids) == 0
        and len(unverified_completed_milestone_ids) == 0
        and len(overdue_milestone_ids) == 0
    )

    if len(unverified_completed_milestone_ids) > 0:
        milestone_posture = "UNVERIFIED_COMPLETED_MILESTONES"
    elif len(unscheduled_milestone_ids) > 0:
        milestone_posture = "UNSCHEDULED_MILESTONE_BASELINES"
    elif len(overdue_milestone_ids) > 0:
        milestone_posture = "OVERDUE_KEY_MILESTONES"
    else:
        milestone_posture = "VERIFIED_MILESTONE_DELIVERY_GOVERNANCE"

    return {
        "total_milestones": total_milestones,
        "completed_milestones_count": completed_milestones_count,
        "unscheduled_milestone_ids": unscheduled_milestone_ids,
        "unverified_completed_milestone_ids": unverified_completed_milestone_ids,
        "overdue_milestone_ids": overdue_milestone_ids,
        "is_traceable": is_traceable,
        "milestone_posture": milestone_posture,
    }


def audit_risks_csv_register_completeness(
    csv_content: str | None,
) -> dict[str, Any]:
    """Audita un archivo CSV exportado del Registro de Riesgos según PMI PMBOK §11.2 (Identify Risks)."""
    text = (csv_content if isinstance(csv_content, str) else "").lstrip("\ufeff")

    if not text.strip():
        return {
            "total_rows": 0,
            "mitigation_documented_rows": 0,
            "owner_assigned_rows": 0,
            "scored_rows": 0,
            "mitigation_coverage_pct": 0.0,
            "posture": "EMPTY_RISK_EXPORT",
        }

    reader = csv.DictReader(io.StringIO(text))
    mitigation_keys = (
        "mitigacion",
        "mitigación",
        "mitigation",
        "mitigation_plan",
        "response_plan",
        "plan_mitigacion",
    )
    owner_keys = ("responsable", "owner", "assigned_to", "propietario")
    prob_keys = ("probabilidad", "probability")
    impact_keys = ("impacto", "impact")

    total_rows = 0
    mitigation_documented_rows = 0
    owner_assigned_rows = 0
    scored_rows = 0

    for raw_row in reader:
        if not isinstance(raw_row, dict):
            continue
        norm_row = {
            str(k).lstrip("\ufeff").strip().lower(): str(v or "")
            for k, v in raw_row.items()
            if k is not None
        }
        if not any(v.strip() for v in norm_row.values()):
            continue

        total_rows += 1

        if any(len(norm_row.get(k, "").strip()) >= 5 for k in mitigation_keys):
            mitigation_documented_rows += 1

        if any(bool(norm_row.get(k, "").strip()) for k in owner_keys):
            owner_assigned_rows += 1

        has_prob = any(bool(norm_row.get(k, "").strip()) for k in prob_keys)
        has_impact = any(bool(norm_row.get(k, "").strip()) for k in impact_keys)
        if has_prob and has_impact:
            scored_rows += 1

    mitigation_coverage_pct = (
        round((mitigation_documented_rows / total_rows) * 100.0, 2)
        if total_rows > 0
        else 0.0
    )

    if total_rows == 0:
        posture = "EMPTY_RISK_EXPORT"
    elif (
        mitigation_coverage_pct >= 80.0
        and owner_assigned_rows == total_rows
        and scored_rows == total_rows
    ):
        posture = "AUDIT_READY_RISK_REGISTER"
    elif mitigation_coverage_pct < 50.0:
        posture = "UNMITIGATED_EXPOSURE_GAPS"
    else:
        posture = "PARTIAL_REGISTER_GOVERNANCE"

    return {
        "total_rows": total_rows,
        "mitigation_documented_rows": mitigation_documented_rows,
        "owner_assigned_rows": owner_assigned_rows,
        "scored_rows": scored_rows,
        "mitigation_coverage_pct": mitigation_coverage_pct,
        "posture": posture,
    }


def audit_stakeholders_csv_engagement_gaps(
    csv_content: str | None,
) -> dict[str, Any]:
    """Audita un CSV del registro de interesados según PMI PMBOK §13.1 / §13.4.

    Parse con csv.DictReader normalizando claves (strip+lower) e ignorando
    filas vacías, y calcula:
    - `total_rows`: filas de datos válidas.
    - `high_power_rows`: poder/alto impacto según la columna
      'poder'/'power'/'influence'/'influencia' en
      ('high','alto','alta','critical','critico','crítico','4','5').
    - `resistant_or_unaware_rows`: engagement 'unaware'/'desconocedor' o
      'resistant'/'resistente' en 'engagement'/'compromiso'/'current_engagement'/'postura'.
    - `supportive_or_leading_rows`: engagement 'supportive'/'apoyo' o
      'leading'/'lider'/'líder'.
    - `alignment_rate`: % de filas en engagement positivo (2 decimales;
      0.0 sin filas).
    - `posture`: 'EMPTY_STAKEHOLDER_EXPORT' sin filas;
      'CRITICAL_ENGAGEMENT_RESISTANCE' con resistencia;
      'STRONG_STAKEHOLDER_COALITION' con alignment >= 75.0; y
      'NEUTRAL_ENGAGEMENT_POSTURE' en otro caso.
    """
    text = (csv_content if isinstance(csv_content, str) else "").lstrip("\ufeff")

    if not text.strip():
        return {
            "total_rows": 0,
            "high_power_rows": 0,
            "resistant_or_unaware_rows": 0,
            "supportive_or_leading_rows": 0,
            "alignment_rate": 0.0,
            "posture": "EMPTY_STAKEHOLDER_EXPORT",
        }

    reader = csv.DictReader(io.StringIO(text))
    power_keys = ("poder", "power", "influence", "influencia")
    engagement_keys = ("engagement", "compromiso", "current_engagement", "postura")
    high_power_values = {
        "high", "alto", "alta", "critical", "critico", "crítico", "4", "5"
    }
    resistant_values = {"unaware", "desconocedor", "resistant", "resistente"}
    supportive_values = {"supportive", "apoyo", "leading", "lider", "líder"}

    total_rows = 0
    high_power_rows = 0
    resistant_or_unaware_rows = 0
    supportive_or_leading_rows = 0

    for raw_row in reader:
        if not isinstance(raw_row, dict):
            continue
        norm_row = {
            str(k).lstrip("\ufeff").strip().lower(): str(v or "")
            for k, v in raw_row.items()
            if k is not None
        }
        if not any(v.strip() for v in norm_row.values()):
            continue

        total_rows += 1

        power_text = next(
            (norm_row.get(k, "") for k in power_keys if norm_row.get(k, "").strip()),
            "",
        ).strip().lower()
        engagement_text = next(
            (
                norm_row.get(k, "")
                for k in engagement_keys
                if norm_row.get(k, "").strip()
            ),
            "",
        ).strip().lower()

        if power_text in high_power_values:
            high_power_rows += 1
        if engagement_text in resistant_values:
            resistant_or_unaware_rows += 1
        elif engagement_text in supportive_values:
            supportive_or_leading_rows += 1

    alignment_rate = (
        round((supportive_or_leading_rows / total_rows) * 100.0, 2)
        if total_rows > 0
        else 0.0
    )

    if total_rows == 0:
        posture = "EMPTY_STAKEHOLDER_EXPORT"
    elif resistant_or_unaware_rows > 0:
        posture = "CRITICAL_ENGAGEMENT_RESISTANCE"
    elif alignment_rate >= 75.0:
        posture = "STRONG_STAKEHOLDER_COALITION"
    else:
        posture = "NEUTRAL_ENGAGEMENT_POSTURE"

    return {
        "total_rows": total_rows,
        "high_power_rows": high_power_rows,
        "resistant_or_unaware_rows": resistant_or_unaware_rows,
        "supportive_or_leading_rows": supportive_or_leading_rows,
        "alignment_rate": alignment_rate,
        "posture": posture,
    }


def audit_expenses_vendor_concentration(
    csv_content: str | None,
) -> dict[str, Any]:
    """Audita la concentración de proveedores y trazabilidad de adquisiciones en un CSV exportado de gastos según PMI PMBOK §12.1 y §7.4."""
    text = (csv_content if isinstance(csv_content, str) else "").lstrip("\ufeff")
    if not text.strip():
        return {
            "total_rows": 0,
            "total_spend": 0.0,
            "vendor_documented_rows": 0,
            "unique_vendors_count": 0,
            "top_vendor_share_pct": 0.0,
            "posture": "EMPTY_EXPENSES_EXPORT",
        }

    reader = csv.DictReader(io.StringIO(text))
    amount_keys = ("monto", "amount", "importe", "costo", "cost", "valor")
    vendor_keys = ("proveedor", "vendor", "supplier", "beneficiario", "contratista")

    total_rows = 0
    total_spend_raw = 0.0
    vendor_documented_rows = 0
    vendor_totals: dict[str, float] = {}

    for raw_row in reader:
        if not isinstance(raw_row, dict):
            continue
        norm_row: dict[str, str] = {}
        for k, v in raw_row.items():
            if k is None:
                continue
            key = str(k).lstrip("\ufeff").strip().lower()
            if isinstance(v, list):
                norm_row[key] = ",".join(str(part) for part in v)
            else:
                norm_row[key] = str(v or "")
        if not any(val.strip() for val in norm_row.values()):
            continue

        total_rows += 1

        amount_str = next(
            (norm_row.get(k, "") for k in amount_keys if norm_row.get(k, "").strip()),
            "",
        ).strip()
        cleaned_amount = amount_str.replace("$", "").replace(",", "").strip()
        try:
            row_amount = max(0.0, float(cleaned_amount)) if cleaned_amount else 0.0
        except (ValueError, TypeError):
            row_amount = 0.0

        total_spend_raw += row_amount

        vendor_str = next(
            (norm_row.get(k, "") for k in vendor_keys if norm_row.get(k, "").strip()),
            "",
        ).strip()
        if vendor_str:
            vendor_documented_rows += 1
            vendor_key = vendor_str.lower()
            vendor_totals[vendor_key] = vendor_totals.get(vendor_key, 0.0) + row_amount

    total_spend = round(total_spend_raw, 2)
    unique_vendors_count = len(vendor_totals)
    max_vendor_spend = max(vendor_totals.values(), default=0.0)
    top_vendor_share_pct = (
        round((max_vendor_spend / total_spend) * 100.0, 2)
        if total_spend > 0 and unique_vendors_count > 0
        else 0.0
    )

    if total_rows == 0:
        posture = "EMPTY_EXPENSES_EXPORT"
    elif vendor_documented_rows < total_rows:
        posture = "UNATTRIBUTED_VENDOR_SPEND"
    elif (
        vendor_documented_rows == total_rows
        and total_rows >= 2
        and top_vendor_share_pct >= 70.0
    ):
        posture = "SINGLE_SOURCE_CONCENTRATION_RISK"
    else:
        posture = "DIVERSIFIED_PROCUREMENT_POSTURE"

    return {
        "total_rows": total_rows,
        "total_spend": total_spend,
        "vendor_documented_rows": vendor_documented_rows,
        "unique_vendors_count": unique_vendors_count,
        "top_vendor_share_pct": top_vendor_share_pct,
        "posture": posture,
    }


def audit_executive_report_change_governance(
    report_data: Optional[dict],
) -> dict[str, Any]:
    """Audita la gobernanza de control de cambios y línea base del reporte ejecutivo según PMI PMBOK §10.2 y §4.6."""
    data = report_data if isinstance(report_data, dict) else {}
    ccb_summary = (
        data.get("ccb_and_quality_summary")
        if isinstance(data.get("ccb_and_quality_summary"), dict)
        else {}
    )
    raw_requests = (
        data.get("change_requests")
        if isinstance(data.get("change_requests"), list)
        else data.get("ccb_requests")
        if isinstance(data.get("ccb_requests"), list)
        else ccb_summary.get("change_requests")
        if isinstance(ccb_summary.get("change_requests"), list)
        else ccb_summary.get("ccb_requests")
        if isinstance(ccb_summary.get("ccb_requests"), list)
        else []
    )

    items = [item for item in raw_requests if isinstance(item, dict)]
    total_requests = len(items)
    approved_count = 0
    rejected_count = 0
    pending_count = 0
    untraceable_decisions: list[str] = []
    net_approved_cost_raw = 0.0
    net_approved_schedule_raw = 0.0

    for idx, item in enumerate(items):
        req_id = str(item.get("id") or item.get("code") or f"CR-{idx + 1}").strip()
        status = str(item.get("status") or "").strip().upper()
        try:
            cost_impact = float(item.get("cost_impact") or 0.0)
        except (ValueError, TypeError):
            cost_impact = 0.0
        try:
            schedule_impact = float(item.get("schedule_impact_days") or 0.0)
        except (ValueError, TypeError):
            schedule_impact = 0.0

        has_minutes = bool(item.get("has_ccb_minutes")) or bool(
            str(item.get("ccb_minutes_ref") or "").strip()
        )

        if status == "APPROVED":
            approved_count += 1
            net_approved_cost_raw += cost_impact
            net_approved_schedule_raw += schedule_impact
            if not has_minutes:
                untraceable_decisions.append(req_id)
        elif status == "REJECTED":
            rejected_count += 1
            if not has_minutes:
                untraceable_decisions.append(req_id)
        elif status == "PENDING":
            pending_count += 1

    net_approved_cost_impact = round(net_approved_cost_raw, 2)
    net_approved_schedule_days = round(net_approved_schedule_raw, 2)

    recommendations: list[str] = []
    if total_requests == 0:
        governance_posture = "NO_CHANGE_ACTIVITY"
        recommendations.append(
            "Mantener monitoreo de línea base conforme a PMI PMBOK §4.6."
        )
    elif len(untraceable_decisions) > 0:
        governance_posture = "UNCONTROLLED_CHANGES"
        recommendations.append(
            "Vincular actas formales del Comité de Control de Cambios (CCB) a todas las decisiones aprobadas o rechazadas (PMI §4.6)."
        )
    elif pending_count / total_requests >= 0.5:
        governance_posture = "PENDING_BACKLOG_BOTTLENECK"
        recommendations.append(
            "Convocar sesión extraordinaria del CCB para destrabar las solicitudes pendientes y evitar deriva de alcance/cronograma."
        )
    else:
        governance_posture = "BASELINE_GOVERNED"
        recommendations.append(
            "Gobernanza de cambios controlada y trazable con actas CCB verificadas."
        )

    return {
        "total_requests": total_requests,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "pending_count": pending_count,
        "untraceable_decisions": untraceable_decisions,
        "net_approved_cost_impact": net_approved_cost_impact,
        "net_approved_schedule_days": net_approved_schedule_days,
        "governance_posture": governance_posture,
        "recommendations": recommendations,
    }


def audit_executive_report_quality_disclosure(
    report_data: Optional[dict],
) -> dict[str, Any]:
    """Audita la divulgación de Costo de la Calidad (CoQ) y aceptación DoD en el reporte ejecutivo (PMBOK §8.2 y §10.2)."""
    data = report_data if isinstance(report_data, dict) else {}

    summary_block: dict[str, Any] = {}
    for key in ("ccb_quality_summary", "quality_kpis", "ccb_and_quality_summary"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            summary_block = candidate
            break
    if not summary_block:
        summary_block = data

    coq_block = (
        summary_block.get("coq_by_category")
        if isinstance(summary_block.get("coq_by_category"), dict)
        else data.get("coq_by_category")
        if isinstance(data.get("coq_by_category"), dict)
        else {}
    )

    def _safe_float(source_a: dict[str, Any], source_b: dict[str, Any], *keys: str) -> float:
        for k in keys:
            val = source_a.get(k)
            if val is None:
                val = source_b.get(k)
            if val is not None:
                try:
                    return max(0.0, float(val))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _safe_int(source_a: dict[str, Any], source_b: dict[str, Any], *keys: str) -> int:
        for k in keys:
            val = source_a.get(k)
            if val is None:
                val = source_b.get(k)
            if val is not None:
                try:
                    return max(0, int(val))
                except (TypeError, ValueError):
                    return 0
        return 0

    prevention = _safe_float(coq_block, summary_block, "prevention", "prevention_cost")
    appraisal = _safe_float(coq_block, summary_block, "appraisal", "appraisal_cost")
    internal_failure = _safe_float(
        coq_block, summary_block, "internal_failure", "internal_failure_cost"
    )
    external_failure = _safe_float(
        coq_block, summary_block, "external_failure", "external_failure_cost"
    )

    tasks_dod_accepted_count = _safe_int(
        summary_block, data, "tasks_dod_accepted_count", "dod_accepted_count"
    )
    total_completed_tasks = _safe_int(
        summary_block, data, "total_completed_tasks", "completed_tasks_count"
    )

    conformance_cost = round(prevention + appraisal, 2)
    nonconformance_cost = round(internal_failure + external_failure, 2)
    total_coq_cost = round(conformance_cost + nonconformance_cost, 2)

    conformance_ratio_pct = (
        round((conformance_cost / total_coq_cost) * 100.0, 2)
        if total_coq_cost > 0
        else 0.0
    )

    if total_completed_tasks > 0:
        dod_acceptance_coverage_pct = round(
            min(100.0, (tasks_dod_accepted_count / total_completed_tasks) * 100.0), 2
        )
    elif tasks_dod_accepted_count > 0:
        dod_acceptance_coverage_pct = 100.0
    else:
        dod_acceptance_coverage_pct = 0.0

    recommendations: list[str] = []
    if (
        total_coq_cost <= 0
        and tasks_dod_accepted_count <= 0
        and total_completed_tasks <= 0
    ):
        quality_disclosure_posture = "NO_QUALITY_METRICS_DISCLOSED"
        recommendations.append(
            "Incluir desglose de Costo de la Calidad (CoQ) y cobertura de aceptación DoD en el reporte ejecutivo (PMBOK §8.2 / §10.2)."
        )
    elif total_coq_cost > 0 and nonconformance_cost > conformance_cost:
        quality_disclosure_posture = "FAILURE_COST_DOMINATED"
        recommendations.append(
            f"Los costos de no conformidad ({nonconformance_cost}) superan la inversión en conformidad ({conformance_cost}). Rebalancear presupuesto hacia prevención e inspección temprana (PMBOK §8.2)."
        )
    elif total_completed_tasks > 0 and dod_acceptance_coverage_pct < 80.0:
        quality_disclosure_posture = "UNVERIFIED_COMPLETED_DELIVERABLES"
        recommendations.append(
            f"Cobertura de aceptación DoD ({dod_acceptance_coverage_pct}%) inferior al 80% sobre tareas completadas ({tasks_dod_accepted_count}/{total_completed_tasks}). Exigir verificación formal antes de cerrar entregables (PMBOK §8.3)."
        )
    else:
        quality_disclosure_posture = "PROACTIVE_QUALITY_GOVERNANCE"
        recommendations.append(
            "Gobernanza de calidad proactiva con inversión predominante en conformidad y alta cobertura de aceptación DoD verificada (PMBOK §8.2)."
        )

    return {
        "conformance_cost": conformance_cost,
        "nonconformance_cost": nonconformance_cost,
        "total_coq_cost": total_coq_cost,
        "conformance_ratio_pct": conformance_ratio_pct,
        "dod_acceptance_coverage_pct": dod_acceptance_coverage_pct,
        "quality_disclosure_posture": quality_disclosure_posture,
        "recommendations": recommendations,
    }


def audit_executive_report_resource_workload(
    report_data: Optional[dict],
) -> dict[str, Any]:
    """Audita la distribución de carga de trabajo y cuellos de botella del equipo en el reporte ejecutivo según PMI PMBOK §9.6 y §10.2."""
    data = report_data if isinstance(report_data, dict) else {}

    raw_members = (
        data.get("resource_allocations")
        if isinstance(data.get("resource_allocations"), list)
        else data.get("team_workload")
        if isinstance(data.get("team_workload"), list)
        else []
    )
    members = [m for m in raw_members if isinstance(m, dict)]

    total_members = len(members)
    overallocated_member_ids: list[str] = []
    underutilized_member_ids: list[str] = []
    bottleneck_member_ids: list[str] = []
    utilization_sum = 0.0

    for idx, member in enumerate(members, start=1):
        raw_id = (
            member.get("id")
            if member.get("id") is not None
            else member.get("member_id")
            if member.get("member_id") is not None
            else member.get("name")
        )
        member_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"RES-{idx}"
        )

        if member.get("utilization_pct") is not None:
            try:
                utilization_pct = max(0.0, float(member.get("utilization_pct") or 0.0))
            except (TypeError, ValueError):
                utilization_pct = 0.0
        else:
            try:
                allocated_hours = max(0.0, float(member.get("allocated_hours") or 0.0))
            except (TypeError, ValueError):
                allocated_hours = 0.0
            try:
                capacity_hours = max(0.0, float(member.get("capacity_hours") or 0.0))
            except (TypeError, ValueError):
                capacity_hours = 0.0
            utilization_pct = (
                (allocated_hours / capacity_hours) * 100.0
                if capacity_hours > 0.0
                else 0.0
            )

        try:
            overdue_tasks = max(0, int(member.get("overdue_tasks") or 0))
        except (TypeError, ValueError):
            overdue_tasks = 0

        utilization_sum += utilization_pct

        if utilization_pct > 100.0:
            overallocated_member_ids.append(member_id)
            if overdue_tasks > 0:
                bottleneck_member_ids.append(member_id)
        elif utilization_pct < 30.0:
            underutilized_member_ids.append(member_id)

    average_utilization_pct = (
        round(utilization_sum / total_members, 2) if total_members > 0 else 0.0
    )

    recommendations: list[str] = []
    if total_members == 0:
        workload_posture = "NO_RESOURCE_WORKLOAD_DATA"
        recommendations.append(
            "Incluir matriz de asignación y capacidad del equipo en el reporte ejecutivo para controlar recursos (PMBOK §9.6 / §10.2)."
        )
    elif len(bottleneck_member_ids) > 0:
        workload_posture = "CRITICAL_BOTTLENECK_OVERLOAD"
        recommendations.append(
            f"Aplicar nivelación de recursos (resource leveling) inmediata sobre miembros sobrecargados con tareas vencidas ({', '.join(bottleneck_member_ids)}) conforme a PMBOK §9.6."
        )
        if underutilized_member_ids:
            recommendations.append(
                f"Reasignar carga operativa hacia miembros con capacidad disponible ({', '.join(underutilized_member_ids)})."
            )
    elif len(overallocated_member_ids) > 0:
        workload_posture = "RESOURCE_OVERALLOCATION_RISK"
        recommendations.append(
            f"Ejecutar estabilización de recursos (resource smoothing) para reducir sobreasignación (>100%) en {', '.join(overallocated_member_ids)} antes de generar atrasos en ruta crítica (PMBOK §9.6)."
        )
    else:
        workload_posture = "BALANCED_TEAM_CAPACITY"
        recommendations.append(
            "Capacidad del equipo equilibrada sin sobreasignación crítica. Mantener monitoreo periódico de utilización (PMBOK §9.6)."
        )

    return {
        "total_members": total_members,
        "overallocated_member_ids": overallocated_member_ids,
        "underutilized_member_ids": underutilized_member_ids,
        "bottleneck_member_ids": bottleneck_member_ids,
        "average_utilization_pct": average_utilization_pct,
        "workload_posture": workload_posture,
        "recommendations": recommendations,
    }


def audit_executive_report_procurement_sla_and_holdbacks(
    report_payload: dict[str, Any] | None = None,
    min_holdback_pct: float = 5.0,
) -> dict[str, Any]:
    """Audita SLA de adquisiciones y retenciones de garantía (PMBOK §12.3).

    Contratos validos en `procurement_governance.contracts` (con
    `id`/`contract_id` no vacío). Cada contrato declara valor
    (`contract_value`), retención (`holdback_retained`), `sla_met`,
    `penalty_applied`, `deliverables_verified` y `holdback_released`:
    - `premature_holdback_release_ids`: retención liberada sin verificables.
    - `unpenalized_sla_breach_ids`: SLA incumplido sin penalización.
    - `insufficient_holdback_ids`: retención < min_holdback_pct del valor sin liberar.
    - `is_procurement_sla_governed`: con contratos y las 3 listas vacías.
    - `procurement_sla_posture`: 'NO_PROCUREMENT_CONTRACTS' vacío;
      'PREMATURE_WARRANTY_HOLDBACK_RELEASE'; 'UNPENALIZED_VENDOR_SLA_BREACH';
      'INSUFFICIENT_WARRANTY_HOLDBACK_RETENTION'; 'GOVERNED_PROCUREMENT_SLA_AND_HOLDBACKS'.
    """
    contracts_raw = ((report_payload or {}).get("procurement_governance") or {}).get("contracts")
    contracts = (
        [c for c in contracts_raw if isinstance(c, dict)]
        if isinstance(contracts_raw, list)
        else []
    )
    valid_contracts = [
        c
        for c in contracts
        if str(c.get("id") or c.get("contract_id") or "").strip()
    ]

    total_contracts = len(valid_contracts)
    if total_contracts == 0:
        return {
            "total_contracts": 0,
            "total_contract_value": 0.0,
            "total_holdback_retained": 0.0,
            "premature_holdback_release_ids": [],
            "unpenalized_sla_breach_ids": [],
            "insufficient_holdback_ids": [],
            "is_procurement_sla_governed": False,
            "procurement_sla_posture": "NO_PROCUREMENT_CONTRACTS",
        }

    total_contract_value = 0.0
    total_holdback_retained = 0.0
    premature_holdback_release_ids: list[str] = []
    unpenalized_sla_breach_ids: list[str] = []
    insufficient_holdback_ids: list[str] = []

    for contract in valid_contracts:
        contract_id = str(contract.get("id") or contract.get("contract_id") or "").strip()
        contract_value = max(0.0, float(contract.get("contract_value") or 0.0))
        holdback_retained = max(0.0, float(contract.get("holdback_retained") or 0.0))
        sla_met = bool(contract.get("sla_met", True))
        penalty_applied = bool(contract.get("penalty_applied", False))
        deliverables_verified = bool(contract.get("deliverables_verified", False))
        holdback_released = bool(contract.get("holdback_released", False))

        total_contract_value += contract_value
        total_holdback_retained += holdback_retained

        if holdback_released is True and not deliverables_verified:
            premature_holdback_release_ids.append(contract_id)
        if not sla_met and not penalty_applied:
            unpenalized_sla_breach_ids.append(contract_id)
        if (
            not holdback_released
            and contract_value > 0.0
            and ((holdback_retained / contract_value) * 100.0 + 1e-6)
            < float(min_holdback_pct)
        ):
            insufficient_holdback_ids.append(contract_id)

    is_procurement_sla_governed = bool(
        total_contracts > 0
        and len(premature_holdback_release_ids) == 0
        and len(unpenalized_sla_breach_ids) == 0
        and len(insufficient_holdback_ids) == 0
    )

    if total_contracts == 0:
        procurement_sla_posture = "NO_PROCUREMENT_CONTRACTS"
    elif premature_holdback_release_ids:
        procurement_sla_posture = "PREMATURE_WARRANTY_HOLDBACK_RELEASE"
    elif unpenalized_sla_breach_ids:
        procurement_sla_posture = "UNPENALIZED_VENDOR_SLA_BREACH"
    elif insufficient_holdback_ids:
        procurement_sla_posture = "INSUFFICIENT_WARRANTY_HOLDBACK_RETENTION"
    else:
        procurement_sla_posture = "GOVERNED_PROCUREMENT_SLA_AND_HOLDBACKS"

    return {
        "total_contracts": total_contracts,
        "total_contract_value": round(total_contract_value, 2),
        "total_holdback_retained": round(total_holdback_retained, 2),
        "premature_holdback_release_ids": premature_holdback_release_ids,
        "unpenalized_sla_breach_ids": unpenalized_sla_breach_ids,
        "insufficient_holdback_ids": insufficient_holdback_ids,
        "is_procurement_sla_governed": is_procurement_sla_governed,
        "procurement_sla_posture": procurement_sla_posture,
    }


def audit_executive_report_procurement_slas(
    report_data: Optional[dict],
) -> dict[str, Any]:
    """Audita el desempeño de contratos y SLAs de proveedores en el reporte ejecutivo según PMI PMBOK §12.3 y §10.2."""
    data = report_data if isinstance(report_data, dict) else {}

    raw_contracts = (
        data.get("vendor_contracts")
        if isinstance(data.get("vendor_contracts"), list)
        else data.get("procurement_kpis")
        if isinstance(data.get("procurement_kpis"), list)
        else []
    )
    contracts = [c for c in raw_contracts if isinstance(c, dict)]

    total_contracts = len(contracts)
    sla_breach_contract_ids: list[str] = []
    ceiling_exceeded_contract_ids: list[str] = []
    unbounded_tm_contract_ids: list[str] = []
    sla_sum = 0.0

    for idx, contract in enumerate(contracts, start=1):
        raw_id = (
            contract.get("id")
            if contract.get("id") is not None
            else contract.get("contract_id")
            if contract.get("contract_id") is not None
            else contract.get("vendor")
        )
        contract_id = (
            str(raw_id).strip()
            if raw_id is not None and str(raw_id).strip()
            else f"CTR-{idx}"
        )

        raw_sla_met = (
            contract.get("sla_met_pct")
            if contract.get("sla_met_pct") is not None
            else contract.get("delivery_score_pct")
        )
        try:
            sla_met_pct = (
                float(raw_sla_met) if raw_sla_met is not None else 100.0
            )
        except (TypeError, ValueError):
            sla_met_pct = 100.0

        raw_sla_target = contract.get("sla_target_pct")
        try:
            sla_target_pct = (
                float(raw_sla_target) if raw_sla_target is not None else 95.0
            )
        except (TypeError, ValueError):
            sla_target_pct = 95.0

        contract_type = (
            str(contract.get("contract_type") or "FFP").strip().upper()
            or "FFP"
        )

        raw_ceiling = (
            contract.get("budget_ceiling")
            if contract.get("budget_ceiling") is not None
            else contract.get("not_to_exceed_limit")
        )
        try:
            budget_ceiling = float(raw_ceiling or 0.0)
        except (TypeError, ValueError):
            budget_ceiling = 0.0

        try:
            invoiced_amount = float(contract.get("invoiced_amount") or 0.0)
        except (TypeError, ValueError):
            invoiced_amount = 0.0

        sla_sum += sla_met_pct

        if sla_met_pct < sla_target_pct:
            sla_breach_contract_ids.append(contract_id)

        if budget_ceiling > 0.0 and invoiced_amount > budget_ceiling:
            ceiling_exceeded_contract_ids.append(contract_id)

        if contract_type == "TM" and budget_ceiling <= 0.0:
            unbounded_tm_contract_ids.append(contract_id)

    average_sla_pct = (
        round(sla_sum / total_contracts, 2) if total_contracts > 0 else 0.0
    )

    recommendations: list[str] = []
    if total_contracts == 0:
        procurement_posture = "NO_PROCUREMENT_CONTRACTS"
        recommendations.append(
            "Incluir inventario de contratos y métricas SLA de proveedores en el reporte ejecutivo para auditar adquisiciones (PMBOK §12.3 / §10.2)."
        )
    elif len(ceiling_exceeded_contract_ids) > 0:
        procurement_posture = "CONTRACT_CEILING_OVERRUN"
        recommendations.append(
            f"Suspender pagos adicionales o tramitar adenda aprobada por el CCB para contratos que exceden el tope presupuestario ({', '.join(ceiling_exceeded_contract_ids)}) conforme a PMBOK §12.3."
        )
    elif len(unbounded_tm_contract_ids) > 0:
        procurement_posture = "UNBOUNDED_TIME_AND_MATERIALS_RISK"
        recommendations.append(
            f"Establecer cláusula de límite máximo (Not-To-Exceed / NTE) en contratos Time & Materials sin tope ({', '.join(unbounded_tm_contract_ids)}) según PMBOK §12.1 / §12.3."
        )
    elif len(sla_breach_contract_ids) > 0:
        procurement_posture = "VENDOR_SLA_BREACH_DETECTED"
        recommendations.append(
            f"Ejecutar revisión de desempeño y plan de acción correctivo con proveedores bajo el SLA objetivo ({', '.join(sla_breach_contract_ids)}) conforme a PMBOK §12.3."
        )
    else:
        procurement_posture = "GOVERNED_PROCUREMENT_PORTFOLIO"
        recommendations.append(
            "Portafolio de adquisiciones gobernado con SLAs cumplidos y límites contractuales controlados (PMBOK §12.3)."
        )

    return {
        "total_contracts": total_contracts,
        "sla_breach_contract_ids": sla_breach_contract_ids,
        "ceiling_exceeded_contract_ids": ceiling_exceeded_contract_ids,
        "unbounded_tm_contract_ids": unbounded_tm_contract_ids,
        "average_sla_pct": average_sla_pct,
        "procurement_posture": procurement_posture,
        "recommendations": recommendations,
    }


def audit_executive_report_stakeholder_communications(
    report_payload: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Audita la transparencia de involucramiento de interesados y entregables de comunicación en informes ejecutivos según PMI PMBOK §10.2 y §13.3."""
    if not isinstance(report_payload, dict) or not report_payload:
        return {
            "total_stakeholders": 0,
            "total_communications": 0,
            "unmitigated_resistant_stakeholder_ids": [],
            "overdue_communication_ids": [],
            "is_transparent": False,
            "communication_posture": "MISSING_STAKEHOLDER_COMMUNICATIONS_DATA",
        }

    raw_stakeholders = (
        report_payload.get("stakeholders")
        or report_payload.get("stakeholder_summary")
        or report_payload.get("interesados")
        or []
    )
    raw_communications = (
        report_payload.get("communications")
        or report_payload.get("communication_log")
        or report_payload.get("comunicaciones")
        or []
    )

    stakeholders = (
        [s for s in raw_stakeholders if isinstance(s, dict)]
        if isinstance(raw_stakeholders, list)
        else []
    )
    communications = (
        [c for c in raw_communications if isinstance(c, dict)]
        if isinstance(raw_communications, list)
        else []
    )

    total_stakeholders = len(stakeholders)
    total_communications = len(communications)

    if total_stakeholders == 0 and total_communications == 0:
        return {
            "total_stakeholders": 0,
            "total_communications": 0,
            "unmitigated_resistant_stakeholder_ids": [],
            "overdue_communication_ids": [],
            "is_transparent": False,
            "communication_posture": "MISSING_STAKEHOLDER_COMMUNICATIONS_DATA",
        }

    unmitigated_resistant_stakeholder_ids: list[str] = []
    resistant_levels = {"resistant", "resistente", "unaware", "desconocedor"}

    for idx, item in enumerate(stakeholders, start=1):
        stk_id = (
            str(
                item.get("id")
                or item.get("stakeholder_id")
                or item.get("name")
                or ""
            ).strip()
            or f"STK-{idx}"
        )
        level = (
            str(
                item.get("engagement_level")
                or item.get("current_engagement")
                or ""
            )
            .strip()
            .lower()
        )
        strategy = str(
            item.get("action_plan") or item.get("engagement_strategy") or ""
        ).strip()
        if level in resistant_levels and not strategy:
            unmitigated_resistant_stakeholder_ids.append(stk_id)

    overdue_communication_ids: list[str] = []
    overdue_statuses = {"overdue", "missed", "vencida", "no_enviada"}

    for idx, item in enumerate(communications, start=1):
        comm_id = (
            str(
                item.get("id")
                or item.get("comm_id")
                or item.get("channel")
                or ""
            ).strip()
            or f"COMM-{idx}"
        )
        status = (
            str(item.get("status") or item.get("delivery_status") or "")
            .strip()
            .lower()
        )
        if status in overdue_statuses:
            overdue_communication_ids.append(comm_id)

    is_transparent = bool(
        (total_stakeholders > 0 or total_communications > 0)
        and len(unmitigated_resistant_stakeholder_ids) == 0
        and len(overdue_communication_ids) == 0
    )

    if len(unmitigated_resistant_stakeholder_ids) > 0:
        communication_posture = "UNMITIGATED_STAKEHOLDER_RESISTANCE"
    elif len(overdue_communication_ids) > 0:
        communication_posture = "OVERDUE_COMMUNICATION_DELIVERABLES"
    else:
        communication_posture = "TRANSPARENT_STAKEHOLDER_ENGAGEMENT"

    return {
        "total_stakeholders": total_stakeholders,
        "total_communications": total_communications,
        "unmitigated_resistant_stakeholder_ids": unmitigated_resistant_stakeholder_ids,
        "overdue_communication_ids": overdue_communication_ids,
        "is_transparent": is_transparent,
        "communication_posture": communication_posture,
    }


def audit_executive_report_risk_burndown(
    report_payload: Optional[dict[str, Any]],
    max_residual_to_initial_ratio_pct: float = 60.0,
) -> dict[str, Any]:
    """Audita la efectividad de mitigación y exposición residual de riesgos en el informe ejecutivo según PMI PMBOK §11.6."""
    if not isinstance(report_payload, dict) or not report_payload:
        return {
            "total_risks": 0,
            "active_risks_count": 0,
            "residual_ratio_pct": 0.0,
            "unowned_active_risk_ids": [],
            "unassessed_residual_risk_ids": [],
            "stagnant_mitigation_risk_ids": [],
            "is_effective": False,
            "risk_burndown_posture": "NO_RISKS_DISCLOSED",
        }

    raid_kpis = report_payload.get("raid_kpis")
    raw_risks = (
        report_payload.get("risks")
        if isinstance(report_payload.get("risks"), list)
        else report_payload.get("risk_register")
        if isinstance(report_payload.get("risk_register"), list)
        else (raid_kpis.get("risks") if isinstance(raid_kpis, dict) else None)
    )
    risks = (
        [r for r in raw_risks if isinstance(r, dict)]
        if isinstance(raw_risks, list)
        else []
    )
    total_risks = len(risks)

    if total_risks == 0:
        return {
            "total_risks": 0,
            "active_risks_count": 0,
            "residual_ratio_pct": 0.0,
            "unowned_active_risk_ids": [],
            "unassessed_residual_risk_ids": [],
            "stagnant_mitigation_risk_ids": [],
            "is_effective": False,
            "risk_burndown_posture": "NO_RISKS_DISCLOSED",
        }

    active_risks_count = 0
    unowned_active_risk_ids: list[str] = []
    unassessed_residual_risk_ids: list[str] = []
    stagnant_mitigation_risk_ids: list[str] = []
    sum_initial = 0.0
    sum_residual = 0.0
    closed_statuses = {"closed", "retired", "cerrado", "retirado"}

    for idx, item in enumerate(risks, start=1):
        risk_id = (
            str(
                item.get("id")
                or item.get("risk_id")
                or item.get("code")
                or ""
            ).strip()
            or f"RISK-{idx}"
        )
        status = str(item.get("status") or "").strip().lower()
        is_active = status not in closed_statuses
        if not is_active:
            continue

        active_risks_count += 1
        owner = str(item.get("owner") or item.get("risk_owner") or "").strip()
        if not owner:
            unowned_active_risk_ids.append(risk_id)

        raw_init = (
            item.get("initial_score")
            if item.get("initial_score") is not None
            else (item.get("inherent_score") or 0.0)
        )
        try:
            init_score = max(0.0, float(raw_init))
        except (TypeError, ValueError):
            init_score = 0.0

        res_raw = item.get("residual_score")
        res_score: Optional[float] = None
        if res_raw is not None and not isinstance(res_raw, bool):
            try:
                res_score = max(0.0, float(res_raw))
            except (TypeError, ValueError):
                res_score = None

        if res_score is None or init_score <= 0.0:
            unassessed_residual_risk_ids.append(risk_id)
        else:
            sum_initial += init_score
            sum_residual += res_score
            if res_score >= init_score:
                stagnant_mitigation_risk_ids.append(risk_id)

    residual_ratio_pct = (
        round((sum_residual / sum_initial) * 100.0, 2)
        if sum_initial > 0.0
        else 0.0
    )

    try:
        max_ratio = float(max_residual_to_initial_ratio_pct)
    except (TypeError, ValueError):
        max_ratio = 60.0

    is_effective = bool(
        total_risks > 0
        and len(unowned_active_risk_ids) == 0
        and len(unassessed_residual_risk_ids) == 0
        and len(stagnant_mitigation_risk_ids) == 0
        and (sum_initial == 0.0 or residual_ratio_pct <= max_ratio)
    )

    if len(unowned_active_risk_ids) > 0 or len(unassessed_residual_risk_ids) > 0:
        risk_burndown_posture = "UNOWNED_OR_UNASSESSED_ACTIVE_RISKS"
    elif len(stagnant_mitigation_risk_ids) > 0 or (
        sum_initial > 0.0 and residual_ratio_pct > max_ratio
    ):
        risk_burndown_posture = "INEFFECTIVE_RISK_MITIGATION_BURNDOWN"
    else:
        risk_burndown_posture = "EFFECTIVE_RESIDUAL_RISK_BURNDOWN"

    return {
        "total_risks": total_risks,
        "active_risks_count": active_risks_count,
        "residual_ratio_pct": residual_ratio_pct,
        "unowned_active_risk_ids": unowned_active_risk_ids,
        "unassessed_residual_risk_ids": unassessed_residual_risk_ids,
        "stagnant_mitigation_risk_ids": stagnant_mitigation_risk_ids,
        "is_effective": is_effective,
        "risk_burndown_posture": risk_burndown_posture,
    }


_CCB_APPROVED_STATUSES = frozenset(
    {"approved", "aprobado", "aprobada", "implemented", "implementado"}
)
_CCB_REJECTED_STATUSES = frozenset(
    {
        "rejected",
        "rechazado",
        "rechazada",
        "deferred",
        "diferido",
        "cancelled",
        "cancelado",
    }
)
_CCB_PENDING_STATUSES = frozenset(
    {
        "pending",
        "pendiente",
        "under_review",
        "en_revision",
        "open",
        "submitted",
        "",
    }
)


def audit_executive_report_change_control_log(
    report_payload: dict[str, Any] | None = None,
    max_pending_days: int = 14,
) -> dict[str, Any]:
    """Audita el registro del Comité de Control de Cambios (CCB) en el informe ejecutivo según PMI PMBOK §4.6."""
    raw_list: Any = None
    if isinstance(report_payload, dict):
        for key in ("change_requests", "ccb_log", "changes"):
            candidate = report_payload.get(key)
            if isinstance(candidate, list):
                raw_list = candidate
                break

    items = [item for item in (raw_list or []) if isinstance(item, dict)]
    total_change_requests = len(items)
    if total_change_requests == 0:
        return {
            "total_change_requests": 0,
            "approved_count": 0,
            "unquantified_approved_cr_ids": [],
            "overdue_pending_cr_ids": [],
            "undocumented_decision_cr_ids": [],
            "traceability_rate_pct": 100.0,
            "is_ccb_log_compliant": True,
            "ccb_log_posture": "NO_CHANGE_REQUESTS_LOGGED",
        }

    try:
        max_days = int(max_pending_days)
    except (TypeError, ValueError):
        max_days = 14

    approved_count = 0
    unquantified_approved_cr_ids: list[str] = []
    overdue_pending_cr_ids: list[str] = []
    undocumented_decision_cr_ids: list[str] = []
    flagged_ids: set[str] = set()

    for idx, item in enumerate(items, start=1):
        cr_id = (
            str(
                item.get("id")
                or item.get("cr_id")
                or item.get("code")
                or f"CR-{idx}"
            ).strip()
            or f"CR-{idx}"
        )
        status = (
            str(
                item.get("status")
                if item.get("status") is not None
                else (
                    item.get("decision")
                    if item.get("decision") is not None
                    else (item.get("state") or "")
                )
            )
            .strip()
            .lower()
        )

        if status in _CCB_APPROVED_STATUSES:
            approved_count += 1
            has_impact = (
                item.get("cost_impact") is not None
                or item.get("schedule_days_impact") is not None
                or item.get("schedule_impact_days") is not None
            )
            has_approver = bool(
                str(
                    item.get("approved_by")
                    or item.get("ccb_reference")
                    or item.get("resolution_id")
                    or ""
                ).strip()
            )
            if not (has_impact and has_approver):
                unquantified_approved_cr_ids.append(cr_id)
                flagged_ids.add(cr_id)
        elif status in _CCB_REJECTED_STATUSES:
            rationale = str(
                item.get("rationale")
                or item.get("decision_rationale")
                or item.get("rejection_reason")
                or ""
            ).strip()
            if len(rationale) < 5:
                undocumented_decision_cr_ids.append(cr_id)
                flagged_ids.add(cr_id)
        elif status in _CCB_PENDING_STATUSES:
            raw_days = (
                item.get("pending_days")
                if item.get("pending_days") is not None
                else (
                    item.get("age_days")
                    if item.get("age_days") is not None
                    else (item.get("days_open") or 0)
                )
            )
            try:
                p_days = max(0.0, float(raw_days))
            except (TypeError, ValueError):
                p_days = 0.0
            if p_days > max_days:
                overdue_pending_cr_ids.append(cr_id)
                flagged_ids.add(cr_id)

    compliant_count = max(0, total_change_requests - len(flagged_ids))
    traceability_rate_pct = round(
        (compliant_count / total_change_requests) * 100.0, 2
    )
    is_ccb_log_compliant = bool(
        len(unquantified_approved_cr_ids) == 0
        and len(undocumented_decision_cr_ids) == 0
        and len(overdue_pending_cr_ids) == 0
    )

    if len(unquantified_approved_cr_ids) > 0:
        ccb_log_posture = "UNQUANTIFIED_APPROVED_BASELINE_CHANGE"
    elif len(overdue_pending_cr_ids) > 0:
        ccb_log_posture = "OVERDUE_CCB_PENDING_DECISIONS"
    elif len(undocumented_decision_cr_ids) > 0:
        ccb_log_posture = "UNDOCUMENTED_CCB_REJECTION_RATIONALE"
    else:
        ccb_log_posture = "TRACEABLE_CCB_DECISION_LOG"

    return {
        "total_change_requests": total_change_requests,
        "approved_count": approved_count,
        "unquantified_approved_cr_ids": unquantified_approved_cr_ids,
        "overdue_pending_cr_ids": overdue_pending_cr_ids,
        "undocumented_decision_cr_ids": undocumented_decision_cr_ids,
        "traceability_rate_pct": traceability_rate_pct,
        "is_ccb_log_compliant": is_ccb_log_compliant,
        "ccb_log_posture": ccb_log_posture,
    }


def audit_executive_report_resource_spof_and_utilization(
    report_payload: dict[str, Any] | None = None,
    max_utilization_pct: float = 100.0,
) -> dict[str, Any]:
    """Audita utilización de recursos y puntos únicos de falla (SPOF) de habilidades críticas según PMI PMBOK §9.3 & §9.6."""
    raw_list: Any = None
    if isinstance(report_payload, dict):
        for key in ("resource_allocations", "resources", "team_allocations"):
            candidate = report_payload.get(key)
            if isinstance(candidate, list):
                raw_list = candidate
                break

    items = [item for item in (raw_list or []) if isinstance(item, dict)]
    total_allocations = len(items)
    if total_allocations == 0:
        return {
            "total_allocations": 0,
            "average_utilization_pct": 0.0,
            "unassigned_role_ids": [],
            "overallocated_resource_ids": [],
            "unbacked_spof_resource_ids": [],
            "is_resource_plan_healthy": True,
            "resource_posture": "NO_RESOURCES_REPORTED",
        }

    try:
        max_util = float(max_utilization_pct)
    except (TypeError, ValueError):
        max_util = 100.0

    utilizations: list[float] = []
    unassigned_role_ids: list[str] = []
    overallocated_resource_ids: list[str] = []
    unbacked_spof_resource_ids: list[str] = []

    for idx, item in enumerate(items, start=1):
        res_id = (
            str(
                item.get("id")
                or item.get("resource_id")
                or item.get("role_id")
                or f"RES-{idx}"
            ).strip()
            or f"RES-{idx}"
        )
        assignee = str(
            item.get("resource_name")
            or item.get("assignee")
            or item.get("member")
            or ""
        ).strip()
        try:
            utilization_pct = float(
                item.get("utilization_pct")
                or item.get("allocation_pct")
                or 0.0
            )
        except (TypeError, ValueError):
            utilization_pct = 0.0
        utilizations.append(utilization_pct)

        is_critical_role = bool(
            item.get("is_critical_role")
            or item.get("critical_skill")
            or item.get("key_person")
        )
        backup = str(
            item.get("backup_resource")
            or item.get("cross_trained_backup")
            or item.get("deputy")
            or ""
        ).strip()

        if not assignee:
            unassigned_role_ids.append(res_id)
        if utilization_pct > max_util + 1e-9:
            overallocated_resource_ids.append(res_id)
        if is_critical_role and not backup:
            unbacked_spof_resource_ids.append(res_id)

    average_utilization_pct = round(sum(utilizations) / len(utilizations), 2)
    is_resource_plan_healthy = bool(
        len(unassigned_role_ids) == 0
        and len(overallocated_resource_ids) == 0
        and len(unbacked_spof_resource_ids) == 0
    )

    if len(unassigned_role_ids) > 0:
        resource_posture = "UNASSIGNED_CRITICAL_ROLE"
    elif len(unbacked_spof_resource_ids) > 0:
        resource_posture = "UNBACKED_KEY_PERSON_SPOF"
    elif len(overallocated_resource_ids) > 0:
        resource_posture = "RESOURCE_OVERALLOCATION_ALERT"
    else:
        resource_posture = "BALANCED_RESILIENT_RESOURCE_PLAN"

    return {
        "total_allocations": total_allocations,
        "average_utilization_pct": average_utilization_pct,
        "unassigned_role_ids": unassigned_role_ids,
        "overallocated_resource_ids": overallocated_resource_ids,
        "unbacked_spof_resource_ids": unbacked_spof_resource_ids,
        "is_resource_plan_healthy": is_resource_plan_healthy,
        "resource_posture": resource_posture,
    }


_CLOSURE_ACCEPTED_DELIVERABLE_STATUSES = {
    "accepted",
    "aceptado",
    "aceptada",
    "signed_off",
    "approved",
    "aprobado",
    "completed",
    "completado",
}
_CLOSURE_SETTLED_CONTRACT_STATUSES = {
    "closed",
    "cerrado",
    "settled",
    "liquidado",
    "completed",
    "completado",
}


def audit_executive_report_closure_readiness(
    report_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita alistamiento de cierre administrativo y contractual en el informe ejecutivo según PMI PMBOK §4.7 y §12.3."""
    if not isinstance(report_payload, dict) or not report_payload:
        return {
            "total_deliverables": 0,
            "total_contracts": 0,
            "unaccepted_deliverable_ids": [],
            "unsettled_contract_ids": [],
            "has_administrative_signoff": True,
            "is_ready_for_closure": True,
            "closure_posture": "NO_CLOSURE_DATA_REPORTED",
        }

    raw_deliverables = (
        report_payload.get("deliverables")
        if isinstance(report_payload.get("deliverables"), list)
        else (
            report_payload.get("final_deliverables")
            if isinstance(report_payload.get("final_deliverables"), list)
            else []
        )
    )
    deliverables = [
        item for item in (raw_deliverables or []) if isinstance(item, dict)
    ]

    raw_contracts = (
        report_payload.get("contracts")
        if isinstance(report_payload.get("contracts"), list)
        else (
            report_payload.get("procurements")
            if isinstance(report_payload.get("procurements"), list)
            else []
        )
    )
    contracts = [
        item for item in (raw_contracts or []) if isinstance(item, dict)
    ]

    raw_closure_summary = report_payload.get("closure_summary")
    closure_src = (
        raw_closure_summary if isinstance(raw_closure_summary, dict) else {}
    )

    if (
        len(deliverables) == 0
        and len(contracts) == 0
        and "lessons_learned_archived" not in report_payload
        and "sponsor_signoff" not in report_payload
        and "closure_summary" not in report_payload
    ):
        return {
            "total_deliverables": 0,
            "total_contracts": 0,
            "unaccepted_deliverable_ids": [],
            "unsettled_contract_ids": [],
            "has_administrative_signoff": True,
            "is_ready_for_closure": True,
            "closure_posture": "NO_CLOSURE_DATA_REPORTED",
        }

    lessons_learned_archived = bool(
        closure_src.get(
            "lessons_learned_archived",
            report_payload.get("lessons_learned_archived", True),
        )
    )
    sponsor_signoff = bool(
        closure_src.get(
            "sponsor_signoff",
            report_payload.get("sponsor_signoff", True),
        )
    )

    unaccepted_deliverable_ids: list[str] = []
    for idx, item in enumerate(deliverables, start=1):
        deliv_id = (
            str(
                item.get("id")
                or item.get("deliverable_id")
                or item.get("code")
                or f"DEL-{idx}"
            ).strip()
            or f"DEL-{idx}"
        )
        acc_status = (
            str(item.get("acceptance_status") or item.get("status") or "")
            .strip()
            .lower()
        )
        if acc_status not in _CLOSURE_ACCEPTED_DELIVERABLE_STATUSES:
            unaccepted_deliverable_ids.append(deliv_id)

    unsettled_contract_ids: list[str] = []
    for idx, item in enumerate(contracts, start=1):
        cnt_id = (
            str(
                item.get("id")
                or item.get("contract_id")
                or item.get("code")
                or f"CNT-{idx}"
            ).strip()
            or f"CNT-{idx}"
        )
        cnt_status = (
            str(item.get("status") or item.get("closeout_status") or "")
            .strip()
            .lower()
        )
        has_open_claims = bool(
            item.get("has_open_claims") or item.get("open_disputes")
        )
        if has_open_claims or (
            cnt_status not in _CLOSURE_SETTLED_CONTRACT_STATUSES
        ):
            unsettled_contract_ids.append(cnt_id)

    has_administrative_signoff = bool(
        lessons_learned_archived and sponsor_signoff
    )
    is_ready_for_closure = bool(
        len(unaccepted_deliverable_ids) == 0
        and len(unsettled_contract_ids) == 0
        and has_administrative_signoff
    )

    if len(unaccepted_deliverable_ids) > 0:
        closure_posture = "UNACCEPTED_FINAL_DELIVERABLES"
    elif len(unsettled_contract_ids) > 0:
        closure_posture = "OPEN_PROCUREMENT_CLAIMS_OR_CONTRACTS"
    elif not has_administrative_signoff:
        closure_posture = "PENDING_ADMINISTRATIVE_SIGNOFF"
    else:
        closure_posture = "READY_FOR_ADMINISTRATIVE_CLOSURE"

    return {
        "total_deliverables": len(deliverables),
        "total_contracts": len(contracts),
        "unaccepted_deliverable_ids": unaccepted_deliverable_ids,
        "unsettled_contract_ids": unsettled_contract_ids,
        "has_administrative_signoff": has_administrative_signoff,
        "is_ready_for_closure": is_ready_for_closure,
        "closure_posture": closure_posture,
    }


def audit_executive_report_distribution_cadence(
    report_payload: dict[str, Any] | None = None,
    max_days_since_last_dispatch: int = 14,
    min_ack_rate_pct: float = 80.0,
) -> dict[str, Any]:
    """Audita cadencia de distribución y acuse de recibo del reporte ejecutivo (PMBOK §10.3 / §4.5).

    Reglas:
    - Extrae `distribution = (report_payload or {}).get("distribution_governance") or {}`.
    - Filtra destinatarios válidos (`id` o `recipient_id` no vacío).
    - `days_since_last_dispatch`: entero extraído de `distribution.get("days_since_last_dispatch")` (por defecto `-1`).
    - Por cada destinatario:
      - `is_mandatory = bool(r.get("mandatory", True))`
      - `is_dispatched = bool(r.get("dispatched", False))`
      - `is_acknowledged = bool(r.get("acknowledged", False))`
      - Si `is_mandatory and not is_dispatched`: agrega a `undispatched_mandatory_recipient_ids`.
      - Si `is_dispatched`: incrementa `dispatched_count`; si `is_acknowledged` incrementa `acknowledged_count`,
        de lo contrario agrega a `unacknowledged_recipient_ids`.
    - `ack_rate_pct = round((acknowledged_count / dispatched_count) * 100.0, 2) if dispatched_count > 0 else 0.0`
    - `is_cadence_overdue = bool(days_since_last_dispatch < 0 or days_since_last_dispatch > max(1, int(max_days_since_last_dispatch)))`
    - `is_distribution_governed = bool(len(recipients) > 0 and not is_cadence_overdue and len(undispatched_mandatory_recipient_ids) == 0 and ack_rate_pct >= float(min_ack_rate_pct))`
    """
    payload = report_payload if isinstance(report_payload, dict) else {}
    raw_distribution = payload.get("distribution_governance")
    distribution = raw_distribution if isinstance(raw_distribution, dict) else {}

    raw_recipients = distribution.get("recipients") or []
    recipients: list[dict[str, Any]] = []
    if isinstance(raw_recipients, list):
        for r in raw_recipients:
            if not isinstance(r, dict):
                continue
            r_id = str(r.get("id") or r.get("recipient_id") or "").strip()
            if r_id:
                recipients.append(r)

    raw_days = distribution.get("days_since_last_dispatch")
    try:
        days_since_last_dispatch = int(raw_days) if raw_days is not None else -1
    except (TypeError, ValueError):
        days_since_last_dispatch = -1

    undispatched_mandatory_recipient_ids: list[str] = []
    unacknowledged_recipient_ids: list[str] = []
    dispatched_count = 0
    acknowledged_count = 0

    for r in recipients:
        recipient_id = str(r.get("id") or r.get("recipient_id") or "").strip()
        is_mandatory = bool(r.get("mandatory", True))
        is_dispatched = bool(r.get("dispatched", False))
        is_acknowledged = bool(r.get("acknowledged", False))

        if is_mandatory and not is_dispatched:
            undispatched_mandatory_recipient_ids.append(recipient_id)

        if is_dispatched:
            dispatched_count += 1
            if is_acknowledged:
                acknowledged_count += 1
            else:
                unacknowledged_recipient_ids.append(recipient_id)

    ack_rate_pct = (
        round((acknowledged_count / dispatched_count) * 100.0, 2)
        if dispatched_count > 0
        else 0.0
    )
    is_cadence_overdue = bool(
        days_since_last_dispatch < 0
        or days_since_last_dispatch > max(1, int(max_days_since_last_dispatch))
    )
    is_distribution_governed = bool(
        len(recipients) > 0
        and not is_cadence_overdue
        and len(undispatched_mandatory_recipient_ids) == 0
        and ack_rate_pct >= float(min_ack_rate_pct)
    )

    if len(recipients) == 0:
        distribution_posture = "NO_DISTRIBUTION_RECIPIENTS"
    elif len(undispatched_mandatory_recipient_ids) > 0:
        distribution_posture = "UNDISPATCHED_MANDATORY_STAKEHOLDERS"
    elif is_cadence_overdue:
        distribution_posture = "REPORT_DISPATCH_CADENCE_OVERDUE"
    elif ack_rate_pct < float(min_ack_rate_pct):
        distribution_posture = "LOW_STAKEHOLDER_ACKNOWLEDGMENT_RATE"
    else:
        distribution_posture = "GOVERNED_EXECUTIVE_DISTRIBUTION"

    return {
        "total_recipients": len(recipients),
        "dispatched_count": dispatched_count,
        "acknowledged_count": acknowledged_count,
        "ack_rate_pct": ack_rate_pct,
        "undispatched_mandatory_recipient_ids": undispatched_mandatory_recipient_ids,
        "unacknowledged_recipient_ids": unacknowledged_recipient_ids,
        "is_cadence_overdue": is_cadence_overdue,
        "is_distribution_governed": is_distribution_governed,
        "distribution_posture": distribution_posture,
    }


def audit_executive_report_risk_contingency_coverage(
    report_payload: dict[str, Any] | None = None,
    min_coverage_ratio: float = 1.0,
) -> dict[str, Any]:
    """Audita la suficiencia de reserva de contingencia frente a la exposición EMV de riesgos activos en el reporte ejecutivo según PMI PMBOK §11.6 y §11.7."""
    payload = report_payload if isinstance(report_payload, dict) else {}
    raw_raid = payload.get("raid_kpis")
    raid = raw_raid if isinstance(raw_raid, dict) else {}

    remaining_reserve = max(0.0, float(raid.get("remaining_contingency_reserve") or 0.0))
    risks = raid.get("risks") if isinstance(raid.get("risks"), list) else []

    active_threats_count = 0
    total_active_emv = 0.0
    unplanned_critical_threat_ids: list[str] = []

    for r in risks:
        if not isinstance(r, dict):
            continue
        risk_id = str(r.get("id") or r.get("risk_id") or "").strip()
        if not risk_id:
            continue
        status = str(r.get("status") or "OPEN").strip().upper()
        if status not in {"OPEN", "ACTIVE", "MITIGATING"}:
            continue

        active_threats_count += 1
        prob = max(0.0, min(1.0, float(r.get("probability") or 0.0)))
        impact = max(0.0, float(r.get("monetary_impact") or 0.0))
        emv = prob * impact
        total_active_emv += emv

        severity = str(r.get("severity") or "").strip().upper()
        response_plan = str(r.get("response_plan") or "").strip()
        if (emv >= 10000.0 or severity == "CRITICAL") and not response_plan:
            unplanned_critical_threat_ids.append(risk_id)

    coverage_ratio = (
        round(remaining_reserve / total_active_emv, 4)
        if total_active_emv > 1e-6
        else (1.0 if remaining_reserve >= 0.0 else 0.0)
    )
    reserve_shortfall = round(max(0.0, total_active_emv - remaining_reserve), 2)
    is_contingency_adequate = bool(
        active_threats_count > 0
        and len(unplanned_critical_threat_ids) == 0
        and coverage_ratio + 1e-6 >= float(min_coverage_ratio)
    )

    if active_threats_count == 0:
        contingency_posture = "NO_ACTIVE_THREATS_REPORTED"
    elif len(unplanned_critical_threat_ids) > 0:
        contingency_posture = "UNPLANNED_CRITICAL_THREAT_EXPOSURE"
    elif coverage_ratio + 1e-6 < float(min_coverage_ratio):
        contingency_posture = "CONTINGENCY_RESERVE_UNDERFUNDED"
    else:
        contingency_posture = "ADEQUATE_RISK_CONTINGENCY_COVERAGE"

    return {
        "active_threats_count": active_threats_count,
        "total_active_emv": round(total_active_emv, 2),
        "remaining_contingency_reserve": round(remaining_reserve, 2),
        "reserve_shortfall": reserve_shortfall,
        "coverage_ratio": coverage_ratio,
        "unplanned_critical_threat_ids": unplanned_critical_threat_ids,
        "is_contingency_adequate": is_contingency_adequate,
        "contingency_posture": contingency_posture,
    }


def audit_executive_report_scope_creep_governance(
    report_payload: dict[str, Any] | None = None,
    max_unbaselined_scope_pct: float = 5.0,
) -> dict[str, Any]:
    """Audita corrupción de alcance (Scope Creep) y paquetes no autorizados (Gold Plating) en el reporte ejecutivo según PMI PMBOK §5.6 y §4.6."""
    payload = report_payload if isinstance(report_payload, dict) else {}
    raw_scope = payload.get("scope_governance")
    scope_gov = raw_scope if isinstance(raw_scope, dict) else {}

    packages = (
        scope_gov.get("work_packages")
        if isinstance(scope_gov.get("work_packages"), list)
        else []
    )

    total_work_packages = 0
    total_effort_hours = 0.0
    unapproved_effort_hours = 0.0
    unapproved_scope_creep_ids: list[str] = []
    gold_plating_package_ids: list[str] = []

    for p in packages:
        if not isinstance(p, dict):
            continue
        wp_id = str(p.get("id") or p.get("wp_id") or "").strip()
        if not wp_id:
            continue

        total_work_packages += 1
        effort = max(0.0, float(p.get("effort_hours") or 0.0))
        total_effort_hours += effort

        added_post = bool(p.get("added_post_baseline", False))
        approved_cr = str(p.get("approved_cr_id") or "").strip()
        gold_plating = bool(p.get("is_gold_plating", False))

        if gold_plating:
            gold_plating_package_ids.append(wp_id)
        if added_post and not approved_cr:
            unapproved_scope_creep_ids.append(wp_id)
            unapproved_effort_hours += effort

    scope_creep_effort_pct = (
        round((unapproved_effort_hours / total_effort_hours) * 100.0, 2)
        if total_effort_hours > 1e-6
        else 0.0
    )
    is_scope_baseline_protected = bool(
        total_work_packages > 0
        and len(unapproved_scope_creep_ids) == 0
        and len(gold_plating_package_ids) == 0
        and scope_creep_effort_pct <= float(max_unbaselined_scope_pct)
    )

    if total_work_packages == 0:
        scope_creep_posture = "NO_SCOPE_PACKAGES_REPORTED"
    elif len(unapproved_scope_creep_ids) > 0:
        scope_creep_posture = "UNAPPROVED_SCOPE_CREEP_DETECTED"
    elif len(gold_plating_package_ids) > 0:
        scope_creep_posture = "UNAUTHORIZED_GOLD_PLATING_DETECTED"
    else:
        scope_creep_posture = "PROTECTED_SCOPE_BASELINE"

    return {
        "total_work_packages": total_work_packages,
        "total_effort_hours": round(total_effort_hours, 2),
        "unapproved_effort_hours": round(unapproved_effort_hours, 2),
        "scope_creep_effort_pct": scope_creep_effort_pct,
        "unapproved_scope_creep_ids": unapproved_scope_creep_ids,
        "gold_plating_package_ids": gold_plating_package_ids,
        "is_scope_baseline_protected": is_scope_baseline_protected,
        "scope_creep_posture": scope_creep_posture,
    }


ProjectExportService.audit_executive_report_risk_burndown = staticmethod(
    audit_executive_report_risk_burndown
)
ProjectExportService.audit_executive_report_change_control_log = staticmethod(
    audit_executive_report_change_control_log
)
ProjectExportService.audit_executive_report_resource_spof_and_utilization = staticmethod(
    audit_executive_report_resource_spof_and_utilization
)
ProjectExportService.audit_executive_report_closure_readiness = staticmethod(
    audit_executive_report_closure_readiness
)
ProjectExportService.audit_executive_report_distribution_cadence = staticmethod(
    audit_executive_report_distribution_cadence
)
ProjectExportService.audit_executive_report_risk_contingency_coverage = staticmethod(
    audit_executive_report_risk_contingency_coverage
)
ProjectExportService.audit_executive_report_scope_creep_governance = staticmethod(
    audit_executive_report_scope_creep_governance
)


def audit_executive_report_stakeholder_engagement_drift(
    stakeholder_assessments: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evalúa deriva y resistencia en la Matriz de Evaluación del Involucramiento de los Interesados según PMI PMBOK §13.1.3.2 & §13.3.2."""
    level_ranks = {
        "unaware": 1,
        "resistant": 2,
        "neutral": 3,
        "supportive": 4,
        "leading": 5,
    }
    high_influence_levels = {"high", "critical"}

    evaluated_stakeholder_count = 0
    engagement_gap_ids: list[str] = []
    regressing_stakeholder_ids: list[str] = []
    high_influence_resistant_ids: list[str] = []
    unmitigated_high_influence_gap_ids: list[str] = []
    invalid_assessment_ids: list[str] = []

    for item in stakeholder_assessments or []:
        if not isinstance(item, Mapping):
            continue
        stakeholder_id = str(item.get("stakeholder_id") or "").strip()
        if not stakeholder_id:
            continue

        evaluated_stakeholder_count += 1
        influence_level = (
            str(item.get("influence_level") or "medium").strip().lower()
        )
        previous_engagement = (
            str(item.get("previous_engagement") or "").strip().lower()
        )
        current_engagement = (
            str(item.get("current_engagement") or "").strip().lower()
        )
        desired_engagement = (
            str(item.get("desired_engagement") or "").strip().lower()
        )
        action_plan_defined = bool(item.get("action_plan_defined", False))

        if (
            current_engagement not in level_ranks
            or desired_engagement not in level_ranks
            or (previous_engagement and previous_engagement not in level_ranks)
        ):
            invalid_assessment_ids.append(stakeholder_id)
            continue

        current_rank = level_ranks[current_engagement]
        desired_rank = level_ranks[desired_engagement]

        if current_rank < desired_rank:
            engagement_gap_ids.append(stakeholder_id)
            if (
                influence_level in high_influence_levels
                and not action_plan_defined
            ):
                unmitigated_high_influence_gap_ids.append(stakeholder_id)

        if previous_engagement and current_rank < level_ranks[previous_engagement]:
            regressing_stakeholder_ids.append(stakeholder_id)

        if (
            current_engagement == "resistant"
            and influence_level in high_influence_levels
        ):
            high_influence_resistant_ids.append(stakeholder_id)

    is_engagement_healthy = bool(
        evaluated_stakeholder_count > 0
        and len(invalid_assessment_ids) == 0
        and len(unmitigated_high_influence_gap_ids) == 0
        and len(high_influence_resistant_ids) == 0
    )

    return {
        "evaluated_stakeholder_count": evaluated_stakeholder_count,
        "engagement_gap_ids": engagement_gap_ids,
        "regressing_stakeholder_ids": regressing_stakeholder_ids,
        "high_influence_resistant_ids": high_influence_resistant_ids,
        "unmitigated_high_influence_gap_ids": unmitigated_high_influence_gap_ids,
        "invalid_assessment_ids": invalid_assessment_ids,
        "is_engagement_healthy": is_engagement_healthy,
    }


ProjectExportService.audit_executive_report_stakeholder_engagement_drift = staticmethod(
    audit_executive_report_stakeholder_engagement_drift
)


def audit_executive_report_contract_type_risk_allocation(
    contracts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita la coherencia entre el tipo de contrato de adquisición y la madurez del alcance según PMI PMBOK §12.1.1.6 & §12.3."""
    valid_contract_types = {"ffp", "fp_epa", "fpif", "cpff", "cpif", "tm"}
    fixed_price_types = {"ffp", "fp_epa", "fpif"}
    reimbursable_or_tm_types = {"cpff", "cpif", "tm"}
    valid_maturities = {"well_defined", "evolving", "uncertain"}

    evaluated_contract_count = 0
    missing_sow_contract_ids: list[str] = []
    mismatched_fixed_price_uncertainty_ids: list[str] = []
    uncapped_time_and_materials_ids: list[str] = []
    missing_buyer_audit_clause_ids: list[str] = []
    invalid_contract_ids: list[str] = []

    for item in contracts or []:
        if not isinstance(item, Mapping):
            continue
        contract_id = str(item.get("contract_id") or "").strip()
        if not contract_id:
            continue

        evaluated_contract_count += 1
        contract_type = str(item.get("contract_type") or "").strip().lower()
        scope_definition_maturity = (
            str(item.get("scope_definition_maturity") or "").strip().lower()
        )

        if (
            contract_type not in valid_contract_types
            or scope_definition_maturity not in valid_maturities
        ):
            invalid_contract_ids.append(contract_id)
            continue

        has_statement_of_work = bool(item.get("has_statement_of_work", False))
        has_ceiling_price = bool(item.get("has_ceiling_price", False))
        buyer_audit_rights_clause = bool(
            item.get("buyer_audit_rights_clause", False)
        )

        if not has_statement_of_work:
            missing_sow_contract_ids.append(contract_id)

        if (
            contract_type in fixed_price_types
            and scope_definition_maturity == "uncertain"
        ):
            mismatched_fixed_price_uncertainty_ids.append(contract_id)

        if contract_type == "tm" and not has_ceiling_price:
            uncapped_time_and_materials_ids.append(contract_id)

        if (
            contract_type in reimbursable_or_tm_types
            and not buyer_audit_rights_clause
        ):
            missing_buyer_audit_clause_ids.append(contract_id)

    is_risk_aligned = bool(
        evaluated_contract_count > 0
        and len(missing_sow_contract_ids) == 0
        and len(mismatched_fixed_price_uncertainty_ids) == 0
        and len(uncapped_time_and_materials_ids) == 0
        and len(missing_buyer_audit_clause_ids) == 0
        and len(invalid_contract_ids) == 0
    )

    return {
        "evaluated_contract_count": evaluated_contract_count,
        "missing_sow_contract_ids": missing_sow_contract_ids,
        "mismatched_fixed_price_uncertainty_ids": mismatched_fixed_price_uncertainty_ids,
        "uncapped_time_and_materials_ids": uncapped_time_and_materials_ids,
        "missing_buyer_audit_clause_ids": missing_buyer_audit_clause_ids,
        "invalid_contract_ids": invalid_contract_ids,
        "is_risk_aligned": is_risk_aligned,
    }


ProjectExportService.audit_executive_report_contract_type_risk_allocation = staticmethod(
    audit_executive_report_contract_type_risk_allocation
)


__all__ = [
    "audit_csv_export_integrity",
    "evaluate_executive_report_completeness",
    "get_project_executive_report_data",
    "generate_project_summary_pdf",
    "generate_project_tasks_csv",
    "generate_project_expenses_csv",
    "summarize_executive_report_risk_posture",
    "audit_expenses_csv_financial_totals",
    "audit_tasks_csv_schedule_completeness",
    "audit_executive_report_milestone_coverage",
    "audit_executive_report_milestone_deliverables",
    "audit_risks_csv_register_completeness",
    "audit_stakeholders_csv_engagement_gaps",
    "audit_expenses_vendor_concentration",
    "audit_executive_report_change_governance",
    "audit_executive_report_benefits_realization",
    "audit_executive_report_quality_disclosure",
    "audit_executive_report_resource_workload",
    "audit_executive_report_procurement_sla_and_holdbacks",
    "audit_executive_report_procurement_slas",
    "audit_executive_report_stakeholder_communications",
    "audit_executive_report_risk_burndown",
    "audit_executive_report_change_control_log",
    "audit_executive_report_resource_spof_and_utilization",
    "audit_executive_report_closure_readiness",
    "audit_executive_report_distribution_cadence",
    "audit_executive_report_risk_contingency_coverage",
    "audit_executive_report_scope_creep_governance",
    "audit_executive_report_stakeholder_engagement_drift",
    "audit_executive_report_contract_type_risk_allocation",
    "audit_executive_report_lessons_learned_institutionalization",
    "audit_executive_report_risk_trigger_activation_governance",
    "audit_executive_report_procurement_claims_settlement",
    "audit_executive_report_stakeholder_feedback_sla",
    "audit_executive_report_benefits_handover_kpis",
    "audit_executive_report_resource_spof_and_overallocation",
    "audit_executive_report_change_readiness_and_adoption",
    "audit_executive_report_strategic_alignment_and_esg",
    "audit_executive_report_contract_closeout_and_claims",
    "audit_executive_report_rag_status_and_narrative_consistency",
    "audit_executive_report_reserve_drawdown_burn_rate",
    "audit_executive_report_post_implementation_handover_sla",
    "audit_executive_report_team_burnout_and_turnover_risk",
    "audit_executive_report_monte_carlo_p50_p80_confidence",
    "audit_executive_report_vendor_sla_and_liquidated_damages",
    "audit_executive_report_stakeholder_escalation_and_briefing_cadence",
    "audit_executive_report_esg_sustainability_and_regulatory_compliance",
    "audit_executive_report_risk_burndown_and_residual_exposure",
    "audit_executive_report_critical_path_float_and_convergence",
    "audit_executive_report_contract_claims_and_change_orders",
    "audit_executive_report_cybersecurity_vulnerability_and_patch_sla",
    "audit_executive_report_capex_opex_capitalization_compliance",
    "audit_executive_report_key_personnel_bus_factor_and_succession",
    "audit_executive_report_vendor_sla_and_service_credit_recovery",
    "audit_executive_report_supply_chain_lead_time_and_single_source",
    "audit_executive_report_stakeholder_sentiment_and_nps_drift",
    "audit_executive_report_regulatory_and_data_privacy_compliance",
    "audit_executive_report_finops_cloud_cost_and_idle_capacity",
    "audit_executive_report_sbom_cve_and_oss_license_compliance",
    "audit_executive_report_disaster_recovery_rto_rpo_readiness",
    "audit_executive_report_software_license_true_up_and_shelfware",
    "audit_executive_report_pentest_remediation_sla_and_zero_trust",
    "audit_executive_report_esg_carbon_footprint_and_green_cloud_pue",
    "ProjectExportService",
]



def audit_executive_report_lessons_learned_institutionalization(
    report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """PMBOK §4.4 / §10.2 — accionabilidad de lecciones aprendidas e institucionalización OPA del informe ejecutivo.

    - Secuencia desde ``report['lessons_learned']`` (fallback
      ``report['governance']['lessons_learned']``); strings/bytes/mappings se
      descartan como secuencia.
    - Sin causa raíz documentada -> ``missing_root_cause_lesson_ids``.
    - Sin acción preventiva -> ``missing_action_plan_lesson_ids``.
    - Estado institucionalizado/archivado/cerrado sin referencia OPA ->
      ``unlinked_opa_lesson_ids``.
    - Institucionalizada: causa raíz + acción preventiva + referencia OPA.
    """
    missing_root_cause_lesson_ids: list[str] = []
    missing_action_plan_lesson_ids: list[str] = []
    unlinked_opa_lesson_ids: list[str] = []

    lessons: Any
    if isinstance(report, Mapping):
        raw_lessons = report.get("lessons_learned")
        if isinstance(raw_lessons, (list, tuple)):
            lessons = raw_lessons
        elif isinstance(report.get("governance"), Mapping):
            governance_lessons = report["governance"].get("lessons_learned")
            lessons = governance_lessons if isinstance(governance_lessons, (list, tuple)) else []
        else:
            lessons = []
    else:
        lessons = []

    total_lessons = 0
    institutionalized_count = 0

    for item in lessons:
        if not isinstance(item, Mapping):
            continue
        lesson_id = str(item.get("lesson_id") or "").strip()
        if not lesson_id:
            continue
        total_lessons += 1

        root_cause_documented = bool(item.get("root_cause_documented", False))
        preventive_action = str(item.get("preventive_action") or "").strip()
        opa_repository_ref = str(item.get("opa_repository_ref") or "").strip()
        status = str(item.get("status") or "").strip().lower()

        if not root_cause_documented:
            missing_root_cause_lesson_ids.append(lesson_id)

        if not preventive_action:
            missing_action_plan_lesson_ids.append(lesson_id)

        if status in {"institutionalized", "archived_to_opa", "closed"} and not opa_repository_ref:
            unlinked_opa_lesson_ids.append(lesson_id)

        if root_cause_documented and preventive_action and opa_repository_ref:
            institutionalized_count += 1

    institutionalization_rate_pct = (
        round((institutionalized_count / total_lessons) * 100.0, 2)
        if total_lessons > 0
        else 0.0
    )
    is_opa_ready = bool(
        total_lessons > 0
        and not missing_root_cause_lesson_ids
        and not missing_action_plan_lesson_ids
        and not unlinked_opa_lesson_ids
    )

    return {
        "total_lessons": total_lessons,
        "missing_root_cause_lesson_ids": missing_root_cause_lesson_ids,
        "missing_action_plan_lesson_ids": missing_action_plan_lesson_ids,
        "unlinked_opa_lesson_ids": unlinked_opa_lesson_ids,
        "institutionalization_rate_pct": institutionalization_rate_pct,
        "is_opa_ready": is_opa_ready,
    }


ProjectExportService.audit_executive_report_lessons_learned_institutionalization = staticmethod(
    audit_executive_report_lessons_learned_institutionalization
)


def audit_executive_report_risk_trigger_activation_governance(
    report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Audita la activación de disparadores de riesgo (risk triggers), ejecución de planes de contingencia y autorización de uso de reservas en el reporte ejecutivo según PMI PMBOK §11.7 y §10.2."""
    triggers: Sequence[Any] = []
    if isinstance(report, Mapping):
        raw_root = report.get("risk_triggers")
        if isinstance(raw_root, Sequence) and not isinstance(
            raw_root, (str, bytes, Mapping)
        ):
            triggers = raw_root
        elif isinstance(report.get("governance"), Mapping):
            raw_gov = report["governance"].get("risk_triggers")
            if isinstance(raw_gov, Sequence) and not isinstance(
                raw_gov, (str, bytes, Mapping)
            ):
                triggers = raw_gov

    total_monitored_risks = 0
    activated_triggers_count = 0
    missing_trigger_condition_risk_ids: list[str] = []
    unexecuted_contingency_risk_ids: list[str] = []
    unauthorized_drawdown_risk_ids: list[str] = []

    for item in triggers:
        if not isinstance(item, Mapping):
            continue
        risk_id = str(item.get("risk_id") or "").strip()
        if not risk_id:
            continue

        total_monitored_risks += 1
        trigger_condition = str(item.get("trigger_condition") or "").strip()
        trigger_activated = bool(item.get("trigger_activated", False))
        contingency_plan_executed = bool(
            item.get("contingency_plan_executed", False)
        )
        reserve_drawdown_authorized = bool(
            item.get("reserve_drawdown_authorized", False)
        )
        try:
            reserve_drawn_amount = max(
                0.0, float(item.get("reserve_drawn_amount", 0.0) or 0.0)
            )
        except (TypeError, ValueError):
            reserve_drawn_amount = 0.0

        if not trigger_condition:
            missing_trigger_condition_risk_ids.append(risk_id)

        if trigger_activated:
            activated_triggers_count += 1
            if not contingency_plan_executed:
                unexecuted_contingency_risk_ids.append(risk_id)

        if reserve_drawn_amount > 0.0 and (
            not trigger_activated or not reserve_drawdown_authorized
        ):
            unauthorized_drawdown_risk_ids.append(risk_id)

    is_trigger_governance_compliant = bool(
        total_monitored_risks > 0
        and not missing_trigger_condition_risk_ids
        and not unexecuted_contingency_risk_ids
        and not unauthorized_drawdown_risk_ids
    )

    return {
        "total_monitored_risks": total_monitored_risks,
        "activated_triggers_count": activated_triggers_count,
        "missing_trigger_condition_risk_ids": missing_trigger_condition_risk_ids,
        "unexecuted_contingency_risk_ids": unexecuted_contingency_risk_ids,
        "unauthorized_drawdown_risk_ids": unauthorized_drawdown_risk_ids,
        "is_trigger_governance_compliant": is_trigger_governance_compliant,
    }


ProjectExportService.audit_executive_report_risk_trigger_activation_governance = staticmethod(
    audit_executive_report_risk_trigger_activation_governance
)


def audit_executive_report_procurement_claims_settlement(
    report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Audita reclamos de adquisiciones (procurement claims), métodos ADR (negociación, mediación, arbitraje, litigio) y documentación de acuerdos en el reporte ejecutivo según PMI PMBOK §12.3 y §7.3."""
    claims: Sequence[Any] = []
    if isinstance(report, Mapping):
        raw_root = report.get("procurement_claims")
        if isinstance(raw_root, Sequence) and not isinstance(
            raw_root, (str, bytes, Mapping)
        ):
            claims = raw_root
        elif isinstance(report.get("governance"), Mapping):
            raw_gov = report["governance"].get("procurement_claims")
            if isinstance(raw_gov, Sequence) and not isinstance(
                raw_gov, (str, bytes, Mapping)
            ):
                claims = raw_gov

    valid_adr_methods = {"negotiation", "mediation", "arbitration", "litigation"}
    total_claims = 0
    total_disputed_amount = 0.0
    invalid_adr_method_claim_ids: list[str] = []
    escalated_litigation_claim_ids: list[str] = []
    undocumented_settlement_claim_ids: list[str] = []

    for item in claims:
        if not isinstance(item, Mapping):
            continue
        claim_id = str(item.get("claim_id") or "").strip()
        if not claim_id:
            continue

        total_claims += 1
        try:
            disputed_amount = max(
                0.0, float(item.get("disputed_amount", 0.0) or 0.0)
            )
        except (TypeError, ValueError):
            disputed_amount = 0.0
        total_disputed_amount += disputed_amount

        resolution_method = (
            str(item.get("resolution_method") or "").strip().lower()
        )
        status = str(item.get("status") or "").strip().lower()
        settlement_documented = bool(item.get("settlement_documented", False))

        if resolution_method not in valid_adr_methods:
            invalid_adr_method_claim_ids.append(claim_id)
        if resolution_method == "litigation":
            escalated_litigation_claim_ids.append(claim_id)
        if status in {"settled", "closed"} and not settlement_documented:
            undocumented_settlement_claim_ids.append(claim_id)

    total_disputed_amount = round(total_disputed_amount, 2)
    is_claims_governance_clean = bool(
        total_claims > 0
        and not invalid_adr_method_claim_ids
        and not escalated_litigation_claim_ids
        and not undocumented_settlement_claim_ids
    )

    return {
        "total_claims": total_claims,
        "total_disputed_amount": total_disputed_amount,
        "invalid_adr_method_claim_ids": invalid_adr_method_claim_ids,
        "escalated_litigation_claim_ids": escalated_litigation_claim_ids,
        "undocumented_settlement_claim_ids": undocumented_settlement_claim_ids,
        "is_claims_governance_clean": is_claims_governance_clean,
    }


ProjectExportService.audit_executive_report_procurement_claims_settlement = staticmethod(
    audit_executive_report_procurement_claims_settlement
)


def audit_executive_report_stakeholder_feedback_sla(
    report: Mapping[str, Any] | None,
    *,
    max_sla_days: float = 7.0,
) -> dict[str, Any]:
    """Audita el ciclo de retroalimentación de interesados (stakeholder feedback loop), asignación de dueños de acción, cumplimiento de SLA y confirmación de cierre en el reporte ejecutivo según PMI PMBOK §10.2 y §13.3."""
    feedback_items: Sequence[Any] = []
    if isinstance(report, Mapping):
        raw_root = report.get("stakeholder_feedback")
        if isinstance(raw_root, Sequence) and not isinstance(
            raw_root, (str, bytes, Mapping)
        ):
            feedback_items = raw_root
        elif isinstance(report.get("governance"), Mapping):
            raw_gov = report["governance"].get("stakeholder_feedback")
            if isinstance(raw_gov, Sequence) and not isinstance(
                raw_gov, (str, bytes, Mapping)
            ):
                feedback_items = raw_gov

    total_feedback_items = 0
    unassigned_feedback_ids: list[str] = []
    sla_breached_feedback_ids: list[str] = []
    unacknowledged_closure_feedback_ids: list[str] = []

    for item in feedback_items:
        if not isinstance(item, Mapping):
            continue
        feedback_id = str(item.get("feedback_id") or "").strip()
        if not feedback_id:
            continue

        total_feedback_items += 1
        try:
            response_days = max(0.0, float(item.get("response_days", 0.0) or 0.0))
        except (TypeError, ValueError):
            response_days = 0.0

        action_owner_id = str(item.get("action_owner_id") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        stakeholder_acknowledged = bool(
            item.get("stakeholder_acknowledged", False)
        )

        if not action_owner_id:
            unassigned_feedback_ids.append(feedback_id)
        if response_days > float(max_sla_days):
            sla_breached_feedback_ids.append(feedback_id)
        if status in {"closed", "resolved"} and not stakeholder_acknowledged:
            unacknowledged_closure_feedback_ids.append(feedback_id)

    sla_compliance_rate_pct = (
        round(
            (
                (total_feedback_items - len(sla_breached_feedback_ids))
                / total_feedback_items
            )
            * 100.0,
            2,
        )
        if total_feedback_items > 0
        else 0.0
    )
    is_feedback_loop_healthy = bool(
        total_feedback_items > 0
        and not unassigned_feedback_ids
        and not sla_breached_feedback_ids
        and not unacknowledged_closure_feedback_ids
    )

    return {
        "total_feedback_items": total_feedback_items,
        "unassigned_feedback_ids": unassigned_feedback_ids,
        "sla_breached_feedback_ids": sla_breached_feedback_ids,
        "unacknowledged_closure_feedback_ids": unacknowledged_closure_feedback_ids,
        "sla_compliance_rate_pct": sla_compliance_rate_pct,
        "is_feedback_loop_healthy": is_feedback_loop_healthy,
    }


ProjectExportService.audit_executive_report_stakeholder_feedback_sla = staticmethod(
    audit_executive_report_stakeholder_feedback_sla
)


def audit_executive_report_benefits_handover_kpis(
    report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """PMBOK §1.2.6 / §4.7 — handover de beneficios y cadencia de KPIs del informe ejecutivo.

    - Secuencia desde ``report['benefits_kpis']`` con fallback a
      ``report['governance']['benefits_kpis']`` (root-level con prioridad;
      str/bytes/Mapping descartados como secuencia).
    - Sin baseline/target numéricos (bool excluido) -> ``unquantified_benefit_ids``.
    - Sin ``benefit_owner_id`` o cadencia fuera de
      {weekly, monthly, quarterly, annual} -> ``ungoverned_cadence_benefit_ids``.
    - ``operational_custodian_accepted`` falso -> ``unaccepted_handover_benefit_ids``.
    """
    unquantified_benefit_ids: list[str] = []
    ungoverned_cadence_benefit_ids: list[str] = []
    unaccepted_handover_benefit_ids: list[str] = []

    if isinstance(report, Mapping):
        raw_kpis = report.get("benefits_kpis")
        if isinstance(raw_kpis, (list, tuple)):
            kpis = raw_kpis
        elif isinstance(report.get("governance"), Mapping):
            gov_kpis = report["governance"].get("benefits_kpis")
            kpis = gov_kpis if isinstance(gov_kpis, (list, tuple)) else []
        else:
            kpis = []
    else:
        kpis = []

    total_benefits = 0

    for item in kpis:
        if not isinstance(item, Mapping):
            continue
        benefit_id = str(item.get("benefit_id") or "").strip()
        if not benefit_id:
            continue
        total_benefits += 1

        b_val = item.get("baseline_value")
        t_val = item.get("target_value")
        has_quant = (
            isinstance(b_val, (int, float))
            and not isinstance(b_val, bool)
            and isinstance(t_val, (int, float))
            and not isinstance(t_val, bool)
        )
        benefit_owner_id = str(item.get("benefit_owner_id") or "").strip()
        measurement_cadence = str(item.get("measurement_cadence") or "").strip().lower()
        operational_custodian_accepted = bool(item.get("operational_custodian_accepted", False))

        if not has_quant:
            unquantified_benefit_ids.append(benefit_id)

        if not benefit_owner_id or measurement_cadence not in {
            "weekly",
            "monthly",
            "quarterly",
            "annual",
        }:
            ungoverned_cadence_benefit_ids.append(benefit_id)

        if not operational_custodian_accepted:
            unaccepted_handover_benefit_ids.append(benefit_id)

    is_benefits_handover_ready = bool(
        total_benefits > 0
        and not unquantified_benefit_ids
        and not ungoverned_cadence_benefit_ids
        and not unaccepted_handover_benefit_ids
    )

    return {
        "total_benefits": total_benefits,
        "unquantified_benefit_ids": unquantified_benefit_ids,
        "ungoverned_cadence_benefit_ids": ungoverned_cadence_benefit_ids,
        "unaccepted_handover_benefit_ids": unaccepted_handover_benefit_ids,
        "is_benefits_handover_ready": is_benefits_handover_ready,
    }


ProjectExportService.audit_executive_report_benefits_handover_kpis = staticmethod(
    audit_executive_report_benefits_handover_kpis
)


def audit_executive_report_resource_spof_and_overallocation(
    report: Mapping[str, Any] | None,
    max_allocation_pct: float = 100.0,
    max_overtime_pct: float = 15.0,
) -> dict[str, Any]:
    """Audita sobreasignación de recursos, agotamiento por horas extra (burnout) y puntos únicos de fallo (SPOF / Bus Factor = 1) en reportes ejecutivos según PMI PMBOK §9.3 y §9.4."""
    allocations: Sequence[Any] = []
    if isinstance(report, Mapping):
        raw_root = report.get("resource_allocations")
        if isinstance(raw_root, Sequence) and not isinstance(
            raw_root, (str, bytes, Mapping)
        ):
            allocations = raw_root
        elif isinstance(report.get("governance"), Mapping):
            raw_gov = report["governance"].get("resource_allocations")
            if isinstance(raw_gov, Sequence) and not isinstance(
                raw_gov, (str, bytes, Mapping)
            ):
                allocations = raw_gov

    total_resources = 0
    overallocated_resource_ids: list[str] = []
    burnout_risk_resource_ids: list[str] = []
    spof_unbacked_resource_ids: list[str] = []

    max_alloc = float(max_allocation_pct)
    max_ot = float(max_overtime_pct)

    for item in allocations:
        if not isinstance(item, Mapping):
            continue
        resource_id = str(
            item.get("resource_id") or item.get("id") or ""
        ).strip()
        if not resource_id:
            continue

        total_resources += 1
        try:
            allocation_pct = float(item.get("allocation_pct") or 0.0)
        except (TypeError, ValueError):
            allocation_pct = 0.0

        try:
            overtime_pct = float(item.get("overtime_pct") or 0.0)
        except (TypeError, ValueError):
            overtime_pct = 0.0

        is_critical_skill = bool(item.get("is_critical_skill") is True)
        try:
            assigned_critical_tasks_count = int(
                item.get("assigned_critical_tasks_count") or 0
            )
        except (TypeError, ValueError):
            assigned_critical_tasks_count = 0
        backup_resource_id = str(item.get("backup_resource_id") or "").strip()

        if allocation_pct > max_alloc:
            overallocated_resource_ids.append(resource_id)

        if overtime_pct > max_ot:
            burnout_risk_resource_ids.append(resource_id)

        if (
            is_critical_skill or assigned_critical_tasks_count > 0
        ) and not backup_resource_id:
            spof_unbacked_resource_ids.append(resource_id)

    is_resource_governance_healthy = bool(
        len(overallocated_resource_ids) == 0
        and len(burnout_risk_resource_ids) == 0
        and len(spof_unbacked_resource_ids) == 0
    )

    recommendations: list[str] = []
    if spof_unbacked_resource_ids:
        recommendations.append(
            "Asignar recurso de respaldo (backup_resource_id) y plan de cross-training para eliminar puntos únicos de fallo (SPOF) en habilidades o tareas críticas."
        )
    if overallocated_resource_ids:
        recommendations.append(
            "Aplicar nivelación o suavizado de recursos (Resource Leveling/Smoothing) para reducir asignaciones superiores al límite de capacidad."
        )
    if burnout_risk_resource_ids:
        recommendations.append(
            "Redistribuir carga operativa para contener el exceso de horas extra y prevenir el agotamiento del equipo."
        )

    if len(spof_unbacked_resource_ids) > 0 or len(overallocated_resource_ids) > 0:
        status = "critical"
    elif len(burnout_risk_resource_ids) > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_resources": total_resources,
        "overallocated_resource_ids": overallocated_resource_ids,
        "burnout_risk_resource_ids": burnout_risk_resource_ids,
        "spof_unbacked_resource_ids": spof_unbacked_resource_ids,
        "is_resource_governance_healthy": is_resource_governance_healthy,
        "status": status,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_resource_spof_and_overallocation = staticmethod(
    audit_executive_report_resource_spof_and_overallocation
)


def audit_executive_report_change_readiness_and_adoption(
    report: Mapping[str, Any] | None,
    *,
    min_training_completion_pct: float = 85.0,
    min_readiness_score_pct: float = 75.0,
) -> dict[str, Any]:
    """Audita preparación para el cambio organizacional y adopción operativa (ADKAR / Training Readiness) en reportes ejecutivos según PMI PMBOK §13.3."""
    readiness_units: Sequence[Any] = []
    if isinstance(report, Mapping):
        raw_root = report.get("change_readiness_units")
        if isinstance(raw_root, Sequence) and not isinstance(
            raw_root, (str, bytes, Mapping)
        ):
            readiness_units = raw_root
        elif isinstance(report.get("governance"), Mapping):
            raw_gov = report["governance"].get("change_readiness_units")
            if isinstance(raw_gov, Sequence) and not isinstance(
                raw_gov, (str, bytes, Mapping)
            ):
                readiness_units = raw_gov

    min_training = float(min_training_completion_pct)
    min_readiness = float(min_readiness_score_pct)

    total_units = 0
    insufficient_training_unit_ids: list[str] = []
    low_readiness_unit_ids: list[str] = []
    missing_champion_or_hypercare_unit_ids: list[str] = []

    for item in readiness_units:
        if not isinstance(item, Mapping):
            continue
        unit_id = str(item.get("unit_id") or item.get("id") or "").strip()
        if not unit_id:
            continue

        total_units += 1

        try:
            raw_training = item.get("training_completion_pct")
            training_pct = (
                float(raw_training)
                if isinstance(raw_training, (int, float))
                and not isinstance(raw_training, bool)
                else 0.0
            )
        except (TypeError, ValueError):
            training_pct = 0.0
        if not (
            isinstance(raw_training, (int, float))
            and not isinstance(raw_training, bool)
        ) or training_pct < min_training:
            insufficient_training_unit_ids.append(unit_id)

        try:
            raw_readiness = item.get("readiness_score_pct")
            readiness_pct = (
                float(raw_readiness)
                if isinstance(raw_readiness, (int, float))
                and not isinstance(raw_readiness, bool)
                else 0.0
            )
        except (TypeError, ValueError):
            readiness_pct = 0.0
        if not (
            isinstance(raw_readiness, (int, float))
            and not isinstance(raw_readiness, bool)
        ) or readiness_pct < min_readiness:
            low_readiness_unit_ids.append(unit_id)

        change_champion = str(item.get("change_champion") or "").strip()
        hypercare_ready = bool(item.get("hypercare_support_ready") is True)
        if not change_champion or not hypercare_ready:
            missing_champion_or_hypercare_unit_ids.append(unit_id)

    is_change_readiness_compliant = bool(
        total_units > 0
        and len(insufficient_training_unit_ids) == 0
        and len(low_readiness_unit_ids) == 0
        and len(missing_champion_or_hypercare_unit_ids) == 0
    )

    return {
        "total_units": total_units,
        "insufficient_training_unit_ids": insufficient_training_unit_ids,
        "low_readiness_unit_ids": low_readiness_unit_ids,
        "missing_champion_or_hypercare_unit_ids": missing_champion_or_hypercare_unit_ids,
        "is_change_readiness_compliant": is_change_readiness_compliant,
    }


ProjectExportService.audit_executive_report_change_readiness_and_adoption = staticmethod(
    audit_executive_report_change_readiness_and_adoption
)


def audit_executive_report_contract_closeout_and_claims(
    contracts: object,
) -> dict[str, object]:
    """Audita cierre administrativo de contratos, liquidación de reclamos/disputas y SLA de garantías según PMI PMBOK §12.3 y §4.7."""
    total_evaluated = 0
    unresolved_claim_contract_ids: list[str] = []
    premature_closeout_contract_ids: list[str] = []
    missing_warranty_sla_contract_ids: list[str] = []

    if isinstance(contracts, Sequence) and not isinstance(
        contracts, (str, bytes, bytearray)
    ):
        for item in contracts:
            if not isinstance(item, Mapping):
                continue
            contract_id = str(
                item.get("contract_id") or item.get("id") or ""
            ).strip()
            if not contract_id:
                continue

            total_evaluated += 1
            status = str(item.get("status") or "").strip().lower()
            try:
                open_claims_or_disputes_count = int(
                    item.get("open_claims_or_disputes_count", 0) or 0
                )
            except (TypeError, ValueError):
                open_claims_or_disputes_count = 0

            final_deliverables_accepted = bool(
                item.get("final_deliverables_accepted", False)
            )
            lien_waiver_or_release_signed = bool(
                item.get("lien_waiver_or_release_signed", False)
            )
            try:
                warranty_period_months = int(
                    item.get("warranty_period_months", 0) or 0
                )
            except (TypeError, ValueError):
                warranty_period_months = 0

            warranty_sla_documented = bool(
                item.get("warranty_sla_documented", False)
            )

            if open_claims_or_disputes_count > 0:
                unresolved_claim_contract_ids.append(contract_id)

            if status in {"closed", "completed", "terminated"} and (
                not final_deliverables_accepted
                or not lien_waiver_or_release_signed
                or open_claims_or_disputes_count > 0
            ):
                premature_closeout_contract_ids.append(contract_id)

            if warranty_period_months > 0 and not warranty_sla_documented:
                missing_warranty_sla_contract_ids.append(contract_id)

    return {
        "total_evaluated": total_evaluated,
        "unresolved_claim_contract_ids": unresolved_claim_contract_ids,
        "premature_closeout_contract_ids": premature_closeout_contract_ids,
        "missing_warranty_sla_contract_ids": missing_warranty_sla_contract_ids,
        "is_contract_closeout_compliant": (
            len(unresolved_claim_contract_ids) == 0
            and len(premature_closeout_contract_ids) == 0
            and len(missing_warranty_sla_contract_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_contract_closeout_and_claims = staticmethod(
    audit_executive_report_contract_closeout_and_claims
)


def audit_executive_report_strategic_alignment_and_esg(
    initiatives: object,
    *,
    min_alignment_score: float = 70.0,
) -> dict[str, object]:
    """Audita alineamiento estratégico portfolio-OKR e impacto ESG (sostenibilidad) de iniciativas en reportes ejecutivos según PMI PMBOK §1.2 y §2.4."""
    total_evaluated = 0
    unaligned_strategic_initiative_ids: list[str] = []
    unassessed_esg_initiative_ids: list[str] = []
    unmitigated_esg_risk_initiative_ids: list[str] = []

    min_score = float(min_alignment_score)
    items: Sequence[Any] = (
        initiatives
        if isinstance(initiatives, Sequence)
        and not isinstance(initiatives, (str, bytes, bytearray))
        else []
    )

    for item in items:
        if not isinstance(item, Mapping):
            continue
        init_id = str(item.get("initiative_id") or item.get("id") or "").strip()
        if not init_id:
            continue

        total_evaluated += 1

        okr_or_pillar_code = str(item.get("okr_or_pillar_code") or "").strip()
        try:
            strategic_alignment_score = float(
                item.get("strategic_alignment_score", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            strategic_alignment_score = 0.0
        esg_impact_assessed = bool(item.get("esg_impact_assessed", False))
        has_negative_environmental_or_social_impact = bool(
            item.get("has_negative_environmental_or_social_impact", False)
        )
        esg_mitigation_plan_approved = bool(
            item.get("esg_mitigation_plan_approved", False)
        )

        if not okr_or_pillar_code or strategic_alignment_score < min_score:
            unaligned_strategic_initiative_ids.append(init_id)

        if not esg_impact_assessed:
            unassessed_esg_initiative_ids.append(init_id)

        if (
            has_negative_environmental_or_social_impact
            and not esg_mitigation_plan_approved
        ):
            unmitigated_esg_risk_initiative_ids.append(init_id)

    is_strategic_and_esg_compliant = bool(
        len(unaligned_strategic_initiative_ids) == 0
        and len(unassessed_esg_initiative_ids) == 0
        and len(unmitigated_esg_risk_initiative_ids) == 0
    )

    return {
        "total_evaluated": total_evaluated,
        "unaligned_strategic_initiative_ids": unaligned_strategic_initiative_ids,
        "unassessed_esg_initiative_ids": unassessed_esg_initiative_ids,
        "unmitigated_esg_risk_initiative_ids": unmitigated_esg_risk_initiative_ids,
        "is_strategic_and_esg_compliant": is_strategic_and_esg_compliant,
    }


ProjectExportService.audit_executive_report_strategic_alignment_and_esg = staticmethod(
    audit_executive_report_strategic_alignment_and_esg
)


def audit_executive_report_rag_status_and_narrative_consistency(
    kpi_cards: object,
) -> dict[str, object]:
    """Audita coherencia de semáforos RAG frente a umbrales cuantitativos (prevención de 'Watermelon Projects') y presencia de narrativa de acción correctiva según PMI PMBOK §10.2 y §10.3."""
    total_evaluated = 0
    invalid_rag_label_kpi_ids: list[str] = []
    watermelon_masked_status_kpi_ids: list[str] = []
    missing_corrective_narrative_kpi_ids: list[str] = []

    valid_raw_labels = {"green", "amber", "yellow", "red"}
    severity_rank = {"green": 0, "amber": 1, "red": 2}

    if isinstance(kpi_cards, Sequence) and not isinstance(
        kpi_cards, (str, bytes, bytearray)
    ):
        for item in kpi_cards:
            if not isinstance(item, Mapping):
                continue
            kpi_id = str(item.get("kpi_id") or item.get("id") or "").strip()
            if not kpi_id:
                continue

            total_evaluated += 1
            reported_rag = str(item.get("reported_rag") or "").strip().lower()

            try:
                variance_pct = float(item.get("variance_pct", 0.0) or 0.0)
            except (TypeError, ValueError):
                variance_pct = 0.0

            raw_amber = item.get("amber_threshold_pct", -5.0)
            try:
                amber_threshold_pct = (
                    float(raw_amber) if raw_amber is not None else -5.0
                )
            except (TypeError, ValueError):
                amber_threshold_pct = -5.0

            raw_red = item.get("red_threshold_pct", -10.0)
            try:
                red_threshold_pct = (
                    float(raw_red) if raw_red is not None else -10.0
                )
            except (TypeError, ValueError):
                red_threshold_pct = -10.0

            corrective_action_narrative = str(
                item.get("corrective_action_narrative") or ""
            ).strip()

            if variance_pct <= red_threshold_pct:
                target_status = "red"
            elif variance_pct <= amber_threshold_pct:
                target_status = "amber"
            else:
                target_status = "green"

            if reported_rag not in valid_raw_labels:
                invalid_rag_label_kpi_ids.append(kpi_id)
                norm_reported = ""
            else:
                norm_reported = (
                    "amber" if reported_rag == "yellow" else reported_rag
                )
                if severity_rank[norm_reported] < severity_rank[target_status]:
                    watermelon_masked_status_kpi_ids.append(kpi_id)

            if (
                target_status in {"red", "amber"}
                or norm_reported in {"red", "amber"}
            ) and len(corrective_action_narrative) < 15:
                missing_corrective_narrative_kpi_ids.append(kpi_id)

    return {
        "total_evaluated": total_evaluated,
        "invalid_rag_label_kpi_ids": invalid_rag_label_kpi_ids,
        "watermelon_masked_status_kpi_ids": watermelon_masked_status_kpi_ids,
        "missing_corrective_narrative_kpi_ids": missing_corrective_narrative_kpi_ids,
        "is_rag_reporting_transparent": (
            len(invalid_rag_label_kpi_ids) == 0
            and len(watermelon_masked_status_kpi_ids) == 0
            and len(missing_corrective_narrative_kpi_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_rag_status_and_narrative_consistency = staticmethod(
    audit_executive_report_rag_status_and_narrative_consistency
)


def audit_executive_report_reserve_drawdown_burn_rate(
    reserve_tranches: object,
    *,
    project_percent_complete: float = 0.0,
    max_burn_to_progress_ratio: float = 1.25,
) -> dict[str, object]:
    """Audita tasa de consumo (drawdown burn rate) de reservas de contingencia y de gestión frente al avance del proyecto y autorizaciones del patrocinador/CCB según PMI PMBOK §10.2 y §11.2."""
    try:
        pct_complete = (
            max(0.0, min(100.0, float(project_percent_complete or 0.0))) / 100.0
        )
    except (TypeError, ValueError):
        pct_complete = 0.0

    max_ratio = float(max_burn_to_progress_ratio)

    total_tranches = 0
    total_initial_raw = 0.0
    total_consumed_raw = 0.0
    invalid_reserve_type_tranche_ids: list[str] = []
    overdrawn_or_negative_tranche_ids: list[str] = []
    unlinked_drawdown_tranche_ids: list[str] = []
    unapproved_management_reserve_tranche_ids: list[str] = []
    accelerated_burn_tranche_ids: list[str] = []

    if isinstance(reserve_tranches, Sequence) and not isinstance(
        reserve_tranches, (str, bytes, bytearray)
    ):
        for item in reserve_tranches:
            if not isinstance(item, Mapping):
                continue
            tranche_id = str(
                item.get("tranche_id") or item.get("id") or ""
            ).strip()
            if not tranche_id:
                continue

            total_tranches += 1
            reserve_type = str(item.get("reserve_type") or "").strip().lower()

            try:
                initial_amount = float(item.get("initial_amount", 0.0) or 0.0)
            except (TypeError, ValueError):
                initial_amount = 0.0

            try:
                consumed_amount = float(item.get("consumed_amount", 0.0) or 0.0)
            except (TypeError, ValueError):
                consumed_amount = 0.0

            total_initial_raw += max(0.0, initial_amount)
            total_consumed_raw += max(0.0, consumed_amount)

            raw_links = item.get("linked_risk_or_change_ids")
            if isinstance(raw_links, Sequence) and not isinstance(
                raw_links, (str, bytes, bytearray)
            ):
                has_linked_id = any(
                    str(ref or "").strip() for ref in raw_links
                )
            else:
                has_linked_id = False

            executive_sponsor_approved = bool(
                item.get("executive_sponsor_approved", False)
            )

            if reserve_type not in {"contingency", "management"}:
                invalid_reserve_type_tranche_ids.append(tranche_id)

            if (
                consumed_amount < 0.0
                or initial_amount < 0.0
                or consumed_amount > initial_amount
            ):
                overdrawn_or_negative_tranche_ids.append(tranche_id)

            if consumed_amount > 0.0 and not has_linked_id:
                unlinked_drawdown_tranche_ids.append(tranche_id)

            if (
                reserve_type == "management"
                and consumed_amount > 0.0
                and not executive_sponsor_approved
            ):
                unapproved_management_reserve_tranche_ids.append(tranche_id)

            if initial_amount > 0.0 and consumed_amount >= 0.0:
                drawdown_ratio = consumed_amount / initial_amount
                if (
                    pct_complete > 0.0
                    and (drawdown_ratio / pct_complete) > max_ratio
                ) or (pct_complete == 0.0 and drawdown_ratio > 0.15):
                    accelerated_burn_tranche_ids.append(tranche_id)

    total_initial_reserve = round(total_initial_raw, 2)
    total_consumed_reserve = round(total_consumed_raw, 2)
    overall_drawdown_pct = (
        round((total_consumed_reserve / total_initial_reserve) * 100.0, 2)
        if total_initial_reserve > 0.0
        else 0.0
    )

    return {
        "total_tranches": total_tranches,
        "total_initial_reserve": total_initial_reserve,
        "total_consumed_reserve": total_consumed_reserve,
        "overall_drawdown_pct": overall_drawdown_pct,
        "invalid_reserve_type_tranche_ids": invalid_reserve_type_tranche_ids,
        "overdrawn_or_negative_tranche_ids": overdrawn_or_negative_tranche_ids,
        "unlinked_drawdown_tranche_ids": unlinked_drawdown_tranche_ids,
        "unapproved_management_reserve_tranche_ids": unapproved_management_reserve_tranche_ids,
        "accelerated_burn_tranche_ids": accelerated_burn_tranche_ids,
        "is_reserve_drawdown_compliant": (
            len(invalid_reserve_type_tranche_ids) == 0
            and len(overdrawn_or_negative_tranche_ids) == 0
            and len(unlinked_drawdown_tranche_ids) == 0
            and len(unapproved_management_reserve_tranche_ids) == 0
            and len(accelerated_burn_tranche_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_reserve_drawdown_burn_rate = staticmethod(
    audit_executive_report_reserve_drawdown_burn_rate
)


def audit_executive_report_post_implementation_handover_sla(
    handover_packages: list[dict[str, object]],
    *,
    min_hypercare_days: int = 14,
) -> dict[str, object]:
    """Audita los paquetes de traspaso operativo post-implementación, ventana de soporte hypercare, runbooks SOP y defectos críticos bloqueantes según PMI PMBOK §4.7 y §10.2."""
    try:
        min_days = float(min_hypercare_days)
    except (TypeError, ValueError):
        min_days = 14.0

    total_packages = 0
    unsigned_or_unowned_handover_ids: list[str] = []
    insufficient_runbook_or_hypercare_ids: list[str] = []
    blocking_critical_defect_handover_ids: list[str] = []

    if isinstance(handover_packages, Sequence) and not isinstance(
        handover_packages, (str, bytes, bytearray)
    ):
        for item in handover_packages:
            if not isinstance(item, Mapping):
                continue
            package_id = str(
                item.get("package_id") or item.get("id") or ""
            ).strip()
            if not package_id:
                continue

            total_packages += 1
            receiving_team = str(
                item.get("receiving_operations_team") or ""
            ).strip()
            runbook_complete = bool(item.get("runbook_and_sop_complete", False))
            operations_signed = bool(
                item.get("operations_acceptance_signed", False)
            )
            benefits_owner_assigned = bool(
                item.get("benefits_owner_assigned", False)
            )

            raw_hypercare = item.get("hypercare_support_days", 0)
            if raw_hypercare is None or isinstance(raw_hypercare, bool):
                hypercare_days = 0.0
            else:
                try:
                    hypercare_days = float(raw_hypercare)
                except (TypeError, ValueError):
                    hypercare_days = 0.0

            raw_defects = item.get("open_sev1_sev2_defects", 0)
            if raw_defects is None or isinstance(raw_defects, bool):
                open_defects = 0
            else:
                try:
                    open_defects = int(float(raw_defects))
                except (TypeError, ValueError):
                    open_defects = 0

            if (
                not receiving_team
                or not operations_signed
                or not benefits_owner_assigned
            ):
                unsigned_or_unowned_handover_ids.append(package_id)

            if not runbook_complete or hypercare_days < min_days:
                insufficient_runbook_or_hypercare_ids.append(package_id)

            if open_defects > 0:
                blocking_critical_defect_handover_ids.append(package_id)

    return {
        "total_packages": total_packages,
        "unsigned_or_unowned_handover_ids": unsigned_or_unowned_handover_ids,
        "insufficient_runbook_or_hypercare_ids": insufficient_runbook_or_hypercare_ids,
        "blocking_critical_defect_handover_ids": blocking_critical_defect_handover_ids,
        "is_handover_sla_compliant": (
            len(unsigned_or_unowned_handover_ids) == 0
            and len(insufficient_runbook_or_hypercare_ids) == 0
            and len(blocking_critical_defect_handover_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_post_implementation_handover_sla = staticmethod(
    audit_executive_report_post_implementation_handover_sla
)


def audit_executive_report_team_burnout_and_turnover_risk(
    team_health_snapshots: list[dict[str, object]],
    *,
    max_sustainable_utilization_pct: float = 100.0,
    max_attrition_rate_pct: float = 15.0,
) -> dict[str, object]:
    """Audita el riesgo de agotamiento del equipo (burnout por sobreutilización o sprints consecutivos en sobretiempo), rotación anualizada y roles SPOF sin plan de cross-training según PMI PMBOK §9.4 y §9.5."""
    try:
        max_util = float(max_sustainable_utilization_pct)
    except (TypeError, ValueError):
        max_util = 100.0

    try:
        max_attrition = float(max_attrition_rate_pct)
    except (TypeError, ValueError):
        max_attrition = 15.0

    total_teams = 0
    invalid_health_metric_team_ids: list[str] = []
    chronic_burnout_risk_team_ids: list[str] = []
    high_turnover_attrition_team_ids: list[str] = []
    unmitigated_key_person_spof_team_ids: list[str] = []

    if isinstance(team_health_snapshots, Sequence) and not isinstance(
        team_health_snapshots, (str, bytes, bytearray)
    ):
        for item in team_health_snapshots:
            if not isinstance(item, Mapping):
                continue
            team_id = str(item.get("team_id") or item.get("id") or "").strip()
            if not team_id:
                continue

            total_teams += 1

            def _float_val(key: str, default: float = 0.0) -> float:
                raw = item.get(key, default)
                if raw is None or isinstance(raw, bool):
                    return default
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return -1.0

            def _int_val(key: str, default: int = 0) -> int:
                raw = item.get(key, default)
                if raw is None or isinstance(raw, bool):
                    return default
                try:
                    return int(float(raw))
                except (TypeError, ValueError):
                    return -1

            avg_util = _float_val("avg_utilization_pct", 0.0)
            overtime_sprints = _int_val("consecutive_overtime_sprints", 0)
            attrition_rate = _float_val("annualized_attrition_rate_pct", 0.0)
            spof_roles = _int_val("single_point_of_failure_roles_count", 0)
            cross_training_active = bool(
                item.get("cross_training_plan_active", False)
            )

            if (
                avg_util < 0.0
                or overtime_sprints < 0
                or attrition_rate < 0.0
                or spof_roles < 0
            ):
                invalid_health_metric_team_ids.append(team_id)
                continue

            if avg_util > max_util or overtime_sprints >= 3:
                chronic_burnout_risk_team_ids.append(team_id)

            if attrition_rate > max_attrition:
                high_turnover_attrition_team_ids.append(team_id)

            if spof_roles > 0 and not cross_training_active:
                unmitigated_key_person_spof_team_ids.append(team_id)

    return {
        "total_teams": total_teams,
        "invalid_health_metric_team_ids": invalid_health_metric_team_ids,
        "chronic_burnout_risk_team_ids": chronic_burnout_risk_team_ids,
        "high_turnover_attrition_team_ids": high_turnover_attrition_team_ids,
        "unmitigated_key_person_spof_team_ids": unmitigated_key_person_spof_team_ids,
        "is_team_sustainability_compliant": (
            len(invalid_health_metric_team_ids) == 0
            and len(chronic_burnout_risk_team_ids) == 0
            and len(high_turnover_attrition_team_ids) == 0
            and len(unmitigated_key_person_spof_team_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_team_burnout_and_turnover_risk = staticmethod(
    audit_executive_report_team_burnout_and_turnover_risk
)


def audit_executive_report_monte_carlo_p50_p80_confidence(
    simulation_summaries: list[dict[str, object]],
    *,
    min_iterations: int = 1000,
) -> dict[str, object]:
    """Audita simulaciones cuantitativas Monte Carlo de riesgo de costos verificando iteraciones mínimas, matriz de correlación, monotonía de cuantiles P50 <= P80 <= P90 y suficiencia de reserva de contingencia frente a P80 según PMI PMBOK §11.4."""
    try:
        min_iter = int(min_iterations)
    except (TypeError, ValueError):
        min_iter = 1000

    total_simulations = 0
    invalid_simulation_metric_ids: list[str] = []
    under_sampled_or_uncorrelated_ids: list[str] = []
    non_monotonic_percentile_ids: list[str] = []
    underfunded_p80_contingency_ids: list[str] = []

    if isinstance(simulation_summaries, Sequence) and not isinstance(
        simulation_summaries, (str, bytes, bytearray)
    ):
        for item in simulation_summaries:
            if not isinstance(item, Mapping):
                continue
            simulation_id = str(
                item.get("simulation_id") or item.get("id") or ""
            ).strip()
            if not simulation_id:
                continue

            total_simulations += 1

            def _float_val(key: str, default: float = -1.0) -> float:
                raw = item.get(key)
                if raw is None:
                    return default
                if isinstance(raw, bool):
                    return -1.0
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return -1.0

            base_cost = _float_val("deterministic_base_cost", -1.0)
            p50 = _float_val("p50_cost", -1.0)
            p80 = _float_val("p80_cost", -1.0)
            p90 = _float_val("p90_cost", -1.0)
            contingency = _float_val("allocated_contingency_reserve", 0.0)

            raw_iter = item.get("iterations_count", 0)
            if raw_iter is None or isinstance(raw_iter, bool):
                iterations = 0
            else:
                try:
                    iterations = int(float(raw_iter))
                except (TypeError, ValueError):
                    iterations = 0

            correlation_applied = bool(
                item.get("correlation_matrix_applied", False)
            )

            if (
                base_cost <= 0.0
                or p50 <= 0.0
                or p80 <= 0.0
                or p90 <= 0.0
                or contingency < 0.0
            ):
                invalid_simulation_metric_ids.append(simulation_id)
                continue

            if iterations < min_iter or not correlation_applied:
                under_sampled_or_uncorrelated_ids.append(simulation_id)

            if not (p50 <= p80 <= p90):
                non_monotonic_percentile_ids.append(simulation_id)

            if (base_cost + contingency) + 0.01 < p80:
                underfunded_p80_contingency_ids.append(simulation_id)

    return {
        "total_simulations": total_simulations,
        "invalid_simulation_metric_ids": invalid_simulation_metric_ids,
        "under_sampled_or_uncorrelated_ids": under_sampled_or_uncorrelated_ids,
        "non_monotonic_percentile_ids": non_monotonic_percentile_ids,
        "underfunded_p80_contingency_ids": underfunded_p80_contingency_ids,
        "is_monte_carlo_governance_compliant": (
            len(invalid_simulation_metric_ids) == 0
            and len(under_sampled_or_uncorrelated_ids) == 0
            and len(non_monotonic_percentile_ids) == 0
            and len(underfunded_p80_contingency_ids) == 0
        ),
    }


ProjectExportService.audit_executive_report_monte_carlo_p50_p80_confidence = staticmethod(
    audit_executive_report_monte_carlo_p50_p80_confidence
)


def audit_executive_report_vendor_sla_and_liquidated_damages(
    vendor_contracts: list[dict[str, Any]],
    *,
    max_ld_cap_utilization_pct: float = 80.0,
) -> dict[str, Any]:
    """PMBOK §12.3 / §4.7 — auditoría de SLA de proveedores y exposición a daños liquidados (LD)."""
    if not isinstance(vendor_contracts, Sequence) or isinstance(
        vendor_contracts, (str, bytes)
    ):
        return {
            "total_contracts": 0,
            "compliant_contracts_count": 0,
            "sla_breached_contracts_count": 0,
            "late_deliverables_contracts_count": 0,
            "near_or_at_ld_cap_count": 0,
            "total_accrued_liquidated_damages": 0.0,
            "total_disputed_claims_amount": 0.0,
            "vendor_sla_governance_status": "HEALTHY",
            "findings": [],
        }

    try:
        max_util = float(max_ld_cap_utilization_pct)
    except (TypeError, ValueError):
        max_util = 80.0

    total_contracts = 0
    compliant_contracts_count = 0
    sla_breached_contracts_count = 0
    late_deliverables_contracts_count = 0
    near_or_at_ld_cap_count = 0
    total_accrued_ld = 0.0
    total_disputed = 0.0
    findings: list[dict[str, Any]] = []

    for item in vendor_contracts:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("contract_id")
        if raw_id is None:
            continue
        contract_id = str(raw_id).strip()
        if not contract_id:
            continue

        total_contracts += 1

        contract_value = float(item.get("contract_value", 0.0) or 0.0)
        sla_target = float(item.get("sla_target_uptime_pct", 0.0) or 0.0)
        actual_uptime = float(item.get("actual_uptime_pct", 0.0) or 0.0)
        late_count = int(item.get("late_deliverables_count", 0) or 0)
        accrued_ld = float(item.get("accrued_liquidated_damages", 0.0) or 0.0)
        ld_cap_pct = float(item.get("ld_cap_pct", 0.0) or 0.0)
        disputed_amt = float(item.get("disputed_claims_amount", 0.0) or 0.0)

        total_accrued_ld += accrued_ld
        total_disputed += disputed_amt

        sla_breached = actual_uptime < sla_target
        has_late_deliverables = late_count > 0
        ld_cap_amount = contract_value * (ld_cap_pct / 100.0)
        if ld_cap_amount > 0.0:
            ld_cap_utilization_pct = round((accrued_ld / ld_cap_amount) * 100.0, 2)
        else:
            ld_cap_utilization_pct = 0.0

        near_or_at_ld_cap = ld_cap_utilization_pct >= max_util or (
            accrued_ld > 0.0 and ld_cap_amount <= 0.0
        )

        issues: list[str] = []
        if sla_breached:
            sla_breached_contracts_count += 1
            issues.append("sla_uptime_breached")
        if has_late_deliverables:
            late_deliverables_contracts_count += 1
            issues.append("late_deliverables_present")
        if near_or_at_ld_cap:
            near_or_at_ld_cap_count += 1
            issues.append("near_or_at_liquidated_damages_cap")
        if disputed_amt > 0.0:
            issues.append("unsettled_disputed_claims")

        if not issues:
            compliant_contracts_count += 1
        else:
            findings.append(
                {
                    "contract_id": contract_id,
                    "ld_cap_utilization_pct": ld_cap_utilization_pct,
                    "issues": issues,
                }
            )

    total_accrued_liquidated_damages = round(total_accrued_ld, 2)
    total_disputed_claims_amount = round(total_disputed, 2)

    if (
        sla_breached_contracts_count == 0
        and late_deliverables_contracts_count == 0
        and near_or_at_ld_cap_count == 0
        and total_disputed_claims_amount == 0.0
    ):
        status = "HEALTHY"
    elif near_or_at_ld_cap_count > 0 or (
        sla_breached_contracts_count > 0 and late_deliverables_contracts_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_contracts": total_contracts,
        "compliant_contracts_count": compliant_contracts_count,
        "sla_breached_contracts_count": sla_breached_contracts_count,
        "late_deliverables_contracts_count": late_deliverables_contracts_count,
        "near_or_at_ld_cap_count": near_or_at_ld_cap_count,
        "total_accrued_liquidated_damages": total_accrued_liquidated_damages,
        "total_disputed_claims_amount": total_disputed_claims_amount,
        "vendor_sla_governance_status": status,
        "findings": findings,
    }


ProjectExportService.audit_executive_report_vendor_sla_and_liquidated_damages = staticmethod(
    audit_executive_report_vendor_sla_and_liquidated_damages
)


def audit_executive_report_stakeholder_escalation_and_briefing_cadence(
    stakeholder_escalations: list[dict[str, Any]],
    *,
    max_open_escalation_days: int = 7,
    max_briefing_gap_days: int = 14,
) -> dict[str, Any]:
    """PMBOK §13.3 / §10.3 — auditoría de matriz de escalamiento de interesados y cadencia de briefings."""
    if not isinstance(stakeholder_escalations, Sequence) or isinstance(
        stakeholder_escalations, (str, bytes)
    ):
        return {
            "total_stakeholders_evaluated": 0,
            "compliant_stakeholders_count": 0,
            "overdue_escalations_stakeholders_count": 0,
            "unmitigated_escalations_count": 0,
            "stale_briefing_stakeholders_count": 0,
            "total_open_escalations": 0,
            "escalation_governance_status": "HEALTHY",
            "findings": [],
        }

    try:
        max_esc_days = int(max_open_escalation_days)
    except (TypeError, ValueError):
        max_esc_days = 7

    try:
        max_brief_days = int(max_briefing_gap_days)
    except (TypeError, ValueError):
        max_brief_days = 14

    total_stakeholders_evaluated = 0
    compliant_stakeholders_count = 0
    overdue_escalations_stakeholders_count = 0
    unmitigated_escalations_count = 0
    stale_briefing_stakeholders_count = 0
    total_open_escalations = 0
    findings: list[dict[str, Any]] = []

    for item in stakeholder_escalations:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("stakeholder_id")
        if raw_id is None:
            continue
        stakeholder_id = str(raw_id).strip()
        if not stakeholder_id:
            continue

        total_stakeholders_evaluated += 1

        influence_level = str(item.get("influence_level") or "").strip().upper()
        open_count = int(item.get("open_escalations_count", 0) or 0)
        oldest_days = int(item.get("oldest_open_escalation_days", 0) or 0)
        briefing_days = int(
            item.get("days_since_last_executive_briefing", 0) or 0
        )
        plan_documented = bool(item.get("action_plan_documented", False))
        sponsor_notified = bool(item.get("sponsor_notified", False))

        total_open_escalations += open_count

        overdue_escalation = open_count > 0 and oldest_days > max_esc_days
        unmitigated_escalation = open_count > 0 and (
            (not plan_documented)
            or (influence_level == "HIGH" and not sponsor_notified)
        )
        stale_briefing = briefing_days > max_brief_days

        issues: list[str] = []
        if overdue_escalation:
            overdue_escalations_stakeholders_count += 1
            issues.append("overdue_open_escalation")
        if unmitigated_escalation:
            unmitigated_escalations_count += 1
            issues.append("unmitigated_or_unnotified_escalation")
        if stale_briefing:
            stale_briefing_stakeholders_count += 1
            issues.append("stale_executive_briefing_cadence")

        if not issues:
            compliant_stakeholders_count += 1
        else:
            findings.append({"stakeholder_id": stakeholder_id, "issues": issues})

    if (
        overdue_escalations_stakeholders_count == 0
        and unmitigated_escalations_count == 0
        and stale_briefing_stakeholders_count == 0
    ):
        status = "HEALTHY"
    elif (
        overdue_escalations_stakeholders_count > 0
        or unmitigated_escalations_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_stakeholders_evaluated": total_stakeholders_evaluated,
        "compliant_stakeholders_count": compliant_stakeholders_count,
        "overdue_escalations_stakeholders_count": overdue_escalations_stakeholders_count,
        "unmitigated_escalations_count": unmitigated_escalations_count,
        "stale_briefing_stakeholders_count": stale_briefing_stakeholders_count,
        "total_open_escalations": total_open_escalations,
        "escalation_governance_status": status,
        "findings": findings,
    }


ProjectExportService.audit_executive_report_stakeholder_escalation_and_briefing_cadence = staticmethod(
    audit_executive_report_stakeholder_escalation_and_briefing_cadence
)




def audit_executive_report_esg_sustainability_and_regulatory_compliance(
    compliance_controls: list[dict],
    *,
    max_permit_expiry_warning_days: int = 30,
) -> dict:
    """Audita cumplimiento regulatorio, permisos y sostenibilidad ESG (PMBOK §2.2 y §8.1).

    Cada control aporta control_id, status, days_until_permit_expiry,
    non_compliance_fine_exposure, corrective_action_assigned y
    regulatory_authority_notified:
    - is_breached: status en {BREACHED, NON_COMPLIANT, REVOKED}
      (case-insensitive).
    - expiring_permit: days_until_permit_expiry no nulo con dias <= SLA
      de aviso.
    - unmitigated_breach: breach sin acción correctiva, o con exposición
      a multa positiva sin notificación a la autoridad.
    - total_fine_exposure_amount: suma de exposición a multas (2 dec).
    - regulatory_governance_status: 'HEALTHY' sin hallazgos; 'CRITICAL'
      con breaches o breaches sin mitigar; 'AT_RISK' en otro caso;
      findings con {control_id, issues}.
    """
    if not isinstance(compliance_controls, list):
        compliance_controls = []
    controls = [c for c in compliance_controls if isinstance(c, dict)]

    total_controls = len(controls)
    compliant_controls_count = 0
    breached_controls_count = 0
    expiring_permits_count = 0
    unmitigated_breaches_count = 0
    findings: list[dict] = []

    for idx, control in enumerate(controls, start=1):
        control_id = str(control.get("control_id", f"CONTROL-{idx}"))
        issues: list[str] = []
        is_breached = False
        has_expiring = False
        has_unmitigated = False

        status = str(control.get("status") or "").strip().upper()
        raw_days = control.get("days_until_permit_expiry")
        try:
            fine_exposure = float(control.get("non_compliance_fine_exposure", 0.0) or 0.0)
        except (TypeError, ValueError):
            fine_exposure = 0.0

        if status in {"BREACHED", "NON_COMPLIANT", "REVOKED"}:
            is_breached = True
            issues.append(f"REGULATORY_BREACH ({status})")
        if raw_days is not None:
            try:
                days = int(raw_days)
            except (TypeError, ValueError):
                days = None
            if days is not None and days <= int(max_permit_expiry_warning_days):
                has_expiring = True
                issues.append(f"PERMIT_EXPIRY_WARNING ({days}<={max_permit_expiry_warning_days})")
        if is_breached and (
            (not bool(control.get("corrective_action_assigned", False)))
            or (fine_exposure > 0.0 and not bool(control.get("regulatory_authority_notified", False)))
        ):
            has_unmitigated = True
            if not control.get("corrective_action_assigned", False):
                issues.append("CORRECTIVE_ACTION_UNASSIGNED")
            if fine_exposure > 0.0 and not control.get("regulatory_authority_notified", False):
                issues.append("AUTHORITY_NOT_NOTIFIED")

        if is_breached:
            breached_controls_count += 1
        if has_expiring:
            expiring_permits_count += 1
        if has_unmitigated:
            unmitigated_breaches_count += 1
        if not (is_breached or has_expiring or has_unmitigated):
            compliant_controls_count += 1
        if issues:
            findings.append({"control_id": control_id, "issues": issues})

    def _safe_fine(item: dict) -> float:
        try:
            return float(item.get("non_compliance_fine_exposure", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    total_fine_exposure_amount = round(sum(_safe_fine(c) for c in controls), 2)

    regulatory_governance_status = (
        "CRITICAL"
        if breached_controls_count > 0 or unmitigated_breaches_count > 0
        else (
            "AT_RISK"
            if expiring_permits_count > 0
            else "HEALTHY"
        )
    )

    return {
        "total_controls": total_controls,
        "compliant_controls_count": compliant_controls_count,
        "breached_controls_count": breached_controls_count,
        "expiring_permits_count": expiring_permits_count,
        "unmitigated_breaches_count": unmitigated_breaches_count,
        "total_fine_exposure_amount": total_fine_exposure_amount,
        "regulatory_governance_status": regulatory_governance_status,
        "findings": findings,
    }


ProjectExportService.audit_executive_report_esg_sustainability_and_regulatory_compliance = staticmethod(
    audit_executive_report_esg_sustainability_and_regulatory_compliance
)


def audit_executive_report_risk_burndown_and_residual_exposure(
    risk_burndown_snapshots: list[dict[str, Any]],
    *,
    current_contingency_reserve: float = 0.0,
    max_residual_to_reserve_ratio: float = 1.0,
) -> dict[str, Any]:
    """Audita velocidad de reduccion de riesgos (risk burndown) y cobertura de reserva frente a exposicion residual EMV (PMBOK §11.6, §4.5)."""
    if not isinstance(risk_burndown_snapshots, list):
        risk_burndown_snapshots = []

    total_periods = 0
    compliant_periods_count = 0
    expanding_risk_periods_count = 0
    overdue_mitigation_periods_count = 0
    latest_residual_emv = 0.0
    findings: list[dict[str, Any]] = []

    for raw in risk_burndown_snapshots:
        if not isinstance(raw, dict):
            continue
        total_periods += 1
        period_id = str(raw.get("period_id") or "").strip() or f"PERIOD-{total_periods}"
        initial_emv = float(raw.get("initial_emv_exposure", 0.0) or 0.0)
        closed_emv = float(raw.get("closed_or_mitigated_emv", 0.0) or 0.0)
        new_emv = float(raw.get("newly_identified_emv", 0.0) or 0.0)
        overdue_actions = int(raw.get("overdue_mitigation_actions_count", 0) or 0)

        net_emv_reduction = round(closed_emv - new_emv, 2)
        ending_residual_emv = round(max(0.0, initial_emv - net_emv_reduction), 2)
        latest_residual_emv = ending_residual_emv

        expanding_risk = net_emv_reduction < 0.0
        has_overdue_mitigations = overdue_actions > 0

        issues: list[str] = []
        if expanding_risk:
            expanding_risk_periods_count += 1
            issues.append("net_risk_exposure_expansion")
        if has_overdue_mitigations:
            overdue_mitigation_periods_count += 1
            issues.append("overdue_mitigation_actions")

        if not issues:
            compliant_periods_count += 1
        else:
            findings.append(
                {
                    "period_id": period_id,
                    "ending_residual_emv": ending_residual_emv,
                    "issues": issues,
                }
            )

    reserve_cap = float(current_contingency_reserve) * float(max_residual_to_reserve_ratio)
    reserve_coverage_shortfall = round(max(0.0, latest_residual_emv - reserve_cap), 2)
    is_reserve_underfunded = bool(reserve_coverage_shortfall > 0.0)

    if (
        expanding_risk_periods_count == 0
        and overdue_mitigation_periods_count == 0
        and not is_reserve_underfunded
    ):
        status = "HEALTHY"
    elif is_reserve_underfunded or (
        expanding_risk_periods_count > 0 and overdue_mitigation_periods_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_periods": total_periods,
        "compliant_periods_count": compliant_periods_count,
        "expanding_risk_periods_count": expanding_risk_periods_count,
        "overdue_mitigation_periods_count": overdue_mitigation_periods_count,
        "latest_residual_emv": latest_residual_emv,
        "reserve_coverage_shortfall": reserve_coverage_shortfall,
        "is_reserve_underfunded": is_reserve_underfunded,
        "risk_burndown_governance_status": status,
        "findings": findings,
    }


ProjectExportService.audit_executive_report_risk_burndown_and_residual_exposure = staticmethod(
    audit_executive_report_risk_burndown_and_residual_exposure
)


def audit_executive_report_critical_path_float_and_convergence(
    network_paths: Sequence[Mapping[str, Any]] | None,
    *,
    near_critical_float_days: float = 5.0,
    max_float_burn_rate_pct: float = 80.0,
    max_merge_point_predecessors: int = 3,
) -> dict[str, Any]:
    """Audita consumo de holgura total, holgura negativa y sesgo de convergencia en puntos de unión de la ruta crítica (PMI PMBOK §6.6 y §10.2)."""
    if (
        network_paths is None
        or isinstance(network_paths, (str, bytes))
        or not isinstance(network_paths, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = network_paths

    try:
        near_crit_days = float(near_critical_float_days)
    except (TypeError, ValueError):
        near_crit_days = 5.0

    try:
        max_burn_pct = float(max_float_burn_rate_pct)
    except (TypeError, ValueError):
        max_burn_pct = 80.0

    try:
        max_merge_preds = int(max_merge_point_predecessors)
    except (TypeError, ValueError):
        max_merge_preds = 3

    total_paths = 0
    compliant_paths = 0
    remaining_floats: list[float] = []

    negative_float_without_recovery_ids: list[str] = []
    near_critical_paths_ids: list[str] = []
    excessive_float_burn_ids: list[str] = []
    high_convergence_merge_bias_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_paths += 1

        path_id = (
            str(raw.get("id") or raw.get("path_id") or "").strip()
            or "PATH-UNKNOWN"
        )

        try:
            baseline_float_days = float(raw.get("baseline_float_days") or 0.0)
        except (TypeError, ValueError):
            baseline_float_days = 0.0

        try:
            remaining_float_days = float(raw.get("remaining_float_days") or 0.0)
        except (TypeError, ValueError):
            remaining_float_days = 0.0

        try:
            merge_predecessors_count = max(
                0, int(raw.get("merge_predecessors_count") or 0)
            )
        except (TypeError, ValueError):
            merge_predecessors_count = 0

        recovery_plan_documented = bool(raw.get("recovery_plan_documented"))
        remaining_floats.append(remaining_float_days)

        is_neg_without_recovery = (
            remaining_float_days < 0.0 and not recovery_plan_documented
        )
        is_near_critical = 0.0 < remaining_float_days <= near_crit_days
        is_excessive_burn = (
            baseline_float_days > 0.0
            and (
                (baseline_float_days - remaining_float_days)
                / baseline_float_days
            )
            * 100.0
            > max_burn_pct
        )
        is_high_convergence = (
            merge_predecessors_count > max_merge_preds
            and remaining_float_days <= near_crit_days
        )

        if is_neg_without_recovery:
            negative_float_without_recovery_ids.append(path_id)
        if is_near_critical:
            near_critical_paths_ids.append(path_id)
        if is_excessive_burn:
            excessive_float_burn_ids.append(path_id)
        if is_high_convergence:
            high_convergence_merge_bias_ids.append(path_id)

        if (
            not is_neg_without_recovery
            and not is_excessive_burn
            and not is_high_convergence
        ):
            compliant_paths += 1

    min_remaining_float_days = (
        0.0 if not remaining_floats else round(min(remaining_floats), 2)
    )

    if len(negative_float_without_recovery_ids) > 0:
        schedule_network_health = "critical"
    elif (
        len(excessive_float_burn_ids) > 0
        or len(high_convergence_merge_bias_ids) > 0
    ):
        schedule_network_health = "at_risk"
    else:
        schedule_network_health = "healthy"

    is_compliant = schedule_network_health == "healthy"

    recommendations: list[str] = []
    if negative_float_without_recovery_ids:
        recommendations.append(
            f"Documentar plan de compresión (crashing/fast-tracking) para caminos con holgura negativa sin plan de recuperación: {negative_float_without_recovery_ids}."
        )
    if excessive_float_burn_ids:
        recommendations.append(
            f"Contener tasa de consumo de holgura total (> {max_burn_pct}%) en caminos {excessive_float_burn_ids}."
        )
    if high_convergence_merge_bias_ids:
        recommendations.append(
            f"Mitigar sesgo de convergencia en hitos de unión (> {max_merge_preds} predecesores con holgura <= {near_crit_days}d) en {high_convergence_merge_bias_ids}."
        )
    if near_critical_paths_ids:
        recommendations.append(
            f"Monitorear preventivamente los caminos cuasi-críticos (0 < holgura <= {near_crit_days}d): {near_critical_paths_ids}."
        )

    return {
        "total_paths": total_paths,
        "compliant_paths": compliant_paths,
        "negative_float_without_recovery_ids": negative_float_without_recovery_ids,
        "near_critical_paths_ids": near_critical_paths_ids,
        "excessive_float_burn_ids": excessive_float_burn_ids,
        "high_convergence_merge_bias_ids": high_convergence_merge_bias_ids,
        "min_remaining_float_days": min_remaining_float_days,
        "schedule_network_health": schedule_network_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_critical_path_float_and_convergence = staticmethod(
    audit_executive_report_critical_path_float_and_convergence
)


def audit_executive_report_contract_claims_and_change_orders(
    contract_claims: Sequence[Mapping[str, Any]] | None,
    *,
    max_claim_resolution_days: int = 45,
    max_disputed_to_contract_value_pct: float = 10.0,
    require_adr_before_litigation: bool = True,
) -> dict[str, Any]:
    """Audita administración de reclamos contractuales, órdenes de cambio en disputa y escalamiento ADR previo a litigio (PMI PMBOK §12.3 y §10.2)."""
    if (
        contract_claims is None
        or isinstance(contract_claims, (str, bytes))
        or not isinstance(contract_claims, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = contract_claims

    try:
        max_days = int(max_claim_resolution_days)
    except (TypeError, ValueError):
        max_days = 45

    try:
        max_disputed_pct = float(max_disputed_to_contract_value_pct)
    except (TypeError, ValueError):
        max_disputed_pct = 10.0

    total_claims = 0
    compliant_claims = 0
    total_disputed_raw = 0.0

    unsubstantiated_claim_ids: list[str] = []
    overdue_unresolved_claim_ids: list[str] = []
    excessive_disputed_exposure_ids: list[str] = []
    premature_litigation_without_adr_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_claims += 1

        claim_id = (
            str(raw.get("id") or raw.get("claim_id") or "").strip()
            or "CLM-UNKNOWN"
        )
        status = str(raw.get("status") or "open").strip().lower()

        try:
            contract_base_value = max(
                0.0, float(raw.get("contract_base_value") or 0.0)
            )
        except (TypeError, ValueError):
            contract_base_value = 0.0

        try:
            disputed_amount = max(
                0.0, float(raw.get("disputed_amount") or 0.0)
            )
        except (TypeError, ValueError):
            disputed_amount = 0.0

        try:
            days_unresolved = max(0, int(raw.get("days_unresolved") or 0))
        except (TypeError, ValueError):
            days_unresolved = 0

        adr_attempted = bool(raw.get("adr_attempted"))
        contract_clause_referenced = bool(
            raw.get("contract_clause_referenced")
        )

        if status != "settled":
            total_disputed_raw += disputed_amount

        is_unsubstantiated = not contract_clause_referenced
        is_overdue = (
            status in {"open", "contested", "litigation"}
            and days_unresolved > max_days
        )
        is_excessive_exposure = (
            contract_base_value > 0.0
            and (disputed_amount / contract_base_value) * 100.0
            > max_disputed_pct
        )
        is_premature_litigation = (
            status == "litigation"
            and bool(require_adr_before_litigation)
            and not adr_attempted
        )

        if is_unsubstantiated:
            unsubstantiated_claim_ids.append(claim_id)
        if is_overdue:
            overdue_unresolved_claim_ids.append(claim_id)
        if is_excessive_exposure:
            excessive_disputed_exposure_ids.append(claim_id)
        if is_premature_litigation:
            premature_litigation_without_adr_ids.append(claim_id)

        if (
            not is_unsubstantiated
            and not is_overdue
            and not is_excessive_exposure
            and not is_premature_litigation
        ):
            compliant_claims += 1

    total_disputed_amount = round(total_disputed_raw, 2)

    is_compliant = (
        len(unsubstantiated_claim_ids) == 0
        and len(overdue_unresolved_claim_ids) == 0
        and len(excessive_disputed_exposure_ids) == 0
        and len(premature_litigation_without_adr_ids) == 0
    )

    if is_compliant:
        claims_governance_health = "healthy"
    elif (
        len(excessive_disputed_exposure_ids) > 0
        or len(premature_litigation_without_adr_ids) > 0
    ):
        claims_governance_health = "critical"
    else:
        claims_governance_health = "at_risk"

    recommendations: list[str] = []
    if unsubstantiated_claim_ids:
        recommendations.append(
            f"Vincular cláusula contractual o referencia SOW verificable en los reclamos {unsubstantiated_claim_ids}."
        )
    if overdue_unresolved_claim_ids:
        recommendations.append(
            f"Resolver o mediar reclamos abiertos que exceden el SLA de {max_days} días: {overdue_unresolved_claim_ids}."
        )
    if excessive_disputed_exposure_ids:
        recommendations.append(
            f"Provisionar contingencia legal para reclamos cuya disputa supera el {max_disputed_pct}% del contrato: {excessive_disputed_exposure_ids}."
        )
    if premature_litigation_without_adr_ids:
        recommendations.append(
            f"Agotar negociación directa o mecanismos ADR antes de escalar a litigio en {premature_litigation_without_adr_ids}."
        )

    return {
        "total_claims": total_claims,
        "compliant_claims": compliant_claims,
        "total_disputed_amount": total_disputed_amount,
        "unsubstantiated_claim_ids": unsubstantiated_claim_ids,
        "overdue_unresolved_claim_ids": overdue_unresolved_claim_ids,
        "excessive_disputed_exposure_ids": excessive_disputed_exposure_ids,
        "premature_litigation_without_adr_ids": premature_litigation_without_adr_ids,
        "claims_governance_health": claims_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_contract_claims_and_change_orders = staticmethod(
    audit_executive_report_contract_claims_and_change_orders
)


def audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
    vulnerabilities: Sequence[Mapping[str, Any]] | None,
    *,
    critical_cvss_threshold: float = 9.0,
    high_cvss_threshold: float = 7.0,
    max_critical_open_days: int = 7,
    max_high_open_days: int = 30,
) -> dict[str, Any]:
    """PMI PMBOK 11.6 & 8.3 — exposición de vulnerabilidades y SLA de parcheo.

    Auditoría pura sobre ``vulnerabilities``. Entradas no-lista/None se
    tratan como lista vacía y elementos no-dict se ignoran. Reglas aplicadas
    solo a estados case-insensitive ``open``/``accepted_risk``; los estados
    ``patched``/``mitigated`` no generan hallazgos:

    1. ``critical_sla_breach_or_active_exploit``: status ``open`` AND
       (``exploited_in_wild`` OR (``cvss_score >= critical_cvss_threshold``
       AND ``days_open > max_critical_open_days``)).
    2. ``high_severity_sla_breach``: status ``open`` AND
       (``high_cvss_threshold <= cvss_score < critical_cvss_threshold``) AND
       ``days_open > max_high_open_days``.
    3. ``unmitigated_accepted_risk``: status ``accepted_risk`` AND
       (``not compensating_control_documented`` OR ``cvss_score >=
       critical_cvss_threshold``).

    Returns dict con total_vulnerabilities, compliant_vulnerabilities_count,
    los 3 conteos de violación, security_posture_status
    (HEALTHY/AT_RISK/CRITICAL) y violations (dicts con ``vuln_id`` /
    ``reasons``).
    """
    raw_items = vulnerabilities if isinstance(vulnerabilities, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    total = 0
    critical_breach_count = 0
    high_breach_count = 0
    accepted_risk_count = 0
    compliant_count = 0
    violations: list[dict[str, Any]] = []

    for entry in items:
        total += 1

        vuln_id = entry.get("vuln_id")
        status_raw = entry.get("status")
        status = str(status_raw).strip().lower() if status_raw is not None else ""
        cvss_score = entry.get("cvss_score")
        days_open = entry.get("days_open")
        exploited_in_wild = entry.get("exploited_in_wild")
        compensating_control_documented = entry.get("compensating_control_documented")

        reasons: list[str] = []

        if status == "open":
            second_clause = (
                isinstance(cvss_score, (int, float))
                and cvss_score >= critical_cvss_threshold
                and isinstance(days_open, (int, float))
                and days_open > max_critical_open_days
            )
            if exploited_in_wild is True or second_clause:
                reasons.append("critical_sla_breach_or_active_exploit")

            if (
                isinstance(cvss_score, (int, float))
                and high_cvss_threshold <= cvss_score < critical_cvss_threshold
                and isinstance(days_open, (int, float))
                and days_open > max_high_open_days
            ):
                reasons.append("high_severity_sla_breach")

        elif status == "accepted_risk":
            third_clause = isinstance(cvss_score, (int, float)) and (
                cvss_score >= critical_cvss_threshold
            )
            if not compensating_control_documented or third_clause:
                reasons.append("unmitigated_accepted_risk")

        # patched / mitigated y estados desconocidos: sin hallazgos.

        ordered_reasons = list(dict.fromkeys(reasons))
        if not ordered_reasons:
            compliant_count += 1
            continue

        if "critical_sla_breach_or_active_exploit" in ordered_reasons:
            critical_breach_count += 1
        if "high_severity_sla_breach" in ordered_reasons:
            high_breach_count += 1
        if "unmitigated_accepted_risk" in ordered_reasons:
            accepted_risk_count += 1

        violations.append(
            {
                "vuln_id": vuln_id,
                "reasons": ordered_reasons,
            }
        )

    if critical_breach_count > 0 or accepted_risk_count > 0:
        posture_status = "CRITICAL"
    elif high_breach_count > 0:
        posture_status = "AT_RISK"
    else:
        posture_status = "HEALTHY"

    return {
        "total_vulnerabilities": total,
        "compliant_vulnerabilities_count": compliant_count,
        "critical_sla_breach_or_active_exploit_count": critical_breach_count,
        "high_severity_sla_breach_count": high_breach_count,
        "unmitigated_accepted_risk_count": accepted_risk_count,
        "security_posture_status": posture_status,
        "violations": violations,
    }


ProjectExportService.audit_executive_report_cybersecurity_vulnerability_and_patch_sla = staticmethod(
    audit_executive_report_cybersecurity_vulnerability_and_patch_sla
)


def audit_executive_report_capex_opex_capitalization_compliance(
    cost_entries: Sequence[Mapping[str, Any]] | None,
    *,
    capitalizable_stages: tuple[str, ...] = (
        "application_development",
        "construction",
        "hardware_acquisition",
        "implementation",
    ),
    non_capitalizable_stages: tuple[str, ...] = (
        "preliminary_discovery",
        "research",
        "training",
        "post_implementation_maintenance",
        "hypercare_support",
    ),
    min_capex_useful_life_months: int = 12,
) -> dict[str, Any]:
    """Audita la clasificación contable CapEx vs OpEx en el reporte ejecutivo: elegibilidad de capitalización por etapa (ASC 350-40 / IAS 38), vida útil mínima y registro de activo fijo (PMI PMBOK §7.3 y §10.2)."""
    if (
        cost_entries is None
        or isinstance(cost_entries, (str, bytes))
        or not isinstance(cost_entries, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = cost_entries

    cap_stages = {
        str(s).strip().lower()
        for s in (capitalizable_stages or ())
        if str(s).strip()
    }
    non_cap_stages = {
        str(s).strip().lower()
        for s in (non_capitalizable_stages or ())
        if str(s).strip()
    }

    try:
        min_life = int(min_capex_useful_life_months)
    except (TypeError, ValueError):
        min_life = 12

    total_entries = 0
    compliant_entries = 0
    total_capex_accum = 0.0
    total_opex_accum = 0.0

    improper_capex_in_opex_stage_ids: list[str] = []
    unqualified_capex_asset_ids: list[str] = []
    missed_capitalization_opportunity_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_entries += 1

        entry_id = (
            str(raw.get("id") or raw.get("entry_id") or "").strip()
            or "CST-UNKNOWN"
        )
        classification = str(raw.get("classification") or "").strip().lower()
        project_stage = str(raw.get("project_stage") or "").strip().lower()

        try:
            amount = max(0.0, float(raw.get("amount") or 0.0))
        except (TypeError, ValueError):
            amount = 0.0

        try:
            useful_life_months = max(
                0, int(raw.get("useful_life_months") or 0)
            )
        except (TypeError, ValueError):
            useful_life_months = 0

        asset_register_id = str(raw.get("asset_register_id") or "").strip()
        finance_approved = bool(raw.get("finance_approved"))

        if classification == "capex":
            total_capex_accum += amount
        elif classification == "opex":
            total_opex_accum += amount

        is_improper_capex = (
            classification == "capex" and project_stage in non_cap_stages
        )
        is_unqualified_capex = classification == "capex" and (
            useful_life_months < min_life
            or not asset_register_id
            or not finance_approved
        )
        is_missed_capex = (
            classification == "opex"
            and project_stage in cap_stages
            and useful_life_months >= min_life
            and bool(asset_register_id)
        )

        if is_improper_capex:
            improper_capex_in_opex_stage_ids.append(entry_id)
        if is_unqualified_capex:
            unqualified_capex_asset_ids.append(entry_id)
        if is_missed_capex:
            missed_capitalization_opportunity_ids.append(entry_id)

        if (
            not is_improper_capex
            and not is_unqualified_capex
            and not is_missed_capex
        ):
            compliant_entries += 1

    is_compliant = (
        len(improper_capex_in_opex_stage_ids) == 0
        and len(unqualified_capex_asset_ids) == 0
        and len(missed_capitalization_opportunity_ids) == 0
    )

    if is_compliant:
        accounting_governance_health = "healthy"
    elif (
        len(improper_capex_in_opex_stage_ids) > 0
        or len(unqualified_capex_asset_ids) > 0
    ):
        accounting_governance_health = "critical"
    else:
        accounting_governance_health = "at_risk"

    recommendations: list[str] = []
    if improper_capex_in_opex_stage_ids:
        recommendations.append(
            f"Reclasificar a OpEx las partidas en etapas no capitalizables (descubrimiento, capacitación, mantenimiento) en {improper_capex_in_opex_stage_ids}."
        )
    if unqualified_capex_asset_ids:
        recommendations.append(
            f"Asegurar vida útil >= {min_life} meses, ID de registro de activo fijo y aprobación de Finanzas para CapEx en {unqualified_capex_asset_ids}."
        )
    if missed_capitalization_opportunity_ids:
        recommendations.append(
            f"Evaluar la reclasificación a CapEx de activos elegibles en etapa de construcción/desarrollo en {missed_capitalization_opportunity_ids}."
        )

    return {
        "total_entries": total_entries,
        "compliant_entries": compliant_entries,
        "total_capex_amount": round(total_capex_accum, 2),
        "total_opex_amount": round(total_opex_accum, 2),
        "improper_capex_in_opex_stage_ids": improper_capex_in_opex_stage_ids,
        "unqualified_capex_asset_ids": unqualified_capex_asset_ids,
        "missed_capitalization_opportunity_ids": missed_capitalization_opportunity_ids,
        "accounting_governance_health": accounting_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_capex_opex_capitalization_compliance = staticmethod(
    audit_executive_report_capex_opex_capitalization_compliance
)


def audit_executive_report_key_personnel_bus_factor_and_succession(
    critical_roles: list[dict[str, Any]],
    *,
    max_single_point_of_failure_roles: int = 0,
    min_cross_training_coverage_pct: float = 80.0,
    max_annualized_turnover_pct: float = 15.0,
    total_team_headcount: int = 10,
    departures_last_12m: int = 0,
) -> dict[str, Any]:
    """Audita rotación de personal clave, factor autobús (Bus Factor / SPOF), cobertura de entrenamiento cruzado y planes de sucesión en el reporte ejecutivo (PMI PMBOK §9.4 y §9.5)."""
    if (
        critical_roles is None
        or isinstance(critical_roles, (str, bytes))
        or not isinstance(critical_roles, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = critical_roles

    try:
        max_spof = max(0, int(max_single_point_of_failure_roles))
    except (TypeError, ValueError):
        max_spof = 0

    try:
        min_training_pct = float(min_cross_training_coverage_pct)
    except (TypeError, ValueError):
        min_training_pct = 80.0

    try:
        max_turnover_pct = float(max_annualized_turnover_pct)
    except (TypeError, ValueError):
        max_turnover_pct = 15.0

    try:
        headcount = max(1, int(total_team_headcount))
    except (TypeError, ValueError):
        headcount = 1

    try:
        departures = max(0, int(departures_last_12m))
    except (TypeError, ValueError):
        departures = 0

    total_critical_roles = 0
    spof_role_ids: list[str] = []
    spof_without_succession_ids: list[str] = []
    high_flight_risk_spof_ids: list[str] = []
    under_trained_role_ids: list[str] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_critical_roles += 1

        role_id = (
            str(raw.get("role_id") or raw.get("id") or "").strip()
            or f"ROLE-{total_critical_roles}"
        )
        role_name = str(raw.get("role_name") or role_id).strip()

        raw_holders = raw.get("qualified_holders_count")
        try:
            qualified_holders_count = (
                int(raw_holders) if raw_holders is not None else 0
            )
        except (TypeError, ValueError):
            qualified_holders_count = 0

        has_documented_succession_plan = bool(
            raw.get("has_documented_succession_plan")
        )

        raw_training = raw.get("cross_training_completion_pct")
        try:
            cross_training_completion_pct = (
                float(raw_training) if raw_training is not None else 0.0
            )
        except (TypeError, ValueError):
            cross_training_completion_pct = 0.0

        attrition_flight_risk = (
            str(raw.get("attrition_flight_risk") or "low").strip().lower()
        )

        is_spof = qualified_holders_count <= 1
        if is_spof:
            spof_role_ids.append(role_id)
            if not has_documented_succession_plan:
                spof_without_succession_ids.append(role_id)
                issues.append(
                    f"Rol crítico '{role_name}' ({role_id}) es punto único de fallo (bus factor={qualified_holders_count}) sin plan de sucesión documentado."
                )
            if attrition_flight_risk == "high":
                high_flight_risk_spof_ids.append(role_id)
                issues.append(
                    f"Rol crítico '{role_name}' ({role_id}) es punto único de fallo con riesgo de fuga alto."
                )

        if cross_training_completion_pct < min_training_pct:
            under_trained_role_ids.append(role_id)
            issues.append(
                f"Rol crítico '{role_name}' ({role_id}) tiene cobertura de cross-training ({cross_training_completion_pct:.1f}%) inferior al mínimo ({min_training_pct:.1f}%)."
            )

    annualized_turnover_pct = round((departures / headcount) * 100.0, 2)
    turnover_breach = annualized_turnover_pct > max_turnover_pct
    if turnover_breach:
        issues.append(
            f"La rotación anualizada del equipo ({annualized_turnover_pct:.2f}%) excede el umbral permitido ({max_turnover_pct:.2f}%)."
        )

    spof_roles_count = len(spof_role_ids)
    if spof_roles_count > max_spof:
        issues.append(
            f"Cantidad de roles con punto único de fallo ({spof_roles_count}) supera el límite tolerado ({max_spof})."
        )

    if (
        len(high_flight_risk_spof_ids) > 0
        or len(spof_without_succession_ids) > 0
        or (spof_roles_count > max_spof and turnover_breach)
    ):
        continuity_status = "critical_bus_factor"
    elif (
        spof_roles_count > max_spof
        or len(under_trained_role_ids) > 0
        or turnover_breach
    ):
        continuity_status = "at_risk"
    else:
        continuity_status = "resilient"

    return {
        "total_critical_roles": total_critical_roles,
        "spof_roles_count": spof_roles_count,
        "spof_role_ids": spof_role_ids,
        "spof_without_succession_ids": spof_without_succession_ids,
        "high_flight_risk_spof_ids": high_flight_risk_spof_ids,
        "under_trained_role_ids": under_trained_role_ids,
        "annualized_turnover_pct": annualized_turnover_pct,
        "turnover_breach": turnover_breach,
        "continuity_status": continuity_status,
        "is_continuity_ready": continuity_status == "resilient",
        "issues": issues,
    }


ProjectExportService.audit_executive_report_key_personnel_bus_factor_and_succession = staticmethod(
    audit_executive_report_key_personnel_bus_factor_and_succession
)



def audit_executive_report_vendor_sla_and_service_credit_recovery(
    vendor_contracts: Sequence[Mapping[str, Any]] | None,
    *,
    min_uptime_or_delivery_sla_pct: float = 99.0,
    max_unrecovered_credit_ratio_pct: float = 10.0,
) -> dict[str, Any]:
    """PMBOK 12.3 — Control Procurements: SLA de vendors y créditos de servicio.

    Auditoría pura sobre ``vendor_contracts``. Entradas no-lista/None se
    tratan como lista vacía y elementos no-dict se ignoran. Cada elemento:
    ``vendor_id``, ``measured_sla_pct``, ``target_sla_pct`` (opcional, por
    defecto ``min_uptime_or_delivery_sla_pct``), ``accrued_service_credits_usd``,
    ``recovered_service_credits_usd``, ``chronic_consecutive_breach_months``.

    Reglas:
    1. ``sla_breach_vendor_ids``: ``measured_sla_pct < target_sla_pct``
       (target explícito o default). Comparación estricta; bools excluidos
       de la aritmética.
    2. ``chronic_breach_vendor_ids``:
       ``chronic_consecutive_breach_months >= 3``.
    3. ``unrecovered_credit_vendor_ids``: ``accrued > 0`` AND ratio no
       recuperado ((accrued - recovered) / accrued * 100) >
       ``max_unrecovered_credit_ratio_pct``.
    4. ``total_unrecovered_credits_usd``: suma de ``max(0.0, accrued -
       recovered)`` redondeada a 2 decimales.

    ``vendor_governance_status``: CRITICAL_DEFAULT con breaches crónicos;
    CREDITS_OR_SLA_AT_RISK con otros breach; COMPLIANT en caso contrario.
    ``is_vendor_sla_healthy`` = status == 'COMPLIANT'.
    """
    def _num(value: Any) -> float | None:
        # Helper boolean/str-safe para valores numéricos opcionales.
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    raw_items = vendor_contracts if isinstance(vendor_contracts, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    sla_breach_vendor_ids: list[str] = []
    chronic_breach_vendor_ids: list[str] = []
    unrecovered_credit_vendor_ids: list[str] = []
    total_unrecovered = 0.0

    for entry in items:
        vendor_id = entry.get("vendor_id")
        measured = _num(entry.get("measured_sla_pct"))
        accrued = _num(entry.get("accrued_service_credits_usd"))
        recovered = _num(entry.get("recovered_service_credits_usd"))
        chronic_months = entry.get("chronic_consecutive_breach_months")
        target = _num(entry.get("target_sla_pct"))
        effective_target = target if target is not None else min_uptime_or_delivery_sla_pct

        if measured is not None and measured < effective_target:
            sla_breach_vendor_ids.append(vendor_id)

        if (
            isinstance(chronic_months, (int, float))
            and not isinstance(chronic_months, bool)
            and chronic_months >= 3
        ):
            chronic_breach_vendor_ids.append(vendor_id)

        if accrued is not None and accrued > 0.0:
            unrecovered = max(0.0, accrued - (recovered if recovered is not None else 0.0))
            total_unrecovered += unrecovered
            if (unrecovered / accrued) * 100.0 > max_unrecovered_credit_ratio_pct:
                unrecovered_credit_vendor_ids.append(vendor_id)

    if chronic_breach_vendor_ids:
        vendor_governance_status = "CRITICAL_DEFAULT"
    elif sla_breach_vendor_ids or unrecovered_credit_vendor_ids:
        vendor_governance_status = "CREDITS_OR_SLA_AT_RISK"
    else:
        vendor_governance_status = "COMPLIANT"

    return {
        "total_vendor_contracts": len(items),
        "sla_breach_vendor_ids": sla_breach_vendor_ids,
        "chronic_breach_vendor_ids": chronic_breach_vendor_ids,
        "unrecovered_credit_vendor_ids": unrecovered_credit_vendor_ids,
        "total_unrecovered_credits_usd": round(total_unrecovered, 2),
        "vendor_governance_status": vendor_governance_status,
        "is_vendor_sla_healthy": vendor_governance_status == "COMPLIANT",
    }


ProjectExportService.audit_executive_report_vendor_sla_and_service_credit_recovery = staticmethod(
    audit_executive_report_vendor_sla_and_service_credit_recovery
)


def audit_executive_report_supply_chain_lead_time_and_single_source(
    procurement_items: list[dict[str, Any]],
    *,
    max_lead_time_slip_pct: float = 20.0,
    require_dual_source_on_critical_path: bool = True,
) -> dict[str, Any]:
    """Audita la volatilidad de tiempos de entrega (lead-time), cuellos de botella de proveedor único (single-source) en ruta crítica y agotamiento de buffers de suministro en el reporte ejecutivo (PMI PMBOK §11.6 y §12.3)."""
    if (
        procurement_items is None
        or isinstance(procurement_items, (str, bytes))
        or not isinstance(procurement_items, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = procurement_items

    try:
        max_slip_pct = float(max_lead_time_slip_pct)
    except (TypeError, ValueError):
        max_slip_pct = 20.0

    total_procurement_items = 0
    single_source_critical_ids: list[str] = []
    lead_time_slip_ids: list[str] = []
    buffer_exhausted_critical_ids: list[str] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_procurement_items += 1

        item_id = (
            str(raw.get("item_id") or raw.get("id") or "").strip()
            or f"PRC-{total_procurement_items}"
        )

        def _float_val(key: str) -> float:
            val = raw.get(key)
            if val is None or isinstance(val, bool):
                return 0.0
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        def _int_val(key: str) -> int:
            val = raw.get(key)
            if val is None or isinstance(val, bool):
                return 0
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0

        baseline_lead_time_days = _float_val("baseline_lead_time_days")
        current_projected_lead_time_days = _float_val(
            "current_projected_lead_time_days"
        )
        qualified_suppliers_count = _int_val("qualified_suppliers_count")
        is_on_critical_path = bool(raw.get("is_on_critical_path"))
        buffer_days_available = _float_val("buffer_days_available")

        if (
            bool(require_dual_source_on_critical_path)
            and is_on_critical_path
            and qualified_suppliers_count <= 1
        ):
            single_source_critical_ids.append(item_id)
            issues.append(
                f"Suministro crítico '{item_id}' depende de fuente única (qualified_suppliers_count={qualified_suppliers_count})."
            )

        lead_time_delta = (
            current_projected_lead_time_days - baseline_lead_time_days
        )
        if (
            baseline_lead_time_days > 0.0
            and ((lead_time_delta / baseline_lead_time_days) * 100.0)
            > max_slip_pct
        ):
            lead_time_slip_ids.append(item_id)
            issues.append(
                f"Suministro '{item_id}' presenta deslizamiento de lead-time ({current_projected_lead_time_days}d vs {baseline_lead_time_days}d) superior al {max_slip_pct}%."
            )

        if is_on_critical_path and lead_time_delta > buffer_days_available:
            buffer_exhausted_critical_ids.append(item_id)
            issues.append(
                f"Suministro crítico '{item_id}' agota el buffer disponible ({lead_time_delta}d de retraso > {buffer_days_available}d de buffer)."
            )

    if (
        len(buffer_exhausted_critical_ids) > 0
        or len(single_source_critical_ids) > 0
    ):
        supply_chain_status = "CRITICAL_BOTTLENECK"
    elif len(lead_time_slip_ids) > 0:
        supply_chain_status = "AT_RISK"
    else:
        supply_chain_status = "RESILIENT"

    return {
        "total_procurement_items": total_procurement_items,
        "single_source_critical_ids": single_source_critical_ids,
        "lead_time_slip_ids": lead_time_slip_ids,
        "buffer_exhausted_critical_ids": buffer_exhausted_critical_ids,
        "supply_chain_status": supply_chain_status,
        "is_supply_chain_resilient": supply_chain_status == "RESILIENT",
        "issues": issues,
    }


ProjectExportService.audit_executive_report_supply_chain_lead_time_and_single_source = staticmethod(
    audit_executive_report_supply_chain_lead_time_and_single_source
)


def audit_executive_report_stakeholder_sentiment_and_nps_drift(
    stakeholder_surveys: list[dict[str, Any]],
    *,
    min_acceptable_nps_score: float = 10.0,
    max_key_detractor_count: int = 0,
) -> dict[str, Any]:
    """Audita pulso de sentimiento de interesados, NPS y resistencia escalada en el informe ejecutivo (PMI PMBOK §13.4)."""
    if not isinstance(stakeholder_surveys, list):
        return {
            "total_surveyed": 0,
            "net_promoter_score_nps": 0.0,
            "key_detractor_stakeholder_ids": [],
            "declining_sentiment_stakeholder_ids": [],
            "unaddressed_detractor_ids": [],
            "sentiment_health_status": "SUPPORTIVE",
            "is_sentiment_healthy": True,
            "issues": [],
        }

    min_nps = float(
        min_acceptable_nps_score if min_acceptable_nps_score is not None else 10.0
    )
    max_key_detractors = int(
        max_key_detractor_count if max_key_detractor_count is not None else 0
    )

    total_surveyed = 0
    promoters_count = 0
    detractors_count = 0
    key_detractor_stakeholder_ids: list[str] = []
    declining_sentiment_stakeholder_ids: list[str] = []
    unaddressed_detractor_ids: list[str] = []
    issues: list[str] = []

    for idx, item in enumerate(stakeholder_surveys):
        if not isinstance(item, dict):
            continue
        total_surveyed += 1
        stakeholder_id = str(item.get("stakeholder_id") or f"STK-{idx + 1}").strip()
        rating = float(item.get("nps_rating_0_to_10") or 0.0)
        is_key = bool(item.get("is_high_influence_key_stakeholder", False))
        prev_raw = item.get("previous_nps_rating_0_to_10")
        has_concern = bool(item.get("has_unresolved_concern", False))

        if rating >= 9.0:
            promoters_count += 1
        elif rating <= 6.0:
            detractors_count += 1

        if is_key and rating <= 6.0:
            key_detractor_stakeholder_ids.append(stakeholder_id)
            issues.append(
                f"Interesado clave de alta influencia '{stakeholder_id}' en rango detractor (NPS={rating:.1f})."
            )

        if prev_raw is not None:
            prev_rating = float(prev_raw)
            if (prev_rating - rating) >= 2.0:
                declining_sentiment_stakeholder_ids.append(stakeholder_id)
                issues.append(
                    f"Interesado '{stakeholder_id}' presenta caída de sentimiento de {prev_rating:.1f} a {rating:.1f}."
                )

        if rating <= 6.0 and has_concern:
            unaddressed_detractor_ids.append(stakeholder_id)
            issues.append(
                f"Detractor '{stakeholder_id}' mantiene preocupaciones sin respuesta."
            )

    net_promoter_score_nps = (
        round(((promoters_count - detractors_count) / total_surveyed) * 100.0, 2)
        if total_surveyed > 0
        else 0.0
    )

    if total_surveyed > 0 and net_promoter_score_nps < min_nps:
        issues.append(
            f"NPS global ({net_promoter_score_nps:.2f}) inferior al umbral mínimo aceptable ({min_nps:.2f})."
        )

    if (
        len(key_detractor_stakeholder_ids) > max_key_detractors
        or len(unaddressed_detractor_ids) > 0
    ):
        sentiment_health_status = "CRITICAL_RESISTANCE"
    elif len(declining_sentiment_stakeholder_ids) > 0 or (
        total_surveyed > 0 and net_promoter_score_nps < min_nps
    ):
        sentiment_health_status = "SENTIMENT_EROSION"
    else:
        sentiment_health_status = "SUPPORTIVE"

    return {
        "total_surveyed": total_surveyed,
        "net_promoter_score_nps": net_promoter_score_nps,
        "key_detractor_stakeholder_ids": key_detractor_stakeholder_ids,
        "declining_sentiment_stakeholder_ids": declining_sentiment_stakeholder_ids,
        "unaddressed_detractor_ids": unaddressed_detractor_ids,
        "sentiment_health_status": sentiment_health_status,
        "is_sentiment_healthy": sentiment_health_status == "SUPPORTIVE",
        "issues": issues,
    }


ProjectExportService.audit_executive_report_stakeholder_sentiment_and_nps_drift = staticmethod(
    audit_executive_report_stakeholder_sentiment_and_nps_drift
)


def audit_executive_report_regulatory_and_data_privacy_compliance(
    compliance_controls: list[dict[str, Any]],
    *,
    require_dpia_for_pii: bool = True,
    max_finding_remediation_days: int = 30,
) -> dict[str, Any]:
    """Audita cumplimiento regulatorio, privacidad de datos (GDPR/Habeas Data) y SLA de hallazgos de auditoría (PMI PMBOK §4.5 / §11.6)."""
    if not isinstance(compliance_controls, list):
        return {
            "total_controls": 0,
            "missing_dpia_control_ids": [],
            "unverified_statutory_control_ids": [],
            "overdue_finding_control_ids": [],
            "regulatory_compliance_status": "COMPLIANT",
            "is_regulatory_compliant": True,
            "issues": [],
        }

    max_days = int(
        max_finding_remediation_days
        if max_finding_remediation_days is not None
        else 30
    )

    total_controls = 0
    missing_dpia_control_ids: list[str] = []
    unverified_statutory_control_ids: list[str] = []
    overdue_finding_control_ids: list[str] = []
    issues: list[str] = []

    for idx, item in enumerate(compliance_controls):
        if not isinstance(item, dict):
            continue
        total_controls += 1
        control_id = str(item.get("control_id") or f"CTRL-{idx + 1}").strip()
        processes_pii = bool(item.get("processes_personal_data_pii", False))
        dpia_done = bool(item.get("dpia_completed_and_signed", False))
        has_finding = bool(item.get("has_open_audit_finding", False))
        finding_age = int(item.get("finding_age_days") or 0)
        is_statutory = bool(item.get("is_mandatory_statutory", False))
        verified = bool(item.get("control_verified", False))

        if require_dpia_for_pii and processes_pii and not dpia_done:
            missing_dpia_control_ids.append(control_id)
            issues.append(
                f"Control '{control_id}' procesa datos personales (PII) sin evaluación DPIA completada y firmada."
            )

        if is_statutory and not verified:
            unverified_statutory_control_ids.append(control_id)
            issues.append(
                f"Control estatutario obligatorio '{control_id}' no ha sido verificado."
            )

        if has_finding and finding_age > max_days:
            overdue_finding_control_ids.append(control_id)
            issues.append(
                f"Control '{control_id}' mantiene hallazgo de auditoría abierto por {finding_age}d (> {max_days}d)."
            )

    if (
        len(missing_dpia_control_ids) > 0
        or len(unverified_statutory_control_ids) > 0
    ):
        regulatory_compliance_status = "STATUTORY_OR_PRIVACY_BREACH"
    elif len(overdue_finding_control_ids) > 0:
        regulatory_compliance_status = "REMEDIATION_OVERDUE"
    else:
        regulatory_compliance_status = "COMPLIANT"

    return {
        "total_controls": total_controls,
        "missing_dpia_control_ids": missing_dpia_control_ids,
        "unverified_statutory_control_ids": unverified_statutory_control_ids,
        "overdue_finding_control_ids": overdue_finding_control_ids,
        "regulatory_compliance_status": regulatory_compliance_status,
        "is_regulatory_compliant": regulatory_compliance_status == "COMPLIANT",
        "issues": issues,
    }


ProjectExportService.audit_executive_report_regulatory_and_data_privacy_compliance = staticmethod(
    audit_executive_report_regulatory_and_data_privacy_compliance
)


def audit_executive_report_finops_cloud_cost_and_idle_capacity(
    workloads: list[dict[str, Any]],
    *,
    max_unit_cost_drift_pct: float = 15.0,
    min_utilization_pct: float = 40.0,
    min_commitment_coverage_pct: float = 60.0,
) -> dict[str, Any]:
    """Audita deriva de costo unitario FinOps, capacidad ociosa y cobertura de instancias reservadas (PMI PMBOK §7.4 / §9.6)."""
    if not isinstance(workloads, list):
        return {
            "total_workloads": 0,
            "total_baseline_cost": 0.0,
            "total_actual_cost": 0.0,
            "total_untagged_spend": 0.0,
            "untagged_spend_share_pct": 0.0,
            "estimated_monthly_waste": 0.0,
            "unit_cost_drift_workload_ids": [],
            "idle_capacity_workload_ids": [],
            "low_commitment_workload_ids": [],
            "finops_governance_status": "OPTIMAL",
            "recommendations": [],
        }

    max_drift_pct = float(
        max_unit_cost_drift_pct if max_unit_cost_drift_pct is not None else 15.0
    )
    min_util_pct = float(
        min_utilization_pct if min_utilization_pct is not None else 40.0
    )
    min_commit_pct = float(
        min_commitment_coverage_pct
        if min_commitment_coverage_pct is not None
        else 60.0
    )

    total_workloads = 0
    sum_baseline = 0.0
    sum_actual = 0.0
    sum_untagged = 0.0
    idle_waste_sum = 0.0

    unit_cost_drift_workload_ids: list[str] = []
    idle_capacity_workload_ids: list[str] = []
    low_commitment_workload_ids: list[str] = []
    recommendations: list[str] = []

    for idx, item in enumerate(workloads):
        if not isinstance(item, dict):
            continue
        total_workloads += 1
        workload_id = str(item.get("workload_id") or f"WKL-{idx + 1}").strip()
        baseline_cost = max(0.0, float(item.get("monthly_baseline_cost") or 0.0))
        actual_cost = max(0.0, float(item.get("monthly_actual_cost") or 0.0))
        base_unit = max(0.0, float(item.get("baseline_unit_cost") or 0.0))
        actual_unit = max(0.0, float(item.get("actual_unit_cost") or 0.0))
        avg_util = float(item.get("avg_utilization_pct") or 0.0)
        commit_cov = float(
            item.get("commitment_coverage_pct")
            if item.get("commitment_coverage_pct") is not None
            else 100.0
        )
        untagged = max(0.0, float(item.get("untagged_spend_amount") or 0.0))

        sum_baseline += baseline_cost
        sum_actual += actual_cost
        sum_untagged += untagged

        if base_unit > 0.0:
            unit_drift_pct = ((actual_unit - base_unit) / base_unit) * 100.0
            if unit_drift_pct > max_drift_pct:
                unit_cost_drift_workload_ids.append(workload_id)
                recommendations.append(
                    f"Optimizar costo unitario en workload '{workload_id}' (deriva={unit_drift_pct:.2f}% > {max_drift_pct:.2f}%)."
                )

        if actual_cost > 0.0 and avg_util < min_util_pct:
            idle_capacity_workload_ids.append(workload_id)
            idle_waste_sum += actual_cost * ((min_util_pct - avg_util) / 100.0)
            recommendations.append(
                f"Redimensionar (rightsize) workload '{workload_id}' por baja utilización ({avg_util:.1f}% < {min_util_pct:.1f}%)."
            )

        if actual_cost > 0.0 and commit_cov < min_commit_pct:
            low_commitment_workload_ids.append(workload_id)
            recommendations.append(
                f"Incrementar cobertura de instancias reservadas/savings plans en workload '{workload_id}' ({commit_cov:.1f}% < {min_commit_pct:.1f}%)."
            )

    total_baseline_cost = round(sum_baseline, 2)
    total_actual_cost = round(sum_actual, 2)
    total_untagged_spend = round(sum_untagged, 2)
    untagged_spend_share_pct = (
        round((total_untagged_spend / total_actual_cost) * 100.0, 2)
        if total_actual_cost > 0.0
        else 0.0
    )
    estimated_monthly_waste = round(idle_waste_sum + total_untagged_spend, 2)

    if untagged_spend_share_pct > 5.0:
        recommendations.append(
            f"Etiquetar gasto FinOps huérfano ({untagged_spend_share_pct:.2f}% del gasto total)."
        )

    if (
        total_actual_cost > total_baseline_cost * 1.2
        or untagged_spend_share_pct > 15.0
        or len(unit_cost_drift_workload_ids) >= 2
    ):
        finops_governance_status = "CRITICAL"
    elif (
        len(unit_cost_drift_workload_ids) > 0
        or len(idle_capacity_workload_ids) > 0
        or len(low_commitment_workload_ids) > 0
        or untagged_spend_share_pct > 5.0
    ):
        finops_governance_status = "WARNING"
    else:
        finops_governance_status = "OPTIMAL"

    return {
        "total_workloads": total_workloads,
        "total_baseline_cost": total_baseline_cost,
        "total_actual_cost": total_actual_cost,
        "total_untagged_spend": total_untagged_spend,
        "untagged_spend_share_pct": untagged_spend_share_pct,
        "estimated_monthly_waste": estimated_monthly_waste,
        "unit_cost_drift_workload_ids": unit_cost_drift_workload_ids,
        "idle_capacity_workload_ids": idle_capacity_workload_ids,
        "low_commitment_workload_ids": low_commitment_workload_ids,
        "finops_governance_status": finops_governance_status,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_finops_cloud_cost_and_idle_capacity = staticmethod(
    audit_executive_report_finops_cloud_cost_and_idle_capacity
)


def audit_executive_report_sbom_cve_and_oss_license_compliance(
    dependencies: list[dict[str, Any]],
    *,
    critical_cve_sla_days: int = 7,
    high_cve_sla_days: int = 30,
    forbidden_licenses: tuple[str, ...] = ("GPL-3.0", "AGPL-3.0", "SSPL-1.0"),
) -> dict[str, Any]:
    """Audit PMI PMBOK §12.3 & §11.6 SBOM CVE remediation SLAs and OSS copyleft license compliance."""
    copyleft_violation_package_ids: list[str] = []
    breached_critical_cve_package_ids: list[str] = []
    breached_high_cve_package_ids: list[str] = []
    unpatched_zero_day_package_ids: list[str] = []
    recommendations: list[str] = []

    valid_deps = (
        [
            d
            for d in dependencies
            if isinstance(d, dict) and str(d.get("package_id", "")).strip()
        ]
        if isinstance(dependencies, list)
        else []
    )
    forbidden_set = {str(lic).strip().upper() for lic in (forbidden_licenses or ())}

    for dep in valid_deps:
        package_id = str(dep.get("package_id", "")).strip()
        spdx_license = str(dep.get("spdx_license") or "").strip().upper()
        cvss_severity = str(dep.get("cvss_severity") or "NONE").strip().upper()
        days_open = int(dep.get("days_open", 0) or 0)
        has_patch_available = (
            bool(dep.get("has_patch_available", True))
            if dep.get("has_patch_available") is not None
            else True
        )

        if spdx_license in forbidden_set or spdx_license in {
            "",
            "UNKNOWN",
            "UNLICENSED",
            "NONE",
        }:
            copyleft_violation_package_ids.append(package_id)

        if cvss_severity == "CRITICAL" and days_open > critical_cve_sla_days:
            breached_critical_cve_package_ids.append(package_id)
        elif cvss_severity == "HIGH" and days_open > high_cve_sla_days:
            breached_high_cve_package_ids.append(package_id)

        if cvss_severity in ("CRITICAL", "HIGH") and not has_patch_available:
            unpatched_zero_day_package_ids.append(package_id)

    if copyleft_violation_package_ids:
        recommendations.append(
            f"Replace or obtain commercial licensing for packages with forbidden/unverified OSS licenses: {', '.join(copyleft_violation_package_ids)}."
        )
    if breached_critical_cve_package_ids:
        recommendations.append(
            f"Expedite emergency patching for CRITICAL CVEs exceeding {critical_cve_sla_days}d SLA: {', '.join(breached_critical_cve_package_ids)}."
        )
    if breached_high_cve_package_ids:
        recommendations.append(
            f"Remediate HIGH severity CVEs exceeding {high_cve_sla_days}d SLA: {', '.join(breached_high_cve_package_ids)}."
        )
    if unpatched_zero_day_package_ids:
        recommendations.append(
            f"Apply compensating WAF/runtime controls or isolate unpatched zero-day packages: {', '.join(unpatched_zero_day_package_ids)}."
        )

    if copyleft_violation_package_ids or breached_critical_cve_package_ids:
        sbom_governance_status = "CRITICAL"
    elif breached_high_cve_package_ids or unpatched_zero_day_package_ids:
        sbom_governance_status = "WARNING"
    else:
        sbom_governance_status = "COMPLIANT"

    is_sbom_compliant = sbom_governance_status == "COMPLIANT"

    return {
        "total_dependencies": len(valid_deps),
        "copyleft_violation_package_ids": copyleft_violation_package_ids,
        "breached_critical_cve_package_ids": breached_critical_cve_package_ids,
        "breached_high_cve_package_ids": breached_high_cve_package_ids,
        "unpatched_zero_day_package_ids": unpatched_zero_day_package_ids,
        "sbom_governance_status": sbom_governance_status,
        "is_sbom_compliant": is_sbom_compliant,
        "is_release_cleared": is_sbom_compliant,
        "is_release_Cleared": is_sbom_compliant,
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_sbom_cve_and_oss_license_compliance = staticmethod(
    audit_executive_report_sbom_cve_and_oss_license_compliance
)


def audit_executive_report_disaster_recovery_rto_rpo_readiness(
    systems: Any,
    *,
    max_days_since_drill: int = 90,
) -> Dict[str, object]:
    """Auditoría PMBOK 11.5 y 8.2: preparación DR (RTO/RPO drills).

    Evalúa por sistema el cumplimiento de RTO/RPO en el drill real, la
    antigüedad del último drill y la verificación de restore de backups,
    determinando el estado DR (RESILIENT / WARNING / CRITICAL).
    """
    entries = systems if isinstance(systems, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    rto_breached_system_ids: List[str] = []
    rpo_breached_system_ids: List[str] = []
    stale_drill_system_ids: List[str] = []
    unverified_backup_system_ids: List[str] = []
    tier_zero_or_one_breach = False

    for system in rows:
        system_id = system.get("system_id")
        tier = system.get("criticality_tier", "TIER_1")

        target_rto = system.get("target_rto_minutes")
        actual_rto = system.get("actual_drill_rto_minutes")
        if (
            isinstance(target_rto, (int, float))
            and isinstance(actual_rto, (int, float))
            and actual_rto > target_rto
        ):
            rto_breached_system_ids.append(system_id)
            if tier in ("TIER_0", "TIER_1"):
                tier_zero_or_one_breach = True

        target_rpo = system.get("target_rpo_minutes")
        actual_rpo = system.get("actual_drill_rpo_minutes")
        if (
            isinstance(target_rpo, (int, float))
            and isinstance(actual_rpo, (int, float))
            and actual_rpo > target_rpo
        ):
            rpo_breached_system_ids.append(system_id)
            if tier in ("TIER_0", "TIER_1"):
                tier_zero_or_one_breach = True

        days_since_last_drill = system.get("days_since_last_drill")
        if (
            isinstance(days_since_last_drill, (int, float))
            and days_since_last_drill > max_days_since_drill
        ):
            stale_drill_system_ids.append(system_id)

        if system.get("backup_restore_verified", True) is False:
            unverified_backup_system_ids.append(system_id)

    total_systems = len(rows)
    total_breaches = len(rto_breached_system_ids) + len(rpo_breached_system_ids)

    if (
        unverified_backup_system_ids
        or tier_zero_or_one_breach
        or total_breaches >= 2
    ):
        dr_governance_status = "CRITICAL"
    elif (
        rto_breached_system_ids
        or rpo_breached_system_ids
        or stale_drill_system_ids
    ):
        dr_governance_status = "WARNING"
    else:
        dr_governance_status = "RESILIENT"

    recommendations: List[str] = []
    if unverified_backup_system_ids:
        recommendations.append(
            "Verify backup restore procedures for systems: "
            + ", ".join(str(s) for s in unverified_backup_system_ids)
        )
    if rto_breached_system_ids:
        recommendations.append(
            "Close RTO gap: drill recovery times exceeded the target for systems: "
            + ", ".join(str(s) for s in rto_breached_system_ids)
        )
    if rpo_breached_system_ids:
        recommendations.append(
            "Close RPO gap: drill data-loss windows exceeded the target for systems: "
            + ", ".join(str(s) for s in rpo_breached_system_ids)
        )
    if stale_drill_system_ids:
        recommendations.append(
            f"Run a fresh DR drill within {max_days_since_drill} days for systems: "
            + ", ".join(str(s) for s in stale_drill_system_ids)
        )

    return {
        "total_systems": total_systems,
        "rto_breached_system_ids": rto_breached_system_ids,
        "rpo_breached_system_ids": rpo_breached_system_ids,
        "stale_drill_system_ids": stale_drill_system_ids,
        "unverified_backup_system_ids": unverified_backup_system_ids,
        "dr_governance_status": dr_governance_status,
        "is_dr_compliant": dr_governance_status == "RESILIENT",
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_disaster_recovery_rto_rpo_readiness = staticmethod(
    audit_executive_report_disaster_recovery_rto_rpo_readiness
)


def audit_executive_report_software_license_true_up_and_shelfware(
    licenses: list[dict[str, Any]],
    *,
    max_shelfware_waste_pct: float = 20.0,
    true_up_penalty_multiplier: float = 1.25,
) -> dict[str, Any]:
    """Audit PMI PMBOK §12.3 & §7.4 software license true-up exposure, seat over-deployment, and shelfware waste."""
    overdeployed_subscription_ids: list[str] = []
    shelfware_subscription_ids: list[str] = []
    imminent_renewal_rightsizing_ids: list[str] = []
    recommendations: list[str] = []

    valid_licenses = (
        [
            lic
            for lic in licenses
            if isinstance(lic, dict) and str(lic.get("subscription_id", "")).strip()
        ]
        if isinstance(licenses, list)
        else []
    )

    total_true_up_exposure_cost = 0.0
    total_annual_shelfware_waste_cost = 0.0

    for lic in valid_licenses:
        subscription_id = str(lic.get("subscription_id", "")).strip()
        purchased_seats = int(lic.get("purchased_seats", 0) or 0)
        deployed_active_seats = int(lic.get("deployed_active_seats", 0) or 0)
        annual_cost_per_seat = float(lic.get("annual_cost_per_seat", 0.0) or 0.0)
        days_until_renewal = int(
            lic.get("days_until_renewal", 90)
            if lic.get("days_until_renewal") is not None
            else 90
        )

        overdeployed_seats = max(0, deployed_active_seats - purchased_seats)
        unused_shelfware_seats = max(0, purchased_seats - deployed_active_seats)
        shelfware_ratio_pct = (
            round((unused_shelfware_seats / purchased_seats) * 100.0, 2)
            if purchased_seats > 0
            else 0.0
        )

        true_up_exposure_cost = round(
            overdeployed_seats * annual_cost_per_seat * true_up_penalty_multiplier,
            2,
        )
        annual_shelfware_waste_cost = round(
            unused_shelfware_seats * annual_cost_per_seat, 2
        )

        total_true_up_exposure_cost += true_up_exposure_cost
        total_annual_shelfware_waste_cost += annual_shelfware_waste_cost

        is_overdeployed = overdeployed_seats > 0
        is_shelfware = (
            shelfware_ratio_pct > max_shelfware_waste_pct
            and unused_shelfware_seats > 0
        )

        if is_overdeployed:
            overdeployed_subscription_ids.append(subscription_id)

        if is_shelfware:
            shelfware_subscription_ids.append(subscription_id)

        if (is_overdeployed or is_shelfware) and days_until_renewal <= 30:
            imminent_renewal_rightsizing_ids.append(subscription_id)

    total_true_up_exposure_cost = round(total_true_up_exposure_cost, 2)
    total_annual_shelfware_waste_cost = round(total_annual_shelfware_waste_cost, 2)

    if overdeployed_subscription_ids:
        recommendations.append(
            f"Reclaim inactive accounts or execute pre-audit seat expansion to eliminate True-Up penalty exposure on: {', '.join(overdeployed_subscription_ids)}."
        )
    if shelfware_subscription_ids:
        recommendations.append(
            f"Deprovision unused shelfware seats (>{max_shelfware_waste_pct:.1f}% idle) on subscriptions: {', '.join(shelfware_subscription_ids)}."
        )
    if imminent_renewal_rightsizing_ids:
        recommendations.append(
            f"Expedite contract right-sizing negotiations before imminent renewal (<=30d) for: {', '.join(imminent_renewal_rightsizing_ids)}."
        )

    if overdeployed_subscription_ids:
        license_governance_status = "COMPLIANCE_RISK"
    elif shelfware_subscription_ids:
        license_governance_status = "WARNING"
    else:
        license_governance_status = "OPTIMIZED"

    return {
        "total_subscriptions": len(valid_licenses),
        "total_true_up_exposure_cost": total_true_up_exposure_cost,
        "total_annual_shelfware_waste_cost": total_annual_shelfware_waste_cost,
        "overdeployed_subscription_ids": overdeployed_subscription_ids,
        "shelfware_subscription_ids": shelfware_subscription_ids,
        "imminent_renewal_rightsizing_ids": imminent_renewal_rightsizing_ids,
        "license_governance_status": license_governance_status,
        "is_license_compliant": license_governance_status == "OPTIMIZED",
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_software_license_true_up_and_shelfware = staticmethod(
    audit_executive_report_software_license_true_up_and_shelfware
)


def audit_executive_report_pentest_remediation_sla_and_zero_trust(
    security_findings: list[dict[str, Any]],
    *,
    critical_sla_days: int = 7,
    high_sla_days: int = 30,
    days_since_last_pentest: int = 30,
    max_pentest_age_days: int = 180,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §10.2 — Executive Report Penetration Test Finding Remediation SLA, Attack Surface Drift & Zero-Trust Readiness Auditor."""
    valid_findings: list[dict[str, Any]] = []
    for item in security_findings or []:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("finding_id") or "").strip()
        if not fid:
            continue
        valid_findings.append({**item, "_fid": fid})

    stale_pentest_assessment = int(days_since_last_pentest or 0) > int(
        max_pentest_age_days or 180
    )

    if not valid_findings:
        recommendations: list[str] = []
        if stale_pentest_assessment:
            recommendations.append(
                f"Schedule updated penetration test / Red Team assessment (> {max_pentest_age_days} days elapsed)."
            )
            pentest_governance_status = "WARNING"
        else:
            pentest_governance_status = "HARDENED"
        return {
            "total_findings": 0,
            "open_findings_count": 0,
            "stale_pentest_assessment": stale_pentest_assessment,
            "breached_critical_finding_ids": [],
            "breached_high_finding_ids": [],
            "unmitigated_external_exploit_ids": [],
            "pentest_governance_status": pentest_governance_status,
            "is_security_posture_ready": pentest_governance_status == "HARDENED",
            "recommendations": recommendations,
        }

    open_findings_count = 0
    breached_critical_finding_ids: list[str] = []
    breached_high_finding_ids: list[str] = []
    unmitigated_external_exploit_ids: list[str] = []

    for fnd in valid_findings:
        fid = fnd["_fid"]
        is_remediated = bool(fnd.get("is_remediated_and_retested", False))
        if is_remediated:
            continue

        open_findings_count += 1
        severity = str(fnd.get("severity") or "").strip().upper()
        days_open = max(0, int(fnd.get("days_open", 0) or 0))
        ext_exploit = bool(fnd.get("exploitable_externally", False))
        waf_active = bool(fnd.get("compensating_waf_control_active", False))

        if severity == "CRITICAL" and days_open > critical_sla_days:
            breached_critical_finding_ids.append(fid)
        if severity == "HIGH" and days_open > high_sla_days:
            breached_high_finding_ids.append(fid)
        if severity in ("CRITICAL", "HIGH") and ext_exploit and not waf_active:
            unmitigated_external_exploit_ids.append(fid)

    recommendations = []
    if breached_critical_finding_ids:
        recommendations.append(
            f"Remediate and retest CRITICAL pentest finding(s) breaching {critical_sla_days}-day SLA: {', '.join(breached_critical_finding_ids)}."
        )
    if unmitigated_external_exploit_ids:
        recommendations.append(
            f"Deploy immediate WAF/Zero-Trust compensating controls for externally exploitable finding(s): {', '.join(unmitigated_external_exploit_ids)}."
        )
    if breached_high_finding_ids:
        recommendations.append(
            f"Remediate HIGH pentest finding(s) breaching {high_sla_days}-day SLA: {', '.join(breached_high_finding_ids)}."
        )
    if stale_pentest_assessment:
        recommendations.append(
            f"Schedule updated penetration test / Red Team assessment (> {max_pentest_age_days} days elapsed)."
        )

    if breached_critical_finding_ids or unmitigated_external_exploit_ids:
        pentest_governance_status = "BREACH_EXPOSURE"
    elif breached_high_finding_ids or stale_pentest_assessment:
        pentest_governance_status = "WARNING"
    else:
        pentest_governance_status = "HARDENED"

    return {
        "total_findings": len(valid_findings),
        "open_findings_count": open_findings_count,
        "stale_pentest_assessment": stale_pentest_assessment,
        "breached_critical_finding_ids": breached_critical_finding_ids,
        "breached_high_finding_ids": breached_high_finding_ids,
        "unmitigated_external_exploit_ids": unmitigated_external_exploit_ids,
        "pentest_governance_status": pentest_governance_status,
        "is_security_posture_ready": pentest_governance_status == "HARDENED",
        "recommendations": recommendations,
    }


ProjectExportService.audit_executive_report_pentest_remediation_sla_and_zero_trust = staticmethod(
    audit_executive_report_pentest_remediation_sla_and_zero_trust
)


def audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(
    workloads: list[dict[str, Any]],
    *,
    max_pue_ratio: float = 1.4,
    max_carbon_intensity_g_per_kwh: float = 350.0,
    carbon_budget_kg_co2e: float = 1000.0,
) -> dict[str, Any]:
    """PMI PMBOK §1.2.6 & §9.6 — Executive Report ESG Carbon Footprint (Scope 2/3), Green Cloud PUE & Sustainability Budget Auditor."""
    inefficient_pue_workload_ids: list[str] = []
    high_carbon_grid_workload_ids: list[str] = []

    valid_workloads = (
        [
            w
            for w in workloads
            if isinstance(w, dict) and str(w.get("workload_id", "")).strip()
        ]
        if isinstance(workloads, list)
        else []
    )

    total_net_co2e_raw = 0.0

    for wl in valid_workloads:
        workload_id = str(wl.get("workload_id", "")).strip()
        energy_consumed_kwh = float(wl.get("energy_consumed_kwh", 0.0) or 0.0)
        datacenter_pue = float(
            wl.get("datacenter_pue", 1.2)
            if wl.get("datacenter_pue") is not None
            else 1.2
        )
        grid_carbon_intensity_g_per_kwh = float(
            wl.get("grid_carbon_intensity_g_per_kwh", 250.0)
            if wl.get("grid_carbon_intensity_g_per_kwh") is not None
            else 250.0
        )
        renewable_energy_offset_pct = float(
            wl.get("renewable_energy_offset_pct", 0.0) or 0.0
        )

        gross_co2e_kg = (
            energy_consumed_kwh
            * datacenter_pue
            * grid_carbon_intensity_g_per_kwh
        ) / 1000.0
        offset_clamped = min(max(renewable_energy_offset_pct, 0.0), 100.0)
        net_co2e_kg = gross_co2e_kg * (1.0 - offset_clamped / 100.0)
        total_net_co2e_raw += net_co2e_kg

        if datacenter_pue > max_pue_ratio:
            inefficient_pue_workload_ids.append(workload_id)

        if grid_carbon_intensity_g_per_kwh > max_carbon_intensity_g_per_kwh:
            high_carbon_grid_workload_ids.append(workload_id)

    total_net_co2e_kg = round(total_net_co2e_raw, 2)
    budget_utilization_pct = (
        round((total_net_co2e_kg / carbon_budget_kg_co2e) * 100.0, 2)
        if carbon_budget_kg_co2e > 0.0
        else 0.0
    )

    if total_net_co2e_kg > carbon_budget_kg_co2e:
        esg_sustainability_status = "CARBON_BUDGET_BREACH"
    elif inefficient_pue_workload_ids or high_carbon_grid_workload_ids:
        esg_sustainability_status = "INEFFICIENT_INFRASTRUCTURE"
    else:
        esg_sustainability_status = "GREEN_SUSTAINABLE"

    return {
        "total_workloads_evaluated": len(valid_workloads),
        "total_net_co2e_kg": total_net_co2e_kg,
        "budget_utilization_pct": budget_utilization_pct,
        "inefficient_pue_workload_ids": inefficient_pue_workload_ids,
        "high_carbon_grid_workload_ids": high_carbon_grid_workload_ids,
        "esg_sustainability_status": esg_sustainability_status,
        "is_esg_compliant": esg_sustainability_status == "GREEN_SUSTAINABLE",
    }


ProjectExportService.audit_executive_report_esg_carbon_footprint_and_green_cloud_pue = staticmethod(
    audit_executive_report_esg_carbon_footprint_and_green_cloud_pue
)

