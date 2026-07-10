from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from backend.models_crm_pipeline import EtapaPipeline, PipelineCRM
from backend.models_shared import _utcnow


def list_pipelines(db: Session, sede_id: UUID) -> list[PipelineCRM]:
    return (
        db.query(PipelineCRM)
        .filter(PipelineCRM.sede_id == sede_id, PipelineCRM.deleted_at.is_(None))
        .order_by(PipelineCRM.nombre)
        .all()
    )


def get_pipeline(db: Session, pipeline_id: UUID) -> PipelineCRM | None:
    return (
        db.query(PipelineCRM)
        .filter(PipelineCRM.id == pipeline_id, PipelineCRM.deleted_at.is_(None))
        .first()
    )


def create_pipeline(db: Session, data: dict) -> PipelineCRM:
    row = PipelineCRM(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_pipeline(db: Session, row: PipelineCRM, data: dict) -> PipelineCRM:
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def archive_pipeline(db: Session, row: PipelineCRM) -> None:
    row.deleted_at = _utcnow()
    db.commit()


def list_stages(db: Session, pipeline_id: UUID) -> list[EtapaPipeline]:
    return (
        db.query(EtapaPipeline)
        .filter(
            EtapaPipeline.pipeline_id == pipeline_id,
            EtapaPipeline.deleted_at.is_(None),
        )
        .order_by(EtapaPipeline.orden)
        .all()
    )


def get_stage(db: Session, stage_id: UUID) -> EtapaPipeline | None:
    return (
        db.query(EtapaPipeline)
        .filter(EtapaPipeline.id == stage_id, EtapaPipeline.deleted_at.is_(None))
        .first()
    )


def create_stage(db: Session, data: dict) -> EtapaPipeline:
    row = EtapaPipeline(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_stage(db: Session, row: EtapaPipeline, data: dict) -> EtapaPipeline:
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def archive_stage(db: Session, row: EtapaPipeline) -> None:
    row.deleted_at = _utcnow()
    db.commit()
