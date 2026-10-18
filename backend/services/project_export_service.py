"""Servicio de exportación 360° de Proyectos, incluida la gobernanza PMI."""

from __future__ import annotations

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
    "ProjectExportService",
]


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


class ProjectExportService:
    """Fachada canónica de informes ejecutivos con ``governance_summary`` PMI."""

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
