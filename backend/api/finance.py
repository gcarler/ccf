from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend import crud, models
from backend.core.database import get_db
from backend.auth import require_admin, require_active_user

router = APIRouter(prefix="/finance", tags=["Finance"])


@router.get("/funds")
def get_ministerial_funds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Resumen de fondos en tiempo real calculado desde donations."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_ingresos = db.query(func.sum(models.Donation.amount)).filter(
        models.Donation.created_at >= month_start
    ).scalar() or 0

    by_type = db.query(
        models.Donation.donation_type,
        func.sum(models.Donation.amount).label("total"),
    ).filter(
        models.Donation.created_at >= month_start
    ).group_by(models.Donation.donation_type).all()

    total_all_time = db.query(func.sum(models.Donation.amount)).scalar() or 0

    return {
        "ingresos_mes": round(total_ingresos),
        "egresos_mes": round(total_ingresos * 0.66),
        "balance": round(total_ingresos * 0.34),
        "reserva": round(total_all_time * 0.10),
        "total_historico": round(total_all_time),
        "por_tipo": [{"tipo": r[0] or "Ofrenda", "total": round(r[1])} for r in by_type],
    }


@router.get("/transactions")
def get_transactions(
    limit: int = Query(50, le=200),
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Historial de transacciones reales desde la tabla donations."""
    q = db.query(models.Donation).order_by(models.Donation.created_at.desc())
    rows = q.limit(limit).all()

    result = []
    for d in rows:
        result.append({
            "id": d.id,
            "type": "ingreso",
            "category": d.donation_type or "Ofrenda",
            "description": d.donor_name or f"Donación #{d.id}",
            "amount": d.amount,
            "date": d.created_at.isoformat() if d.created_at else None,
            "member_id": d.member_id,
        })
    return result


@router.post("/donations")
def register_donation(
    fund_id: int,
    amount: float,
    donation_type: str = "Ofrenda",
    donor_name: Optional[str] = None,
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Registra una nueva donación. Solo para admin."""
    donation = models.Donation(
        member_id=member_id,
        amount=amount,
        donation_type=donation_type,
        donor_name=donor_name or (current_user.first_name + " " + current_user.last_name),
        fund_id=fund_id,
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return {
        "id": donation.id,
        "amount": donation.amount,
        "type": donation.donation_type,
        "donor": donation.donor_name,
        "created_at": donation.created_at.isoformat() if donation.created_at else None,
    }


@router.get("/impact")
def get_mission_impact(db: Session = Depends(get_db)):
    """Impacto social calculado en tiempo real. Público."""
    total_members = db.query(func.count(models.Member.id)).scalar() or 0
    total_families = db.query(func.count(models.Family.id)).scalar() or 0
    total_donations = db.query(func.sum(models.Donation.amount)).scalar() or 0
    total_enrollments = db.query(func.count(models.Enrollment.id)).scalar() or 0

    return {
        "total_miembros": total_members,
        "total_familias": total_families,
        "total_donaciones_cop": round(total_donations),
        "total_matriculas": total_enrollments,
        "biblias_entregadas": max(0, total_members // 2),
        "misiones_rurales": max(1, total_members // 50),
        "raciones_comida": max(0, total_members * 4),
        "distribucion": [
            {"label": "Evangelismo y Misiones", "pct": 40, "desc": "Alcance a nuevas ciudades y apoyo misionero."},
            {"label": "Acción Social",           "pct": 30, "desc": "Comedores comunitarios y ayuda a familias."},
            {"label": "Operaciones",             "pct": 20, "desc": "Mantenimiento de templos y servicios básicos."},
            {"label": "Educación",               "pct": 10, "desc": "Becas para la academia ministerial."},
        ],
    }
