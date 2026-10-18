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
    "audit_executive_report_milestone_coverage",
    "audit_risks_csv_register_completeness",
    "audit_stakeholders_csv_engagement_gaps",
    "audit_expenses_vendor_concentration",
    "audit_executive_report_change_governance",
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




