from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend import models, models_finance_suite
from backend.core.database import get_db
from backend.core.permissions import require_admin, require_module_access
from backend.core.rate_limit import rate_limiter
from backend.core.tenant import get_user_sede_id
from backend.models_shared import _utcnow
from backend.schemas.finance_suite import FundCreate, FundUpdate, RegisterDonationPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/finance", tags=["Finance"])

# FIN-M24: Simple TTL cache for expensive queries
_impact_cache: dict = {"data": None, "ts": 0.0}
IMPACT_CACHE_TTL = 120  # seconds


@router.get("/summary")
def get_finance_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    """Resumen financiero para el dashboard de administración."""
    sede_id = get_user_sede_id(db, current_user.id)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    income_q = db.query(func.sum(models.Donation.amount)).filter(
        models.Donation.created_at >= month_start,
        models.Donation.deleted_at.is_(None),
    )
    if sede_id:
        income_q = income_q.filter(models.Donation.sede_id == sede_id)
    total_income = income_q.scalar() or 0

    expense_q = db.query(func.sum(models_finance_suite.ExpenseReport.total_amount)).filter(
        models_finance_suite.ExpenseReport.status == "reimbursed",
        models_finance_suite.ExpenseReport.reimbursed_at >= month_start,
    )
    if sede_id:
        expense_q = expense_q.filter(models_finance_suite.ExpenseReport.sede_id == sede_id)
    total_expense = expense_q.scalar() or 0

    # Balance: fondos activos de la sede + ingresos del mes
    fund_q = db.query(func.sum(models.Fund.current_balance))
    if sede_id:
        fund_q = fund_q.filter(models.Fund.sede_id == sede_id)
    total_funds = fund_q.scalar() or 0
    balance = round(float(total_income) - float(total_expense))

    return {
        "balance": balance,
        "total_income": round(total_income),
        "total_expense": round(total_expense),
        "funds_total": round(total_funds),
    }


@router.get("/funds")
def get_ministerial_funds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    """Resumen de fondos en tiempo real calculado desde donations."""
    sede_id = get_user_sede_id(db, current_user.id)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    income_q = db.query(func.sum(models.Donation.amount)).filter(
        models.Donation.created_at >= month_start,
        models.Donation.deleted_at.is_(None),
    )
    if sede_id:
        income_q = income_q.filter(models.Donation.sede_id == sede_id)
    total_ingresos = income_q.scalar() or 0

    expense_q = db.query(func.sum(models_finance_suite.ExpenseReport.total_amount)).filter(
        models_finance_suite.ExpenseReport.status == "reimbursed",
        models_finance_suite.ExpenseReport.reimbursed_at >= month_start,
    )
    if sede_id:
        expense_q = expense_q.filter(models_finance_suite.ExpenseReport.sede_id == sede_id)
    total_egresos = expense_q.scalar() or 0

    by_type_q = db.query(
        models.Donation.donation_type,
        func.sum(models.Donation.amount).label("total"),
    ).filter(
        models.Donation.created_at >= month_start,
        models.Donation.deleted_at.is_(None),
    )
    if sede_id:
        by_type_q = by_type_q.filter(models.Donation.sede_id == sede_id)
    by_type = by_type_q.group_by(models.Donation.donation_type).all()

    all_time_q = db.query(func.sum(models.Donation.amount)).filter(
        models.Donation.deleted_at.is_(None),
    )
    if sede_id:
        all_time_q = all_time_q.filter(models.Donation.sede_id == sede_id)
    total_all_time = all_time_q.scalar() or 0

    return {
        "ingresos_mes": round(total_ingresos),
        "egresos_mes": round(total_egresos),
        "balance": round(float(total_ingresos) - float(total_egresos)),
        # FIN-H15: Reserva = 10% del total histórico (política financiera CCF)
        "reserva": round(float(total_all_time) * 0.10),
        "total_historico": round(total_all_time),
        "por_tipo": [{"tipo": r[0] or "Ofrenda", "total": round(r[1])} for r in by_type],
    }


@router.get("/transactions")
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    """Historial de transacciones reales desde la tabla donations."""
    sede_id = get_user_sede_id(db, current_user.id)
    q = (
        db.query(models.Donation)
        .options(joinedload(models.Donation.persona))
        .filter(
            models.Donation.deleted_at.is_(None),
        )
        .order_by(models.Donation.created_at.desc())
    )
    if sede_id:
        q = q.filter(models.Donation.sede_id == sede_id)
    # FIN-H02: Implementar filtro por tipo (antes era código muerto)
    if tipo:
        q = q.filter(models.Donation.donation_type == tipo)
    rows = q.offset(skip).limit(limit).all()

    result = []
    for d in rows:
        person_obj = None
        if d.persona:
            full_name = f"{d.persona.first_name} {d.persona.last_name}".strip()
            person_obj = {
                "id": str(d.persona.id),
                "persona_id": str(d.persona.id),
                "nombre_completo": full_name,
                "full_name": full_name,
                "first_name": d.persona.first_name,
                "last_name": d.persona.last_name,
                "email": d.persona.email,
            }
        result.append(
            {
                "id": d.id,
                "donation_id": d.id,
                "type": "ingreso",
                "donation_type": d.donation_type,
                "category": d.donation_type or "Ofrenda",
                "description": f"Donación {d.donation_type or 'general'} - {d.donor_name or 'Anónimo'}",
                "amount": d.amount,
                "date": d.donation_date.isoformat() if d.donation_date else (d.created_at.isoformat() if d.created_at else None),
                "transaction_date": d.donation_date.isoformat() if d.donation_date else (d.created_at.isoformat() if d.created_at else None),
                "persona_id": d.persona_id,
                "donor_name": d.donor_name,
                "person": person_obj,
            }
        )
    return result


@router.post(
    "/donations",
    status_code=201,
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def register_donation(
    payload: RegisterDonationPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Registra una nueva donacion. Solo para admin."""
    # FIN-C05: Validar que fund exista y pertenezca a la sede del usuario
    fund = db.query(models.Fund).filter(models.Fund.fund_id == payload.fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id and fund.sede_id and str(fund.sede_id) != sede_id:
        raise HTTPException(status_code=403, detail="Fund not in your sede")

    donation = models.Donation(
        persona_id=str(payload.persona_id) if payload.persona_id else None,
        amount=payload.amount,
        donation_type=payload.donation_type,
        donor_name=payload.donor_name or current_user.username,
        fund_id=str(payload.fund_id),
        sede_id=sede_id,
    )
    db.add(donation)
    fund.current_balance = (fund.current_balance or 0) + payload.amount
    db.commit()
    db.refresh(donation)
    return {
        "id": donation.id,
        "amount": donation.amount,
        "type": donation.donation_type,
        "donor": donation.donor_name,
        "created_at": donation.created_at.isoformat() if donation.created_at else None,
    }


@router.get("/admin/funds")
def list_funds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    # FIN-C02: Filtrar fondos por sede
    sede_id = get_user_sede_id(db, current_user.id)
    q = db.query(models.Fund).order_by(models.Fund.fund_id)
    if sede_id:
        q = q.filter(models.Fund.sede_id == sede_id)
    funds = q.all()
    return [
        {
            "id": f.fund_id,
            "fund_id": f.fund_id,
            "name": f.name,
            "description": f.description,
            "is_public": f.is_public,
            "current_balance": f.current_balance,
            "target_amount": f.target_amount,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in funds
    ]


@router.post("/admin/funds", status_code=201)
def create_fund(
    payload: FundCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    # FIN-C03: Pydantic payload en vez de dict
    sede_id = get_user_sede_id(db, current_user.id)
    fund = models.Fund(
        sede_id=sede_id,
        name=payload.name,
        description=payload.description,
        is_public=payload.is_public,
        target_amount=payload.target_amount,
        current_balance=0.0,
    )
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return {
        "fund_id": fund.fund_id,
        "name": fund.name,
        "description": fund.description,
        "is_public": fund.is_public,
        "current_balance": fund.current_balance,
        "target_amount": fund.target_amount,
    }


@router.patch("/admin/funds/{fund_id}")
def update_fund(
    fund_id: str,
    payload: FundUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    # FIN-C04: Pydantic payload en vez de dict + setattr peligroso
    fund = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id and fund.sede_id and str(fund.sede_id) != sede_id:
        raise HTTPException(status_code=403, detail="Fund not in your sede")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fund, k, v)
    db.commit()
    db.refresh(fund)
    return {
        "fund_id": fund.fund_id,
        "name": fund.name,
        "description": fund.description,
        "is_public": fund.is_public,
        "current_balance": fund.current_balance,
        "target_amount": fund.target_amount,
    }


@router.delete("/admin/funds/{fund_id}", status_code=204)
def delete_fund(
    fund_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    fund = db.query(models.Fund).filter(models.Fund.fund_id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    sede_id = get_user_sede_id(db, current_user.id)
    if sede_id and fund.sede_id and str(fund.sede_id) != sede_id:
        raise HTTPException(status_code=403, detail="Fund not in your sede")
    fund.deleted_at = _utcnow()
    db.commit()
    logger.info("Fund deleted: fund_id=%s by user=%s sede=%s", fund_id, current_user.id, sede_id)


@router.get("/impact")
def get_mission_impact(
    db: Session = Depends(get_db),
    # FIN-C10: Agregar auth — antes era endpoint público
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    """Impacto social calculado en tiempo real."""
    now_ts = time.monotonic()
    if _impact_cache["data"] and (now_ts - _impact_cache["ts"]) < IMPACT_CACHE_TTL:
        return _impact_cache["data"]

    total_personas = db.query(func.count(models.Persona.id)).scalar() or 0
    total_families = db.query(func.count(models.Family.id)).scalar() or 0
    total_donations = db.query(func.sum(models.Donation.amount)).scalar() or 0
    total_enrollments = db.query(func.count(models.Enrollment.id)).scalar() or 0

    # Distribucion basada en categorias de donacion reales
    by_category = (
        db.query(
            models.Donation.donation_type,
            func.sum(models.Donation.amount).label("total"),
        )
        .group_by(models.Donation.donation_type)
        .all()
    )

    total_cat = sum(r[1] for r in by_category) or 1
    distribucion = [{"label": r[0] or "Ofrenda", "pct": round(r[1] / total_cat * 100), "desc": ""} for r in by_category]
    if not distribucion:
        distribucion = [{"label": "Ofrendas Generales", "pct": 100, "desc": "Donaciones recibidas."}]

    result = {
        "total_miembros": total_personas,
        "total_familias": total_families,
        "total_donaciones_cop": round(total_donations),
        "total_matriculas": total_enrollments,
        "distribucion": distribucion,
    }
    _impact_cache["data"] = result
    _impact_cache["ts"] = time.monotonic()
    return result
